"""src/extract/match_values.py

Stage 3a-fix: Transparent, rule-based value matcher with pre-registered tiers:
  - exact: equal after Unicode NFC, lowercase, whitespace collapse.
  - normalized: equal after normalizing money, percentages, unambiguous dates to ISO,
    and legal entity / article tokens + punctuation.
  - partial: all numbers of the reference appear in the prediction (or vice versa)
    AND symmetric token overlap (Dice/F1) >= 0.6.
  - no: otherwise.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

_SCALE_MAP = {
    "thousand": Decimal("1000"),
    "million": Decimal("1000000"),
    "billion": Decimal("1000000000"),
    "lakh": Decimal("100000"),
    "lakhs": Decimal("100000"),
    "crore": Decimal("10000000"),
    "crores": Decimal("10000000"),
}

_MONTHS = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sept": 9, "sep": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}

_MONTH_PAT = "|".join(_MONTHS.keys())

_STOPWORDS = {
    "the", "a", "an", "of", "and", "or", "in", "on", "to", "for", "by", "as",
    "is", "are", "be", "at", "from", "with", "this", "that", "it",
}

_PUNCT_DASHE_TRANS = str.maketrans({
    "\u2018": "'", "\u2019": "'", "\u201a": "'",
    "\u201c": '"', "\u201d": '"', "\u201e": '"',
    "\u2013": "-", "\u2014": "-", "\u2212": "-", "\u2011": "-",
})


def _exact_normalize(text: str) -> str:
    """Unicode NFC, lowercase, and whitespace collapse."""
    t = unicodedata.normalize("NFC", str(text or ""))
    t = t.lower()
    return " ".join(t.split())


def _canonical_decimal_str(dec: Decimal) -> str:
    """Formats a Decimal without scientific notation or trailing fractional zeros."""
    s = format(dec.normalize(), "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"


def _try_iso_date(year: int, month: int, day: int) -> str | None:
    if year < 1900 or year > 2100:
        return None
    try:
        return datetime(year, month, day).strftime("%Y-%m-%d")
    except ValueError:
        return None


def _normalize_dates_to_iso(text: str) -> str:
    """Converts unambiguous dates (named months or unambiguous numeric formats) to YYYY-MM-DD."""
    t = text

    # 1. Day-first with month name: "1st day of February, 2011" / "28 March 1997"
    day_first = re.compile(
        rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:day\s+of\s+|of\s+)?({_MONTH_PAT})\.?\s*,?\s*(\d{{4}})\b",
        re.IGNORECASE,
    )

    def _rep_day_first(m: re.Match[str]) -> str:
        iso = _try_iso_date(int(m.group(3)), _MONTHS[m.group(2).lower()], int(m.group(1)))
        return iso if iso else m.group(0)

    t = day_first.sub(_rep_day_first, t)

    # 2. Month-first with month name: "February 1, 2011" / "May 9th, 2015"
    month_first = re.compile(
        rf"\b({_MONTH_PAT})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?\s*,?\s*(\d{{4}})\b",
        re.IGNORECASE,
    )

    def _rep_month_first(m: re.Match[str]) -> str:
        iso = _try_iso_date(int(m.group(3)), _MONTHS[m.group(1).lower()], int(m.group(2)))
        return iso if iso else m.group(0)

    t = month_first.sub(_rep_month_first, t)

    # 3. Unambiguous slash/dash dates where one part > 12 or YYYY-first (YYYY-MM-DD / YYYY/MM/DD)
    ymd_re = re.compile(r"\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b")

    def _rep_ymd(m: re.Match[str]) -> str:
        iso = _try_iso_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        return iso if iso else m.group(0)

    t = ymd_re.sub(_rep_ymd, t)

    dmy_or_mdy_re = re.compile(r"\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b")

    def _rep_dmy_mdy(m: re.Match[str]) -> str:
        a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if a > 12 and b <= 12:
            iso = _try_iso_date(y, b, a)
            return iso if iso else m.group(0)
        if b > 12 and a <= 12:
            iso = _try_iso_date(y, a, b)
            return iso if iso else m.group(0)
        # Ambiguous when both a <= 12 and b <= 12 and a != b; equal (e.g. 05/05/2025) is unambiguous
        if a == b and a <= 12:
            iso = _try_iso_date(y, a, b)
            return iso if iso else m.group(0)
        return m.group(0)

    t = dmy_or_mdy_re.sub(_rep_dmy_mdy, t)
    return t


def _normalize_money_and_percent(text: str) -> str:
    """Normalizes percentages (8.50% -> 8.5%) and money expressions (USD / $ / 30 million -> 30000000)."""
    t = text

    # Strip commas inside numbers: 30,000,000 -> 30000000
    t = re.sub(r"(?<=\d),(?=\d)", "", t)

    # Normalize percentages BEFORE stripping dollar/currency markers
    pct_re = re.compile(r"\b(\d+(?:\.\d+)?)\s*(?:%|percent|per\s+cent|प्रतिशत)\b|\b(\d+(?:\.\d+)?)\s*%", re.IGNORECASE)

    def _rep_pct(m: re.Match[str]) -> str:
        num = m.group(1) or m.group(2)
        try:
            return f"{_canonical_decimal_str(Decimal(num))}%"
        except InvalidOperation:
            return m.group(0)

    t = pct_re.sub(_rep_pct, t)

    # Expand scaled numbers (e.g. "$30 million", "30.5 million", "USD 2.5 billion")
    scale_re = re.compile(
        r"(?:(?:u\.?s\.?\s*dollars?|usd|u\.?s\.?\$|\$|rs\.?|inr|₹|eur|gbp)\s*)?"
        r"(\d+(?:\.\d+)?)\s*(thousand|million|billion|lakhs?|crores?)\b"
        r"(?:\s*(?:dollars?|usd))?",
        re.IGNORECASE,
    )

    def _rep_scaled(m: re.Match[str]) -> str:
        full = m.group(0).lower()
        num_str = m.group(1)
        scale_word = m.group(2).lower()
        try:
            val = Decimal(num_str) * _SCALE_MAP[scale_word]
        except (InvalidOperation, KeyError):
            return m.group(0)
        canon = _canonical_decimal_str(val)
        # Keep non-USD/INR prefix distinction for GBP/EUR/INR only if explicitly present
        if any(tok in full for tok in ("rs", "inr", "₹")):
            return f"inr {canon}"
        if "eur" in full or "€" in full:
            return f"eur {canon}"
        if "gbp" in full or "£" in full:
            return f"gbp {canon}"
        return canon

    t = scale_re.sub(_rep_scaled, t)

    # Normalize plain USD / $ amounts (e.g., "USD 30000000", "$500.00" -> "30000000", "500")
    usd_prefix_re = re.compile(r"(?:\bu\.?s\.?d\.?\b|\bu\.?s\.?\$|\$)\s*(\d+(?:\.\d+)?)", re.IGNORECASE)

    def _rep_usd(m: re.Match[str]) -> str:
        try:
            return _canonical_decimal_str(Decimal(m.group(1)))
        except InvalidOperation:
            return m.group(1)

    t = usd_prefix_re.sub(_rep_usd, t)

    # Remove trailing "dollars" / "dollar" / "usd" attached to numeric amounts
    t = re.sub(r"(?<=\d)\s*(?:u\.?s\.?\s*dollars?|dollars?|usd)\b", "", t, flags=re.IGNORECASE)

    # Normalize Indian Rupees symbols/prefixes consistently
    t = re.sub(r"(?:₹|\brs\.?|\binr\b)\s*(\d+(?:\.\d+)?)", lambda m: f"inr {_canonical_decimal_str(Decimal(m.group(1)))}", t, flags=re.IGNORECASE)

    # Canonicalize standalone decimals with trailing .00 (e.g. "500.00" -> "500", "8.50" -> "8.5")
    def _rep_dec(m: re.Match[str]) -> str:
        try:
            return _canonical_decimal_str(Decimal(m.group(0)))
        except InvalidOperation:
            return m.group(0)

    t = re.sub(r"\b\d+\.\d+\b", _rep_dec, t)
    return t


def _full_normalize(text: str) -> str:
    """Applies exact normalization + dates + money/percent + party suffixes + punctuation strip."""
    t = _exact_normalize(text).translate(_PUNCT_DASHE_TRANS)
    t = _normalize_dates_to_iso(t)
    t = _normalize_money_and_percent(t)

    # Remove party suffixes & leading/standalone "the": "N.A.", "Inc.", "LLC", "Corp.", "The"
    t = re.sub(r"\bn\.?\s*a\.?(?=\s|,|;|$|\))", " ", t, flags=re.IGNORECASE)
    t = re.sub(r"\b(?:inc|llc|corp)\.?(?=\s|,|;|$|\))", " ", t, flags=re.IGNORECASE)
    t = re.sub(r"\bthe\b", " ", t, flags=re.IGNORECASE)

    # Preserve decimal dots and percentage symbols and ISO hyphens inside tokens; strip other punctuation
    t = re.sub(r"(?<!\d)[./-]|/(?!\d)", " ", t)
    t = re.sub(r"[./-](?!\d)", " ", t)
    t = re.sub(r"[,;:()\[\]{}\"'?!*~`]", " ", t)
    return " ".join(t.split())


def _extract_numbers(norm_text: str) -> set[str]:
    """Extracts canonical numeric tokens (dates split or numbers/percentages unified)."""
    tokens = re.findall(r"\d+(?:\.\d+)?", norm_text)
    out: set[str] = set()
    for tok in tokens:
        try:
            out.add(_canonical_decimal_str(Decimal(tok)))
        except InvalidOperation:
            out.add(tok)
    return out


def _content_tokens(norm_text: str) -> set[str]:
    raw_tokens = re.findall(r"\d{1,4}[/-]\d{1,4}(?:[/-]\d{1,4})?|\d+(?:\.\d+)?%?|[a-z0-9\u0900-\u097f]+", norm_text)
    return {tok for tok in raw_tokens if tok not in _STOPWORDS}


def _token_f1(tokens_a: set[str], tokens_b: set[str]) -> float:
    if not tokens_a or not tokens_b:
        return 0.0
    inter = len(tokens_a & tokens_b)
    return (2.0 * inter) / (len(tokens_a) + len(tokens_b))


def values_match(field: str, predicted: str, reference: str) -> dict[str, Any]:
    """Compares predicted vs reference field value under fixed pre-registered rules.

    Returns {"match": "exact" | "normalized" | "partial" | "no", "reason": str}.
    """
    p_exact = _exact_normalize(predicted)
    r_exact = _exact_normalize(reference)

    if not p_exact or not r_exact:
        return {"match": "no", "reason": "empty predicted or reference value"}

    if p_exact == r_exact:
        return {"match": "exact", "reason": "equal after NFC, lowercase, and whitespace collapse"}

    p_norm = _full_normalize(predicted)
    r_norm = _full_normalize(reference)

    if p_norm and p_norm == r_norm:
        return {
            "match": "normalized",
            "reason": "equal after money, percent, ISO date, entity-suffix, and punctuation normalization",
        }

    # Partial match: reference numbers contained in prediction (or vice versa) AND token overlap >= 0.6
    nums_p = _extract_numbers(p_norm)
    nums_r = _extract_numbers(r_norm)

    if nums_r and nums_p:
        numbers_ok = nums_r.issubset(nums_p) or nums_p.issubset(nums_r)
    elif not nums_r:
        numbers_ok = True
    else:
        # Reference specifies numeric value(s) while prediction contains none
        numbers_ok = False

    if not numbers_ok:
        return {
            "match": "no",
            "reason": f"numeric mismatch (pred={sorted(nums_p)}, ref={sorted(nums_r)})",
        }

    tok_p = _content_tokens(p_norm)
    tok_r = _content_tokens(r_norm)
    overlap = _token_f1(tok_p, tok_r)

    if overlap >= 0.6:
        return {
            "match": "partial",
            "reason": f"numbers compatible and symmetric token overlap={overlap:.3f} >= 0.6",
        }

    return {
        "match": "no",
        "reason": f"token overlap={overlap:.3f} < 0.6",
    }
