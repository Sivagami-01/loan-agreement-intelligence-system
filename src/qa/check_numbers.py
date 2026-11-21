"""src/qa/check_numbers.py

Deterministic Number, Date, Percentage, and Money Checker (Stage 2c-3).
No LLM / API calls.
Extracts numbers, dates, percentages, and currency amounts from answer text and
checks that each extracted value appears in the verified quotes or cited pages
after deterministic normalization (including Devanagari ०-९ -> 0-9).
Does NOT guess or convert date formats (e.g. '14/08/2024' != 'August 14, 2024').
"""

from __future__ import annotations

import re
import unicodedata
from decimal import Decimal, InvalidOperation
from typing import Any

DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

MONTH_PATTERN = (
    r"(?:january|jan|february|feb|march|mar|april|apr|may|june|jun|"
    r"july|jul|august|aug|september|sept|sep|october|oct|november|nov|december|dec)"
)

# Priority extraction patterns on normalized text (match dates before standalone numbers)
DATE_SLASH_DASH_RE = re.compile(r"\b\d{1,4}[-/]\d{1,2}[-/]\d{1,4}\b")
DATE_MONTH_FIRST_RE = re.compile(
    rf"\b{MONTH_PATTERN}\.?\s+\d{{1,2}}(?:st|nd|rd|th)?(?:\s*,?\s*\d{{2,4}})?\b",
    re.IGNORECASE,
)
DATE_DAY_FIRST_RE = re.compile(
    rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:of\s+)?{MONTH_PATTERN}\.?(?:\s*,?\s*\d{{2,4}})?\b",
    re.IGNORECASE,
)
DATE_MONTH_YEAR_RE = re.compile(
    rf"\b{MONTH_PATTERN}\.?\s+\d{{4}}\b",
    re.IGNORECASE,
)

PERCENT_RE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:%|percent|per\s+cent|प्रतिशत)")
MONEY_SYMBOL_RE = re.compile(r"(?:[$₹€£¥]|rs\.?|inr|usd|eur|gbp)\s*\d+(?:\.\d+)?", re.IGNORECASE)
NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?\b")


def normalize_numeric_text(text: str) -> str:
    """Normalizes digits (Devanagari -> ASCII), commas in numbers, currency spacing, and dates."""
    if not text:
        return ""
    t = unicodedata.normalize("NFC", str(text)).translate(DEVANAGARI_DIGITS)
    t = re.sub(r"[\u2014\u2013\u2212\u2011\u2012\u2015]", "-", t)
    t = " ".join(t.split()).lower()
    # Remove thousands commas inside digits: 30,000,000 -> 30000000
    t = re.sub(r"(?<=\d),(?=\d)", "", t)
    # Remove spaces after currency symbols ($ 500 -> $500) and before % (8.5 % -> 8.5%)
    t = re.sub(r"([$₹€£¥])\s+(?=\d)", r"\1", t)
    t = re.sub(r"\b(rs\.?|inr|usd|eur|gbp)\s+(?=\d)", lambda m: m.group(1).replace(".", "") + " ", t)
    t = re.sub(r"\brs\.(?=\d)", "rs ", t)
    t = re.sub(r"(?<=\d)\s+%", "%", t)
    return t


def _strip_decimal_zeros(num_str: str) -> str:
    """Normalizes '8.50' -> '8.5' or '500.00' -> '500' when comparing pure numeric values."""
    if "." not in num_str:
        return num_str
    try:
        d = Decimal(num_str).normalize()
        # Avoid scientific notation like 5E+2
        s = format(d, "f")
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        return s
    except InvalidOperation:
        return num_str


def extract_items(text: str) -> list[tuple[str, str]]:
    """Extracts typed numeric/date/money/percent tokens as (kind, normalized_value) tuples."""
    norm = normalize_numeric_text(text)
    if not norm:
        return []

    spans: list[tuple[int, int, str, str]] = []
    used = [False] * len(norm)

    def _claim(pattern: re.Pattern[str], kind: str) -> None:
        for m in pattern.finditer(norm):
            s, e = m.start(), m.end()
            if any(used[i] for i in range(s, e)):
                continue
            val = m.group(0).strip()
            for i in range(s, e):
                used[i] = True
            spans.append((s, e, kind, val))

    # Order matters: dates first, then percentages, then currency amounts, then bare numbers
    _claim(DATE_SLASH_DASH_RE, "date")
    _claim(DATE_MONTH_FIRST_RE, "date")
    _claim(DATE_DAY_FIRST_RE, "date")
    _claim(DATE_MONTH_YEAR_RE, "date")
    _claim(PERCENT_RE, "percent")
    _claim(MONEY_SYMBOL_RE, "money")
    _claim(NUMBER_RE, "number")

    spans.sort(key=lambda x: x[0])
    return [(kind, val) for _, _, kind, val in spans]


def _numeric_regex(num_str: str) -> str:
    """Builds regex matching symmetric trailing decimal zeros (8.5 <-> 8.50, 500 <-> 500.00)."""
    stripped = _strip_decimal_zeros(num_str)
    if "." in stripped:
        return re.escape(stripped) + r"0*(?!\d)"
    return re.escape(stripped) + r"(?:\.0+)?(?![\d.])"


def _item_in_reference(kind: str, val: str, norm_ref: str, ref_clean_dates: str) -> bool:
    """Checks if an extracted item matches the normalized reference text with digit boundaries."""
    if kind == "date":
        # Exact date format check (only normalize comma/whitespace around month/day/year, NEVER convert format)
        clean_val = re.sub(r"\s*,\s*", " ", val).replace(".", "").strip()
        clean_val = " ".join(clean_val.split())
        # Ensure digit/letter boundary on numeric slash/dash dates so 1/2/2024 doesn't match 11/2/2024
        pattern = r"(?<![0-9a-z])" + re.escape(clean_val) + r"(?![0-9a-z])"
        return bool(re.search(pattern, ref_clean_dates))

    if kind == "percent":
        num_part = re.search(r"\d+(?:\.\d+)?", val).group(0)  # type: ignore[union-attr]
        num_pat = _numeric_regex(num_part)
        # Match '8.50%', '8.5%', '8.50 percent', '8.50 प्रतिशत'
        p = rf"(?<![\d.]){num_pat}\s*(?:%|percent|per\s+cent|प्रतिशत)"
        return bool(re.search(p, norm_ref))

    if kind == "money":
        # Separate prefix symbol/code from numeric part
        m = re.match(r"^([$₹€£¥]|rs|inr|usd|eur|gbp)\s*(\d+(?:\.\d+)?)$", val)
        if not m:
            return val in norm_ref
        curr, num_part = m.group(1), m.group(2)
        num_pat = _numeric_regex(num_part)
        # Equivalent Indian rupee prefixes (rs / inr / ₹) or exact symbol match
        if curr in {"rs", "inr", "₹"}:
            curr_pattern = r"(?:₹|rs\.?|inr)"
        else:
            curr_pattern = re.escape(curr)
        p = rf"{curr_pattern}\s*{num_pat}"
        return bool(re.search(p, norm_ref))

    if kind == "number":
        num_pat = _numeric_regex(val)
        p = rf"(?<![\d.]){num_pat}"
        return bool(re.search(p, norm_ref))

    return val in norm_ref


def check_numbers(
    answer: str,
    evidence: list[dict[str, Any]] | None = None,
    doc_pages: dict[int, str] | None = None,
) -> dict[str, Any]:
    """Checks that all numbers, dates, percentages, and money amounts in `answer`
    appear in the verified quotes or cited pages.

    Returns:
        {"all_found": bool, "missing": list[str], "extracted": list[str]}
    """
    items = extract_items(answer)
    if not items:
        return {"all_found": True, "missing": [], "extracted": []}

    ref_parts: list[str] = []
    cited_pages: set[int] = set()
    if evidence:
        for ev in evidence:
            if isinstance(ev, dict):
                q_txt = str(ev.get("quote", ""))
                if q_txt:
                    ref_parts.append(q_txt)
                p = ev.get("page")
                if p is not None:
                    try:
                        cited_pages.add(int(p))
                    except (TypeError, ValueError):
                        pass

    if doc_pages:
        for p_num in sorted(cited_pages):
            if p_num in doc_pages:
                ref_parts.append(str(doc_pages[p_num]))

    norm_ref = normalize_numeric_text("\n".join(ref_parts))
    ref_clean_dates = re.sub(r"\s*,\s*", " ", norm_ref).replace(".", " ")
    ref_clean_dates = " ".join(ref_clean_dates.split())

    missing: list[str] = []
    extracted: list[str] = []
    for kind, val in items:
        extracted.append(val)
        if not _item_in_reference(kind, val, norm_ref, ref_clean_dates):
            missing.append(val)

    return {
        "all_found": len(missing) == 0,
        "missing": missing,
        "extracted": extracted,
    }
