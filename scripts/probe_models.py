"""scripts/probe_models.py

Probes up to 8 Gemini text models (from required list + available_models.csv)
with a tiny prompt ("Reply with OK"), NO fallback, 30s timeout, and max 1 retry after 10s.
Total calls strictly <= 20. Saves data/processed/model_probe.csv.
"""

from __future__ import annotations

import csv
import sys
import time
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.llm.gemini_client import GEMINI_API_ENDPOINT, get_api_key

AVAILABLE_CSV = ROOT / "data" / "processed" / "available_models.csv"
PROBE_CSV = ROOT / "data" / "processed" / "model_probe.csv"

REQUIRED_CANDIDATES = [
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.1-pro-preview",
]

MAX_CANDIDATES = 8
MAX_TOTAL_CALLS = 20


def select_candidates() -> list[str]:
    candidates = list(REQUIRED_CANDIDATES)
    seen = set(candidates)

    if AVAILABLE_CSV.is_file():
        with AVAILABLE_CSV.open("r", encoding="utf-8", errors="ignore") as f:
            rows = list(csv.DictReader(f))

        # Prefer general text "pro" / "flash" Gemini models (exclude tts/image/lyria/deep-research/legacy 2.5)
        excluded_markers = ("-tts", "-image", "lyria", "deep-research", "robotics", "computer-use", "gemini-2.5-pro")
        preferred_order = []
        fallback_order = []
        for row in rows:
            name = str(row.get("model_name", "")).strip()
            low = name.lower()
            if not name or name in seen:
                continue
            if ("pro" in low or "flash" in low) and "gemini" in low:
                if any(bad in low for bad in excluded_markers):
                    continue
                if "3.7" in low or "pro-latest" in low or "3-flash-preview" in low or "3.6" in low:
                    preferred_order.append(name)
                else:
                    fallback_order.append(name)

        for name in preferred_order + fallback_order:
            if len(candidates) >= MAX_CANDIDATES:
                break
            if name not in seen:
                candidates.append(name)
                seen.add(name)

    return candidates[:MAX_CANDIDATES]


def probe_once(model_name: str, api_key: str) -> tuple[int | str, float, bool, str]:
    url = f"{GEMINI_API_ENDPOINT}/{model_name}:generateContent"
    payload = {"contents": [{"parts": [{"text": "Reply with OK"}]}]}
    t0 = time.time()
    try:
        resp = requests.post(
            url,
            json=payload,
            timeout=30.0,
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        )
        dt = time.time() - t0
        if resp.status_code == 200:
            data = resp.json()
            cands = data.get("candidates", [])
            txt = ""
            if cands:
                parts = cands[0].get("content", {}).get("parts", [])
                txt = "".join(str(p.get("text", "")) for p in parts).strip()
            has_text = len(txt) > 0
            return 200, round(dt, 3), has_text, txt[:60] if has_text else "EMPTY_TEXT"
        else:
            err_msg = resp.text.replace("\n", " ")[:120]
            return resp.status_code, round(dt, 3), False, err_msg
    except Exception as exc:
        dt = time.time() - t0
        return type(exc).__name__, round(dt, 3), False, str(exc).replace("\n", " ")[:120]


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    api_key = get_api_key()
    candidates = select_candidates()

    results: list[dict[str, Any]] = []
    calls_made = 0

    print(f"Probing {len(candidates)} Gemini candidates (30s timeout, 1 retry after 10s, max {MAX_TOTAL_CALLS} calls):")
    for idx, model in enumerate(candidates, 1):
        if calls_made >= MAX_TOTAL_CALLS:
            print(f"[{idx}/{len(candidates)}] Budget reached ({MAX_TOTAL_CALLS} calls); stopping.")
            break

        attempts = 1
        calls_made += 1
        status, latency, has_text, detail = probe_once(model, api_key)

        # 1 retry after 10s if failed and budget remains
        if not (status == 200 and has_text) and calls_made < MAX_TOTAL_CALLS:
            print(f"  [{idx}/{len(candidates)}] {model}: attempt 1 -> {status} ({latency}s). Retrying after 10s...", flush=True)
            time.sleep(10.0)
            attempts = 2
            calls_made += 1
            status, latency, has_text, detail = probe_once(model, api_key)

        ok = (status == 200 and has_text)
        row = {
            "model_name": model,
            "attempts": attempts,
            "http_status": status,
            "latency_seconds": latency,
            "text_returned": has_text,
            "ok": ok,
            "detail": detail,
        }
        results.append(row)
        print(
            f"  [{idx}/{len(candidates)}] {model:<28} | HTTP={str(status):<12} | "
            f"{latency:>6.2f}s | text={str(has_text):<5} | ok={ok}",
            flush=True,
        )

    PROBE_CSV.parent.mkdir(parents=True, exist_ok=True)
    with PROBE_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["model_name", "attempts", "http_status", "latency_seconds", "text_returned", "ok", "detail"],
        )
        writer.writeheader()
        writer.writerows(results)

    print("\n" + "=" * 88)
    print(f"MODEL PROBE SUMMARY (Total API calls: {calls_made}/{MAX_TOTAL_CALLS})")
    print("=" * 88)
    print(f"{'Model':<30} | {'Attempts':<8} | {'Status':<12} | {'Latency':<8} | {'Text?':<6} | {'OK?'}")
    print("-" * 88)
    for r in results:
        print(
            f"{r['model_name']:<30} | {r['attempts']:<8} | {str(r['http_status']):<12} | "
            f"{r['latency_seconds']:<7.2f}s | {str(r['text_returned']):<6} | {r['ok']}"
        )
    print("=" * 88)


if __name__ == "__main__":
    main()
