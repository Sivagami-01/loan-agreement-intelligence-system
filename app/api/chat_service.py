"""app/api/chat_service.py

Stage 7a-2b Q&A chat service wrapping src/qa/ask.py (`ask()`).
Enforces:
- Single concurrent request per doc_id (429 when busy)
- Daily soft quota guard + per-question live-call budget (6 calls)
- Server-side quote verification via src/qa/verify_quotes.py
- Last-50-turn history persistence in data/processed/uploads/<doc_id>/results/chat.json
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from app.api.doc_bridge import ensure_qa_doc_bridge_installed, load_uploaded_document
from app.api.ingest_service import _write_json_atomic
from app.api.jobs import get_doc_dir
from app.api.task_service import (
    BudgetedGeminiClient,
    DailyQuotaExceededError,
    TaskBudgetExceededError,
    count_today_live_calls,
    load_app_config,
)
from src.llm.gemini_client import load_model_config
from src.qa.ask import ask
from src.qa.verify_quotes import verify_evidence

_CHAT_LOCK = threading.Lock()
_ACTIVE_CHAT_DOCS: set[str] = set()
_HISTORY_LOCK = threading.Lock()
MAX_CHAT_HISTORY = 50


def get_chat_history_path(doc_id: str, results_dir_name: str = "results") -> Path:
    return get_doc_dir(doc_id) / results_dir_name / "chat.json"


def read_chat_history(doc_id: str) -> list[dict[str, Any]]:
    cfg = load_app_config()
    path = get_chat_history_path(doc_id, cfg["results_dir_name"])
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        turns = data.get("turns", []) if isinstance(data, dict) else []
        return list(turns[-MAX_CHAT_HISTORY:])
    except Exception:
        return []


def _append_chat_turn(doc_id: str, results_dir_name: str, turn: dict[str, Any]) -> None:
    path = get_chat_history_path(doc_id, results_dir_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _HISTORY_LOCK:
        existing: list[dict[str, Any]] = []
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and isinstance(data.get("turns"), list):
                    existing = list(data["turns"])
            except Exception:
                existing = []
        existing.append(turn)
        trimmed = existing[-MAX_CHAT_HISTORY:]
        _write_json_atomic(path, {"doc_id": doc_id, "turns": trimmed})


def _to_json_safe(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, dict):
        return {str(k): _to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_json_safe(x) for x in obj]
    return obj


def _serialize_calc_fields(res: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in ("inputs", "missing", "formula_name", "steps", "assumptions", "currency", "result"):
        if key in res:
            out[key] = _to_json_safe(res[key])
    return out


def handle_chat_request(doc_id: str, question: str) -> dict[str, Any]:
    """Executes one grounded chat turn for `doc_id` cleanly."""
    clean_q = (question or "").strip()
    if not clean_q:
        raise HTTPException(status_code=422, detail="Question must not be empty.")

    with _CHAT_LOCK:
        if doc_id in _ACTIVE_CHAT_DOCS:
            raise HTTPException(
                status_code=429,
                detail="Another chat request is already in progress for this document. Please wait.",
            )
        _ACTIVE_CHAT_DOCS.add(doc_id)

    try:
        cfg = load_app_config()
        notice = cfg["notices"]["task_output"]
        quota_msg = cfg["notices"]["quota_blocked"]
        chat_budget = int(cfg["task_budgets"].get("chat", 6))
        daily_limit = int(cfg["daily_soft_limit"])
        results_dir_name = str(cfg.get("results_dir_name", "results"))

        today_calls = count_today_live_calls()
        if today_calls >= daily_limit:
            return {
                "category": None,
                "state": "quota_blocked",
                "status": "quota_blocked",
                "answer": quota_msg,
                "message": quota_msg,
                "evidence": [],
                "final_check": None,
                "verifier_independent": None,
                "model_used": None,
                "models_used": {},
                "fallback_used": False,
                "live_calls": 0,
                "flags": ["quota_blocked"],
                "notice": notice,
            }

        ensure_qa_doc_bridge_installed()
        _, doc_pages = load_uploaded_document(doc_id)
        client = BudgetedGeminiClient(
            task_budget=chat_budget,
            daily_limit=daily_limit,
            today_baseline=today_calls,
        )

        try:
            ask_res = ask(
                doc_id=doc_id,
                question=clean_q,
                client=client,
                verify=True,
                doc_pages=doc_pages,
            )
        except DailyQuotaExceededError:
            return {
                "category": None,
                "state": "quota_blocked",
                "status": "quota_blocked",
                "answer": quota_msg,
                "message": quota_msg,
                "evidence": [],
                "final_check": None,
                "verifier_independent": None,
                "model_used": None,
                "models_used": client.models_used,
                "fallback_used": False,
                "live_calls": client.api_calls_made,
                "flags": ["quota_blocked"],
                "notice": notice,
            }
        except TaskBudgetExceededError as exc:
            return {
                "category": None,
                "state": "failed",
                "status": "failed",
                "answer": str(exc),
                "evidence": [],
                "final_check": None,
                "verifier_independent": None,
                "model_used": None,
                "models_used": client.models_used,
                "fallback_used": False,
                "live_calls": client.api_calls_made,
                "flags": ["chat_budget_reached"],
                "notice": notice,
            }

        if client.daily_quota_stopped:
            return {
                "category": ask_res.get("category"),
                "state": "quota_blocked",
                "status": "quota_blocked",
                "answer": quota_msg,
                "message": quota_msg,
                "evidence": [],
                "final_check": None,
                "verifier_independent": None,
                "model_used": ask_res.get("model_used"),
                "models_used": client.models_used,
                "fallback_used": False,
                "live_calls": client.api_calls_made,
                "flags": ["quota_blocked"],
                "notice": notice,
            }

        if client.budget_stopped_reason:
            return {
                "category": ask_res.get("category"),
                "state": "failed",
                "status": "failed",
                "answer": client.budget_stopped_reason,
                "evidence": [],
                "final_check": None,
                "verifier_independent": None,
                "model_used": ask_res.get("model_used"),
                "models_used": client.models_used,
                "fallback_used": False,
                "live_calls": client.api_calls_made,
                "flags": ["chat_budget_reached"],
                "notice": notice,
            }

        # Server-side re-verification of every returned evidence quote
        raw_ev = list(ask_res.get("evidence") or [])
        verified_ev, srv_flags = verify_evidence(doc_pages, raw_ev)
        dropped_cnt = len(raw_ev) - len(verified_ev)
        flags = list(ask_res.get("flags") or [])
        for sf in srv_flags:
            if sf not in flags:
                flags.append(sf)

        status = str(ask_res.get("status", "unknown"))
        answer_text = str(ask_res.get("answer", ""))
        category = str(ask_res.get("category", ""))

        if dropped_cnt > 0:
            flags.append(f"quote_dropped:{dropped_cnt}")
        if category == "fact" and status == "ok" and not verified_ev:
            status = "unverified"
            answer_text = ""
            if "evidence_unverified_server" not in flags:
                flags.append("evidence_unverified_server")

        models_cfg = load_model_config()
        main_model = models_cfg.get("main", "")
        bulk_model = models_cfg.get("bulk", "")
        model_used = ask_res.get("model_used")
        fallback_used = False
        if category == "fact" and model_used and main_model and model_used != main_model:
            fallback_used = True
        if fallback_used and "model_fallback" not in flags:
            flags.append("model_fallback")

        response_payload: dict[str, Any] = {
            "category": category,
            "status": status,
            "answer": answer_text,
            "evidence": [
                {"quote": str(e.get("quote", "")), "page": int(e["page"])}
                for e in verified_ev
                if e.get("page") is not None
            ],
            "final_check": ask_res.get("final_check"),
            "verifier_independent": ask_res.get("verifier_independent"),
            "verifier_verdict": ask_res.get("verifier_verdict"),
            "verifier_model_used": ask_res.get("verifier_model_used"),
            "model_used": model_used,
            "models_used": client.models_used,
            "fallback_used": fallback_used,
            "configured_main_model": main_model,
            "configured_bulk_model": bulk_model,
            "live_calls": client.api_calls_made,
            "quotes_checked": len(raw_ev),
            "quotes_verified": len(verified_ev),
            "unverified_dropped": dropped_cnt,
            "flags": flags,
            "router_fallback": bool(ask_res.get("router_fallback", False)),
            "language": ask_res.get("language", "en"),
            "notice": notice,
        }
        response_payload.update(_serialize_calc_fields(ask_res))

        turn_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "question": clean_q,
            **response_payload,
        }
        _append_chat_turn(doc_id, results_dir_name, turn_record)
        return response_payload
    finally:
        with _CHAT_LOCK:
            _ACTIVE_CHAT_DOCS.discard(doc_id)
