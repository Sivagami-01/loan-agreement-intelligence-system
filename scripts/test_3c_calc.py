from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.calc import formulas
from src.calc import extract_inputs as input_module
from src.calc.extract_inputs import calculate, extract_inputs
from src.llm.gemini_client import GeminiClient, get_api_key
from src.qa.ask import ask

SEC_DOC = "000010/104897/0000950123-11-030926_2.txt"


def line(label: str, passed: bool, detail: str) -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {label}: {detail}")
    return passed


def test_t1_key_leak_scan() -> tuple[bool, str]:
    api_key = get_api_key()
    if not api_key or len(api_key) < 10:
        return False, "API key unavailable for scan; key value not printed."
    paths = [
        ROOT / "config" / "calc.yaml",
        ROOT / "src" / "calc",
        ROOT / "src" / "qa" / "ask.py",
        ROOT / "scripts" / "demo_calc.py",
        ROOT / "scripts" / "test_3c_calc.py",
        ROOT / "scripts" / "test_2d_router.py",
        ROOT / "docs" / "WORK_REPORT.md",
        ROOT / "data" / "processed" / "llm_log.csv",
    ]
    files = [p for entry in paths for p in (entry.rglob("*") if entry.is_dir() else [entry]) if p.is_file()]
    leaks = sum(api_key in path.read_text(encoding="utf-8", errors="ignore") for path in files)
    return leaks == 0, f"Scanned {len(files)} files; leaks={leaks} (key value withheld)."


def test_t2_formulas() -> tuple[bool, str]:
    checks: list[tuple[str, bool, str]] = []
    payment = formulas.emi("1000000", "12", 12)["result"]
    checks.append(("reference EMI", payment == Decimal("88848.79"), str(payment)))
    zero = formulas.emi("1200", "0", 12)["result"]
    checks.append(("zero-rate loan", zero == Decimal("100.00"), str(zero)))
    schedule = formulas.amortization_schedule("1000000", "12", 12)["result"]
    interest = formulas.total_interest("1000000", "12", 12)["result"]
    total = formulas.total_payment("1000000", "12", 12)["result"]
    balance = formulas.outstanding_after(6, "1000000", "12", 12)["result"]
    checks.append(("schedule ends at zero", schedule[-1]["balance"] == Decimal("0.00"), str(schedule[-1]["balance"])))
    checks.append(("interest equals schedule sum", interest == sum((row["interest"] for row in schedule), Decimal("0")), str(interest)))
    checks.append(("total payment equals schedule", total == sum((row["payment"] for row in schedule), Decimal("0")), str(total)))
    checks.append(("outstanding after payments", balance == schedule[5]["balance"], str(balance)))
    prepay = formulas.prepayment_cost("200000", "2")["result"]
    minimum = formulas.prepayment_cost("1000", "2", "50")["result"]
    checks.append(("prepayment percentage", prepay == Decimal("4000.00"), str(prepay)))
    checks.append(("prepayment minimum", minimum == Decimal("50.00"), str(minimum)))
    penal = formulas.penal_charge("10000", "24", 30)["result"]
    flat_penal = formulas.penal_charge("10000", "0", 30, flat_penal_fee="75")["result"]
    checks.append(("penal simple interest", penal == Decimal("197.26"), str(penal)))
    checks.append(("flat penal fee", flat_penal == Decimal("75.00"), str(flat_penal)))
    monthly = formulas.interest_only_monthly("100000", "12")["result"]
    checks.append(("interest-only monthly", monthly == Decimal("1000.00"), str(monthly)))
    flat = formulas.flat_rate_total_interest("1000000", "12", "1")["result"]
    reducing = formulas.total_interest("1000000", "12", 12)["result"]
    checks.append(("flat higher than reducing", flat > reducing, f"flat={flat}; reducing={reducing}"))
    schedule_total = sum((row["payment"] for row in schedule), Decimal("0"))
    checks.append(("EMI total property", abs(payment * 12 - schedule_total) < Decimal("1"), f"emi*n={payment * 12}; schedule={schedule_total}"))
    failures = [f"{name}={detail}" for name, passed, detail in checks if not passed]
    return not failures, "; ".join(f"{name}={detail}" for name, _, detail in checks)


def test_t3_input_extraction() -> tuple[bool, str]:
    parsed = extract_inputs("Calculate EMI for Rs 5 lakh at 9% for 2 years")
    good = (
        parsed["calculation"] == "emi"
        and parsed["inputs"]["principal"]["value"] == Decimal("500000")
        and parsed["inputs"]["annual_rate_pct"]["value"] == Decimal("9")
        and parsed["inputs"]["months"]["value"] == 24
        and not parsed["missing"]
    )
    hindi = extract_inputs("५ लाख रुपये पर ९% ब्याज से २ years की EMI")
    hindi_good = (
        hindi["inputs"].get("principal", {}).get("value") == Decimal("500000")
        and hindi["inputs"].get("annual_rate_pct", {}).get("value") == Decimal("9")
        and hindi["inputs"].get("months", {}).get("value") == 24
    )
    missing = extract_inputs("Calculate EMI for Rs 5 lakh at 9%")
    missing_good = "months" in missing["missing"]

    def fake_wrong_result(prompt: str) -> tuple[str, str]:
        if not prompt:
            raise AssertionError("Expected an input-extraction prompt.")
        return json.dumps({
            "result": 1,
            "inputs": {"annual_rate_pct": {"value": 9, "quote": "9 percent"}},
        }), "fake"

    no_result_injection = extract_inputs(
        "Calculate EMI for Rs 5 lakh at 9 percent for 2 years",
        llm_fn=fake_wrong_result,
    )
    formula_result = calculate(no_result_injection)["result"] if not no_result_injection["missing"] else None
    independent = formula_result == Decimal("22842.37") and formula_result != Decimal("1")

    original = input_module._load_cached_key_info
    original_pages = input_module.load_document
    try:
        input_module._load_cached_key_info = lambda _: {
            "fields": [{
                "field": "loan_or_commitment_amount",
                "status": "verified",
                "value": "500000",
                "evidence": [{"quote": "amount is Rs 500,000", "page": 1, "verified": False}],
            }]
        }
        input_module.load_document = lambda _: ("", {1: "amount is Rs 500,000"})
        refused = extract_inputs("Calculate EMI at 9% for 24 months", doc_id="fake_doc")
        refuses_unverified = "principal" in refused["missing"]
    finally:
        input_module._load_cached_key_info = original
        input_module.load_document = original_pages

    ok = good and hindi_good and missing_good and independent and refuses_unverified
    return ok, (
        f"English={good}, Hindi digits={hindi_good}, no guessed tenure={missing_good}, "
        f"LLM result ignored={independent}, unverified document value refused={refuses_unverified}"
    )


def test_t4_live_ask(client: GeminiClient) -> tuple[bool, str]:
    from scripts.eval_3a_matches import _read_zip_doc_pages

    sec_pages = _read_zip_doc_pages("000010/104897/0000950123-11-030926_2.txt")
    calls_before = client.api_calls_made
    dbs = ask(
        "03_dbs_mitc",
        "Calculate monthly EMI for Rs 500000 at 9% for 24 months",
        client=client,
        verify=True,
    )
    sec = ask(
        SEC_DOC,
        "Calculate monthly EMI at 9% annual rate for 24 months using the principal amount in this agreement",
        client=client,
        verify=True,
        doc_pages=sec_pages,
    )
    calls = client.api_calls_made - calls_before
    dbs_sources = {
        v["source"] for v in dbs.get("inputs", {}).values()
        if isinstance(v, dict) and isinstance(v.get("source"), str)
    }
    sec_sources = {
        v["source"] for v in sec.get("inputs", {}).values()
        if isinstance(v, dict) and isinstance(v.get("source"), str)
    }
    sec_evidence = any(
        v.get("source") == "document" and v.get("quote") and v.get("page") is not None
        for v in sec.get("inputs", {}).values()
        if isinstance(v, dict)
    )
    def input_summary(result: dict[str, Any]) -> str:
        return "; ".join(
            f"{name}={item.get('value')} [{item.get('source')}; quote={item.get('quote')!r}; page={item.get('page')}]"
            for name, item in result.get("inputs", {}).items()
            if isinstance(item, dict)
        )

    passed = (
        dbs.get("category") == "calculation"
        and dbs.get("status") == "ok"
        and dbs_sources == {"user"}
        and sec.get("category") == "calculation"
        and sec.get("status") == "ok"
        and "user" in sec_sources
        and "document" in sec_sources
        and sec_evidence
        and calls <= 15
    )
    detail = (
        f"DBS={dbs.get('status')}/{sorted(dbs_sources)}; SEC={sec.get('status')}/{sorted(sec_sources)}; "
        f"document quote+page={sec_evidence}; calls={calls}/15; "
        f"DBS inputs: {input_summary(dbs)}; SEC inputs: {input_summary(sec)}"
    )
    return passed, detail


def test_t5_2d_compatibility(client: GeminiClient) -> tuple[bool, str]:
    from scripts.test_2d_router import run_t5_ask_live_6_cases

    passed, details, _ = run_t5_ask_live_6_cases(client)
    return passed, details


def test_t6_budget_and_cache(client: GeminiClient) -> tuple[bool, str]:
    from scripts.eval_3a_matches import _read_zip_doc_pages

    sec_pages = _read_zip_doc_pages("000010/104897/0000950123-11-030926_2.txt")
    calls_before = client.api_calls_made
    first = ask(
        SEC_DOC,
        "Calculate monthly EMI at 9% annual rate for 24 months using the principal amount in this agreement",
        client=client,
        verify=True,
        doc_pages=sec_pages,
    )
    first_calls = client.api_calls_made - calls_before
    repeat_before = client.api_calls_made
    repeat = ask(
        SEC_DOC,
        "Calculate monthly EMI at 9% annual rate for 24 months using the principal amount in this agreement",
        client=client,
        verify=True,
        doc_pages=sec_pages,
    )
    repeat_calls = client.api_calls_made - repeat_before
    passed = (
        first.get("status") == "ok"
        and repeat.get("status") == "ok"
        and first_calls <= 15
        and repeat_calls == 0
        and first.get("result") == repeat.get("result")
    )
    return passed, f"first calls={first_calls} (<=15); cached repeat={repeat_calls}; same result={first.get('result') == repeat.get('result')}"


def main() -> None:
    print("=" * 84)
    print("TEST SUITE: STAGE 3c (DETERMINISTIC LOAN CALCULATORS)")
    print("=" * 84)
    checks = [
        ("T1 key leak scan", *test_t1_key_leak_scan()),
        ("T2 Decimal formula unit tests (0 API calls)", *test_t2_formulas()),
        ("T3 input extraction / fake LLM (0 API calls)", *test_t3_input_extraction()),
    ]
    for label, passed, detail in checks:
        line(label, passed, detail)

    client = GeminiClient()
    live_results = [
        ("T4 live ask() / cached extraction", test_t4_live_ask(client)),
        ("T5 2d six-case compatibility and advice isolation", test_t5_2d_compatibility(client)),
        ("T6 call budget and cached repeat", test_t6_budget_and_cache(client)),
    ]
    for label, result in live_results:
        line(label, result[0], result[1])
    overall = all(passed for _, passed, _ in checks) and all(result[0] for _, result in live_results)
    print("=" * 84)
    print(f"OVERALL RESULT: {'PASS' if overall else 'FAIL'}")
    print("=" * 84)
    if not overall:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
