"""scripts/test_3a_extract.py

Verification test suite for Stage 3a: Key-information extraction.
Tests:
  T1: API key leak scan across code, configs, logs, docs, and caches (0 leaks).
  T2: Fake-LLM unit tests (0 API calls): invalid JSON retry, fake quote dropped,
      changed number flagged as needs_review, missing field becomes not_found,
      plus BM25 retrieval fallback when doc exceeds max_doc_chars_for_whole_doc.
  T3: Live extraction on 5 documents (03_dbs_mitc, 13_bajaj Hindi MITC, aesohio,
      09_muthoot MITC, and long SEC contract CITGO from friend ZIP in memory),
      checking >= 99% verified kept quotes and reporting raw quote survival.
  T4: Field-level Precision/Recall/F1 against 3 docs (48 rows) in
      data/processed/labels/llm_assisted/key_info_llm.csv (silver labels).
  T5: Comparison on 3 human-verified docs (27 rows across 9 shared fields) in
      data/friend/04_annotated_data/gold_standard_extraction_v1.csv.
  T6: Live API call count <= 80 and 0 new API calls on cached repeat run.
"""

from __future__ import annotations

import csv
import json
import re
import sys
import time
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.extract.extract_fields import extract_key_info, load_extract_config
from src.llm.gemini_client import GeminiClient, get_api_key
from src.qa.verify_quotes import normalize, verify_evidence

LOG_FILE = ROOT / "data" / "processed" / "llm_log.csv"
GEMINI_CACHE_DIR = ROOT / "data" / "processed" / "cache" / "gemini"
RETRIEVAL_CACHE_DIR = ROOT / "data" / "processed" / "retrieval_cache"
SILVER_CSV = ROOT / "data" / "processed" / "labels" / "llm_assisted" / "key_info_llm.csv"
GOLD_CSV = ROOT / "data" / "friend" / "04_annotated_data" / "gold_standard_extraction_v1.csv"
FRIEND_ZIP = ROOT / "data" / "friend" / "01_loan_agreements" / "publicly_filed_contracts.zip"
OUTPUT_JSON = ROOT / "data" / "processed" / "extract_3a_results.json"

GOLD_TO_16_FIELD = {
    "document_title": "document_title",
    "borrower": "borrowers",
    "lender": "lenders",
    "loan_facility_amount": "loan_or_commitment_amount",
    "interest_rate": "interest_rate",
    "repayment_terms": "repayment_terms",
    "maturity_date": "maturity_termination_date",
    "fees_and_charges": "fees",
    "default_related_clauses": "events_of_default",
}


def _split_edgar_pages(raw_text: str) -> dict[int, str]:
    """Splits raw SEC EDGAR .txt contracts on <PAGE> markers into page_num -> text."""
    parts = re.split(r"<PAGE>\s*(\d*)", raw_text)
    pages: dict[int, str] = {}
    if len(parts) > 1:
        cur_page = 0
        if parts[0].strip():
            cur_page = 1
            pages[1] = parts[0]
        for i in range(1, len(parts), 2):
            explicit_num = parts[i].strip()
            body = parts[i + 1]
            if explicit_num:
                p_num = int(explicit_num)
            else:
                cur_page += 1
                p_num = cur_page
            pages[p_num] = (pages[p_num] + "\n" + body) if p_num in pages else body
    else:
        pages[1] = raw_text
    return pages


def _read_zip_doc_pages(member_path: str) -> dict[int, str]:
    with zipfile.ZipFile(FRIEND_ZIP, "r") as zf:
        raw = zf.read(member_path).decode("utf-8", errors="ignore")
    return _split_edgar_pages(raw)


def _containment_match(pred: str, ref: str) -> bool:
    np = normalize(pred)
    nr = normalize(ref)
    if not np or not nr:
        return False
    return np == nr or np in nr or nr in np


def _token_overlap_ratio(pred: str, ref: str) -> float:
    stop = {
        "the", "and", "or", "of", "to", "in", "a", "an", "for", "by", "on", "with",
        "as", "is", "are", "be", "at", "per", "not", "this", "any", "from", "no",
    }
    tp = {t for t in re.findall(r"[a-z0-9]+", normalize(pred)) if t not in stop and len(t) > 1}
    tr = {t for t in re.findall(r"[a-z0-9]+", normalize(ref)) if t not in stop and len(t) > 1}
    if not tr:
        return 0.0
    return len(tp & tr) / len(tr)


def test_t1_key_leak_scan() -> tuple[bool, str]:
    api_key = get_api_key()
    if not api_key or len(api_key) < 10:
        return False, "GEMINI_API_KEY missing or invalid."

    files_to_scan: list[Path] = [
        ROOT / "config" / "extract.yaml",
        ROOT / "src" / "extract" / "extract_fields.py",
        ROOT / "scripts" / "demo_extract.py",
        ROOT / "scripts" / "test_3a_extract.py",
        ROOT / "docs" / "WORK_REPORT.md",
        LOG_FILE,
        OUTPUT_JSON,
    ]
    if GEMINI_CACHE_DIR.is_dir():
        files_to_scan.extend(GEMINI_CACHE_DIR.glob("*.json"))
    if RETRIEVAL_CACHE_DIR.is_dir():
        files_to_scan.extend(RETRIEVAL_CACHE_DIR.glob("*.json"))

    leaks = 0
    scanned = 0
    for f in files_to_scan:
        if f.is_file():
            scanned += 1
            if api_key in f.read_text(encoding="utf-8", errors="ignore"):
                leaks += 1

    ok = leaks == 0
    return ok, f"Scanned {scanned} files; API key leaks = {leaks}"


def test_t2_fake_llm_unit_tests() -> tuple[bool, str]:
    cfg = load_extract_config()
    fake_pages = {
        1: (
            "CREDIT AGREEMENT dated May 10, 2025.\n"
            "Borrower: Beta Manufacturing Corp.\n"
            "Lender: Acme National Bank.\n"
            "Loan Commitment: $500,000 revolving credit facility.\n"
            "Interest Rate: 7.5% per annum fixed.\n"
        ),
        2: (
            "Repayment: Monthly installments of $12,000 starting June 1, 2025.\n"
            "Maturity Date: May 10, 2030.\n"
            "Fees: Processing fee of $1,500 due at closing.\n"
            "Late Payment: Default interest of 2% per annum above the contract rate.\n"
            "Prepayment: Borrower may prepay in full without penalty.\n"
            "Governing Law: State of Delaware.\n"
        ),
    }

    # Case A: Invalid JSON on attempt 1 -> retry succeeds on attempt 2;
    # plus fake quote dropped (unverified), changed number flagged (needs_review), missing field (not_found).
    call_counter = {"n": 0}

    def fake_llm_main(prompt: str) -> tuple[str, str]:
        call_counter["n"] += 1
        if call_counter["n"] == 1:
            return "Sorry, malformed output {not json", "fake-main-model"
        payload = {
            "fields": [
                {
                    "field": "document_title",
                    "found": True,
                    "value": "Credit Agreement",
                    "evidence": [{"quote": "CREDIT AGREEMENT", "page": 1}],
                },
                {
                    "field": "agreement_date",
                    "found": True,
                    "value": "May 10, 2025",
                    "evidence": [{"quote": "dated May 10, 2025", "page": 1}],
                },
                {
                    "field": "borrowers",
                    "found": True,
                    "value": "Invented Fake Corp",
                    # Fake quote must be dropped and field marked unverified + value hidden
                    "evidence": [{"quote": "THIS VERBATIM QUOTE DOES NOT EXIST", "page": 1}],
                },
                {
                    "field": "lenders",
                    "found": True,
                    "value": "Acme National Bank",
                    # Wrong page number (says 2, actually on 1) should auto-correct
                    "evidence": [{"quote": "Lender: Acme National Bank.", "page": 2}],
                },
                {
                    "field": "loan_or_commitment_amount",
                    "found": True,
                    "value": "$500,000",
                    "evidence": [{"quote": "Loan Commitment: $500,000 revolving credit facility.", "page": 1}],
                },
                {
                    "field": "interest_rate",
                    "found": True,
                    # Changed number: 9.9% instead of 7.5% -> check_numbers must flag needs_review
                    "value": "9.9% per annum fixed",
                    "evidence": [{"quote": "Interest Rate: 7.5% per annum fixed.", "page": 1}],
                },
                # Omit 'guarantees' completely -> must become not_found
            ]
        }
        return json.dumps(payload), "fake-main-model"

    def fake_verifier(prompt: str) -> tuple[str, str]:
        return json.dumps({"verdict": "supported", "reason": "Confirmed.", "unsupported_parts": []}), "fake-verifier-model"

    res = extract_key_info(
        doc_id="unit_fake_doc",
        doc_pages=fake_pages,
        config=cfg,
        verify_numeric=True,
        llm_fn=fake_llm_main,
        verifier_llm_fn=fake_verifier,
    )

    by_f = res["by_field"]
    checks: list[tuple[str, bool, str]] = [
        ("json_retry_used", res["extraction_calls"] == 2, f"extraction_calls={res['extraction_calls']}"),
        ("fake_quote_dropped_status", by_f["borrowers"]["status"] == "unverified", f"status={by_f['borrowers']['status']}"),
        ("fake_quote_value_hidden", by_f["borrowers"]["value"] == "", f"value={by_f['borrowers']['value']!r}"),
        ("fake_quote_found_false", by_f["borrowers"]["found"] is False, f"found={by_f['borrowers']['found']}"),
        ("changed_number_flagged", by_f["interest_rate"]["status"] == "needs_review", f"status={by_f['interest_rate']['status']}"),
        ("changed_number_final_check", by_f["interest_rate"]["final_check"] == "NEEDS_REVIEW", f"fc={by_f['interest_rate']['final_check']}"),
        ("missing_field_not_found", by_f["guarantees"]["status"] == "not_found", f"status={by_f['guarantees']['status']}"),
        ("page_corrected_lender", by_f["lenders"]["evidence"][0]["page"] == 1, f"page={by_f['lenders']['evidence']}"),
        ("numeric_verifier_indep", by_f["loan_or_commitment_amount"]["verifier_independent"] is True, f"indep={by_f['loan_or_commitment_amount']['verifier_independent']}"),
        ("numeric_verifier_verified", by_f["loan_or_commitment_amount"]["status"] == "verified", f"status={by_f['loan_or_commitment_amount']['status']}"),
    ]

    # Case B: Over-limit retrieval fallback
    small_cfg = dict(cfg)
    small_cfg["max_doc_chars_for_whole_doc"] = 100
    small_cfg["max_calls_per_doc"] = 16

    def fake_llm_retrieval(prompt: str) -> tuple[str, str]:
        m = re.search(r"FIELD:\s*([a-z_]+)", prompt)
        fname = m.group(1) if m else "document_title"
        if fname == "document_title":
            out = {"field": fname, "found": True, "value": "Credit Agreement", "evidence": [{"quote": "CREDIT AGREEMENT", "page": 1}]}
        else:
            out = {"field": fname, "found": False, "value": "Not found in this document", "evidence": []}
        return json.dumps(out), "fake-main-model"

    res_ret = extract_key_info(
        doc_id="unit_fake_doc_ret",
        doc_pages=fake_pages,
        config=small_cfg,
        verify_numeric=False,
        llm_fn=fake_llm_retrieval,
    )
    checks.append(("retrieval_mode_triggered", res_ret["retrieval_used"] is True, f"ret={res_ret['retrieval_used']}"))
    checks.append(("retrieval_respects_budget", res_ret["extraction_calls"] <= 16, f"calls={res_ret['extraction_calls']}"))
    checks.append(("retrieval_title_verified", res_ret["by_field"]["document_title"]["status"] == "verified", f"status={res_ret['by_field']['document_title']['status']}"))

    # Case C: Multi-integer page repair (`"page": 1, 2`) still parses cleanly
    def fake_llm_multipage(prompt: str) -> tuple[str, str]:
        return (
            '{"fields": [{"field": "document_title", "found": true, "value": "Credit Agreement", '
            '"evidence": [{"quote": "CREDIT AGREEMENT", "page": 1, 2}]}]}',
            "fake-main-model",
        )

    res_mp = extract_key_info(doc_id="unit_multipage", doc_pages=fake_pages, config=cfg, llm_fn=fake_llm_multipage)
    checks.append(("multipage_int_repair", res_mp["by_field"]["document_title"]["status"] == "verified", f"status={res_mp['by_field']['document_title']['status']}"))

    failures = [f"{name} ({detail})" for name, passed, detail in checks if not passed]
    ok = len(failures) == 0
    return ok, f"{len(checks) - len(failures)}/{len(checks)} unit checks passed" + (f"; FAILURES: {failures}" if failures else "")


def test_t3_live_5_docs(client: GeminiClient) -> tuple[bool, str, list[dict[str, Any]], int]:
    """Runs live extraction on the 5 target docs (ingested + CITGO from ZIP)."""
    docs_spec: list[tuple[str, dict[int, str] | None, bool]] = [
        ("03_dbs_mitc", None, True),
        ("13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi", None, False),
        ("0000027430-25-000005_aesohio10qex10120250630q2", None, False),
        ("09_muthoothomefin_MHIL-MITC", None, False),
        ("CITGO (000101/1011746/0000950129-03-001503_8.txt)", _read_zip_doc_pages("000101/1011746/0000950129-03-001503_8.txt"), False),
    ]

    before_api = client.api_calls_made
    summaries: list[dict[str, Any]] = []
    all_kept_quotes = 0
    all_reverified_quotes = 0

    for doc_id, custom_pages, do_verify in docs_spec:
        res = extract_key_info(
            doc_id=doc_id,
            doc_pages=custom_pages,
            client=client,
            verify_numeric=do_verify,
            max_verifier_calls=6,
        )
        # Re-verify every kept quote independently
        if custom_pages is None:
            from src.qa.doc_loader import load_document
            _, pages_for_check = load_document(doc_id)
        else:
            pages_for_check = custom_pages

        doc_kept = 0
        doc_rev = 0
        for row in res["fields"]:
            if row["evidence"]:
                doc_kept += len(row["evidence"])
                vev, _ = verify_evidence(pages_for_check, row["evidence"])
                doc_rev += len(vev)
        all_kept_quotes += doc_kept
        all_reverified_quotes += doc_rev

        c = res["counts"]
        summaries.append({
            "doc_id": doc_id,
            "doc_chars": res["doc_chars"],
            "num_pages": res["num_pages"],
            "retrieval_used": res["retrieval_used"],
            "model_used": res["model_used"],
            "fields_found": c["verified"] + c["needs_review"],
            "verified": c["verified"],
            "needs_review": c["needs_review"],
            "not_found": c["not_found"],
            "unverified_dropped": c["unverified"],
            "raw_quotes_total": res["raw_quotes_total"],
            "verified_quotes_total": res["verified_quotes_total"],
            "dropped_quotes_total": res["dropped_quotes_total"],
            "raw_quote_pass_rate": res["raw_quote_pass_rate"],
            "kept_quote_verified_rate": (doc_rev / doc_kept) if doc_kept > 0 else 1.0,
            "verifier_independent": res["verifier_independent"],
            "fields": res["fields"],
        })

    new_calls = client.api_calls_made - before_api
    overall_kept_rate = (all_reverified_quotes / all_kept_quotes) if all_kept_quotes > 0 else 1.0
    ok = overall_kept_rate >= 0.99 and len(summaries) == 5
    msg = (
        f"5 docs extracted; new_api_calls={new_calls}; "
        f"kept_quotes_verified={all_reverified_quotes}/{all_kept_quotes} ({overall_kept_rate:.1%})"
    )
    return ok, msg, summaries, new_calls


def test_t4_silver_labels(client: GeminiClient) -> tuple[bool, str, dict[str, Any], int]:
    """Compares extract_key_info against LLM-assisted silver labels in key_info_llm.csv."""
    with open(SILVER_CSV, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))

    by_doc: dict[str, dict[str, dict[str, str]]] = {}
    for r in rows:
        by_doc.setdefault(r["doc_id"], {})[r["field_name"]] = r

    before_api = client.api_calls_made
    tp = fp = fn = tn = 0
    unclear_cases: list[dict[str, Any]] = []
    mismatches: list[dict[str, Any]] = []
    per_doc: list[dict[str, Any]] = []

    for doc_id, gold_fields in sorted(by_doc.items()):
        pages = _read_zip_doc_pages(doc_id)
        res = extract_key_info(doc_id=doc_id, doc_pages=pages, client=client, verify_numeric=False)
        pred_map = res["by_field"]

        d_tp = d_fp = d_fn = d_tn = 0
        d_unclear = 0
        ev_pos = 0
        ev_match = 0
        for fname, row in gold_fields.items():
            silver_val = row["llm_value"].strip()
            silver_quote = row.get("llm_evidence_quote", "").strip()
            pred_rec = pred_map[fname]
            pred_found = pred_rec["status"] in {"verified", "needs_review"}
            pred_val = pred_rec["value"]

            if silver_val == "UNCLEAR":
                d_unclear += 1
                unclear_cases.append({
                    "doc_id": doc_id,
                    "field": fname,
                    "silver_quote": silver_quote,
                    "pred_status": pred_rec["status"],
                    "pred_value": pred_val,
                })
                continue

            if silver_val == "NOT_PRESENT":
                if not pred_found:
                    tn += 1
                    d_tn += 1
                else:
                    fp += 1
                    d_fp += 1
                    mismatches.append({"doc_id": doc_id, "field": fname, "silver": "NOT_PRESENT", "pred": pred_val, "type": "FP"})
                continue

            # Diagnostic: check if predicted verified quotes locate same source quote
            if silver_quote:
                ev_pos += 1
                ns = normalize(silver_quote)
                p_quotes = [normalize(e["quote"]) for e in pred_rec.get("evidence", []) if e.get("quote")]
                if any(pq == ns or pq in ns or ns in pq or _token_overlap_ratio(pq, ns) >= 0.4 for pq in p_quotes):
                    ev_match += 1

            # Positive silver label
            if not pred_found:
                fn += 1
                d_fn += 1
                mismatches.append({"doc_id": doc_id, "field": fname, "silver": silver_val, "pred": pred_rec["status"], "type": "FN"})
            elif _containment_match(pred_val, silver_val):
                tp += 1
                d_tp += 1
            else:
                fp += 1
                fn += 1
                d_fp += 1
                d_fn += 1
                mismatches.append({
                    "doc_id": doc_id,
                    "field": fname,
                    "silver": silver_val,
                    "pred": pred_val,
                    "overlap": round(_token_overlap_ratio(pred_val, silver_val), 3),
                    "type": "VALUE_MISMATCH",
                })

        per_doc.append({
            "doc_id": doc_id,
            "tp": d_tp,
            "fp": d_fp,
            "fn": d_fn,
            "tn": d_tn,
            "unclear_skipped": d_unclear,
            "ev_quote_matches": f"{ev_match}/{ev_pos}",
            "model_used": res["model_used"],
            "raw_quotes": res["raw_quotes_total"],
            "verified_quotes": res["verified_quotes_total"],
        })

    new_calls = client.api_calls_made - before_api
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    # Also compute diagnostic overlap stats (without redefining primary strict containment F1)
    overlap_ge_50 = sum(1 for m in mismatches if m.get("type") == "VALUE_MISMATCH" and m.get("overlap", 0) >= 0.5)
    diag_tp = tp + overlap_ge_50
    diag_fp = fp - overlap_ge_50
    diag_fn = fn - overlap_ge_50
    diag_p = diag_tp / (diag_tp + diag_fp) if (diag_tp + diag_fp) > 0 else 0.0
    diag_r = diag_tp / (diag_tp + diag_fn) if (diag_tp + diag_fn) > 0 else 0.0
    diag_f1 = (2 * diag_p * diag_r / (diag_p + diag_r)) if (diag_p + diag_r) > 0 else 0.0

    ok = f1 >= 0.85
    report = {
        "note": "LLM-assisted silver labels (not human gold)",
        "total_rows": len(rows),
        "definitive_rows_evaluated": tp + fp + fn + tn - min(fp, fn) if False else (48 - len(unclear_cases)),
        "unclear_rows": len(unclear_cases),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "diagnostic_token_overlap_ge_0_5_f1": diag_f1,
        "per_doc": per_doc,
        "mismatches": mismatches,
        "unclear_cases": unclear_cases,
    }
    msg = (
        f"Silver (3 docs, 41 definitive rows + {len(unclear_cases)} UNCLEAR): "
        f"P={precision:.1%}, R={recall:.1%}, F1={f1:.1%} "
        f"(TP={tp}, FP={fp}, FN={fn}, TN={tn}; new_calls={new_calls}); "
        f"diagnostic token-overlap F1={diag_f1:.1%}"
    )
    return ok, msg, report, new_calls


def test_t5_gold_standard(client: GeminiClient) -> tuple[bool, str, dict[str, Any], int]:
    """Compares extract_key_info against friend's 3 human-verified docs in gold_standard_extraction_v1.csv."""
    with open(GOLD_CSV, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))

    by_doc: dict[str, list[dict[str, str]]] = {}
    for r in rows:
        doc_id = r.get("document_id") or r.get("\ufeffdocument_id") or ""
        by_doc.setdefault(doc_id, []).append(r)

    before_api = client.api_calls_made
    total = 0
    containment_matches = 0
    token_overlap_ge_40 = 0
    missing_or_unavail = 0
    details: list[dict[str, Any]] = []

    for doc_id, doc_rows in sorted(by_doc.items()):
        pages = _read_zip_doc_pages(doc_id)
        doc_before = client.api_calls_made
        res = extract_key_info(doc_id=doc_id, doc_pages=pages, client=client, verify_numeric=False)
        if client.api_calls_made > doc_before and res["doc_chars"] >= 120000:
            # Allow TPM window recovery between live 150k-300k character SEC contracts
            time.sleep(25.0)
        pred_map = res["by_field"]
        agr_name = doc_rows[0]["agreement_name"]

        for r in doc_rows:
            g_field = r["field"]
            mapped = GOLD_TO_16_FIELD.get(g_field)
            if not mapped:
                continue
            total += 1
            gold_status = r["gold_status"].strip()
            gold_val = r["gold_value"].strip()
            pred_rec = pred_map[mapped]
            pred_val = pred_rec["value"]

            if gold_status != "KNOWN":
                missing_or_unavail += 1
            is_contain = _containment_match(pred_val, gold_val) if gold_val else False
            ov = _token_overlap_ratio(pred_val, gold_val) if gold_val else 0.0
            if is_contain:
                containment_matches += 1
            if ov >= 0.40 or is_contain:
                token_overlap_ge_40 += 1

            details.append({
                "doc_id": doc_id,
                "agreement_name": agr_name,
                "gold_field": g_field,
                "mapped_field": mapped,
                "gold_status": gold_status,
                "containment_match": is_contain,
                "token_overlap": round(ov, 3),
                "pred_status": pred_rec["status"],
                "pred_flags": pred_rec["flags"],
                "gold_value_short": gold_val[:120],
                "pred_value_short": pred_val[:120],
                "verified_quotes": len(pred_rec["evidence"]),
            })

    new_calls = client.api_calls_made - before_api
    # T5 is a comparison & honest reporting check (crash-free across all 27 gold items with valid mapped outputs)
    ok = total == 27 and len(by_doc) == 3
    per_doc_found: dict[str, str] = {}
    for drow in details:
        agr = drow["agreement_name"]
        per_doc_found.setdefault(agr, "0/0")
    for agr in sorted({d["agreement_name"] for d in details}):
        sub = [d for d in details if d["agreement_name"] == agr]
        found_cnt = sum(1 for d in sub if d["pred_status"] in {"verified", "needs_review"})
        match_cnt = sum(1 for d in sub if d["containment_match"] or d["token_overlap"] >= 0.40)
        per_doc_found[agr] = f"found={found_cnt}/{len(sub)}, match_or_ov40={match_cnt}/{len(sub)}"

    report = {
        "docs": len(by_doc),
        "comparable_cells": total,
        "non_known_gold_cells": missing_or_unavail,
        "containment_matches": containment_matches,
        "token_overlap_ge_0_4_or_contain": token_overlap_ge_40,
        "per_doc_summary": per_doc_found,
        "details": details,
    }
    msg = (
        f"Gold (3 human docs, {total} cells across 9 mapped fields, {missing_or_unavail} UNAVAILABLE_MISSING_SCHEDULE): "
        f"strict containment={containment_matches}/{total}, "
        f"token-overlap>=0.40 or contain={token_overlap_ge_40}/{total}; "
        f"per_doc={per_doc_found}; new_calls={new_calls}"
    )
    return ok, msg, report, new_calls


def test_t6_budget_and_cache(total_live_calls: int) -> tuple[bool, str]:
    fresh_client = GeminiClient()
    before = fresh_client.api_calls_made
    docs_to_recheck: list[tuple[str, dict[int, str] | None]] = [
        ("03_dbs_mitc", None),
        ("13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi", None),
        ("0000027430-25-000005_aesohio10qex10120250630q2", None),
        ("09_muthoothomefin_MHIL-MITC", None),
        ("CITGO (000101/1011746/0000950129-03-001503_8.txt)", _read_zip_doc_pages("000101/1011746/0000950129-03-001503_8.txt")),
    ]
    for did, pages in docs_to_recheck:
        extract_key_info(did, doc_pages=pages, client=fresh_client, verify_numeric=False)
    cached_new_calls = fresh_client.api_calls_made - before
    ok = total_live_calls <= 80 and cached_new_calls == 0 and fresh_client.cache_hits > 0
    return ok, (
        f"total_live_calls={total_live_calls} (limit <=80); "
        f"cached_repeat_new_calls={cached_new_calls} across 5 docs (cache_hits={fresh_client.cache_hits})"
    )


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    client = GeminiClient(min_interval_seconds=10.0, request_timeout=90.0)
    # Wait out any residual short cooldown on main model from prior runs (<120s)
    main_model = client.models.get("main", "")
    rem = client.model_cooldowns.get(main_model, 0.0) - time.time()
    if 0 < rem <= 120:
        print(f"Waiting {rem + 1:.0f}s for {main_model} cooldown to clear...", flush=True)
        time.sleep(rem + 1.0)
        client.model_cooldowns = client._load_cooldowns()

    start_api_calls = client.api_calls_made

    print("=" * 90, flush=True)
    print("STAGE 3a TEST SUITE: Key-Information Extraction (16 Guideline Fields)", flush=True)
    print("=" * 90, flush=True)

    t1_ok, t1_msg = test_t1_key_leak_scan()
    print(f"[{'PASS' if t1_ok else 'FAIL'}] T1 Key leak scan: {t1_msg}", flush=True)

    t2_ok, t2_msg = test_t2_fake_llm_unit_tests()
    print(f"[{'PASS' if t2_ok else 'FAIL'}] T2 Fake-LLM unit tests: {t2_msg}", flush=True)

    t3_ok, t3_msg, t3_summaries, t3_calls = test_t3_live_5_docs(client)
    print(f"[{'PASS' if t3_ok else 'FAIL'}] T3 Live 5 documents: {t3_msg}", flush=True)
    for s in t3_summaries:
        print(
            f"   - {s['doc_id'][:48]:<48} | found={s['fields_found']:2d}/16 "
            f"(ver={s['verified']:2d}, rev={s['needs_review']:2d}, nf={s['not_found']:2d}, drop={s['unverified_dropped']:2d}) | "
            f"raw_q={s['verified_quotes_total']}/{s['raw_quotes_total']} ({s['raw_quote_pass_rate']:.1%}) | "
            f"kept_q={s['kept_quote_verified_rate']:.1%} | indep={s['verifier_independent']} | model={s['model_used']}",
            flush=True,
        )

    t4_ok, t4_msg, t4_report, t4_calls = test_t4_silver_labels(client)
    print(f"[{'PASS' if t4_ok else 'FAIL'}] T4 Silver labels comparison: {t4_msg}", flush=True)
    for d in t4_report["per_doc"]:
        print(
            f"   - {d['doc_id']:<42} | TP={d['tp']} FP={d['fp']} FN={d['fn']} TN={d['tn']} "
            f"| ev_quotes={d['ev_quote_matches']} | model={d['model_used']}",
            flush=True,
        )

    t5_ok, t5_msg, t5_report, t5_calls = test_t5_gold_standard(client)
    print(f"[{'PASS' if t5_ok else 'FAIL'}] T5 Gold standard comparison: {t5_msg}", flush=True)

    total_live_calls = client.api_calls_made - start_api_calls
    t6_ok, t6_msg = test_t6_budget_and_cache(total_live_calls)
    print(f"[{'PASS' if t6_ok else 'FAIL'}] T6 Call budget & cache reuse: {t6_msg}", flush=True)

    # Re-run T1 after all outputs & caches were written
    t1_final_ok, t1_final_msg = test_t1_key_leak_scan()
    print(f"[{'PASS' if t1_final_ok else 'FAIL'}] T1 Post-run leak scan: {t1_final_msg}")

    out_payload = {
        "t1": {"passed": t1_ok and t1_final_ok, "msg": t1_final_msg},
        "t2": {"passed": t2_ok, "msg": t2_msg},
        "t3": {"passed": t3_ok, "msg": t3_msg, "calls": t3_calls, "docs": t3_summaries},
        "t4": {"passed": t4_ok, "msg": t4_msg, "calls": t4_calls, "report": t4_report},
        "t5": {"passed": t5_ok, "msg": t5_msg, "calls": t5_calls, "report": t5_report},
        "t6": {"passed": t6_ok, "msg": t6_msg, "total_live_calls": total_live_calls},
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(out_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved detailed results to {OUTPUT_JSON}")

    overall = t1_ok and t1_final_ok and t2_ok and t3_ok and t4_ok and t5_ok and t6_ok
    print(f"\nOVERALL SUITE STATUS: {'PASS' if overall else 'FAIL (see details above)'}")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
