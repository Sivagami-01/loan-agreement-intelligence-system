"""src/risk/split_clauses.py

Stage 4a-3 per-page deterministic clause splitter.

SEC agreements (from data/friend/01_loan_agreements/publicly_filed_contracts.zip):
- Parses BOTH `<PAGE>` markers and `N * * * [#####]` page-break markers where N
  is the page number that ENDS at that mark.
- Removes page-break markers cleanly from clause text.
- Detects mid-clause page breaks (trailing sentence fragment on page p continuing on
  page p+1) and stitches the continuation onto page p so no clause is cut in half.
- Assigns `page = "not available"` instead of 1 when a document has no page marks.
- Keeps min_chars=150, max_chars=1500.

Indian MITC documents (data/processed/ingested/*.txt + *.json):
- Splits per [[PAGE n]] page at headings, paragraph breaks, list markers
  ("a)", "b)", "(i)", "1.", Roman numerals, bullets), and JSON table rows.
- Uses min_chars=85 and max_chars=600 so individual terms & table rows stay isolated.
"""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from typing import Any

from src.qa.doc_loader import INGESTED_DIR, load_document

ROOT = Path(__file__).resolve().parents[2]
FRIEND_ZIP = ROOT / "data" / "friend" / "01_loan_agreements" / "publicly_filed_contracts.zip"

DEFAULT_MIN_CHARS = 150
DEFAULT_MAX_CHARS = 1500
MITC_MIN_CHARS = 85
MITC_MAX_CHARS = 600

# SEC & general line-start headings
HEADING_LINE_RE = re.compile(
    r"^(?:"
    r"(?:ARTICLE|Article|SECTION|Section|SCHEDULE|Schedule|EXHIBIT|Exhibit|ANNEX|Annex)\s+(?:[IVXLCDM]+|\d+(?:\.\d+)*)\b"
    r"|\d+(?:\.\d+){1,4}\.?(?:\s+\S)"
    r"|\d+\.\s+[A-Z][A-Za-z0-9 ,/&()'\"-]{1,}"
    r"|\([a-z0-9]{1,3}\)\s+[A-Z]"
    r"|[a-z]\)\s+[A-Z]"
    r")",
    re.MULTILINE,
)

# Finer MITC line-start headings, list markers, and bullets
MITC_LINE_MARKER_RE = re.compile(
    r"^(?:"
    r"(?:ARTICLE|Article|SECTION|Section|SCHEDULE|Schedule)\s+(?:[IVXLCDM]+|\d+(?:\.\d+)*)\b"
    r"|(?:[IVX]{1,5}|[0-9]{1,2}(?:\.[0-9]{1,2}){0,4})[.)]\s+\S"
    r"|\((?:[ivx]{1,4}|[a-z0-9]{1,3})\)\s+\S"
    r"|[a-z][.)]\s+\S"
    r"|[•\-\*▪►]\s+\S"
    r")",
    re.MULTILINE,
)

PARAGRAPH_BREAK_RE = re.compile(r"\r?\n[ \t]*\r?\n+")
SENTENCE_END_RE = re.compile(r"(?<=[.!?;:])(?:\s+|\r?\n)")

# EDGAR <PAGE> tag on its own line (optionally followed by same-line page digits only, never across \n)
EDGAR_PAGE_TAG_RE = re.compile(r"<PAGE>[ \t]*(\d*)[ \t]*(?=\r?\n|$)")

# EDGAR/SEC asterisk-hash footer break: optional footer number (optionally preceded by "S-\n"), then "* * *", optional "#####"
STAR_PAGE_MARK_RE = re.compile(
    r"(?:\r?\n[ \t]*(?:(?P<prefix>S-)[ \t]*\r?\n[ \t]*)?(?P<pnum>\d+|[ivx]{1,5})[ \t]*)?"
    r"\r?\n[ \t]*\*[ \t]+\*[ \t]+\*(?:[ \t]*\r?\n[ \t]*#####)?[ \t]*(?=\r?\n|$)"
)


def is_mitc_doc(doc_id: str) -> bool:
    """Return True if doc_id refers to an ingested local document (MITC) rather than SEC ZIP path."""
    if "/" in doc_id or "\\" in doc_id or doc_id.endswith(".txt"):
        return False
    return (INGESTED_DIR / f"{doc_id}.txt").is_file()


def _read_zip_raw(member_path: str) -> str:
    with zipfile.ZipFile(FRIEND_ZIP, "r") as zf:
        return zf.read(member_path).decode("utf-8", errors="ignore")


def split_sec_text_to_pages(raw_text: str) -> tuple[dict[int | str, str], dict[str, Any]]:
    """Parse SEC raw agreement text into clean page segments and strip page-break marks.

    Returns:
        (pages_dict, meta) where pages_dict maps integer page_num (or "not available")
        to page text with page-break marks removed, and meta describes mark format & counts.
    """
    if EDGAR_PAGE_TAG_RE.search(raw_text):
        parts = EDGAR_PAGE_TAG_RE.split(raw_text)
        pages: dict[int | str, str] = {}
        cur_page = 0
        if parts[0].strip():
            cur_page = 1
            pages[1] = parts[0]
        for i in range(1, len(parts), 2):
            explicit_num = parts[i].strip()
            body = parts[i + 1]
            p_num = int(explicit_num) if explicit_num else (cur_page + 1)
            cur_page = p_num
            pages[p_num] = (pages[p_num] + "\n" + body) if p_num in pages else body
        return pages, {"mark_type": "edgar_page_tag", "marks_count": (len(parts) - 1) // 2}

    marks = list(STAR_PAGE_MARK_RE.finditer(raw_text))
    if marks:
        pages = {}
        cur_page = 0
        pos = 0
        for m in marks:
            segment = raw_text[pos : m.start()]
            pos = m.end()
            prefix = m.group("prefix")
            pnum_str = (m.group("pnum") or "").strip()

            if prefix:
                # e.g. signature page S-1 after page 12 -> continue sequentially
                cur_page += 1
                page_num = cur_page
            elif pnum_str.isdigit():
                val = int(pnum_str)
                # Sequential continuity guard if cover/roman reset appears earlier
                if val >= cur_page and val <= cur_page + 5:
                    page_num = val
                    cur_page = val
                else:
                    cur_page += 1
                    page_num = cur_page
            else:
                cur_page += 1
                page_num = cur_page

            if prefix:
                # Keep signature indicator S-1 outside the stripped "* * *" mark if needed, or clean
                segment = segment.rstrip()
            pages[page_num] = (pages[page_num] + "\n" + segment) if page_num in pages else segment

        tail = raw_text[pos:]
        if tail.strip():
            cur_page += 1
            pages[cur_page] = tail

        return pages, {"mark_type": "star_page_mark", "marks_count": len(marks)}

    # No page-break markers at all -> keep page = "not available" instead of 1
    return {"not available": raw_text}, {"mark_type": "none", "marks_count": 0}


def _parse_ingested_pages(raw_text: str) -> dict[int | str, str]:
    parts = re.split(r"\[\[PAGE\s+(\d+)\]\]", raw_text)
    if len(parts) > 1:
        pages: dict[int | str, str] = {}
        for i in range(1, len(parts), 2):
            pnum = int(parts[i])
            body = parts[i + 1]
            pages[pnum] = (pages[pnum] + "\n" + body) if pnum in pages else body
        return pages
    return {1: raw_text} if raw_text.strip() else {}


def load_doc_pages(doc_id: str) -> dict[int | str, str]:
    """Load clean {page_num_or_not_available: page_text} for ingested doc or SEC ZIP doc."""
    if is_mitc_doc(doc_id):
        _, pages = load_document(doc_id)
        if pages:
            return dict(pages)
        txt_path = INGESTED_DIR / f"{doc_id}.txt"
        return _parse_ingested_pages(txt_path.read_text(encoding="utf-8", errors="ignore"))
    try:
        _, pages = load_document(doc_id)
        if pages:
            return dict(pages)
    except FileNotFoundError:
        pass
    raw_text = _read_zip_raw(doc_id)
    pages, _ = split_sec_text_to_pages(raw_text)
    return pages


def load_mitc_table_rows_by_page(doc_id: str) -> dict[int, list[str]]:
    """Read extracted table row prefixes from data/processed/ingested/<doc_id>.json if present."""
    json_path = INGESTED_DIR / f"{doc_id}.json"
    if not json_path.is_file():
        return {}
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    by_page: dict[int, list[str]] = {}
    for pg in data.get("pages", []):
        pnum = pg.get("page")
        if not isinstance(pnum, int):
            continue
        anchors: list[str] = []
        for tb in pg.get("tables", []):
            for row in tb.get("rows", []):
                cells = [" ".join(str(c or "").split()) for c in row if str(c or "").strip()]
                if not cells:
                    continue
                first_cell = cells[0]
                second_cell = cells[1] if len(cells) > 1 else ""
                # Build short line-matching anchor from the first non-trivial cell(s)
                anchor = first_cell if len(first_cell) >= 6 or not second_cell else f"{first_cell} {second_cell}"
                anchor = " ".join(anchor.split())
                if len(anchor) >= 4:
                    anchors.append(anchor[:40])
        if anchors:
            by_page[pnum] = anchors
    return by_page


def _trim_span(text: str, start: int, end: int) -> tuple[int, int] | None:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    if start >= end:
        return None
    return start, end


def _split_long_span(text: str, start: int, end: int, max_chars: int) -> list[tuple[int, int]]:
    """Split [start, end) into verbatim trimmed spans each <= max_chars."""
    out: list[tuple[int, int]] = []
    cur_start = start
    while cur_start < end:
        trimmed = _trim_span(text, cur_start, end)
        if trimmed is None:
            break
        cur_start, cur_end = trimmed
        if cur_end - cur_start <= max_chars:
            out.append((cur_start, cur_end))
            break

        limit = cur_start + max_chars
        window = text[cur_start:limit]

        cut: int | None = None
        min_pos = max(1, int(max_chars * 0.2))
        for m in SENTENCE_END_RE.finditer(window):
            if m.start() >= min_pos:
                cut = cur_start + m.start()
        if cut is None:
            for m in SENTENCE_END_RE.finditer(window):
                if m.start() > 0:
                    cut = cur_start + m.start()
        if cut is None:
            nl = window.rfind("\n")
            if nl > 0:
                cut = cur_start + nl
        if cut is None:
            ws = max(window.rfind(" "), window.rfind("\t"))
            if ws > 0:
                cut = cur_start + ws
        if cut is None or cut <= cur_start:
            cut = limit

        piece = _trim_span(text, cur_start, cut)
        if piece is not None:
            out.append(piece)
        else:
            out.append((cur_start, limit))
            cut = limit
        cur_start = cut
    return out


def _table_row_breaks(page_text: str, anchors: list[str]) -> list[int]:
    """Locate line-start character offsets in page_text matching ingested table row anchors."""
    if not anchors or not page_text:
        return []
    # Map line start offsets and normalized whitespace lines
    line_starts: list[tuple[int, str]] = []
    pos = 0
    for ln in page_text.splitlines(keepends=True):
        stripped = " ".join(ln.split())
        if stripped:
            line_starts.append((pos, stripped))
        pos += len(ln)

    hits: list[int] = []
    search_from = 0
    for anch in anchors:
        # Try exact normalized prefix on each line starting from search_from
        words = anch.split()
        prefix = " ".join(words[:5])
        if len(prefix) < 4:
            continue
        p_low = prefix.lower()
        for idx in range(search_from, len(line_starts)):
            off, ltxt = line_starts[idx]
            if ltxt.lower().startswith(p_low):
                hits.append(off)
                search_from = idx + 1
                break
    return hits


def _initial_spans(
    page_text: str,
    mitc_mode: bool = False,
    table_anchors: list[str] | None = None,
) -> list[tuple[int, int]]:
    """Find trimmed spans split at paragraph breaks, headings, and optional MITC list/table rows."""
    n = len(page_text)
    breaks: set[int] = {0, n}
    for m in PARAGRAPH_BREAK_RE.finditer(page_text):
        breaks.add(m.start())
        breaks.add(m.end())

    marker_re = MITC_LINE_MARKER_RE if mitc_mode else HEADING_LINE_RE
    for m in marker_re.finditer(page_text):
        breaks.add(m.start())

    if mitc_mode and table_anchors:
        for off in _table_row_breaks(page_text, table_anchors):
            breaks.add(off)

    pts = sorted(breaks)
    spans: list[tuple[int, int]] = []
    for i in range(len(pts) - 1):
        tr = _trim_span(page_text, pts[i], pts[i + 1])
        if tr is not None:
            spans.append(tr)
    return spans


def _split_page_clauses_with_cont(
    page_text: str,
    min_chars: int = DEFAULT_MIN_CHARS,
    max_chars: int = DEFAULT_MAX_CHARS,
    mitc_mode: bool = False,
    table_anchors: list[str] | None = None,
) -> list[tuple[str, bool]]:
    """Split a single page into (clause_text, is_continuation_of_prev) tuples."""
    if not page_text or not page_text.strip():
        return []

    raw_spans = _initial_spans(page_text, mitc_mode=mitc_mode, table_anchors=table_anchors)
    if not raw_spans:
        return []

    sized: list[tuple[int, int, bool]] = []
    for s, e in raw_spans:
        if e - s > max_chars:
            parts = _split_long_span(page_text, s, e, max_chars)
            for idx, (ps, pe) in enumerate(parts):
                prev_cut_mid = False
                if idx > 0:
                    prev_s, prev_e = parts[idx - 1]
                    prev_txt = page_text[prev_s:prev_e].rstrip()
                    prev_cut_mid = (prev_e - prev_s) >= max(min_chars, int(max_chars * 0.5)) and not prev_txt.endswith((".", "!", "?", ";", ":"))
                sized.append((ps, pe, prev_cut_mid))
        else:
            sized.append((s, e, False))

    merged: list[tuple[int, int, bool]] = []
    for s, e, is_cont in sized:
        if (e - s) < min_chars and merged:
            ps, _, p_cont = merged[-1]
            tr = _trim_span(page_text, ps, e)
            if tr is not None and (tr[1] - tr[0]) <= max_chars:
                merged[-1] = (tr[0], tr[1], p_cont)
                continue
        merged.append((s, e, is_cont))

    final_spans: list[tuple[int, int, bool]] = []
    i = 0
    while i < len(merged):
        s, e, is_cont = merged[i]
        if (e - s) < min_chars and i + 1 < len(merged):
            ns, ne, n_cont = merged[i + 1]
            tr = _trim_span(page_text, s, ne)
            if tr is not None and (tr[1] - tr[0]) <= max_chars:
                merged[i + 1] = (tr[0], tr[1], is_cont)
                i += 1
                continue
        final_spans.append((s, e, is_cont))
        i += 1

    return [(page_text[s:e], is_cont) for s, e, is_cont in final_spans]


def split_page_clauses(
    page_text: str,
    min_chars: int = DEFAULT_MIN_CHARS,
    max_chars: int = DEFAULT_MAX_CHARS,
    mitc_mode: bool = False,
    table_anchors: list[str] | None = None,
) -> list[str]:
    """Split a single page's text into verbatim clauses (min_chars merge, <= max_chars cap)."""
    return [
        t
        for t, _ in _split_page_clauses_with_cont(
            page_text,
            min_chars=min_chars,
            max_chars=max_chars,
            mitc_mode=mitc_mode,
            table_anchors=table_anchors,
        )
    ]


def _ends_mid_clause(tail_text: str, next_head_text: str) -> bool:
    """Return True if a page break split an unfinished clause across two consecutive pages."""
    t = tail_text.rstrip()
    n = next_head_text.lstrip()
    if not t or not n:
        return False
    # If next page starts lowercase (e.g. 'herein shall constitute', 'substantial part', 'Borrower;'), definitely mid-clause
    if n[0].islower() or n[0] in (",", ";"):
        return True
    # Heading lines like 'ARTICLE IV' / '1. Loan' aren't mid-clause
    if t.endswith((".", "!", "?", ";", ":", ")", "]", '"', "'")):
        return False
    if len(t.splitlines()[-1].strip()) <= 60 and t.splitlines()[-1].strip().isupper():
        return False
    return True


def _strip_leading_sentence_or_clause(text: str, max_take: int) -> tuple[str, str]:
    """Take the continuation fragment from start of next page up to first paragraph/sentence end."""
    limit = min(len(text), max(1, max_take))
    # Prefer double newline or heading boundary first, then sentence end
    para_m = PARAGRAPH_BREAK_RE.search(text[:limit])
    if para_m and para_m.start() > 0:
        return text[: para_m.start()].rstrip(), text[para_m.end() :].lstrip()
    sent_m = SENTENCE_END_RE.search(text[:limit])
    if sent_m and sent_m.end() > 0:
        return text[: sent_m.start()].rstrip(), text[sent_m.end() :].lstrip()
    # Fallback: take entire first chunk if fits
    if len(text) <= max_take:
        return text.rstrip(), ""
    ws = text[:limit].rfind(" ")
    if ws > 0:
        return text[:ws].rstrip(), text[ws:].lstrip()
    return text[:limit], text[limit:]


def _sort_page_keys(keys: Any) -> list[int | str]:
    return sorted(keys, key=lambda k: (0, int(k)) if isinstance(k, int) or str(k).isdigit() else (1, str(k)))


def split_pages(
    doc_id: str,
    doc_pages: dict[int | str, str],
    min_chars: int | None = None,
    max_chars: int | None = None,
    mitc_mode: bool | None = None,
    table_rows_by_page: dict[int, list[str]] | None = None,
    stitch_page_breaks: bool = True,
) -> list[dict[str, Any]]:
    """Split all pages of a document into {doc_id, page, clause_id, text} records."""
    if mitc_mode is None:
        mitc_mode = is_mitc_doc(doc_id)
    eff_min = min_chars if min_chars is not None else (MITC_MIN_CHARS if mitc_mode else DEFAULT_MIN_CHARS)
    eff_max = max_chars if max_chars is not None else (MITC_MAX_CHARS if mitc_mode else DEFAULT_MAX_CHARS)

    ordered_keys = _sort_page_keys(doc_pages.keys())
    per_page_texts: list[tuple[int | str, list[tuple[str, bool]]]] = []

    for pk in ordered_keys:
        anchors = table_rows_by_page.get(int(pk)) if (table_rows_by_page and (isinstance(pk, int) or str(pk).isdigit())) else None
        chunks = _split_page_clauses_with_cont(
            doc_pages[pk],
            min_chars=eff_min,
            max_chars=eff_max,
            mitc_mode=mitc_mode,
            table_anchors=anchors,
        )
        per_page_texts.append((pk, chunks))

    # Handle mid-clause breaks across page boundaries (especially SEC agreements)
    if stitch_page_breaks and len(per_page_texts) >= 2:
        for idx in range(len(per_page_texts) - 1):
            pk_cur, chunks_cur = per_page_texts[idx]
            pk_nxt, chunks_nxt = per_page_texts[idx + 1]
            if not chunks_cur or not chunks_nxt:
                continue
            cur_text, cur_cont = chunks_cur[-1]
            nxt_text, nxt_cont = chunks_nxt[0]
            if _ends_mid_clause(cur_text, nxt_text):
                budget = eff_max - len(cur_text) - 1
                if budget >= 20:
                    head_part, remainder = _strip_leading_sentence_or_clause(nxt_text, budget)
                    if head_part:
                        chunks_cur[-1] = (cur_text.rstrip() + " " + head_part, cur_cont)
                        if remainder.strip():
                            chunks_nxt[0] = (remainder.strip(), nxt_cont)
                        else:
                            chunks_nxt.pop(0)

    clauses: list[dict[str, Any]] = []
    cid_num = 0
    cur_head_cid = ""
    for pk, chunks in per_page_texts:
        for text, is_cont in chunks:
            if not text.strip():
                continue
            cid_num += 1
            cid = f"C{cid_num:04d}"
            cont_of = cur_head_cid if (is_cont and cur_head_cid) else ""
            if not cont_of:
                cur_head_cid = cid
            clauses.append(
                {
                    "doc_id": doc_id,
                    "page": int(pk) if (isinstance(pk, int) or str(pk).isdigit()) else str(pk),
                    "clause_id": cid,
                    "text": text,
                    "continuation_of": cont_of,
                }
            )
    return clauses


def split_document(
    doc_id: str,
    min_chars: int | None = None,
    max_chars: int | None = None,
) -> list[dict[str, Any]]:
    """Load pages (and MITC table rows if ingested JSON exists) and split cleanly."""
    mitc = is_mitc_doc(doc_id)
    pages = load_doc_pages(doc_id)
    table_rows = load_mitc_table_rows_by_page(doc_id) if mitc else None
    return split_pages(
        doc_id,
        pages,
        min_chars=min_chars,
        max_chars=max_chars,
        mitc_mode=mitc,
        table_rows_by_page=table_rows,
        stitch_page_breaks=True,
    )
