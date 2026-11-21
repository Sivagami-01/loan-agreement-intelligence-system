"""scripts/demo_qa.py

CLI Demo for Single-Prompt QA with Quote Verification.
Usage:
    python scripts/demo_qa.py <doc_id> "<question>"

Example:
    python scripts/demo_qa.py 03_dbs_mitc "What is the purpose of the gold loan?"
    python scripts/demo_qa.py 0000027430-25-000005_aesohio10qex10120250630q2 "Who are the parties to this amendment?"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.qa.answer import answer_question


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Ask a question against an ingested document")
    parser.add_argument("doc_id", type=str, help="Document ID or filename (e.g. 03_dbs_mitc)")
    parser.add_argument("question", type=str, help="Question to ask")
    parser.add_argument("--verify", action="store_true", help="Run second-model & numeric verifier pass")
    args = parser.parse_args()

    print("=" * 80)
    print("LOAN AGREEMENT QA DEMO (SINGLE-PROMPT WITH VERBATIM VERIFICATION)")
    print("=" * 80)
    print(f"Document ID: {args.doc_id}")
    print(f"Question:    {args.question}")
    print("-" * 80)

    res = answer_question(args.doc_id, args.question, verify=args.verify)

    status = res.get("status", "unknown")
    answer = res.get("answer", "")
    evidence = res.get("evidence", [])
    flags = res.get("flags", [])

    print(f"Status:      {status.upper()}")
    print(f"Model Used:  {res.get('model_used')}")
    print(f"Answer:      {answer if answer else '(No answer presented)'}")
    print("-" * 80)
    print(f"Verified Evidence Quotes ({len(evidence)}):")
    if evidence:
        for idx, item in enumerate(evidence, 1):
            page = item.get("page", "?")
            quote = item.get("quote", "")
            orig = item.get("original_page")
            corrected_note = f" [Page corrected from {orig}]" if orig and orig != page else ""
            print(f"  [{idx}] Page {page}{corrected_note}:")
            print(f"      \"{quote}\"")
    else:
        print("  (None)")

    if args.verify and status == "ok":
        print("-" * 80)
        print("Second-Model & Numeric Verifier:")
        print(f"  Final Check:          {res.get('final_check')}")
        print(f"  Verifier Verdict:     {res.get('verifier_verdict')}")
        print(f"  Verifier Model Used:  {res.get('verifier_model_used')}")
        print(f"  Verifier Independent: {res.get('verifier_independent')}")
        print(f"  Verifier Reason:      {res.get('verifier_reason')}")

    if flags:
        print("-" * 80)
        print(f"Flags:       {', '.join(flags)}")
    print("=" * 80)


if __name__ == "__main__":
    main()
