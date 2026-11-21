"""scripts/score_holdout_v5.py

Zero-API evaluator for Stage 4a-4 hold-out review (37 rows across 3 unseen docs):
(a) Verifies every (doc_id, clause_id) exists in data/processed/risk_scan_review_v5.csv
    with exact matching scan_category and scan_severity.
(b) Computes category exact agreement (/37), severity exact & within-1 over decided rows,
    High-or-Critical precision, +1 over-rating, -1 under-rating, 2+ misses, overall & by doc (A/B/C).
(c) Checks exact match against reviewer's hand counts.
(d) Prints TARGET MET / TARGET MISSED (severity within-1 >= 90%), severity exact INFO,
    and macro-F1 INCONCLUSIVE note.
(e) Read-only WHAT-IF padded_top3 document score table comparing scanned vs reviewer severities.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_4a2_scan import _collapse_continuations, doc_slug  # noqa: E402
from src.risk.score import load_score_config, score_document  # noqa: E402

PROCESSED_DIR = ROOT / "data" / "processed"
HOLDOUT_CSV = PROCESSED_DIR / "labels" / "llm_assisted" / "scan_review_holdout_v5.csv"
REVIEW_V5_CSV = PROCESSED_DIR / "risk_scan_review_v5.csv"
LLM_LOG_PATH = PROCESSED_DIR / "llm_log.csv"

DOC_LABELS = {
    "000087/876645/0000891618-03-004250_9.txt": "A (000087/876645)",
    "04_dbs_mitc-ahl": "B (04_dbs_mitc-ahl)",
    "000104/1041426/0000950144-99-003055_2.txt": "C (000104/1041426)",
}
SEV_IDX = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}


def _count_llm_log_rows() -> int:
    with LLM_LOG_PATH.open("r", encoding="utf-8", errors="ignore") as fh:
        return sum(1 for _ in fh)


def _compute_subset_metrics(rows: list[dict[str, str]]) -> dict[str, Any]:
    n_total = len(rows)
    cat_exact = sum(1 for r in rows if r["scan_category"] == r["rev_category"])

    decided = [r for r in rows if r["rev_severity"] != "unclear"]
    n_decided = len(decided)
    sev_exact = sum(1 for r in decided if r["scan_severity"] == r["rev_severity"])
    sev_w1 = sum(
        1 for r in decided if abs(SEV_IDX[r["scan_severity"]] - SEV_IDX[r["rev_severity"]]) <= 1
    )

    over1 = sum(1 for r in decided if SEV_IDX[r["scan_severity"]] - SEV_IDX[r["rev_severity"]] == 1)
    under1 = sum(1 for r in decided if SEV_IDX[r["scan_severity"]] - SEV_IDX[r["rev_severity"]] == -1)
    miss2plus = sum(1 for r in decided if abs(SEV_IDX[r["scan_severity"]] - SEV_IDX[r["rev_severity"]]) >= 2)
    over2plus = sum(1 for r in decided if SEV_IDX[r["scan_severity"]] - SEV_IDX[r["rev_severity"]] >= 2)
    under2plus = sum(1 for r in decided if SEV_IDX[r["scan_severity"]] - SEV_IDX[r["rev_severity"]] <= -2)

    hc_decided = [r for r in decided if r["scan_severity"] in {"High", "Critical"}]
    hc_hits = sum(1 for r in hc_decided if r["rev_severity"] in {"High", "Critical"})

    return {
        "total": n_total,
        "cat_exact": cat_exact,
        "decided": n_decided,
        "unclear": n_total - n_decided,
        "sev_exact": sev_exact,
        "sev_w1": sev_w1,
        "hc_hits": hc_hits,
        "hc_total": len(hc_decided),
        "over1": over1,
        "under1": under1,
        "miss2plus": miss2plus,
        "over2plus": over2plus,
        "under2plus": under2plus,
    }


def _pct(num: int, den: int) -> str:
    return f"{num}/{den} ({num/den*100:.1f}%)" if den else f"{num}/0 (n/a)"


def main() -> None:
    rows_before = _count_llm_log_rows()

    with HOLDOUT_CSV.open("r", encoding="utf-8-sig", newline="") as fh:
        hold_rows = list(csv.DictReader(fh))
    with REVIEW_V5_CSV.open("r", encoding="utf-8-sig", newline="") as fh:
        rev5_map = {(r["doc_id"], r["clause_id"]): r for r in csv.DictReader(fh)}

    # (a) Cross-check existence and exact scan_category / scan_severity match
    mismatches: list[str] = []
    for r in hold_rows:
        key = (r["doc_id"], r["clause_id"])
        src = rev5_map.get(key)
        if src is None:
            mismatches.append(f"MISSING in risk_scan_review_v5.csv: {key}")
            continue
        if src["category"] != r["scan_category"] or src["severity"] != r["scan_severity"]:
            mismatches.append(
                f"MISMATCH {key}: review_v5=({src['category']}/{src['severity']}) vs holdout=({r['scan_category']}/{r['scan_severity']})"
            )

    check_a_status = "PASS" if (len(hold_rows) == 37 and not mismatches) else "FAIL"
    print(f"CHECK_A {check_a_status} | verified {len(hold_rows)} rows against risk_scan_review_v5.csv; mismatches={len(mismatches)}")
    for mm in mismatches:
        print(f"  {mm}")

    # (b) Overall + per-doc breakdown
    ov = _compute_subset_metrics(hold_rows)
    print("\n=== HOLDOUT VERIFICATION METRICS (37 reviewed rows; single reviewer) ===")
    print(
        f"OVERALL | cat_exact={_pct(ov['cat_exact'], ov['total'])} | "
        f"sev_exact={_pct(ov['sev_exact'], ov['decided'])} (unclear={ov['unclear']}) | "
        f"sev_within1={_pct(ov['sev_w1'], ov['decided'])} | "
        f"High_or_Crit_prec={_pct(ov['hc_hits'], ov['hc_total'])} | "
        f"over1={ov['over1']}, under1={ov['under1']}, miss2+={ov['miss2plus']} (over2+={ov['over2plus']}, under2+={ov['under2plus']})"
    )

    for did, lbl in DOC_LABELS.items():
        sub = [r for r in hold_rows if r["doc_id"] == did]
        m = _compute_subset_metrics(sub)
        print(
            f"  {lbl:20s} | cat_exact={_pct(m['cat_exact'], m['total'])} | "
            f"sev_exact={_pct(m['sev_exact'], m['decided'])} (unclear={m['unclear']}) | "
            f"sev_within1={_pct(m['sev_w1'], m['decided'])} | "
            f"HC_prec={_pct(m['hc_hits'], m['hc_total'])} | "
            f"over1={m['over1']}, under1={m['under1']}, miss2+={m['miss2plus']} (over2+={m['over2plus']}, under2+={m['under2plus']})"
        )

    # (c) Compare with hand counts
    hand_match = (
        ov["sev_exact"] == 22
        and ov["decided"] == 35
        and ov["sev_w1"] == 34
        and ov["cat_exact"] == 33
        and ov["total"] == 37
        and ov["hc_hits"] == 15
        and ov["hc_total"] == 25
    )
    if hand_match:
        print("\nHOLDOUT_COUNT MATCH")
    else:
        print(
            f"\nHOLDOUT_COUNT MISMATCH | hand=(sev_exact 22/35, within-1 34/35, cat 33/37, HC_prec 15/25) "
            f"vs actual=(sev_exact {ov['sev_exact']}/{ov['decided']}, within-1 {ov['sev_w1']}/{ov['decided']}, "
            f"cat {ov['cat_exact']}/{ov['total']}, HC_prec {ov['hc_hits']}/{ov['hc_total']})"
        )

    # (d) Targets and INCONCLUSIVE notes
    w1_pct = (ov["sev_w1"] / ov["decided"] * 100.0) if ov["decided"] else 0.0
    print(f"TARGET {'MET' if w1_pct >= 90.0 else 'MISSED'} | hold-out severity within-1 = {ov['sev_w1']}/{ov['decided']} ({w1_pct:.1f}% >= 90% target)")
    print("INFO: severity exact has no target")
    print("macro-F1: INCONCLUSIVE (hold-out is biased to High-flagged rows; no recall measured)")

    # Step 3: WHAT-IF padded_top3 document scores (read-only)
    rev_lookup = {(r["doc_id"], r["clause_id"]): r for r in hold_rows}
    score_cfg = load_score_config()
    print("\n=== WHAT-IF, partial reviewer coverage, not a result ===")
    print("doc | score_scanned | level_scanned | floor_scanned | score_reviewer | level_reviewer | floor_reviewer")
    for did, lbl in DOC_LABELS.items():
        scan_path = PROCESSED_DIR / f"risk_scan_v5_{doc_slug(did)}.csv"
        with scan_path.open("r", encoding="utf-8-sig", newline="") as fh:
            raw_rows = list(csv.DictReader(fh))
        for r in raw_rows:
            r["page"] = int(r["page"]) if str(r["page"]).isdigit() else r["page"]

        flagged = [
            r for r in _collapse_continuations(raw_rows)
            if r["category"] not in {"none", "unclassified", ""} and r["severity"] in SEV_IDX
        ]
        clauses_scanned = [
            {
                "clause_id": r["clause_id"],
                "category": r["category"],
                "severity": r["severity"],
                "quote": r["clause_text"],
                "page": r["page"],
                "rationale": r["rationale"],
            }
            for r in flagged
        ]
        clauses_whatif: list[dict[str, Any]] = []
        for c in clauses_scanned:
            rv = rev_lookup.get((did, c["clause_id"]))
            c2 = dict(c)
            if rv and rv["rev_severity"] in SEV_IDX:
                c2["severity"] = rv["rev_severity"]
            clauses_whatif.append(c2)

        res_sc = score_document(clauses_scanned, score_cfg)
        res_wi = score_document(clauses_whatif, score_cfg)
        print(
            f"{lbl:20s} | {res_sc['score']:13.1f} | {res_sc['level']:13s} | "
            f"{'yes' if res_sc['critical_floor_applied'] else 'no':13s} | "
            f"{res_wi['score']:14.1f} | {res_wi['level']:14s} | "
            f"{'yes' if res_wi['critical_floor_applied'] else 'no'}"
        )

    rows_after = _count_llm_log_rows()
    log_status = "PASS" if rows_before == rows_after else "FAIL"
    print(f"\nllm_log rows: {rows_before} -> {rows_after} | {log_status}")


if __name__ == "__main__":
    main()
