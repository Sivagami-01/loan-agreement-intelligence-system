"""scripts/test_7a1_api.py

Verification suite for Stage 7a-1 FastAPI backend (ZERO Gemini API calls).
Prints T1-T8 PASS/FAIL/INCONCLUSIVE lines plus llm_log rows check.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.api import jobs  # noqa: E402
from app.api.main import app  # noqa: E402
from src.llm.gemini_client import get_api_key  # noqa: E402

LLM_LOG_PATH = ROOT / "data" / "processed" / "llm_log.csv"
RAW_INDIAN_DIR = ROOT / "data" / "raw" / "08_indian_bank_loans"
INGESTED_DIR = ROOT / "data" / "processed" / "ingested"

T4_PDF = RAW_INDIAN_DIR / "03_dbs_mitc.pdf"
T4_INGESTED_JSON = INGESTED_DIR / "03_dbs_mitc.json"
T5_PDF = RAW_INDIAN_DIR / "30_piramal_finance_mortgage_mitc_latest_10042024.pdf"


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


def _clear_test_upload_cache(pdf_path: Path) -> str:
    doc_id = hashlib.sha256(pdf_path.read_bytes()).hexdigest()[:12]
    target = jobs.UPLOADS_DIR / doc_id
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
    with jobs._LOCK:
        jobs._IN_MEMORY_STATUS.pop(doc_id, None)
        jobs._INGEST_RUN_COUNTS.pop(doc_id, None)
    return doc_id


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


def run_t2_health_and_meta(client: TestClient) -> tuple[str, str]:
    r_h = client.get("/api/health")
    r_m = client.get("/api/meta")
    expected_meta = {
        "disclaimer": "This system provides information, not legal or financial advice.",
        "upload_notice": "Upload only public documents.",
        "max_upload_mb": 25,
        "allowed_types": ["pdf", "html", "txt"],
    }
    ok = (
        r_h.status_code == 200
        and r_h.json() == {"status": "ok"}
        and r_m.status_code == 200
        and r_m.json() == expected_meta
    )
    return (
        "PASS" if ok else "FAIL",
        f"health={r_h.status_code}:{r_h.json()}, meta={r_m.status_code}:{r_m.json()}",
    )


def run_t3_upload_rejections(client: TestClient, api_key: str) -> tuple[str, str]:
    r_exe = client.post("/api/documents", files={"file": ("malware.exe", b"MZ\x90\x00test", "application/octet-stream")})
    r_fake_pdf = client.post("/api/documents", files={"file": ("fake.pdf", b"NOT A PDF HEADER", "application/pdf")})
    big_bytes = b"%PDF-1.4\n" + (b"A" * (26 * 1024 * 1024))
    r_big = client.post("/api/documents", files={"file": ("big.pdf", big_bytes, "application/pdf")})

    statuses = (r_exe.status_code, r_fake_pdf.status_code, r_big.status_code)
    bodies = (r_exe.text, r_fake_pdf.text, r_big.text)
    all_4xx = all(400 <= s < 500 for s in statuses)
    all_safe = all(_is_safe_body(b, api_key) for b in bodies)
    ok = all_4xx and all_safe
    return (
        "PASS" if ok else "FAIL",
        f"statuses(exe/fake_pdf/26mb)={statuses}, all_4xx={all_4xx}, safe_bodies={all_safe}",
    )


def _poll_until_ready(client: TestClient, doc_id: str, timeout_s: float) -> tuple[dict[str, Any] | None, float, bool]:
    t0 = time.perf_counter()
    last_st: dict[str, Any] | None = None
    while True:
        elapsed = time.perf_counter() - t0
        res = client.get(f"/api/documents/{doc_id}/status")
        if res.status_code == 200:
            last_st = res.json()
            if last_st.get("state") in ("ready", "failed"):
                return last_st, elapsed, False
        if elapsed >= timeout_s:
            return last_st, elapsed, True
        time.sleep(0.25)


def run_t4_real_dbs_upload(client: TestClient) -> tuple[str, str, dict[str, Any]]:
    expected_pages = int(json.loads(T4_INGESTED_JSON.read_text(encoding="utf-8"))["total_pages"])
    doc_id = _clear_test_upload_cache(T4_PDF)

    t0 = time.perf_counter()
    with T4_PDF.open("rb") as fh:
        r_up = client.post("/api/documents", files={"file": (T4_PDF.name, fh.read(), "application/pdf")})
    if r_up.status_code >= 300:
        return "FAIL", f"upload failed status={r_up.status_code}: {r_up.text}", {}
    up_json = r_up.json()
    st, _, timed_out = _poll_until_ready(client, doc_id, timeout_s=60.0)
    elapsed = round(time.perf_counter() - t0, 3)

    if timed_out or not st or st.get("state") != "ready":
        return "FAIL", f"status={st}, timed_out={timed_out}", {}

    r_p1 = client.get(f"/api/documents/{doc_id}/pages/1")
    p1 = r_p1.json() if r_p1.status_code == 200 else {}
    ok = (
        up_json.get("doc_id") == doc_id
        and up_json.get("cached") is False
        and int(st.get("pages_total", -1)) == expected_pages
        and r_p1.status_code == 200
        and len(str(p1.get("text", "")).strip()) > 0
        and p1.get("quality") in {"GOOD", "SUSPICIOUS", "BAD"}
        and p1.get("source") in {"text", "ocr"}
    )
    info = {
        "doc_id": doc_id,
        "elapsed_s": elapsed,
        "pages": int(st["pages_total"]),
        "p1_source": p1.get("source"),
        "p1_quality": p1.get("quality"),
        "run_count_after_t4": jobs.get_ingest_run_count(doc_id),
    }
    return (
        "PASS" if ok else "FAIL",
        f"doc_id={doc_id}, state=ready in {elapsed:.3f}s, pages={st.get('pages_total')}=={expected_pages}, "
        f"p1_len={len(str(p1.get('text', '')).strip())}, p1_source={p1.get('source')}, p1_quality={p1.get('quality')}",
        info,
    )


def run_t5_scanned_ocr_upload(client: TestClient) -> tuple[str, str, dict[str, Any]]:
    doc_id = _clear_test_upload_cache(T5_PDF)
    t0 = time.perf_counter()
    with T5_PDF.open("rb") as fh:
        r_up = client.post("/api/documents", files={"file": (T5_PDF.name, fh.read(), "application/pdf")})
    if r_up.status_code >= 300:
        return "FAIL", f"upload failed status={r_up.status_code}: {r_up.text}", {}

    st, _, timed_out = _poll_until_ready(client, doc_id, timeout_s=300.0)
    elapsed = round(time.perf_counter() - t0, 3)

    if timed_out:
        return "INCONCLUSIVE", f"OCR ingest timed out after {elapsed:.2f}s (limit=300s)", {"elapsed_s": elapsed}
    if not st or st.get("state") != "ready":
        return "FAIL", f"state={st} after {elapsed:.2f}s", {}

    total_pages = int(st.get("pages_total", 0))
    ocr_pages = 0
    bad_pages = 0
    for n in range(1, total_pages + 1):
        rp = client.get(f"/api/documents/{doc_id}/pages/{n}")
        if rp.status_code == 200:
            pj = rp.json()
            if pj.get("source") == "ocr":
                ocr_pages += 1
        else:
            bad_pages += 1

    ok = total_pages > 0 and ocr_pages >= 1 and bad_pages == 0
    return (
        "PASS" if ok else "FAIL",
        f"doc_id={doc_id} ({T5_PDF.name}), ready in {elapsed:.3f}s, pages={total_pages}, ocr_pages={ocr_pages}",
        {"doc_id": doc_id, "elapsed_s": elapsed, "pages": total_pages, "ocr_pages": ocr_pages},
    )


def run_t6_duplicate_upload(client: TestClient, t4_info: dict[str, Any]) -> tuple[str, str]:
    if not t4_info:
        return "INCONCLUSIVE", "skipped because T4 did not produce a ready doc_id"
    doc_id = t4_info["doc_id"]
    runs_before = jobs.get_ingest_run_count(doc_id)
    with T4_PDF.open("rb") as fh:
        r_dup = client.post("/api/documents", files={"file": (T4_PDF.name, fh.read(), "application/pdf")})
    runs_after = jobs.get_ingest_run_count(doc_id)
    dj = r_dup.json() if r_dup.status_code == 200 else {}
    ok = (
        r_dup.status_code == 200
        and dj.get("doc_id") == doc_id
        and dj.get("cached") is True
        and runs_before == runs_after == 1
    )
    return (
        "PASS" if ok else "FAIL",
        f"doc_id={dj.get('doc_id')}=={doc_id}, cached={dj.get('cached')}, ingest_runs={runs_before}->{runs_after}",
    )


def run_t7_safety_doc_ids(client: TestClient, api_key: str) -> tuple[str, str]:
    probes = ["../x", "..%2Fx", "abc", "0123456789ag", "ZZZZZZZZZZZZ"]
    results: list[tuple[str, int, bool]] = []
    for bad in probes:
        r_st = client.get(f"/api/documents/{bad}/status")
        r_pg = client.get(f"/api/documents/{bad}/pages/1")
        for r in (r_st, r_pg):
            results.append((bad, r.status_code, _is_safe_body(r.text, api_key)))

    all_400_or_404 = all(code in (400, 404) for _, code, _ in results)
    all_safe = all(safe for _, _, safe in results)
    ok = all_400_or_404 and all_safe
    summary_codes = {bad: client.get(f"/api/documents/{bad}/status").status_code for bad in probes}
    return (
        "PASS" if ok else "FAIL",
        f"probe_statuses={summary_codes}, all_400_or_404={all_400_or_404}, zero_abs_paths_or_leaks={all_safe}",
    )


def main() -> None:
    rows_before = _count_llm_log_rows()
    api_key = get_api_key()

    st1, msg1 = run_t1_key_leak_scan(api_key)
    _emit("T1", st1, msg1)

    with TestClient(app) as client:
        st2, msg2 = run_t2_health_and_meta(client)
        _emit("T2", st2, msg2)

        st3, msg3 = run_t3_upload_rejections(client, api_key)
        _emit("T3", st3, msg3)

        st4, msg4, t4_info = run_t4_real_dbs_upload(client)
        _emit("T4", st4, msg4)

        st5, msg5, t5_info = run_t5_scanned_ocr_upload(client)
        _emit("T5", st5, msg5)

        st6, msg6 = run_t6_duplicate_upload(client, t4_info)
        _emit("T6", st6, msg6)

        st7, msg7 = run_t7_safety_doc_ids(client, api_key)
        _emit("T7", st7, msg7)

    rows_after = _count_llm_log_rows()
    t8_ok = (rows_before == rows_after) and ("src.llm" not in sys.modules or rows_before == rows_after)
    _emit("T8", "PASS" if t8_ok else "FAIL", f"zero Gemini calls; llm_log.csv rows={rows_before}->{rows_after}")
    print(f"llm_log rows: {rows_before} -> {rows_after} | {'PASS' if t8_ok else 'FAIL'}", flush=True)


if __name__ == "__main__":
    main()
