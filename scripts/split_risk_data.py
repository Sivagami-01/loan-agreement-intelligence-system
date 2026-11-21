"""scripts/split_risk_data.py

Step 1 (Stage 4a): Creates document-level split data/processed/risk_split.csv
(doc_id, split, n_clauses) from data/processed/labels/llm_assisted/risk_final.csv
and prints category and severity counts per split.
"""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINAL_CSV = ROOT / "data" / "processed" / "labels" / "llm_assisted" / "risk_final.csv"
SPLIT_CSV = ROOT / "data" / "processed" / "risk_split.csv"

CATEGORIES = [
    "Financial terms",
    "Repayment",
    "Penalties and charges",
    "Collateral",
    "Default conditions",
    "Termination",
    "Covenants",
]
SEVERITIES = ["Low", "Medium", "High", "Critical"]


def is_indian_mitc(doc_id: str) -> bool:
    return "/" not in doc_id and "\\" not in doc_id


def build_split() -> dict[str, str]:
    with FINAL_CSV.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))

    doc_counts = Counter(r["doc_id"] for r in rows)
    sorted_docs = sorted(doc_counts.keys())
    assert len(sorted_docs) == 13, f"Expected 13 documents, got {len(sorted_docs)}"

    # Positions 3, 6, 9, 12 (1-based) -> 0-based indices 2, 5, 8, 11
    test_docs = {doc for idx, doc in enumerate(sorted_docs, start=1) if idx % 3 == 0}
    if not any(is_indian_mitc(d) for d in test_docs):
        # Deterministic fallback swap if no Indian MITC landed in test
        indian_docs = [d for d in sorted_docs if is_indian_mitc(d)]
        swap_out = sorted(test_docs)[-1]
        test_docs.remove(swap_out)
        test_docs.add(indian_docs[0])

    split_map = {doc: ("test" if doc in test_docs else "dev") for doc in sorted_docs}

    SPLIT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with SPLIT_CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["doc_id", "split", "n_clauses"])
        w.writeheader()
        for doc in sorted_docs:
            w.writerow({"doc_id": doc, "split": split_map[doc], "n_clauses": doc_counts[doc]})

    return split_map


def main() -> None:
    split_map = build_split()
    with FINAL_CSV.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))

    print(f"Wrote split map to {SPLIT_CSV.relative_to(ROOT)}:")
    for split_name in ("dev", "test"):
        s_docs = [d for d, sp in split_map.items() if sp == split_name]
        s_rows = [r for r in rows if split_map[r["doc_id"]] == split_name]
        cat_c = Counter(r["final_category"] for r in s_rows)
        sev_c = Counter(r["final_severity"] for r in s_rows)
        print(f"\n=== {split_name.upper()} ({len(s_docs)} docs, {len(s_rows)} clauses) ===")
        for d in s_docs:
            print(f"  - {d} ({sum(1 for r in s_rows if r['doc_id']==d)})")
        print("  Categories:", {c: cat_c[c] for c in CATEGORIES})
        print("  Severities:", {s: sev_c[s] for s in SEVERITIES})


if __name__ == "__main__":
    main()
