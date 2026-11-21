"""src/qa/router.py

Question Router for Loan Agreement QA (Stage 2d).
Routes user questions into one of five categories:
    fact | explain_term | calculation | advice | off_topic

Design note:
    "not in document" is intentionally NOT a router category. Whether a factual
    question is absent from a specific document is decided downstream by
    answer_question() returning status="not_found" (found=false).

Pipeline:
    1. Detect language deterministically from Unicode script (en|hi|ta|bn|pa|ml|other).
    2. Apply cheap deterministic rules for high-confidence cases (especially safety-critical
       advice, calculation, term explanation, off-topic, and explicit document lookups).
    3. Call the bulk LLM (configured in config/router.yaml) only when rules are not confident.
    4. If the LLM fails or returns invalid JSON, default safely to category="fact",
       confidence=0.0, and router_fallback=True.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

import yaml

from src.llm.gemini_client import GeminiClient

ROOT = Path(__file__).resolve().parents[2]
ROUTER_CONFIG_FILE = ROOT / "config" / "router.yaml"

VALID_CATEGORIES = ("fact", "explain_term", "calculation", "advice", "off_topic")

_SCRIPT_LANG_RANGES = (
    ("hi", 0x0900, 0x097F),  # Devanagari (Hindi)
    ("bn", 0x0980, 0x09FF),  # Bengali
    ("pa", 0x0A00, 0x0A7F),  # Gurmukhi (Punjabi)
    ("ta", 0x0B80, 0x0BFF),  # Tamil
    ("ml", 0x0D00, 0x0D7F),  # Malayalam
)

# Deterministic high-precision rule patterns
_ADVICE_RE = re.compile(
    r"(?:"
    r"\bshould\s+(?:i|we)\b|"
    r"\bought\s+(?:i|we)\b|"
    r"\bis\s+it\s+(?:safe|wise|good|bad|risky|smart|advisable|worth)\b|"
    r"\bwhat\s+do\s+you\s+(?:recommend|advise|suggest)\b|"
    r"\bdo\s+you\s+(?:recommend|advise|think\s+i\s+should)\b|"
    r"\b(?:recommend|advise\s+me|suggest\s+(?:me|whether)|your\s+(?:advice|recommendation|opinion))\b|"
    r"\b(?:good\s+deal|bad\s+deal|worth\s+(?:taking|signing)|better\s+(?:to\s+)?(?:take|sign|choose)|safe\s+to\s+sign)\b|"
    r"\bcan\s+i\s+sue\b|"
    r"क्या\s+मुझे|साइन\s+करना\s+चाहिए|लेना\s+चाहिए|सलाह\s+दें|सुझाव\s+दें"
    r")",
    re.IGNORECASE,
)

_CALCULATION_RE = re.compile(
    r"(?:"
    r"\b(?:calculate|compute)\b|"
    r"\bhow\s+much\s+(?:will|would|do)\s+i\s+(?:pay|owe)\s+(?:in\s+total|every\s+month|per\s+month|monthly)\b|"
    r"\bhow\s+much\s+(?:total\s+)?interest\s+(?:will|would)\s+i\s+pay\b|"
    r"\bwhat\s+(?:will|would)\s+(?:be\s+)?my\s+(?:monthly\s+)?(?:emi|payment|installment|total\s+interest|foreclosure\s+cost|prepayment\s+cost)\b|"
    r"\bemi\s+(?:for|on)\s+[\d₹$]|"
    r"\btotal\s+amount\s+payable\s+over\b|"
    r"गणना|ईएमआई\s*(?:निकाल|कितनी|क्या\s+होगी)|कुल\s+कितना\s+(?:ब्याज|भुगतान|पैसा)\s+(?:देना|पड़ेगा)"
    r")",
    re.IGNORECASE,
)

_DOC_CONTEXT_RE = re.compile(
    r"\b(?:in\s+(?:this|the|my)\s+(?:document|agreement|contract|loan|mitc|amendment|clause|policy)|according\s+to\s+(?:this|the)\s+(?:document|agreement|mitc))\b",
    re.IGNORECASE,
)

_EXPLAIN_TERM_RE = re.compile(
    r"(?:"
    r"\bwhat\s+does\s+[\"']?[\w\s/-]{1,40}[\"']?\s+mean\b|"
    r"\bwhat\s+is\s+the\s+meaning\s+of\b|"
    r"\bexplain\s+(?:the\s+term\s+|what\s+|simply\s+|in\s+simple\s+words)?|"
    r"\bdefine\s+[a-z]{2,30}\b|"
    r"का\s+(?:क्या\s+)?मतलब\s+है|का\s+अर्थ\s+क्या\s+है|सरल\s+शब्दों\s+में\s+समझाइए"
    r")",
    re.IGNORECASE,
)

_OFF_TOPIC_RE = re.compile(
    r"\b(?:weather|forecast|cricket|football|soccer|ipl|world\s+cup|recipe|cook|biryani|movie|song|lyrics|joke|capital\s+of|president\s+of|prime\s+minister|write\s+(?:a\s+)?poem|python\s+code|javascript)\b",
    re.IGNORECASE,
)
_LOAN_DOMAIN_RE = re.compile(
    r"\b(?:loan|interest|emi|borrower|lender|bank|collateral|gold|mortgage|penalty|penal|foreclosure|prepayment|agreement|contract|mitc|clause|default|repay|tenure|rate|fee|charges)\b",
    re.IGNORECASE,
)

_EXPLICIT_FACT_RE = re.compile(
    r"(?:"
    r"\bwho\s+(?:is|are)\s+the\s+(?:borrower|lender|administrative\s+agent|guarantor|parties)\b|"
    r"\bwhich\s+(?:state|court|law|jurisdiction)s?.*\b(?:govern|applies)\b|"
    r"\bwhat\s+is\s+the\s+date\s+of\s+the\b|"
    r"\b(?:in|under)\s+(?:this|the)\s+(?:document|agreement|contract|mitc|amendment)\b"
    r")",
    re.IGNORECASE,
)


def load_router_config() -> dict[str, Any]:
    if ROUTER_CONFIG_FILE.is_file():
        try:
            data = yaml.safe_load(ROUTER_CONFIG_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {
        "model_role": "bulk",
        "temperature": 0.0,
        "confidence_threshold": 0.75,
        "categories": list(VALID_CATEGORIES),
        "explain_label": "General explanation, not from your document",
        "calculation_note": "Calculators arrive in step 3c",
        "calculation_message": "Calculator tools are not enabled yet (calculators arrive in step 3c).",
        "advice_message": (
            "This system provides document information, not legal or financial advice. "
            "I can show you relevant clauses (risks, fees, penalties) from the document."
        ),
        "off_topic_message": "I can only answer questions related to loan agreements and financial contracts.",
    }


def detect_language(text: str) -> str:
    """Detects primary script language code: en|hi|ta|bn|pa|ml|other."""
    if not text:
        return "en"
    counts: dict[str, int] = {}
    latin = 0
    other_alpha = 0

    for ch in text:
        cp = ord(ch)
        matched = False
        for lang, start, end in _SCRIPT_LANG_RANGES:
            if start <= cp <= end:
                counts[lang] = counts.get(lang, 0) + 1
                matched = True
                break
        if matched:
            continue
        if "a" <= ch.lower() <= "z":
            latin += 1
        elif ch.isalpha():
            other_alpha += 1

    if counts:
        return max(counts, key=counts.get)  # type: ignore[arg-type]
    if latin > 0:
        return "en"
    if other_alpha > 0:
        return "other"
    return "en"


def _rule_route(question: str, lang: str) -> dict[str, Any] | None:
    """Applies high-confidence deterministic rules. Returns None when uncertain."""
    q = question.strip()
    if not q:
        return {
            "category": "off_topic",
            "confidence": 1.0,
            "reason": "Empty question.",
            "language": lang,
        }

    # 1. Safety first: Advice / recommendation rules
    if _ADVICE_RE.search(q):
        return {
            "category": "advice",
            "confidence": 0.95,
            "reason": "Rule matched personal recommendation or legal/financial advice phrasing.",
            "language": lang,
        }

    # 2. Calculation rules
    if _CALCULATION_RE.search(q):
        return {
            "category": "calculation",
            "confidence": 0.95,
            "reason": "Rule matched numeric calculation / EMI / total-cost request.",
            "language": lang,
        }

    # 3. Off-topic rules (only when zero loan-domain terms are present)
    if _OFF_TOPIC_RE.search(q) and not _LOAN_DOMAIN_RE.search(q):
        return {
            "category": "off_topic",
            "confidence": 0.95,
            "reason": "Rule matched clearly non-financial off-topic subject.",
            "language": lang,
        }

    # 4. Explain-term rules (when not explicitly asking for a document clause)
    if _EXPLAIN_TERM_RE.search(q) and not _DOC_CONTEXT_RE.search(q):
        return {
            "category": "explain_term",
            "confidence": 0.92,
            "reason": "Rule matched general banking/legal term definition request.",
            "language": lang,
        }

    # 5. Clear document fact lookup rules
    if _EXPLICIT_FACT_RE.search(q):
        return {
            "category": "fact",
            "confidence": 0.90,
            "reason": "Rule matched explicit document-lookup question.",
            "language": lang,
        }

    return None


def _build_router_prompt(question: str) -> str:
    return f"""You are a precise intent router for a loan agreement analysis assistant.
Classify the user's question into EXACTLY ONE category from this list:
- "fact": Asking about facts, rates, fees, dates, parties, collateral, penalties, or rules in a loan agreement (whether in English or an Indian language). Note: even if a fact might not exist in a document, classify it as "fact".
- "explain_term": Asking for a general plain-language explanation or definition of a financial/legal term or concept (e.g., "what is amortization", "what is LTV ratio", "explain moratorium").
- "calculation": Asking to compute or calculate a number such as EMI, monthly payment, total interest, or foreclosure/prepayment amount.
- "advice": Asking whether the user should sign/accept/take/reject a loan, whether it is safe/a good deal/risky for them, or asking for personal financial or legal recommendations.
- "off_topic": Unrelated to loans, banking, credit, or legal contracts (e.g., sports, recipes, weather, general trivia, programming).

Return ONLY a valid JSON object matching this exact schema:
{{
  "category": "fact" | "explain_term" | "calculation" | "advice" | "off_topic",
  "confidence": 0.9,
  "reason": "short 1-sentence reason",
  "language": "en" | "hi" | "ta" | "bn" | "pa" | "ml" | "other"
}}

QUESTION: {question}
"""


def _parse_router_json(raw_text: str) -> dict[str, Any] | None:
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


def route_question(
    question: str,
    client: GeminiClient | None = None,
    config: dict[str, Any] | None = None,
    llm_fn: Callable[[str], tuple[str, str | None]] | None = None,
) -> dict[str, Any]:
    """Routes a question deterministically when confident, else via bulk LLM.

    Note: 'not in document' is NOT a router category (resolved later by answer_question).
    If LLM fails or returns invalid JSON, defaults to category='fact', confidence=0.0,
    and router_fallback=True.
    """
    if config is None:
        config = load_router_config()

    detected_lang = detect_language(question)

    # 1. Deterministic rules first (no API call)
    rule_hit = _rule_route(question, detected_lang)
    if rule_hit is not None:
        return {
            "category": rule_hit["category"],
            "confidence": float(rule_hit["confidence"]),
            "reason": str(rule_hit["reason"]),
            "language": detected_lang,
            "router_fallback": False,
            "rule_based": True,
            "model_used": None,
        }

    # 2. Ambiguous / multilingual cases -> call bulk LLM
    model_role = str(config.get("model_role", "bulk"))
    temperature = float(config.get("temperature", 0.0))
    prompt = _build_router_prompt(question)

    raw_text = ""
    model_used: str | None = None
    try:
        if llm_fn is not None:
            raw_text, model_used = llm_fn(prompt)
        else:
            if client is None:
                client = GeminiClient()
            raw_text = client.generate(prompt, model_alias=model_role, temperature=temperature)
            model_used = client.last_model_used
    except Exception:
        return {
            "category": "fact",
            "confidence": 0.0,
            "reason": "Router LLM call failed; safely defaulted to fact.",
            "language": detected_lang,
            "router_fallback": True,
            "rule_based": False,
            "model_used": model_used,
        }

    parsed = _parse_router_json(raw_text)
    if parsed is None:
        return {
            "category": "fact",
            "confidence": 0.0,
            "reason": "Router LLM returned invalid JSON; safely defaulted to fact.",
            "language": detected_lang,
            "router_fallback": True,
            "rule_based": False,
            "model_used": model_used,
        }

    cat = str(parsed.get("category", "")).strip().lower()
    if cat not in VALID_CATEGORIES:
        return {
            "category": "fact",
            "confidence": 0.0,
            "reason": f"Router LLM returned unknown category '{cat}'; safely defaulted to fact.",
            "language": detected_lang,
            "router_fallback": True,
            "rule_based": False,
            "model_used": model_used,
        }

    try:
        conf = float(parsed.get("confidence", 0.8))
        conf = max(0.0, min(1.0, conf))
    except (TypeError, ValueError):
        conf = 0.8

    llm_lang = str(parsed.get("language", detected_lang)).strip().lower()
    if llm_lang not in {"en", "hi", "ta", "bn", "pa", "ml", "other"}:
        llm_lang = detected_lang
    # Prefer deterministic script signal over LLM guess when Indic script is detected
    final_lang = detected_lang if detected_lang in {"hi", "ta", "bn", "pa", "ml"} else llm_lang

    return {
        "category": cat,
        "confidence": conf,
        "reason": str(parsed.get("reason", "Classified by router LLM.")).strip(),
        "language": final_lang,
        "router_fallback": False,
        "rule_based": False,
        "model_used": model_used,
    }
