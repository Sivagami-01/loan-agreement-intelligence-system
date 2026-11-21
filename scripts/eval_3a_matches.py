"""scripts/eval_3a_matches.py

Stage 3a-fix: Re-score cached Stage 3a extraction outputs using the fixed,
transparent matcher src/extract/match_values.py against:
  (a) LLM-assisted silver labels (data/processed/labels/llm_assisted/key_info_llm.csv)
  (b) Human-verified gold standard (data/friend/04_annotated_data/gold_standard_extraction_v1.csv)

Reports strict (exact + normalized) and lenient (exact + normalized + partial)
scores separately, writes ALL non-matches to data/processed/extract_3a_mismatch_review.csv,
and saves detailed evaluation JSON to data/processed/extract_3a_fix_results.json.
"""

from __future__ import annotations

import csv
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.extract.extract_fields import extract_key_info
from src.extract.match_values import values_match
from src.llm.gemini_client import GeminiClient

RESULTS_3A_JSON = ROOT / "data" / "processed" / "extract_3a_results.json"
SNAPSHOT_JSON = ROOT / "data" / "processed" / "extract_3a_eval_snapshot.json"
SILVER_CSV = ROOT / "data" / "processed" / "labels" / "llm_assisted" / "key_info_llm.csv"
GOLD_CSV = ROOT / "data" / "friend" / "04_annotated_data" / "gold_standard_extraction_v1.csv"
FRIEND_ZIP = ROOT / "data" / "friend" / "01_loan_agreements" / "publicly_filed_contracts.zip"
REVIEW_CSV = ROOT / "data" / "processed" / "extract_3a_mismatch_review.csv"
FIX_RESULTS_JSON = ROOT / "data" / "processed" / "extract_3a_fix_results.json"

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
            p_num = int(explicit_num) if explicit_num else (cur_page + 1)
            cur_page = p_num if explicit_num else p_num
            pages[p_num] = (pages[p_num] + "\n" + body) if p_num in pages else body
    else:
        pages[1] = raw_text
    return pages


def _read_zip_doc_pages(member_path: str) -> dict[int, str]:
    with zipfile.ZipFile(FRIEND_ZIP, "r") as zf:
        raw = zf.read(member_path).decode("utf-8", errors="ignore")
    return _split_edgar_pages(raw)


def _format_evidence_quotes(evidence: list[dict[str, Any]]) -> str:
    quotes = [f"[p.{e.get('page')}] {e.get('quote', '').strip()}" for e in evidence if e.get("quote")]
    return " | ".join(quotes)


def load_cached_extractions(
    doc_ids: list[str],
    client: GeminiClient | None = None,
    use_snapshot: bool = True,
) -> tuple[dict[str, dict[str, Any]], int]:
    """Loads full 16-field extraction dicts for each doc_id using cached LLM responses (0 new calls if cached)."""
    snapshot: dict[str, Any] = {}
    if use_snapshot and SNAPSHOT_JSON.is_file():
        try:
            snapshot = json.loads(SNAPSHOT_JSON.read_text(encoding="utf-8"))
        except Exception:
            snapshot = {}

    if client is None:
        client = GeminiClient(min_interval_seconds=8.0, request_timeout=90.0)

    before_calls = client.api_calls_made
    out: dict[str, dict[str, Any]] = {}
    updated_snapshot = False

    for did in doc_ids:
        if use_snapshot and did in snapshot:
            out[did] = snapshot[did]
            continue
        pages = _read_zip_doc_pages(did)
        res = extract_key_info(doc_id=did, doc_pages=pages, client=client, verify_numeric=False)
        out[did] = res
        snapshot[did] = res
        updated_snapshot = True

    if updated_snapshot:
        SNAPSHOT_JSON.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT_JSON.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")

    new_calls = client.api_calls_made - before_calls
    return out, new_calls


def _prf1(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2.0 * p * r / (p + r)) if (p + r) > 0 else 0.0
    return p, r, f1


def evaluate_silver(extractions: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    with open(SILVER_CSV, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))

    counts = {"exact": 0, "normalized": 0, "partial": 0, "no": 0}
    strict_tp = strict_fp = strict_fn = 0
    lenient_tp = lenient_fp = lenient_fn = 0
    tn = unclear_rows = 0
    per_doc: dict[str, dict[str, Any]] = {}
    non_matches: list[dict[str, Any]] = []

    for r in rows:
        did = r["doc_id"].strip()
        fname = r["field_name"].strip()
        ref_val = r["llm_value"].strip()
        ref_quote = r.get("llm_evidence_quote", "").strip()

        dstat = per_doc.setdefault(did, {
            "exact": 0, "normalized": 0, "partial": 0, "no": 0,
            "tn": 0, "fp": 0, "fn": 0, "unclear": 0,
        })

        pred_rec = extractions[did]["by_field"][fname]
        pred_status = pred_rec["status"]
        pred_found = pred_status in {"verified", "needs_review"}
        pred_val = pred_rec["value"] if pred_found else (
            "Not found in this document" if pred_status == "not_found" else "[unverified/dropped]"
        )
        pred_quote = _format_evidence_quotes(pred_rec.get("evidence", []))

        if ref_val == "UNCLEAR":
            unclear_rows += 1
            dstat["unclear"] += 1
            non_matches.append({
                "dataset": "silver (LLM-assisted)",
                "doc": did,
                "field": fname,
                "predicted_value": pred_val,
                "reference_value": "UNCLEAR",
                "predicted_quote": pred_quote,
                "reference_quote": ref_quote,
                "rule_result": "unclear_reference",
                "rule_reason": "silver label marked UNCLEAR (deferred to unattached Note)",
                "who_is_right": "",
            })
            continue

        if ref_val == "NOT_PRESENT":
            if not pred_found:
                tn += 1
                dstat["tn"] += 1
            else:
                strict_fp += 1
                lenient_fp += 1
                dstat["fp"] += 1
                non_matches.append({
                    "dataset": "silver (LLM-assisted)",
                    "doc": did,
                    "field": fname,
                    "predicted_value": pred_val,
                    "reference_value": "NOT_PRESENT",
                    "predicted_quote": pred_quote,
                    "reference_quote": ref_quote,
                    "rule_result": "no (fp_over_not_present)",
                    "rule_reason": "reference is NOT_PRESENT but system extracted a value",
                    "who_is_right": "",
                })
            continue

        # Positive silver field
        if not pred_found:
            counts["no"] += 1
            dstat["no"] += 1
            dstat["fn"] += 1
            strict_fn += 1
            lenient_fn += 1
            non_matches.append({
                "dataset": "silver (LLM-assisted)",
                "doc": did,
                "field": fname,
                "predicted_value": pred_val,
                "reference_value": ref_val,
                "predicted_quote": pred_quote,
                "reference_quote": ref_quote,
                "rule_result": f"no (system_{pred_status})",
                "rule_reason": f"system status={pred_status}; flags={pred_rec.get('flags', [])}",
                "who_is_right": "",
            })
            continue

        res = values_match(fname, pred_val, ref_val)
        m = res["match"]
        counts[m] += 1
        dstat[m] += 1

        if m in {"exact", "normalized"}:
            strict_tp += 1
            lenient_tp += 1
        elif m == "partial":
            strict_fp += 1
            strict_fn += 1
            lenient_tp += 1
            non_matches.append({
                "dataset": "silver (LLM-assisted)",
                "doc": did,
                "field": fname,
                "predicted_value": pred_val,
                "reference_value": ref_val,
                "predicted_quote": pred_quote,
                "reference_quote": ref_quote,
                "rule_result": "partial",
                "rule_reason": res["reason"],
                "who_is_right": "",
            })
        else:
            strict_fp += 1
            strict_fn += 1
            lenient_fp += 1
            lenient_fn += 1
            non_matches.append({
                "dataset": "silver (LLM-assisted)",
                "doc": did,
                "field": fname,
                "predicted_value": pred_val,
                "reference_value": ref_val,
                "predicted_quote": pred_quote,
                "reference_quote": ref_quote,
                "rule_result": "no",
                "rule_reason": res["reason"],
                "who_is_right": "",
            })

    sp, sr, sf1 = _prf1(strict_tp, strict_fp, strict_fn)
    lp, lr, lf1 = _prf1(lenient_tp, lenient_fp, lenient_fn)

    summary = {
        "disclaimer": "LLM-assisted silver labels (not independent human gold)",
        "total_rows": len(rows),
        "definitive_rows": len(rows) - unclear_rows,
        "positive_rows": sum(counts.values()),
        "negative_not_present_rows": tn + sum(d["fp"] for d in per_doc.values()),
        "unclear_rows": unclear_rows,
        "counts": counts,
        "tn": tn,
        "strict": {
            "tp": strict_tp,
            "fp": strict_fp,
            "fn": strict_fn,
            "precision": sp,
            "recall": sr,
            "f1": sf1,
        },
        "lenient": {
            "tp": lenient_tp,
            "fp": lenient_fp,
            "fn": lenient_fn,
            "precision": lp,
            "recall": lr,
            "f1": lf1,
        },
        "per_doc": per_doc,
    }
    return summary, non_matches


def evaluate_gold(extractions: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    with open(GOLD_CSV, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))

    counts = {"exact": 0, "normalized": 0, "partial": 0, "no": 0}
    per_doc: dict[str, dict[str, Any]] = {}
    non_matches: list[dict[str, Any]] = []
    total_cells = 0

    for r in rows:
        did = (r.get("document_id") or r.get("\ufeffdocument_id") or "").strip()
        agr = r["agreement_name"].strip()
        g_field = r["field"].strip()
        mapped = GOLD_TO_16_FIELD.get(g_field)
        if not mapped:
            continue

        total_cells += 1
        gold_status = r["gold_status"].strip()
        ref_val = r["gold_value"].strip()
        ref_quote = r.get("evidence_quote", "").strip()

        dstat = per_doc.setdefault(agr, {
            "doc_id": did,
            "total": 0,
            "exact": 0,
            "normalized": 0,
            "partial": 0,
            "no": 0,
        })
        dstat["total"] += 1

        pred_rec = extractions[did]["by_field"][mapped]
        pred_status = pred_rec["status"]
        pred_found = pred_status in {"verified", "needs_review"}
        pred_val = pred_rec["value"] if pred_found else (
            "Not found in this document" if pred_status == "not_found" else "[unverified/dropped]"
        )
        pred_quote = _format_evidence_quotes(pred_rec.get("evidence", []))

        if not pred_found:
            m = "no"
            reason = f"system status={pred_status}; flags={pred_rec.get('flags', [])}"
        elif not ref_val:
            m = "no"
            reason = f"gold_status={gold_status} with empty gold_value"
        else:
            res = values_match(mapped, pred_val, ref_val)
            m = res["match"]
            reason = res["reason"]

        counts[m] += 1
        dstat[m] += 1

        if m in {"partial", "no"}:
            non_matches.append({
                "dataset": "gold (human-verified)",
                "doc": f"{agr} ({did})",
                "field": f"{g_field} -> {mapped}",
                "predicted_value": pred_val,
                "reference_value": ref_val if ref_val else f"[{gold_status}]",
                "predicted_quote": pred_quote,
                "reference_quote": ref_quote,
                "rule_result": m,
                "rule_reason": reason,
                "who_is_right": "",
            })

    strict_matches = counts["exact"] + counts["normalized"]
    lenient_matches = strict_matches + counts["partial"]

    for agr, d in per_doc.items():
        d_strict = d["exact"] + d["normalized"]
        d_lenient = d_strict + d["partial"]
        d["strict_rate"] = d_strict / d["total"] if d["total"] else 0.0
        d["lenient_rate"] = d_lenient / d["total"] if d["total"] else 0.0

    summary = {
        "total_cells": total_cells,
        "counts": counts,
        "strict_matches": strict_matches,
        "strict_rate": strict_matches / total_cells if total_cells else 0.0,
        "lenient_matches": lenient_matches,
        "lenient_rate": lenient_matches / total_cells if total_cells else 0.0,
        "per_doc": per_doc,
    }
    return summary, non_matches


def write_mismatch_csv(rows: list[dict[str, Any]], csv_path: Path = REVIEW_CSV) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "dataset",
        "doc",
        "field",
        "predicted_value",
        "reference_value",
        "predicted_quote",
        "reference_quote",
        "rule_result",
        "rule_reason",
        "who_is_right",
    ]
    with open(csv_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run_eval(
    use_snapshot: bool = True,
    client: GeminiClient | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    with open(SILVER_CSV, encoding="utf-8-sig", newline="") as fh:
        silver_docs = sorted({r["doc_id"].strip() for r in csv.DictReader(fh)})
    with open(GOLD_CSV, encoding="utf-8-sig", newline="") as fh:
        gold_docs = sorted({(r.get("document_id") or r.get("\ufeffdocument_id") or "").strip() for r in csv.DictReader(fh)})

    all_docs = sorted(set(silver_docs + gold_docs))
    extractions, new_calls = load_cached_extractions(all_docs, client=client, use_snapshot=use_snapshot)

    silver_summary, silver_non_matches = evaluate_silver(extractions)
    gold_summary, gold_non_matches = evaluate_gold(extractions)

    all_non_matches = silver_non_matches + gold_non_matches
    write_mismatch_csv(all_non_matches, REVIEW_CSV)

    prior_3a_loaded = RESULTS_3A_JSON.is_file()
    payload = {
        "prior_3a_results_present": prior_3a_loaded,
        "new_live_calls": new_calls,
        "silver": silver_summary,
        "gold": gold_summary,
        "mismatch_csv_rows": len(all_non_matches),
        "mismatch_csv_path": str(REVIEW_CSV),
    }
    FIX_RESULTS_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload, all_non_matches


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    payload, non_matches = run_eval(use_snapshot=True)
    s = payload["silver"]
    g = payload["gold"]

    print("=" * 92)
    print("STAGE 3a-fix: TRANSPARENT VALUE MATCHING EVALUATION (CACHED STAGE 3a OUTPUTS)")
    print("=" * 92)
    print(f"New live API calls made: {payload['new_live_calls']}")
    print("\n--- (a) SILVER LABELS (LLM-assisted, NOT human gold; 3 docs, 41 definitive + 7 UNCLEAR) ---")
    print(f"Counts (36 positive fields): exact={s['counts']['exact']}, normalized={s['counts']['normalized']}, partial={s['counts']['partial']}, no={s['counts']['no']} | TN={s['tn']}, unclear={s['unclear_rows']}")
    print(f"STRICT  (exact + normalized only)   : P={s['strict']['precision']:.1%}, R={s['strict']['recall']:.1%}, F1={s['strict']['f1']:.1%} (TP={s['strict']['tp']}, FP={s['strict']['fp']}, FN={s['strict']['fn']})")
    print(f"LENIENT (exact + normalized + partial): P={s['lenient']['precision']:.1%}, R={s['lenient']['recall']:.1%}, F1={s['lenient']['f1']:.1%} (TP={s['lenient']['tp']}, FP={s['lenient']['fp']}, FN={s['lenient']['fn']})")

    print("\n--- (b) HUMAN-VERIFIED GOLD (3 docs, 27 cells across 9 mapped fields, incl. 1 UNAVAILABLE_MISSING_SCHEDULE) ---")
    print(f"Counts (27 cells): exact={g['counts']['exact']}, normalized={g['counts']['normalized']}, partial={g['counts']['partial']}, no={g['counts']['no']}")
    print(f"STRICT  field-match rate (exact + normalized)          : {g['strict_matches']}/{g['total_cells']} ({g['strict_rate']:.1%})")
    print(f"LENIENT field-match rate (exact + normalized + partial): {g['lenient_matches']}/{g['total_cells']} ({g['lenient_rate']:.1%})")
    for agr, d in sorted(g["per_doc"].items()):
        print(
            f"  - {agr:<13}: strict={d['exact']+d['normalized']}/{d['total']} ({d['strict_rate']:.1%}), "
            f"lenient={d['exact']+d['normalized']+d['partial']}/{d['total']} ({d['lenient_rate']:.1%}) "
            f"[exact={d['exact']}, norm={d['normalized']}, partial={d['partial']}, no={d['no']}]"
        )

    print(f"\nWrote {len(non_matches)} non-match rows to {REVIEW_CSV}")
    print("\n--- FIRST 20 NON-MATCHES FOR REVIEWER (who_is_right left empty) ---")
    for idx, row in enumerate(non_matches[:20], 1):
        print(
            f"[{idx:02d}] ({row['dataset']}) doc={row['doc']} | field={row['field']} | rule={row['rule_result']} ({row['rule_reason']})\n"
            f"     PRED_VAL  : {row['predicted_value']}\n"
            f"     REF_VAL   : {row['reference_value']}\n"
            f"     PRED_QUOTE: {row['predicted_quote'][:220]}\n"
            f"     REF_QUOTE : {row['reference_quote'][:220]}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
