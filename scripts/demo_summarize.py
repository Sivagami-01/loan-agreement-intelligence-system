"""scripts/demo_summarize.py

CLI demo for Stage 3b plain-English grounded summarization.
Usage: python scripts/demo_summarize.py <doc_id>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.summarize.summarize import summarize_document


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Generate grounded short and detailed summaries.")
    parser.add_argument("doc_id", help="Ingested document ID (stem in data/processed/ingested)")
    args = parser.parse_args()

    res = summarize_document(args.doc_id)
    print(f"\nDocument: {res['doc_id']}")
    print(f"Model: {res['model_used']} | Short words: {res['short_word_count']}")
    print("\n=== SHORT SUMMARY ===")
    print(res["short"] or "(No kept short sentences)")

    print("\n=== DETAILED SUMMARY ===")
    print(res["detailed"])

    dropped = [s for s in res["sentences"] if s["status"] != "kept"]
    print(f"\n=== DROPPED SENTENCES ({len(dropped)}) ===")
    if not dropped:
        print("None.")
    else:
        for d in dropped:
            print(f"- [{d['section']}] ({d['status']}) {d['text']} | missing={d['numbers_checked'].get('missing')}")

    print(f"\n=== FLAGS ({len(res['flags'])}) ===")
    print(res["flags"] if res["flags"] else "None.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
