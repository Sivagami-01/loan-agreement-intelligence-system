"""src/qa/verifier.py

Second-Model Answer Verifier Pass (Stage 2c-3).
- Verifies that an answer is strictly entailed by the verified quotes and their
  local context window (up to context_chars_around_quote from the cited page).
  Never passes the whole document to the verifier.
- Enforces deterministic number/date/money/percentage consistency via check_numbers.
- Enforces strict independence: if the verifier call falls back to the same model
  that generated the answer (or no verifier response is obtained), marks
  verifier_independent=False and verdict='unchecked' (never 'verified').
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

import yaml

from src.llm.gemini_client import GeminiClient, load_model_config
from src.qa.check_numbers import check_numbers

ROOT = Path(__file__).resolve().parents[2]
VERIFY_CONFIG_FILE = ROOT / "config" / "verify.yaml"


def load_verify_config() -> dict[str, Any]:
    if VERIFY_CONFIG_FILE.is_file():
        try:
            data = yaml.safe_load(VERIFY_CONFIG_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {
        "model_role": "verifier",
        "temperature": 0.0,
        "max_calls_per_run": 25,
        "context_chars_around_quote": 1500,
    }


def _extract_quote_context(
    quote: str,
    page_text: str,
    context_chars: int = 1500,
) -> str:
    """Extracts the quote plus up to `context_chars` characters around it from `page_text`.
    Never returns the whole document.
    """
    if not page_text:
        return quote

    half = max(100, int(context_chars) // 2)
    q_clean = quote.strip()
    if not q_clean:
        return page_text[:context_chars]

    # 1. Try direct case-insensitive find
    idx = page_text.lower().find(q_clean.lower())
    if idx != -1:
        start = max(0, idx - half)
        end = min(len(page_text), idx + len(q_clean) + half)
        return page_text[start:end].strip()

    # 2. Try whitespace-flexible search anchored by quote tokens
    words = [re.escape(w) for w in q_clean.split() if w]
    if words:
        if len(words) <= 12:
            pattern_str = r"\s+".join(words)
        else:
            # Match start words ... end words flexibly if quote spans lines/tabs
            head = r"\s+".join(words[:5])
            tail = r"\s+".join(words[-4:])
            pattern_str = f"{head}.{{0,800}}?{tail}"
        try:
            m = re.search(pattern_str, page_text, re.IGNORECASE | re.DOTALL)
            if m:
                start = max(0, m.start() - half)
                end = min(len(page_text), m.end() + half)
                return page_text[start:end].strip()
        except re.error:
            pass

    # 3. Fallback: quote + capped leading snippet of cited page (strictly <= len(quote)+context_chars)
    snippet = page_text[:half].strip()
    if snippet and snippet.lower() not in q_clean.lower():
        return f"{q_clean}\n[Cited page excerpt]: {snippet}"
    return q_clean


def build_verifier_prompt(
    question: str,
    answer: str,
    evidence: list[dict[str, Any]],
    doc_pages: dict[int, str],
    context_chars_around_quote: int = 1500,
) -> str:
    evidence_blocks: list[str] = []
    for idx, ev in enumerate(evidence or [], 1):
        quote = str(ev.get("quote", "")).strip()
        page_num = ev.get("page")
        page_text = ""
        if doc_pages and page_num is not None:
            try:
                page_text = doc_pages.get(int(page_num), "")
            except (TypeError, ValueError):
                page_text = ""
        local_ctx = _extract_quote_context(quote, page_text, context_chars=context_chars_around_quote)
        evidence_blocks.append(
            f"[Quote {idx} - Page {page_num}]\n"
            f"Exact Quote: \"{quote}\"\n"
            f"Local Page Context: {local_ctx}"
        )

    evidence_section = "\n\n".join(evidence_blocks) if evidence_blocks else "(No verified quotes provided)"

    return f"""You are a strict, independent factual verification judge for loan agreement Q&A.
Your ONLY task is to decide whether the ANSWER is strictly supported by the GIVEN EVIDENCE TEXT below.

CRITICAL RULES:
1. Judge ONLY from the GIVEN EVIDENCE TEXT below. Do NOT use outside knowledge.
2. The answer must NOT add any claim, number, date, party, condition, or implication that the text does not explicitly say.
3. A changed number, changed party, changed place, changed date, or opposite meaning (for example "charges apply" when text says "no charges") MUST be marked "not_supported".
4. If the main claim is supported but the answer adds an extra unsupported detail or minor overstatement, mark "partly_supported".
5. Only mark "supported" if every factual claim in the answer is directly stated in the given text.

Reply with ONLY a valid JSON object matching this exact schema:
{{
  "verdict": "supported" | "partly_supported" | "not_supported",
  "reason": "One short sentence explaining why.",
  "unsupported_parts": ["list any unsupported words or claims, empty list if supported"]
}}

QUESTION: {question}

PROPOSED ANSWER: {answer}

GIVEN EVIDENCE TEXT:
---
{evidence_section}
---
"""


def _parse_verifier_json(raw_text: str) -> dict[str, Any] | None:
    if not raw_text:
        return None
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return None


def combine_checks(
    verdict: str,
    verifier_independent: bool,
    number_check: dict[str, Any],
) -> tuple[str, str]:
    """Combines LLM verdict, independence flag, and deterministic check_numbers result.

    Returns:
        (effective_verdict, final_check)
    """
    all_found = bool(number_check.get("all_found", True))

    if not verifier_independent or verdict not in {"supported", "partly_supported", "not_supported"}:
        effective_verdict = "unchecked"
        final_check = "unchecked" if all_found else "needs_review"
        return effective_verdict, final_check

    if verdict == "not_supported":
        return "not_supported", "rejected"

    if verdict == "partly_supported" or not all_found:
        return verdict, "needs_review"

    if verdict == "supported" and all_found:
        return "supported", "verified"

    return "unchecked", "unchecked"


def verify_answer(
    question: str,
    answer: str,
    evidence: list[dict[str, Any]],
    doc_pages: dict[int, str],
    answer_model_used: str | None = None,
    client: GeminiClient | None = None,
    config: dict[str, Any] | None = None,
    llm_fn: Callable[[str], tuple[str, str | None]] | None = None,
) -> dict[str, Any]:
    """Runs second-model verification + deterministic number verification on an answer.

    Args:
        question: User question.
        answer: Proposed answer text.
        evidence: Verified quotes list [{'quote': ..., 'page': ...}, ...].
        doc_pages: Full document pages mapping {page_num: text}.
        answer_model_used: Model name that generated `answer` (for cross-model independence check).
        client: Optional GeminiClient instance (shares API counter / cache).
        config: Optional verify config dict.
        llm_fn: Optional fake callable `(prompt) -> (raw_json_text, model_used)` for unit tests.

    Returns:
        dict with verifier_verdict, verifier_reason, unsupported_parts,
        verifier_model_used, verifier_independent, final_check, number_check,
        raw_llm_verdict, raw_llm_reason.
    """
    if config is None:
        config = load_verify_config()

    model_role = str(config.get("model_role", "verifier"))
    temperature = float(config.get("temperature", 0.0))
    context_chars = int(config.get("context_chars_around_quote", 1500))

    # 1. Deterministic number/date/percentage/money check
    num_res = check_numbers(answer, evidence, doc_pages)

    # 2. Build focused prompt (ONLY question, answer, verified quote + local context window)
    prompt = build_verifier_prompt(
        question=question,
        answer=answer,
        evidence=evidence,
        doc_pages=doc_pages,
        context_chars_around_quote=context_chars,
    )

    # 3. Query verifier LLM (or fake callable in unit tests)
    raw_text = ""
    verifier_model_used: str | None = None
    call_error: str | None = None

    try:
        if llm_fn is not None:
            raw_text, verifier_model_used = llm_fn(prompt)
        else:
            if client is None:
                client = GeminiClient()
            # Keep verifier RPM conservative on free tier to prevent premature 429 fallback
            if hasattr(client, "min_interval") and client.min_interval < 6.5:
                client.min_interval = 6.5
            raw_text = client.generate(prompt, model_alias=model_role, temperature=temperature)
            verifier_model_used = client.last_model_used
    except Exception as exc:
        call_error = f"{type(exc).__name__}: {str(exc)[:160]}"
        raw_text = ""
        verifier_model_used = None

    parsed = _parse_verifier_json(raw_text)

    # 4. Determine cross-model independence strictly
    models_cfg = load_model_config()
    effective_answer_model = answer_model_used or models_cfg.get("bulk")

    if not verifier_model_used or parsed is None:
        verifier_independent = False
    elif effective_answer_model and verifier_model_used == effective_answer_model:
        verifier_independent = False
    elif verifier_model_used == models_cfg.get("bulk") and answer_model_used is None:
        # Without explicit answer_model_used, falling back to bulk is non-independent
        verifier_independent = False
    else:
        verifier_independent = True

    raw_llm_verdict: str | None = None
    raw_llm_reason: str = ""
    unsupported_parts: list[str] = []

    if parsed is not None:
        raw_v = str(parsed.get("verdict", "")).strip().lower()
        if raw_v in {"supported", "partly_supported", "not_supported"}:
            raw_llm_verdict = raw_v
        raw_llm_reason = str(parsed.get("reason", "")).strip()
        raw_unsupp = parsed.get("unsupported_parts", [])
        if isinstance(raw_unsupp, list):
            unsupported_parts = [str(x) for x in raw_unsupp if str(x).strip()]

    # If verifier failed or fell back to same model -> verdict MUST be "unchecked"
    candidate_verdict = raw_llm_verdict or "unchecked"
    effective_verdict, final_check = combine_checks(
        verdict=candidate_verdict,
        verifier_independent=verifier_independent,
        number_check=num_res,
    )

    # Construct clear reason explaining outcome and any fallback / missing numbers
    reason_parts: list[str] = []
    if call_error:
        reason_parts.append(f"Verifier unavailable ({call_error}).")
    elif not verifier_independent:
        reason_parts.append(
            f"Not independent: verifier model '{verifier_model_used}' matches answer model "
            f"'{effective_answer_model}'."
        )
    if raw_llm_reason:
        reason_parts.append(raw_llm_reason)
    if not num_res["all_found"]:
        reason_parts.append(f"Missing numeric/date values in source: {num_res['missing']}.")

    verifier_reason = " ".join(reason_parts).strip() or f"Verdict: {effective_verdict}."

    return {
        "verifier_verdict": effective_verdict,
        "verifier_reason": verifier_reason,
        "unsupported_parts": unsupported_parts,
        "verifier_model_used": verifier_model_used,
        "verifier_independent": verifier_independent,
        "final_check": final_check,
        "number_check": num_res,
        "raw_llm_verdict": raw_llm_verdict,
        "raw_llm_reason": raw_llm_reason,
    }
