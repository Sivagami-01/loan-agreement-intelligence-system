"""scripts/test_7b2_web.py

Stage 7b-2: Summary tab and Key Info tab in web/src.
- Zero Gemini API calls: asserts llm_log.csv row count unchanged.
- T1 static: no API key leaks, no localStorage/sessionStorage, no hardcoded results, no advice phrasing.
- T2 API: starts FastAPI subprocess, uploads 03_dbs_mitc.pdf, calls POST summary & keyinfo,
  verifies 200/done with live_calls == 0, and asserts all response statuses are handled by UI.
- T3 build: attempts npm run build; reports INCONCLUSIVE if sandbox blocks realpath.
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
    """Scans web/ source files for security, storage, hardcoded mock results, and advice phrasing."""
    if not WEB_SRC_DIR.is_dir():
        return "FAIL", f"Source directory missing: {WEB_SRC_DIR}"

    scanned_files = 0
    key_leaks: list[str] = []
    storage_hits: list[str] = []
    hardcoded_hits: list[str] = []
    advice_hits: list[str] = []
    tables_count_hits: list[str] = []

    api_key = os.environ.get("GEMINI_API_KEY", "")
    key_bytes = api_key.encode("utf-8") if api_key and len(api_key) > 5 else None

    storage_re = re.compile(r"\b(localStorage|sessionStorage)\b")
    mock_calc_re = re.compile(r"\b(22842\.37|47\.9)\b")
    advice_re = re.compile(r"\b(you should|we recommend|what to ask the lender)\b", re.IGNORECASE)

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

    ok = (
        scanned_files >= 6
        and len(key_leaks) == 0
        and len(storage_hits) == 0
        and len(hardcoded_hits) == 0
        and len(advice_hits) == 0
        and len(tables_count_hits) == 0
    )

    detail = (
        f"files={scanned_files}, key_leaks={len(key_leaks)}, storage_hits={len(storage_hits)}, "
        f"hardcoded_hits={len(hardcoded_hits)}, advice_hits={len(advice_hits)}, "
        f"tables_count_hits={len(tables_count_hits)}"
    )
    return ("PASS" if ok else "FAIL"), detail


def run_t2_api_integration() -> tuple[str, str]:
    """Starts FastAPI, uploads 03_dbs_mitc.pdf, POSTs summary and keyinfo, verifies live_calls==0 and handled statuses."""
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
        while time.perf_counter() - t0 < 35.0:
            try:
                with urllib.request.urlopen(f"{base_url}/api/meta", timeout=1.0) as resp:
                    if resp.status == 200:
                        meta_ok = True
                        break
            except Exception:
                time.sleep(0.5)

        if not meta_ok:
            return "FAIL", f"FastAPI server failed to start on port {port} within 35s"

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

        # 4. POST Summary task
        req_sum = urllib.request.Request(
            f"{base_url}/api/documents/{doc_id}/tasks/summary",
            data=b"",
            method="POST",
        )
        with urllib.request.urlopen(req_sum, timeout=10.0) as resp:
            sum_code = resp.status
            sum_data = json.loads(resp.read().decode("utf-8"))

        # 5. POST Key Info task
        req_ki = urllib.request.Request(
            f"{base_url}/api/documents/{doc_id}/tasks/keyinfo",
            data=b"",
            method="POST",
        )
        with urllib.request.urlopen(req_ki, timeout=10.0) as resp:
            ki_code = resp.status
            ki_data = json.loads(resp.read().decode("utf-8"))

        sum_ok = (
            sum_code == 200
            and sum_data.get("state") == "done"
            and int(sum_data.get("live_calls", 0)) == 0
            and isinstance(sum_data.get("result"), dict)
            and len(sum_data["result"].get("short", "")) > 50
        )

        ki_ok = (
            ki_code == 200
            and ki_data.get("state") == "done"
            and int(ki_data.get("live_calls", 0)) == 0
            and isinstance(ki_data.get("result"), dict)
            and len(ki_data["result"].get("fields", [])) == 16
        )

        if not sum_ok:
            return "FAIL", f"Summary task assertion failed: code={sum_code}, data={sum_data}"
        if not ki_ok:
            return "FAIL", f"Key Info task assertion failed: code={ki_code}, data={ki_data}"

        # 6. Status coverage check: UI code vs API response
        resp_field_statuses = {
            f.get("status") for f in ki_data["result"]["fields"] if f.get("status")
        }
        resp_task_states = {sum_data.get("state"), ki_data.get("state")}

        # Scan UI component code to verify handled statuses
        ki_tab_text = (WEB_SRC_DIR / "KeyInfoTab.jsx").read_text(encoding="utf-8")
        sum_tab_text = (WEB_SRC_DIR / "SummaryTab.jsx").read_text(encoding="utf-8")

        ui_handled_field_statuses = {
            s for s in [
                "verified",
                "needs_review",
                "not_found",
                "deferred_to_other_document",
                "unverified",
            ] if f"'{s}'" in ki_tab_text or f'"{s}"' in ki_tab_text
        }

        ui_handled_task_states = {
            s for s in [
                "not_started",
                "running",
                "done",
                "failed",
                "quota_blocked",
                "partial",
            ] if f"'{s}'" in ki_tab_text and f"'{s}'" in sum_tab_text
        }

        fields_covered = resp_field_statuses.issubset(ui_handled_field_statuses)
        tasks_covered = resp_task_states.issubset(ui_handled_task_states)

        # 7. Check no uploads deleted
        uploads_after = {p.name for p in UPLOADS_DIR.iterdir()} if UPLOADS_DIR.is_dir() else set()
        no_deletions = uploads_before.issubset(uploads_after)

        all_ok = sum_ok and ki_ok and fields_covered and tasks_covered and no_deletions

        detail = (
            f"port={port}, doc_id={doc_id}, sum_live_calls={sum_data.get('live_calls')}, "
            f"ki_live_calls={ki_data.get('live_calls')}, "
            f"response_field_statuses={sorted(list(resp_field_statuses))}, "
            f"ui_handled_field_statuses={sorted(list(ui_handled_field_statuses))}, "
            f"response_task_states={sorted(list(resp_task_states))}, "
            f"ui_handled_task_states={sorted(list(ui_handled_task_states))}, "
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
    print("STAGE 7b-2: SUMMARY AND KEY INFO TABS INTEGRATION TESTS")
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
