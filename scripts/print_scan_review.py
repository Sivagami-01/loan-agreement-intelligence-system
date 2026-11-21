"""scripts/print_scan_review.py

Prints unlabeled risk clauses flagged by whole-document scan from a review CSV
(default: data/processed/risk_scan_review.csv; accepts optional CSV path argument).
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REVIEW_CSV = ROOT / "data" / "processed" / "risk_scan_review.csv"


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Print scan review CSV clauses cleanly")
    parser.add_argument(
        "review_file",
        nargs="?",
        default=str(DEFAULT_REVIEW_CSV),
        help="Path to review CSV (default: data/processed/risk_scan_review.csv)",
    )
    args = parser.parse_args()
    review_path = Path(args.review_file)
    if not review_path.is_absolute():
        review_path = ROOT / review_path

    if not review_path.is_file():
        print(f"Missing review file: {review_path}")
        return

    with review_path.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))

    high_crit = sum(1 for r in rows if r.get("severity") in {"High", "Critical"})
    med_low = sum(1 for r in rows if r.get("severity") in {"Medium", "Low"})
    try:
        rel_src = review_path.relative_to(ROOT)
    except ValueError:
        rel_src = review_path
    print(f"Scan Unlabeled Flagged Clauses for Human Review: {len(rows)} rows (High/Critical={high_crit}, Medium/Low={med_low})")
    print(f"Source: {rel_src} (silver/classifier-predicted; NOT human gold)\n")

    for i, r in enumerate(rows, 1):
        verdict = (r.get("reviewer_verdict") or "").strip() or "PENDING"
        print(
            f"--- {i}. {r['doc_id']} {r['clause_id']} [page {r['page']}] | "
            f"{r['category']} / {r['severity']} | verdict={verdict} ---"
        )
        text = " ".join((r.get("clause_text") or "").split())
        if len(text) > 500:
            text = text[:497] + "..."
        print(f"  CLAUSE   : {text}")
        print(f"  RATIONALE: {r.get('rationale', '')}")


if __name__ == "__main__":
    main()
