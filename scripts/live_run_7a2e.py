"""scripts/live_run_7a2e.py

Live end-to-end execution of a brand new, un-cached loan document on Stage 7a backend.
Target document: personal_business_loan_agreement.pdf (16 pages, HDFC Bank Business Loan).
Never prints or logs GEMINI_API_KEY.
"""

from __future__ import annotations

import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from app.api.doc_bridge import load_uploaded_document
from app.api.main import app
from app.api.task_service import (
    count_today_calls_by_timezone,
    load_app_config,
)
from scripts.offline_guard import offline_guard
from src.qa.verify_quotes import verify_evidence

LOG_PATH = ROOT / "data" / "processed" / "llm_log.csv"
REPORT_DIR = ROOT / "data" / "processed" / "live_run_7a2e"
REPORT_PATH = REPORT_DIR / "report.json"
TARGET_PDF = ROOT / "data" / "raw" / "08_indian_bank_loans" / "personal_business_loan_agreement.pdf"

CHAT_QUESTIONS = [
    {
        "id": "Q1",
        "type": "fact_found",
        "question": "Who is the lender named in this agreement?",
        "expected_category": "fact",
    },
    {
        "id": "Q2",
        "type": "fact_not_found",
        "question": "What is the borrower's annual household income?",
        "expected_category": "fact",
    },
    {
        "id": "Q3",
        "type": "explain_term",
        "question": "What does 'Outstanding Balance' mean in this loan agreement?",
        "expected_category": "explain_term",
    },
]


def _count_log_rows() -> int:
    if not LOG_PATH.is_file():
        return 0
    with LOG_PATH.open("r", encoding="utf-8", errors="ignore") as fh:
        return sum(1 for _ in fh)


def _read_recent_log_entries(n: int) -> list[dict[str, str]]:
    if not LOG_PATH.is_file() or n <= 0:
        return []
    with LOG_PATH.open("r", encoding="utf-8", errors="ignore", newline="") as fh:
        rows = list(csv.DictReader(fh))
        return rows[-n:]


def _poll_doc_ready(client: TestClient, doc_id: str, timeout_s: float = 300.0) -> dict[str, Any]:
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < timeout_s:
        r = client.get(f"/api/documents/{doc_id}/status")
        if r.status_code == 200:
            st = r.json()
            if st.get("state") in ("ready", "failed"):
                return st
        time.sleep(1.0)
    raise TimeoutError(f"Doc {doc_id} ingest timed out after {timeout_s}s")


def _poll_task(client: TestClient, doc_id: str, kind: str, timeout_s: float = 300.0) -> dict[str, Any]:
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < timeout_s:
        r = client.get(f"/api/documents/{doc_id}/tasks/{kind}")
        if r.status_code == 200:
            st = r.json()
            if st.get("state") in ("done", "failed", "quota_blocked", "partial"):
                return st
        time.sleep(1.0)
    raise TimeoutError(f"Task {kind} on {doc_id} timed out after {timeout_s}s")


def run_live() -> dict[str, Any]:
    wall_start = time.perf_counter()
    print("=" * 80)
    print("STAGE 7a-2e: LIVE END-TO-END EXECUTION OF NEW LOAN DOCUMENT")
    print("=" * 80)

    # 1. Quota Pre-check
    tz_counts = count_today_calls_by_timezone()
    pt_calls = tz_counts.get("America/Los_Angeles", 0)
    print(f"Pacific-time live calls today: {pt_calls} (counts_by_tz={tz_counts})")
    if pt_calls > 20:
        print(f"ABORT: Pacific-time live calls today ({pt_calls}) exceeds safety threshold (20).")
        sys.exit(1)

    if not TARGET_PDF.is_file():
        print(f"ABORT: Target document not found at {TARGET_PDF}")
        sys.exit(1)

    rows_before = _count_log_rows()
    print(f"llm_log.csv baseline rows: {rows_before}")

    client = TestClient(app)

    # 2. Upload Document
    pdf_bytes = TARGET_PDF.read_bytes()
    print(f"\n[Step 1] Uploading {TARGET_PDF.name} ({len(pdf_bytes)} bytes)...")
    t0_up = time.perf_counter()
    r_up = client.post("/api/documents", files={"file": (TARGET_PDF.name, pdf_bytes, "application/pdf")})
    if r_up.status_code != 200:
        print(f"ABORT: Upload failed status={r_up.status_code}: {r_up.text}")
        sys.exit(1)
    doc_id = r_up.json()["doc_id"]
    st_doc = _poll_doc_ready(client, doc_id, timeout_s=300.0)
    el_up = round(time.perf_counter() - t0_up, 3)
    print(f"Document ready: doc_id={doc_id}, pages={st_doc.get('pages_total')}, elapsed={el_up}s")

    _, doc_pages = load_uploaded_document(doc_id)

    total_quotes_found = 0
    total_quotes_verified = 0

    # Helper to check run delta abort
    def _assert_safety() -> None:
        cur_delta = _count_log_rows() - rows_before
        if cur_delta > 40:
            print(f"ABORT: Mid-run new log rows delta ({cur_delta}) exceeded 40-call budget.")
            sys.exit(1)

    # 3. Summary Task
    print("\n[Step 2] Triggering Summary Task...")
    t0_sum = time.perf_counter()
    r_sum_post = client.post(f"/api/documents/{doc_id}/tasks/summary")
    st_sum = _poll_task(client, doc_id, "summary", timeout_s=300.0)
    el_sum = round(time.perf_counter() - t0_sum, 3)
    _assert_safety()

    sum_res = st_sum.get("result") or {}
    sum_sents = list(sum_res.get("sentences", []))
    sum_kept = [s for s in sum_sents if s.get("status") == "kept"]
    sum_words = sum_res.get("short_word_count", 0)
    print(
        f"Summary: state={st_sum.get('state')}, elapsed={el_sum}s, live_calls={st_sum.get('live_calls')}, "
        f"models_used={st_sum.get('models_used')}, kept_sentences={len(sum_kept)}, short_words={sum_words}"
    )
    print(f"Summary notice: {st_sum.get('notice')}")

    # 4. Key-Info Task
    print("\n[Step 3] Triggering Key-Info Task...")
    t0_ki = time.perf_counter()
    r_ki_post = client.post(f"/api/documents/{doc_id}/tasks/keyinfo")
    st_ki = _poll_task(client, doc_id, "keyinfo", timeout_s=300.0)
    el_ki = round(time.perf_counter() - t0_ki, 3)
    _assert_safety()

    ki_res = st_ki.get("result") or {}
    ki_fields = list(ki_res.get("fields", []))
    ki_quotes: list[dict[str, Any]] = []
    for f in ki_fields:
        for ev in f.get("evidence", []):
            ki_quotes.append(ev)
    v_ki, d_ki = verify_evidence(doc_pages, ki_quotes)
    total_quotes_found += len(ki_quotes)
    total_quotes_verified += len(v_ki)
    print(
        f"Key-Info: state={st_ki.get('state')}, elapsed={el_ki}s, live_calls={st_ki.get('live_calls')}, "
        f"models_used={st_ki.get('models_used')}, counts={ki_res.get('counts')}"
    )
    print(f"Key-Info quotes verified: {len(v_ki)}/{len(ki_quotes)}")
    print(f"Key-Info notice: {st_ki.get('notice')}")

    # 5. Risk Task
    print("\n[Step 4] Triggering Risk Task...")
    t0_rk = time.perf_counter()
    r_rk_post = client.post(f"/api/documents/{doc_id}/tasks/risk")
    st_rk = _poll_task(client, doc_id, "risk", timeout_s=300.0)
    el_rk = round(time.perf_counter() - t0_rk, 3)
    _assert_safety()

    rk_res = st_rk.get("result") or {}
    rk_score = rk_res.get("score")
    rk_level = rk_res.get("level")
    rk_flagged = list(rk_res.get("flagged_clauses", []))
    rk_dropped = rk_res.get("dropped_clauses_count", 0)
    rk_strength = rk_res.get("evidence_strength")

    rk_quotes: list[dict[str, Any]] = []
    for c in rk_flagged:
        q_txt = c.get("quote", "")
        pg = c.get("page", 1)
        if q_txt:
            rk_quotes.append({"quote": q_txt, "page": pg})
    v_rk, d_rk = verify_evidence(doc_pages, rk_quotes)
    total_quotes_found += len(rk_quotes)
    total_quotes_verified += len(v_rk)
    print(
        f"Risk: state={st_rk.get('state')}, elapsed={el_rk}s, live_calls={st_rk.get('live_calls')}, "
        f"models_used={st_rk.get('models_used')}, score={rk_score}, level={rk_level}, "
        f"flagged={len(rk_flagged)}, dropped={rk_dropped}, evidence_strength={rk_strength}"
    )
    print(f"Risk quotes verified: {len(v_rk)}/{len(rk_quotes)}")
    print(f"Risk labels: {rk_res.get('labels')}")

    # 6. Chat Questions (3 questions)
    print("\n[Step 5] Running 3 Chat Questions...")
    chat_results = []
    for q_spec in CHAT_QUESTIONS:
        t0_q = time.perf_counter()
        r_q = client.post(
            f"/api/documents/{doc_id}/chat",
            json={"question": q_spec["question"]},
        )
        el_q = round(time.perf_counter() - t0_q, 3)
        _assert_safety()
        q_body = r_q.json() if r_q.status_code == 200 else {}
        q_ev = list(q_body.get("evidence", []))
        v_q, d_q = verify_evidence(doc_pages, q_ev)
        total_quotes_found += len(q_ev)
        total_quotes_verified += len(v_q)

        fallback = bool(q_body.get("fallback_used") or "model_fallback" in (q_body.get("flags") or []))
        q_rec = {
            "id": q_spec["id"],
            "type": q_spec["type"],
            "question": q_spec["question"],
            "status_code": r_q.status_code,
            "status": q_body.get("status"),
            "category": q_body.get("category"),
            "answer_preview": (q_body.get("answer") or "")[:120],
            "quotes_count": len(q_ev),
            "quotes_verified": len(v_q),
            "model_used": q_body.get("model_used"),
            "fallback_used": fallback,
            "elapsed_s": el_q,
        }
        chat_results.append(q_rec)
        print(
            f"Chat {q_spec['id']} ({q_spec['type']}): category={q_body.get('category')}, status={q_body.get('status')}, "
            f"quotes={len(v_q)}/{len(q_ev)}, model={q_body.get('model_used')}, fallback={fallback}, elapsed={el_q}s"
        )

    wall_total = round(time.perf_counter() - wall_start, 3)
    rows_after = _count_log_rows()
    live_delta = rows_after - rows_before
    new_rows = _read_recent_log_entries(live_delta)

    models_breakdown: dict[str, int] = {}
    for r in new_rows:
        m = r.get("model", "unknown")
        models_breakdown[m] = models_breakdown.get(m, 0) + 1

    print("\n" + "=" * 80)
    print("LIVE RUN SUMMARY & LOG TOTALS")
    print("=" * 80)
    print(f"Total wall time: {wall_total}s")
    print(f"llm_log.csv rows: {rows_before} -> {rows_after} (delta = {live_delta})")
    print(f"New rows per model: {models_breakdown}")

    # 7. Re-run Whole Flow Under offline_guard
    print("\n[Step 6] Re-running complete flow under offline_guard to verify 100% cache replay...")
    with offline_guard() as guard:
        # Repeat summary
        r_sum_rep = client.post(f"/api/documents/{doc_id}/tasks/summary")
        # Repeat keyinfo
        r_ki_rep = client.post(f"/api/documents/{doc_id}/tasks/keyinfo")
        # Repeat risk
        r_rk_rep = client.post(f"/api/documents/{doc_id}/tasks/risk")
        # Repeat chat
        for q_spec in CHAT_QUESTIONS:
            client.post(f"/api/documents/{doc_id}/chat", json={"question": q_spec["question"]})

    print(f"Offline guard intercepted attempts: {guard.attempts} (expected: 0)")
    cached_replay_pass = (guard.attempts == 0)

    # Verification target
    quote_pct = (total_quotes_verified / total_quotes_found * 100.0) if total_quotes_found else 100.0
    target_met = quote_pct >= 99.0
    print(
        f"Quotes verified total: {total_quotes_verified}/{total_quotes_found} ({quote_pct:.1f}%) "
        f"-> {'TARGET MET' if target_met else 'TARGET MISSED'}"
    )

    # 8. Save Report (key-free)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "doc_id": doc_id,
        "document": TARGET_PDF.name,
        "pages": st_doc.get("pages_total"),
        "wall_time_s": wall_total,
        "llm_log": {
            "before": rows_before,
            "after": rows_after,
            "delta": live_delta,
            "models_breakdown": models_breakdown,
        },
        "tasks": {
            "summary": {
                "state": st_sum.get("state"),
                "elapsed_s": el_sum,
                "live_calls": st_sum.get("live_calls"),
                "models_used": st_sum.get("models_used"),
                "kept_sentences": len(sum_kept),
                "short_words": sum_words,
            },
            "keyinfo": {
                "state": st_ki.get("state"),
                "elapsed_s": el_ki,
                "live_calls": st_ki.get("live_calls"),
                "models_used": st_ki.get("models_used"),
                "quotes_verified": len(v_ki),
                "quotes_total": len(ki_quotes),
            },
            "risk": {
                "state": st_rk.get("state"),
                "elapsed_s": el_rk,
                "live_calls": st_rk.get("live_calls"),
                "models_used": st_rk.get("models_used"),
                "score": rk_score,
                "level": rk_level,
                "flagged": len(rk_flagged),
                "dropped": rk_dropped,
                "quotes_verified": len(v_rk),
                "quotes_total": len(rk_quotes),
            },
            "chat": chat_results,
        },
        "offline_repeat": {
            "offline_attempts": guard.attempts,
            "cached_replay_pass": cached_replay_pass,
        },
        "quotes_verification": {
            "total_found": total_quotes_found,
            "total_verified": total_quotes_verified,
            "percentage": round(quote_pct, 2),
            "target_met": target_met,
        },
    }

    REPORT_PATH.write_text(json.dumps(report_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Report saved to: {REPORT_PATH}")
    return report_data


if __name__ == "__main__":
    run_live()
