"""src/qa/answer.py

Single-Prompt & Retrieval-Backed QA Core for Loan Agreement Analysis.
Implements Stage 2c-1 and Stage 2c-2a of MASTER_PLAN:
- Long-context first: if document length <= max_doc_chars_for_whole_doc and retrieval
  is not forced, sends the full document with [[PAGE n]] markers.
- Retrieval mode (Stage 2c-2a): if text length > max_doc_chars_for_whole_doc OR
  force_retrieval is True, retrieves top_k BM25 chunks (within max_prompt_chars).
- Strict JSON contract: {"found": bool, "answer": str, "evidence": [{"quote": str, "page": int}]}
- Verbatim quote verification runs against FULL document pages (never only retrieved chunks).
- Suppresses unverified answers (returns status='unverified').
- Output contract:
  {status, answer, evidence, flags, retrieval_used, retrieved_pages, model_used}
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from src.llm.gemini_client import GeminiClient
from src.qa.doc_loader import INGESTED_DIR, load_document  # noqa: F401
from src.qa.retrieve import load_retrieval_config, retrieve
from src.qa.verifier import verify_answer
from src.qa.verify_quotes import verify_evidence

ROOT = Path(__file__).resolve().parents[2]
QA_CONFIG_FILE = ROOT / "config" / "qa.yaml"

DEFAULT_MAX_DOC_CHARS = 400000


def load_qa_config() -> dict[str, Any]:
    if QA_CONFIG_FILE.is_file():
        try:
            data = yaml.safe_load(QA_CONFIG_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {
        "max_doc_chars_for_whole_doc": DEFAULT_MAX_DOC_CHARS,
        "temperature": 0.0,
        "model_role": "main",
        "retry_on_invalid_json": 1,
    }


def parse_json_response(raw_text: str) -> dict[str, Any] | None:
    """Extracts and parses a JSON object from LLM response text."""
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

    # Fallback: search for outermost {...}
    match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    return None


def build_qa_prompt(doc_context: str, question: str, retrieval_mode: bool = False) -> str:
    if not retrieval_mode:
        return f"""You are a precise, objective loan agreement and legal contract assistant.
Your task is to answer the user's question using ONLY the verbatim information present in the document text provided below.

CRITICAL RULES:
1. Answer ONLY from the document text provided. Do NOT extrapolate, guess, or use external knowledge.
2. If the document does not explicitly state the answer, set "found": false and "answer": "Not found in this document", with an empty "evidence" list.
3. If the document states the answer, set "found": true and provide a concise, factual answer.
4. For every claim, you MUST include supporting evidence in the "evidence" array:
   - "quote": exact verbatim words copied directly from the document.
   - "page": the integer page number (from the [[PAGE n]] marker) where the quote appears.
5. Do NOT give legal or financial advice.

You must reply with ONLY a valid JSON object matching this schema:
{{
  "found": true,
  "answer": "Concise factual answer to the question",
  "evidence": [
    {{
      "quote": "exact quote copied directly from text",
      "page": 1
    }}
  ]
}}

DOCUMENT TEXT:
---
{doc_context}
---

QUESTION: {question}
"""
    return f"""You are a precise, objective loan agreement and legal contract assistant.
Your task is to answer the user's question using ONLY the retrieved document excerpts (marked with [[PAGE n]]) provided below.

CRITICAL RULES:
1. Answer ONLY from the retrieved excerpts provided below. Do NOT extrapolate, guess, or use external knowledge.
2. If the retrieved excerpts do not explicitly state the answer (even if it might appear elsewhere in the document), set "found": false and "answer": "Not found in this document", with an empty "evidence" list. Never guess.
3. If the retrieved excerpts state the answer, set "found": true and provide a concise, factual answer.
4. For every claim, you MUST include supporting evidence in the "evidence" array:
   - "quote": exact character-for-character substring copied directly from the excerpts (NEVER fix typos, spelling, OCR errors, or garbled font characters; if bilingual text contains clean English alongside garbled Indic text, prefer quoting the clean exact substring or copy the exact characters verbatim).
   - "page": the integer page number (from the [[PAGE n]] marker) where the quote appears.
5. Do NOT give legal or financial advice.

You must reply with ONLY a valid JSON object matching this schema:
{{
  "found": true,
  "answer": "Concise factual answer to the question",
  "evidence": [
    {{
      "quote": "exact quote copied directly from text",
      "page": 1
    }}
  ]
}}

DOCUMENT TEXT:
---
{doc_context}
---

QUESTION: {question}
"""


def _format_retrieved_context(
    chunks: list[dict[str, Any]],
    question: str,
    max_prompt_chars: int,
) -> tuple[str, list[dict[str, Any]]]:
    """Selects chunks in relevance order up to max_prompt_chars, then formats with [[PAGE n]]."""
    prompt_overhead = len(build_qa_prompt("", question, retrieval_mode=True)) + 100
    context_budget = max(500, int(max_prompt_chars) - prompt_overhead)

    selected: list[dict[str, Any]] = []
    used_chars = 0

    for ch in chunks:
        block = f"[[PAGE {ch['page']}]]\n{ch['text']}"
        addition = len(block) + (2 if selected else 0)
        if used_chars + addition <= context_budget:
            selected.append(ch)
            used_chars += addition
        elif not selected:
            # Ensure at least the top chunk fits cleanly even if budget is tight
            allowed = max(100, context_budget - len(f"[[PAGE {ch['page']}]]\n"))
            truncated = dict(ch)
            truncated["text"] = ch["text"][:allowed]
            selected.append(truncated)
            break
        else:
            break

    # Order selected excerpts naturally by (page, char_start) for readability
    ordered = sorted(selected, key=lambda c: (int(c["page"]), int(c.get("char_start", 0))))
    blocks = [f"[[PAGE {c['page']}]]\n{c['text']}" for c in ordered]
    return "\n\n".join(blocks), selected


def answer_question(
    doc_id: str,
    question: str,
    client: GeminiClient | None = None,
    config: dict[str, Any] | None = None,
    force_retrieval: bool = False,
    retrieval_config: dict[str, Any] | None = None,
    verify: bool = False,
) -> dict[str, Any]:
    """Answers a question against a document using whole-document or BM25 retrieval context.

    Returns:
        dict: {
            "status": "ok" | "not_found" | "unverified",
            "answer": str,
            "evidence": list[dict],
            "flags": list[str],
            "retrieval_used": bool,
            "retrieved_pages": list[int],
            "model_used": str | None,
        }
    """
    if config is None:
        config = load_qa_config()
    if retrieval_config is None:
        retrieval_config = load_retrieval_config()

    max_chars = int(config.get("max_doc_chars_for_whole_doc", DEFAULT_MAX_DOC_CHARS))
    model_role = str(config.get("model_role", "main"))
    temperature = float(config.get("temperature", 0.0))

    # 1. Load document
    full_text, doc_pages = load_document(doc_id)
    if not full_text or not doc_pages:
        return {
            "status": "not_found",
            "answer": f"Document '{doc_id}' not found in processed corpus.",
            "evidence": [],
            "flags": ["document_not_found"],
            "retrieval_used": False,
            "retrieved_pages": [],
            "model_used": None,
        }

    # 2. Decide whole-doc vs retrieval mode
    use_retrieval = (
        len(full_text) > max_chars
        or bool(retrieval_config.get("force_retrieval", False))
        or bool(force_retrieval)
    )

    retrieved_pages: list[int] = []
    if use_retrieval:
        top_k = int(retrieval_config.get("top_k", 8))
        max_prompt_chars = int(retrieval_config.get("max_prompt_chars", 60000))
        chunks = retrieve(
            doc_id=doc_id,
            question=question,
            top_k=top_k,
            doc_pages=doc_pages,
            config=retrieval_config,
        )
        if not chunks:
            return {
                "status": "not_found",
                "answer": "Not found in this document",
                "evidence": [],
                "raw_evidence": [],
                "flags": ["no_chunks_retrieved"],
                "retrieval_used": True,
                "retrieved_pages": [],
                "model_used": None,
            }
        doc_context, selected_chunks = _format_retrieved_context(chunks, question, max_prompt_chars)
        retrieved_pages = sorted({int(c["page"]) for c in selected_chunks})
    else:
        doc_context = full_text

    if client is None:
        client = GeminiClient()

    # 3. Call LLM
    prompt = build_qa_prompt(doc_context, question, retrieval_mode=use_retrieval)
    raw_response = client.generate(prompt, model_alias=model_role, temperature=temperature)
    model_used = client.last_model_used

    # 4. Parse JSON with 1 retry
    parsed = parse_json_response(raw_response)
    if parsed is None and int(config.get("retry_on_invalid_json", 1)) > 0:
        reprompt = (
            "The following output was not valid JSON. Please extract and return ONLY a valid JSON object "
            f'matching {{"found": bool, "answer": str, "evidence": [{{"quote": str, "page": int}}]}}:\n\n'
            f"{raw_response[:2000]}"
        )
        retry_raw = client.generate(reprompt, model_alias=model_role, temperature=temperature)
        model_used = client.last_model_used or model_used
        parsed = parse_json_response(retry_raw)

    if parsed is None:
        return {
            "status": "unverified",
            "answer": "",
            "evidence": [],
            "flags": ["invalid_json_response"],
            "retrieval_used": use_retrieval,
            "retrieved_pages": retrieved_pages,
            "model_used": model_used,
        }

    found = bool(parsed.get("found", False))
    answer_text = str(parsed.get("answer", "")).strip()
    raw_evidence = parsed.get("evidence", [])
    if not isinstance(raw_evidence, list):
        raw_evidence = []

    # 5. Handle "not found"
    if not found or answer_text.lower().startswith("not found"):
        return {
            "status": "not_found",
            "answer": "Not found in this document",
            "evidence": [],
            "raw_evidence": raw_evidence,
            "flags": [],
            "retrieval_used": use_retrieval,
            "retrieved_pages": retrieved_pages,
            "model_used": model_used,
        }

    # 6. Verify evidence quotes against FULL document pages (never only retrieved chunks)
    verified_evidence, verify_flags = verify_evidence(doc_pages, raw_evidence)

    # 7. Quality gate: if found=true but no evidence survives verification, reject answer
    if not verified_evidence:
        return {
            "status": "unverified",
            "answer": "",
            "evidence": [],
            "raw_evidence": raw_evidence,
            "flags": ["evidence_unverified"] + verify_flags,
            "retrieval_used": use_retrieval,
            "retrieved_pages": retrieved_pages,
            "model_used": model_used,
        }

    result: dict[str, Any] = {
        "status": "ok",
        "answer": answer_text,
        "evidence": verified_evidence,
        "raw_evidence": raw_evidence,
        "flags": verify_flags,
        "retrieval_used": use_retrieval,
        "retrieved_pages": retrieved_pages,
        "model_used": model_used,
    }

    if verify:
        vres = verify_answer(
            question=question,
            answer=answer_text,
            evidence=verified_evidence,
            doc_pages=doc_pages,
            answer_model_used=model_used,
            client=client,
        )
        result["verifier_verdict"] = vres["verifier_verdict"]
        result["verifier_reason"] = vres["verifier_reason"]
        result["verifier_model_used"] = vres["verifier_model_used"]
        result["verifier_independent"] = vres["verifier_independent"]
        result["final_check"] = vres["final_check"]

    return result
