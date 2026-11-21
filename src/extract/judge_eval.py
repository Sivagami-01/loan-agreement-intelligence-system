"""src/extract/judge_eval.py

Stage 3a-fix2: Post-hoc, judge-based (NOT pre-registered) LLM comparison
using the verifier role from config/models.yaml (strictly a different model
from the extractor). Calibrates against human verdicts first; refuses to
report Metric B if agreement < 85% or if verifier quota runs out.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import requests

from src.llm.gemini_client import GEMINI_API_ENDPOINT, LOG_FILE, get_api_key, load_model_config

ROOT = Path(__file__).resolve().parents[2]
JUDGE_CACHE_DIR = ROOT / "data" / "processed" / "cache" / "judge"

METRIC_B_LABEL = "post-hoc, judge-based, not pre-registered"


class VerifierQuotaExhausted(RuntimeError):
    """Raised when the independent verifier model hits a 429 / quota limit."""


def _append_llm_log(model: str, latency: float, input_size: int, output_size: int) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    need_header = not LOG_FILE.is_file() or LOG_FILE.stat().st_size == 0
    now_iso = datetime.now(timezone.utc).isoformat()
    with open(LOG_FILE, "a" if not need_header else "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        if need_header:
            w.writerow(["time", "model", "latency", "input_size", "output_size"])
        w.writerow([now_iso, model, f"{latency:.3f}", input_size, output_size])


class IndependentVerifierJudgeClient:
    """Direct verifier-role REST caller with disk caching, RPM pacing, and NO fallback to bulk."""

    def __init__(
        self,
        extractor_models: set[str] | None = None,
        cache_dir: Path = JUDGE_CACHE_DIR,
        min_interval_seconds: float = 7.0,
        timeout: float = 35.0,
    ) -> None:
        models_cfg = load_model_config()
        self.verifier_model = str(models_cfg.get("verifier", "")).strip()
        self.extractor_models = extractor_models or set()
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.min_interval = min_interval_seconds
        self.timeout = timeout
        self.last_call_time = 0.0
        self.api_calls_made = 0
        self.cache_hits = 0
        self.quota_exhausted = False
        self.stop_reason = ""

    def _hash_key(self, prompt: str) -> str:
        raw = f"{self.verifier_model}\n{prompt}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def generate_json(self, prompt: str) -> str:
        if not self.verifier_model:
            raise VerifierQuotaExhausted("No verifier model configured in config/models.yaml.")
        if self.verifier_model in self.extractor_models:
            raise VerifierQuotaExhausted(
                f"Verifier '{self.verifier_model}' is identical to extractor model; cannot judge independently."
            )

        key = self._hash_key(prompt)
        cache_path = self.cache_dir / f"{key}.json"
        if cache_path.is_file():
            try:
                data = json.loads(cache_path.read_text(encoding="utf-8"))
                self.cache_hits += 1
                return str(data.get("text", ""))
            except Exception:
                pass

        if self.quota_exhausted:
            raise VerifierQuotaExhausted(self.stop_reason or "Verifier quota already exhausted.")

        elapsed = time.time() - self.last_call_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

        api_key = get_api_key()
        url = f"{GEMINI_API_ENDPOINT}/{self.verifier_model}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.0},
        }
        input_bytes = len(prompt.encode("utf-8"))

        for attempt in range(2):
            start = time.time()
            self.last_call_time = start
            try:
                resp = requests.post(
                    url,
                    json=payload,
                    timeout=self.timeout,
                    headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
                )
            except (requests.ConnectionError, requests.Timeout) as exc:
                self.quota_exhausted = True
                self.stop_reason = f"{type(exc).__name__} reaching verifier {self.verifier_model}"
                raise VerifierQuotaExhausted(self.stop_reason) from exc

            latency = time.time() - start
            if resp.status_code == 200:
                body = resp.json()
                cands = body.get("candidates", [])
                if not cands:
                    raise ValueError("Empty candidates from verifier judge")
                parts = cands[0].get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts)
                self.api_calls_made += 1
                _append_llm_log(self.verifier_model, latency, input_bytes, len(text.encode("utf-8")))
                cache_path.write_text(
                    json.dumps({"model": self.verifier_model, "text": text}, ensure_ascii=False),
                    encoding="utf-8",
                )
                return text

            if resp.status_code == 429:
                txt = resp.text or ""
                # Daily quota exhaustion cannot recover in seconds; stop gracefully immediately
                is_daily = "free_tier_requests" in txt or "PerDay" in txt or "Please retry in" in txt
                if attempt == 0 and not is_daily:
                    time.sleep(10.0)
                    continue
                self.quota_exhausted = True
                self.stop_reason = f"HTTP 429 quota exhausted for {self.verifier_model}: {txt[:240]}"
                raise VerifierQuotaExhausted(self.stop_reason)

            self.quota_exhausted = True
            self.stop_reason = f"HTTP {resp.status_code} from {self.verifier_model}: {resp.text[:200]}"
            raise VerifierQuotaExhausted(self.stop_reason)

        raise VerifierQuotaExhausted("Verifier judge failed after retries.")


def _parse_judge_batch(raw_text: str, expected_ids: list[int]) -> dict[int, dict[str, str]]:
    cleaned = (raw_text or "").strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, flags=re.IGNORECASE)
    if m:
        cleaned = m.group(1).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        s, e = cleaned.find("["), cleaned.rfind("]")
        if s == -1 or e <= s:
            return {}
        try:
            data = json.loads(cleaned[s : e + 1])
        except json.JSONDecodeError:
            return {}

    if isinstance(data, dict) and isinstance(data.get("items"), list):
        data = data["items"]
    if not isinstance(data, list):
        return {}

    out: dict[int, dict[str, str]] = {}
    exp_set = set(expected_ids)
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            idx = int(item.get("idx", item.get("id")))
        except (TypeError, ValueError):
            continue
        verdict = str(item.get("verdict", "")).strip().lower()
        if idx in exp_set and verdict in {"equivalent", "partial", "different"}:
            out[idx] = {"verdict": verdict, "reason": str(item.get("reason", "")).strip()}
    return out


def _build_judge_batch_prompt(items: list[dict[str, Any]]) -> str:
    payload_items = [
        {
            "idx": it["idx"],
            "field": it["field"],
            "predicted": it["predicted"],
            "reference": it["reference"],
        }
        for it in items
    ]
    return (
        "You are an impartial legal extraction evaluator.\n"
        "For EACH item below, compare `predicted` against `reference` for the named loan-agreement `field`.\n"
        "Output ONLY a JSON array: [{\"idx\": <int>, \"verdict\": \"equivalent\"|\"partial\"|\"different\", \"reason\": \"<one short line>\"}].\n"
        "Definitions:\n"
        "- equivalent: captures the same substantive fact(s), numbers, entities, or valid deferral/absence status.\n"
        "- partial: shares the core value/entity/number, with minor extra or missing details.\n"
        "- different: wrong value, over-answered unrelated clause, missing key value (`[unverified/dropped]` or `Not found`), or contradicts reference.\n\n"
        f"ITEMS:\n{json.dumps(payload_items, indent=2, ensure_ascii=False)}\n"
    )


def verdict_matches_human(human_who: str, judge_verdict: str) -> bool:
    """Applies required calibration mapping between human who_is_right and judge verdict."""
    w = (human_who or "").strip().lower()
    v = (judge_verdict or "").strip().lower()
    if w == "both ok":
        return v in {"equivalent", "partial"}
    if w == "label":
        return v == "different"
    if w == "system":
        return v == "equivalent"
    return False


def calibrate_and_score_metric_b(
    review_rows: list[dict[str, Any]],
    post_positive_rows: list[dict[str, Any]],
    extractor_models: set[str],
    batch_size: int = 6,
    llm_batch_fn: Callable[[str], str] | None = None,
    judge_client: IndependentVerifierJudgeClient | None = None,
) -> dict[str, Any]:
    """Calibrates judge on human verdicts; only scores Metric B if agreement >= 85% and quota holds."""
    client = judge_client or IndependentVerifierJudgeClient(extractor_models=extractor_models)

    def _call(prompt: str) -> str:
        if llm_batch_fn is not None:
            return llm_batch_fn(prompt)
        return client.generate_json(prompt)

    cal_items = [
        {
            "idx": i,
            "field": r["field"],
            "predicted": r["predicted_value"],
            "reference": r["reference_value"],
            "who_is_right": r["who_is_right"].strip(),
        }
        for i, r in enumerate(review_rows)
    ]

    calibrated_judgements: dict[int, dict[str, str]] = {}
    stopped_gracefully = False
    stop_reason = ""

    for start in range(0, len(cal_items), batch_size):
        batch = cal_items[start : start + batch_size]
        prompt = _build_judge_batch_prompt(batch)
        try:
            raw = _call(prompt)
        except VerifierQuotaExhausted as exc:
            stopped_gracefully = True
            stop_reason = str(exc)
            break
        parsed = _parse_judge_batch(raw, [it["idx"] for it in batch])
        calibrated_judgements.update(parsed)

    total_cal = len(cal_items)
    completed_cal = len(calibrated_judgements)
    agreed_cal = 0
    for it in cal_items:
        j = calibrated_judgements.get(it["idx"])
        if j and verdict_matches_human(it["who_is_right"], j["verdict"]):
            agreed_cal += 1

    agreement = (agreed_cal / completed_cal) if completed_cal > 0 else 0.0
    trusted = (not stopped_gracefully) and (completed_cal == total_cal) and (agreement >= 0.85)

    cal_report = {
        "label": METRIC_B_LABEL,
        "verifier_model": client.verifier_model if llm_batch_fn is None else "injected-verifier",
        "extractor_models": sorted(extractor_models),
        "total_verdicts": total_cal,
        "completed": completed_cal,
        "agreed": agreed_cal,
        "agreement": agreement,
        "trusted": trusted,
        "stopped_gracefully": stopped_gracefully,
        "stop_reason": stop_reason,
    }

    if not trusted:
        return {
            "label": METRIC_B_LABEL,
            "calibration": cal_report,
            "metric_b_reported": False,
            "reason": (
                f"Judge NOT trusted / NOT scored: stopped_gracefully={stopped_gracefully}, "
                f"calibrated={completed_cal}/{total_cal}, agreement={agreement:.1%} (requires >=85%). "
                + stop_reason
            ).strip(),
            "new_judge_calls": client.api_calls_made,
            "cache_hits": client.cache_hits,
        }

    # Score positive rows separately by dataset (silver vs human-verified gold)
    pos_items = [
        {
            "idx": i,
            "dataset": r["dataset"],
            "field": r["field"],
            "predicted": r["predicted"],
            "reference": r["reference"],
        }
        for i, r in enumerate(post_positive_rows)
    ]

    pos_judgements: dict[int, dict[str, str]] = {}
    for start in range(0, len(pos_items), batch_size):
        batch = pos_items[start : start + batch_size]
        prompt = _build_judge_batch_prompt(batch)
        try:
            raw = _call(prompt)
        except VerifierQuotaExhausted as exc:
            stopped_gracefully = True
            stop_reason = str(exc)
            break
        parsed = _parse_judge_batch(raw, [it["idx"] for it in batch])
        pos_judgements.update(parsed)

    by_dataset: dict[str, dict[str, Any]] = {}
    for ds in ("silver", "gold"):
        ds_items = [it for it in pos_items if it["dataset"] == ds]
        cnt = {"equivalent": 0, "partial": 0, "different": 0, "unjudged": 0}
        for it in ds_items:
            j = pos_judgements.get(it["idx"])
            if j:
                cnt[j["verdict"]] += 1
            else:
                cnt["unjudged"] += 1
        judged = len(ds_items) - cnt["unjudged"]
        strict_rate = (cnt["equivalent"] / judged) if judged > 0 else 0.0
        lenient_rate = ((cnt["equivalent"] + cnt["partial"]) / judged) if judged > 0 else 0.0
        by_dataset[ds] = {
            "total": len(ds_items),
            "judged": judged,
            "counts": cnt,
            "strict_equivalent_rate": strict_rate,
            "lenient_equiv_or_partial_rate": lenient_rate,
        }

    return {
        "label": METRIC_B_LABEL,
        "calibration": cal_report,
        "metric_b_reported": not stopped_gracefully,
        "stopped_gracefully": stopped_gracefully,
        "stop_reason": stop_reason,
        "by_dataset": by_dataset,
        "new_judge_calls": client.api_calls_made,
        "cache_hits": client.cache_hits,
    }
