"""scripts/demo_ask.py

CLI Demo for the Question Router & Unified ask() Pipeline (Stage 2d).
Usage:
    python scripts/demo_ask.py <doc_id> "<question>"

Examples:
    python scripts/demo_ask.py 03_dbs_mitc "Are there prepayment charges on floating interest loans?"
    python scripts/demo_ask.py 03_dbs_mitc "What does foreclosure mean?"
    python scripts/demo_ask.py 03_dbs_mitc "Calculate my monthly EMI on Rs. 500000 at 9% for 24 months"
    python scripts/demo_ask.py 03_dbs_mitc "Should I sign this gold loan agreement?"
    python scripts/demo_ask.py 03_dbs_mitc "What is the weather in Mumbai today?"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.qa.ask import ask


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Ask any question via the Stage 2d router")
    parser.add_argument("doc_id", type=str, help="Document ID or filename (e.g. 03_dbs_mitc)")
    parser.add_argument("question", type=str, help="Question to route and answer")
    parser.add_argument("--no-verify", action="store_true", help="Skip second-model verifier on fact questions")
    args = parser.parse_args()

    print("=" * 80)
    print("UNIFIED ROUTED QA DEMO (STAGE 2d)")
    print("=" * 80)
    print(f"Document ID: {args.doc_id}")
    print(f"Question:    {args.question}")
    print("-" * 80)

    res = ask(args.doc_id, args.question, verify=not args.no_verify)

    print(f"Category:        {res.get('category')}")
    print(f"Status:          {res.get('status')}")
    print(f"Language:        {res.get('language')}")
    print(f"Rule-Based:      {res.get('rule_based_route')}")
    print(f"Router Fallback: {res.get('router_fallback')}")
    print(f"Model Used:      {res.get('model_used')}")
    print("-" * 80)
    print("Answer:")
    print(res.get("answer") or "(No answer presented)")
    print("-" * 80)

    evidence = res.get("evidence", [])
    print(f"Verified Evidence ({len(evidence)}):")
    for idx, ev in enumerate(evidence, 1):
        print(f"  [{idx}] Page {ev.get('page')}: \"{ev.get('quote')}\"")

    if "final_check" in res:
        print("-" * 80)
        print(
            f"Verifier: final_check={res.get('final_check')}, "
            f"verdict={res.get('verifier_verdict')}, "
            f"model={res.get('verifier_model_used')}, "
            f"independent={res.get('verifier_independent')}"
        )
    print("=" * 80)


if __name__ == "__main__":
    main()
