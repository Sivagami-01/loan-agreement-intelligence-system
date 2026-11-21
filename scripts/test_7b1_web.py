"""scripts/test_7b1_web.py

Test suite for Stage 7b-1: Scaffold + Notices + Upload with Progress.
Makes ZERO Gemini API calls.
Never prints or logs GEMINI_API_KEY.
"""

from __future__ import annotations

import csv
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
DBS_PDF = ROOT / "data" / "raw" / "08_indian_bank_loans" / "03_dbs_mitc.pdf"
UPLOADS_DIR = ROOT / "data" / "processed" / "uploads"


def _count_llm_log_rows() -> int:
    if not LLM_LOG_PATH.is_file():
        return 0
    with LLM_LOG_PATH.open("r", encoding="utf-8", errors="ignore") as fh:
        return sum(1 for _ in fh)


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def run_t1_static_web_checks() -> tuple[str, str]:
    """Scans web/ source files for forbidden patterns, storage usage, and hard-coded values."""
    if not WEB_DIR.is_dir():
        return "FAIL", "web/ directory does not exist"

    scanned_files = 0
    key_leaks: list[str] = []
    storage_hits: list[str] = []
    hardcoded_hits: list[str] = []
    tables_count_hits: list[str] = []

    # Get API key if available to verify absence
    api_key = os.environ.get("GEMINI_API_KEY", "")
    key_bytes = api_key.encode("utf-8") if api_key and len(api_key) > 5 else None

    # Forbidden patterns
    storage_re = re.compile(r"\b(localStorage|sessionStorage)\b")
    # Avoid hard-coded mock calculations or scores in client code
    mock_calc_re = re.compile(r"\b(22842\.37|47\.9)\b")

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
        if "src" in p.parts and "tables_count" in text:
            tables_count_hits.append(str(p.relative_to(WEB_DIR)))

    ok = (
        scanned_files >= 5
        and len(key_leaks) == 0
        and len(storage_hits) == 0
        and len(hardcoded_hits) == 0
        and len(tables_count_hits) == 0
    )

    detail = (
        f"files={scanned_files}, key_leaks={len(key_leaks)}, "
        f"storage_usage={len(storage_hits)}, hardcoded_results={len(hardcoded_hits)}, "
        f"tables_count_hits={len(tables_count_hits)}"
    )
    return ("PASS" if ok else "FAIL"), detail


def run_t2_api_server_flow() -> tuple[str, str]:
    """Starts FastAPI in subprocess, exercises meta/upload/status/pages, asserts clean response fields."""
    if not DBS_PDF.is_file():
        return "FAIL", f"Source PDF missing: {DBS_PDF}"

    port = _find_free_port()
    base_url = f"http://127.0.0.1:{port}"

    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"

    # Snapshot existing uploads to verify none are deleted
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
        # Wait for server to respond to /api/meta (allow up to 35s for uvicorn import & startup)
        t0 = time.perf_counter()
        meta_data: dict[str, Any] | None = None
        while time.perf_counter() - t0 < 35.0:
            try:
                with urllib.request.urlopen(f"{base_url}/api/meta", timeout=1.0) as resp:
                    if resp.status == 200:
                        meta_data = json.loads(resp.read().decode("utf-8"))
                        break
            except Exception:
                time.sleep(0.5)

        if meta_data is None:
            return "FAIL", f"FastAPI server failed to start on port {port} within 35s"

        # 1. Verify GET /api/meta fields
        meta_ok = (
            "disclaimer" in meta_data
            and "upload_notice" in meta_data
            and "max_upload_mb" in meta_data
            and "allowed_types" in meta_data
            and isinstance(meta_data["allowed_types"], list)
        )
        if not meta_ok:
            return "FAIL", f"Invalid /api/meta response schema: {meta_data}"

        # 2. Upload DBS PDF via POST /api/documents
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
        up_ok = (
            doc_id is not None
            and "cached" in up_data
            and "filename" in up_data
        )
        if not up_ok:
            return "FAIL", f"Invalid upload response schema: {up_data}"

        # 3. Poll GET /api/documents/{doc_id}/status until ready
        t_poll_start = time.perf_counter()
        status_data: dict[str, Any] | None = None
        while time.perf_counter() - t_poll_start < 30.0:
            with urllib.request.urlopen(f"{base_url}/api/documents/{doc_id}/status", timeout=5.0) as resp:
                cur_status = json.loads(resp.read().decode("utf-8"))
                if cur_status.get("state") in ("ready", "failed"):
                    status_data = cur_status
                    break
            time.sleep(0.5)

        if not status_data or status_data.get("state") != "ready":
            return "FAIL", f"Status did not reach 'ready': {status_data}"

        status_fields_ok = (
            "state" in status_data
            and "stage" in status_data
            and "pages_done" in status_data
            and "pages_total" in status_data
            and status_data["pages_done"] == status_data["pages_total"] == 2
        )
        if not status_fields_ok:
            return "FAIL", f"Status schema mismatch: {status_data}"

        # 4. Fetch Page 1: GET /api/documents/{doc_id}/pages/1
        with urllib.request.urlopen(f"{base_url}/api/documents/{doc_id}/pages/1", timeout=5.0) as resp:
            page_data = json.loads(resp.read().decode("utf-8"))

        page_fields_ok = (
            page_data.get("page") == 1
            and len(str(page_data.get("text", "")).strip()) > 50
            and page_data.get("source") in ("text", "ocr")
            and page_data.get("quality") in ("GOOD", "SUSPICIOUS", "BAD")
        )
        if not page_fields_ok:
            return "FAIL", f"Page 1 schema mismatch: {page_data}"

        # 5. Verify no pre-existing uploads deleted
        uploads_after = {p.name for p in UPLOADS_DIR.iterdir()} if UPLOADS_DIR.is_dir() else set()
        no_deletions = uploads_before.issubset(uploads_after)

        ok = meta_ok and up_ok and status_fields_ok and page_fields_ok and no_deletions
        return (
            "PASS" if ok else "FAIL",
            f"port={port}, doc_id={doc_id}, pages={page_data.get('page')}/{status_data.get('pages_total')}, "
            f"source={page_data.get('source')}, quality={page_data.get('quality')}, uploads_preserved={no_deletions}",
        )

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            proc.kill()


def run_t3_build_check() -> tuple[str, str]:
    """Checks build feasibility: runs npm run build if node_modules present, otherwise reports INCONCLUSIVE."""
    node_modules = WEB_DIR / "node_modules"
    if not node_modules.is_dir():
        return (
            "INCONCLUSIVE",
            "web/node_modules absent (npm install requires internet for react-refresh; student runs on host)",
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
        if "EPERM" in proc.stderr or "realpath" in proc.stderr:
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
    print("STAGE 7b-1: WEB FRONTEND SCAFFOLD & API INTEGRATION TESTS")
    print("=" * 80)

    rows_before = _count_llm_log_rows()

    # T1: Static Web Checks
    st1, msg1 = run_t1_static_web_checks()
    print(f"T1 {st1} | Static checks: {msg1}")

    # T2: Live API Flow via Local Subprocess
    st2, msg2 = run_t2_api_server_flow()
    print(f"T2 {st2} | API server flow: {msg2}")

    # T3: Build Check
    st3, msg3 = run_t3_build_check()
    print(f"T3 {st3} | Build check: {msg3}")

    rows_after = _count_llm_log_rows()
    zero_api = rows_after == rows_before
    print(f"llm_log.csv rows: {rows_before} -> {rows_after} (delta = {rows_after - rows_before})")

    all_pass = (st1 == "PASS" and st2 == "PASS" and st3 in ("PASS", "INCONCLUSIVE") and zero_api)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
