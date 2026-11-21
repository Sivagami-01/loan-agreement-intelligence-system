"""scripts/demo_retrieval.py

CLI Demo for BM25 Chunk Retrieval and Retrieval-Backed QA (Stage 2c-2a).
Usage:
    python scripts/demo_retrieval.py <doc_id> "<question>"
    python scripts/demo_retrieval.py <doc_id> "<question>" --answer

Examples:
    python scripts/demo_retrieval.py 13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi "बैंक हॉलिडे के कारण पेमेंट क्रेडिट होने में T+ कितने दिनों से अधिक का समय लग सकता है?"
    python scripts/demo_retrieval.py 03_dbs_mitc "Are prepayment or foreclosure charges levied on floating interest rate loans?" --answer
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.qa.answer import answer_question
from src.qa.retrieve import load_retrieval_config, retrieve


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    cfg = load_retrieval_config()
    parser = argparse.ArgumentParser(description="Inspect BM25 retrieval chunks (and optionally answer)")
    parser.add_argument("doc_id", type=str, help="Document ID or filename")
    parser.add_argument("question", type=str, help="Question to search")
    parser.add_argument("--top-k", type=int, default=int(cfg.get("top_k", 8)), help="Number of chunks to retrieve")
    parser.add_argument("--answer", action="store_true", help="Also run answer_question(force_retrieval=True)")
    args = parser.parse_args()

    print("=" * 80)
    print("BM25 RETRIEVAL DEMO (STAGE 2c-2a)")
    print("=" * 80)
    print(f"Document ID: {args.doc_id}")
    print(f"Question:    {args.question}")
    print(f"Top-K:       {args.top_k}")
    print("-" * 80)

    chunks = retrieve(args.doc_id, args.question, top_k=args.top_k)
    if not chunks:
        print("No matching chunks found (or document empty/missing).")
    else:
        for ch in chunks:
            preview = " ".join(ch["text"].split())[:260]
            print(
                f"[Rank {ch['rank']}] Page {ch['page']} | Score: {ch['score']:.4f} | "
                f"Len: {len(ch['text'])} chars | ID: {ch['chunk_id']}"
            )
            print(f"         {preview}...")
            print()

    if args.answer:
        print("=" * 80)
        print("RETRIEVAL-BACKED QA ANSWER (force_retrieval=True)")
        print("=" * 80)
        res = answer_question(args.doc_id, args.question, force_retrieval=True)
        print(f"Status:          {res.get('status', '').upper()}")
        print(f"Model Used:      {res.get('model_used')}")
        print(f"Retrieval Used:  {res.get('retrieval_used')}")
        print(f"Retrieved Pages: {res.get('retrieved_pages')}")
        print(f"Answer:          {res.get('answer') or '(No answer presented)'}")
        print("-" * 80)
        evidence = res.get("evidence", [])
        print(f"Verified Evidence ({len(evidence)}):")
        for idx, ev in enumerate(evidence, 1):
            orig = ev.get("original_page")
            note = f" [Page corrected from {orig}]" if orig and orig != ev.get("page") else ""
            print(f"  [{idx}] Page {ev.get('page')}{note}: \"{ev.get('quote')}\"")
        if res.get("flags"):
            print(f"Flags:           {', '.join(res['flags'])}")
        print("=" * 80)


if __name__ == "__main__":
    main()
