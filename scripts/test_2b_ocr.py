"""scripts/test_2b_ocr.py

Test Suite for Stage 2b (OCR Comparison).
Verifies:
1. API key present and never logged (0 leaks across all logs/data/docs).
2. 80+ comparison pages processed with 0 crashes.
3. A CER value for every language and engine.
4. config/ocr_choice.yaml exists and names an engine for each language.
5. The disk cache works (a second run makes 0 new API calls).
"""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.llm.gemini_client import GeminiClient, get_api_key

CSV_FILE = ROOT / "data" / "processed" / "ocr_compare.csv"
LOG_FILE = ROOT / "data" / "processed" / "llm_log.csv"
CHOICE_FILE = ROOT / "config" / "ocr_choice.yaml"
MD_FILE = ROOT / "docs" / "OCR_COMPARISON.md"
MODELS_FILE = ROOT / "config" / "models.yaml"
CACHE_DIR = ROOT / "data" / "processed" / "cache" / "gemini"


def check_1_api_key_safety() -> tuple[bool, str]:
    try:
        api_key = get_api_key()
    except Exception as exc:
        return False, f"API key not found: {exc}"

    if not api_key or len(api_key) < 10:
        return False, "API key is empty or suspiciously short."

    # Search files that might contain text
    files_to_check = [
        LOG_FILE,
        CSV_FILE,
        CHOICE_FILE,
        MD_FILE,
        MODELS_FILE,
    ]
    # Also check cache json files
    if CACHE_DIR.is_dir():
        files_to_check.extend(list(CACHE_DIR.glob("*.json")))

    leak_count = 0
    checked_count = 0
    for f in files_to_check:
        if f.is_file():
            checked_count += 1
            content = f.read_text(encoding="utf-8", errors="ignore")
            if api_key in content:
                leak_count += 1

    if leak_count > 0:
        return False, f"API key was found logged in {leak_count} file(s)!"

    return True, f"API key present (len: {len(api_key)}) and never logged across {checked_count} inspected files (leaks: 0)"


def check_2_pages_and_crashes() -> tuple[bool, str]:
    if not CSV_FILE.is_file():
        return False, f"Results CSV not found at {CSV_FILE}"

    rows: list[dict[str, Any]] = []
    with CSV_FILE.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)

    if not rows:
        return False, "Results CSV is empty."

    distinct_items = {r["item_id"] for r in rows if "item_id" in r}
    crash_rows = [r for r in rows if r.get("status") != "OK"]

    total_pages = len(distinct_items)
    crash_count = len(crash_rows)

    if total_pages < 80:
        return False, f"Only {total_pages} comparison pages processed (target: >= 80)."

    if crash_count > 0:
        return False, f"{crash_count} crashes recorded during processing."

    return True, f"{total_pages} comparison pages processed with {crash_count} crashes (total evaluations: {len(rows)})"


def check_3_cer_for_every_language_and_engine() -> tuple[bool, str]:
    if not CSV_FILE.is_file():
        return False, f"Results CSV not found at {CSV_FILE}"

    rows: list[dict[str, Any]] = []
    with CSV_FILE.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)

    expected_languages = ["hindi", "bengali", "punjabi", "malayalam", "english"]
    expected_engines = ["tesseract", "gemini"]

    summary: dict[str, dict[str, float]] = {}
    missing: list[str] = []

    for lang in expected_languages:
        summary[lang] = {}
        for eng in expected_engines:
            matched = [
                float(r["cer"])
                for r in rows
                if r.get("language") == lang and r.get("engine") == eng and r.get("status") == "OK"
            ]
            if not matched:
                missing.append(f"{lang}:{eng}")
            else:
                summary[lang][eng] = round(sum(matched) / len(matched), 4)

    if missing:
        return False, f"Missing CER values for: {', '.join(missing)}"

    details = " | ".join(
        f"{l}: Tesseract={summary[l]['tesseract']*100:.1f}%, Gemini={summary[l]['gemini']*100:.1f}%"
        for l in expected_languages
    )
    return True, f"CER values verified for all {len(expected_languages)*len(expected_engines)} language-engine pairs ({details})"


def check_4_ocr_choice_yaml() -> tuple[bool, str]:
    if not CHOICE_FILE.is_file():
        return False, f"Config file not found at {CHOICE_FILE}"

    try:
        data = yaml.safe_load(CHOICE_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, f"Failed to parse {CHOICE_FILE}: {exc}"

    if not isinstance(data, dict):
        return False, f"{CHOICE_FILE} must contain a YAML mapping."

    rule = data.get("rule", "")
    if not rule or "Gemini only" not in rule:
        return False, f"Rule missing or incomplete in {CHOICE_FILE}: '{rule}'"

    engines = data.get("engines", {})
    if not isinstance(engines, dict):
        return False, "'engines' section missing or not a dictionary."

    expected_langs = ["hindi", "bengali", "punjabi", "malayalam", "english"]
    missing_langs = [l for l in expected_langs if l not in engines or not engines[l]]

    if missing_langs:
        return False, f"Missing engine selection for languages: {missing_langs}"

    selections = ", ".join(f"{l}->{engines[l]}" for l in expected_langs)
    return True, f"config/ocr_choice.yaml valid with rule and engine choices for {len(expected_langs)} languages ({selections})"


def check_5_cache_operates() -> tuple[bool, str]:
    # Check that disk cache prevents new API calls on an already cached item
    if not CACHE_DIR.is_dir() or not any(CACHE_DIR.glob("*.json")):
        return False, "No cache files found in disk cache directory."

    client = GeminiClient()
    initial_calls = client.api_calls_made
    initial_hits = client.cache_hits

    # Probe with an already cached prompt or item
    prompt = "transcribe all text exactly, keep line breaks, no commentary"

    # Find any existing cache file to borrow its hash or test sample
    # Even simpler: call client.generate with the SROIE test image
    sroie_jpg = ROOT / "data" / "raw" / "12_sroie" / "SROIE2019" / "0325updated.task1train(626p)" / "X00016469612.jpg"
    if sroie_jpg.is_file():
        img_bytes = sroie_jpg.read_bytes()
        _ = client.generate(prompt, image_bytes=img_bytes, mime_type="image/jpeg", model_alias="main")
    else:
        _ = client.generate("Ping")

    delta_calls = client.api_calls_made - initial_calls
    delta_hits = client.cache_hits - initial_hits

    if delta_calls > 0:
        return False, f"Cache test failed: made {delta_calls} new API calls instead of hitting cache."

    if delta_hits == 0:
        return False, f"Cache test failed: cache hit count did not increase (hits: {delta_hits})."

    return True, f"Disk cache verified: 0 new API calls made, {delta_hits} cache hit(s) served instantly from disk"


def main() -> None:
    print("=" * 80)
    print("RUNNING TEST SUITE: STAGE 2b (OCR COMPARISON)")
    print("=" * 80)

    checks = [
        ("Check 1: API key present and never logged", check_1_api_key_safety),
        ("Check 2: 80+ comparison pages processed with 0 crashes", check_2_pages_and_crashes),
        ("Check 3: CER value for every language and engine", check_3_cer_for_every_language_and_engine),
        ("Check 4: config/ocr_choice.yaml exists and names an engine", check_4_ocr_choice_yaml),
        ("Check 5: Disk cache eliminates redundant API calls", check_5_cache_operates),
    ]

    results: list[tuple[str, bool, str]] = []
    for name, fn in checks:
        passed, msg = fn()
        results.append((name, passed, msg))
        status_tag = "PASS" if passed else "FAIL"
        print(f"[{status_tag}] {name}")
        print(f"       Details: {msg}")

    print("=" * 80)
    total_passed = sum(1 for _, p, _ in results if p)
    print(f"OVERALL RESULT: {total_passed}/{len(checks)} checks passed")
    print("=" * 80)

    if total_passed < len(checks):
        sys.exit(1)


if __name__ == "__main__":
    main()
