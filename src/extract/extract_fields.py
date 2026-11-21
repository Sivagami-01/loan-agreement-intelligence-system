"""src/extract/extract_fields.py

Stage 3a: Key-information extraction with verbatim quote grounding,
deterministic numeric verification, and optional cross-model verification.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

import yaml
from rapidfuzz import fuzz

from src.llm.gemini_client import GeminiClient, load_model_config
from src.qa.check_numbers import check_numbers, extract_items
from src.qa.doc_loader import load_document
from src.qa.retrieve import retrieve
from src.qa.verifier import verify_answer
from src.qa.verify_quotes import normalize, verify_evidence

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EXTRACT_CONFIG = ROOT / "config" / "extract.yaml"

NOT_FOUND_VALUE = "Not found in this document"
_NOT_FOUND_MARKERS = {
    "",
    "not found",
    "not found in this document",
    "not_found",
    "not_present",
    "not present",
    "n/a",
    "none found",
}

_DEFER_DOC_RE = re.compile(
    r"\b(?:as\s+defined\s+in|defined\s+in|as\s+set\s+forth\s+in|set\s+forth\s+in|"
    r"in\s+accordance\s+with|governed\s+by|specified\s+in|provided\s+in|referenced\s+in|listed\s+in)\s+"
    r"(?:the\s+|a\s+)?(?:separate\s+|attached\s+)?"
    r"(promissory\s+note|revolving\s+note|note|schedule(?:\s+[a-z0-9.]+|\s+of\s+charges)?|fee\s+letter|other\s+loan\s+documents?)\b",
    re.IGNORECASE,
)
_VAGUE_TERM_OF_NOTE_RE = re.compile(
    r"^(?:the\s+)?term\s+of\s+(?:the\s+)?(?:promissory\s+|revolving\s+)?note\.?$",
    re.IGNORECASE,
)


def load_extract_config(config_path: Path | None = None) -> dict[str, Any]:
    """Loads extraction settings and field schema from config/extract.yaml."""
    path = config_path or DEFAULT_EXTRACT_CONFIG
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return data


def _format_pages_text(doc_pages: dict[int, str]) -> str:
    """Formats page mapping into [[PAGE n]] delimited text."""
    parts: list[str] = []
    for p_num in sorted(doc_pages):
        parts.append(f"[[PAGE {p_num}]]\n{doc_pages[p_num]}")
    return "\n\n".join(parts)


def _strip_json_fences(raw_text: str) -> str:
    text = (raw_text or "").strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)
    if fence_match:
        return fence_match.group(1).strip()
    return text


def _parse_json_payload(raw_text: str) -> Any | None:
    """Parses JSON from LLM output, recovering outermost {} or [] if needed."""
    cleaned = _strip_json_fences(raw_text)
    if not cleaned:
        return None
    # Repair malformed multi-integer page values like `"page": 44, 45` emitted by Flash-Lite
    repaired = re.sub(r'("page"\s*:\s*\d+)(?:\s*,\s*\d+)+', r"\1", cleaned)
    for candidate_text in (cleaned, repaired):
        try:
            return json.loads(candidate_text)
        except json.JSONDecodeError:
            pass

    # Attempt recovery from outermost braces/brackets
    for source_text in (cleaned, repaired):
        obj_start = source_text.find("{")
        arr_start = source_text.find("[")
        candidates: list[tuple[int, str, str]] = []
        if obj_start != -1:
            candidates.append((obj_start, "{", "}"))
        if arr_start != -1:
            candidates.append((arr_start, "[", "]"))
        candidates.sort(key=lambda x: x[0])

        for start_idx, _, end_ch in candidates:
            end_idx = source_text.rfind(end_ch)
            if end_idx > start_idx:
                snippet = source_text[start_idx : end_idx + 1]
                try:
                    return json.loads(snippet)
                except json.JSONDecodeError:
                    continue
    return None


def _normalize_raw_items(payload: Any, field_names: list[str]) -> dict[str, dict[str, Any]] | None:
    """Normalizes parsed JSON into a dict keyed by field name, or None if invalid."""
    if payload is None:
        return None

    field_set = set(field_names)
    items: list[dict[str, Any]] = []

    if isinstance(payload, dict):
        if "fields" in payload and isinstance(payload["fields"], list):
            items = [x for x in payload["fields"] if isinstance(x, dict)]
        elif "field" in payload and len(payload) <= 6:
            items = [payload]
        else:
            # Handle {field_name: {...}} object map shape
            mapped: dict[str, dict[str, Any]] = {}
            for k, v in payload.items():
                if k in field_set and isinstance(v, dict):
                    entry = dict(v)
                    entry.setdefault("field", k)
                    mapped[k] = entry
            return mapped if mapped else None
    elif isinstance(payload, list):
        items = [x for x in payload if isinstance(x, dict)]
    else:
        return None

    if not items:
        return None

    mapped_out: dict[str, dict[str, Any]] = {}
    for item in items:
        fname = str(item.get("field") or item.get("field_name") or "").strip()
        if fname in field_set and fname not in mapped_out:
            mapped_out[fname] = item
    return mapped_out if mapped_out else None


def _build_whole_doc_prompt(doc_text: str, fields_cfg: list[dict[str, Any]], numeric_fields: set[str]) -> str:
    """Builds a single JSON extraction prompt for all configured fields."""
    field_lines: list[str] = []
    for f in fields_cfg:
        name = f["name"]
        desc = f.get("description", "")
        num_note = " [NUMERIC_FIELD]" if name in numeric_fields else ""
        field_lines.append(f"- {name}{num_note}: {desc}")

    fields_block = "\n".join(field_lines)
    return (
        "You are a legal/financial document key-information extractor.\n"
        "Extract ALL 16 fields below ONLY from the DOCUMENT provided. Output strictly valid JSON with NO extra text.\n\n"
        "STRICT RULES:\n"
        "1. Output JSON schema:\n"
        '   {"fields": [{"field": "<field_name>", "found": true|false, "deferred": false, "defers_to": "", "value": "<string>", '
        '"evidence": [{"quote": "<exact verbatim substring>", "page": <integer page>}]}]}\n'
        "2. Always include all 16 field entries in order.\n"
        "3. Absence vs Deferral (NEVER guess or stretch unrelated clauses):\n"
        '   - If a field is NOT stated in this agreement, set "found": false, "deferred": false, "defers_to": "", "value": "Not found in this document", "evidence": [].\n'
        "   - Use found=false when the text does NOT actually state that field: e.g., do NOT answer `late_payment_or_default_interest` with general payment-default Events of Default clauses unless a penal/default interest rate or late fee is stated; do NOT answer `prepayment_terms` with ordinary revolving borrow/repay clauses unless prepayment rights/penalties are stated; do NOT answer `maturity_termination_date` when a 'date' is only a vague phrase like 'the term of the Note' with no actual date or numeric tenure; for `agents`, ignore agents mentioned only inside external/prior agreements.\n"
        '   - ONLY if a term is defined solely by reference to another unattached document ("as defined in the Note", "as set forth in the Schedule", "in accordance with the Fee Letter") with no substantive value in this text, set "found": true, "deferred": true, "defers_to": "<document name e.g. Note>", "value": "", "evidence": [{"quote": "<exact deferral clause>", "page": N}]. (If substantive terms ARE stated alongside a Note reference, e.g. 365/360 basis or Event of Loss prepayment, extract them with "deferred": false.)\n'
        "4. `evidence` quotes MUST copy ONE contiguous verbatim passage of 1-3 sentences directly from the document:\n"
        '   - NEVER use ellipses ("..."), NEVER skip words or paraphrase inside a quote, and preserve all numbers, punctuation, and non-English glyphs identically.\n'
        "   - For long numbered/bulleted lists (such as Events of Default or Collateral), copy only 1-2 contiguous clauses (under 350 characters) per quote entry rather than bridging distant clauses; use separate `evidence` items if citing a second clause.\n"
        "5. Set `page` to the integer N from the nearest preceding [[PAGE N]] marker.\n"
        "6. `value` must be a concise, clean normalized summary (1 sentence max, NOT raw legalese or a bare heading):\n"
        "   - Strip spelled-out number words and zero `.00` cents when an amount appears in digits (write `$1,000,000` instead of `One Million and 00/100 ($1,000,000.00) Dollars`, and `$500` instead of `$500.00`).\n"
        "   - Strip incorporation boilerplate from entity names unless needed. For `lenders`, list named banks from both the opening paragraph and Schedule I / signature blocks if present.\n"
        "   - NEVER return only a section heading or pointer (`Section 7.01 Events of Default`, `at the rate therein provided`). Summarize the operative triggers/grace days/thresholds, repayment schedules, benchmarks/margins/day-count bases, and collateral.\n"
        "   - For [NUMERIC_FIELD] items, preserve exact numeric digits, percentages, currencies, and dates from the source quote (do not invent unquoted count digits like '2 fees').\n\n"
        f"FIELDS TO EXTRACT:\n{fields_block}\n\n"
        f"DOCUMENT:\n{doc_text}\n"
    )


def _build_field_retrieval_prompt(
    field_cfg: dict[str, Any],
    chunks: list[dict[str, Any]],
    is_numeric: bool,
) -> str:
    """Builds a single-field extraction prompt from BM25-retrieved chunks."""
    snippets: list[str] = []
    for ch in chunks:
        snippets.append(f"[[PAGE {ch['page']}]]\n{ch['text']}")
    context = "\n\n---\n\n".join(snippets) if snippets else "(No relevant excerpts retrieved)"
    num_rule = (
        "- Preserve exact digits, percentages, currencies, and dates from the source quote (strip trailing `.00` zero cents; do not invent unquoted counts).\n"
        if is_numeric
        else ""
    )
    return (
        "You are a legal/financial document key-information extractor.\n"
        "Extract ONLY the requested field from the EXCERPTS below. Output strictly valid JSON with NO extra text.\n\n"
        "JSON schema:\n"
        f'{{"field": "{field_cfg["name"]}", "found": true|false, "deferred": false, "defers_to": "", "value": "<string>", '
        '"evidence": [{"quote": "<exact verbatim substring>", "page": <integer page>}]}\n\n'
        "RULES:\n"
        "- If absent from all excerpts or only an unrelated clause (e.g., general default for late-payment rate, ordinary borrow/repay for prepayment, vague 'term of the Note' for date), set \"found\": false, \"deferred\": false, \"defers_to\": \"\", \"value\": \"Not found in this document\", \"evidence\": [].\n"
        "- If defined solely by reference to another unattached document (\"as defined in the Note\", \"as set forth in the Schedule\", \"in accordance with the Fee Letter\"), set \"found\": true, \"deferred\": true, \"defers_to\": \"<doc>\", \"value\": \"\", with the verbatim deferral quote.\n"
        "- Copy ONE contiguous verbatim passage of 1-3 sentences per `quote` directly from the excerpts. NEVER use ellipses (`...`) or skip words.\n"
        "- Provide a concise, substantive summary in `value` (never return only a section heading or generic pointer); for `agents`, ignore prior external agreements.\n"
        f"{num_rule}"
        f"FIELD: {field_cfg['name']} — {field_cfg.get('description', '')}\n\n"
        f"EXCERPTS:\n{context}\n"
    )


def _call_llm_with_json_retry(
    prompt: str,
    model_role: str,
    temperature: float,
    field_names: list[str],
    retry_limit: int,
    max_calls_left: int,
    client: GeminiClient | None,
    llm_fn: Callable[[str], tuple[str, str]] | None,
) -> tuple[dict[str, dict[str, Any]] | None, str | None, int]:
    """Calls the configured LLM and retries once on invalid JSON if budget allows."""
    calls = 0
    model_used: str | None = None
    cur_prompt = prompt

    attempts = 1 + max(0, retry_limit)
    for attempt in range(attempts):
        if calls >= max_calls_left:
            break
        calls += 1
        if llm_fn is not None:
            raw_text, used = llm_fn(cur_prompt)
            model_used = used
        else:
            assert client is not None
            raw_text = client.generate(cur_prompt, model_alias=model_role, temperature=temperature)
            model_used = client.last_model_used

        payload = _parse_json_payload(raw_text)
        normalized = _normalize_raw_items(payload, field_names)
        if normalized is not None:
            return normalized, model_used, calls

        if attempt + 1 < attempts and calls < max_calls_left:
            cur_prompt = (
                "Your previous output was NOT valid JSON matching the required schema.\n"
                "Return ONLY valid JSON with no markdown or commentary.\n\n"
                + prompt
            )

    return None, model_used, calls


def _clean_raw_evidence(raw_ev: Any) -> list[dict[str, Any]]:
    """Normalizes LLM evidence list into [{quote, page}] dictionaries."""
    if not isinstance(raw_ev, list):
        return []
    cleaned: list[dict[str, Any]] = []
    for item in raw_ev:
        if isinstance(item, dict):
            q = str(item.get("quote", "")).strip()
            p = item.get("page")
            if q:
                cleaned.append({"quote": q, "page": p})
        elif isinstance(item, str) and item.strip():
            cleaned.append({"quote": item.strip(), "page": None})
    return cleaned


def _build_page_norm_index(raw_page: str) -> tuple[str, list[int], list[int]]:
    """Normalizes raw_page following verify_quotes rules while mapping chars to raw offsets."""
    norm_chars: list[str] = []
    raw_starts: list[int] = []
    raw_ends: list[int] = []
    prev_end = 0

    for m in re.finditer(r"\S+", raw_page):
        tok_norm = normalize(m.group(0))
        if not tok_norm:
            prev_end = m.end()
            continue
        if norm_chars and not (norm_chars[-1] in "([{" or tok_norm[0] in ",.);:!?]"):
            norm_chars.append(" ")
            raw_starts.append(prev_end)
            raw_ends.append(m.start())
        for ch in tok_norm:
            norm_chars.append(ch)
            raw_starts.append(m.start())
            raw_ends.append(m.end())
        prev_end = m.end()

    return "".join(norm_chars), raw_starts, raw_ends


def _align_segment(seg_norm: str, haystack: str, min_sim: float) -> tuple[int, int, float] | None:
    """Finds best match for seg_norm inside haystack with similarity >= min_sim."""
    if not seg_norm or not haystack:
        return None
    exact_idx = haystack.find(seg_norm)
    if exact_idx != -1:
        return exact_idx, exact_idx + len(seg_norm), 100.0
    if len(seg_norm) < 10:
        return None
    al = fuzz.partial_ratio_alignment(seg_norm, haystack)
    if al is None or al.score < min_sim:
        return None
    d_s, d_e = al.dest_start, al.dest_end
    while d_s < d_e and haystack[d_s] == " ":
        d_s += 1
    while d_e > d_s and haystack[d_e - 1] == " ":
        d_e -= 1
    if d_s >= d_e:
        return None
    full_sim = fuzz.ratio(seg_norm, haystack[d_s:d_e])
    if full_sim < min_sim:
        return None
    return d_s, d_e, float(full_sim)


def _numbers_preserved(
    orig_quote: str,
    repaired_quote: str,
    page_num: int,
    seg_pairs: list[tuple[str, str]] | None = None,
) -> bool:
    """Ensures repaired quote never alters numbers from the original quote."""
    if not check_numbers(orig_quote, evidence=[{"quote": repaired_quote, "page": page_num}])["all_found"]:
        return False
    if not seg_pairs or len(seg_pairs) <= 1:
        return bool(
            check_numbers(repaired_quote, evidence=[{"quote": orig_quote, "page": page_num}])["all_found"]
        )
    for orig_seg, rep_seg in seg_pairs:
        if not check_numbers(orig_seg, evidence=[{"quote": rep_seg, "page": page_num}])["all_found"]:
            return False
        if not check_numbers(rep_seg, evidence=[{"quote": orig_seg, "page": page_num}])["all_found"]:
            return False
    return True


def _repair_quote_on_page(
    raw_quote: str,
    page_num: int,
    raw_page: str,
    page_idx: tuple[str, list[int], list[int]],
    min_sim: float,
    max_chars: int,
) -> tuple[str, float] | None:
    """Attempts to repair a single failed quote against one source page."""
    norm_page, raw_starts, raw_ends = page_idx
    if not norm_page:
        return None

    raw_segs = [s.strip() for s in re.split(r"\.{3,}|…", raw_quote) if s.strip()]
    seg_items = [(s, normalize(s)) for s in raw_segs if normalize(s)]
    if not seg_items:
        return None

    if len(seg_items) == 1:
        raw_seg, seg_norm = seg_items[0]
        hit = _align_segment(seg_norm, norm_page, min_sim)
        if hit is None:
            return None
        d_s, d_e, sim = hit
        while d_s < d_e and norm_page[d_s] == " ":
            d_s += 1
        while d_e > d_s and norm_page[d_e - 1] == " ":
            d_e -= 1
        if d_s >= d_e:
            return None
        cand = raw_page[raw_starts[d_s] : raw_ends[d_e - 1]].strip()
        if len(cand) > max_chars:
            trimmed = cand[:max_chars].rsplit(None, 1)[0].strip() if " " in cand[:max_chars] else cand[:max_chars]
            cand = trimmed
            if not cand or fuzz.partial_ratio(seg_norm, normalize(cand)) < min_sim:
                return None
        if cand not in raw_page:
            return None
        if not _numbers_preserved(raw_quote, cand, page_num):
            return None
        return cand, sim

    # Multi-segment ("...") bridge inside <= max_chars contiguous source span
    a_idx = max(range(len(seg_items)), key=lambda i: len(seg_items[i][1]))
    anchor_norm = seg_items[a_idx][1]
    if len(anchor_norm) < 8:
        return None

    anchor_hits: list[tuple[int, int]] = []
    pos = 0
    while len(anchor_hits) < 10:
        found_at = norm_page.find(anchor_norm, pos)
        if found_at == -1:
            break
        anchor_hits.append((found_at, found_at + len(anchor_norm)))
        pos = found_at + max(1, len(anchor_norm))

    if not anchor_hits:
        al = _align_segment(anchor_norm, norm_page, min_sim)
        if al is None:
            return None
        anchor_hits.append((al[0], al[1]))

    best: tuple[str, float] | None = None
    for a_s, a_e in anchor_hits:
        w_s = max(0, a_s - max_chars)
        w_e = min(len(norm_page), a_e + max_chars)
        win = norm_page[w_s:w_e]

        cur = 0
        global_spans: list[tuple[int, int]] = []
        scores: list[float] = []
        ok = True
        for _, seg_norm in seg_items:
            sub_hit = _align_segment(seg_norm, win[cur:], min_sim)
            if sub_hit is None:
                ok = False
                break
            h_s, h_e, sc = sub_hit
            global_spans.append((w_s + cur + h_s, w_s + cur + h_e))
            scores.append(sc)
            cur += h_e

        if not ok or not global_spans:
            continue

        g_first = global_spans[0][0]
        g_last = global_spans[-1][1]
        while g_first < g_last and norm_page[g_first] == " ":
            g_first += 1
        while g_last > g_first and norm_page[g_last - 1] == " ":
            g_last -= 1
        if g_first >= g_last:
            continue

        cand = raw_page[raw_starts[g_first] : raw_ends[g_last - 1]].strip()
        if not cand or len(cand) > max_chars or cand not in raw_page:
            continue

        seg_pairs: list[tuple[str, str]] = []
        for (raw_s_txt, _), (gs, ge) in zip(seg_items, global_spans):
            while gs < ge and norm_page[gs] == " ":
                gs += 1
            while ge > gs and norm_page[ge - 1] == " ":
                ge -= 1
            if gs >= ge:
                ok = False
                break
            rep_seg = raw_page[raw_starts[gs] : raw_ends[ge - 1]].strip()
            seg_pairs.append((raw_s_txt, rep_seg))

        if not ok or not _numbers_preserved(raw_quote, cand, page_num, seg_pairs=seg_pairs):
            continue

        avg_sc = sum(scores) / len(scores)
        if best is None or avg_sc > best[1]:
            best = (cand, avg_sc)

    if best is not None:
        return best

    # Fallback if ellipsis bridged > max_chars: accept longest valid contiguous sub-segment ONLY if ALL original numbers still match
    for raw_seg, seg_norm in sorted(seg_items, key=lambda pair: len(pair[1]), reverse=True):
        if len(seg_norm) < 15:
            continue
        hit = _align_segment(seg_norm, norm_page, min_sim)
        if hit is None:
            continue
        d_s, d_e, sim = hit
        cand = raw_page[raw_starts[d_s] : raw_ends[d_e - 1]].strip()
        if len(cand) > max_chars:
            cand = cand[:max_chars].rsplit(None, 1)[0].strip() if " " in cand[:max_chars] else cand[:max_chars]
        if cand and len(cand) <= max_chars and cand in raw_page and _numbers_preserved(raw_quote, cand, page_num):
            return cand, sim

    return None


def _repair_quote_across_pages(
    item: dict[str, Any],
    doc_pages: dict[int, str],
    page_norm_cache: dict[int, tuple[str, list[int], list[int]]],
    min_sim: float = 95.0,
    max_chars: int = 400,
) -> dict[str, Any] | None:
    """Searches cited page and its neighbours for a matching exact source span."""
    raw_quote = str(item.get("quote", "")).strip()
    if not raw_quote:
        return None

    target_page_raw = item.get("page")
    cited_page: int | None = None
    if target_page_raw is not None:
        try:
            cited_page = int(target_page_raw)
        except (TypeError, ValueError):
            cited_page = None

    if cited_page is not None and cited_page in doc_pages:
        search_pages = [p for p in (cited_page, cited_page - 1, cited_page + 1) if p in doc_pages]
    elif cited_page is not None and doc_pages:
        search_pages = sorted(doc_pages, key=lambda p: abs(p - cited_page))[:3]
    else:
        search_pages = sorted(doc_pages)

    for p_num in search_pages:
        if p_num not in page_norm_cache:
            page_norm_cache[p_num] = _build_page_norm_index(doc_pages[p_num])
        res = _repair_quote_on_page(
            raw_quote=raw_quote,
            page_num=p_num,
            raw_page=doc_pages[p_num],
            page_idx=page_norm_cache[p_num],
            min_sim=min_sim,
            max_chars=max_chars,
        )
        if res is not None:
            repaired_quote, _ = res
            return {
                "quote": repaired_quote,
                "page": p_num,
                "verified": True,
                "quote_repaired": True,
                "flags": ["quote_repaired"],
            }
    return None


def _infer_deferral_target(raw_value: str, evidence: list[dict[str, Any]]) -> str:
    """Detects when a field value defers solely to another document and names that document."""
    val = (raw_value or "").strip()
    if not val:
        for ev in evidence:
            m = _DEFER_DOC_RE.search(str(ev.get("quote", "")))
            if m:
                return m.group(1).strip()
        return ""
    stripped_ref_nums = re.sub(r"\b(?:schedule|section|clause)\s+[a-z0-9.]+\b", "", val, flags=re.IGNORECASE)
    if extract_items(stripped_ref_nums):
        return ""
    m = _DEFER_DOC_RE.search(val)
    if m and len(val.split()) <= 16:
        return m.group(1).strip()
    return ""


def _verify_single_field(
    field_name: str,
    field_desc: str,
    raw_item: dict[str, Any] | None,
    doc_pages: dict[int, str],
    numeric_fields: set[str],
    model_used: str | None,
    verify_numeric: bool,
    client: GeminiClient | None,
    verifier_llm_fn: Callable[[str], tuple[str, str]] | None,
    verifier_calls_remaining: int,
    repair_enabled: bool = True,
    repair_min_sim: float = 95.0,
    repair_max_chars: int = 400,
    page_norm_cache: dict[int, tuple[str, list[int], list[int]]] | None = None,
) -> tuple[dict[str, Any], int, int, int, int]:
    """Applies quote verification/repair, deferral, number checking, and optional LLM verification.

    Returns (field_record, raw_q_count, verified_q_count, repaired_q_count, verifier_calls_used).
    """
    if raw_item is None:
        return (
            {
                "field": field_name,
                "found": False,
                "value": NOT_FOUND_VALUE,
                "evidence": [],
                "status": "not_found",
                "final_check": "PASS",
                "quote_repaired": False,
                "defers_to": "",
                "number_check": None,
                "verifier_verdict": None,
                "verifier_independent": None,
                "model_used": model_used,
                "flags": ["missing_from_llm_output"],
            },
            0,
            0,
            0,
            0,
        )

    raw_found = bool(raw_item.get("found", False))
    raw_deferred = bool(raw_item.get("deferred", False))
    raw_defers_to = str(raw_item.get("defers_to", "")).strip()
    raw_value = str(raw_item.get("value", "")).strip()
    cleaned_ev = _clean_raw_evidence(raw_item.get("evidence", []))
    raw_q_count = len(cleaned_ev)

    # Reject vague non-date pointers like "Term of the Note" on date fields unless explicitly deferred
    if (
        field_name == "maturity_termination_date"
        and not raw_deferred
        and _VAGUE_TERM_OF_NOTE_RE.match(raw_value)
    ):
        return (
            {
                "field": field_name,
                "found": False,
                "value": NOT_FOUND_VALUE,
                "evidence": [],
                "status": "not_found",
                "final_check": "PASS",
                "quote_repaired": False,
                "defers_to": "",
                "number_check": None,
                "verifier_verdict": None,
                "verifier_independent": None,
                "model_used": model_used,
                "flags": ["vague_date_rejected_as_not_found"],
            },
            0,
            0,
            0,
            0,
        )

    # Treat explicit not-found responses cleanly as not_found
    if not raw_found or (not raw_deferred and raw_value.lower() in _NOT_FOUND_MARKERS):
        return (
            {
                "field": field_name,
                "found": False,
                "value": NOT_FOUND_VALUE,
                "evidence": [],
                "status": "not_found",
                "final_check": "PASS",
                "quote_repaired": False,
                "defers_to": "",
                "number_check": None,
                "verifier_verdict": None,
                "verifier_independent": None,
                "model_used": model_used,
                "flags": [],
            },
            0,
            0,
            0,
            0,
        )

    # Field claims found=True (or deferred=True): require at least one verified/repaired quote
    if raw_q_count == 0:
        return (
            {
                "field": field_name,
                "found": False,
                "value": "",
                "evidence": [],
                "status": "unverified",
                "final_check": "FAIL",
                "quote_repaired": False,
                "defers_to": "",
                "number_check": None,
                "verifier_verdict": None,
                "verifier_independent": None,
                "model_used": model_used,
                "flags": ["no_evidence_provided"],
            },
            0,
            0,
            0,
            0,
        )

    norm_cache = page_norm_cache if page_norm_cache is not None else {}
    surviving_ev: list[dict[str, Any]] = []
    flags: list[str] = []
    repaired_q_count = 0

    for ev_item in cleaned_ev:
        vev, qflags = verify_evidence(doc_pages, [ev_item])
        for fl in qflags:
            if fl not in flags:
                flags.append(fl)
        if vev:
            surviving_ev.append({
                "quote": vev[0]["quote"],
                "page": int(vev[0]["page"]),
                "quote_repaired": False,
            })
            continue

        if repair_enabled:
            repaired_item = _repair_quote_across_pages(
                item=ev_item,
                doc_pages=doc_pages,
                page_norm_cache=norm_cache,
                min_sim=repair_min_sim,
                max_chars=repair_max_chars,
            )
            if repaired_item is not None:
                # Re-verify repaired quote with strict verbatim checker
                r_vev, _ = verify_evidence(doc_pages, [repaired_item])
                if r_vev:
                    surviving_ev.append({
                        "quote": r_vev[0]["quote"],
                        "page": int(r_vev[0]["page"]),
                        "quote_repaired": True,
                    })
                    repaired_q_count += 1
                    if "quote_repaired" not in flags:
                        flags.append("quote_repaired")

    verified_q_count = len(surviving_ev)
    field_quote_repaired = repaired_q_count > 0
    if verified_q_count < raw_q_count:
        flags.append(f"dropped_quotes:{raw_q_count - verified_q_count}/{raw_q_count}")

    if verified_q_count == 0:
        return (
            {
                "field": field_name,
                "found": False,
                "value": "",
                "evidence": [],
                "status": "unverified",
                "final_check": "FAIL",
                "quote_repaired": False,
                "defers_to": "",
                "number_check": None,
                "verifier_verdict": None,
                "verifier_independent": None,
                "model_used": model_used,
                "flags": flags + ["all_quotes_failed_verification"],
            },
            raw_q_count,
            0,
            0,
            0,
        )

    # Check if field is solely deferred to another document
    inferred_target = _infer_deferral_target(raw_value, []) if raw_value else ""
    if raw_deferred or inferred_target:
        defers_target = (
            raw_defers_to
            or inferred_target
            or _infer_deferral_target("", surviving_ev)
            or "other document"
        )
        if "deferred_to_other_document" not in flags:
            flags.append("deferred_to_other_document")
        return (
            {
                "field": field_name,
                "found": False,
                "value": "",
                "evidence": surviving_ev,
                "status": "deferred_to_other_document",
                "final_check": "PASS",
                "quote_repaired": field_quote_repaired,
                "defers_to": defers_target,
                "number_check": None,
                "verifier_verdict": None,
                "verifier_independent": None,
                "model_used": model_used,
                "flags": flags,
            },
            raw_q_count,
            verified_q_count,
            repaired_q_count,
            0,
        )

    clean_evidence = surviving_ev
    status = "verified"
    final_check = "PASS"
    num_res: dict[str, Any] | None = None
    verifier_verdict: str | None = None
    verifier_independent: bool | None = None
    verifier_calls_used = 0

    is_numeric = field_name in numeric_fields
    if is_numeric:
        num_res = check_numbers(answer=raw_value, evidence=clean_evidence, doc_pages=doc_pages)
        if not num_res["all_found"]:
            status = "needs_review"
            final_check = "NEEDS_REVIEW"
            flags.append(f"number_mismatch:{num_res['missing']}")

        if verify_numeric and verifier_calls_remaining > 0:
            verifier_calls_used = 1
            v_res = verify_answer(
                question=f"Verify extracted field '{field_name}' ({field_desc})",
                answer=raw_value,
                evidence=clean_evidence,
                doc_pages=doc_pages,
                answer_model_used=model_used,
                client=client,
                llm_fn=verifier_llm_fn,
            )
            verifier_verdict = v_res.get("verifier_verdict")
            verifier_independent = v_res.get("verifier_independent")
            v_final = str(v_res.get("final_check", "NEEDS_REVIEW"))
            num_res = v_res.get("number_check", num_res)

            if v_final in {"FAIL", "NEEDS_REVIEW"}:
                status = "needs_review"
                final_check = v_final
                flags.append(f"verifier:{verifier_verdict}")
            elif not num_res["all_found"]:
                status = "needs_review"
                final_check = "NEEDS_REVIEW"

    return (
        {
            "field": field_name,
            "found": True,
            "value": raw_value,
            "evidence": clean_evidence,
            "status": status,
            "final_check": final_check,
            "quote_repaired": field_quote_repaired,
            "defers_to": "",
            "number_check": num_res,
            "verifier_verdict": verifier_verdict,
            "verifier_independent": verifier_independent,
            "model_used": model_used,
            "flags": flags,
        },
        raw_q_count,
        verified_q_count,
        repaired_q_count,
        verifier_calls_used,
    )


def extract_key_info(
    doc_id: str,
    doc_pages: dict[int, str] | None = None,
    client: GeminiClient | None = None,
    config: dict[str, Any] | None = None,
    verify_numeric: bool = False,
    max_verifier_calls: int = 8,
    llm_fn: Callable[[str], tuple[str, str]] | None = None,
    verifier_llm_fn: Callable[[str], tuple[str, str]] | None = None,
) -> dict[str, Any]:
    """Extracts the 16 key fields from doc_id with verbatim quote & number checks."""
    cfg = config if config is not None else load_extract_config()
    model_role = str(cfg.get("model_role", "main"))
    temperature = float(cfg.get("temperature", 0.0))
    max_doc_chars = int(cfg.get("max_doc_chars_for_whole_doc", 400000))
    max_calls_per_doc = int(cfg.get("max_calls_per_doc", 16))
    retry_limit = int(cfg.get("retry_on_invalid_json", 1))
    top_k = int(cfg.get("retrieval_top_k_per_field", 6))
    repair_enabled = bool(cfg.get("quote_repair_enabled", True))
    repair_min_sim = float(cfg.get("quote_repair_min_similarity", 95.0))
    repair_max_chars = int(cfg.get("quote_repair_max_chars", 400))
    numeric_fields = set(cfg.get("numeric_fields", []))
    fields_cfg: list[dict[str, Any]] = list(cfg.get("fields", []))
    field_names = [f["name"] for f in fields_cfg]

    if doc_pages is None:
        full_text, loaded_pages = load_document(doc_id)
    else:
        loaded_pages = {int(k): str(v) for k, v in doc_pages.items()}
        full_text = _format_pages_text(loaded_pages)

    if client is None and llm_fn is None:
        client = GeminiClient()

    doc_chars = len(full_text)
    retrieval_used = doc_chars > max_doc_chars
    calls_made = 0
    raw_by_field: dict[str, dict[str, Any]] = {}
    field_models: dict[str, str | None] = {}
    parse_failed_doc = False

    if not retrieval_used:
        prompt = _build_whole_doc_prompt(full_text, fields_cfg, numeric_fields)
        parsed_map, used_model, used_calls = _call_llm_with_json_retry(
            prompt=prompt,
            model_role=model_role,
            temperature=temperature,
            field_names=field_names,
            retry_limit=retry_limit,
            max_calls_left=max_calls_per_doc,
            client=client,
            llm_fn=llm_fn,
        )
        calls_made += used_calls
        if parsed_map is None:
            parse_failed_doc = True
        else:
            raw_by_field.update(parsed_map)
        for fname in field_names:
            field_models[fname] = used_model
    else:
        for f_cfg in fields_cfg:
            fname = f_cfg["name"]
            if calls_made >= max_calls_per_doc:
                field_models[fname] = None
                continue
            query = f"{fname} {f_cfg.get('description', '')} {f_cfg.get('query_hint', '')}".strip()
            chunks = retrieve(
                doc_id=doc_id,
                question=query,
                top_k=top_k,
                doc_pages=loaded_pages,
            )
            prompt = _build_field_retrieval_prompt(
                field_cfg=f_cfg,
                chunks=chunks,
                is_numeric=fname in numeric_fields,
            )
            parsed_map, used_model, used_calls = _call_llm_with_json_retry(
                prompt=prompt,
                model_role=model_role,
                temperature=temperature,
                field_names=[fname],
                retry_limit=retry_limit,
                max_calls_left=max_calls_per_doc - calls_made,
                client=client,
                llm_fn=llm_fn,
            )
            calls_made += used_calls
            field_models[fname] = used_model
            if parsed_map and fname in parsed_map:
                raw_by_field[fname] = parsed_map[fname]

    # Verify every extracted field deterministically (+ optional numeric verifier)
    models_cfg = load_model_config()
    default_model_label = models_cfg.get(model_role)
    results: list[dict[str, Any]] = []
    by_field: dict[str, dict[str, Any]] = {}

    raw_quotes_total = 0
    verified_quotes_total = 0
    quotes_repaired_total = 0
    verifier_calls_used_total = 0
    indep_flags: list[bool] = []
    counts = {
        "verified": 0,
        "not_found": 0,
        "unverified": 0,
        "needs_review": 0,
        "deferred_to_other_document": 0,
    }
    page_norm_cache: dict[int, tuple[str, list[int], list[int]]] = {}

    for f_cfg in fields_cfg:
        fname = f_cfg["name"]
        f_model = field_models.get(fname) or default_model_label
        rec, raw_q, ver_q, rep_q, v_calls = _verify_single_field(
            field_name=fname,
            field_desc=f_cfg.get("description", ""),
            raw_item=raw_by_field.get(fname),
            doc_pages=loaded_pages,
            numeric_fields=numeric_fields,
            model_used=f_model,
            verify_numeric=verify_numeric,
            client=client,
            verifier_llm_fn=verifier_llm_fn,
            verifier_calls_remaining=max(0, max_verifier_calls - verifier_calls_used_total),
            repair_enabled=repair_enabled,
            repair_min_sim=repair_min_sim,
            repair_max_chars=repair_max_chars,
            page_norm_cache=page_norm_cache,
        )
        if parse_failed_doc and "invalid_json_from_llm" not in rec["flags"]:
            rec["flags"].append("invalid_json_from_llm")

        raw_quotes_total += raw_q
        verified_quotes_total += ver_q
        quotes_repaired_total += rep_q
        verifier_calls_used_total += v_calls
        if rec["verifier_independent"] is not None:
            indep_flags.append(bool(rec["verifier_independent"]))

        counts[rec["status"]] = counts.get(rec["status"], 0) + 1
        results.append(rec)
        by_field[fname] = rec

    dropped_quotes_total = raw_quotes_total - verified_quotes_total
    raw_quote_pass_rate = (
        verified_quotes_total / raw_quotes_total if raw_quotes_total > 0 else 1.0
    )

    kept_quotes = sum(len(r["evidence"]) for r in results)
    kept_quote_verified_rate = 1.0 if kept_quotes == verified_quotes_total else (
        verified_quotes_total / kept_quotes if kept_quotes > 0 else 1.0
    )

    doc_verifier_indep: bool | None
    if not indep_flags:
        doc_verifier_indep = None
    else:
        doc_verifier_indep = all(indep_flags)

    unique_models = sorted({m for m in field_models.values() if m})
    doc_model_used = ", ".join(unique_models) if unique_models else default_model_label

    return {
        "doc_id": doc_id,
        "fields": results,
        "by_field": by_field,
        "model_used": doc_model_used,
        "retrieval_used": retrieval_used,
        "calls_made": calls_made + verifier_calls_used_total,
        "extraction_calls": calls_made,
        "verifier_calls": verifier_calls_used_total,
        "doc_chars": doc_chars,
        "num_pages": len(loaded_pages),
        "raw_quotes_total": raw_quotes_total,
        "verified_quotes_total": verified_quotes_total,
        "quotes_repaired_total": quotes_repaired_total,
        "dropped_quotes_total": dropped_quotes_total,
        "raw_quote_pass_rate": raw_quote_pass_rate,
        "quote_verified_rate": kept_quote_verified_rate,
        "counts": counts,
        "verifier_independent": doc_verifier_indep,
    }
