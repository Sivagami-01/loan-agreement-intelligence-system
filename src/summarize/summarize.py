"""src/summarize/summarize.py

Stage 3b: Grounded SHORT and DETAILED plain-English document summaries.
Uses verified/needs_review outputs from Stage 3a extract_key_info, appends
verified not_found/deferred fields deterministically, and drops any sentence
missing a page cite, containing advice/opinions, or introducing unverified numbers.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

import yaml

from src.extract.extract_fields import extract_key_info
from src.llm.gemini_client import GeminiClient, load_model_config
from src.qa.check_numbers import check_numbers, extract_items
from src.qa.doc_loader import load_document

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SUMMARIZE_CONFIG = ROOT / "config" / "summarize.yaml"

_CITE_BLOCK_RE = re.compile(r"\[p\.\s*(\d+(?:\s*,\s*(?:p\.\s*)?\d+)*)\]", re.IGNORECASE)

_ADVICE_PATTERNS = [
    re.compile(r"\byou should\b", re.IGNORECASE),
    re.compile(r"\byou ought to\b", re.IGNORECASE),
    re.compile(r"\b(?:i|we)\s+(?:recommend|advise|suggest)\b", re.IGNORECASE),
    re.compile(r"\brecommended\b", re.IGNORECASE),
    re.compile(r"\bsafe to sign\b", re.IGNORECASE),
    re.compile(r"\b(?:not\s+)?advisable\b", re.IGNORECASE),
    re.compile(r"\bconsult a (?:lawyer|attorney|professional|advisor)\b", re.IGNORECASE),
    re.compile(r"\b(?:good|bad|unfair|fair|favorable|unfavorable|predatory)\s+(?:deal|loan|agreement|rate|terms?)\b", re.IGNORECASE),
    re.compile(r"\bin my opinion\b", re.IGNORECASE),
    re.compile(r"\bdo not sign\b", re.IGNORECASE),
    re.compile(r"\bshould\s+(?:not\s+)?(?:sign|take|accept|avoid|consult)\b", re.IGNORECASE),
]

_DEFAULT_SECTIONS = [
    "Parties",
    "Money",
    "Interest and repayment",
    "Fees and penalties",
    "Prepayment",
    "Security and guarantees",
    "Default and termination",
    "Governing law",
]


def load_summarize_config(config_path: Path | None = None) -> dict[str, Any]:
    """Loads Stage 3b summary configuration from config/summarize.yaml."""
    path = config_path or DEFAULT_SUMMARIZE_CONFIG
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _extract_cited_pages(sentence: str, valid_pages: set[int]) -> list[int]:
    """Extracts unique integer page numbers from [p.N] or [p.N, p.M] cites if valid in doc."""
    pages: list[int] = []
    seen: set[int] = set()
    for match in _CITE_BLOCK_RE.finditer(sentence):
        nums = re.findall(r"\d+", match.group(1))
        for n_str in nums:
            p = int(n_str)
            if p in valid_pages and p not in seen:
                seen.add(p)
                pages.append(p)
    return pages


def _strip_cites(sentence: str) -> str:
    """Removes [p.N] citation tags before deterministic number checking."""
    cleaned = _CITE_BLOCK_RE.sub("", sentence)
    cleaned = re.sub(r"\s+([.,;:!?])", r"\1", cleaned)
    return " ".join(cleaned.split()).strip()


def _has_advice_or_opinion(sentence: str) -> bool:
    return any(pat.search(sentence) for pat in _ADVICE_PATTERNS)


def _strip_json_fences(raw_text: str) -> str:
    text = (raw_text or "").strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return text


def _parse_summary_json(raw_text: str) -> dict[str, Any] | None:
    cleaned = _strip_json_fences(raw_text)
    if not cleaned:
        return None
    for candidate in (cleaned,):
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
    s_idx, e_idx = cleaned.find("{"), cleaned.rfind("}")
    if s_idx != -1 and e_idx > s_idx:
        try:
            obj = json.loads(cleaned[s_idx : e_idx + 1])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
    return None


def _build_facts_payload(
    key_info: dict[str, Any],
    doc_pages: dict[int, str],
) -> tuple[list[dict[str, Any]], list[str], list[dict[str, Any]]]:
    """Selects ONLY verified/needs_review fields with >=1 verified quote; tracks absent/deferred."""
    verified_inputs: list[dict[str, Any]] = []
    not_found_fields: list[str] = []
    deferred_fields: list[dict[str, Any]] = []

    for rec in key_info.get("fields", []):
        fname = str(rec.get("field", ""))
        status = str(rec.get("status", ""))
        evidence = list(rec.get("evidence", []))
        if status == "not_found":
            not_found_fields.append(fname)
        elif status == "deferred_to_other_document":
            pages = sorted({int(e["page"]) for e in evidence if e.get("page") is not None})
            deferred_fields.append({
                "field": fname,
                "defers_to": str(rec.get("defers_to", "")).strip() or "another document",
                "pages": pages,
                "evidence": evidence,
            })
        elif status in {"verified", "needs_review"} and evidence:
            verified_inputs.append({
                "field": fname,
                "status": status,
                "value": str(rec.get("value", "")).strip(),
                "evidence": [{"quote": str(e.get("quote", "")), "page": int(e["page"])} for e in evidence if e.get("page") is not None],
            })

    return verified_inputs, not_found_fields, deferred_fields


def _build_summary_prompt(
    verified_inputs: list[dict[str, Any]],
    not_found_fields: list[str],
    deferred_fields: list[dict[str, Any]],
    short_max_words: int,
    section_names: list[str],
) -> str:
    """Builds JSON prompt for grounded SHORT and DETAILED plain-English summaries."""
    sections_list = [s for s in section_names if not s.lower().startswith("not found")]
    if not sections_list:
        sections_list = list(_DEFAULT_SECTIONS)

    input_json = json.dumps(
        {
            "verified_fields": verified_inputs,
            "deferred_fields": [
                {"field": d["field"], "defers_to": d["defers_to"], "pages": d["pages"]}
                for d in deferred_fields
            ],
            "not_found_fields": not_found_fields,
        },
        indent=2,
        ensure_ascii=False,
    )

    sec_schema = ", ".join(f'"{s}": [{{"text": "... [p.N]."}}]' for s in sections_list)
    return (
        "You are a plain-English legal document summarizer.\n"
        "Write BOTH a SHORT summary and DETAILED summary sections strictly from the VERIFIED FACTS JSON below.\n"
        "Output ONLY strictly valid JSON matching this schema with NO extra commentary:\n"
        f'{{"short_sentences": [{{"text": "<sentence ending with [p.N].>"}}], '
        f'"detailed_sections": {{{sec_schema}}}}}\n\n'
        "STRICT RULES:\n"
        "1. Plain English (about grade 8 reading level): clear, short, neutral sentences even when source facts are in another language (always write in English).\n"
        "2. ONE factual claim per sentence.\n"
        "3. EVERY sentence MUST end with valid page cite(s) from the verified evidence, e.g. `[p.1]` or `[p.1, p.3]` before the final period (`... [p.1].`). Sentences without a valid `[p.N]` cite will be dropped.\n"
        "4. ZERO numbers, dates, percentages, or currency amounts that do not appear verbatim in the cited page quotes/text. Copy numbers, percentages, currencies, and dates in their EXACT format (e.g. keep `$1,000,000` or `May 9, 2015` exact; never write section numbers unless quoted on that page; never convert words like 'two' to '2' unless '2' appears on the cited page).\n"
        "5. NO advice and NO opinions (never write 'you should', 'recommend', 'safe to sign', 'good deal', 'unfair', etc.).\n"
        f"6. SHORT (`short_sentences`): 4 to 6 sentences covering ONLY verified facts about: who lends to whom, how much, interest rate, tenure/maturity, repayment, main fee/penalty, and security. Keep SHORT strictly <= {short_max_words} words total (target 70-100 words). Do NOT invent facts for missing fields.\n"
        "7. DETAILED (`detailed_sections`): assign verified facts cleanly into the 8 sections "
        f"({', '.join(sections_list)}). If a section has no verified facts in the input, output `[]` for that section (our pipeline fills the `Not found / defined elsewhere` section automatically).\n\n"
        f"VERIFIED INPUTS:\n{input_json}\n"
    )


def _extract_sentences_list(section_val: Any) -> list[str]:
    out: list[str] = []
    if not isinstance(section_val, list):
        return out
    for item in section_val:
        if isinstance(item, dict):
            txt = str(item.get("text", "")).strip()
        else:
            txt = str(item).strip()
        if txt:
            out.append(txt)
    return out


def _validate_sentence(
    section: str,
    raw_text: str,
    doc_pages: dict[int, str],
    valid_pages: set[int],
) -> tuple[dict[str, Any], str | None]:
    """Deterministically validates page cite, advice absence, and source numbers for one sentence."""
    text = " ".join(str(raw_text).split()).strip()
    pages = _extract_cited_pages(text, valid_pages)
    if _has_advice_or_opinion(text):
        return (
            {
                "section": section,
                "text": text,
                "pages": pages,
                "numbers_checked": {"all_found": True, "extracted": [], "missing": []},
                "status": "dropped_advice",
            },
            f"{section}:dropped_advice",
        )

    if not pages:
        return (
            {
                "section": section,
                "text": text,
                "pages": [],
                "numbers_checked": {"all_found": False, "extracted": [], "missing": []},
                "status": "dropped_no_cite",
            },
            f"{section}:dropped_no_cite",
        )

    clean_for_nums = _strip_cites(text)
    ev_for_check = [{"quote": "", "page": p} for p in pages]
    num_res = check_numbers(answer=clean_for_nums, evidence=ev_for_check, doc_pages=doc_pages)
    # Also ensure Devanagari extraction summary counts cleanly
    if not num_res["all_found"]:
        return (
            {
                "section": section,
                "text": text,
                "pages": pages,
                "numbers_checked": num_res,
                "status": "dropped_unverified_number",
            },
            f"{section}:dropped_unverified_number:{num_res['missing']}",
        )

    return (
        {
            "section": section,
            "text": text,
            "pages": pages,
            "numbers_checked": num_res,
            "status": "kept",
        },
        None,
    )


def _format_field_label(fname: str) -> str:
    return fname.replace("_", " ").capitalize()


def summarize_document(
    doc_id: str,
    doc_pages: dict[int, str] | None = None,
    key_info: dict[str, Any] | None = None,
    client: GeminiClient | None = None,
    config: dict[str, Any] | None = None,
    llm_fn: Callable[[str], tuple[str, str]] | None = None,
) -> dict[str, Any]:
    """Produces verified SHORT and DETAILED plain-English summaries for one document."""
    cfg = config if config is not None else load_summarize_config()
    model_role = str(cfg.get("model_role", "bulk"))
    temperature = float(cfg.get("temperature", 0.0))
    short_max_words = int(cfg.get("short_max_words", 120))
    max_live_calls = int(cfg.get("max_live_calls", 30))
    retry_limit = int(cfg.get("retry_on_invalid_json", 1))
    section_names = list(cfg.get("detailed_sections", _DEFAULT_SECTIONS))

    if doc_pages is None:
        _, loaded_pages = load_document(doc_id)
    else:
        loaded_pages = {int(k): str(v) for k, v in doc_pages.items()}

    if not loaded_pages:
        raise FileNotFoundError(f"Could not load pages for doc_id={doc_id!r}")

    if client is None and llm_fn is None:
        client = GeminiClient()

    if key_info is None:
        key_info = extract_key_info(doc_id=doc_id, doc_pages=loaded_pages, client=client, verify_numeric=False)

    verified_inputs, not_found_fields, deferred_fields = _build_facts_payload(key_info, loaded_pages)
    valid_pages = set(loaded_pages.keys())
    flags: list[str] = []
    calls_made = 0
    models_cfg = load_model_config()
    model_used: str | None = models_cfg.get(model_role)

    parsed_payload: dict[str, Any] | None = None
    quota_stopped = False

    if verified_inputs:
        prompt = _build_summary_prompt(
            verified_inputs=verified_inputs,
            not_found_fields=not_found_fields,
            deferred_fields=deferred_fields,
            short_max_words=short_max_words,
            section_names=section_names,
        )
        cur_prompt = prompt
        attempts = 1 + max(0, retry_limit)

        for attempt in range(attempts):
            if llm_fn is None:
                assert client is not None
                if client.api_calls_made >= max_live_calls:
                    quota_stopped = True
                    flags.append(f"call_budget_reached:{max_live_calls}")
                    break
            calls_made += 1
            try:
                if llm_fn is not None:
                    raw_text, model_used = llm_fn(cur_prompt)
                else:
                    assert client is not None
                    raw_text = client.generate(cur_prompt, model_alias=model_role, temperature=temperature)
                    model_used = client.last_model_used or model_used
            except Exception as exc:
                quota_stopped = True
                flags.append(f"quota_or_api_error:{type(exc).__name__}")
                break

            parsed_payload = _parse_summary_json(raw_text)
            if parsed_payload is not None:
                break
            if attempt + 1 < attempts:
                cur_prompt = (
                    "Previous output was NOT valid JSON matching the schema. Return ONLY JSON.\n\n"
                    + prompt
                )
        if parsed_payload is None and not quota_stopped:
            flags.append("invalid_json_from_llm")
    else:
        flags.append("no_verified_fields_for_summary")

    sentences: list[dict[str, Any]] = []
    kept_short: list[str] = []
    detailed_by_sec: dict[str, list[str]] = {}

    if parsed_payload is not None:
        # 1. Validate SHORT sentences
        for raw_s in _extract_sentences_list(parsed_payload.get("short_sentences", [])):
            rec, flag = _validate_sentence("short", raw_s, loaded_pages, valid_pages)
            sentences.append(rec)
            if flag:
                flags.append(flag)
            else:
                kept_short.append(rec["text"])

        # Enforce short_max_words strictly without breaking sentences
        while len(" ".join(kept_short).split()) > short_max_words and kept_short:
            dropped_txt = kept_short.pop()
            for rec in reversed(sentences):
                if rec["section"] == "short" and rec["text"] == dropped_txt and rec["status"] == "kept":
                    rec["status"] = "dropped_over_short_word_limit"
                    break
            if "short_trimmed_to_max_words" not in flags:
                flags.append("short_trimmed_to_max_words")

        # 2. Validate DETAILED sections
        raw_secs = parsed_payload.get("detailed_sections", {})
        if not isinstance(raw_secs, dict):
            raw_secs = {}

        ordered_detail_secs = [s for s in section_names if not s.lower().startswith("not found")]
        if not ordered_detail_secs:
            ordered_detail_secs = list(_DEFAULT_SECTIONS)

        for sec_name in ordered_detail_secs:
            detailed_by_sec[sec_name] = []
            for raw_s in _extract_sentences_list(raw_secs.get(sec_name, [])):
                rec, flag = _validate_sentence(sec_name, raw_s, loaded_pages, valid_pages)
                sentences.append(rec)
                if flag:
                    flags.append(flag)
                else:
                    detailed_by_sec[sec_name].append(rec["text"])

    short_text = " ".join(kept_short).strip()

    # Build deterministic "Not found / defined elsewhere" lines
    absence_lines: list[str] = []
    for d in deferred_fields:
        label = _format_field_label(d["field"])
        cites = ", ".join(f"p.{p}" for p in d["pages"]) if d["pages"] else ""
        cite_str = f" [{cites}]" if cites else ""
        absence_lines.append(
            f"- {label}: Defined in another document (not provided; refers to {d['defers_to']}){cite_str}."
        )
    for fname in not_found_fields:
        label = _format_field_label(fname)
        absence_lines.append(f"- {label}: Not found in this document.")

    # Format detailed text from kept sentences + deterministic Not found / defined elsewhere
    detailed_blocks: list[str] = []
    ordered_detail_secs = [s for s in section_names if not s.lower().startswith("not found")] or list(_DEFAULT_SECTIONS)
    for sec_name in ordered_detail_secs:
        lines = detailed_by_sec.get(sec_name, [])
        body = " ".join(lines) if lines else "None verified in this document."
        detailed_blocks.append(f"## {sec_name}\n{body}")

    absence_body = "\n".join(absence_lines) if absence_lines else "None."
    detailed_blocks.append(f"## Not found / defined elsewhere\n{absence_body}")
    detailed_text = "\n\n".join(detailed_blocks).strip()

    return {
        "doc_id": doc_id,
        "short": short_text,
        "detailed": detailed_text,
        "sentences": sentences,
        "not_found_fields": not_found_fields,
        "deferred_fields": [d["field"] for d in deferred_fields],
        "flags": flags,
        "model_used": model_used,
        "calls_made": calls_made,
        "short_word_count": len(short_text.split()) if short_text else 0,
    }
