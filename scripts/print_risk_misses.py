"""scripts/print_risk_misses.py

Prints the 20 largest classifier vs silver disagreements across test and dev
(severity off by 2+ levels first, then category errors) in the same format
as print_risk_review.py.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

csv.field_size_limit(2**31 - 1)

ROOT = Path(__file__).resolve().parents[1]
FINAL_CSV = ROOT / "data" / "processed" / "labels" / "llm_assisted" / "risk_final.csv"
PRED_TEST = ROOT / "data" / "processed" / "risk_pred_test.csv"
PRED_DEV = ROOT / "data" / "processed" / "risk_pred_dev.csv"

SEV_INDEX = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}


def _load(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _sev_gap(row: dict[str, str]) -> int:
    t = row.get("true_severity", "")
    p = row.get("pred_severity", "")
    if t in SEV_INDEX and p in SEV_INDEX:
        return abs(SEV_INDEX[t] - SEV_INDEX[p])
    return 3


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    final_rows = {(r["doc_id"], r["clause_id"]): r for r in _load(FINAL_CSV)}
    preds = _load(PRED_TEST) + _load(PRED_DEV)
    if not preds:
        print("No prediction CSVs found (run dev/test evaluation first).")
        return

    misses: list[tuple[tuple[int, int, int, int], dict[str, str], int, bool]] = []
    for row in preds:
        gap = _sev_gap(row)
        cat_err = row.get("true_category") != row.get("pred_category")
        if gap == 0 and not cat_err:
            continue
        split_prio = 1 if row.get("split") == "test" else 0
        # Sort priority: severity off by >= 2 first (by larger gap), then category errors
        # (larger gap first, test split first on ties), then remaining 1-level misses.
        sort_key = (
            1 if gap >= 2 else 0,
            gap if gap >= 2 else 0,
            1 if cat_err else 0,
            gap,
            split_prio,
        )
        misses.append((sort_key, row, gap, cat_err))

    misses.sort(key=lambda item: item[0], reverse=True)
    top_misses = misses[:20]
    ge2 = sum(1 for _, _, g, _ in misses if g >= 2)
    cat_errs = sum(1 for _, _, _, c in misses if c)
    print(f"TOTAL_DISAGREEMENTS={len(misses)} (sev_gap>=2: {ge2}, category_errors: {cat_errs})")
    print("=== TOP 20 LARGEST DISAGREEMENTS (sev off >=2 first, then category errors) ===")

    for idx, (_, row, gap, cat_err) in enumerate(top_misses, 1):
        key = (row["doc_id"], row["clause_id"])
        src = final_rows.get(key, {})
        print(f"--- {idx}. {row['doc_id']} {row['clause_id']} ({row.get('split', '')})")
        print(
            f"   MISS: {row['true_category']}/{row['true_severity']} -> "
            f"{row['pred_category']}/{row['pred_severity']} | sev_gap={gap} cat_err={cat_err} "
            f"rule={row.get('applied_rule', '')} num_flag={row.get('number_flag', '')}"
        )
        ctext = str(src.get("clause_text", "")).strip()
        trat = str(src.get("rationale", "")).strip()
        prat = str(row.get("pred_rationale", "")).strip()
        if ctext:
            print(f"   clause_text: {ctext[:220]}")
        if trat:
            print(f"   silver_rationale: {trat[:220]}")
        if prat:
            print(f"   pred_rationale: {prat[:220]}")


if __name__ == "__main__":
    main()
