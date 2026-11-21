"""app/api/main.py

Stage 7a-1 FastAPI backend skeleton: health, metadata, upload, ingestion status, and page retrieval.
Zero Gemini API calls. Zero stack traces or host paths in error responses.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.api.chat_service import handle_chat_request, read_chat_history
from app.api.ingest_service import _write_json_atomic
from app.api.jobs import UPLOADS_DIR, get_doc_dir, is_cached_or_active, read_status, start_ingest_job
from app.api.task_service import ALLOWED_TASK_KINDS, get_task_status, load_app_config, start_task

MAX_UPLOAD_MB = 25
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
DOC_ID_RE = re.compile(r"^[0-9a-f]{12}$")

_EXT_MAP = {
    "pdf": {".pdf"},
    "html": {".html", ".htm"},
    "txt": {".txt"},
}


class ChatRequest(BaseModel):
    question: str


class TranslateRequest(BaseModel):
    source: str
    language: str
    turn_index: int | None = None


def _get_allowed_types_and_exts() -> tuple[list[str], set[str]]:
    types = [t for t in load_app_config().get("allowed_types", ["pdf", "html", "txt"]) if t in _EXT_MAP]
    exts: set[str] = set()
    for t in types:
        exts.update(_EXT_MAP[t])
    return types, exts

app = FastAPI(title="AI Loan Agreement Analyzer API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def safe_exception_handler(_request: Any, _exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


def _validate_doc_id(doc_id: str) -> str:
    if not DOC_ID_RE.fullmatch(doc_id):
        raise HTTPException(status_code=400, detail="Invalid doc_id format; expected 12 hex characters.")
    uploads_root = UPLOADS_DIR.resolve()
    doc_dir = get_doc_dir(doc_id).resolve()
    try:
        doc_dir.relative_to(uploads_root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid doc_id path.") from exc
    return doc_id


def _sanitize_filename(raw_name: str | None) -> str:
    base = Path(raw_name or "document").name
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._")
    return (cleaned or "document")[:120]


@app.get("/api/health")
def get_health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/meta")
def get_meta() -> dict[str, Any]:
    allowed_types, _ = _get_allowed_types_and_exts()
    return {
        "disclaimer": "This system provides information, not legal or financial advice.",
        "upload_notice": "Upload only public documents.",
        "max_upload_mb": MAX_UPLOAD_MB,
        "allowed_types": allowed_types,
    }


@app.post("/api/documents")
async def upload_document(file: UploadFile = File(...)) -> dict[str, Any]:
    allowed_types, allowed_exts = _get_allowed_types_and_exts()
    orig_name = file.filename or "document"
    ext = Path(orig_name).suffix.lower()
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_types)}.",
        )

    chunks: list[bytes] = []
    total_size = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail=f"File exceeds {MAX_UPLOAD_MB} MB upload limit.")
        chunks.append(chunk)

    raw_bytes = b"".join(chunks)
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Real content / magic-bytes validation
    if ext == ".pdf":
        if not raw_bytes.startswith(b"%PDF"):
            raise HTTPException(status_code=400, detail="Invalid PDF file content.")
    else:
        if b"\x00" in raw_bytes or raw_bytes.startswith(b"MZ"):
            raise HTTPException(status_code=400, detail="Invalid text/html file content.")

    sha256_hex = hashlib.sha256(raw_bytes).hexdigest()
    doc_id = sha256_hex[:12]
    safe_name = _sanitize_filename(orig_name)

    cached, existing_state = is_cached_or_active(doc_id)
    if cached:
        return {
            "doc_id": doc_id,
            "filename": safe_name,
            "cached": True,
            "state": existing_state or "ready",
        }

    doc_dir = get_doc_dir(doc_id)
    doc_dir.mkdir(parents=True, exist_ok=True)
    storage_ext = ".html" if ext in (".html", ".htm") else ext
    raw_path = doc_dir / f"source{storage_ext}"
    tmp_path = doc_dir / f"source{storage_ext}.tmp"
    tmp_path.write_bytes(raw_bytes)
    tmp_path.replace(raw_path)

    _write_json_atomic(
        doc_dir / "meta.json",
        {
            "doc_id": doc_id,
            "filename": safe_name,
            "sha256": sha256_hex,
            "ext": storage_ext,
            "size_bytes": len(raw_bytes),
        },
    )

    st = start_ingest_job(doc_id=doc_id, raw_path=raw_path, safe_name=safe_name)
    return {
        "doc_id": doc_id,
        "filename": safe_name,
        "cached": False,
        "state": st["state"],
    }


@app.get("/api/documents/{doc_id}/status")
def get_document_status(doc_id: str) -> dict[str, Any]:
    valid_id = _validate_doc_id(doc_id)
    st = read_status(valid_id)
    if st is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return {
        "state": st.get("state", "failed"),
        "stage": st.get("stage", ""),
        "pages_done": int(st.get("pages_done", 0)),
        "pages_total": int(st.get("pages_total", 0)),
        "error": st.get("error"),
    }


@app.get("/api/documents/{doc_id}/pages/{n}")
def get_document_page(doc_id: str, n: int) -> dict[str, Any]:
    valid_id = _validate_doc_id(doc_id)
    if n < 1:
        raise HTTPException(status_code=404, detail="Page not found.")
    ing_path = get_doc_dir(valid_id) / "ingested.json"
    if not ing_path.is_file():
        raise HTTPException(status_code=404, detail="Document not ingested or not found.")

    try:
        data = json.loads(ing_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to load ingested document.") from exc

    page_obj = next((p for p in data.get("pages", []) if int(p.get("page", -1)) == n), None)
    if page_obj is None:
        raise HTTPException(status_code=404, detail="Page not found.")

    src = "ocr" if page_obj.get("source") == "ocr" or page_obj.get("ocr_used") else "text"
    return {
        "page": int(page_obj["page"]),
        "text": str(page_obj.get("text", "")),
        "quality": str(page_obj.get("quality", "BAD")),
        "source": src,
    }


def _validate_task_target(doc_id: str, kind: str, require_ready: bool = False) -> tuple[str, str]:
    valid_id = _validate_doc_id(doc_id)
    if kind not in ALLOWED_TASK_KINDS:
        raise HTTPException(status_code=404, detail="Unknown task kind.")
    st = read_status(valid_id)
    if st is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    if require_ready:
        ing_ok = (get_doc_dir(valid_id) / "ingested.json").is_file()
        if st.get("state") != "ready" or not ing_ok:
            raise HTTPException(status_code=409, detail="Document is not ready for analysis.")
    return valid_id, kind


@app.post("/api/documents/{doc_id}/tasks/{kind}")
def start_document_task(doc_id: str, kind: str) -> JSONResponse:
    valid_id, task_kind = _validate_task_target(doc_id, kind, require_ready=True)
    status_code, payload = start_task(valid_id, task_kind)
    return JSONResponse(status_code=status_code, content=payload)


@app.get("/api/documents/{doc_id}/tasks/{kind}")
def get_document_task(doc_id: str, kind: str) -> dict[str, Any]:
    valid_id, task_kind = _validate_task_target(doc_id, kind, require_ready=False)
    return get_task_status(valid_id, task_kind)


def _validate_doc_ready(doc_id: str) -> str:
    valid_id = _validate_doc_id(doc_id)
    st = read_status(valid_id)
    if st is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    ing_ok = (get_doc_dir(valid_id) / "ingested.json").is_file()
    if st.get("state") != "ready" or not ing_ok:
        raise HTTPException(status_code=409, detail="Document is not ready for chat.")
    return valid_id


@app.post("/api/documents/{doc_id}/chat")
def post_document_chat(doc_id: str, body: ChatRequest) -> dict[str, Any]:
    valid_id = _validate_doc_ready(doc_id)
    return handle_chat_request(valid_id, body.question)


@app.get("/api/documents/{doc_id}/chat")
def get_document_chat(doc_id: str) -> dict[str, Any]:
    valid_id = _validate_doc_id(doc_id)
    st = read_status(valid_id)
    if st is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return {"doc_id": valid_id, "turns": read_chat_history(valid_id)}


_TRANSLATE_HOOK: Any = None


@app.post("/api/documents/{doc_id}/translate")
def post_document_translate(doc_id: str, body: TranslateRequest) -> dict[str, Any]:
    valid_id = _validate_doc_id(doc_id)
    st = read_status(valid_id)
    if st is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    clean_source = (body.source or "").strip().lower()
    if clean_source not in ("summary", "chat"):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid source '{body.source}'. Allowed: 'summary', 'chat'.",
        )

    clean_lang = (body.language or "").strip().lower()
    if clean_lang not in ("hi", "ta", "bn", "pa", "ml"):
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported language '{body.language}'. Allowed: 'hi', 'ta', 'bn', 'pa', 'ml'.",
        )

    if clean_source == "chat":
        if body.turn_index is None or body.turn_index < 0:
            raise HTTPException(
                status_code=422,
                detail="turn_index is required for chat translation and must be an integer >= 0.",
            )
        turns = read_chat_history(valid_id)
        if body.turn_index >= len(turns):
            raise HTTPException(
                status_code=422,
                detail=f"turn_index {body.turn_index} is out of range (total turns: {len(turns)}).",
            )
        turn = turns[body.turn_index]
        if turn.get("category") == "advice":
            text_to_translate = (
                "This system gives document information only. It does not give legal or financial advice, "
                "so it cannot say whether to sign or accept this agreement. It can show the risks, fees, penalties "
                "or foreclosure clauses stated in the document."
            )
        else:
            text_to_translate = str(turn.get("answer", "")).strip()
        turn_key = str(body.turn_index)
    else:
        # clean_source == "summary"
        sum_path = (
            get_doc_dir(valid_id)
            / str(load_app_config().get("results_dir_name", "results"))
            / "summary.json"
        )
        if not sum_path.is_file():
            raise HTTPException(status_code=404, detail="Summary not found for this document.")
        try:
            sum_data = json.loads(sum_path.read_text(encoding="utf-8"))
            sum_result = sum_data.get("result", {}) if isinstance(sum_data, dict) else {}
            text_to_translate = str(sum_result.get("short", "")).strip()
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to load summary: {exc}")
        turn_key = str(body.turn_index) if body.turn_index is not None else "0"

    cfg = load_app_config()
    results_dir_name = str(cfg.get("results_dir_name", "results"))
    trans_dir = get_doc_dir(valid_id) / results_dir_name / "translations"
    trans_dir.mkdir(parents=True, exist_ok=True)
    cache_file = trans_dir / f"{clean_source}_{turn_key}_{clean_lang}.json"

    if cache_file.is_file():
        try:
            cached_data = json.loads(cache_file.read_text(encoding="utf-8"))
            if isinstance(cached_data, dict):
                cached_data["live_calls"] = 0
                return cached_data
        except Exception:
            pass

    if _TRANSLATE_HOOK is not None:
        res = _TRANSLATE_HOOK(text_to_translate, clean_lang)
    else:
        from src.translate.translate_text import translate_text
        res = translate_text(text_to_translate, clean_lang)

    if isinstance(res, dict):
        try:
            _write_json_atomic(cache_file, res)
        except Exception:
            pass

    return res



