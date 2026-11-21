"""app/api/task_service.py

Stage 7a-2a background task runner for grounded summary and key-info extraction.
- Reads config/app.yaml (task_budgets: summary=10, keyinfo=20; daily_soft_limit=60; results_dir_name="results")
- Counts today's rows in data/processed/llm_log.csv before starting (returns quota_blocked cleanly)
- Enforces strict per-task live-call caps without silent retries
- Persists finished results to data/processed/uploads/<doc_id>/results/<kind>.json
"""

from __future__ import annotations

import csv
import json
import threading
import time
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator
from zoneinfo import ZoneInfo

import yaml

from app.api.doc_bridge import load_uploaded_document
from app.api.ingest_service import _write_json_atomic
from app.api.jobs import ROOT, get_doc_dir
from app.api.risk_service import run_risk_analysis
from src.extract.extract_fields import extract_key_info, load_extract_config
from src.llm.gemini_client import LOG_FILE, GeminiClient
from src.summarize.summarize import load_summarize_config, summarize_document

APP_CONFIG_PATH = ROOT / "config" / "app.yaml"
ALLOWED_TASK_KINDS = ("summary", "keyinfo", "risk")

DEFAULT_NOTICE = (
    "Automated output. Check each quote against the cited page. "
    "Information, not legal or financial advice."
)
DEFAULT_QUOTA_MSG = (
    "Today's free AI allowance is used up. Try again tomorrow or use a cached document."
)

_TASK_LOCK = threading.Lock()
_TASK_STATES: dict[tuple[str, str], dict[str, Any]] = {}
_TASK_THREADS: dict[tuple[str, str], threading.Thread] = {}

_CONFIG_LOCK = threading.Lock()
_CONFIG_OVERRIDES: dict[str, Any] = {}


class TaskBudgetExceededError(RuntimeError):
    """Raised when a task reaches its per-task live-call budget."""


class DailyQuotaExceededError(RuntimeError):
    """Raised when the daily soft live-call limit is reached."""


def load_app_config(config_path: Path | None = None) -> dict[str, Any]:
    """Loads config/app.yaml merged with defaults and any active in-process overrides."""
    path = config_path or APP_CONFIG_PATH
    data: dict[str, Any] = {}
    if path.is_file():
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            data = loaded

    cfg: dict[str, Any] = {
        "daily_soft_limit": int(data.get("daily_soft_limit", 60)),
        "quota_timezone": str(data.get("quota_timezone", "America/Los_Angeles") or "America/Los_Angeles"),
        "results_dir_name": str(data.get("results_dir_name", "results") or "results"),
        "allowed_types": [
            str(x).lower().strip()
            for x in (data.get("allowed_types") or ["pdf", "html", "txt"])
        ],
        "task_budgets": {
            "summary": int((data.get("task_budgets") or {}).get("summary", 10)),
            "keyinfo": int((data.get("task_budgets") or {}).get("keyinfo", 20)),
            "risk": int((data.get("task_budgets") or {}).get("risk", 15)),
            "chat": int((data.get("task_budgets") or {}).get("chat", 6)),
        },
        "notices": {
            "task_output": str(
                (data.get("notices") or {}).get("task_output", DEFAULT_NOTICE)
            ),
            "quota_blocked": str(
                (data.get("notices") or {}).get("quota_blocked", DEFAULT_QUOTA_MSG)
            ),
        },
    }

    with _CONFIG_LOCK:
        if "daily_soft_limit" in _CONFIG_OVERRIDES:
            cfg["daily_soft_limit"] = int(_CONFIG_OVERRIDES["daily_soft_limit"])
        if "quota_timezone" in _CONFIG_OVERRIDES:
            cfg["quota_timezone"] = str(_CONFIG_OVERRIDES["quota_timezone"])
        if "results_dir_name" in _CONFIG_OVERRIDES:
            cfg["results_dir_name"] = str(_CONFIG_OVERRIDES["results_dir_name"])
        if isinstance(_CONFIG_OVERRIDES.get("task_budgets"), dict):
            cfg["task_budgets"].update(_CONFIG_OVERRIDES["task_budgets"])

    return cfg


@contextmanager
def override_app_config(**overrides: Any) -> Iterator[None]:
    """Thread-safe temporary config override for tests (never writes to config/app.yaml)."""
    with _CONFIG_LOCK:
        prev = deepcopy(_CONFIG_OVERRIDES)
        _CONFIG_OVERRIDES.update(overrides)
    try:
        yield
    finally:
        with _CONFIG_LOCK:
            _CONFIG_OVERRIDES.clear()
            _CONFIG_OVERRIDES.update(prev)


def reset_in_memory_task_cache() -> None:
    """Clears in-memory task states (used by persistence tests to simulate restart)."""
    with _TASK_LOCK:
        _TASK_STATES.clear()


def _resolve_tz(tz_name: str | None) -> Any:
    if not tz_name or tz_name.upper() == "UTC":
        return timezone.utc
    if tz_name.upper() in ("IST", "ASIA/KOLKATA"):
        try:
            return ZoneInfo("Asia/Kolkata")
        except Exception:
            return timezone(timedelta(hours=5, minutes=30))
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return timezone.utc


def count_today_live_calls(log_path: Path = LOG_FILE, tz_name: str | None = None) -> int:
    """Counts rows logged for today in data/processed/llm_log.csv using quota_timezone."""
    if not log_path.is_file():
        return 0
    tz_label = tz_name or str(load_app_config().get("quota_timezone", "America/Los_Angeles"))
    tz = _resolve_tz(tz_label)
    today_in_tz = datetime.now(tz).date()
    count = 0
    try:
        with log_path.open("r", encoding="utf-8", errors="ignore", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                ts_raw = (row.get("time") or "").strip()
                if not ts_raw:
                    continue
                try:
                    dt = datetime.fromisoformat(ts_raw)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    if dt.astimezone(tz).date() == today_in_tz:
                        count += 1
                except ValueError:
                    continue
    except OSError:
        return 0
    return count


def count_today_calls_by_timezone(log_path: Path = LOG_FILE) -> dict[str, int]:
    """Returns today's row count under UTC, IST, and configured quota_timezone."""
    qtz = str(load_app_config().get("quota_timezone", "America/Los_Angeles"))
    return {
        "UTC": count_today_live_calls(log_path, tz_name="UTC"),
        "IST": count_today_live_calls(log_path, tz_name="Asia/Kolkata"),
        qtz: count_today_live_calls(log_path, tz_name=qtz),
    }


def get_result_file_path(doc_id: str, kind: str, results_dir_name: str = "results") -> Path:
    return get_doc_dir(doc_id) / results_dir_name / f"{kind}.json"


def read_saved_task_result(doc_id: str, kind: str) -> dict[str, Any] | None:
    cfg = load_app_config()
    path = get_result_file_path(doc_id, kind, cfg["results_dir_name"])
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("state") == "done":
            return data
    except Exception:
        pass
    return None


class BudgetedGeminiClient(GeminiClient):
    """GeminiClient enforcing per-task and daily live-call caps without silent retries."""

    def __init__(
        self,
        task_budget: int,
        daily_limit: int,
        today_baseline: int,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.task_budget = int(task_budget)
        self.daily_limit = int(daily_limit)
        self.today_baseline = int(today_baseline)
        self.models_used: dict[str, int] = {}
        self.live_models_used: dict[str, int] = {}
        self.budget_stopped_reason: str | None = None
        self.daily_quota_stopped: bool = False

    def _send_request(
        self,
        model: str,
        prompt: str,
        image_bytes: bytes | None = None,
        mime_type: str = "image/png",
        temperature: float | None = None,
    ) -> tuple[str, float]:
        if self.daily_limit >= 0 and (self.today_baseline + self.api_calls_made) >= self.daily_limit:
            self.daily_quota_stopped = True
            raise DailyQuotaExceededError(DEFAULT_QUOTA_MSG)
        if self.api_calls_made >= self.task_budget:
            self.budget_stopped_reason = f"Per-task live-call budget ({self.task_budget}) reached."
            raise TaskBudgetExceededError(self.budget_stopped_reason)

        text, latency = super()._send_request(
            model=model,
            prompt=prompt,
            image_bytes=image_bytes,
            mime_type=mime_type,
            temperature=temperature,
        )
        self.live_models_used[model] = self.live_models_used.get(model, 0) + 1
        return text, latency

    def generate(
        self,
        prompt: str,
        image_bytes: bytes | None = None,
        mime_type: str = "image/png",
        model_alias: str = "main",
        temperature: float | None = None,
    ) -> str:
        if self.daily_quota_stopped:
            raise DailyQuotaExceededError(DEFAULT_QUOTA_MSG)
        if self.budget_stopped_reason:
            raise TaskBudgetExceededError(self.budget_stopped_reason)

        primary_model = self.models.get(model_alias, self.models.get("main", "gemini-3.8-flash"))
        bulk_model = self.models.get("bulk", "gemini-3.5-flash-lite")
        cache_key = self._compute_hash(primary_model, prompt, image_bytes, temperature)
        cache_path = self.cache_dir / f"{cache_key}.json"

        # If primary model is not in cache, check if bulk fallback cache has a valid hit
        if not cache_path.is_file() and primary_model != bulk_model:
            bulk_key = self._compute_hash(bulk_model, prompt, image_bytes, temperature)
            bulk_path = self.cache_dir / f"{bulk_key}.json"
            if bulk_path.is_file():
                model_alias = "bulk"

        text = super().generate(
            prompt=prompt,
            image_bytes=image_bytes,
            mime_type=mime_type,
            model_alias=model_alias,
            temperature=temperature,
        )
        used = self.last_model_used or self.models.get(model_alias, "unknown")
        self.models_used[used] = self.models_used.get(used, 0) + 1
        return text


def _format_keyinfo_result(raw_res: dict[str, Any], doc_pages: dict[int, str]) -> dict[str, Any]:
    out = deepcopy(raw_res)
    formatted_fields: list[dict[str, Any]] = []
    formatted_by_field: dict[str, dict[str, Any]] = {}

    for rec in out.get("fields", []):
        item = dict(rec)
        ev = list(item.get("evidence", []))
        item["quotes"] = [str(e.get("quote", "")) for e in ev if str(e.get("quote", "")).strip()]
        item["page"] = int(ev[0]["page"]) if ev and ev[0].get("page") is not None else None
        formatted_fields.append(item)
        formatted_by_field[str(item.get("field", ""))] = item

    out["fields"] = formatted_fields
    out["by_field"] = formatted_by_field
    out["page_count"] = len(doc_pages)
    return out


def _format_summary_result(raw_res: dict[str, Any], doc_pages: dict[int, str]) -> dict[str, Any]:
    out = deepcopy(raw_res)
    detailed_sections: dict[str, list[dict[str, Any]]] = {}
    for sent in out.get("sentences", []):
        if sent.get("status") != "kept":
            continue
        sec = str(sent.get("section", ""))
        if sec.lower() == "short":
            continue
        detailed_sections.setdefault(sec, []).append(
            {
                "text": str(sent.get("text", "")),
                "pages": [int(p) for p in sent.get("pages", [])],
            }
        )
    out["detailed_sections"] = detailed_sections
    out["page_count"] = len(doc_pages)
    return out


def _base_task_payload(
    state: str,
    notice: str,
    result: dict[str, Any] | None = None,
    live_calls: int = 0,
    models_used: dict[str, int] | None = None,
    error: str | None = None,
    elapsed_s: float | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "state": state,
        "result": result,
        "live_calls": int(live_calls),
        "models_used": dict(models_used or {}),
        "notice": notice,
        "error": error,
        "elapsed_s": elapsed_s,
    }
    if state == "quota_blocked" and error:
        payload["message"] = error
    return payload


def _set_task_state(doc_id: str, kind: str, payload: dict[str, Any]) -> None:
    with _TASK_LOCK:
        _TASK_STATES[(doc_id, kind)] = deepcopy(payload)


def get_task_status(doc_id: str, kind: str) -> dict[str, Any]:
    cfg = load_app_config()
    notice = cfg["notices"]["task_output"]

    with _TASK_LOCK:
        cached = _TASK_STATES.get((doc_id, kind))
        if cached is not None:
            return deepcopy(cached)

    saved = read_saved_task_result(doc_id, kind)
    if saved is not None:
        with _TASK_LOCK:
            _TASK_STATES[(doc_id, kind)] = deepcopy(saved)
        return deepcopy(saved)

    return _base_task_payload(state="not_started", notice=notice)


def _run_task_worker(
    doc_id: str,
    kind: str,
    cfg: dict[str, Any],
    today_baseline: int,
) -> None:
    notice = cfg["notices"]["task_output"]
    quota_msg = cfg["notices"]["quota_blocked"]
    task_budget = int(cfg["task_budgets"].get(kind, 10 if kind == "summary" else 20))
    daily_limit = int(cfg["daily_soft_limit"])
    results_dir_name = str(cfg.get("results_dir_name", "results"))

    started = time.perf_counter()
    client: BudgetedGeminiClient | None = None

    try:
        _, doc_pages = load_uploaded_document(doc_id)
        if kind in ("summary", "keyinfo") and task_budget <= 0:
            reason = f"Per-task live-call budget ({task_budget}) reached."
            _set_task_state(
                doc_id,
                kind,
                _base_task_payload(
                    state="failed",
                    notice=notice,
                    result=None,
                    live_calls=0,
                    models_used={},
                    error=reason,
                    elapsed_s=0.0,
                ),
            )
            return

        client = BudgetedGeminiClient(
            task_budget=task_budget,
            daily_limit=daily_limit,
            today_baseline=today_baseline,
        )

        if kind == "keyinfo":
            ex_cfg = load_extract_config()
            ex_cfg["model_role"] = str(cfg.get("task_model_role", {}).get("keyinfo", "bulk"))
            ex_cfg["max_calls_per_doc"] = min(int(ex_cfg.get("max_calls_per_doc", 16)), task_budget)
            raw_res = extract_key_info(
                doc_id=doc_id,
                doc_pages=doc_pages,
                client=client,
                config=ex_cfg,
                verify_numeric=True,
                max_verifier_calls=6,
            )
            formatted = _format_keyinfo_result(raw_res, doc_pages)
        elif kind == "risk":
            formatted = run_risk_analysis(
                doc_id=doc_id,
                client=client,
                task_budget=task_budget,
            )
        else:
            saved_keyinfo = read_saved_task_result(doc_id, "keyinfo")
            existing_ki = saved_keyinfo.get("result") if saved_keyinfo else None
            sum_cfg = load_summarize_config()
            sum_cfg["max_live_calls"] = min(int(sum_cfg.get("max_live_calls", 30)), task_budget)
            if existing_ki is None:
                ex_cfg = load_extract_config()
                ex_cfg["model_role"] = str(cfg.get("task_model_role", {}).get("keyinfo", "bulk"))
                ex_cfg["max_calls_per_doc"] = min(int(ex_cfg.get("max_calls_per_doc", 16)), task_budget)
                raw_ki = extract_key_info(
                    doc_id=doc_id,
                    doc_pages=doc_pages,
                    client=client,
                    config=ex_cfg,
                    verify_numeric=False,
                )
                existing_ki = _format_keyinfo_result(raw_ki, doc_pages)
            raw_res = summarize_document(
                doc_id=doc_id,
                doc_pages=doc_pages,
                key_info=existing_ki,
                client=client,
                config=sum_cfg,
            )
            formatted = _format_summary_result(raw_res, doc_pages)

        elapsed = round(time.perf_counter() - started, 3)

        if client.daily_quota_stopped or formatted.get("quota_stopped"):
            _set_task_state(
                doc_id,
                kind,
                _base_task_payload(
                    state="quota_blocked",
                    notice=notice,
                    result=None,
                    live_calls=client.api_calls_made,
                    models_used=client.models_used,
                    error=quota_msg,
                    elapsed_s=elapsed,
                ),
            )
            return

        flags_list = [str(f) for f in (formatted.get("flags") or [])]
        budget_flag = any(
            f.startswith(("call_budget_reached:", "quota_or_api_error:TaskBudgetExceededError"))
            for f in flags_list
        )
        if client.budget_stopped_reason or budget_flag or formatted.get("budget_stopped"):
            reason = client.budget_stopped_reason or f"Per-task live-call budget ({task_budget}) reached."
            has_partial = bool(formatted.get("short") or formatted.get("fields") or formatted.get("flagged_clauses"))
            _set_task_state(
                doc_id,
                kind,
                _base_task_payload(
                    state="partial" if has_partial else "failed",
                    notice=notice,
                    result=formatted if has_partial else None,
                    live_calls=client.api_calls_made,
                    models_used=client.models_used,
                    error=reason,
                    elapsed_s=elapsed,
                ),
            )
            return

        if formatted.get("status") == "scan_failed":
            _set_task_state(
                doc_id,
                kind,
                _base_task_payload(
                    state="failed",
                    notice=notice,
                    result=None,
                    live_calls=client.api_calls_made,
                    models_used=client.models_used,
                    error="Risk scan failed due to API or network error.",
                    elapsed_s=elapsed,
                ),
            )
            return

        done_payload = _base_task_payload(
            state="done",
            notice=notice,
            result=formatted,
            live_calls=client.api_calls_made,
            models_used=client.models_used,
            error=None,
            elapsed_s=elapsed,
        )
        out_path = get_result_file_path(doc_id, kind, results_dir_name)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json_atomic(out_path, done_payload)
        _set_task_state(doc_id, kind, done_payload)

    except DailyQuotaExceededError:
        elapsed = round(time.perf_counter() - started, 3)
        _set_task_state(
            doc_id,
            kind,
            _base_task_payload(
                state="quota_blocked",
                notice=notice,
                result=None,
                live_calls=client.api_calls_made if client else 0,
                models_used=client.models_used if client else {},
                error=quota_msg,
                elapsed_s=elapsed,
            ),
        )
    except TaskBudgetExceededError as exc:
        elapsed = round(time.perf_counter() - started, 3)
        _set_task_state(
            doc_id,
            kind,
            _base_task_payload(
                state="failed",
                notice=notice,
                result=None,
                live_calls=client.api_calls_made if client else 0,
                models_used=client.models_used if client else {},
                error=str(exc),
                elapsed_s=elapsed,
            ),
        )
    except Exception as exc:
        elapsed = round(time.perf_counter() - started, 3)
        _set_task_state(
            doc_id,
            kind,
            _base_task_payload(
                state="failed",
                notice=notice,
                result=None,
                live_calls=client.api_calls_made if client else 0,
                models_used=client.models_used if client else {},
                error=f"Task failed ({type(exc).__name__}).",
                elapsed_s=elapsed,
            ),
        )


def start_task(doc_id: str, kind: str) -> tuple[int, dict[str, Any]]:
    """Starts a background summary/keyinfo task or returns cached/blocked status."""
    cfg = load_app_config()
    notice = cfg["notices"]["task_output"]
    quota_msg = cfg["notices"]["quota_blocked"]

    with _TASK_LOCK:
        cur = _TASK_STATES.get((doc_id, kind))
        if cur is not None:
            if cur.get("state") == "done":
                return 200, deepcopy(cur)
            if cur.get("state") == "running":
                return 202, deepcopy(cur)

    saved = read_saved_task_result(doc_id, kind)
    if saved is not None:
        _set_task_state(doc_id, kind, saved)
        return 200, deepcopy(saved)

    today_calls = count_today_live_calls()
    daily_limit = int(cfg["daily_soft_limit"])
    if today_calls >= daily_limit:
        blocked = _base_task_payload(
            state="quota_blocked",
            notice=notice,
            result=None,
            live_calls=0,
            models_used={},
            error=quota_msg,
            elapsed_s=0.0,
        )
        _set_task_state(doc_id, kind, blocked)
        return 202, blocked

    running_payload = _base_task_payload(
        state="running",
        notice=notice,
        result=None,
        live_calls=0,
        models_used={},
        error=None,
        elapsed_s=None,
    )
    _set_task_state(doc_id, kind, running_payload)

    t = threading.Thread(
        target=_run_task_worker,
        args=(doc_id, kind, cfg, today_calls),
        daemon=True,
        name=f"task-{kind}-{doc_id}",
    )
    with _TASK_LOCK:
        _TASK_THREADS[(doc_id, kind)] = t
    t.start()
    return 202, running_payload
