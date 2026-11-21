"""scripts/test_5a_numbers.py

Stage 5a: Number, date, and amount checker verification suite.
Validates src/translate/number_check.py (check_numbers) against positive and negative
test cases across Indic scripts (Hindi, Tamil, Bengali, Punjabi, Malayalam),
thousands separator formats, dates, and empty-number text.
Zero Gemini API calls: asserts data/processed/llm_log.csv row count delta == 0.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.translate.number_check import check_numbers

LLM_LOG_PATH = ROOT / "data" / "processed" / "llm_log.csv"


def _count_llm_log_rows() -> int:
    if not LLM_LOG_PATH.is_file():
        return 0
    with LLM_LOG_PATH.open("r", encoding="utf-8", errors="ignore") as fh:
        return sum(1 for _ in fh)


def main() -> int:
    print("=" * 80)
    print("STAGE 5a: NUMBER / DATE / AMOUNT TRANSLATION CHECKER TESTS")
    print("=" * 80)
    print("[NOTICE] All 13 test cases below are hand-written by the builder (optimistic")
    print("synthetic evaluation). This test suite does not represent an independent evaluation")
    print("on wild messy real-world translations. No benchmark target is claimed to be met.\n")

    rows_before = _count_llm_log_rows()

    source_emi = "EMI is Rs. 22842.37 for 24 months at 9%"

    # List of test cases: (id, name, expected_checker_status, source, translation, description)
    test_cases = [
        # Positive cases (must report pass)
        (
            "P1",
            "Hindi (Devanagari digits)",
            "pass",
            source_emi,
            "ईएमआई ९% की दर पर २४ महीनों के लिए २२८४२.३७ रुपये है।",
            "Devanagari script digits for amount (२२८४२.३७), tenure (२४), and rate (९%).",
        ),
        (
            "P2",
            "Tamil (Tamil digits)",
            "pass",
            source_emi,
            "மாதத் தவணை ௯% வட்டியில் ௨௪ மாதங்களுக்கு ரூ. ௨௨௮௪௨.௩௭ ஆகும்.",
            "Tamil script digits for amount (௨௨௮௪௨.௩௭), tenure (௨௪), and rate (௯%).",
        ),
        (
            "P3",
            "Bengali (Bengali digits)",
            "pass",
            source_emi,
            "৯% হারে ২৪ মাসের জন্য মাসিক কিস্তি হলো ২২৮৪২.৩৭ টাকা।",
            "Bengali script digits for amount (২২৮৪২.৩৭), tenure (২৪), and rate (৯%).",
        ),
        (
            "P4",
            "Punjabi (Gurmukhi digits)",
            "pass",
            source_emi,
            "੯% ਦੀ ਦਰ 'ਤੇ ੨੪ ਮਹੀਨਿਆਂ ਲਈ ਈਐਮਆਈ ੨੨੮੪੨.੩੭ ਰੁਪਏ ਹੈ।",
            "Gurmukhi script digits for amount (੨੨੮੪੨.੩੭), tenure (੨੪), and rate (੯%).",
        ),
        (
            "P5",
            "Malayalam (Malayalam digits)",
            "pass",
            source_emi,
            "൯% നിരക്കിൽ ൨൪ മാസത്തേക്ക് ഇഎംഐ ൨൨൮൪൨.൩൭ രൂപയാണ്.",
            "Malayalam script digits for amount (൨൨൮൪൨.൩൭), tenure (൨൪), and rate (൯%).",
        ),
        (
            "P6",
            "Thousands separators: 5,00,000 vs 500000",
            "pass",
            "The approved loan amount is Rs. 5,00,000 only.",
            "स्वीकृत ऋण राशि केवल 500000 रुपये है।",
            "Indian comma separator (5,00,000) matched with unformatted 500000.",
        ),
        (
            "P7",
            "Date token: 15/03/2026",
            "pass",
            "The agreement date is 15/03/2026.",
            "समझौते की तारीख १५/०३/२०२६ है।",
            "Date token 15/03/2026 matched against Devanagari date १५/०३/२०२६.",
        ),
        (
            "P8",
            "No numbers present in text",
            "pass",
            "This loan agreement is governed by the laws of India.",
            "यह ऋण समझौता भारत के कानूनों द्वारा शासित है।",
            "Both source and translation contain 0 numbers; returns empty lists.",
        ),
        # Negative cases (checker must report fail)
        (
            "N1",
            "Rate altered: 9% changed to 19%",
            "fail",
            source_emi,
            "ईएमआई 19% की दर पर 24 महीनों के लिए 22842.37 रुपये है।",
            "Rate 9% was changed to 19% in translation.",
        ),
        (
            "N2",
            "Omission: tenure 24 deleted",
            "fail",
            source_emi,
            "ईएमआई 9% की दर पर 22842.37 रुपये है।",
            "Tenure of 24 months omitted entirely in translation.",
        ),
        (
            "N3",
            "Addition: extra 500 fee added",
            "fail",
            source_emi,
            "ईएमआई 9% की दर पर 24 महीनों के लिए 22842.37 रुपये और 500 शुल्क है।",
            "Extra amount 500 hallucinated into translation.",
        ),
        (
            "N4",
            "Magnitude error: 500000 changed to 50000",
            "fail",
            "The loan amount is 500000.",
            "ऋण राशि 50000 है।",
            "Amount altered by dropping one zero (500000 -> 50000).",
        ),
        (
            "N5",
            "Native digit error: 22842.37 changed to 22843.37",
            "fail",
            source_emi,
            "ईएमआई ९% की दर पर २४ महीनों के लिए २२८४३.३७ रुपये है।",
            "Digit 2 replaced with 3 in Devanagari numeral (२२८४३.३७).",
        ),
    ]

    all_passed = True

    for cid, name, expected_status, src, trans, desc in test_cases:
        res = check_numbers(src, trans)
        actual_status = res.get("status")
        test_ok = (actual_status == expected_status)
        if not test_ok:
            all_passed = False

        status_label = "PASS" if test_ok else "FAIL"
        print(f"[{status_label}] {cid}: {name}")
        print(f"       Description: {desc}")
        print(f"       Source:      {src}")
        print(f"       Translation: {trans}")
        print(f"       Expected:    {expected_status} | Actual: {actual_status}")
        print(f"       Result dict: {res}\n")

    rows_after = _count_llm_log_rows()
    zero_api = (rows_after == rows_before)
    delta = rows_after - rows_before
    print("-" * 80)
    print(f"llm_log.csv rows: {rows_before} -> {rows_after} (delta = {delta})")
    print(f"Zero API calls assertion: {'PASS' if zero_api else 'FAIL'}")
    print("=" * 80)

    overall_ok = all_passed and zero_api
    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
