"""src/qa/chunker.py

Page-Respecting Document Chunker for Retrieval (Stage 2c-2a).
- Splits each page independently (no chunk ever crosses a page boundary).
- Prefers paragraph, numbered-clause, and heading boundaries, then newlines,
  then sentence boundaries, then whitespace.
- Grapheme-safe boundary snapping ensures Unicode combining marks and Indic
  virama conjuncts are never split mid-character.
- Zero lost text: sliding intervals cover [0, len(page_text)) completely.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

# Indic Virama / Halant characters (Devanagari, Bengali, Gurmukhi, Malayalam, Tamil)
VIRAMAS = {"\u094D", "\u09CD", "\u0A4D", "\u0D4D", "\u0BCD"}
JOINERS = {"\u200C", "\u200D"}

# Boundary regex patterns in priority order
PARA_HEADING_RE = re.compile(
    r"(?:\n\s*\n+|\n(?=(?:\d+\.(?:\d+\.)*\s+|[a-zA-Z]\)\s+|\([a-zA-Z0-9]+\)\s+|[IVX]+\.\s+|Section\s+\d+|Article\s+\d+|Clause\s+\d+|#{1,4}\s)))"
)
NEWLINE_RE = re.compile(r"\n+")
SENTENCE_RE = re.compile(r"(?<=[.!?।])\s+")
WHITESPACE_RE = re.compile(r"\s+")


def _is_unsafe_split_pos(text: str, pos: int) -> bool:
    """Returns True if splitting at index `pos` would break a Unicode grapheme or Indic conjunct."""
    if pos <= 0 or pos >= len(text):
        return False
    curr = text[pos]
    prev = text[pos - 1]
    # Never split right before a combining mark (Mn, Mc, Me) or joiner
    if unicodedata.category(curr).startswith("M") or curr in JOINERS:
        return True
    # Never split right after a Virama/Halant or joiner (breaks Indic conjuncts)
    if prev in VIRAMAS or prev in JOINERS:
        return True
    return False


def _snap_safe_pos(text: str, pos: int, min_pos: int, max_pos: int) -> int:
    """Adjusts `pos` so it never splits inside a Unicode grapheme cluster."""
    if not _is_unsafe_split_pos(text, pos):
        return pos
    # Try advancing forward within max_pos
    p = pos
    while p < max_pos and _is_unsafe_split_pos(text, p):
        p += 1
    if not _is_unsafe_split_pos(text, p) and p > min_pos:
        return p
    # Fallback: walk backward within min_pos
    p = pos
    while p > min_pos and _is_unsafe_split_pos(text, p):
        p -= 1
    return max(min_pos, p)


def _find_best_split(text: str, start: int, max_end: int) -> int:
    """Finds the furthest natural boundary in text[start:max_end]."""
    min_end = start + max(1, (max_end - start) // 3)
    window = text[start:max_end]

    for pattern in (PARA_HEADING_RE, NEWLINE_RE, SENTENCE_RE, WHITESPACE_RE):
        best: int | None = None
        for match in pattern.finditer(window):
            # Split after whitespace/boundary except for lookahead paragraph starts where match.end() is after \n
            candidate = start + match.end()
            if candidate >= min_end and candidate <= max_end:
                best = candidate
        if best is not None:
            return _snap_safe_pos(text, best, start + 1, max_end)

    # If no boundary in [min_end, max_end], look for any whitespace in [start+1, max_end]
    best_ws: int | None = None
    for match in WHITESPACE_RE.finditer(window):
        candidate = start + match.end()
        if start < candidate <= max_end:
            best_ws = candidate
    if best_ws is not None:
        return _snap_safe_pos(text, best_ws, start + 1, max_end)

    # Last resort for giant unspaced strings: grapheme-safe split near max_end
    return _snap_safe_pos(text, max_end, start + 1, len(text))


def chunk_page(
    doc_id: str,
    page_num: int,
    page_text: str,
    chunk_chars: int = 2000,
    chunk_overlap: int = 200,
) -> list[dict[str, Any]]:
    """Splits a single page's text into chunks without crossing page boundaries.

    Guarantees complete coverage of page_text (no characters dropped) and
    safe Unicode/Indic boundaries.
    """
    if not page_text or not page_text.strip():
        return []

    chunk_chars = max(50, int(chunk_chars))
    chunk_overlap = max(0, min(int(chunk_overlap), chunk_chars - 1))

    n = len(page_text)
    if n <= chunk_chars:
        return [
            {
                "doc_id": doc_id,
                "page": int(page_num),
                "chunk_id": f"{doc_id}::p{page_num}::c0",
                "text": page_text,
                "char_start": 0,
                "char_end": n,
            }
        ]

    chunks: list[dict[str, Any]] = []
    start = 0
    chunk_idx = 0

    while start < n:
        if n - start <= chunk_chars:
            end = n
        else:
            end = _find_best_split(page_text, start, min(n, start + chunk_chars))
            if end <= start:
                end = min(n, start + chunk_chars)

        chunk_text = page_text[start:end]
        if chunk_text.strip():
            chunks.append(
                {
                    "doc_id": doc_id,
                    "page": int(page_num),
                    "chunk_id": f"{doc_id}::p{page_num}::c{chunk_idx}",
                    "text": chunk_text,
                    "char_start": start,
                    "char_end": end,
                }
            )
            chunk_idx += 1

        if end >= n:
            break

        if chunk_overlap == 0:
            next_start = end
        else:
            raw_next = max(start + 1, end - chunk_overlap)
            # Snap forward to word start if possible so overlap begins cleanly
            ws_match = WHITESPACE_RE.search(page_text, raw_next, end)
            if ws_match and ws_match.end() < end:
                next_start = ws_match.end()
            else:
                next_start = raw_next
            next_start = _snap_safe_pos(page_text, next_start, start + 1, end)
            if next_start <= start:
                next_start = start + 1

        start = next_start

    return chunks


def chunk_document(
    doc_id: str,
    doc_pages: dict[int, str],
    chunk_chars: int = 2000,
    chunk_overlap: int = 200,
) -> list[dict[str, Any]]:
    """Chunks every page in doc_pages sequentially while strictly preserving page boundaries."""
    all_chunks: list[dict[str, Any]] = []
    for page_num in sorted(doc_pages.keys()):
        page_text = doc_pages[page_num]
        page_chunks = chunk_page(
            doc_id=doc_id,
            page_num=page_num,
            page_text=page_text,
            chunk_chars=chunk_chars,
            chunk_overlap=chunk_overlap,
        )
        all_chunks.extend(page_chunks)
    return all_chunks
