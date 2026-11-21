"""scripts/test_2c1_qa.py

Test Suite for Stage 2c-1: Single-Prompt QA with Verbatim Verification.
Verifies:
T1: Imports work and no API key appears in any output, cache, or log file.
T2: Verifier unit tests (no API calls):
    - exact quote PASS
    - changed word FAIL-as-expected (rejected)
    - quote on wrong page gets corrected (flag: page_corrected)
    - extra spaces/newlines still match
    - a Hindi quote matches after NFC
T3: Oversized-document test returns needs_retrieval without calling the API.
T4: Live test on 3 documents (English SEC agreement, Indian English MITC, Hindi MITC):
    - 8 fact questions + 4 not-in-document questions (max 15 API calls, cached).
T5: Report real numbers:
    - JSON valid rate (target 100%)
    - verified-quote rate (target 99%+, pass threshold >= 95%)
    - correct-page rate
    - correct 'not found' rate (target 90%+, pass threshold >= 3 of 4)
    - PASS if no crashes, JSON valid 100%, verified quote rate >= 95%, at least 3/4 not-found correct.
"""

from __future__ import annotations

import csv
import json
import os
import sys
import unicodedata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.llm.gemini_client import GeminiClient, get_api_key
from src.qa.verify_quotes import normalize, verify_evidence
from src.qa.answer import answer_question, load_qa_config

LOG_FILE = ROOT / "data" / "processed" / "llm_log.csv"
CACHE_DIR = ROOT / "data" / "processed" / "cache" / "gemini"


def test_t1_imports_and_key_safety() -> tuple[bool, str]:
    """T1: imports work and no API key appears in any output, cache or log file."""
    try:
        api_key = get_api_key()
    except Exception as exc:
        return False, f"Could not obtain API key: {exc}"

    if not api_key or len(api_key) < 10:
        return False, "API key is missing or suspiciously short."

    # Inspect all data, log, and cache files
    files_to_scan = [LOG_FILE, ROOT / "config" / "qa.yaml"]
    if CACHE_DIR.is_dir():
        files_to_scan.extend(list(CACHE_DIR.glob("*.json")))

    leak_count = 0
    scanned_count = 0
    for f in files_to_scan:
        if f.is_file():
            scanned_count += 1
            content = f.read_text(encoding="utf-8", errors="ignore")
            if api_key in content:
                leak_count += 1

    if leak_count > 0:
        return False, f"CRITICAL: API key found logged in {leak_count} file(s)!"

    return True, f"Imports successful, API key verified safe (length: {len(api_key)}, leaks: 0 across {scanned_count} files)"


def test_t2_verifier_unit_tests() -> tuple[bool, str]:
    """T2: verifier unit tests (no API calls):

    - exact quote PASS
    - changed word FAIL-as-expected
    - quote on wrong page gets corrected
    - extra spaces/newlines still match
    - a Hindi quote matches after NFC
    """
    pages = {
        1: "The Borrower shall repay the loan in 36 monthly installments of $500 each.",
        2: "Governing Law: This Agreement shall be construed in accordance with the laws of New York.",
        3: unicodedata.normalize("NFC", "ब्याज दर प्रति वर्ष 8.50% तय की गई है।"),
    }

    # 1. Exact quote
    ev1 = [{"quote": "36 monthly installments of $500 each", "page": 1}]
    v1, f1 = verify_evidence(pages, ev1)
    if not (len(v1) == 1 and v1[0]["page"] == 1 and not f1):
        return False, f"T2.1 (exact quote) failed: {v1}"

    # 2. Changed word (must be rejected)
    ev2 = [{"quote": "36 yearly installments of $500 each", "page": 1}]
    v2, f2 = verify_evidence(pages, ev2)
    if len(v2) != 0:
        return False, f"T2.2 (changed word rejection) failed: {v2}"

    # 3. Quote on wrong page gets corrected
    ev3 = [{"quote": "laws of New York", "page": 1}]  # Actually on page 2
    v3, f3 = verify_evidence(pages, ev3)
    if not (len(v3) == 1 and v3[0]["page"] == 2 and "page_corrected" in f3):
        return False, f"T2.3 (page correction) failed: {v3}, flags: {f3}"

    # 4. Extra spaces / newlines still match
    ev4 = [{"quote": "The  Borrower\n\nshall   repay\t the loan", "page": 1}]
    v4, f4 = verify_evidence(pages, ev4)
    if len(v4) != 1 or v4[0]["page"] != 1:
        return False, f"T2.4 (extra spaces/newlines) failed: {v4}"

    # 5. Hindi quote matches after NFC
    hin_nfd_quote = unicodedata.normalize("NFD", "ब्याज दर प्रति वर्ष 8.50%")
    ev5 = [{"quote": hin_nfd_quote, "page": 3}]
    v5, f5 = verify_evidence(pages, ev5)
    if len(v5) != 1 or v5[0]["page"] != 3:
        return False, f"T2.5 (Hindi quote NFC) failed: {v5}"

    return True, "All 5 verifier unit tests passed (exact quote, rejection, page correction, whitespace, NFC)"


def test_t3_oversized_document_guardrail() -> tuple[bool, str]:
    """T3: oversized-document test returns needs_retrieval without calling the API."""
    client = GeminiClient()
    initial_api_calls = client.api_calls_made

    # Test with custom config where max chars is artificially small (e.g. 100 chars)
    # on an ingested document of > 10,000 chars
    mock_config = {
        "max_doc_chars_for_whole_doc": 100,
        "temperature": 0.0,
        "model_role": "main",
    }

    res = answer_question("03_dbs_mitc", "What is the interest rate?", client=client, config=mock_config)

    api_calls_after = client.api_calls_made
    new_calls = api_calls_after - initial_api_calls

    if res.get("status") != "needs_retrieval":
        return False, f"Expected status 'needs_retrieval', got: {res.get('status')}"

    if new_calls != 0:
        return False, f"Oversized document test made {new_calls} API calls; expected 0 calls!"

    return True, f"Oversized document successfully returned 'needs_retrieval' with 0 API calls (guardrail works)"


def run_t4_and_t5_live_qa_test() -> tuple[bool, str, dict[str, Any]]:
    """T4 & T5: Live test on 3 documents (one English SEC agreement, one Indian English MITC, one Hindi MITC).

    8 fact questions + 4 not-in-document questions.
    """
    client = GeminiClient()
    initial_api_calls = client.api_calls_made

    test_cases: list[dict[str, Any]] = [
        # --- Document 1: English SEC Agreement ---
        {
            "doc_id": "0000027430-25-000005_aesohio10qex10120250630q2",
            "type": "fact",
            "question": "Who is the Borrower in this First Amendment?",
            "expected_contains": ["dayton power", "aes ohio"],
        },
        {
            "doc_id": "0000027430-25-000005_aesohio10qex10120250630q2",
            "type": "fact",
            "question": "What is the date of the original Term Loan Agreement referenced in Recital A?",
            "expected_contains": ["august 14, 2024", "august 14 2024"],
        },
        {
            "doc_id": "0000027430-25-000005_aesohio10qex10120250630q2",
            "type": "fact",
            "question": "Which state's laws govern this Amendment?",
            "expected_contains": ["new york"],
        },
        # --- Document 2: Indian English MITC ---
        {
            "doc_id": "03_dbs_mitc",
            "type": "fact",
            "question": "What collateral or security is deposited for this facility?",
            "expected_contains": ["gold", "ornaments"],
        },
        {
            "doc_id": "03_dbs_mitc",
            "type": "fact",
            "question": "What are the two types of interest rate mentioned in the document?",
            "expected_contains": ["fixed", "floating"],
        },
        {
            "doc_id": "03_dbs_mitc",
            "type": "fact",
            "question": "Are prepayment or foreclosure charges levied on floating interest rate loans?",
            "expected_contains": ["no", "prepayment", "floating"],
        },
        # --- Document 3: Hindi MITC ---
        {
            "doc_id": "13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi",
            "type": "fact",
            "question": "अगर ब्याज दर में बदलाव उधारकर्ता के प्रतिकूल है तो वह कितने दिनों के भीतर बिना किसी अतिरिक्त शुल्क के लोन खाता बंद कर सकता है?",
            "expected_contains": ["60"],
        },
        {
            "doc_id": "13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi",
            "type": "fact",
            "question": "बैंक हॉलिडे के कारण पेमेंट क्रेडिट होने में T+ कितने दिनों से अधिक का समय लग सकता है?",
            "expected_contains": ["t+1", "1"],
        },
        # --- 4 Questions NOT in the document ---
        {
            "doc_id": "0000027430-25-000005_aesohio10qex10120250630q2",
            "type": "not_found",
            "question": "What is the annual interest rate percentage for this loan?",
        },
        {
            "doc_id": "03_dbs_mitc",
            "type": "not_found",
            "question": "Can Bitcoin or cryptocurrency be accepted as collateral for this loan?",
        },
        {
            "doc_id": "13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi",
            "type": "not_found",
            "question": "What is the penalty fee if the borrower buys property in London?",
        },
        {
            "doc_id": "03_dbs_mitc",
            "type": "not_found",
            "question": "What is the maximum home loan amount allowed under this policy?",
        },
    ]

    crashes = 0
    json_valid_count = 0
    total_quotes = 0
    verified_quotes = 0
    correct_page_quotes = 0
    not_found_correct = 0
    fact_correct = 0
    failed_questions: list[dict[str, Any]] = []

    print("\n--- Running Live 12-Question QA Evaluation ---")
    for idx, tc in enumerate(test_cases, 1):
        doc = tc["doc_id"]
        q = tc["question"]
        q_type = tc["type"]

        try:
            res = answer_question(doc, q, client=client)
        except Exception as exc:
            crashes += 1
            failed_questions.append({
                "index": idx,
                "question": q,
                "doc": doc,
                "reason": f"Crash with exception: {exc}",
            })
            print(f"[{idx}/12] CRASH: {q[:40]}... -> {exc}")
            continue

        status = res.get("status")
        answer = res.get("answer", "")
        evidence = res.get("evidence", [])
        flags = res.get("flags", [])

        # JSON was valid if status is not 'unverified' with 'invalid_json_response'
        is_json_valid = "invalid_json_response" not in flags
        if is_json_valid:
            json_valid_count += 1

        if q_type == "fact":
            # Must have status 'ok' and evidence
            expected = tc.get("expected_contains", [])
            norm_ans = normalize(answer)
            ans_matches = any(normalize(exp) in norm_ans for exp in expected)

            raw_ev = res.get("raw_evidence", evidence)
            raw_count = len(raw_ev)
            ev_count = len(evidence)
            total_quotes += raw_count
            verified_quotes += ev_count

            # Check if any quotes had their page corrected
            for ev in evidence:
                if "page_corrected" not in ev.get("flags", []):
                    correct_page_quotes += 1

            if status == "ok" and ans_matches and ev_count > 0:
                fact_correct += 1
                print(f"[{idx}/12] PASS (Fact): {q[:45]}... -> {answer[:45]}... (Quotes: {ev_count})")
            else:
                failed_questions.append({
                    "index": idx,
                    "question": q,
                    "doc": doc,
                    "status": status,
                    "answer": answer,
                    "reason": f"Status={status}, ans_matches={ans_matches}, quotes={ev_count}",
                })
                print(f"[{idx}/12] FAIL (Fact): {q[:45]}... -> Status={status}, Ans={answer[:45]}")

        elif q_type == "not_found":
            # Must have status 'not_found' or answer contains 'not found'
            is_not_found = (status == "not_found") or ("not found in this document" in normalize(answer))
            if is_not_found:
                not_found_correct += 1
                print(f"[{idx}/12] PASS (Not-Found): {q[:45]}... -> Correctly abstained")
            else:
                failed_questions.append({
                    "index": idx,
                    "question": q,
                    "doc": doc,
                    "status": status,
                    "answer": answer,
                    "reason": f"Expected not_found, got status={status}, answer={answer}",
                })
                print(f"[{idx}/12] FAIL (Not-Found): {q[:45]}... -> Status={status}, Ans={answer[:45]}")

    new_api_calls = client.api_calls_made - initial_api_calls

    json_valid_rate = (json_valid_count / len(test_cases)) * 100
    verified_quote_rate = (verified_quotes / max(1, total_quotes)) * 100
    correct_page_rate = (correct_page_quotes / max(1, total_quotes)) * 100
    not_found_rate = (not_found_correct / 4) * 100

    metrics = {
        "total_questions": len(test_cases),
        "crashes": crashes,
        "new_api_calls": new_api_calls,
        "json_valid_rate": json_valid_rate,
        "verified_quote_rate": verified_quote_rate,
        "correct_page_rate": correct_page_rate,
        "not_found_correct": not_found_correct,
        "not_found_rate": not_found_rate,
        "fact_correct": fact_correct,
        "failed_questions": failed_questions,
    }

    # Pass criteria:
    # 1. crashes == 0
    # 2. JSON valid == 100%
    # 3. verified-quote rate >= 95%
    # 4. at least 3 of 4 not-found correct
    # 5. max 15 API calls
    all_passed = (
        crashes == 0
        and json_valid_rate == 100.0
        and verified_quote_rate >= 95.0
        and not_found_correct >= 3
        and new_api_calls <= 15
    )

    details = (
        f"Crashes: {crashes}, JSON valid: {json_valid_rate:.1f}%, "
        f"Verified quote rate: {verified_quote_rate:.1f}% ({verified_quotes}/{total_quotes}), "
        f"Correct page rate: {correct_page_rate:.1f}%, "
        f"Not-found accuracy: {not_found_correct}/4 ({not_found_rate:.1f}%), "
        f"API calls made: {new_api_calls}"
    )

    return all_passed, details, metrics


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("=" * 80)
    print("TEST SUITE: STAGE 2c-1 (SINGLE-PROMPT QA WITH VERBATIM VERIFICATION)")
    print("=" * 80)

    # T1
    p1, msg1 = test_t1_imports_and_key_safety()
    print(f"[{'PASS' if p1 else 'FAIL'}] T1: Imports & API Key Safety")
    print(f"       Details: {msg1}")

    # T2
    p2, msg2 = test_t2_verifier_unit_tests()
    print(f"[{'PASS' if p2 else 'FAIL'}] T2: Verifier Unit Tests (No API Calls)")
    print(f"       Details: {msg2}")

    # T3
    p3, msg3 = test_t3_oversized_document_guardrail()
    print(f"[{'PASS' if p3 else 'FAIL'}] T3: Oversized Document Guardrail")
    print(f"       Details: {msg3}")

    # T4 & T5
    p4, msg4, metrics = run_t4_and_t5_live_qa_test()
    print(f"[{'PASS' if p4 else 'FAIL'}] T4/T5: Live QA Benchmark & Metrics Report")
    print(f"       Details: {msg4}")

    if metrics.get("failed_questions"):
        print("\n--- Failed Questions Summary ---")
        for fq in metrics["failed_questions"]:
            print(f"  * [Q{fq['index']}] Doc: {fq['doc']}")
            print(f"    Question: {fq['question']}")
            print(f"    Reason:   {fq['reason']}")
    else:
        print("\nAll 12 evaluation questions completed successfully with 0 failures!")

    all_passed = p1 and p2 and p3 and p4
    print("=" * 80)
    print(f"OVERALL RESULT: {'PASS (All quality gates satisfied)' if all_passed else 'FAIL'}")
    print("=" * 80)

    if not all_passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
