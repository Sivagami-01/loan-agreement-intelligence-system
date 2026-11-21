"""src/qa/ask.py

Unified Routed QA Entrypoint (Stage 2d).
Calls route_question(question) first, then dispatches cleanly:
- fact: answer_question(doc_id, question, verify=True)
- explain_term: plain-language explanation (max 4 sentences, clearly labeled
  'General explanation, not from your document'), plus verified quote if term
  appears in the document.
- calculation: extracts grounded inputs and runs deterministic Decimal calculators.
- advice: returns neutral information-not-advice refusal + offer to show document
  clauses (risks, fees, penalties), never gives a recommendation.
- off_topic: polite refusal, zero API answer calls.

Output always includes: category, status, answer, evidence, model_used, router_fallback.
"""

from __future__ import annotations

import re
from typing import Any

from src.llm.gemini_client import GeminiClient
from src.calc.extract_inputs import calculate, extract_inputs
from src.qa.answer import answer_question, load_document
from src.qa.router import load_router_config, route_question

_EXPLAIN_BOILERPLATE = frozenset({
    "what", "does", "do", "is", "are", "the", "a", "an", "mean", "means",
    "meaning", "of", "explain", "define", "term", "simply", "in", "simple",
    "words", "please", "banking", "finance", "financial", "loan", "legal",
    "could", "you", "tell", "me", "about",
})


def _extract_candidate_terms(question: str) -> list[str]:
    words = re.findall(r"[^\W_]+", question.lower())
    terms = [w for w in words if len(w) >= 3 and w not in _EXPLAIN_BOILERPLATE]
    return terms


def _cap_sentences(text: str, max_sentences: int = 4) -> str:
    cleaned = " ".join(text.split()).strip()
    if not cleaned:
        return cleaned
    parts = re.split(r"(?<=[.!?।])\s+", cleaned)
    if len(parts) <= max_sentences:
        return cleaned
    return " ".join(parts[:max_sentences]).strip()


def ask(
    doc_id: str,
    question: str,
    client: GeminiClient | None = None,
    verify: bool = True,
    doc_pages: dict[int, str] | None = None,
) -> dict[str, Any]:
    """Routes `question` and produces a safe, verified response contract."""
    if client is None:
        client = GeminiClient()

    router_cfg = load_router_config()
    route = route_question(question, client=client, config=router_cfg)
    category = route["category"]
    router_fallback = bool(route.get("router_fallback", False))
    route_model = route.get("model_used")

    # 1. Fact -> Existing answer_question pipeline (with verify=True by default)
    if category == "fact":
        ans_res = answer_question(doc_id, question, client=client, verify=verify)
        result: dict[str, Any] = {
            "category": "fact",
            "status": ans_res.get("status", "unknown"),
            "answer": ans_res.get("answer", ""),
            "evidence": ans_res.get("evidence", []),
            "flags": ans_res.get("flags", []),
            "model_used": ans_res.get("model_used") or route_model,
            "router_fallback": router_fallback,
            "language": route.get("language", "en"),
            "rule_based_route": route.get("rule_based", False),
        }
        for k in (
            "retrieval_used",
            "retrieved_pages",
            "verifier_verdict",
            "verifier_reason",
            "verifier_model_used",
            "verifier_independent",
            "final_check",
        ):
            if k in ans_res:
                result[k] = ans_res[k]
        return result

    # 2. Explain Term -> General explanation (max 4 sentences) + optional document quote
    if category == "explain_term":
        label = str(router_cfg.get("explain_label", "General explanation, not from your document"))
        explain_role = str(router_cfg.get("model_role", "bulk"))
        temperature = float(router_cfg.get("temperature", 0.0))

        prompt = (
            "Explain the following loan/banking/legal term in plain, everyday words "
            "for a student or borrower. Maximum 3 to 4 short sentences. "
            "Do NOT give legal or financial advice, and do NOT recommend signing or avoiding any loan.\n\n"
            f"Question: {question}"
        )
        raw_expl = client.generate(prompt, model_alias=explain_role, temperature=temperature)
        expl_model = client.last_model_used or route_model
        expl_text = _cap_sentences(raw_expl, max_sentences=4)

        answer_parts = [f"{label}:", expl_text]
        evidence: list[dict[str, Any]] = []

        # If candidate term appears in document, try to attach verified document quote
        candidate_terms = _extract_candidate_terms(question)
        if candidate_terms and doc_id:
            full_text, _ = load_document(doc_id)
            low_doc = full_text.lower()
            matched_terms = [t for t in candidate_terms if t in low_doc]
            if matched_terms:
                doc_query = f"What does the document state about {' '.join(matched_terms)}?"
                doc_res = answer_question(doc_id, doc_query, client=client, verify=verify)
                if doc_res.get("status") == "ok" and doc_res.get("evidence"):
                    evidence = doc_res["evidence"]
                    pages = sorted({int(e["page"]) for e in evidence if e.get("page") is not None})
                    answer_parts.append(
                        f"\nAlso mentioned in your document (Page {', '.join(map(str, pages))}): "
                        f"{doc_res.get('answer', '')}"
                    )

        return {
            "category": "explain_term",
            "status": "ok",
            "answer": "\n".join(answer_parts).strip(),
            "evidence": evidence,
            "flags": [],
            "model_used": expl_model,
            "router_fallback": router_fallback,
            "language": route.get("language", "en"),
            "rule_based_route": route.get("rule_based", False),
        }

    # 3. Calculation -> LLMs may extract inputs only; all arithmetic is deterministic Python.
    if category == "calculation":
        calls_before = client.api_calls_made
        cache_hits_before = client.cache_hits
        extracted = extract_inputs(question, doc_id=doc_id, client=client, doc_pages=doc_pages)
        input_model = (
            client.last_model_used
            if client.api_calls_made > calls_before or client.cache_hits > cache_hits_before
            else route_model
        )
        if extracted["missing"]:
            missing = ", ".join(extracted["missing"])
            return {
                "category": "calculation",
                "status": "needs_inputs",
                "answer": f"Please provide: {missing}. I will not guess missing values.",
                "evidence": [],
                "inputs": extracted["inputs"],
                "missing": extracted["missing"],
                "flags": extracted["flags"],
                "model_used": input_model,
                "router_fallback": router_fallback,
                "language": route.get("language", "en"),
                "rule_based_route": route.get("rule_based", False),
            }
        calculation = calculate(extracted)
        result_value = calculation["result"]
        currency = calculation.get("currency")
        rendered_result = f"{currency} {result_value}" if currency else str(result_value)
        disclaimer = (
            "Estimate only: your lender's schedule may differ because of rounding, "
            "day-count, fees and taxes. Not financial advice."
        )
        return {
            "category": "calculation",
            "status": "ok",
            "answer": f"Estimated result: {rendered_result}\n{disclaimer}",
            "evidence": [],
            "inputs": extracted["inputs"],
            "formula_name": calculation["formula_name"],
            "steps": calculation["steps"],
            "assumptions": calculation["assumptions"],
            "result": result_value,
            "currency": currency,
            "flags": extracted["flags"],
            "model_used": input_model,
            "router_fallback": router_fallback,
            "language": route.get("language", "en"),
            "rule_based_route": route.get("rule_based", False),
        }

    # 4. Advice -> Neutral information-not-advice refusal + offer relevant document clauses
    if category == "advice":
        advice_msg = str(
            router_cfg.get(
                "advice_message",
                "This system provides information, not legal or financial advice. "
                "I can show you the relevant clauses (risks, fees, penalties) from the document.",
            )
        ).strip()
        return {
            "category": "advice",
            "status": "refused",
            "answer": advice_msg,
            "evidence": [],
            "flags": ["advice_refused"],
            "model_used": route_model,
            "router_fallback": router_fallback,
            "language": route.get("language", "en"),
            "rule_based_route": route.get("rule_based", False),
        }

    # 5. Off-topic -> Polite refusal, no API answer
    off_msg = str(
        router_cfg.get(
            "off_topic_message",
            "I can only answer questions related to loan agreements and financial contracts.",
        )
    ).strip()
    return {
        "category": "off_topic",
        "status": "off_topic",
        "answer": off_msg,
        "evidence": [],
        "flags": ["off_topic_refused"],
        "model_used": route_model,
        "router_fallback": router_fallback,
        "language": route.get("language", "en"),
        "rule_based_route": route.get("rule_based", False),
    }
