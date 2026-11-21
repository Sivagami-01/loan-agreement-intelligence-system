"""scripts/test_3a_fix2.py

Verification test suite for Stage 3a-fix2 (quote repair, deferral/absence handling,
Metric A with unchanged rules, and Metric B post-hoc verifier judge calibration).

Tests:
  T1: API key leak scan (0 leaks).
  T2: Fake-LLM unit tests (0 API calls): quote with "..." repaired to exact source span,
      fabricated quote dropped, quote with changed number dropped, "defined in the Note"
      gives deferred_to_other_document, vague "term of the Note" date -> not_found,
      plus judge calibration (>= 85% gate, graceful stop on quota exhaustion).
  T3: Re-run extraction on the 5 benchmark documents; kept-quote verified rate == 100%,
      dropped quotes < 4 (previous Stage 3a count).
  T4: Check the 6 rows marked who_is_right=label in extract_3a_mismatch_review_filled.csv
      (rows 7, 8, 16, 20, 32, 54).
  T5: Report Metric A (strict & lenient, unchanged match_values.py rules) and Metric B
      ("post-hoc, judge-based, not pre-registered", only if judge >= 85% calibrated)
      separately for silver and human-verified gold.
  T6: Call budget <= 80 live calls total and 0 new live calls on cached repeat.
"""

from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.eval_3a_matches import (
    GOLD_CSV,
    SILVER_CSV,
    _read_zip_doc_pages,
    evaluate_gold,
    evaluate_silver,
)
from src.extract.extract_fields import extract_key_info, load_extract_config
from src.extract.judge_eval import METRIC_B_LABEL, VerifierQuotaExhausted, calibrate_and_score_metric_b
from src.llm.gemini_client import GeminiClient, get_api_key
from src.qa.doc_loader import load_document
from src.qa.verify_quotes import verify_evidence

LOG_FILE = ROOT / "data" / "processed" / "llm_log.csv"
GEMINI_CACHE_DIR = ROOT / "data" / "processed" / "cache" / "gemini"
JUDGE_CACHE_DIR = ROOT / "data" / "processed" / "cache" / "judge"
FILLED_REVIEW_CSV = ROOT / "data" / "processed" / "extract_3a_mismatch_review_filled.csv"
OUT_RESULTS_JSON = ROOT / "data" / "processed" / "extract_3a_fix2_results.json"

BENCHMARK_DOCS: list[tuple[str, dict[int, str] | None]] = [
    ("03_dbs_mitc", None),
    ("13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi", None),
    ("0000027430-25-000005_aesohio10qex10120250630q2", None),
    ("09_muthoothomefin_MHIL-MITC", None),
    ("CITGO (000101/1011746/0000950129-03-001503_8.txt)", _read_zip_doc_pages("000101/1011746/0000950129-03-001503_8.txt")),
]


def test_t1_key_leaks() -> tuple[bool, str]:
    api_key = get_api_key()
    if not api_key or len(api_key) < 10:
        return False, "GEMINI_API_KEY missing or invalid."

    files_to_scan: list[Path] = [
        ROOT / "config" / "extract.yaml",
        ROOT / "src" / "extract" / "extract_fields.py",
        ROOT / "src" / "extract" / "judge_eval.py",
        ROOT / "scripts" / "test_3a_fix2.py",
        ROOT / "docs" / "WORK_REPORT.md",
        LOG_FILE,
        OUT_RESULTS_JSON,
    ]
    if GEMINI_CACHE_DIR.is_dir():
        files_to_scan.extend(GEMINI_CACHE_DIR.glob("*.json"))
    if JUDGE_CACHE_DIR.is_dir():
        files_to_scan.extend(JUDGE_CACHE_DIR.glob("*.json"))

    leaks = 0
    scanned = 0
    for f in files_to_scan:
        if f.is_file():
            scanned += 1
            if api_key in f.read_text(encoding="utf-8", errors="ignore"):
                leaks += 1
    return leaks == 0, f"Scanned {scanned} files; leaks={leaks}"


def test_t2_unit_tests() -> tuple[bool, str]:
    cfg = load_extract_config()
    fake_pages = {
        1: (
            "CREDIT AGREEMENT dated May 10, 2025 between Acme National Bank and Beta Corp.\n"
            "The Revolving Loan shall bear interest at the rate as defined in the Note.\n"
            'Maturity: "Term" shall mean the term of the Note.\n'
            "Repayment: The Borrower shall pay all unpaid principal and accrued interest on May 10, 2030.\n"
        ),
        2: (
            "Section 7.01 Events of Default: (a) Failure to pay any principal within 10 days after due; "
            "or (b) any insolvency event involving Beta Corp.\n"
            "Security: First priority security interest in all equipment and inventory of Beta Corp.\n"
            "Fees: Facility fee of $500.00 due at closing.\n"
        ),
    }

    def fake_llm(prompt: str) -> tuple[str, str]:
        payload = {
            "fields": [
                {
                    "field": "document_title",
                    "found": True,
                    "value": "Credit Agreement",
                    "evidence": [{"quote": "CREDIT AGREEMENT", "page": 1}],
                },
                {
                    "field": "interest_rate",
                    "found": True,
                    "value": "as defined in the Note",
                    "evidence": [{"quote": "at the rate as defined in the Note.", "page": 1}],
                },
                {
                    "field": "maturity_termination_date",
                    "found": True,
                    "value": "Term of the Note",
                    "evidence": [{"quote": '"Term" shall mean the term of the Note.', "page": 1}],
                },
                {
                    "field": "repayment_terms",
                    "found": True,
                    "value": "Repay unpaid principal and interest on May 10, 2030",
                    # Neighbor-page test + ellipsis "..." bridging test
                    "evidence": [{"quote": "The Borrower shall pay ... accrued interest on May 10, 2030.", "page": 2}],
                },
                {
                    "field": "borrowers",
                    "found": True,
                    "value": "Fake Entity LLC",
                    # Fabricated quote must still be dropped
                    "evidence": [{"quote": "COMPLETELY FABRICATED QUOTE NOT ON ANY PAGE", "page": 1}],
                },
                {
                    "field": "fees",
                    "found": True,
                    "value": "Facility fee of $999.00",
                    # Changed number ($999.00 vs $500.00) must still be dropped even with high string similarity
                    "evidence": [{"quote": "Facility fee of $999.00 due at closing.", "page": 2}],
                },
                {
                    "field": "events_of_default",
                    "found": True,
                    "value": "Failure to pay within 10 days or insolvency",
                    # Minor ellipsis with preserved number 10 must repair cleanly to exact source substring
                    "evidence": [{"quote": "(a) Failure to pay any principal within 10 days ... involving Beta Corp.", "page": 2}],
                },
            ]
        }
        return json.dumps(payload), "fake-main-model"

    res = extract_key_info(
        doc_id="unit_fix2",
        doc_pages=fake_pages,
        config=cfg,
        verify_numeric=False,
        llm_fn=fake_llm,
    )
    bf = res["by_field"]
    rep_ev = bf["repayment_terms"]["evidence"]
    eod_ev = bf["events_of_default"]["evidence"]

    checks: list[tuple[str, bool, str]] = [
        ("ellipsis_repaired_repay", bf["repayment_terms"]["status"] == "verified" and bf["repayment_terms"]["quote_repaired"] is True, f"rec={bf['repayment_terms']}"),
        ("repaired_exact_substr_repay", len(rep_ev) == 1 and rep_ev[0]["quote"] in fake_pages[1] and len(rep_ev[0]["quote"]) <= 400 and rep_ev[0]["page"] == 1, f"ev={rep_ev}"),
        ("ellipsis_repaired_eod", bf["events_of_default"]["status"] == "verified" and bf["events_of_default"]["quote_repaired"] is True, f"rec={bf['events_of_default']}"),
        ("repaired_exact_substr_eod", len(eod_ev) == 1 and eod_ev[0]["quote"] in fake_pages[2], f"ev={eod_ev}"),
        ("fabricated_dropped", bf["borrowers"]["status"] == "unverified" and bf["borrowers"]["value"] == "", f"status={bf['borrowers']['status']}"),
        ("changed_number_quote_dropped", bf["fees"]["status"] == "unverified" and bf["fees"]["value"] == "", f"status={bf['fees']['status']}"),
        ("defined_in_note_deferred", bf["interest_rate"]["status"] == "deferred_to_other_document" and bf["interest_rate"]["value"] == "" and bf["interest_rate"]["defers_to"].lower() == "note" and len(bf["interest_rate"]["evidence"]) == 1, f"rec={bf['interest_rate']}"),
        ("term_of_note_not_found", bf["maturity_termination_date"]["status"] == "not_found", f"status={bf['maturity_termination_date']['status']}"),
    ]

    # Also unit-test Judge calibration mapping, >= 85% gate, and graceful 429 stop (0 API)
    fake_review = [
        {"field": "f1", "predicted_value": "A", "reference_value": "A2", "who_is_right": "both ok"},
        {"field": "f2", "predicted_value": "B", "reference_value": "B2", "who_is_right": "label"},
        {"field": "f3", "predicted_value": "C", "reference_value": "C2", "who_is_right": "system"},
    ]
    fake_pos = [
        {"dataset": "silver", "field": "f1", "predicted": "A", "reference": "A2"},
        {"dataset": "gold", "field": "f2", "predicted": "B", "reference": "B2"},
    ]

    def fake_judge_ok(prompt: str) -> str:
        if "A2" in prompt:
            return json.dumps([
                {"idx": 0, "verdict": "partial", "reason": "ok"},
                {"idx": 1, "verdict": "different", "reason": "lbl"},
                {"idx": 2, "verdict": "equivalent", "reason": "sys"},
            ])
        return json.dumps([
            {"idx": 0, "verdict": "equivalent", "reason": "same"},
            {"idx": 1, "verdict": "different", "reason": "miss"},
        ])

    j_ok = calibrate_and_score_metric_b(
        review_rows=fake_review,
        post_positive_rows=fake_pos,
        extractor_models={"fake-main-model"},
        llm_batch_fn=fake_judge_ok,
    )
    checks.append(("judge_cal_100_trusted", j_ok["calibration"]["trusted"] is True and j_ok["metric_b_reported"] is True, f"cal={j_ok['calibration']}"))

    def fake_judge_low(prompt: str) -> str:
        return json.dumps([
            {"idx": 0, "verdict": "different", "reason": "wrong"},
            {"idx": 1, "verdict": "equivalent", "reason": "wrong"},
            {"idx": 2, "verdict": "different", "reason": "wrong"},
        ])

    j_low = calibrate_and_score_metric_b(
        review_rows=fake_review,
        post_positive_rows=fake_pos,
        extractor_models={"fake-main-model"},
        llm_batch_fn=fake_judge_low,
    )
    checks.append(("judge_low_agreement_untrusted", j_low["calibration"]["trusted"] is False and j_low["metric_b_reported"] is False, f"trusted={j_low['calibration']['trusted']}"))

    def fake_judge_quota(prompt: str) -> str:
        raise VerifierQuotaExhausted("HTTP 429 quota exhausted")

    j_quota = calibrate_and_score_metric_b(
        review_rows=fake_review,
        post_positive_rows=fake_pos,
        extractor_models={"fake-main-model"},
        llm_batch_fn=fake_judge_quota,
    )
    checks.append(("judge_quota_graceful_stop", j_quota["calibration"]["stopped_gracefully"] is True and j_quota["metric_b_reported"] is False, f"reason={j_quota['reason']}"))

    failures = [f"{name} ({detail})" for name, passed, detail in checks if not passed]
    ok = len(failures) == 0
    return ok, f"{len(checks) - len(failures)}/{len(checks)} unit checks passed" + (f"; FAILURES: {failures}" if failures else "")


def run_benchmark_docs(client: GeminiClient) -> tuple[bool, str, list[dict[str, Any]], int]:
    before = client.api_calls_made
    docs_summary: list[dict[str, Any]] = []
    kept_total = 0
    reverified_total = 0
    dropped_total = 0
    repaired_total = 0

    for doc_id, custom_pages in BENCHMARK_DOCS:
        res = extract_key_info(doc_id=doc_id, doc_pages=custom_pages, client=client, verify_numeric=False)
        pages_for_check = custom_pages if custom_pages is not None else load_document(doc_id)[1]

        doc_kept = 0
        doc_rev = 0
        for row in res["fields"]:
            if row["evidence"]:
                doc_kept += len(row["evidence"])
                vev, _ = verify_evidence(pages_for_check, row["evidence"])
                doc_rev += len(vev)

        kept_total += doc_kept
        reverified_total += doc_rev
        dropped_total += res["dropped_quotes_total"]
        repaired_total += res["quotes_repaired_total"]

        c = res["counts"]
        docs_summary.append({
            "doc_id": doc_id,
            "doc_chars": res["doc_chars"],
            "num_pages": res["num_pages"],
            "retrieval_used": res["retrieval_used"],
            "model_used": res["model_used"],
            "verified": c["verified"],
            "needs_review": c["needs_review"],
            "deferred_to_other_document": c["deferred_to_other_document"],
            "not_found": c["not_found"],
            "unverified": c["unverified"],
            "raw_quotes_total": res["raw_quotes_total"],
            "verified_quotes_total": res["verified_quotes_total"],
            "quotes_repaired_total": res["quotes_repaired_total"],
            "dropped_quotes_total": res["dropped_quotes_total"],
            "kept_quote_verified_rate": (doc_rev / doc_kept) if doc_kept > 0 else 1.0,
        })

    new_calls = client.api_calls_made - before
    kept_rate = (reverified_total / kept_total) if kept_total > 0 else 1.0
    ok = kept_rate == 1.0 and dropped_total < 4
    msg = (
        f"5 docs; kept_quotes_verified={reverified_total}/{kept_total} ({kept_rate:.1%}); "
        f"dropped_quotes={dropped_total} (prev 4; repaired={repaired_total}); new_calls={new_calls}"
    )
    return ok, msg, docs_summary, new_calls


def extract_eval_docs(client: GeminiClient) -> tuple[dict[str, dict[str, Any]], int, set[str]]:
    with open(SILVER_CSV, encoding="utf-8-sig", newline="") as fh:
        silver_docs = sorted({r["doc_id"].strip() for r in csv.DictReader(fh)})
    with open(GOLD_CSV, encoding="utf-8-sig", newline="") as fh:
        gold_docs = sorted({(r.get("document_id") or r.get("\ufeffdocument_id") or "").strip() for r in csv.DictReader(fh)})

    all_docs = sorted(set(silver_docs + gold_docs))
    before = client.api_calls_made
    out: dict[str, dict[str, Any]] = {}
    extractor_models: set[str] = set()

    for did in all_docs:
        doc_before = client.api_calls_made
        pages = _read_zip_doc_pages(did)
        res = extract_key_info(doc_id=did, doc_pages=pages, client=client, verify_numeric=False)
        out[did] = res
        for m in str(res.get("model_used", "")).split(","):
            if m.strip():
                extractor_models.add(m.strip())
        if client.api_calls_made > doc_before and res["doc_chars"] >= 120000:
            # Protect 250k TPM limit between uncached large SEC agreements
            time.sleep(25.0)

    return out, client.api_calls_made - before, extractor_models


def check_t4_six_fixed_rows(extractions: dict[str, dict[str, Any]]) -> tuple[bool, str, list[dict[str, Any]]]:
    """Evaluates the 6 rows marked who_is_right='label' in extract_3a_mismatch_review_filled.csv."""
    targets = [
        {
            "row": 7,
            "doc_id": "000010/104897/0000950123-11-030926_2.txt",
            "field": "late_payment_or_default_interest",
            "expect": "not_found_or_deferred",
        },
        {
            "row": 8,
            "doc_id": "000010/104897/0000950123-11-030926_2.txt",
            "field": "prepayment_terms",
            "expect": "not_found_or_deferred",
        },
        {
            "row": 16,
            "doc_id": "000081/810113/0000950116-04-002411_4.txt",
            "field": "maturity_termination_date",
            "expect": "not_found_or_deferred",
        },
        {
            "row": 20,
            "doc_id": "000081/810113/0000950116-04-002411_4.txt",
            "field": "events_of_default",
            "expect": "verified_with_quote",
        },
        {
            "row": 32,
            "doc_id": "000081/810113/0000950116-04-002411_4.txt",
            "field": "collateral_security",
            "expect": "verified_with_quote",
        },
        {
            "row": 54,
            "doc_id": "000004/40211/0000950123-11-048775_2.txt",
            "field": "events_of_default",
            "expect": "verified_with_quote",
        },
    ]

    details: list[dict[str, Any]] = []
    passed_count = 0
    for t in targets:
        rec = extractions[t["doc_id"]]["by_field"][t["field"]]
        st = rec["status"]
        has_ev = len(rec.get("evidence", [])) > 0
        if t["expect"] == "not_found_or_deferred":
            fixed_ok = (
                (st == "deferred_to_other_document" and rec.get("value", "") == "" and has_ev)
                or (st == "not_found" and rec.get("value") == "Not found in this document")
            )
        else:
            fixed_ok = st in {"verified", "needs_review"} and has_ev and bool(rec.get("value"))

        if fixed_ok:
            passed_count += 1
        details.append({
            "row": t["row"],
            "doc_id": t["doc_id"],
            "field": t["field"],
            "expect": t["expect"],
            "new_status": st,
            "defers_to": rec.get("defers_to", ""),
            "quote_repaired": rec.get("quote_repaired", False),
            "new_value": rec.get("value", ""),
            "quotes_kept": len(rec.get("evidence", [])),
            "fixed_ok": fixed_ok,
        })

    ok = passed_count == len(targets)
    msg = f"{passed_count}/{len(targets)} target label-right rows resolved correctly"
    return ok, msg, details


def build_post_positive_rows(extractions: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    with open(SILVER_CSV, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            ref = r["llm_value"].strip()
            if ref in {"NOT_PRESENT", "UNCLEAR"}:
                continue
            did = r["doc_id"].strip()
            fname = r["field_name"].strip()
            rec = extractions[did]["by_field"][fname]
            pred = rec["value"] if rec["status"] in {"verified", "needs_review"} else f"[{rec['status']}]"
            items.append({"dataset": "silver", "doc": did, "field": fname, "predicted": pred, "reference": ref})

    from scripts.eval_3a_matches import GOLD_TO_16_FIELD
    with open(GOLD_CSV, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            did = (r.get("document_id") or r.get("\ufeffdocument_id") or "").strip()
            gf = r["field"].strip()
            mapped = GOLD_TO_16_FIELD.get(gf)
            if not mapped:
                continue
            ref = r["gold_value"].strip() or f"[{r['gold_status'].strip()}]"
            rec = extractions[did]["by_field"][mapped]
            pred = rec["value"] if rec["status"] in {"verified", "needs_review"} else f"[{rec['status']}]"
            items.append({"dataset": "gold", "doc": did, "field": mapped, "predicted": pred, "reference": ref})

    return items


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("=" * 92, flush=True)
    print("STAGE 3a-fix2 TEST SUITE: Quote Repair, Deferral/Absence & Dual Evaluation", flush=True)
    print("=" * 92, flush=True)

    t1_ok, t1_msg = test_t1_key_leaks()
    print(f"[{'PASS' if t1_ok else 'FAIL'}] T1 Key leak scan: {t1_msg}", flush=True)

    t2_ok, t2_msg = test_t2_unit_tests()
    print(f"[{'PASS' if t2_ok else 'FAIL'}] T2 Unit tests (0 API calls): {t2_msg}", flush=True)

    client = GeminiClient(min_interval_seconds=7.0, request_timeout=90.0)
    t3_ok, t3_msg, t3_docs, t3_calls = run_benchmark_docs(client)
    print(f"[{'PASS' if t3_ok else 'FAIL'}] T3 5 benchmark docs re-run: {t3_msg}", flush=True)
    for d in t3_docs:
        print(
            f"   - {d['doc_id'][:46]:<46} | ver={d['verified']:2d} rev={d['needs_review']} "
            f"def={d['deferred_to_other_document']} nf={d['not_found']:2d} unv={d['unverified']} | "
            f"raw_q={d['verified_quotes_total']}/{d['raw_quotes_total']} rep={d['quotes_repaired_total']} "
            f"drop={d['dropped_quotes_total']} kept={d['kept_quote_verified_rate']:.0%} | {d['model_used']}",
            flush=True,
        )

    extractions, eval_calls, extractor_models = extract_eval_docs(client)

    t4_ok, t4_msg, t4_details = check_t4_six_fixed_rows(extractions)
    print(f"[{'PASS' if t4_ok else 'FAIL'}] T4 6 prior system-wrong rows: {t4_msg}", flush=True)
    for item in t4_details:
        print(
            f"   - row {item['row']:2d} {item['field']:<32} | ok={item['fixed_ok']} | "
            f"status={item['new_status']} (defers={item['defers_to'] or '-'}, rep={item['quote_repaired']}, q={item['quotes_kept']}) | "
            f"val={item['new_value'][:75]!r}",
            flush=True,
        )

    # Metric A: unchanged pre-registered rules on re-run outputs
    silver_a, _ = evaluate_silver(extractions)
    gold_a, _ = evaluate_gold(extractions)

    # Metric B: post-hoc, judge-based, not pre-registered
    with open(FILLED_REVIEW_CSV, encoding="utf-8-sig", newline="") as fh:
        review_rows = list(csv.DictReader(fh))
    post_pos = build_post_positive_rows(extractions)
    metric_b = calibrate_and_score_metric_b(
        review_rows=review_rows,
        post_positive_rows=post_pos,
        extractor_models=extractor_models,
        batch_size=6,
    )

    t5_ok = silver_a["total_rows"] == 48 and gold_a["total_cells"] == 27
    print(f"[{'PASS' if t5_ok else 'FAIL'}] T5 Metric A (pre-registered rules, unchanged) & Metric B ({METRIC_B_LABEL}):", flush=True)
    sc = silver_a["counts"]
    print(
        f"   Metric A Silver (3 docs, 41 def + 7 UNCLEAR; counts: exact={sc['exact']}, norm={sc['normalized']}, "
        f"partial={sc['partial']}, no={sc['no']}, TN={silver_a['tn']}):\n"
        f"     STRICT (exact+norm)     : P={silver_a['strict']['precision']:.1%}, R={silver_a['strict']['recall']:.1%}, F1={silver_a['strict']['f1']:.1%}\n"
        f"     LENIENT (+partial)      : P={silver_a['lenient']['precision']:.1%}, R={silver_a['lenient']['recall']:.1%}, F1={silver_a['lenient']['f1']:.1%}",
        flush=True,
    )
    gc = gold_a["counts"]
    print(
        f"   Metric A Human Gold (3 docs, 27 cells; counts: exact={gc['exact']}, norm={gc['normalized']}, "
        f"partial={gc['partial']}, no={gc['no']}):\n"
        f"     STRICT (exact+norm)     : {gold_a['strict_matches']}/27 ({gold_a['strict_rate']:.1%})\n"
        f"     LENIENT (+partial)      : {gold_a['lenient_matches']}/27 ({gold_a['lenient_rate']:.1%})",
        flush=True,
    )
    for agr, gd in sorted(gold_a["per_doc"].items()):
        print(
            f"       {agr:<13}: strict={gd['exact']+gd['normalized']}/{gd['total']} ({gd['strict_rate']:.1%}), "
            f"lenient={gd['exact']+gd['normalized']+gd['partial']}/{gd['total']} ({gd['lenient_rate']:.1%})",
            flush=True,
        )

    cal = metric_b["calibration"]
    print(
        f"   Metric B [{METRIC_B_LABEL}]: calibrated={cal['completed']}/{cal['total_verdicts']}, "
        f"agreed={cal['agreed']}, agreement={cal['agreement']:.1%}, trusted={cal['trusted']}, "
        f"reported={metric_b['metric_b_reported']}",
        flush=True,
    )
    if metric_b["metric_b_reported"]:
        for ds in ("silver", "gold"):
            bd = metric_b["by_dataset"][ds]
            print(
                f"     Metric B {ds:<6}: judged={bd['judged']}/{bd['total']} counts={bd['counts']} | "
                f"equiv={bd['strict_equivalent_rate']:.1%}, equiv+partial={bd['lenient_equiv_or_partial_rate']:.1%}",
                flush=True,
            )
    else:
        print(f"     Metric B omitted: {metric_b['reason']}", flush=True)

    # T6: Call budget <= 80 and 0 new live calls on cached repeat
    total_live_calls = client.api_calls_made + metric_b["new_judge_calls"]
    repeat_client = GeminiClient()
    rep_before = repeat_client.api_calls_made
    for did, custom_pages in BENCHMARK_DOCS:
        extract_key_info(doc_id=did, doc_pages=custom_pages, client=repeat_client, verify_numeric=False)
    repeat_new_calls = repeat_client.api_calls_made - rep_before

    t6_ok = total_live_calls <= 80 and repeat_new_calls == 0 and repeat_client.cache_hits > 0
    print(
        f"[{'PASS' if t6_ok else 'FAIL'}] T6 Call budget & cache reuse: "
        f"total_live_calls={total_live_calls} (extract_t3={t3_calls}, extract_eval={eval_calls}, judge={metric_b['new_judge_calls']}; limit <=80); "
        f"cached_repeat_new_calls={repeat_new_calls} (cache_hits={repeat_client.cache_hits})",
        flush=True,
    )

    t1_post_ok, t1_post_msg = test_t1_key_leaks()
    print(f"[{'PASS' if t1_post_ok else 'FAIL'}] T1 Post-run leak scan: {t1_post_msg}", flush=True)

    out_payload = {
        "t1": {"passed": t1_ok and t1_post_ok, "msg": t1_post_msg},
        "t2": {"passed": t2_ok, "msg": t2_msg},
        "t3": {"passed": t3_ok, "msg": t3_msg, "calls": t3_calls, "docs": t3_docs},
        "t4": {"passed": t4_ok, "msg": t4_msg, "details": t4_details},
        "t5": {"passed": t5_ok, "metric_a_silver": silver_a, "metric_a_gold": gold_a, "metric_b": metric_b},
        "t6": {"passed": t6_ok, "total_live_calls": total_live_calls, "repeat_new_calls": repeat_new_calls},
    }
    OUT_RESULTS_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_RESULTS_JSON.write_text(json.dumps(out_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    overall = t1_ok and t1_post_ok and t2_ok and t3_ok and t4_ok and t5_ok and t6_ok
    print(f"\nOVERALL STAGE 3a-fix2 SUITE: {'PASS' if overall else 'FAIL'}", flush=True)
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
