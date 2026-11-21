from __future__ import annotations

import json
import json
import re
import unicodedata
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable

import yaml

from src.extract.extract_fields import extract_key_info, load_extract_config
from src.llm.gemini_client import GeminiClient
from src.calc import formulas
from src.qa.doc_loader import load_document

ROOT = Path(__file__).resolve().parents[2]
CALC_CONFIG = ROOT / "config" / "calc.yaml"
CACHED_KEY_INFO = ROOT / "data" / "processed" / "extract_3a_eval_snapshot.json"
_DIGIT_MAP = str.maketrans("०१२३४५६७८९", "0123456789")


def _normalize_digits(text: str) -> str:
    return unicodedata.normalize("NFKC", text).translate(_DIGIT_MAP)


def _number(text: str) -> Decimal | None:
    value = text.replace(",", "").strip()
    try:
        return Decimal(value)
    except Exception:
        return None


def _amount_value(number: str, unit: str) -> Decimal | None:
    value = _number(number)
    if value is None:
        return None
    multiplier = {
        "lakh": Decimal("100000"), "lakhs": Decimal("100000"), "lac": Decimal("100000"),
        "लाख": Decimal("100000"), "crore": Decimal("10000000"), "crores": Decimal("10000000"),
        "cr": Decimal("10000000"), "करोड़": Decimal("10000000"),
    }.get(unit.lower(), Decimal("1"))
    return value * multiplier


def _operation(question: str) -> str:
    low = question.lower()
    if re.search(r"\b(?:prepay|prepayment|foreclosure|foreclose)\b", low):
        return "prepayment_cost"
    if re.search(r"\b(?:penal|penalty|overdue|late fee|late charge)\b", low):
        return "penal_charge"
    if re.search(r"\b(?:interest.only|bullet repayment|monthly interest)\b", low):
        return "interest_only_monthly"
    if "flat rate" in low:
        return "flat_rate_total_interest"
    if re.search(r"\b(?:outstanding|balance after)\b", low):
        return "outstanding_after"
    if re.search(r"\btotal interest\b", low):
        return "total_interest"
    if re.search(r"\b(?:total payment|pay in total|total amount paid)\b", low):
        return "total_payment"
    return "emi"


def _load_config() -> dict[str, Any]:
    data = yaml.safe_load(CALC_CONFIG.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def _rule_inputs(question: str) -> tuple[str, dict[str, dict[str, Any]], list[str]]:
    text = _normalize_digits(question)
    operation = _operation(text)
    inputs: dict[str, dict[str, Any]] = {}
    flags: list[str] = []
    currency: str | None = None
    currency_match = re.search(r"(?:\b(?:rs\.?|inr|rupees?)\b|₹|रुपये|रुपए|रु\.?)", text, re.IGNORECASE)
    if currency_match:
        currency = "INR"
    elif re.search(r"(?:\busd\b|\bdollars?\b|\$)", text, re.IGNORECASE):
        currency = "USD"

    amount_pattern = re.compile(
        r"(?:(?:rs\.?|inr|rupees?|₹|\$|usd|dollars?)\s*)?"
        r"(\d[\d,]*(?:\.\d+)?)\s*(lakh|lakhs|lac|crore|crores|cr|लाख|करोड़)?",
        re.IGNORECASE,
    )
    amounts: list[tuple[Decimal, int, int, str]] = []
    for match in amount_pattern.finditer(text):
        number = match.group(1)
        unit = match.group(2) or ""
        before = text[max(0, match.start() - 24):match.start()].lower()
        after = text[match.end():match.end() + 16].lower()
        if not number or (
            not unit
            and not re.search(
                r"(?:rs\.?|inr|rupees?|₹|\$|usd|dollars?|रुपये|रुपए|रु\.?)",
                match.group(0),
                re.IGNORECASE,
            )
        ):
            continue
        amount = _amount_value(number, unit)
        if amount is not None:
            amounts.append((amount, match.start(), match.end(), before + " " + after))

    for index, (amount, _start, _end, context) in enumerate(amounts):
        key: str | None = None
        if re.search(r"\b(?:overdue|late|penal)\b", context):
            key = "overdue_amount"
        elif re.search(r"\b(?:prepay|prepayment|foreclosure|foreclose)\b", context):
            key = "prepaid_amount"
        elif operation == "penal_charge" and index == len(amounts) - 1:
            key = "overdue_amount"
        elif operation == "prepayment_cost" and index == len(amounts) - 1:
            key = "prepaid_amount"
        elif operation in {"emi", "total_interest", "total_payment", "outstanding_after", "interest_only_monthly", "flat_rate_total_interest"} and "principal" not in inputs:
            key = "principal"
        if key and key not in inputs:
            inputs[key] = {"value": amount, "source": "user", "quote": text[_start:_end].strip(), "page": None}

    percent_matches = list(re.finditer(r"(\d+(?:\.\d+)?)\s*(%|percent\b|pct\b)", text, re.IGNORECASE))
    for match in percent_matches:
        rate = _number(match.group(1))
        if rate is None:
            continue
        context = text[max(0, match.start() - 35):match.end() + 28].lower()
        key = "charge_pct" if operation == "prepayment_cost" else "annual_penal_rate_pct" if operation == "penal_charge" else "flat_rate_pct" if operation == "flat_rate_total_interest" else "annual_rate_pct"
        value = rate
        if operation == "penal_charge" and re.search(r"\bper\s+month\b", context):
            value = rate * Decimal("12")
            flags.append("Monthly penal rate converted to a simple annual rate by multiplying by 12.")
        if key not in inputs:
            inputs[key] = {"value": value, "source": "user", "quote": match.group(0), "page": None}

    term_match = re.search(r"(\d+(?:\.\d+)?)\s*(months?|mos?|years?|yrs?)\b", text, re.IGNORECASE)
    if term_match:
        value = _number(term_match.group(1))
        if value is not None:
            if term_match.group(2).lower().startswith(("year", "yr")):
                if operation == "flat_rate_total_interest":
                    inputs["years"] = {"value": value, "source": "user", "quote": term_match.group(0), "page": None}
                else:
                    value *= Decimal("12")
                    flags.append("Years converted to months by multiplying by 12.")
                    if value != value.to_integral_value():
                        flags.append("Non-integer month term needs clarification.")
                    else:
                        inputs["months"] = {"value": int(value), "source": "user", "quote": term_match.group(0), "page": None}
            else:
                if value != value.to_integral_value():
                    flags.append("Non-integer month term needs clarification.")
                else:
                    inputs["months"] = {"value": int(value), "source": "user", "quote": term_match.group(0), "page": None}

    days_match = re.search(r"(\d+)\s*days?\b", text, re.IGNORECASE)
    if days_match:
        inputs["days"] = {"value": int(days_match.group(1)), "source": "user", "quote": days_match.group(0), "page": None}
    k_match = re.search(r"\b(?:after|following)\s+(\d+)\s+(?:payments?|months?)\b", text, re.IGNORECASE)
    if k_match:
        inputs["k_payments"] = {"value": int(k_match.group(1)), "source": "user", "quote": k_match.group(0), "page": None}
    fee_match = re.search(r"\b(?:minimum(?:\s+charge)?|flat\s+(?:penal\s+)?fee)\s*(?:of|is|:)?\s*(?:rs\.?|inr|₹|\$)?\s*(\d[\d,]*(?:\.\d+)?)", text, re.IGNORECASE)
    if fee_match:
        fee_key = "flat_penal_fee" if operation == "penal_charge" else "minimum_charge"
        inputs[fee_key] = {"value": _number(fee_match.group(1)), "source": "user", "quote": fee_match.group(0).strip(), "page": None}

    if currency:
        inputs["currency"] = {"value": currency, "source": "user", "quote": currency_match.group(0) if currency_match else "$", "page": None}
    return operation, inputs, flags


def _required(operation: str) -> list[str]:
    return {
        "emi": ["principal", "annual_rate_pct", "months"],
        "total_interest": ["principal", "annual_rate_pct", "months"],
        "total_payment": ["principal", "annual_rate_pct", "months"],
        "outstanding_after": ["principal", "annual_rate_pct", "months", "k_payments"],
        "prepayment_cost": ["prepaid_amount", "charge_pct"],
        "penal_charge": ["overdue_amount", "annual_penal_rate_pct", "days"],
        "interest_only_monthly": ["principal", "annual_rate_pct"],
        "flat_rate_total_interest": ["principal", "flat_rate_pct", "years"],
    }[operation]


def _load_cached_key_info(doc_id: str) -> dict[str, Any] | None:
    if not CACHED_KEY_INFO.is_file():
        return None
    cached = json.loads(CACHED_KEY_INFO.read_text(encoding="utf-8"))
    if not isinstance(cached, dict):
        return None
    normalized_id = doc_id.replace("\\", "/").lstrip("/").casefold()
    exact = cached.get(normalized_id)
    if isinstance(exact, dict):
        return exact
    matches = [
        value for key, value in cached.items()
        if isinstance(key, str)
        and (key.replace("\\", "/").lstrip("/").casefold().endswith("/" + normalized_id)
             or normalized_id.endswith("/" + key.replace("\\", "/").lstrip("/").casefold()))
        and isinstance(value, dict)
    ]
    return matches[0] if len(matches) == 1 else None


def _document_inputs(
    doc_id: str,
    client: GeminiClient | None,
    doc_pages: dict[int, str] | None = None,
) -> dict[str, dict[str, Any]]:
    extracted = _load_cached_key_info(doc_id)
    if extracted is None:
        extraction_config = load_extract_config()
        extraction_config["max_calls_per_doc"] = min(
            int(extraction_config.get("max_calls_per_doc", 16)),
            int(_load_config().get("max_live_calls", 15)),
        )
        extracted = extract_key_info(
            doc_id=doc_id,
            doc_pages=doc_pages,
            client=client,
            config=extraction_config,
            verify_numeric=False,
        )
    if not isinstance(extracted, dict):
        return {}
    if doc_pages is None:
        _, doc_pages = load_document(doc_id)
    if not doc_pages:
        return {}
    mapped_fields = {
        "principal": "loan_or_commitment_amount",
        "annual_rate_pct": "interest_rate",
        "months": "maturity_termination_date",
        "charge_pct": "prepayment_terms",
        "annual_penal_rate_pct": "late_payment_or_default_interest",
    }
    found: dict[str, dict[str, Any]] = {}
    for field in extracted.get("fields", []):
        if not isinstance(field, dict) or field.get("status") != "verified":
            continue
        evidence = field.get("evidence")
        if not isinstance(evidence, list):
            continue
        verified = None
        for item in evidence:
            if not isinstance(item, dict) or item.get("verified", True) is not True:
                continue
            quote = str(item.get("quote", "")).strip()
            page_value = item.get("page")
            if not isinstance(page_value, (int, str)) or isinstance(page_value, bool):
                continue
            try:
                page = int(page_value)
            except (TypeError, ValueError):
                continue
            if (
                quote
                and page in doc_pages
                and re.sub(r"\s+", " ", quote).strip()
                in re.sub(r"\s+", " ", doc_pages[page]).strip()
            ):
                verified = item
                break
        if verified is None:
            continue
        for input_name, field_name in mapped_fields.items():
            if field.get("field") == field_name:
                raw_value = str(field.get("value", "")).strip()
                numeric_match = re.search(r"\d[\d,]*(?:\.\d+)?", _normalize_digits(raw_value))
                if numeric_match is None:
                    continue
                numeric_value = _number(numeric_match.group(0))
                if numeric_value is None:
                    continue
                if input_name in {"annual_rate_pct", "charge_pct", "annual_penal_rate_pct"}:
                    percentages = re.findall(r"\d+(?:\.\d+)?\s*%", raw_value)
                    if not percentages or len(percentages) != 1:
                        continue
                    if input_name == "annual_rate_pct" and re.search(
                        r"\b(?:sofr|libor|repo|benchmark|base rate|reference rate|applicable margin|spread)\b",
                        raw_value,
                        re.IGNORECASE,
                    ):
                        continue
                    numeric_value = _number(percentages[0].replace("%", "").strip())
                    quote_percentages = re.findall(r"\d+(?:\.\d+)?\s*%", str(verified["quote"]))
                    quote_rate = (
                        _number(quote_percentages[0].replace("%", "").strip())
                        if len(quote_percentages) == 1
                        else None
                    )
                    if numeric_value is None or quote_rate != numeric_value:
                        continue
                if input_name == "months":
                    term = re.search(
                        r"(\d+)\s*(months?|mos?|years?|yrs?)\b",
                        _normalize_digits(raw_value),
                        re.IGNORECASE,
                    )
                    if term is None:
                        continue
                    numeric_value = _number(term.group(1))
                    if numeric_value is None:
                        continue
                    if term.group(2).lower().startswith(("year", "yr")):
                        numeric_value *= Decimal("12")
                found[input_name] = {
                    "value": int(numeric_value) if input_name == "months" else numeric_value,
                    "source": "document",
                    "quote": str(verified["quote"]),
                    "page": int(verified["page"]),
                }
                amount_text = raw_value + " " + str(verified["quote"])
                if re.search(r"(?:\brs\.?\b|\binr\b|₹)", amount_text, re.IGNORECASE):
                    found.setdefault("currency", {
                        "value": "INR",
                        "source": "document",
                        "quote": str(verified["quote"]),
                        "page": int(verified["page"]),
                    })
                elif re.search(r"(?:\busd\b|\$)", amount_text, re.IGNORECASE):
                    found.setdefault("currency", {
                        "value": "USD",
                        "source": "document",
                        "quote": str(verified["quote"]),
                        "page": int(verified["page"]),
                    })
    return found


def _llm_inputs(
    question: str,
    missing: list[str],
    client: GeminiClient | None,
    llm_fn: Callable[[str], tuple[str, str]] | None,
    config: dict[str, Any],
) -> dict[str, Any]:
    prompt = (
        "Map only explicitly stated numeric text in the question to calculator inputs. "
        "Do not calculate or return a result. Do not guess missing values. "
        "For each input return both its value and an exact quote copied from the question. "
        f"Allowed input names: {', '.join(missing)}. "
        "Return {\"inputs\": {\"name\": {\"value\": number, \"quote\": \"exact text\"}}} only.\n\n"
        f"Question: {question}"
    )
    if llm_fn is not None:
        raw, _ = llm_fn(prompt)
    else:
        if client is None:
            client = GeminiClient()
        raw = client.generate(
            prompt,
            model_alias=str(config.get("model_role", "bulk")),
            temperature=float(config.get("temperature", 0.0)),
        )
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    values = parsed.get("inputs", {}) if isinstance(parsed, dict) else {}
    if not isinstance(values, dict):
        return {}
    question_normalized = _normalize_digits(question)
    accepted: dict[str, Any] = {}
    for name in missing:
        item = values.get(name)
        if not isinstance(item, dict):
            continue
        quote = str(item.get("quote", "")).strip()
        if not quote or _normalize_digits(quote) not in question_normalized:
            continue
        raw_value = item.get("value")
        value = _number(str(raw_value)) if isinstance(raw_value, (str, int, float)) and not isinstance(raw_value, bool) else None
        if value is None:
            continue
        quoted = _normalize_digits(quote)
        number_match = re.search(r"\d[\d,]*(?:\.\d+)?", quoted)
        if number_match is None:
            continue
        quoted_number = _number(number_match.group(0))
        if quoted_number is None:
            continue
        if name in {"annual_rate_pct", "charge_pct", "annual_penal_rate_pct", "flat_rate_pct"}:
            if not re.search(r"%|\bpercent\b|\bpct\b", quoted, re.IGNORECASE) or value != quoted_number:
                continue
        elif name == "months":
            expected = quoted_number * Decimal("12") if re.search(r"\byears?\b|\byrs?\b", quoted, re.IGNORECASE) else quoted_number
            if value != expected:
                continue
            value = int(value)
        elif name in {"days", "k_payments"}:
            if value != quoted_number:
                continue
            value = int(value)
        else:
            unit_match = re.search(r"\b(lakh|lakhs|lac|crore|crores|cr|लाख|करोड़)\b", quoted, re.IGNORECASE)
            multiplier = _amount_value("1", unit_match.group(1)) if unit_match else Decimal("1")
            if multiplier is None:
                continue
            expected = quoted_number * multiplier
            if value != expected:
                continue
        accepted[name] = {"value": value, "source": "user", "quote": quote, "page": None}
    return accepted


def extract_inputs(
    question: str,
    doc_id: str | None = None,
    client: GeminiClient | None = None,
    llm_fn: Callable[[str], tuple[str, str]] | None = None,
    doc_pages: dict[int, str] | None = None,
) -> dict[str, Any]:
    """Extract calculation inputs, preferring explicit user values over verified document facts."""
    config = _load_config()
    operation, inputs, flags = _rule_inputs(question)
    required = _required(operation)
    if operation == "penal_charge" and "flat_penal_fee" in inputs and "annual_penal_rate_pct" not in inputs:
        required = ["overdue_amount", "days"]
    missing = [name for name in required if name not in inputs]

    if missing and doc_id:
        for name, value in _document_inputs(doc_id, client, doc_pages).items():
            if name in missing and value.get("value") not in (None, ""):
                inputs[name] = value
            elif name == "currency" and "currency" not in inputs:
                inputs[name] = value
        missing = [name for name in required if name not in inputs]

    if missing and (llm_fn is not None or client is not None):
        llm_values = _llm_inputs(question, missing, client, llm_fn, config)
        for name, value in llm_values.items():
            inputs[name] = value
        missing = [name for name in required if name not in inputs]

    return {
        "calculation": operation,
        "inputs": inputs,
        "missing": missing,
        "flags": flags,
    }


def calculate(
    extracted: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the selected pure-Python calculator on already extracted inputs."""
    settings = config if config is not None else _load_config()
    values = {
        name: item["value"]
        for name, item in extracted["inputs"].items()
        if isinstance(item, dict) and "value" in item
    }
    currency = values.get("currency")
    decimals = int(settings.get("rounding_decimals", 2))
    operation = extracted["calculation"]
    if operation == "emi":
        return formulas.emi(values["principal"], values["annual_rate_pct"], int(values["months"]), currency, decimals)
    if operation == "total_interest":
        return formulas.total_interest(values["principal"], values["annual_rate_pct"], int(values["months"]), currency, decimals)
    if operation == "total_payment":
        return formulas.total_payment(values["principal"], values["annual_rate_pct"], int(values["months"]), currency, decimals)
    if operation == "outstanding_after":
        return formulas.outstanding_after(int(values["k_payments"]), values["principal"], values["annual_rate_pct"], int(values["months"]), currency, decimals)
    if operation == "prepayment_cost":
        return formulas.prepayment_cost(values["prepaid_amount"], values["charge_pct"], values.get("minimum_charge", 0), currency, decimals)
    if operation == "penal_charge":
        return formulas.penal_charge(
            values["overdue_amount"],
            values.get("annual_penal_rate_pct", 0),
            int(values["days"]),
            int(values.get("day_count", settings.get("default_day_count", 365))),
            values.get("flat_penal_fee", 0),
            currency,
            decimals,
        )
    if operation == "interest_only_monthly":
        return formulas.interest_only_monthly(values["principal"], values["annual_rate_pct"], currency, decimals)
    if operation == "flat_rate_total_interest":
        return formulas.flat_rate_total_interest(values["principal"], values["flat_rate_pct"], values["years"], currency, decimals)
    raise ValueError(f"Unsupported calculation type: {operation}")
