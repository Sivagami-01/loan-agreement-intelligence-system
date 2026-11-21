"""scripts/run_4a2_scan.py

Stage 4a-2: Whole-document risk scan runner & evaluation against silver labels.

Selected 4 documents:
- dev:  03_dbs_mitc (indian_mitc), 000010/104897/0000950123-11-030926_2.txt (smallest dev SEC agreement)
- test: 09_muthoothomefin_MHIL-MITC (indian_mitc), 000081/810113/0000950116-04-002411_4.txt (smallest test SEC agreement)

Supports:
  --dry-run            Compute split + prefilter counts and API call estimate (0 API calls)
  --split dev|test|all Run live (or cached) classification on selected split
  --prompt-version v3  Override scan_prompt_version (e.g. v3 or v3b on dev only)
  --from-saved         Re-evaluate and rebuild review CSV / summary JSON from saved risk_scan_*.csv (0 API calls)
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.llm.gemini_client import GeminiClient  # noqa: E402
from src.qa.verify_quotes import normalize  # noqa: E402
from src.risk.classify import classify_clauses, load_risk_config  # noqa: E402
from src.risk.prefilter import prefilter_clauses  # noqa: E402
from src.risk.score import load_score_config, score_document  # noqa: E402
from src.risk.split_clauses import split_document  # noqa: E402

PROCESSED_DIR = ROOT / "data" / "processed"
SILVER_FINAL_CSV = PROCESSED_DIR / "labels" / "llm_assisted" / "risk_final.csv"
PRED_DEV_CSV = PROCESSED_DIR / "risk_pred_dev.csv"
PRED_TEST_CSV = PROCESSED_DIR / "risk_pred_test.csv"
REVIEW_CSV = PROCESSED_DIR / "risk_scan_review.csv"
SUMMARY_JSON = PROCESSED_DIR / "scan_4a2_summary.json"

TARGET_DOCS: list[dict[str, str]] = [
    {"doc_id": "03_dbs_mitc", "doc_type": "indian_mitc", "split": "dev"},
    {"doc_id": "000010/104897/0000950123-11-030926_2.txt", "doc_type": "sec_agreement", "split": "dev"},
    {"doc_id": "09_muthoothomefin_MHIL-MITC", "doc_type": "indian_mitc", "split": "test"},
    {"doc_id": "000081/810113/0000950116-04-002411_4.txt", "doc_type": "sec_agreement", "split": "test"},
]

SEVERITY_INDEX = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}

SCAN_CSV_COLUMNS = [
    "doc_id",
    "clause_id",
    "page",
    "clause_text",
    "prefilter_passed",
    "matched_keywords",
    "category",
    "severity",
    "rationale",
    "applied_rule",
    "number_flag",
    "flagged_numbers",
    "model_used",
    "parse_error",
    "prompt_version",
]

REVIEW_CSV_COLUMNS = [
    "doc_id",
    "clause_id",
    "page",
    "category",
    "severity",
    "clause_text",
    "rationale",
    "reviewer_verdict",
]


def doc_slug(doc_id: str) -> str:
    stem = doc_id[:-4] if doc_id.endswith(".txt") else doc_id
    return stem.replace("/", "_").replace("\\", "_")


def scan_csv_path(doc_id: str) -> Path:
    return PROCESSED_DIR / f"risk_scan_{doc_slug(doc_id)}.csv"


def _load_silver_by_doc() -> dict[str, list[dict[str, str]]]:
    by_doc: dict[str, list[dict[str, str]]] = {}
    with SILVER_FINAL_CSV.open("r", encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            did = row["doc_id"]
            by_doc.setdefault(did, []).append(row)
    return by_doc


def _load_v2_preds_by_doc() -> dict[str, list[dict[str, Any]]]:
    by_doc: dict[str, list[dict[str, Any]]] = {}
    for p in (PRED_DEV_CSV, PRED_TEST_CSV):
        if not p.is_file():
            continue
        with p.open("r", encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                by_doc.setdefault(row["doc_id"], []).append(
                    {
                        "clause_id": row["clause_id"],
                        "category": row["pred_category"],
                        "severity": row["pred_severity"],
                        "quote": row.get("pred_rationale", ""),
                        "page": "not available",
                        "rationale": row.get("pred_rationale", ""),
                    }
                )
    return by_doc


def _token_set(norm_text: str) -> set[str]:
    return {t for t in norm_text.split() if len(t) >= 2}


def _silver_overlap_candidates(
    silver_norm: str,
    scan_rows: list[dict[str, Any]],
) -> list[int]:
    """Return ALL indices of scan_rows that contain silver_norm or share >=50% normalized tokens."""
    if not silver_norm:
        return []
    s_tokens = _token_set(silver_norm)
    hits: set[int] = set()
    scored: list[tuple[float, int]] = []
    for idx, row in enumerate(scan_rows):
        cnorm = normalize(str(row["clause_text"]))
        if not cnorm:
            continue
        if silver_norm in cnorm or (len(cnorm) >= 40 and cnorm in silver_norm):
            hits.add(idx)
            scored.append((1.0, idx))
            continue
        c_tokens = _token_set(cnorm)
        if not s_tokens or not c_tokens:
            continue
        inter = len(s_tokens & c_tokens)
        best = max(inter / len(s_tokens), inter / len(c_tokens))
        if best >= 0.50 and inter >= 4:
            hits.add(idx)
            scored.append((best, idx))
    scored.sort(reverse=True)
    return [idx for _, idx in scored]


def _collapse_continuations(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Collapse split continuation pieces (same continuation_of root) so each cut clause counts ONCE."""
    by_root: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for r in rows:
        root_id = str(r.get("continuation_of") or "").strip() or str(r["clause_id"])
        if root_id not in by_root:
            by_root[root_id] = []
            order.append(root_id)
        by_root[root_id].append(r)

    collapsed: list[dict[str, Any]] = []
    for root_id in order:
        group = by_root[root_id]
        if len(group) == 1:
            collapsed.append(group[0])
        else:
            # Prefer head row (clause_id == root_id), taking highest severity across pieces
            head = next((g for g in group if g["clause_id"] == root_id), group[0])
            best_sev_row = max(group, key=lambda g: SEVERITY_INDEX.get(g.get("severity", ""), -1))
            merged = dict(head)
            merged["severity"] = best_sev_row["severity"]
            merged["category"] = best_sev_row["category"] if head.get("category") in {"none", "unclassified", ""} else head["category"]
            collapsed.append(merged)
    return collapsed


def _evaluate_doc_scan(
    doc_id: str,
    doc_type: str,
    split_name: str,
    scan_rows: list[dict[str, Any]],
    silver_rows: list[dict[str, str]],
    v2_rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Evaluate one scanned doc against silver_final clauses and return (metrics, unlabeled_flagged, silver_matches)."""
    matched_scan_indices: set[int] = set()
    silver_matches: list[dict[str, Any]] = []

    flagged_hits = 0
    cat_agree = 0
    sev_exact = 0
    sev_within1 = 0
    prefilter_kept_hits = 0

    for srow in silver_rows:
        snorm = normalize(srow["clause_text"])
        cand_idxs = _silver_overlap_candidates(snorm, scan_rows)
        matched_scan_indices.update(cand_idxs)

        cands = [scan_rows[i] for i in cand_idxs]
        kept = any(str(c["prefilter_passed"]).lower() == "true" for c in cands)
        if kept:
            prefilter_kept_hits += 1

        # Pick the best matching candidate: exact category match first, else highest severity flagged, else first
        flagged_cands = [
            c for c in cands if c["category"] not in {"none", "unclassified", ""} and c["severity"] in SEVERITY_INDEX
        ]
        target_cat = srow["final_category"]
        target_sev = srow["final_severity"]

        chosen: dict[str, Any] | None = None
        if flagged_cands:
            flagged_hits += 1
            exact_cat = [c for c in flagged_cands if c["category"] == target_cat]
            pool = exact_cat if exact_cat else flagged_cands
            chosen = max(pool, key=lambda c: SEVERITY_INDEX.get(c["severity"], -1))
            if chosen["category"] == target_cat:
                cat_agree += 1
            pred_sev = chosen["severity"]
            if pred_sev in SEVERITY_INDEX and target_sev in SEVERITY_INDEX:
                diff = abs(SEVERITY_INDEX[pred_sev] - SEVERITY_INDEX[target_sev])
                if diff == 0:
                    sev_exact += 1
                if diff <= 1:
                    sev_within1 += 1
        elif cands:
            chosen = cands[0]

        silver_matches.append(
            {
                "silver_clause_id": srow["clause_id"],
                "silver_category": target_cat,
                "silver_severity": target_sev,
                "matched_scan_ids": [c["clause_id"] for c in cands],
                "prefilter_kept": kept,
                "flagged": bool(flagged_cands),
                "pred_category": chosen["category"] if chosen else "NO_SPLIT_MATCH",
                "pred_severity": chosen["severity"] if chosen else "NO_SPLIT_MATCH",
                "snippet": " ".join(srow["clause_text"].split())[:110],
            }
        )

    raw_flagged_rows: list[dict[str, Any]] = []
    raw_unlabeled_rows: list[dict[str, Any]] = []

    for idx, row in enumerate(scan_rows):
        cat = row["category"]
        sev = row["severity"]
        is_flagged = cat not in {"none", "unclassified", ""} and sev in SEVERITY_INDEX
        if is_flagged:
            raw_flagged_rows.append(row)
            if idx not in matched_scan_indices:
                raw_unlabeled_rows.append(row)

    # Collapse continuation_of pieces so long cut clauses count ONCE in scoring and review/unlabeled counts
    logical_flagged = _collapse_continuations(raw_flagged_rows)
    total_flagged = len(logical_flagged)
    flagged_for_score = [
        {
            "clause_id": r["clause_id"],
            "category": r["category"],
            "severity": r["severity"],
            "quote": r["clause_text"],
            "page": r["page"],
            "rationale": r["rationale"],
        }
        for r in logical_flagged
    ]
    unlabeled_flagged = _collapse_continuations(raw_unlabeled_rows)
    unlabeled_by_sev = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
    for r in unlabeled_flagged:
        unlabeled_by_sev[r["severity"]] += 1

    score_cfg = load_score_config()
    scan_score = score_document(flagged_for_score, score_cfg)

    silver_for_score = [
        {
            "clause_id": r["clause_id"],
            "category": r["final_category"],
            "severity": r["final_severity"],
            "quote": r["clause_text"],
            "page": "not available",
            "rationale": r.get("rationale", ""),
        }
        for r in silver_rows
    ]
    silver_score = score_document(silver_for_score, score_cfg)
    v2_score = score_document(v2_rows, score_cfg) if v2_rows else None

    n_silver = len(silver_rows)
    n_total = len(scan_rows)
    n_passed = sum(1 for r in scan_rows if str(r["prefilter_passed"]).lower() == "true")
    metrics = {
        "doc_id": doc_id,
        "doc_type": doc_type,
        "split": split_name,
        "splitter_clauses": n_total,
        "prefilter_passed": n_passed,
        "prefilter_dropped": n_total - n_passed,
        "flagged_clauses": total_flagged,
        "none_clauses": sum(1 for r in scan_rows if r["category"] == "none"),
        "unclassified_clauses": sum(
            1 for r in scan_rows if r["category"] == "unclassified" or r["severity"] == "unclassified"
        ),
        "silver_total": n_silver,
        "silver_prefilter_kept": prefilter_kept_hits,
        "silver_flagged": flagged_hits,
        "silver_flagged_rate": round(flagged_hits / n_silver * 100.0, 1) if n_silver else 0.0,
        "silver_cat_agree_on_flagged": cat_agree,
        "silver_cat_agree_pct_of_flagged": round(cat_agree / flagged_hits * 100.0, 1) if flagged_hits else 0.0,
        "silver_cat_agree_pct_of_all": round(cat_agree / n_silver * 100.0, 1) if n_silver else 0.0,
        "silver_sev_exact_on_flagged": sev_exact,
        "silver_sev_within1_on_flagged": sev_within1,
        "silver_sev_within1_pct_of_flagged": round(sev_within1 / flagged_hits * 100.0, 1) if flagged_hits else 0.0,
        "unlabeled_flagged_total": len(unlabeled_flagged),
        "unlabeled_by_severity": unlabeled_by_sev,
        "full_scan_score": scan_score["score"],
        "full_scan_level": scan_score["level"],
        "full_scan_level_before_floor": scan_score["level_before_floor"],
        "full_scan_floor_applied": scan_score["critical_floor_applied"],
        "silver_labeled_score": silver_score["score"],
        "silver_labeled_level": silver_score["level"],
        "v2_labeled_score": v2_score["score"] if v2_score else None,
        "v2_labeled_level": v2_score["level"] if v2_score else None,
    }
    return metrics, unlabeled_flagged, silver_matches


def _write_scan_csv(doc_id: str, rows: list[dict[str, Any]]) -> Path:
    path = scan_csv_path(doc_id)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=SCAN_CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def _read_scan_csv(doc_id: str) -> list[dict[str, Any]]:
    path = scan_csv_path(doc_id)
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        r["page"] = int(r["page"]) if str(r["page"]).isdigit() else r["page"]
    return rows


def _write_review_csv(all_unlabeled: list[dict[str, Any]]) -> dict[str, int]:
    """Write <=25 High/Critical unlabeled + 10 random Med/Low unlabeled clauses."""
    high_crit = [
        r for r in all_unlabeled if r.get("severity") in {"Critical", "High"}
    ]
    # Critical first, then High, then doc_id/page/clause_id
    high_crit.sort(
        key=lambda r: (
            0 if r["severity"] == "Critical" else 1,
            str(r["doc_id"]),
            int(r["page"]) if str(r["page"]).isdigit() else 999999,
            str(r["clause_id"]),
        )
    )
    high_crit_sample = high_crit[:25]

    med_low = [r for r in all_unlabeled if r.get("severity") in {"Medium", "Low"}]
    rng = random.Random(42)
    med_low_sample = rng.sample(med_low, min(10, len(med_low)))
    med_low_sample.sort(
        key=lambda r: (
            str(r["doc_id"]),
            int(r["page"]) if str(r["page"]).isdigit() else 999999,
            str(r["clause_id"]),
        )
    )

    combined = high_crit_sample + med_low_sample
    with REVIEW_CSV.open("w", encoding="utf-8-sig", newline="") as fh:
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
        "high_critical_pool": len(high_crit),
        "high_critical_sampled": len(high_crit_sample),
        "medium_low_pool": len(med_low),
        "medium_low_sampled": len(med_low_sample),
        "total_review_rows": len(combined),
    }


def _run_dry_summary(selected_docs: list[dict[str, str]], batch_size: int, max_calls: int) -> None:
    print(f"=== STAGE 4a-2 PRE-API DRY RUN (batch_size={batch_size}, max_calls={max_calls}) ===")
    total_clauses = 0
    total_passed = 0
    total_calls = 0
    for d in selected_docs:
        cls = split_document(d["doc_id"])
        passed, dropped = prefilter_clauses(cls)
        calls = (len(passed) + batch_size - 1) // batch_size
        total_clauses += len(cls)
        total_passed += len(passed)
        total_calls += calls
        print(
            f"  [{d['split']:4s}] {d['doc_type']:13s} | {d['doc_id']:45s} | "
            f"split={len(cls):3d} | pass={len(passed):3d} | drop={len(dropped):2d} | calls={calls:2d}"
        )
    print(
        f"TOTAL: docs={len(selected_docs)}, split_clauses={total_clauses}, "
        f"prefilter_passed={total_passed}, estimated_calls={total_calls} / budget={max_calls}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 4a-2 whole-document risk scan")
    parser.add_argument("--dry-run", action="store_true", help="Print split/prefilter/call counts without API calls")
    parser.add_argument("--split", choices=["dev", "test", "all"], default="all", help="Which split to process")
    parser.add_argument("--prompt-version", default=None, help="Override scan prompt version (e.g. v3, v3b)")
    parser.add_argument("--from-saved", action="store_true", help="Rebuild metrics and review CSV from saved scan CSVs (0 API calls)")
    args = parser.parse_args()

    risk_cfg = load_risk_config()
    batch_size = int(risk_cfg.get("scan_batch_size", 20))
    max_calls = int(risk_cfg.get("scan_max_calls", 80))
    prompt_ver = args.prompt_version or str(risk_cfg.get("scan_prompt_version", "v3"))

    selected = [d for d in TARGET_DOCS if args.split == "all" or d["split"] == args.split]

    if args.dry_run:
        _run_dry_summary(selected, batch_size=batch_size, max_calls=max_calls)
        return

    silver_by_doc = _load_silver_by_doc()
    v2_by_doc = _load_v2_preds_by_doc()

    doc_summaries: list[dict[str, Any]] = []
    all_unlabeled_for_review: list[dict[str, Any]] = []
    model_counts_total: dict[str, int] = {}
    finished_docs: list[str] = []
    stopped_reason: str | None = None

    client = None if args.from_saved else GeminiClient()
    t0 = time.perf_counter()

    for d in selected:
        doc_id = d["doc_id"]
        doc_type = d["doc_type"]
        split_name = d["split"]

        if args.from_saved:
            p = scan_csv_path(doc_id)
            if not p.is_file():
                continue
            scan_rows = _read_scan_csv(doc_id)
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
            passed_items, dropped_items = prefilter_clauses(split_items)

            # Classify only passed clauses via Stage 4a classifier in scan mode (v3, batch=20, max_calls=80)
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
                            "clause_text": it["text"],  # EXACT splitter text preserved verbatim
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

            out_path = _write_scan_csv(doc_id, scan_rows)
            print(
                f"[SAVED] {out_path.name} | calls={doc_calls} (live={doc_live_calls}), "
                f"seconds={doc_seconds:.1f}, models={doc_models}"
            )

        finished_docs.append(doc_id)
        metrics, unlabeled_flagged, silver_matches = _evaluate_doc_scan(
            doc_id=doc_id,
            doc_type=doc_type,
            split_name=split_name,
            scan_rows=scan_rows,
            silver_rows=silver_by_doc.get(doc_id, []),
            v2_rows=v2_by_doc.get(doc_id, []),
        )
        metrics["calls_made"] = doc_calls
        metrics["live_calls_made"] = doc_live_calls
        metrics["seconds"] = doc_seconds
        metrics["model_used_counts"] = doc_models
        metrics["prompt_version"] = scan_rows[0]["prompt_version"] if scan_rows else prompt_ver
        metrics["silver_matches"] = silver_matches
        doc_summaries.append(metrics)
        all_unlabeled_for_review.extend(unlabeled_flagged)

        print(
            f"[{split_name:4s}] {doc_id} | split={metrics['splitter_clauses']} pass={metrics['prefilter_passed']} "
            f"flagged={metrics['flagged_clauses']} none={metrics['none_clauses']} | "
            f"silver_flagged={metrics['silver_flagged']}/{metrics['silver_total']} ({metrics['silver_flagged_rate']}%) | "
            f"cat_agree={metrics['silver_cat_agree_on_flagged']}/{metrics['silver_flagged']} ({metrics['silver_cat_agree_pct_of_flagged']}%) | "
            f"sev_w1={metrics['silver_sev_within1_on_flagged']}/{metrics['silver_flagged']} ({metrics['silver_sev_within1_pct_of_flagged']}%) | "
            f"unlabeled={metrics['unlabeled_flagged_total']} {metrics['unlabeled_by_severity']} | "
            f"score: scan={metrics['full_scan_score']} ({metrics['full_scan_level']}) vs silver={metrics['silver_labeled_score']} ({metrics['silver_labeled_level']}) "
            f"vs v2_labeled={metrics['v2_labeled_score']} ({metrics['v2_labeled_level']})"
        )

    total_seconds = round(time.perf_counter() - t0, 2)

    # Whenever review/summary covers all currently finished target docs saved on disk, write them cleanly
    review_stats = _write_review_csv(all_unlabeled_for_review)
    summary_payload = {
        "prompt_version": prompt_ver,
        "split_arg": args.split,
        "finished_docs": finished_docs,
        "stopped_reason": stopped_reason,
        "total_seconds": total_seconds,
        "model_used_counts": model_counts_total,
        "review_sampling": review_stats,
        "documents": doc_summaries,
    }
    SUMMARY_JSON.write_text(json.dumps(summary_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {REVIEW_CSV.relative_to(ROOT)} ({review_stats})")
    print(f"Wrote {SUMMARY_JSON.relative_to(ROOT)} in {total_seconds:.2f}s | models={model_counts_total}")


if __name__ == "__main__":
    main()
