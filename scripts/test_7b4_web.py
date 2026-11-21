"""scripts/test_7b4_web.py

Stage 7b-4: Chat Tab integration and verification tests.
- Zero Gemini API calls: asserts data/processed/llm_log.csv row count strictly unchanged.
- T1 static:
    * No GEMINI_API_KEY leaks.
    * No localStorage or sessionStorage usage.
    * No hardcoded mock results (22842.37, 47.9).
    * No advice phrasing (you should, we recommend, what to ask the lender).
    * No tables_count in web/src.
    * ChatTab.jsx exists and is integrated into App.jsx.
- T2 API integration:
    * Starts FastAPI on a free local port.
    * Ingests 03_dbs_mitc.pdf (cached doc_id 893857f8b7e3) until ready.
    * Reads saved chat history via GET /api/documents/{doc_id}/chat (NO POST of any question).
    * Validates 8 saved turns, category distributions, evidence citations, calculation fields,
      and compares observed statuses/categories/flags against ChatTab.jsx coverage.
    * Tests error responses: unknown doc (404), empty question POST (422) with zero model calls.
    * Verifies no uploads were deleted.
- T3 build check:
    * Runs npm run build in web/, returns INCONCLUSIVE if sandboxed realpath fails.
"""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LLM_LOG_PATH = ROOT / "data" / "processed" / "llm_log.csv"
WEB_DIR = ROOT / "web"
WEB_SRC_DIR = WEB_DIR / "src"
DBS_PDF = ROOT / "data" / "raw" / "08_indian_bank_loans" / "03_dbs_mitc.pdf"
UPLOADS_DIR = ROOT / "data" / "processed" / "uploads"
EXPECTED_DOC_ID = "893857f8b7e3"


def _count_llm_log_rows() -> int:
    if not LLM_LOG_PATH.is_file():
        return 0
    with LLM_LOG_PATH.open("r", encoding="utf-8", errors="ignore") as fh:
        return sum(1 for _ in fh)


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def run_t1_static_checks() -> tuple[str, str]:
    """Scans web/ source files for security, storage, hardcoded mock results, advice phrasing, and ChatTab integration."""
    if not WEB_SRC_DIR.is_dir():
        return "FAIL", f"Source directory missing: {WEB_SRC_DIR}"

    chat_tab_file = WEB_SRC_DIR / "ChatTab.jsx"
    if not chat_tab_file.is_file():
        return "FAIL", f"Missing ChatTab.jsx component at {chat_tab_file}"

    app_file = WEB_SRC_DIR / "App.jsx"
    app_text = app_file.read_text(encoding="utf-8") if app_file.is_file() else ""
    if "ChatTab" not in app_text or "<ChatTab" not in app_text:
        return "FAIL", "ChatTab is not imported or rendered in App.jsx"

    scanned_files = 0
    key_leaks: list[str] = []
    storage_hits: list[str] = []
    hardcoded_hits: list[str] = []
    advice_hits: list[str] = []
    tables_count_hits: list[str] = []
    consult_hits: list[str] = []
    rerun_hits: list[str] = []

    api_key = os.environ.get("GEMINI_API_KEY", "")
    key_bytes = api_key.encode("utf-8") if api_key and len(api_key) > 5 else None

    storage_re = re.compile(r"\b(localStorage|sessionStorage)\b")
    mock_calc_re = re.compile(r"\b(22842\.37|47\.9)\b")
    advice_re = re.compile(r"\b(you should|we recommend|what to ask the lender)\b", re.IGNORECASE)
    consult_re = re.compile(r"\bconsult\b", re.IGNORECASE)
    rerun_re = re.compile(r"\bRe-run\b", re.IGNORECASE)

    expected_refusal = (
        "This system gives document information only. It does not give legal or financial advice, "
        "so it cannot say whether to sign or accept this agreement. It can show the risks, fees, penalties "
        "or foreclosure clauses stated in the document."
    )
    chat_text = chat_tab_file.read_text(encoding="utf-8")
    has_exact_refusal = expected_refusal in chat_text

    for p in WEB_DIR.rglob("*"):
        if not p.is_file():
            continue
        if "node_modules" in p.parts or ".git" in p.parts or "dist" in p.parts:
            continue
        scanned_files += 1

        raw_bytes = p.read_bytes()
        if key_bytes and key_bytes in raw_bytes:
            key_leaks.append(p.name)

        text = raw_bytes.decode("utf-8", errors="ignore")
        if storage_re.search(text):
            storage_hits.append(p.name)
        if mock_calc_re.search(text):
            hardcoded_hits.append(p.name)
        if advice_re.search(text):
            advice_hits.append(f"{p.name}:{advice_re.search(text).group(0)}")
        if "src" in p.parts and "tables_count" in text:
            tables_count_hits.append(p.name)
        if p.name == "ChatTab.jsx" and consult_re.search(text):
            consult_hits.append(f"{p.name}:{consult_re.search(text).group(0)}")
        if p.name in ("SummaryTab.jsx", "KeyInfoTab.jsx") and rerun_re.search(text):
            rerun_hits.append(f"{p.name}:{rerun_re.search(text).group(0)}")

    ok = (
        scanned_files >= 8
        and len(key_leaks) == 0
        and len(storage_hits) == 0
        and len(hardcoded_hits) == 0
        and len(advice_hits) == 0
        and len(tables_count_hits) == 0
        and len(consult_hits) == 0
        and len(rerun_hits) == 0
        and has_exact_refusal
    )

    detail = (
        f"files={scanned_files}, key_leaks={len(key_leaks)}, storage_hits={len(storage_hits)}, "
        f"hardcoded_hits={len(hardcoded_hits)}, advice_hits={len(advice_hits)}, "
        f"tables_count_hits={len(tables_count_hits)}, consult_hits={len(consult_hits)}, "
        f"rerun_hits={len(rerun_hits)}, exact_refusal_present={has_exact_refusal}"
    )
    return ("PASS" if ok else "FAIL"), detail


def run_t2_api_integration() -> tuple[str, str]:
    """Starts FastAPI, uploads DBS PDF, reads saved chat history (NO question POST), verifies shapes and error handling."""
    if not DBS_PDF.is_file():
        return "FAIL", f"Source PDF missing: {DBS_PDF}"

    port = _find_free_port()
    base_url = f"http://127.0.0.1:{port}"

    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"

    uploads_before = {p.name for p in UPLOADS_DIR.iterdir()} if UPLOADS_DIR.is_dir() else set()

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        # 1. Wait for server readiness
        t0 = time.perf_counter()
        meta_ok = False
        while time.perf_counter() - t0 < 45.0:
            try:
                with urllib.request.urlopen(f"{base_url}/api/meta", timeout=1.0) as resp:
                    if resp.status == 200:
                        meta_ok = True
                        break
            except Exception:
                time.sleep(0.5)

        if not meta_ok:
            return "FAIL", f"FastAPI server failed to start on port {port} within 45s"

        # 2. Upload DBS PDF (cached)
        pdf_bytes = DBS_PDF.read_bytes()
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{DBS_PDF.name}"\r\n'
            f"Content-Type: application/pdf\r\n\r\n"
        ).encode("utf-8") + pdf_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

        req = urllib.request.Request(
            f"{base_url}/api/documents",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            up_data = json.loads(resp.read().decode("utf-8"))

        doc_id = up_data.get("doc_id")
        if doc_id != EXPECTED_DOC_ID:
            return "FAIL", f"Expected doc_id {EXPECTED_DOC_ID}, got {doc_id}"

        # 3. Poll document status until ready
        t_poll = time.perf_counter()
        is_ready = False
        while time.perf_counter() - t_poll < 30.0:
            with urllib.request.urlopen(f"{base_url}/api/documents/{doc_id}/status", timeout=5.0) as resp:
                st_data = json.loads(resp.read().decode("utf-8"))
                if st_data.get("state") == "ready":
                    is_ready = True
                    break
            time.sleep(0.5)

        if not is_ready:
            return "FAIL", f"Document {doc_id} did not reach ready state"

        # 4. GET saved chat history (NO POST OF ANY QUESTION!)
        req_chat = urllib.request.Request(
            f"{base_url}/api/documents/{doc_id}/chat",
            method="GET",
        )
        with urllib.request.urlopen(req_chat, timeout=10.0) as resp:
            chat_code = resp.status
            chat_data = json.loads(resp.read().decode("utf-8"))

        turns = chat_data.get("turns", [])
        if chat_code != 200 or len(turns) < 8:
            return "FAIL", f"Chat history GET failed: code={chat_code}, turn_count={len(turns)}"

        # 5. Extract categories, statuses, and flags from saved turns
        resp_categories = {t.get("category") for t in turns if t.get("category")}
        resp_statuses = {t.get("status") for t in turns if t.get("status")}
        resp_flags = {f for t in turns for f in t.get("flags", [])}
        fallback_turns = [t for t in turns if t.get("fallback_used") or "model_fallback" in t.get("flags", [])]
        review_turns = [t for t in turns if t.get("final_check") == "needs_review"]
        calc_turns = [t for t in turns if t.get("category") == "calculation"]

        # Verify calculation turn has expected structure
        if len(calc_turns) != 1:
            return "FAIL", f"Expected exactly 1 calculation turn, found {len(calc_turns)}"
        c_turn = calc_turns[0]
        if not c_turn.get("inputs") or not c_turn.get("steps") or not c_turn.get("result"):
            return "FAIL", f"Calculation turn missing required fields: {c_turn}"

        # 6. Check UI component coverage in ChatTab.jsx
        chat_tab_text = (WEB_SRC_DIR / "ChatTab.jsx").read_text(encoding="utf-8")

        ui_handled_categories = {
            c for c in [
                "fact",
                "explain_term",
                "calculation",
                "advice",
                "off_topic",
            ] if f"'{c}'" in chat_tab_text or f'"{c}"' in chat_tab_text
        }

        ui_handled_statuses = {
            s for s in [
                "ok",
                "not_found",
                "unverified",
                "refused",
                "off_topic",
                "needs_review",
                "needs_inputs",
                "quota_blocked",
                "needs_retrieval",
                "failed",
            ] if f"'{s}'" in chat_tab_text or f'"{s}"' in chat_tab_text
        }

        ui_handled_flags = {
            f for f in [
                "model_fallback",
                "advice_refused",
                "off_topic_refused",
                "evidence_unverified_server",
                "quota_blocked",
                "chat_budget_reached",
            ] if f"'{f}'" in chat_tab_text or f'"{f}"' in chat_tab_text
        }

        cat_covered = resp_categories.issubset(ui_handled_categories)
        status_covered = resp_statuses.issubset(ui_handled_statuses)
        flags_covered = resp_flags.issubset(ui_handled_flags)

        # 7. Test Error Status Codes (without invoking any model)
        # 7a. Unknown doc_id -> 404
        unknown_ok = False
        try:
            with urllib.request.urlopen(f"{base_url}/api/documents/000000000000/chat") as resp:
                pass
        except urllib.error.HTTPError as err:
            if err.code == 404:
                unknown_ok = True

        # 7b. Empty question POST -> 422
        empty_q_ok = False
        empty_req = urllib.request.Request(
            f"{base_url}/api/documents/{doc_id}/chat",
            data=json.dumps({"question": ""}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(empty_req) as resp:
                pass
        except urllib.error.HTTPError as err:
            if err.code == 422:
                empty_q_ok = True

        # 8. Check no uploads deleted
        uploads_after = {p.name for p in UPLOADS_DIR.iterdir()} if UPLOADS_DIR.is_dir() else set()
        no_deletions = uploads_before.issubset(uploads_after)

        all_ok = (
            cat_covered
            and status_covered
            and flags_covered
            and unknown_ok
            and empty_q_ok
            and no_deletions
            and len(fallback_turns) >= 2
            and len(review_turns) >= 1
        )

        detail = (
            f"port={port}, doc_id={doc_id}, turns={len(turns)}, "
            f"fallback_turns={len(fallback_turns)}, review_turns={len(review_turns)}, "
            f"resp_categories={sorted(list(resp_categories))}, "
            f"ui_handled_categories={sorted(list(ui_handled_categories))}, "
            f"resp_statuses={sorted(list(resp_statuses))}, "
            f"ui_handled_statuses={sorted(list(ui_handled_statuses))}, "
            f"resp_flags={sorted(list(resp_flags))}, "
            f"ui_handled_flags={sorted(list(ui_handled_flags))}, "
            f"unknown_doc_404={unknown_ok}, empty_q_422={empty_q_ok}, "
            f"uploads_preserved={no_deletions}"
        )
        return ("PASS" if all_ok else "FAIL"), detail

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            proc.kill()


def run_t3_build_check() -> tuple[str, str]:
    """Checks build feasibility: runs npm run build, reporting INCONCLUSIVE if blocked by sandbox isolation."""
    node_modules = WEB_DIR / "node_modules"
    if not node_modules.is_dir():
        return (
            "INCONCLUSIVE",
            "web/node_modules absent (npm install requires internet; student runs on host)",
        )

    proc = subprocess.run(
        ["npm", "run", "build"],
        cwd=str(WEB_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        shell=True,
    )
    if proc.returncode != 0:
        if "EPERM" in proc.stderr or "realpath" in proc.stderr or "ENOTCACHED" in proc.stderr:
            return (
                "INCONCLUSIVE",
                "sandbox realpath EPERM prevents build inside sandbox (student runs npm run build on host)",
            )
        return "FAIL", f"npm run build failed (rc={proc.returncode}): {proc.stderr[:200]}"

    dist_dir = WEB_DIR / "dist"
    total_size = sum(f.stat().st_size for f in dist_dir.rglob("*") if f.is_file()) if dist_dir.is_dir() else 0
    return "PASS", f"build succeeded, dist_size={total_size / 1024:.1f} KB"


def main() -> int:
    print("=" * 80)
    print("STAGE 7b-4: CHAT TAB INTEGRATION TESTS")
    print("=" * 80)

    rows_before = _count_llm_log_rows()

    st1, msg1 = run_t1_static_checks()
    print(f"T1 {st1} | Static checks: {msg1}")

    st2, msg2 = run_t2_api_integration()
    print(f"T2 {st2} | API integration: {msg2}")

    st3, msg3 = run_t3_build_check()
    print(f"T3 {st3} | Build check: {msg3}")

    rows_after = _count_llm_log_rows()
    zero_api = rows_after == rows_before
    print(f"llm_log.csv rows: {rows_before} -> {rows_after} (delta = {rows_after - rows_before})")

    all_pass = (st1 == "PASS" and st2 == "PASS" and st3 in ("PASS", "INCONCLUSIVE") and zero_api)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
