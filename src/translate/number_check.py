"""src/translate/number_check.py

Stage 5a: Number, date, and amount checker for translations (pure Python, offline).
Extracts numeric tokens (amounts, percentages, dates, counts) from source English
and translated text, normalizes digits across Indic scripts (Devanagari, Bengali,
Gurmukhi, Tamil, Malayalam) using unicodedata.decimal, strips thousands separators,
and compares them as multisets.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from typing import Any


def normalize_script_digits(text: str) -> str:
    """Converts unicode decimal digits from Indic scripts (Devanagari, Bengali,
    Gurmukhi, Tamil, Malayalam, etc.) to standard ASCII 0-9 digits using unicodedata.decimal.
    """
    chars: list[str] = []
    for ch in text:
        try:
            d = unicodedata.decimal(ch)
            chars.append(str(d))
        except (ValueError, TypeError):
            chars.append(ch)
    return "".join(chars)


def normalize_number(num_str: str) -> str:
    """Normalizes a numeric string (strips leading zeros on integers,
    and unnecessary trailing zeros on decimal numbers).
    """
    if "." in num_str:
        parts = num_str.split(".", 1)
        integer_part = str(int(parts[0])) if parts[0] else "0"
        dec_part = parts[1].rstrip("0")
        if not dec_part:
            return integer_part
        return f"{integer_part}.{dec_part}"
    return str(int(num_str))


def extract_numeric_tokens(text: str) -> list[str]:
    """Extracts all numeric tokens (dates, amounts, percentages, counts) from text.
    Returns a list of normalized token strings in order of occurrence.
    """
    if not text or not isinstance(text, str):
        return []

    # 1. Normalize all Indic script digits to standard 0-9
    norm_text = normalize_script_digits(text)

    tokens: list[str] = []

    # 2. Extract and mask dates so day/month/year are not re-extracted as standalone numbers
    # ISO format: YYYY-MM-DD or YYYY/MM/DD
    iso_pattern = re.compile(r"(?<!\d)(\d{4})([/\-])(\d{1,2})\2(\d{1,2})(?!\d)")

    def _mask_iso(m: re.Match[str]) -> str:
        y, sep, mth, d = m.groups()
        tokens.append(f"{int(d):02d}/{int(mth):02d}/{int(y):04d}")
        return " " * len(m.group(0))

    cleaned = iso_pattern.sub(_mask_iso, norm_text)

    # Standard format: DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
    std_pattern = re.compile(r"(?<!\d)(\d{1,2})([/\-\.])(\d{1,2})\2(\d{4})(?!\d)")

    def _mask_std(m: re.Match[str]) -> str:
        d, sep, mth, y = m.groups()
        tokens.append(f"{int(d):02d}/{int(mth):02d}/{int(y):04d}")
        return " " * len(m.group(0))

    cleaned = std_pattern.sub(_mask_std, cleaned)

    # 3. Remove thousands separators between digits (e.g., 5,00,000 or 500,000 -> 500000)
    cleaned = re.sub(r"(?<=\d),(?=\d)", "", cleaned)

    # 4. Extract numeric tokens, consuming ordinal suffixes so each ordinal
    # contributes exactly one number in English and Tamil.
    num_pattern = re.compile(
        r"(?<!\w)(\d+(?:\.\d+)?)(?:\s*(?:st|nd|rd|th|ஆம்))?(?!\w)",
        re.IGNORECASE,
    )
    for m in num_pattern.finditer(cleaned):
        raw_num = m.group(1)
        tokens.append(normalize_number(raw_num))

    return tokens


def check_numbers(source_en: str, translated: str) -> dict[str, Any]:
    """Extracts numeric tokens from source and translation, compares them as multisets,
    and returns pass/fail status along with missing and extra tokens.
    """
    src_tokens = extract_numeric_tokens(source_en)
    tr_tokens = extract_numeric_tokens(translated)

    src_counts = Counter(src_tokens)
    tr_counts = Counter(tr_tokens)

    missing: list[str] = []
    for num, count in src_counts.items():
        diff = count - tr_counts.get(num, 0)
        if diff > 0:
            missing.extend([num] * diff)

    extra: list[str] = []
    for num, count in tr_counts.items():
        diff = count - src_counts.get(num, 0)
        if diff > 0:
            extra.extend([num] * diff)

    missing.sort()
    extra.sort()

    status = "pass" if (not missing and not extra) else "fail"

    return {
        "status": status,
        "missing_in_translation": missing,
        "extra_in_translation": extra,
        "source_numbers": src_tokens,
        "translated_numbers": tr_tokens,
    }
