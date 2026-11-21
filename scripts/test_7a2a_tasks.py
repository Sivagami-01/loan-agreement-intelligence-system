"""scripts/test_7a2a_tasks.py

Verification suite for Stage 7a-2a (summary and keyinfo task endpoints).
Prints T1-T9 PASS/FAIL/INFO/INCONCLUSIVE plus TARGET MET/TARGET MISSED lines,
and finishes with:
  llm_log rows: <before> -> <after> (live calls = <n>)
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.api import jobs, task_service  # noqa: E402
from app.api.doc_bridge import load_uploaded_document  # noqa: E402
from app.api.main import app  # noqa: E402
from scripts.offline_guard import offline_guard  # noqa: E402
from src.llm.gemini_client import get_api_key  # noqa: E402
from src.qa.verify_quotes import verify_evidence  # noqa: E402

LLM_LOG_PATH = ROOT / "data" / "processed" / "llm_log.csv"
RAW_DBS_PDF = ROOT / "data" / "raw" / "08_indian_bank_loans" / "03_dbs_mitc.pdf"
EXPECTED_DBS_DOC_ID = hashlib.sha256(RAW_DBS_PDF.read_bytes()).hexdigest()[:12]

ALLOWED_KEYINFO_STATUSES = {
    "verified",
    "needs_review",
    "not_found",
    "deferred_to_other_document",
    "unverified",
}
CITE_RE = re.compile(r"\[p\.\s*\d+(?:\s*,\s*(?:p\.\s*)?\d+)*\]", re.IGNORECASE)


def _emit(tid: str, status: str, detail: str) -> None:
    print(f"{tid} {status} | {detail}", flush=True)


def _count_llm_log_rows() -> int:
    if not LLM_LOG_PATH.is_file():
        return 0
    with LLM_LOG_PATH.open("r", encoding="utf-8", errors="ignore") as fh:
        return sum(1 for _ in fh)


def _is_safe_body(text: str, api_key: str) -> bool:
    if api_key and api_key in text:
        return False
    lowered = text.lower()
    if str(ROOT).lower() in lowered or "c:\\" in lowered or "traceback" in lowered:
        return False
    return True


def _poll_doc_ready(client: TestClient, doc_id: str, timeout_s: float = 60.0) -> dict[str, Any]:
    t0 = time.perf_counter()
    while True:
        r = client.get(f"/api/documents/{doc_id}/status")
        if r.status_code == 200:
            st = r.json()
            if st.get("state") in ("ready", "failed"):
                return st
        if time.perf_counter() - t0 > timeout_s:
            return {"state": "timeout"}
        time.sleep(0.2)


def _poll_task_done(client: TestClient, doc_id: str, kind: str, timeout_s: float = 120.0) -> dict[str, Any]:
    t0 = time.perf_counter()
    while True:
        r = client.get(f"/api/documents/{doc_id}/tasks/{kind}")
        if r.status_code == 200:
            st = r.json()
            if st.get("state") in ("done", "failed", "partial", "quota_blocked"):
                return st
        if time.perf_counter() - t0 > timeout_s:
            return {"state": "timeout"}
        time.sleep(0.25)


def run_t1_key_leak_scan(api_key: str) -> tuple[str, str]:
    key_bytes = api_key.encode("utf-8")
    scanned = 0
    leaks: list[str] = []
    for rel_dir in ("data/processed", "scripts", "src", "config", "docs", "app"):
        base = ROOT / rel_dir
        if not base.is_dir():
            continue
        for p in base.rglob("*"):
            if not p.is_file():
                continue
            scanned += 1
            try:
                if key_bytes in p.read_bytes():
                    leaks.append(str(p.relative_to(ROOT)))
            except OSError:
                continue
    return (
        "PASS" if not leaks else "FAIL",
        f"Scanned {scanned} files across data/processed, scripts, src, config, docs, app; {len(leaks)} leaks",
    )


def _clear_doc_results(doc_id: str) -> None:
    res_dir = jobs.get_doc_dir(doc_id) / "results"
    if res_dir.exists():
        shutil.rmtree(res_dir, ignore_errors=True)
    task_service.reset_in_memory_task_cache()


def run_t2_summary(client: TestClient) -> tuple[str, str, dict[str, Any]]:
    _clear_doc_results(EXPECTED_DBS_DOC_ID)

    with RAW_DBS_PDF.open("rb") as fh:
        r_up = client.post(
            "/api/documents",
            files={"file": (RAW_DBS_PDF.name, fh.read(), "application/pdf")},
        )
    if r_up.status_code >= 300:
        return "FAIL", f"upload status={r_up.status_code}", {}
    up_json = r_up.json()
    doc_id = up_json.get("doc_id", "")
    if doc_id != EXPECTED_DBS_DOC_ID:
        return "FAIL", f"unexpected doc_id={doc_id} != {EXPECTED_DBS_DOC_ID}", {}

    doc_st = _poll_doc_ready(client, doc_id, timeout_s=60.0)
    if doc_st.get("state") != "ready":
        return "FAIL", f"doc not ready: {doc_st}", {}

    t0 = time.perf_counter()
    with offline_guard() as guard:
        r_post = client.post(f"/api/documents/{doc_id}/tasks/summary")
        if r_post.status_code not in (200, 202):
            return "FAIL", f"POST summary status={r_post.status_code}: {r_post.text}", {}
        st = _poll_task_done(client, doc_id, "summary", timeout_s=120.0)
    elapsed = round(time.perf_counter() - t0, 3)

    live_calls = int(st.get("live_calls", 0))
    models_used = st.get("models_used", {})
    if live_calls > 0:
        print(f"T2 INFO | cache miss (live_calls={live_calls}, models_used={models_used})", flush=True)

    ok = (
        guard.attempts == 0
        and st.get("state") == "done"
        and live_calls == 0
        and isinstance(st.get("result"), dict)
        and bool(st["result"].get("short"))
        and bool(st["result"].get("detailed"))
        and bool(models_used)
    )
    return (
        "PASS" if ok else "FAIL",
        f"doc_id={doc_id}, state={st.get('state')}, live_calls={live_calls}, "
        f"offline_attempts={guard.attempts}, models_used={models_used}, elapsed_s={elapsed}",
        st,
    )


def run_t3_keyinfo(client: TestClient, doc_id: str) -> tuple[str, str, dict[str, Any]]:
    t0 = time.perf_counter()
    with offline_guard() as guard:
        r_post = client.post(f"/api/documents/{doc_id}/tasks/keyinfo")
        if r_post.status_code not in (200, 202):
            return "FAIL", f"POST keyinfo status={r_post.status_code}: {r_post.text}", {}
        st = _poll_task_done(client, doc_id, "keyinfo", timeout_s=120.0)
    elapsed = round(time.perf_counter() - t0, 3)

    if guard.attempts > 0 or st.get("state") != "done" or not isinstance(st.get("result"), dict):
        return (
            "FAIL",
            f"state={st.get('state')}, offline_attempts={guard.attempts}, "
            f"attempted_models={guard.attempted_models}, error={st.get('error')}",
            st,
        )

    res = st["result"]
    fields = res.get("fields", [])
    live_calls = int(st.get("live_calls", 0))
    models_used = st.get("models_used", {})
    counts = res.get("counts", {})

    _, doc_pages = load_uploaded_document(doc_id)
    total_quotes = 0
    verified_quotes = 0
    for f in fields:
        ev = list(f.get("evidence", []))
        total_quotes += len(ev)
        v_ev, _ = verify_evidence(doc_pages, ev)
        verified_quotes += len(v_ev)

    statuses_valid = all(f.get("status") in ALLOWED_KEYINFO_STATUSES for f in fields)
    has_required_keys = all(
        "status" in f and "value" in f and "quotes" in f and "page" in f and "flags" in f
        and "model_used" in f and "verifier_independent" in f
        for f in fields
    )

    ok = (
        guard.attempts == 0
        and len(fields) == 16
        and statuses_valid
        and has_required_keys
        and live_calls == 0
        and total_quotes == verified_quotes
    )
    target_ok = (total_quotes == 0) or (verified_quotes == total_quotes)
    target_line = "TARGET MET" if target_ok else "TARGET MISSED"
    print(f"T3 {target_line} | quotes verified {verified_quotes}/{total_quotes}", flush=True)

    return (
        "PASS" if ok else "FAIL",
        f"fields={len(fields)}, counts={counts}, quotes verified {verified_quotes}/{total_quotes}, "
        f"live_calls={live_calls}, offline_attempts={guard.attempts}, models_used={models_used}, elapsed_s={elapsed}",
        st,
    )


def run_t4_summary_cites(summary_task: dict[str, Any], doc_id: str) -> tuple[str, str]:
    res = summary_task.get("result") or {}
    sentences = list(res.get("sentences", []))
    kept = [s for s in sentences if s.get("status") == "kept"]
    _, doc_pages = load_uploaded_document(doc_id)
    page_count = len(doc_pages)
    valid_pages = set(range(1, page_count + 1))

    cited_ok = 0
    range_ok = 0
    for s in kept:
        txt = str(s.get("text", ""))
        pages = [int(p) for p in s.get("pages", [])]
        if CITE_RE.search(txt) and len(pages) > 0:
            cited_ok += 1
        if pages and all(p in valid_pages for p in pages):
            range_ok += 1

    ok = len(kept) > 0 and cited_ok == len(kept) and range_ok == len(kept)
    return (
        "PASS" if ok else "FAIL",
        f"kept_sentences={len(kept)}, with_pN_cite={cited_ok}/{len(kept)}, "
        f"within_1..{page_count}={range_ok}/{len(kept)}, short_words={res.get('short_word_count')}",
    )


def run_t5_quota_guard(client: TestClient) -> tuple[str, str]:
    sample_bytes = b"DBS Bank Loan Agreement\nLoan amount is Rs. 500,000 for 24 months.\n"
    quota_doc_id = hashlib.sha256(sample_bytes).hexdigest()[:12]
    quota_dir = jobs.get_doc_dir(quota_doc_id)
    if quota_dir.exists():
        shutil.rmtree(quota_dir, ignore_errors=True)
    with jobs._LOCK:
        jobs._IN_MEMORY_STATUS.pop(quota_doc_id, None)
    task_service.reset_in_memory_task_cache()

    rows_before = _count_llm_log_rows()
    try:
        r_up = client.post(
            "/api/documents",
            files={"file": ("quota_test_doc.txt", sample_bytes, "text/plain")},
        )
        if r_up.status_code >= 300:
            return "FAIL", f"upload status={r_up.status_code}"
        doc_st = _poll_doc_ready(client, quota_doc_id, timeout_s=30.0)
        if doc_st.get("state") != "ready":
            return "FAIL", f"doc_st={doc_st}"

        with offline_guard() as guard:
            with task_service.override_app_config(daily_soft_limit=0):
                r_post = client.post(f"/api/documents/{quota_doc_id}/tasks/summary")
                r_get = client.get(f"/api/documents/{quota_doc_id}/tasks/summary")

            body = r_get.json() if r_get.status_code == 200 else {}
            expected_msg = "Today's free AI allowance is used up. Try again tomorrow or use a cached document."
            msg_ok = body.get("error") == expected_msg or body.get("message") == expected_msg

            # Also verify per-task budget cap=0 stops cleanly with state failed/partial and 0 live calls
            with task_service.override_app_config(
                daily_soft_limit=200,
                task_budgets={"summary": 0, "keyinfo": 0},
            ):
                r_bpost = client.post(f"/api/documents/{quota_doc_id}/tasks/summary")
                b_st = _poll_task_done(client, quota_doc_id, "summary", timeout_s=30.0)

        rows_after = _count_llm_log_rows()
        budget_ok = (
            r_bpost.status_code == 202
            and b_st.get("state") in ("failed", "partial")
            and int(b_st.get("live_calls", -1)) == 0
            and bool(b_st.get("error"))
        )
        ok = (
            guard.attempts == 0
            and r_post.status_code == 202
            and r_get.status_code == 200
            and body.get("state") == "quota_blocked"
            and int(body.get("live_calls", -1)) == 0
            and msg_ok
            and budget_ok
            and rows_after == rows_before
        )
        return (
            "PASS" if ok else "FAIL",
            f"post_status={r_post.status_code}, state={body.get('state')}, live_calls={body.get('live_calls')}, "
            f"offline_attempts={guard.attempts}, msg_ok={msg_ok}, budget_cap_state={b_st.get('state')}, "
            f"llm_delta={rows_after - rows_before}",
        )
    finally:
        if quota_dir.exists():
            shutil.rmtree(quota_dir, ignore_errors=True)
        with jobs._LOCK:
            jobs._IN_MEMORY_STATUS.pop(quota_doc_id, None)
        task_service.reset_in_memory_task_cache()


def run_t6_persistence(
    doc_id: str,
    first_summary: dict[str, Any],
    first_keyinfo: dict[str, Any],
) -> tuple[str, str]:
    rows_before = _count_llm_log_rows()
    with jobs._LOCK:
        jobs._IN_MEMORY_STATUS.clear()
    task_service.reset_in_memory_task_cache()

    fresh_client = TestClient(app)
    with offline_guard() as guard:
        r_sum = fresh_client.get(f"/api/documents/{doc_id}/tasks/summary")
        r_ki = fresh_client.get(f"/api/documents/{doc_id}/tasks/keyinfo")
        # Also verify POST on an already-done task returns cached result with 0 live calls
        r_post_cached = fresh_client.post(f"/api/documents/{doc_id}/tasks/summary")
    rows_after = _count_llm_log_rows()

    s2 = r_sum.json() if r_sum.status_code == 200 else {}
    k2 = r_ki.json() if r_ki.status_code == 200 else {}
    p2 = r_post_cached.json() if r_post_cached.status_code in (200, 202) else {}

    sum_identical = s2.get("state") == "done" and s2.get("result") == first_summary.get("result")
    ki_identical = k2.get("state") == "done" and k2.get("result") == first_keyinfo.get("result")
    post_cached_ok = p2.get("state") == "done" and p2.get("result") == first_summary.get("result")
    zero_calls = (rows_after == rows_before) and (guard.attempts == 0)

    ok = sum_identical and ki_identical and post_cached_ok and zero_calls
    return (
        "PASS" if ok else "FAIL",
        f"summary_identical={sum_identical}, keyinfo_identical={ki_identical}, "
        f"post_cached_done={post_cached_ok}, offline_attempts={guard.attempts}, llm_delta={rows_after - rows_before}",
    )


def run_t7_safety(client: TestClient, api_key: str) -> tuple[str, str]:
    unknown_hex = "0123456789ab"
    not_ready_hex = "fedcba987654"
    not_ready_dir = jobs.get_doc_dir(not_ready_hex)
    if not_ready_dir.exists():
        shutil.rmtree(not_ready_dir, ignore_errors=True)

    try:
        r_unk_post = client.post(f"/api/documents/{unknown_hex}/tasks/summary")
        r_unk_get = client.get(f"/api/documents/{unknown_hex}/tasks/summary")
        r_bad_kind = client.post(f"/api/documents/{EXPECTED_DBS_DOC_ID}/tasks/nonexistent_kind")
        r_bad_kind_get = client.get(f"/api/documents/{EXPECTED_DBS_DOC_ID}/tasks/unknown")

        # Create a non-ready doc folder safely to verify 409 conflict
        not_ready_dir.mkdir(parents=True, exist_ok=True)
        (not_ready_dir / "status.json").write_text(
            json.dumps(
                {"state": "ingesting", "stage": "ingesting_pages", "pages_done": 1, "pages_total": 3, "error": None}
            ),
            encoding="utf-8",
        )
        with jobs._LOCK:
            jobs._IN_MEMORY_STATUS.pop(not_ready_hex, None)
        r_conflict = client.post(f"/api/documents/{not_ready_hex}/tasks/summary")

        responses = [r_unk_post, r_unk_get, r_bad_kind, r_bad_kind_get, r_conflict]
        safe_bodies = all(_is_safe_body(r.text, api_key) for r in responses)
        codes_ok = (
            r_unk_post.status_code == 404
            and r_unk_get.status_code == 404
            and r_bad_kind.status_code == 404
            and r_bad_kind_get.status_code == 404
            and r_conflict.status_code == 409
        )
        return (
            "PASS" if (codes_ok and safe_bodies) else "FAIL",
            f"unknown_doc=({r_unk_post.status_code},{r_unk_get.status_code}), "
            f"unknown_kind=({r_bad_kind.status_code},{r_bad_kind_get.status_code}), "
            f"not_ready={r_conflict.status_code}, safe_bodies={safe_bodies}",
        )
    finally:
        if not_ready_dir.exists():
            shutil.rmtree(not_ready_dir, ignore_errors=True)
        with jobs._LOCK:
            jobs._IN_MEMORY_STATUS.pop(not_ready_hex, None)


def run_t9_regressions() -> tuple[str, str]:
    scripts = [
        "scripts/test_2a_ingestion.py",
        "scripts/test_4b_score.py",
        "scripts/test_4a4_scan.py",
        "scripts/test_7a1_api.py",
    ]
    rows_before = _count_llm_log_rows()
    failures: list[str] = []
    summaries: list[str] = []

    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"

    for rel in scripts:
        proc = subprocess.run(
            [sys.executable, "-X", "utf8", str(ROOT / "scripts" / "offline_guard.py"), str(ROOT / rel)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=300,
        )
        lines = [ln.strip() for ln in (proc.stdout + "\n" + proc.stderr).splitlines() if ln.strip()]
        fail_re = re.compile(r"(?:^|\s)\[?FAIL\]?(?:\s|\||$)")
        first_fail = next(
            (ln for ln in lines if fail_re.search(ln)),
            None,
        )
        pass_lines = [ln for ln in lines if ("PASS" in ln or "TARGET" in ln or "INFO" in ln)]
        summary_line = pass_lines[-1] if pass_lines else (lines[-1] if lines else f"exit={proc.returncode}")
        print(f"T9 INFO | {rel} -> rc={proc.returncode} | {summary_line}", flush=True)
        if proc.returncode != 0 or first_fail is not None:
            failures.append(f"{rel}: {first_fail or f'rc={proc.returncode}'}")
        summaries.append(f"{Path(rel).name}={'OK' if proc.returncode == 0 and not first_fail else 'FAIL'}")

    rows_after = _count_llm_log_rows()
    zero_api = (rows_after == rows_before)
    ok = (len(failures) == 0) and zero_api
    detail = f"{', '.join(summaries)}, llm_delta={rows_after - rows_before}"
    if failures:
        detail += f" | first_failure={failures[0]}"
    return ("PASS" if ok else "FAIL"), detail


def main() -> int:
    api_key = get_api_key()
    rows_start = _count_llm_log_rows()

    st1, m1 = run_t1_key_leak_scan(api_key)
    _emit("T1", st1, m1)

    client = TestClient(app)

    print(
        f"T2 INFO | Quota timezone counts={task_service.count_today_calls_by_timezone()} "
        f"(daily_soft_limit={task_service.load_app_config()['daily_soft_limit']})",
        flush=True,
    )
    st2, m2, sum_res = run_t2_summary(client)
    _emit("T2", st2, m2)

    st3, m3, ki_res = run_t3_keyinfo(client, EXPECTED_DBS_DOC_ID)
    _emit("T3", st3, m3)

    st4, m4 = run_t4_summary_cites(sum_res, EXPECTED_DBS_DOC_ID)
    _emit("T4", st4, m4)

    st5, m5 = run_t5_quota_guard(client)
    _emit("T5", st5, m5)

    st6, m6 = run_t6_persistence(EXPECTED_DBS_DOC_ID, sum_res, ki_res)
    _emit("T6", st6, m6)

    st7, m7 = run_t7_safety(client, api_key)
    _emit("T7", st7, m7)

    rows_after_live = _count_llm_log_rows()
    total_live = rows_after_live - rows_start
    st8 = "PASS" if total_live <= 30 else "FAIL"
    _emit("T8", st8, f"total_live_calls={total_live}<=30 (llm_log.csv {rows_start}->{rows_after_live})")

    st9, m9 = run_t9_regressions()
    _emit("T9", st9, m9)

    rows_end = _count_llm_log_rows()
    all_pass = all(s == "PASS" for s in (st1, st2, st3, st4, st5, st6, st7, st8, st9))
    print(f"llm_log rows: {rows_start} -> {rows_end} (live calls = {rows_end - rows_start})", flush=True)
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
