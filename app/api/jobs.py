"""app/api/jobs.py

Thread-safe background ingestion job manager backed by disk status files
under data/processed/uploads/<doc_id>/status.json.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from app.api.ingest_service import _write_json_atomic, ingest_uploaded_document

ROOT = Path(__file__).resolve().parents[2]
UPLOADS_DIR = ROOT / "data" / "processed" / "uploads"

_LOCK = threading.Lock()
_IN_MEMORY_STATUS: dict[str, dict[str, Any]] = {}
_INGEST_RUN_COUNTS: dict[str, int] = {}
_THREADS: dict[str, threading.Thread] = {}


def get_doc_dir(doc_id: str) -> Path:
    return UPLOADS_DIR / doc_id


def read_status(doc_id: str) -> dict[str, Any] | None:
    with _LOCK:
        if doc_id in _IN_MEMORY_STATUS:
            return dict(_IN_MEMORY_STATUS[doc_id])

    doc_dir = get_doc_dir(doc_id)
    status_path = doc_dir / "status.json"
    if status_path.is_file():
        try:
            data = json.loads(status_path.read_text(encoding="utf-8"))
            with _LOCK:
                _IN_MEMORY_STATUS[doc_id] = data
            return dict(data)
        except Exception:
            pass

    ingested_path = doc_dir / "ingested.json"
    if ingested_path.is_file():
        try:
            ing = json.loads(ingested_path.read_text(encoding="utf-8"))
            total = int(ing.get("total_pages", 0))
            data = {
                "state": "ready",
                "stage": "complete",
                "pages_done": total,
                "pages_total": total,
                "error": None,
            }
            _write_status(doc_id, data)
            return dict(data)
        except Exception:
            pass

    return None


def _write_status(doc_id: str, status: dict[str, Any]) -> None:
    doc_dir = get_doc_dir(doc_id)
    doc_dir.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        _IN_MEMORY_STATUS[doc_id] = dict(status)
    _write_json_atomic(doc_dir / "status.json", status)


def get_ingest_run_count(doc_id: str) -> int:
    with _LOCK:
        return int(_INGEST_RUN_COUNTS.get(doc_id, 0))


def is_cached_or_active(doc_id: str) -> tuple[bool, str | None]:
    """Return (True, current_state) if doc_id is already ready, queued, or ingesting."""
    doc_dir = get_doc_dir(doc_id)
    st = read_status(doc_id)
    if st is not None:
        state = st.get("state")
        if state == "ready" and (doc_dir / "ingested.json").is_file():
            return True, "ready"
        if state in ("queued", "ingesting"):
            return True, str(state)
    if (doc_dir / "ingested.json").is_file():
        return True, "ready"
    return False, None


def _run_job(doc_id: str, raw_path: Path, safe_name: str) -> None:
    doc_dir = get_doc_dir(doc_id)
    with _LOCK:
        _INGEST_RUN_COUNTS[doc_id] = _INGEST_RUN_COUNTS.get(doc_id, 0) + 1

    def _on_progress(stage: str, done: int, total: int) -> None:
        _write_status(
            doc_id,
            {
                "state": "ingesting",
                "stage": stage,
                "pages_done": int(done),
                "pages_total": int(total),
                "error": None,
            },
        )

    _on_progress("starting", 0, 0)
    try:
        payload = ingest_uploaded_document(
            raw_path=raw_path,
            doc_dir=doc_dir,
            doc_id=doc_id,
            safe_name=safe_name,
            progress_cb=_on_progress,
        )
        total = int(payload.get("total_pages", 0))
        _write_status(
            doc_id,
            {
                "state": "ready",
                "stage": "complete",
                "pages_done": total,
                "pages_total": total,
                "error": None,
            },
        )
    except Exception as exc:
        # Short safe error message with zero file paths or secret leakage
        safe_err = f"Ingestion failed ({type(exc).__name__})."
        _write_status(
            doc_id,
            {
                "state": "failed",
                "stage": "error",
                "pages_done": 0,
                "pages_total": 0,
                "error": safe_err,
            },
        )


def start_ingest_job(doc_id: str, raw_path: Path, safe_name: str) -> dict[str, Any]:
    initial = {
        "state": "queued",
        "stage": "queued",
        "pages_done": 0,
        "pages_total": 0,
        "error": None,
    }
    _write_status(doc_id, initial)
    t = threading.Thread(
        target=_run_job,
        args=(doc_id, raw_path, safe_name),
        daemon=True,
        name=f"ingest-{doc_id}",
    )
    with _LOCK:
        _THREADS[doc_id] = t
    t.start()
    return initial
