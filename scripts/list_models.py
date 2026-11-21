"""scripts/list_models.py

Lists Gemini API models supporting generateContent via REST API pagination.
Reads GEMINI_API_KEY from environment and sends it strictly in x-goog-api-key header.
Saves results to data/processed/available_models.csv. Never prints or logs keys.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.llm.gemini_client import get_api_key

LIST_MODELS_URL = "https://generativelanguage.googleapis.com/v1beta/models"
OUT_CSV = ROOT / "data" / "processed" / "available_models.csv"


def list_generate_content_models() -> list[dict[str, str]]:
    api_key = get_api_key()
    models_out: list[dict[str, str]] = []
    page_token: str | None = None

    while True:
        params: dict[str, Any] = {"pageSize": 100}
        if page_token:
            params["pageToken"] = page_token

        resp = requests.get(
            LIST_MODELS_URL,
            params=params,
            headers={"x-goog-api-key": api_key},
            timeout=30.0,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"ListModels failed with HTTP {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        for item in data.get("models", []):
            methods = item.get("supportedGenerationMethods", []) or []
            if "generateContent" not in methods:
                continue
            full_name = str(item.get("name", ""))
            short_name = full_name.removeprefix("models/")
            display_name = str(item.get("displayName", ""))
            models_out.append({
                "model_name": short_name,
                "full_name": full_name,
                "display_name": display_name,
                "supported_methods": ";".join(methods),
            })

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return models_out


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    models = list_generate_content_models()
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["model_name", "full_name", "display_name", "supported_methods"],
        )
        writer.writeheader()
        writer.writerows(models)

    print(f"Found {len(models)} models supporting generateContent. Saved to {OUT_CSV.relative_to(ROOT)}:")
    print("-" * 76)
    print(f"{'Model Name':<42} | {'Display Name'}")
    print("-" * 76)
    for m in models:
        print(f"{m['model_name']:<42} | {m['display_name']}")


if __name__ == "__main__":
    main()
