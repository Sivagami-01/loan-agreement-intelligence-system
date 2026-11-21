"""src/translate/translate_text.py

Stage 5b: Translation service for summary prose and chat answers into Indic languages
(Hindi, Tamil, Bengali, Punjabi, Malayalam).
Enforces:
- Target language validation ("hi", "ta", "bn", "pa", "ml")
- Quota guard check before live calls
- Prompting rules enforcing strict numeric/factual preservation and no advice
- Number/date verification via src.translate.number_check.check_numbers
- At most ONE retry on number check failure
- Returns status "number_check_failed" if still invalid (never shows invalid translation as good)
- Supports dependency-injected llm_call for zero-API testing
"""

from __future__ import annotations

import re
from typing import Any, Callable

from src.llm.gemini_client import GeminiClient
from src.translate.number_check import check_numbers

SUPPORTED_LANGUAGES: dict[str, str] = {
    "hi": "Hindi",
    "ta": "Tamil",
    "bn": "Bengali",
    "pa": "Punjabi",
    "ml": "Malayalam",
}


_NUMERIC_DATE_PATTERN = re.compile(
    r"(?<!\d)(?:\d{4}[/\-]\d{1,2}[/\-]\d{1,2}|\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4})(?!\d)"
)
_NUMERIC_TOKEN_PATTERN = re.compile(r"\d[\d,]*(?:\.\d+)?%?")


def _shield_numbers(text: str) -> tuple[str, dict[str, str]]:
    """Replace source numbers with opaque placeholders so translation cannot alter them."""
    replacements: dict[str, str] = {}
    counter = 0

    def shield(match: re.Match[str]) -> str:
        nonlocal counter
        placeholder = f"__NUM{counter}__"
        replacements[placeholder] = match.group(0)
        counter += 1
        return placeholder

    shielded = _NUMERIC_DATE_PATTERN.sub(shield, text)
    shielded = _NUMERIC_TOKEN_PATTERN.sub(shield, shielded)
    return shielded, replacements


def _restore_numbers(translated: str, replacements: dict[str, str]) -> str:
    restored = translated
    for placeholder, original in replacements.items():
        restored = restored.replace(placeholder, original)
        spaced_placeholder = placeholder.replace("__", " __ ").replace("  ", " ")
        restored = restored.replace(spaced_placeholder, original)
    return restored


def translate_text(
    text_en: str,
    lang: str,
    llm_call: Callable[[str], str] | None = None,
) -> dict[str, Any]:
    """Translates English loan agreement prose into the requested Indic language.
    Verifies that all numeric tokens (dates, amounts, percentages, counts) are preserved.
    """
    clean_text = (text_en or "").strip()
    clean_lang = (lang or "").strip().lower()

    if clean_lang not in SUPPORTED_LANGUAGES:
        return {
            "status": "failed",
            "lang": clean_lang,
            "translated_text": "",
            "source_text": clean_text,
            "number_check": None,
            "model_used": None,
            "live_calls": 0,
            "error": f"Unsupported language '{clean_lang}'. Supported: {sorted(list(SUPPORTED_LANGUAGES.keys()))}",
        }

    lang_name = SUPPORTED_LANGUAGES[clean_lang]

    if not clean_text:
        return {
            "status": "ok",
            "lang": clean_lang,
            "translated_text": "",
            "source_text": clean_text,
            "number_check": {
                "status": "pass",
                "missing_in_translation": [],
                "extra_in_translation": [],
                "source_numbers": [],
                "translated_numbers": [],
            },
            "model_used": None,
            "live_calls": 0,
        }

    # Quota check before any live model call (when no fake translator is injected)
    if llm_call is None:
        try:
            from app.api.task_service import count_today_live_calls, load_app_config
            cfg = load_app_config()
            daily_limit = int(cfg.get("daily_soft_limit", 60))
            today_calls = count_today_live_calls()
            if today_calls >= daily_limit:
                return {
                    "status": "quota_blocked",
                    "lang": clean_lang,
                    "translated_text": "",
                    "source_text": clean_text,
                    "number_check": None,
                    "model_used": None,
                    "live_calls": 0,
                    "error": "Today's free Gemini limit is used up, so this translation did not run. Try again after the daily reset.",
                }
        except Exception:
            # If app config is unavailable in isolated context, proceed safely
            pass

    shielded_text, number_replacements = _shield_numbers(clean_text)

    prompt = (
        f"You are a professional legal-financial translator.\n"
        f"Translate the following English loan agreement text into {lang_name} ({clean_lang}).\n\n"
        f"RULES:\n"
        f"1. Translate ONLY the given text prose. Do not add explanations, conversational filler, or commentary.\n"
        f"2. Keep every opaque number placeholder EXACTLY unchanged (for example __NUM0__). Do not translate, rewrite, split, or remove placeholders. The original numbers will be restored automatically after translation.\n"
        f"3. Do not add or omit facts.\n"
        f"4. Information only; do NOT provide legal or financial advice.\n"
        f"5. Output only the direct translation text.\n\n"
        f"Text to translate:\n"
        f"{shielded_text}"
    )

    live_calls = 0
    model_used: str | None = None

    if llm_call is not None:
        def call_model(p: str) -> str:
            nonlocal live_calls, model_used
            live_calls += 1
            model_used = "injected_translator"
            return llm_call(p)
    else:
        client = GeminiClient()
        bulk_model = client.models.get("bulk", "gemini-3.5-flash-lite")
        model_used = bulk_model

        def call_model(p: str) -> str:
            nonlocal live_calls
            live_calls += 1
            return client.generate(p, model_alias="bulk", temperature=0.0)

    # Attempt 1
    try:
        translated_raw = _restore_numbers(call_model(prompt).strip(), number_replacements)
    except Exception as exc:
        return {
            "status": "failed",
            "lang": clean_lang,
            "translated_text": "",
            "source_text": clean_text,
            "number_check": None,
            "model_used": model_used,
            "live_calls": live_calls,
            "error": str(exc),
        }

    num_check = check_numbers(clean_text, translated_raw)
    if num_check.get("status") == "pass":
        return {
            "status": "ok",
            "lang": clean_lang,
            "translated_text": translated_raw,
            "source_text": clean_text,
            "number_check": num_check,
            "model_used": model_used,
            "live_calls": live_calls,
        }

    # Attempt 2: Retry at most ONCE with explicit feedback on failing numbers
    missing = num_check.get("missing_in_translation", [])
    extra = num_check.get("extra_in_translation", [])
    notes: list[str] = []
    if missing:
        notes.append(f"Missing numbers from source: {missing}")
    if extra:
        notes.append(f"Extra numbers introduced: {extra}")

    retry_prompt = (
        f"{prompt}\n\n"
        f"CRITICAL CORRECTION (Retry 1 of 1):\n"
        f"Your previous translation failed the numeric consistency check: {'; '.join(notes)}.\n"
        f"Please ensure every number from the original English text is preserved accurately in the translation."
    )

    try:
        translated_retry = _restore_numbers(call_model(retry_prompt).strip(), number_replacements)
    except Exception as exc:
        return {
            "status": "failed",
            "lang": clean_lang,
            "translated_text": "",
            "source_text": clean_text,
            "number_check": num_check,
            "model_used": model_used,
            "live_calls": live_calls,
            "error": str(exc),
        }

    num_check2 = check_numbers(clean_text, translated_retry)
    if num_check2.get("status") == "pass":
        return {
            "status": "ok",
            "lang": clean_lang,
            "translated_text": translated_retry,
            "source_text": clean_text,
            "number_check": num_check2,
            "model_used": model_used,
            "live_calls": live_calls,
        }

    # If it still fails, return status "number_check_failed" with failing numbers
    # Never show a translation that failed the check as if it were good
    return {
        "status": "number_check_failed",
        "lang": clean_lang,
        "translated_text": "",
        "source_text": clean_text,
        "number_check": num_check2,
        "model_used": model_used,
        "live_calls": live_calls,
        "error": (
            f"Number check failed between translation and original text. "
            f"Missing: {num_check2.get('missing_in_translation')}, "
            f"Extra: {num_check2.get('extra_in_translation')}"
        ),
    }
