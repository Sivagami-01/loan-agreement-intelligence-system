"""scripts/demo_7a2b.py

CLI demo for Stage 7a-2b risk analysis and chat endpoints.
Usage:
  python -X utf8 scripts/demo_7a2b.py <doc_id> [--question "..."]
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.api.main import app  # noqa: E402


def _poll_risk(client: TestClient, doc_id: str, timeout_s: float = 120.0) -> dict[str, Any]:
    t0 = time.perf_counter()
    while time.perf_counter() - t0 <= timeout_s:
        r = client.get(f"/api/documents/{doc_id}/tasks/risk")
        if r.status_code == 200:
            body = r.json()
            if body.get("state") in ("done", "failed", "partial", "quota_blocked"):
                return body
        time.sleep(0.25)
    return {"state": "timeout"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage 7a-2b risk & chat demo")
    parser.add_argument("doc_id", help="12-hex uploaded doc_id (e.g. 893857f8b7e3)")
    parser.add_argument(
        "--question",
        default="What collateral or security is deposited for this facility?",
        help="Question to ask via POST /api/documents/{doc_id}/chat",
    )
    args = parser.parse_args()

    client = TestClient(app)

    r_post = client.post(f"/api/documents/{args.doc_id}/tasks/risk")
    if r_post.status_code not in (200, 202):
        print(f"Risk POST failed ({r_post.status_code}): {r_post.text}")
        return 1

    task = r_post.json() if r_post.status_code == 200 else _poll_risk(client, args.doc_id)
    print("=== RISK RESULT ===")
    print(f"State: {task.get('state')} | live_calls={task.get('live_calls')} | models_used={task.get('models_used')}")
    if task.get("state") != "done" or not isinstance(task.get("result"), dict):
        print(f"Message/Error: {task.get('error')}")
    else:
        res = task["result"]
        print(f"Labels: {res.get('labels')}")
        print(f"Score: {res.get('score')}/100 | Level: {res.get('level')} | Sample range: {res.get('sample_range')}")
        print(f"Level note: {res.get('level_explanation')}")
        print(f"Display note: {res.get('display_note')}")
        print("Breakdown:")
        for c in res.get("categories", []):
            print(
                f"  - {c['name']}: contrib={c['points_contributed']:.2f} "
                f"(weight={c['weight']}, n={c['n_clauses']}, strength={c['evidence_strength']})"
            )
        print("Top 5 clauses:")
        for idx, d in enumerate(res.get("top_drivers", [])[:5], 1):
            snippet = " ".join(str(d.get("quote", "")).split())[:110]
            print(
                f"  {idx}. [{d.get('severity')} | p.{d.get('page')}] {d.get('category')} "
                f"({d.get('contribution')} pts): {snippet}..."
            )

    print("\n=== CHAT RESULT ===")
    r_chat = client.post(f"/api/documents/{args.doc_id}/chat", json={"question": args.question})
    if r_chat.status_code != 200:
        print(f"Chat failed ({r_chat.status_code}): {r_chat.text}")
        return 1
    chat = r_chat.json()
    print(
        f"Question: {args.question}\n"
        f"Category: {chat.get('category')} | Status: {chat.get('status')} | "
        f"Model: {chat.get('model_used')} | Live calls: {chat.get('live_calls')}\n"
        f"Answer: {chat.get('answer')}"
    )
    for idx, ev in enumerate(chat.get("evidence", []), 1):
        print(f"  Quote {idx} [p.{ev.get('page')}]: {ev.get('quote')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
