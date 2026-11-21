"""app/api/doc_bridge.py

Bridge allowing Stage 2/3/4 src modules to read uploaded documents from
data/processed/uploads/<doc_id>/ without writing to data/processed/ingested/
or modifying any files in src/.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import src.calc.extract_inputs as _calc_extract_mod
import src.qa.answer as _qa_answer_mod
import src.qa.ask as _qa_ask_mod
import src.qa.doc_loader as _doc_loader_mod
import src.qa.retrieve as _qa_retrieve_mod
from app.api.jobs import UPLOADS_DIR, get_doc_dir

DOC_ID_RE = re.compile(r"^[0-9a-f]{12}$")
_ORIG_LOAD_DOCUMENT = _doc_loader_mod.load_document
_BRIDGE_INSTALLED = False


def is_uploaded_doc_id(doc_id: str) -> bool:
    """Return True iff doc_id is 12 lowercase hex chars with an uploaded ingested file."""
    if not DOC_ID_RE.fullmatch(doc_id or ""):
        return False
    uploads_root = UPLOADS_DIR.resolve()
    doc_dir = get_doc_dir(doc_id).resolve()
    try:
        doc_dir.relative_to(uploads_root)
    except ValueError:
        return False
    return (doc_dir / "ingested.json").is_file() or (doc_dir / "ingested.txt").is_file()


def load_uploaded_meta(doc_id: str) -> dict[str, Any]:
    """Loads uploads/<doc_id>/meta.json safely if present."""
    if not DOC_ID_RE.fullmatch(doc_id or ""):
        return {}
    meta_path = get_doc_dir(doc_id) / "meta.json"
    if not meta_path.is_file():
        return {}
    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def load_uploaded_table_rows_by_page(doc_id: str) -> dict[int, list[str]]:
    """Extracts table row anchors per page from uploads/<doc_id>/ingested.json."""
    if not DOC_ID_RE.fullmatch(doc_id or ""):
        return {}
    json_path = get_doc_dir(doc_id) / "ingested.json"
    if not json_path.is_file():
        return {}
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    by_page: dict[int, list[str]] = {}
    for pg in data.get("pages", []):
        pnum = pg.get("page")
        if not isinstance(pnum, int):
            continue
        anchors: list[str] = []
        for tb in pg.get("tables", []):
            for row in tb.get("rows", []):
                cells = [" ".join(str(c or "").split()) for c in row if str(c or "").strip()]
                if not cells:
                    continue
                first_cell = cells[0]
                second_cell = cells[1] if len(cells) > 1 else ""
                anchor = first_cell if len(first_cell) >= 6 or not second_cell else f"{first_cell} {second_cell}"
                anchor = " ".join(anchor.split())
                if len(anchor) >= 4:
                    anchors.append(anchor[:40])
        if anchors:
            by_page[pnum] = anchors
    return by_page


def load_uploaded_document(doc_id: str) -> tuple[str, dict[int, str]]:
    """Loads (full_text, doc_pages) for an uploaded 12-hex doc_id."""
    if not DOC_ID_RE.fullmatch(doc_id or ""):
        raise ValueError("Invalid uploaded doc_id format.")
    uploads_root = UPLOADS_DIR.resolve()
    doc_dir = get_doc_dir(doc_id).resolve()
    doc_dir.relative_to(uploads_root)

    json_path = doc_dir / "ingested.json"
    txt_path = doc_dir / "ingested.txt"

    doc_pages: dict[int, str] = {}
    full_text = ""

    if json_path.is_file():
        data = json.loads(json_path.read_text(encoding="utf-8"))
        for p in data.get("pages", []):
            p_num = int(p.get("page", 0))
            if p_num > 0:
                doc_pages[p_num] = str(p.get("text", ""))

    if txt_path.is_file():
        full_text = txt_path.read_text(encoding="utf-8")
        if not doc_pages:
            parts = re.compile(r"\[\[PAGE\s+(\d+)\]\]").split(full_text)
            if len(parts) > 1:
                for i in range(1, len(parts), 2):
                    doc_pages[int(parts[i])] = parts[i + 1]

    if not full_text and doc_pages:
        full_text = "\n\n".join(
            f"[[PAGE {p_num}]]\n{doc_pages[p_num]}" for p_num in sorted(doc_pages)
        )

    if not doc_pages:
        raise FileNotFoundError(f"Uploaded ingested pages missing for doc_id={doc_id!r}")

    return full_text, doc_pages


def load_document_bridge(doc_id: str) -> tuple[str, dict[int, str]]:
    """Reads from uploads/<doc_id> when 12-hex upload exists; otherwise uses original load_document."""
    if is_uploaded_doc_id(doc_id):
        return load_uploaded_document(doc_id)
    return _ORIG_LOAD_DOCUMENT(doc_id)


def ensure_qa_doc_bridge_installed() -> None:
    """Wires load_document_bridge into QA/calc modules in RAM without editing src/ files."""
    global _BRIDGE_INSTALLED
    if _BRIDGE_INSTALLED:
        return
    _doc_loader_mod.load_document = load_document_bridge  # type: ignore[assignment]
    _qa_answer_mod.load_document = load_document_bridge  # type: ignore[assignment]
    _qa_ask_mod.load_document = load_document_bridge  # type: ignore[assignment]
    _qa_retrieve_mod.load_document = load_document_bridge  # type: ignore[assignment]
    _calc_extract_mod.load_document = load_document_bridge  # type: ignore[assignment]
    _BRIDGE_INSTALLED = True
