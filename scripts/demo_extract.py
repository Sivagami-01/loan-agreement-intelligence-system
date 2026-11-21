"""scripts/demo_extract.py

CLI demo for Stage 3a key-information extraction.
Usage: python scripts/demo_extract.py <doc_id> [--verify-numeric]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.extract.extract_fields import extract_key_info


def _truncate(text: str, limit: int = 72) -> str:
    clean = " ".join(str(text).split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 3] + "..."


def print_extraction_table(result: dict) -> None:
    """Prints field | value | page | status table plus extraction summary."""
    print(f"\nDocument: {result['doc_id']}")
    print(
        f"Chars: {result['doc_chars']} | Pages: {result['num_pages']} | "
        f"Mode: {'retrieval' if result['retrieval_used'] else 'whole-doc'} | "
        f"Model: {result['model_used']}"
    )
    print(
        f"Verified quotes kept: {result['verified_quotes_total']}/{result['raw_quotes_total']} "
        f"(dropped={result['dropped_quotes_total']}) | "
        f"Verifier independent: {result['verifier_independent']}"
    )
    print("-" * 118)
    print(f"{'field':<33} | {'value':<60} | {'page':<6} | {'status'}")
    print("-" * 118)
    for row in result["fields"]:
        pages = sorted({str(e["page"]) for e in row["evidence"] if e.get("page") is not None})
        page_str = ",".join(pages) if pages else "-"
        val_display = row["value"] if row["value"] else "<DROPPED/UNVERIFIED>"
        print(f"{row['field']:<33} | {_truncate(val_display, 60):<60} | {page_str:<6} | {row['status']}")
    print("-" * 118)
    c = result["counts"]
    print(
        f"Summary counts: verified={c['verified']}, not_found={c['not_found']}, "
        f"unverified={c['unverified']}, needs_review={c['needs_review']}\n"
    )


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Extract 16 key loan fields from a document.")
    parser.add_argument("doc_id", help="Ingested document ID (stem of file in data/processed/ingested)")
    parser.add_argument(
        "--verify-numeric",
        action="store_true",
        help="Also run cross-model verify_answer on extracted numeric fields.",
    )
    args = parser.parse_args()

    result = extract_key_info(args.doc_id, verify_numeric=args.verify_numeric)
    print_extraction_table(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
