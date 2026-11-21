"""src/qa/verify_quotes.py

Verbatim Quote Verification Engine for QA Grounding.
Rules:
- Unicode NFC normalization
- Collapse whitespace (spaces, tabs, newlines)
- Unify curly/straight quotes and dashes
- Case-insensitive comparison
- Zero fuzzy matching (exact normalized substring match only)
- Page verification:
  * Quote found on specified page -> verified
  * Quote found on a different page -> verified with page corrected and flag 'page_corrected'
  * Quote not found anywhere in document -> rejected
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any


def normalize(text: str) -> str:
    """Normalize text for exact substring matching.

    - Unicode NFC normalization
    - Unify quotation marks: curly double/single quotes to standard quotes
    - Unify dashes: em-dash, en-dash, minus to standard hyphen '-'
    - Collapse contiguous whitespace (including newlines and tabs) to a single space
    - Lowercase for case-insensitivity
    """
    if not text:
        return ""

    # 1. Unicode NFC
    t = unicodedata.normalize("NFC", str(text))

    # 2. Unify double quotes: “ ” „ « » “ ” to "
    t = re.sub(r"[\u201C\u201D\u201E\u00AB\u00BB\u201F\u2033\u2036]", '"', t)

    # 3. Unify single quotes: ‘ ’ ‚ ‛ ` ′ ‵ to '
    t = re.sub(r"[\u2018\u2019\u201A\u201B\u0060\u2032\u2035]", "'", t)

    # 4. Unify hyphens and dashes: — (em), – (en), − (minus), ‑ (non-breaking) to -
    t = re.sub(r"[\u2014\u2013\u2212\u2011\u2012\u2015\uFE63\uFF0D]", "-", t)

    # 5. Collapse all whitespace into a single space and strip edges
    t = " ".join(t.split())

    # 6. Normalize spacing adjacent to punctuation artifacts (e.g. newline before closing paren)
    t = re.sub(r"\s+([,.\);:!?\]])", r"\1", t)
    t = re.sub(r"([(\[{])\s+", r"\1", t)

    # 7. Lowercase
    return t.lower()


def verify_evidence(
    doc_pages: dict[int, str],
    evidence_list: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Verifies evidence quotes against document pages.

    Args:
        doc_pages: mapping of page number (int) to page text (str).
        evidence_list: list of dicts with 'quote' (str) and 'page' (int or str).

    Returns:
        (verified_evidence, flags)
        - verified_evidence: list of surviving verified dicts.
        - flags: list of diagnostic flags (e.g. 'page_corrected').
    """
    verified: list[dict[str, Any]] = []
    flags: list[str] = []

    if not doc_pages or not evidence_list:
        return verified, flags

    # Pre-normalize all page texts
    normalized_pages: dict[int, str] = {
        int(page_num): normalize(text)
        for page_num, text in doc_pages.items()
    }

    for item in evidence_list:
        if not isinstance(item, dict):
            continue

        raw_quote = str(item.get("quote", "")).strip()
        if not raw_quote:
            continue

        target_page_raw = item.get("page")
        target_page: int | None = None
        if target_page_raw is not None:
            try:
                target_page = int(target_page_raw)
            except (ValueError, TypeError):
                target_page = None

        norm_quote = normalize(raw_quote)
        if not norm_quote:
            continue

        # 1. Check specified page
        trimmed_quote = norm_quote.strip(" .,:;!?'\"()")
        if target_page is not None and target_page in normalized_pages:
            page_text = normalized_pages[target_page]
            if norm_quote in page_text or (trimmed_quote and trimmed_quote in page_text):
                verified.append({
                    "quote": raw_quote,
                    "page": target_page,
                    "verified": True,
                    "flags": [],
                })
                continue

        # 2. Check other pages in document
        found_page: int | None = None
        for page_num, page_norm in normalized_pages.items():
            if target_page is not None and page_num == target_page:
                continue
            if norm_quote in page_norm or (trimmed_quote and trimmed_quote in page_norm):
                found_page = page_num
                break

        if found_page is not None:
            item_flags = ["page_corrected"]
            if "page_corrected" not in flags:
                flags.append("page_corrected")
            verified.append({
                "quote": raw_quote,
                "page": found_page,
                "original_page": target_page,
                "verified": True,
                "flags": item_flags,
            })
            continue

        # 3. Not found anywhere -> rejected (dropped)

    return verified, flags
