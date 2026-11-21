"""app/api/ingest_service.py

Thin wrapper around scripts/ingest.py for Stage 7a-1 document ingestion.
Keeps scripts/ingest.py untouched while adding:
- per-page progress callback for PDFs
- safe .txt ingestion with identical JSON/TXT output schema
- path-free metadata (no host absolute paths stored in output JSON)
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Callable

import fitz

from scripts.ingest import check_page_quality, ingest_html, ingest_pdf_page


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _write_txt_atomic(path: Path, pages_data: list[dict[str, Any]]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    lines = [f"[[PAGE {p['page']}]]\n{str(p['text']).strip()}" for p in pages_data]
    tmp.write_text("\n\n".join(lines) + "\n", encoding="utf-8")
    tmp.replace(path)


def _normalize_source(raw_source: str | None, ocr_used: bool = False) -> str:
    if ocr_used or raw_source == "ocr":
        return "ocr"
    return "text"


def _ingest_txt_file(
    raw_path: Path,
    doc_id: str,
    safe_name: str,
    progress_cb: Callable[[str, int, int], None] | None = None,
) -> dict[str, Any]:
    start = time.time()
    raw_str = raw_path.read_bytes().decode("utf-8", errors="ignore")
    parts = re.split(r"\[\[PAGE\s+(\d+)\]\]", raw_str)

    raw_pages: list[tuple[int, str]] = []
    if len(parts) > 1:
        for i in range(1, len(parts), 2):
            raw_pages.append((int(parts[i]), parts[i + 1]))
    else:
        normalized = re.sub(r"\r\n", "\n", raw_str)
        normalized = re.sub(r"\n\s*\n+", "\n\n", normalized)
        chunks: list[str] = []
        cur = ""
        for para in normalized.split("\n\n"):
            if len(cur) + len(para) > 3000 and cur:
                chunks.append(cur)
                cur = ""
            cur += para + "\n\n"
        if cur.strip():
            chunks.append(cur)
        if not chunks:
            chunks = [""]
        raw_pages = [(idx, chunk) for idx, chunk in enumerate(chunks, 1)]

    total = len(raw_pages)
    if progress_cb:
        progress_cb("ingesting_pages", 0, total)

    pages_data: list[dict[str, Any]] = []
    for p_num, body in raw_pages:
        clean_body = body.strip()
        quality, _ = check_page_quality(clean_body, None)
        pages_data.append(
            {
                "page": p_num,
                "text": clean_body,
                "source": "text",
                "quality": quality,
                "ocr_used": False,
                "ocr_confidence": None,
                "ocr_language": None,
                "detected_script": None,
                "is_empty": len(clean_body) == 0,
                "tables": [],
            }
        )
        if progress_cb:
            progress_cb("ingesting_pages", len(pages_data), total)

    return {
        "doc_id": doc_id,
        "source": f"uploads/{doc_id}/{raw_path.name}",
        "filename": safe_name,
        "format": "txt",
        "total_pages": len(pages_data),
        "processing_time_seconds": round(time.time() - start, 3),
        "ocr_pages_count": 0,
        "tables_count": 0,
        "pages": pages_data,
        "tables": [],
    }


def ingest_uploaded_document(
    raw_path: Path,
    doc_dir: Path,
    doc_id: str,
    safe_name: str,
    progress_cb: Callable[[str, int, int], None] | None = None,
) -> dict[str, Any]:
    """Ingest a validated upload (.pdf/.html/.htm/.txt) into doc_dir cleanly."""
    suffix = raw_path.suffix.lower()

    if suffix == ".pdf":
        start = time.time()
        pages_data: list[dict[str, Any]] = []
        all_tables: list[dict[str, Any]] = []

        with fitz.open(raw_path) as doc:
            total = len(doc)
            if progress_cb:
                progress_cb("ingesting_pages", 0, total)
            for page_number, page in enumerate(doc, 1):
                page_info = ingest_pdf_page(page, page_number, raw_path.name)
                page_info["source"] = _normalize_source(page_info.get("source"), bool(page_info.get("ocr_used")))
                pages_data.append(page_info)
                if page_info.get("tables"):
                    all_tables.extend(page_info["tables"])
                if progress_cb:
                    progress_cb("ingesting_pages", page_number, total)

        payload: dict[str, Any] = {
            "doc_id": doc_id,
            "source": f"uploads/{doc_id}/{raw_path.name}",
            "filename": safe_name,
            "format": "pdf",
            "total_pages": len(pages_data),
            "processing_time_seconds": round(time.time() - start, 3),
            "ocr_pages_count": sum(1 for p in pages_data if p.get("ocr_used")),
            "tables_count": len(all_tables),
            "pages": pages_data,
            "tables": all_tables,
        }
    elif suffix in (".html", ".htm"):
        if progress_cb:
            progress_cb("ingesting_html", 0, 0)
        tmp_dir = doc_dir / "_tmp_html"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        payload = ingest_html(raw_path, out_dir=tmp_dir)
        # Normalize path & source fields safely
        payload["doc_id"] = doc_id
        payload["source"] = f"uploads/{doc_id}/{raw_path.name}"
        payload["filename"] = safe_name
        for p in payload.get("pages", []):
            p["source"] = _normalize_source(p.get("source"), bool(p.get("ocr_used")))
        for f in tmp_dir.glob("*"):
            f.unlink(missing_ok=True)
        tmp_dir.rmdir()
        if progress_cb:
            total = int(payload.get("total_pages", 0))
            progress_cb("ingesting_html", total, total)
    elif suffix == ".txt":
        payload = _ingest_txt_file(raw_path, doc_id, safe_name, progress_cb=progress_cb)
    else:
        raise ValueError("Unsupported file extension.")

    _write_json_atomic(doc_dir / "ingested.json", payload)
    _write_txt_atomic(doc_dir / "ingested.txt", payload.get("pages", []))
    return payload
