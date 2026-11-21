from __future__ import annotations

import base64
import csv
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = ROOT / "config" / "models.yaml"
CACHE_DIR = ROOT / "data" / "processed" / "cache" / "gemini"
LOG_FILE = ROOT / "data" / "processed" / "llm_log.csv"
GEMINI_API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"


def get_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY")
    if not key and sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as regkey:
                val, _ = winreg.QueryValueEx(regkey, "GEMINI_API_KEY")
                if val:
                    key = str(val).strip()
                    os.environ["GEMINI_API_KEY"] = key
        except Exception:
            pass
    if not key:
        raise ValueError("GEMINI_API_KEY is not set in environment or user profile.")
    return key


def load_model_config() -> dict[str, str]:
    if CONFIG_FILE.is_file():
        try:
            data = yaml.safe_load(CONFIG_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {
                    "main": data.get("main", "gemini-3.8-flash"),
                    "bulk": data.get("bulk", "gemini-3.5-flash-lite"),
                    "verifier": data.get("verifier", "gemini-2.5-pro"),
                }
        except Exception:
            pass
    return {
        "main": "gemini-3.8-flash",
        "bulk": "gemini-3.5-flash-lite",
        "verifier": "gemini-2.5-pro",
    }


class GeminiClient:
    def __init__(
        self,
        cache_dir: Path | str = CACHE_DIR,
        log_file: Path | str = LOG_FILE,
        min_interval_seconds: float = 3.5,
        max_retries: int = 3,
        request_timeout: float = 30.0,
    ) -> None:
        self.models = load_model_config()
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.min_interval = min_interval_seconds
        self.max_retries = max_retries
        self.timeout = request_timeout
        self.last_call_time: float = 0.0
        self.api_calls_made: int = 0
        self.cache_hits: int = 0
        self.last_model_used: str | None = None
        self.model_cooldowns: dict[str, float] = self._load_cooldowns()
        self._ensure_log_header()

    def _load_cooldowns(self) -> dict[str, float]:
        path = self.cache_dir / "cooldowns.json"
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                now = time.time()
                return {k: v for k, v in data.items() if v > now}
            except Exception:
                pass
        return {}

    def _save_cooldown(self, model: str, until: float) -> None:
        self.model_cooldowns[model] = until
        path = self.cache_dir / "cooldowns.json"
        try:
            path.write_text(json.dumps(self.model_cooldowns, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _ensure_log_header(self) -> None:
        if not self.log_file.is_file() or self.log_file.stat().st_size == 0:
            with self.log_file.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(["time", "model", "latency", "input_size", "output_size"])

    def _append_log(self, model: str, latency: float, input_size: int, output_size: int) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self.log_file.open("a", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow([now_iso, model, f"{latency:.3f}", input_size, output_size])

    def _compute_hash(
        self,
        model: str,
        prompt: str,
        image_bytes: bytes | None = None,
        temperature: float | None = None,
    ) -> str:
        hasher = hashlib.sha256()
        hasher.update(model.encode("utf-8"))
        hasher.update(b"::")
        hasher.update(prompt.encode("utf-8"))
        if image_bytes is not None:
            hasher.update(b"::")
            hasher.update(image_bytes)
        if temperature is not None:
            hasher.update(f"::temp={float(temperature)}".encode("utf-8"))
        return hasher.hexdigest()

    def _rate_limit(self) -> None:
        elapsed = time.time() - self.last_call_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

    def _send_request(
        self,
        model: str,
        prompt: str,
        image_bytes: bytes | None = None,
        mime_type: str = "image/png",
        temperature: float | None = None,
    ) -> tuple[str, float]:
        api_key = get_api_key()
        parts: list[dict[str, Any]] = [{"text": prompt}]
        input_size = len(prompt.encode("utf-8"))

        if image_bytes is not None:
            b64_data = base64.b64encode(image_bytes).decode("ascii")
            parts.append({
                "inline_data": {
                    "mime_type": mime_type,
                    "data": b64_data,
                }
            })
            input_size += len(image_bytes)

        payload: dict[str, Any] = {"contents": [{"parts": parts}]}
        if temperature is not None:
            payload["generationConfig"] = {"temperature": float(temperature)}
        url = f"{GEMINI_API_ENDPOINT}/{model}:generateContent"

        self._rate_limit()
        start = time.time()
        self.last_call_time = time.time()

        response = requests.post(
            url,
            json=payload,
            timeout=self.timeout,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": api_key,
            },
        )
        latency = time.time() - start

        if response.status_code == 200:
            data = response.json()
            candidates = data.get("candidates", [])
            if candidates:
                text_parts = candidates[0].get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in text_parts)
                self.api_calls_made += 1
                self._append_log(model, latency, input_size, len(text.encode("utf-8")))
                return text, latency
            raise ValueError("No candidates returned by Gemini API")

        # Raise HTTP error with status code
        error_msg = f"HTTP {response.status_code}: {response.text[:300]}"
        err = requests.HTTPError(error_msg, response=response)
        err.status_code = response.status_code  # type: ignore[attr-defined]
        raise err

    def generate(
        self,
        prompt: str,
        image_bytes: bytes | None = None,
        mime_type: str = "image/png",
        model_alias: str = "main",
        temperature: float | None = None,
    ) -> str:
        primary_model = self.models.get(model_alias, self.models.get("main", "gemini-3.8-flash"))
        bulk_model = self.models.get("bulk", "gemini-3.5-flash-lite")

        # Check disk cache for the requested primary model first
        cache_key = self._compute_hash(primary_model, prompt, image_bytes, temperature)
        cache_path = self.cache_dir / f"{cache_key}.json"

        if cache_path.is_file():
            try:
                cached_data = json.loads(cache_path.read_text(encoding="utf-8"))
                self.cache_hits += 1
                self.last_model_used = cached_data.get("model", primary_model)
                return cached_data.get("text", "")
            except Exception:
                pass

        # Try primary model with retries (or fallback if primary is in cooldown)
        current_model = primary_model
        if self.model_cooldowns.get(primary_model, 0.0) > time.time() and primary_model != bulk_model:
            current_model = bulk_model

        for attempt in range(self.max_retries + 1):
            # If routed to fallback bulk model via cooldown or error, check bulk disk cache
            if current_model != primary_model:
                cur_cache_key = self._compute_hash(current_model, prompt, image_bytes, temperature)
                cur_cache_path = self.cache_dir / f"{cur_cache_key}.json"
                if cur_cache_path.is_file():
                    try:
                        cached_data = json.loads(cur_cache_path.read_text(encoding="utf-8"))
                        self.cache_hits += 1
                        self.last_model_used = cached_data.get("model", current_model)
                        return cached_data.get("text", "")
                    except Exception:
                        pass

            try:
                # Use faster timeout for primary model during probes
                text, latency = self._send_request(current_model, prompt, image_bytes, mime_type, temperature)
                self.last_model_used = current_model
                # Save to disk cache
                save_key = self._compute_hash(current_model, prompt, image_bytes, temperature)
                (self.cache_dir / f"{save_key}.json").write_text(
                    json.dumps({"model": current_model, "text": text}, ensure_ascii=False),
                    encoding="utf-8",
                )
                return text
            except requests.HTTPError as err:
                status_code = getattr(err, "status_code", None) or (
                    err.response.status_code if getattr(err, "response", None) else None
                )
                # On 404: immediate fallback (model unavailable/retired)
                if status_code == 404 and current_model != bulk_model:
                    self._save_cooldown(current_model, time.time() + 3600.0)
                    current_model = bulk_model
                    time.sleep(0.5)
                    continue

                # On 429/503: wait briefly to ride out RPM spikes before falling back
                is_quota_or_unavailable = status_code in (429, 503)
                if is_quota_or_unavailable:
                    if attempt < min(2, self.max_retries):
                        backoff = 12.0 * (attempt + 1) if status_code == 429 else 4.0 * (attempt + 1)
                        time.sleep(backoff)
                        continue
                    if current_model != bulk_model:
                        self._save_cooldown(current_model, time.time() + 300.0)
                        current_model = bulk_model
                        time.sleep(0.5)
                        continue
                    if attempt < self.max_retries:
                        time.sleep((2.0 ** attempt) * 2.0)
                        continue

                raise err
            except (requests.ConnectionError, requests.Timeout) as net_err:
                if current_model != bulk_model:
                    self._save_cooldown(current_model, time.time() + 300.0)
                    current_model = bulk_model
                    time.sleep(1.0)
                    continue
                if attempt < self.max_retries:
                    time.sleep(2.0 * (attempt + 1))
                    continue
                raise net_err

        raise RuntimeError(f"Failed to generate content after {self.max_retries} attempts.")
