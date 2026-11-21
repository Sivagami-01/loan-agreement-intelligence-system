"""scripts/run_4a3_scan.py

Stage 4a-3: Whole-document scan with prompt v4, SEC real pages, and finer MITC splitter.

Evaluation design (anti-contamination):
- TRAINING docs (4 docs previously scanned under v3; used ONLY to report training-row
  agreement with the 27 finance-review verdicts, NOT held-out accuracy):
    03_dbs_mitc, 000010/104897/..., 09_muthoothomefin_MHIL-MITC, 000081/810113/...
- FRESH docs (3 docs never scanned before under Stage 4a-2/4a-3):
    000103/1039213/0000912057-97-018811_19.txt (test SEC)
    000105/1052667/0000912057-00-028795_20.txt (test SEC)
    11_gichfindia_MOST-IMPORTANT-TERMS-1 (dev MITC; note: no clean MITC test doc remains
    because 09_muthoothomefin_MHIL-MITC is contaminated by v3 scan)

Writes:
- data/processed/risk_scan_v4_<slug>.csv (all 7 documents)
- data/processed/risk_scan_review_v4.csv (ALL unlabeled High/Critical + 10 random Med/Low from 3 fresh docs)
- data/processed/scan_4a3_summary.json
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_4a2_scan import (  # noqa: E402
    PROCESSED_DIR,
    REVIEW_CSV_COLUMNS,
    SCAN_CSV_COLUMNS,
    SEVERITY_INDEX,
    SILVER_FINAL_CSV,
    _evaluate_doc_scan,
    _load_silver_by_doc,
    _load_v2_preds_by_doc,
    _token_set,
    doc_slug,
)
from src.llm.gemini_client import GeminiClient  # noqa: E402
from src.qa.verify_quotes import normalize  # noqa: E402
from src.risk.classify import classify_clauses, load_risk_config  # noqa: E402
from src.risk.prefilter import prefilter_clauses  # noqa: E402
from src.risk.split_clauses import split_document  # noqa: E402

VERDICTS_CSV = PROCESSED_DIR / "labels" / "llm_assisted" / "scan_review_verdicts.csv"
V3_REVIEW_CSV = PROCESSED_DIR / "risk_scan_review.csv"
REVIEW_V4_CSV = PROCESSED_DIR / "risk_scan_review_v4.csv"
SUMMARY_V4_JSON = PROCESSED_DIR / "scan_4a3_summary.json"

TARGET_DOCS_4A3: list[dict[str, str]] = [
    {"doc_id": "03_dbs_mitc", "doc_type": "indian_mitc", "split": "dev", "role": "training"},
    {"doc_id": "000010/104897/0000950123-11-030926_2.txt", "doc_type": "sec_agreement", "split": "dev", "role": "training"},
    {"doc_id": "09_muthoothomefin_MHIL-MITC", "doc_type": "indian_mitc", "split": "test", "role": "training"},
    {"doc_id": "000081/810113/0000950116-04-002411_4.txt", "doc_type": "sec_agreement", "split": "test", "role": "training"},
    {"doc_id": "000103/1039213/0000912057-97-018811_19.txt", "doc_type": "sec_agreement", "split": "test", "role": "fresh"},
    {"doc_id": "000105/1052667/0000912057-00-028795_20.txt", "doc_type": "sec_agreement", "split": "test", "role": "fresh"},
    {"doc_id": "11_gichfindia_MOST-IMPORTANT-TERMS-1", "doc_type": "indian_mitc", "split": "dev", "role": "fresh"},
]


def scan_v4_csv_path(doc_id: str) -> Path:
    return PROCESSED_DIR / f"risk_scan_v4_{doc_slug(doc_id)}.csv"


def _write_scan_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=SCAN_CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _read_scan_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        r["page"] = int(r["page"]) if str(r["page"]).isdigit() else r["page"]
    return rows


def _page_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    non1 = sum(1 for r in rows if str(r["page"]) != "1")
    real_pages = sum(1 for r in rows if str(r["page"]).isdigit())
    int_pages = [int(r["page"]) for r in rows if str(r["page"]).isdigit()]
    prange = f"{min(int_pages)}..{max(int_pages)}" if int_pages else "not available"
    return {
        "total": total,
        "non_page1": non1,
        "non_page1_pct": round(non1 / total * 100.0, 1) if total else 0.0,
        "real_page_count": real_pages,
        "real_page_pct": round(real_pages / total * 100.0, 1) if total else 0.0,
        "page_range": prange,
    }


def _run_dry_summary(selected: list[dict[str, str]], batch_size: int, max_calls: int) -> None:
    print(f"=== STAGE 4a-3 PRE-API DRY RUN (batch_size={batch_size}, max_calls={max_calls}) ===")
    print("NOTE: No clean MITC test document remains (09_muthoothomefin_MHIL-MITC is contaminated by v3 review).")
    tot_cls = 0
    tot_pass = 0
    tot_calls = 0
    for d in selected:
        cls = split_document(d["doc_id"])
        passed, dropped = prefilter_clauses(cls)
        calls = (len(passed) + batch_size - 1) // batch_size
        ps = _page_stats(cls)
        tot_cls += len(cls)
        tot_pass += len(passed)
        tot_calls += calls
        print(
            f"  [{d['role']:8s}|{d['split']:4s}] {d['doc_type']:13s} | {d['doc_id']:45s} | "
            f"split={len(cls):3d} | pass={len(passed):3d} | drop={len(dropped):2d} | "
            f"calls={calls:2d} | page!=1:{ps['non_page1']}/{len(cls)}({ps['non_page1_pct']}%) | range={ps['page_range']}"
        )
    print(
        f"TOTAL: docs={len(selected)}, split_clauses={tot_cls}, "
        f"prefilter_passed={tot_pass}, estimated_calls={tot_calls} / budget={max_calls}"
    )


def _match_v3_row_to_v4(
    v3_text: str,
    v4_doc_rows: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Match a v3 reviewed clause snippet to the corresponding v4 scan clause by normalized text."""
    v3_norm = normalize(v3_text)
    if not v3_norm:
        return None
    # Exact / containment match first
    best: dict[str, Any] | None = None
    best_score = -1.0
    for r in v4_doc_rows:
        cnorm = normalize(str(r.get("clause_text", "")))
        if not cnorm:
            continue
        if v3_norm == cnorm:
            return r
        if v3_norm in cnorm or cnorm in v3_norm:
            ratio = min(len(v3_norm), len(cnorm)) / max(len(v3_norm), len(cnorm))
            if ratio > best_score:
                best_score = ratio
                best = r
    if best is not None and best_score >= 0.45:
        return best

    t3 = _token_set(v3_norm)
    if not t3:
        return None
    for r in v4_doc_rows:
        t4 = _token_set(normalize(str(r.get("clause_text", ""))))
        if not t4:
            continue
        inter = len(t3 & t4)
        jacc = inter / len(t3 | t4)
        if jacc > best_score:
            best_score = jacc
            best = r
    return best if best_score >= 0.4 else None


def _compute_verdict_agreement(v4_by_doc: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """Compare v3 and v4 against the 27 finance-review verdicts on the training rows."""
    if not VERDICTS_CSV.is_file() or not V3_REVIEW_CSV.is_file():
        return {}
    with VERDICTS_CSV.open("r", encoding="utf-8-sig", newline="") as fh:
        verdicts = list(csv.DictReader(fh))
    with V3_REVIEW_CSV.open("r", encoding="utf-8-sig", newline="") as fh:
        v3_rows = {(r["doc_id"], r["clause_id"]): r for r in csv.DictReader(fh)}

    v3_exact = 0
    v3_cat = 0
    v3_sev = 0
    v4_exact = 0
    v4_cat = 0
    v4_sev = 0
    decided = 0
    unclear_count = 0
    details: list[dict[str, Any]] = []

    for v in verdicts:
        did = v["doc_id"]
        cid = v["clause_id"]
        rcat = v["reviewer_category"].strip()
        rsev = v["reviewer_severity"].strip()
        verd = v["verdict"].strip()
        v3_item = v3_rows.get((did, cid), {})
        v3_cat_pred = v3_item.get("category", "")
        v3_sev_pred = v3_item.get("severity", "")
        v4_item = _match_v3_row_to_v4(v3_item.get("clause_text", ""), v4_by_doc.get(did, []))
        v4_cat_pred = v4_item["category"] if v4_item else "MISSING"
        v4_sev_pred = v4_item["severity"] if v4_item else "MISSING"
        v4_cid = v4_item["clause_id"] if v4_item else "MISSING"

        if verd == "unclear" or rsev == "unclear":
            unclear_count += 1
            details.append(
                {
                    "doc_id": did,
                    "v3_id": cid,
                    "v4_id": v4_cid,
                    "reviewer": f"{rcat}/{rsev} (unclear)",
                    "v3": f"{v3_cat_pred}/{v3_sev_pred}",
                    "v4": f"{v4_cat_pred}/{v4_sev_pred}",
                    "v3_exact": None,
                    "v4_exact": None,
                }
            )
            continue

        decided += 1
        v3_c_ok = v3_cat_pred == rcat
        v3_s_ok = v3_sev_pred == rsev
        v3_e_ok = v3_c_ok and v3_s_ok
        v4_c_ok = v4_cat_pred == rcat
        v4_s_ok = v4_sev_pred == rsev
        v4_e_ok = v4_c_ok and v4_s_ok

        v3_cat += int(v3_c_ok)
        v3_sev += int(v3_s_ok)
        v3_exact += int(v3_e_ok)
        v4_cat += int(v4_c_ok)
        v4_sev += int(v4_s_ok)
        v4_exact += int(v4_e_ok)

        details.append(
            {
                "doc_id": did,
                "v3_id": cid,
                "v4_id": v4_cid,
                "reviewer": f"{rcat}/{rsev}",
                "v3": f"{v3_cat_pred}/{v3_sev_pred}",
                "v4": f"{v4_cat_pred}/{v4_sev_pred}",
                "v3_exact": v3_e_ok,
                "v4_exact": v4_e_ok,
            }
        )

    return {
        "label": "agreement on training rows, not accuracy",
        "total_verdict_rows": len(verdicts),
        "decided_rows": decided,
        "unclear_rows": unclear_count,
        "v3": {
            "exact_match": v3_exact,
            "exact_pct": round(v3_exact / decided * 100.0, 1) if decided else 0.0,
            "category_match": v3_cat,
            "severity_match": v3_sev,
        },
        "v4": {
            "exact_match": v4_exact,
            "exact_pct": round(v4_exact / decided * 100.0, 1) if decided else 0.0,
            "category_match": v4_cat,
            "severity_match": v4_sev,
        },
        "details": details,
    }


def _write_fresh_review_csv(fresh_unlabeled: list[dict[str, Any]]) -> dict[str, int]:
    """Write ALL unlabeled High/Critical clauses from 3 fresh docs + 10 random Med/Low."""
    high_crit = [r for r in fresh_unlabeled if r.get("severity") in {"Critical", "High"}]
    high_crit.sort(
        key=lambda r: (
            0 if r["severity"] == "Critical" else 1,
            str(r["doc_id"]),
            int(r["page"]) if str(r["page"]).isdigit() else 999999,
            str(r["clause_id"]),
        )
    )
    med_low = [r for r in fresh_unlabeled if r.get("severity") in {"Medium", "Low"}]
    rng = random.Random(42)
    med_low_sample = rng.sample(med_low, min(10, len(med_low)))
    med_low_sample.sort(
        key=lambda r: (
            str(r["doc_id"]),
            int(r["page"]) if str(r["page"]).isdigit() else 999999,
            str(r["clause_id"]),
        )
    )
    combined = high_crit + med_low_sample
    with REVIEW_V4_CSV.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=REVIEW_CSV_COLUMNS)
        writer.writeheader()
        for r in combined:
            writer.writerow(
                {
                    "doc_id": r["doc_id"],
                    "clause_id": r["clause_id"],
                    "page": r["page"],
                    "category": r["category"],
                    "severity": r["severity"],
                    "clause_text": r["clause_text"],
                    "rationale": r["rationale"],
                    "reviewer_verdict": "",
                }
            )
    return {
        "fresh_high_critical_all": len(high_crit),
        "fresh_medium_low_pool": len(med_low),
        "fresh_medium_low_sampled": len(med_low_sample),
        "total_review_rows": len(combined),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 4a-3 whole-document risk scan (v4)")
    parser.add_argument("--dry-run", action="store_true", help="Print split, page, prefilter, and call counts without API calls")
    parser.add_argument("--group", choices=["training", "fresh", "all"], default="all", help="Document group to scan")
    parser.add_argument("--from-saved", action="store_true", help="Re-evaluate from saved risk_scan_v4_*.csv files (0 API calls)")
    args = parser.parse_args()

    risk_cfg = load_risk_config()
    batch_size = int(risk_cfg.get("scan_batch_size", 20))
    max_calls = int(risk_cfg.get("scan_max_calls", 40))
    prompt_ver = str(risk_cfg.get("scan_prompt_version", "v4"))

    selected = [d for d in TARGET_DOCS_4A3 if args.group == "all" or d["role"] == args.group]

    if args.dry_run:
        _run_dry_summary(selected, batch_size=batch_size, max_calls=max_calls)
        return

    silver_by_doc = _load_silver_by_doc()
    v2_by_doc = _load_v2_preds_by_doc()

    client = None if args.from_saved else GeminiClient()
    t0 = time.perf_counter()

    doc_summaries: list[dict[str, Any]] = []
    v4_by_doc: dict[str, list[dict[str, Any]]] = {}
    fresh_unlabeled: list[dict[str, Any]] = []
    model_counts_total: dict[str, int] = {}
    finished_docs: list[str] = []
    stopped_reason: str | None = None
    total_live_calls = 0

    for d in selected:
        doc_id = d["doc_id"]
        doc_type = d["doc_type"]
        split_name = d["split"]
        role = d["role"]
        out_path = scan_v4_csv_path(doc_id)

        if args.from_saved:
            if not out_path.is_file():
                continue
            scan_rows = _read_scan_csv(out_path)
            doc_calls = 0
            doc_live_calls = 0
            doc_seconds = 0.0
            doc_models: dict[str, int] = {}
            for r in scan_rows:
                m = str(r.get("model_used", ""))
                if m and m != "prefilter":
                    doc_models[m] = doc_models.get(m, 0) + 1
                    model_counts_total[m] = model_counts_total.get(m, 0) + 1
        else:
            assert client is not None
            doc_t0 = time.perf_counter()
            split_items = split_document(doc_id)
            passed_items, _ = prefilter_clauses(split_items)
            classify_input = [
                {
                    "clause_id": it["clause_id"],
                    "clause_text": it["text"],
                    "page": f"page {it['page']}",
                }
                for it in passed_items
            ]
            res = classify_clauses(
                doc_type=doc_type,
                clauses=classify_input,
                client=client,
                config=risk_cfg,
                prompt_version=prompt_ver,
                scan=True,
            )
            doc_seconds = round(time.perf_counter() - doc_t0, 2)
            doc_calls = res["calls_made"]
            doc_live_calls = res["live_calls_made"]
            total_live_calls += doc_live_calls
            doc_models = res["model_used_counts"]
            for m, cnt in doc_models.items():
                model_counts_total[m] = model_counts_total.get(m, 0) + cnt

            if res.get("quota_stopped") or res.get("budget_stopped"):
                reason = "quota_429" if res.get("quota_stopped") else "budget_cap"
                stopped_reason = f"{reason} during {doc_id} (errors={res.get('errors')})"
                print(
                    f"[STOPPED EARLY] {stopped_reason}. "
                    f"Finished docs so far ({len(finished_docs)}): {finished_docs}"
                )
                break
            if res.get("errors") and res.get("unclassified_count", 0) >= len(classify_input):
                stopped_reason = f"api_failure during {doc_id} (errors={res.get('errors')[:2]})"
                print(f"[FAILED] {stopped_reason}")
                break

            pred_by_id = {r["clause_id"]: r for r in res["results"]}
            passed_ids = {it["clause_id"]: it for it in passed_items}
            scan_rows = []
            for it in split_items:
                cid = it["clause_id"]
                if cid in passed_ids:
                    enriched = passed_ids[cid]
                    pred = pred_by_id[cid]
                    scan_rows.append(
                        {
                            "doc_id": doc_id,
                            "clause_id": cid,
                            "page": it["page"],
                            "clause_text": it["text"],
                            "prefilter_passed": True,
                            "matched_keywords": "; ".join(enriched.get("matched_keywords", [])),
                            "category": pred["category"],
                            "severity": pred["severity"],
                            "rationale": pred["rationale"],
                            "applied_rule": pred["applied_rule"],
                            "number_flag": pred["number_flag"],
                            "flagged_numbers": "; ".join(str(x) for x in pred["flagged_numbers"]),
                            "model_used": pred["model_used"],
                            "parse_error": pred["parse_error"],
                            "prompt_version": prompt_ver,
                        }
                    )
                else:
                    scan_rows.append(
                        {
                            "doc_id": doc_id,
                            "clause_id": cid,
                            "page": it["page"],
                            "clause_text": it["text"],
                            "prefilter_passed": False,
                            "matched_keywords": "",
                            "category": "none",
                            "severity": "none",
                            "rationale": "[prefilter-dropped] No guideline or loan-risk keyword triggered.",
                            "applied_rule": "none",
                            "number_flag": False,
                            "flagged_numbers": "",
                            "model_used": "prefilter",
                            "parse_error": False,
                            "prompt_version": prompt_ver,
                        }
                    )

            _write_scan_csv(out_path, scan_rows)
            print(
                f"[SAVED] {out_path.name} | calls={doc_calls} (live={doc_live_calls}), "
                f"seconds={doc_seconds:.1f}, models={doc_models}"
            )

        finished_docs.append(doc_id)
        v4_by_doc[doc_id] = scan_rows
        metrics, unlabeled_flagged, silver_matches = _evaluate_doc_scan(
            doc_id=doc_id,
            doc_type=doc_type,
            split_name=split_name,
            scan_rows=scan_rows,
            silver_rows=silver_by_doc.get(doc_id, []),
            v2_rows=v2_by_doc.get(doc_id, []),
        )
        pstats = _page_stats(scan_rows)
        metrics["role"] = role
        metrics["page_stats"] = pstats
        metrics["calls_made"] = doc_calls
        metrics["live_calls_made"] = doc_live_calls
        metrics["seconds"] = doc_seconds
        metrics["model_used_counts"] = doc_models
        metrics["prompt_version"] = scan_rows[0]["prompt_version"] if scan_rows else prompt_ver
        metrics["silver_matches"] = silver_matches
        doc_summaries.append(metrics)
        if role == "fresh":
            fresh_unlabeled.extend(unlabeled_flagged)

        delta = round(metrics["full_scan_score"] - metrics["silver_labeled_score"], 1)
        print(
            f"[{role:8s}|{split_name:4s}] {doc_id} | split={metrics['splitter_clauses']} pass={metrics['prefilter_passed']} "
            f"flagged={metrics['flagged_clauses']} none={metrics['none_clauses']} | "
            f"real_pages={pstats['real_page_pct']}% ({pstats['page_range']}) | "
            f"silver_flagged={metrics['silver_flagged']}/{metrics['silver_total']} ({metrics['silver_flagged_rate']}%) | "
            f"cat_agree={metrics['silver_cat_agree_on_flagged']}/{metrics['silver_flagged']} ({metrics['silver_cat_agree_pct_of_flagged']}%) | "
            f"sev_w1={metrics['silver_sev_within1_on_flagged']}/{metrics['silver_flagged']} ({metrics['silver_sev_within1_pct_of_flagged']}%) | "
            f"unlabeled={metrics['unlabeled_flagged_total']} {metrics['unlabeled_by_severity']} | "
            f"score: scan={metrics['full_scan_score']} ({metrics['full_scan_level']}) vs silver={metrics['silver_labeled_score']} ({metrics['silver_labeled_level']}) delta={delta:+.1f}"
        )

    total_seconds = round(time.perf_counter() - t0, 2)
    verdict_agreement = _compute_verdict_agreement(v4_by_doc)
    if verdict_agreement:
        v3m = verdict_agreement["v3"]
        v4m = verdict_agreement["v4"]
        dec = verdict_agreement["decided_rows"]
        print(
            f"\nTRAINING-ROW VERDICT AGREEMENT ({verdict_agreement['label']}; n_decided={dec}, unclear={verdict_agreement['unclear_rows']}):\n"
            f"  v3 exact={v3m['exact_match']}/{dec} ({v3m['exact_pct']}%), cat={v3m['category_match']}/{dec}, sev={v3m['severity_match']}/{dec}\n"
            f"  v4 exact={v4m['exact_match']}/{dec} ({v4m['exact_pct']}%), cat={v4m['category_match']}/{dec}, sev={v4m['severity_match']}/{dec}"
        )

    review_stats = _write_fresh_review_csv(fresh_unlabeled)
    summary_payload = {
        "prompt_version": prompt_ver,
        "group_arg": args.group,
        "finished_docs": finished_docs,
        "stopped_reason": stopped_reason,
        "total_live_calls": total_live_calls,
        "total_seconds": total_seconds,
        "model_used_counts": model_counts_total,
        "training_verdict_agreement": verdict_agreement,
        "fresh_review_sampling": review_stats,
        "documents": doc_summaries,
        "contamination_note": "09_muthoothomefin_MHIL-MITC was scanned under v3 and is training evidence; no clean MITC test document remains.",
    }
    SUMMARY_V4_JSON.write_text(json.dumps(summary_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {REVIEW_V4_CSV.relative_to(ROOT)} ({review_stats})")
    print(f"Wrote {SUMMARY_V4_JSON.relative_to(ROOT)} in {total_seconds:.2f}s | models={model_counts_total}")


if __name__ == "__main__":
    main()
