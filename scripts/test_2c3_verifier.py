"""scripts/test_2c3_verifier.py

Test Suite for Stage 2c-3: Second-Model Answer Verifier & Numeric Grounding.
Verifies:
T1: Imports work; no API key in any output, cache, or log file.
T2: check_numbers unit tests (no API): correct amount found; changed amount missing;
    Devanagari digits; percentage; date in different format reported missing (not guessed);
    text with no numbers returns all_found=True.
T3: Combination-logic unit tests with a fake verifier (no API): all four final_check
    outcomes (verified, needs_review, rejected, unchecked), plus strict rule that an
    unavailable or same-model verifier gives 'unchecked', never 'verified'.
T4: Positive controls (live): 8 correct fact answers from 2c-1 (answers loaded from cache).
    Reports final_check counts and raw fallback counts. PASS if >= 7/8 are not rejected.
T5: Negative controls (live): 8 hand-crafted wrong answers (2 changed number/date,
    2 swapped party/place, 2 opposite meaning, 2 extra unsupported claim) keeping
    original quotes. PASS if >= 6/8 get final_check rejected/needs_review and 0/2
    number/date changes get 'verified'. Prints every wrong answer that slipped through.
T6: API budget (<= 25 calls) & honesty: prints verifier_model_used and
    verifier_independent counts. If every verifier call fell back to answer model,
    prints "WARNING: no independent verifier available" and marks T4 & T5
    "NOT A CROSS-MODEL CHECK".
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.llm.gemini_client import GeminiClient, get_api_key
from src.qa.answer import answer_question, load_document, load_qa_config
from src.qa.check_numbers import check_numbers
from src.qa.verifier import verify_answer

LOG_FILE = ROOT / "data" / "processed" / "llm_log.csv"
GEMINI_CACHE_DIR = ROOT / "data" / "processed" / "cache" / "gemini"
RETRIEVAL_CACHE_DIR = ROOT / "data" / "processed" / "retrieval_cache"


def test_t1_imports_and_key_safety() -> tuple[bool, str]:
    try:
        api_key = get_api_key()
    except Exception as exc:
        return False, f"Failed to read API key: {exc}"

    if not api_key or len(api_key) < 10:
        return False, "API key empty or invalid."

    files_to_scan: list[Path] = [
        LOG_FILE,
        ROOT / "config" / "qa.yaml",
        ROOT / "config" / "retrieval.yaml",
        ROOT / "config" / "verify.yaml",
        ROOT / "config" / "models.yaml",
    ]
    if GEMINI_CACHE_DIR.is_dir():
        files_to_scan.extend(GEMINI_CACHE_DIR.glob("*.json"))
    if RETRIEVAL_CACHE_DIR.is_dir():
        files_to_scan.extend(RETRIEVAL_CACHE_DIR.glob("*.json"))

    leaks = 0
    scanned = 0
    for f in files_to_scan:
        if f.is_file():
            scanned += 1
            if api_key in f.read_text(encoding="utf-8", errors="ignore"):
                leaks += 1

    if leaks > 0:
        return False, f"API key leaked in {leaks} file(s)!"

    return True, f"Imports OK; 0 API key leaks across {scanned} files"


def test_t2_check_numbers_unit_tests() -> tuple[bool, str]:
    doc_pages = {
        1: "The Borrower receives a Term Loan of $5,000,000 at 8.50% per annum dated August 14, 2024.",
        2: "यदि ब्याज दर में बदलाव प्रतिकूल हो तो 60 दिनों के भीतर ऋण खाता बंद किया जा सकता है।",
    }
    ev1 = [{"quote": "Term Loan of $5,000,000 at 8.50% per annum dated August 14, 2024", "page": 1}]
    ev2 = [{"quote": "60 दिनों के भीतर ऋण खाता बंद किया जा सकता है", "page": 2}]

    # 1. Correct amount found (with comma difference: $5000000 vs $5,000,000)
    r1 = check_numbers("The loan amount is $5000000.", ev1, doc_pages)
    if not r1["all_found"]:
        return False, f"T2.1 (correct amount) failed: {r1}"

    # 2. Changed amount missing ($500,000 vs $5,000,000; and $5 vs $50)
    r2 = check_numbers("The loan amount is $500,000.", ev1, doc_pages)
    if r2["all_found"] or "$500000" not in r2["missing"]:
        return False, f"T2.2 (changed amount) failed: {r2}"

    # 3. Devanagari digits converted to 0-9 (६० -> 60)
    r3 = check_numbers("उधारकर्ता ६० दिनों के भीतर खाता बंद कर सकता है।", ev2, doc_pages)
    if not r3["all_found"]:
        return False, f"T2.3 (Devanagari digits) failed: {r3}"

    # 4. Percentage matching (8.5% vs 8.50%)
    r4 = check_numbers("The interest rate is 8.5% annually.", ev1, doc_pages)
    if not r4["all_found"]:
        return False, f"T2.4 (percentage) failed: {r4}"

    # 5. Date in DIFFERENT format reported as missing (NOT guessed!)
    r5 = check_numbers("The agreement was dated 14/08/2024.", ev1, doc_pages)
    if r5["all_found"] or "14/08/2024" not in r5["missing"]:
        return False, f"T2.5 (different date format not guessed) failed: {r5}"

    # 6. Text with no numbers returns all_found=True
    r6 = check_numbers("The agreement is governed by New York law.", ev1, doc_pages)
    if not r6["all_found"] or r6["missing"]:
        return False, f"T2.6 (no numbers) failed: {r6}"

    return True, "All 6 check_numbers unit tests passed (money, changed amount, Devanagari ६०, %, unguessed date format, no numbers)"


def test_t3_combination_logic_unit_tests() -> tuple[bool, str]:
    pages = {1: "The Borrower must repay $1,000 within 60 days with no prepayment penalty."}
    ev = [{"quote": "repay $1,000 within 60 days with no prepayment penalty", "page": 1}]
    q = "What are the repayment terms?"

    def fake_supported(_prompt: str) -> tuple[str, str]:
        return json.dumps({"verdict": "supported", "reason": "Exact match.", "unsupported_parts": []}), "fake-verifier-pro"

    def fake_partly(_prompt: str) -> tuple[str, str]:
        return json.dumps({"verdict": "partly_supported", "reason": "Extra claim added.", "unsupported_parts": ["free gift"]}), "fake-verifier-pro"

    def fake_not_supported(_prompt: str) -> tuple[str, str]:
        return json.dumps({"verdict": "not_supported", "reason": "Opposite meaning.", "unsupported_parts": ["penalty applies"]}), "fake-verifier-pro"

    def fake_same_model(_prompt: str) -> tuple[str, str]:
        # Same model as answer_model_used -> must NOT return verified!
        return json.dumps({"verdict": "supported", "reason": "Same model.", "unsupported_parts": []}), "gemini-3.5-flash-lite"

    def fake_unavailable(_prompt: str) -> tuple[str, str | None]:
        raise RuntimeError("Simulated outage")

    # 1. verified (supported + all numbers found + independent)
    o1 = verify_answer(q, "Repay $1,000 within 60 days.", ev, pages, answer_model_used="gemini-3.5-flash-lite", llm_fn=fake_supported)
    if o1["final_check"] != "verified" or not o1["verifier_independent"]:
        return False, f"T3.1 expected verified, got {o1}"

    # 2. needs_review from missing number even if LLM says supported
    o2 = verify_answer(q, "Repay $9,999 within 60 days.", ev, pages, answer_model_used="gemini-3.5-flash-lite", llm_fn=fake_supported)
    if o2["final_check"] != "needs_review":
        return False, f"T3.2 expected needs_review (missing number), got {o2}"

    # 3. needs_review from partly_supported
    o3 = verify_answer(q, "Repay $1,000 within 60 days with a free gift.", ev, pages, answer_model_used="gemini-3.5-flash-lite", llm_fn=fake_partly)
    if o3["final_check"] != "needs_review":
        return False, f"T3.3 expected needs_review (partly_supported), got {o3}"

    # 4. rejected from not_supported
    o4 = verify_answer(q, "A prepayment penalty applies.", ev, pages, answer_model_used="gemini-3.5-flash-lite", llm_fn=fake_not_supported)
    if o4["final_check"] != "rejected":
        return False, f"T3.4 expected rejected, got {o4}"

    # 5. unchecked when verifier falls back to same model as answer
    o5 = verify_answer(q, "Repay $1,000 within 60 days.", ev, pages, answer_model_used="gemini-3.5-flash-lite", llm_fn=fake_same_model)
    if o5["verifier_independent"] or o5["verifier_verdict"] != "unchecked" or o5["final_check"] != "unchecked":
        return False, f"T3.5 expected unchecked on same-model fallback, got {o5}"

    # 6. unchecked when verifier is unavailable
    o6 = verify_answer(q, "Repay $1,000 within 60 days.", ev, pages, answer_model_used="gemini-3.5-flash-lite", llm_fn=fake_unavailable)
    if o6["verifier_independent"] or o6["verifier_verdict"] != "unchecked" or o6["final_check"] != "unchecked":
        return False, f"T3.6 expected unchecked on outage, got {o6}"

    return True, "All 6 combination-logic unit tests passed (verified, needs_review x2, rejected, unchecked on same-model & outage)"


def _get_8_facts_from_2c1(client: GeminiClient) -> list[dict[str, Any]]:
    qa_pairs = [
        ("0000027430-25-000005_aesohio10qex10120250630q2", "Who is the Borrower in this First Amendment?"),
        ("0000027430-25-000005_aesohio10qex10120250630q2", "What is the date of the original Term Loan Agreement referenced in Recital A?"),
        ("0000027430-25-000005_aesohio10qex10120250630q2", "Which state's laws govern this Amendment?"),
        ("03_dbs_mitc", "What collateral or security is deposited for this facility?"),
        ("03_dbs_mitc", "What are the two types of interest rate mentioned in the document?"),
        ("03_dbs_mitc", "Are prepayment or foreclosure charges levied on floating interest rate loans?"),
        ("13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi", "अगर ब्याज दर में बदलाव उधारकर्ता के प्रतिकूल है तो वह कितने दिनों के भीतर बिना किसी अतिरिक्त शुल्क के लोन खाता बंद कर सकता है?"),
        ("13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi", "बैंक हॉलिडे के कारण पेमेंट क्रेडिट होने में T+ कितने दिनों से अधिक का समय लग सकता है?"),
    ]
    # Reuse the cached 2c-1 answers (generated by bulk/gemini-3.5-flash-lite) so only verifier calls are new
    cached_qa_cfg = {**load_qa_config(), "model_role": "bulk"}
    facts: list[dict[str, Any]] = []
    for idx, (doc_id, q) in enumerate(qa_pairs, 1):
        ans_res = answer_question(doc_id, q, client=client, config=cached_qa_cfg, force_retrieval=False, verify=False)
        _, doc_pages = load_document(doc_id)
        facts.append({
            "idx": idx,
            "doc_id": doc_id,
            "question": q,
            "answer": ans_res["answer"],
            "evidence": ans_res["evidence"],
            "doc_pages": doc_pages,
            "answer_model_used": ans_res.get("model_used"),
        })
    return facts


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("=" * 80)
    print("TEST SUITE: STAGE 2c-3 (SECOND-MODEL ANSWER VERIFIER)")
    print("=" * 80)

    # T1
    p1, m1 = test_t1_imports_and_key_safety()
    print(f"[{'PASS' if p1 else 'FAIL'}] T1: Imports & API Key Safety")
    print(f"       Details: {m1}")

    # T2
    p2, m2 = test_t2_check_numbers_unit_tests()
    print(f"[{'PASS' if p2 else 'FAIL'}] T2: check_numbers Unit Tests (No API)")
    print(f"       Details: {m2}")

    # T3
    p3, m3 = test_t3_combination_logic_unit_tests()
    print(f"[{'PASS' if p3 else 'FAIL'}] T3: Combination Logic Unit Tests with Fake Verifier (No API)")
    print(f"       Details: {m3}")

    # Prepare cached 2c-1 facts and shared client for T4 & T5
    client = GeminiClient()
    calls_before_facts = client.api_calls_made
    facts = _get_8_facts_from_2c1(client)
    calls_for_facts = client.api_calls_made - calls_before_facts

    verifier_models: Counter[str] = Counter()
    independent_counts: Counter[bool] = Counter()

    # T4: Positive controls (live)
    print("\n--- T4: Positive Controls (8 Correct Answers from 2c-1 Cache) ---")
    t4_results: list[dict[str, Any]] = []
    calls_before_live = client.api_calls_made

    for f in facts:
        vres = verify_answer(
            question=f["question"],
            answer=f["answer"],
            evidence=f["evidence"],
            doc_pages=f["doc_pages"],
            answer_model_used=f["answer_model_used"],
            client=client,
        )
        t4_results.append(vres)
        verifier_models[str(vres["verifier_model_used"])] += 1
        independent_counts[bool(vres["verifier_independent"])] += 1
        print(
            f"  [Pos {f['idx']}/8] final={vres['final_check']:<12} | verdict={vres['verifier_verdict']:<10} "
            f"| raw_llm={str(vres['raw_llm_verdict']):<16} | model={vres['verifier_model_used']} "
            f"| indep={vres['verifier_independent']} | num_ok={vres['number_check']['all_found']}"
        )

    pos_verified = sum(1 for r in t4_results if r["final_check"] == "verified")
    pos_not_rejected = sum(1 for r in t4_results if r["final_check"] != "rejected")
    pos_raw_supported = sum(1 for r in t4_results if r["raw_llm_verdict"] == "supported" and r["number_check"]["all_found"])
    t4_pass = pos_not_rejected >= 7

    # T5: Negative controls (8 deliberately wrong answers)
    # 2 changed number/date, 2 swapped party/place, 2 opposite meaning, 2 extra unsupported claim
    neg_specs = [
        # (fact_idx_1based, category, wrong_answer)
        (2, "changed_number_date", "The date of the original Term Loan Agreement referenced in Recital A is August 19, 2021."),
        (7, "changed_number_date", "यदि ब्याज दर में बदलाव उधारकर्ता के प्रतिकूल है, तो वह 15 दिनों के भीतर बिना किसी अतिरिक्त शुल्क के लोन खाता बंद कर सकता है।"),
        (1, "swapped_party_place", "The Borrower in this First Amendment is PNC Bank, National Association, a Delaware corporation."),
        (3, "swapped_party_place", "This Amendment is governed by the laws of the State of California."),
        (6, "opposite_meaning", "Yes, prepayment and foreclosure charges apply to loans where the interest rate is floating."),
        (8, "opposite_meaning", "बैंकिंग हॉलिडे को भी क्रेडिट अवधि की गणना में शामिल किया जाता है, इसलिए पेमेंट क्रेडिट होने में T+1 दिनों से अधिक का समय कभी नहीं लग सकता।"),
        (4, "extra_claim", "The facility is secured by gold, gold jewels, and gold ornaments deposited with DBS Bank, and DBS Bank provides complimentary doorstep courier delivery and free locker storage."),
        (5, "extra_claim", "The two types of interest rates mentioned are Fixed Rate of Interest and Floating Rate of Interest, and borrowers can switch between them free of charge every month without notice."),
    ]

    print("\n--- T5: Negative Controls (8 Hand-Crafted Wrong Answers) ---")
    t5_results: list[dict[str, Any]] = []
    slipped_through: list[str] = []

    for neg_i, (fact_idx, cat, wrong_ans) in enumerate(neg_specs, 1):
        f = facts[fact_idx - 1]
        vres = verify_answer(
            question=f["question"],
            answer=wrong_ans,
            evidence=f["evidence"],
            doc_pages=f["doc_pages"],
            answer_model_used=f["answer_model_used"],
            client=client,
        )
        t5_results.append({"cat": cat, "fact_idx": fact_idx, "wrong_ans": wrong_ans, "vres": vres})
        verifier_models[str(vres["verifier_model_used"])] += 1
        independent_counts[bool(vres["verifier_independent"])] += 1

        caught = vres["final_check"] in {"rejected", "needs_review"}
        if not caught:
            slipped_through.append(
                f"[Neg {neg_i} ({cat})] final={vres['final_check']}, raw_llm={vres['raw_llm_verdict']}, "
                f"reason={vres['verifier_reason']} | WrongAns={wrong_ans!r}"
            )
        print(
            f"  [Neg {neg_i}/8 {cat:<19}] final={vres['final_check']:<12} | raw_llm={str(vres['raw_llm_verdict']):<16} "
            f"| num_ok={str(vres['number_check']['all_found']):<5} | model={vres['verifier_model_used']}"
        )

    neg_caught = sum(1 for r in t5_results if r["vres"]["final_check"] in {"rejected", "needs_review"})
    neg_raw_caught = sum(
        1
        for r in t5_results
        if (r["vres"]["raw_llm_verdict"] in {"not_supported", "partly_supported"})
        or (not r["vres"]["number_check"]["all_found"])
    )
    num_changes_verified = sum(
        1
        for r in t5_results
        if r["cat"] == "changed_number_date" and r["vres"]["final_check"] == "verified"
    )
    t5_pass = (neg_caught >= 6) and (num_changes_verified == 0)

    total_live_calls = client.api_calls_made - calls_before_live
    no_independent = (independent_counts.get(True, 0) == 0)
    t6_pass = (total_live_calls + calls_for_facts) <= 25

    print("\n" + "=" * 80)
    if no_independent:
        print("WARNING: no independent verifier available")
        print("         (All verifier calls fell back to the answer model; T4 and T5 are NOT A CROSS-MODEL CHECK)")

    tag_cross = " [NOT A CROSS-MODEL CHECK]" if no_independent else ""

    print(f"[{'PASS' if t4_pass else 'FAIL'}] T4: Positive Controls{tag_cross}")
    print(
        f"       Details: final_check verified={pos_verified}/8, not_rejected={pos_not_rejected}/8 "
        f"(pass gate >=7/8 not rejected) | raw same-model supported={pos_raw_supported}/8"
    )

    print(f"[{'PASS' if t5_pass else 'FAIL'}] T5: Negative Controls{tag_cross}")
    print(
        f"       Details: strict caught (rejected/needs_review)={neg_caught}/8 (pass gate >=6/8), "
        f"number/date verified={num_changes_verified}/2 | diagnostic fallback+numbers caught={neg_raw_caught}/8"
    )
    if slipped_through:
        print("       Wrong answers that slipped through strict final_check:")
        for s in slipped_through:
            print(f"         * {s}")

    print(f"[{'PASS' if t6_pass else 'FAIL'}] T6: API Budget & Independence Honesty")
    print(
        f"       Details: Live verifier API calls={total_live_calls} (+ answer cache misses={calls_for_facts}, max<=25) | "
        f"verifier_model_used={dict(verifier_models)} | verifier_independent={dict(independent_counts)}"
    )

    overall = p1 and p2 and p3 and t4_pass and t5_pass and t6_pass
    print("=" * 80)
    print(f"OVERALL RESULT: {'PASS' if overall else 'FAIL'}")
    print("=" * 80)

    if not overall:
        sys.exit(1)


if __name__ == "__main__":
    main()
