"""scripts/test_2d_router.py

Test Suite for Stage 2d: Question Router & Unified ask() Pipeline.
Verifies:
T1: API key leak scan across data/processed, scripts, src, config, docs -> 0 leaks.
T2: Router unit tests with fake LLM (no API): deterministic rules fire cleanly,
    invalid JSON or LLM exception falls back to category='fact', confidence=0,
    router_fallback=True.
T3: Router accuracy on 40 real-style questions (10 fact, 8 explain_term, 8 calculation,
    8 advice, 6 off_topic; includes 6 Hindi/Tamil/Bengali/Punjabi/Malayalam questions).
    Reports overall accuracy (>=85%), per-category accuracy, advice recall (target 100%,
    advice must NEVER route to fact), and a 5x5 confusion table.
T4: Fraction of questions resolved by deterministic rules only (no API call).
T5: ask() on 6 live cases (2 fact on 03_dbs_mitc, 1 explain_term, 1 calculation,
    1 advice, 1 off_topic): verifies category, behavior, deterministic calculation output,
    and no recommendation on advice.
T6: Total live API calls <= 60 and 0 new calls on a cached repeat run.
"""

from __future__ import annotations

import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.llm.gemini_client import GeminiClient, get_api_key
from src.qa.ask import ask
from src.qa.router import VALID_CATEGORIES, detect_language, route_question

DATASET_40: list[tuple[str, str, str]] = [
    # --- 10 fact ---
    ("fact", "en", "Who is the borrower in this loan agreement?"),
    ("fact", "en", "What is the floating interest rate reset interval mentioned in the MITC?"),
    ("fact", "en", "Are prepayment charges levied on floating rate loans?"),
    ("fact", "en", "What collateral is required for the facility?"),
    ("fact", "en", "When is the maturity date of this term loan?"),
    ("fact", "en", "What are the late-payment penal charges specified in this contract?"),
    ("fact", "en", "Which state's jurisdiction governs this amendment?"),
    ("fact", "en", "What is the lender's grievance redressal office address?"),
    ("fact", "hi", "इस लोन एग्रीमेंट में जुर्माना या दंडात्मक शुल्क कितना है?"),
    ("fact", "bn", "এই ঋণ চুক্তিতে ফ্লোটিং সুদের হার কীভাবে নির্ধারিত হয়?"),

    # --- 8 explain_term ---
    ("explain_term", "en", "What does APR mean?"),
    ("explain_term", "en", "Explain what amortization means in simple words."),
    ("explain_term", "en", "What is the meaning of foreclosure in banking?"),
    ("explain_term", "en", "Define moratorium period for a loan."),
    ("explain_term", "en", "Could you clarify what bullet repayment refers to in gold loans?"),
    ("explain_term", "en", "What is cross-collateralization?"),
    ("explain_term", "pa", "ਲੋਨ ਵਿੱਚ ਫੋਰਕਲੋਜ਼ਰ (foreclosure) ਦਾ ਕੀ ਮਤਲਬ ਹੁੰਦਾ ਹੈ?"),
    ("explain_term", "ml", "ലോൺ കരാറിലെ മോറട്ടോറിയം എന്നതിന്റെ അർത്ഥം എന്താണ്?"),

    # --- 8 calculation ---
    ("calculation", "en", "Calculate my monthly EMI for a 5,00,000 rupee loan at 9.5% for 3 years."),
    ("calculation", "en", "How much total interest will I pay on a $100,000 loan over 60 months?"),
    ("calculation", "en", "Compute the foreclosure cost if Rs. 2,50,000 principal remains and fee is 3%."),
    ("calculation", "en", "How much will I pay in total if I borrow Rs. 1,00,000 at 12% per year for 2 years?"),
    ("calculation", "en", "What would be my monthly installment for Rs 8 lakh over 48 months at 10%?"),
    ("calculation", "en", "If I prepay Rs 50,000 after 6 months, what is the penalty amount at 2%?"),
    ("calculation", "en", "Work out the penal interest charges for a 15-day delay on a Rs 20,000 EMI at 2% per month."),
    ("calculation", "hi", "10 लाख रुपये के लोन पर 9% ब्याज दर से 5 साल की ईएमआई निकालें।"),

    # --- 8 advice ---
    ("advice", "en", "Should I sign this gold loan agreement?"),
    ("advice", "en", "Is it safe to take this floating-rate loan right now?"),
    ("advice", "en", "What do you recommend: fixed or floating interest for my family?"),
    ("advice", "en", "Is this loan a good deal or should I look for another bank?"),
    ("advice", "en", "Can I sue the bank if they change my floating rate?"),
    ("advice", "en", "Do you think the foreclosure penalty here is fair enough for me to accept?"),
    ("advice", "en", "Between Bajaj Finance and DBS Bank, which lender is better for my needs?"),
    ("advice", "ta", "இந்த தங்க நகைக் கடன் ஒப்பந்தத்தில் நான் கையெழுத்திடலாமா?"),

    # --- 6 off_topic ---
    ("off_topic", "en", "What is the weather forecast in Delhi tomorrow?"),
    ("off_topic", "en", "Who won the cricket world cup in 2023?"),
    ("off_topic", "en", "Give me a recipe for paneer butter masala."),
    ("off_topic", "en", "Can you write a short poem about the ocean?"),
    ("off_topic", "en", "Who is the current CEO of Apple?"),
    ("off_topic", "en", "How do I fix a flat bicycle tire?"),
]


def test_t1_leak_scan() -> tuple[bool, str]:
    api_key = get_api_key()
    scan_dirs = [
        ROOT / "data" / "processed",
        ROOT / "scripts",
        ROOT / "src",
        ROOT / "config",
        ROOT / "docs",
    ]
    text_exts = {".py", ".yaml", ".yml", ".json", ".csv", ".md", ".txt", ".bak"}
    leaks = 0
    scanned = 0
    for d in scan_dirs:
        if not d.is_dir():
            continue
        for f in d.rglob("*"):
            if f.is_file() and f.suffix.lower() in text_exts:
                scanned += 1
                if api_key in f.read_text(encoding="utf-8", errors="ignore"):
                    leaks += 1
    return (leaks == 0), f"0 leaks across {scanned} files" if leaks == 0 else f"{leaks} leaks found!"


def test_t2_router_unit_tests() -> tuple[bool, str]:
    def fake_invalid_json(_prompt: str) -> tuple[str, str]:
        return "Sorry, I am not returning JSON right now!", "fake-bulk"

    def fake_crash(_prompt: str) -> tuple[str, str]:
        raise RuntimeError("Simulated timeout")

    # 1. Rules fire cleanly without touching fake_crash
    r_adv = route_question("Should I sign this agreement?", llm_fn=fake_crash)
    r_calc = route_question("Calculate my EMI for 5 lakh at 9%", llm_fn=fake_crash)
    r_exp = route_question("What does foreclosure mean?", llm_fn=fake_crash)
    r_off = route_question("What is the weather today?", llm_fn=fake_crash)
    r_fact = route_question("Who is the borrower in this loan agreement?", llm_fn=fake_crash)

    if r_adv["category"] != "advice" or not r_adv["rule_based"]:
        return False, f"Advice rule failed: {r_adv}"
    if r_calc["category"] != "calculation" or not r_calc["rule_based"]:
        return False, f"Calculation rule failed: {r_calc}"
    if r_exp["category"] != "explain_term" or not r_exp["rule_based"]:
        return False, f"Explain rule failed: {r_exp}"
    if r_off["category"] != "off_topic" or not r_off["rule_based"]:
        return False, f"Off-topic rule failed: {r_off}"
    if r_fact["category"] != "fact" or not r_fact["rule_based"]:
        return False, f"Fact rule failed: {r_fact}"

    # 2. Invalid JSON -> safe fallback to fact, confidence=0, router_fallback=True
    r_fb1 = route_question("Tell me more about the terms.", llm_fn=fake_invalid_json)
    if r_fb1["category"] != "fact" or r_fb1["confidence"] != 0.0 or not r_fb1["router_fallback"]:
        return False, f"Invalid JSON fallback failed: {r_fb1}"

    # 3. LLM error -> safe fallback to fact, confidence=0, router_fallback=True
    r_fb2 = route_question("Tell me more about the terms.", llm_fn=fake_crash)
    if r_fb2["category"] != "fact" or r_fb2["confidence"] != 0.0 or not r_fb2["router_fallback"]:
        return False, f"LLM crash fallback failed: {r_fb2}"

    # 4. Language checks
    if detect_language("இந்த கடன்") != "ta" or detect_language("ਬਿਆਜ") != "pa" or detect_language("പലിശ") != "ml":
        return False, "Script language detection failed on ta/pa/ml."

    return True, "All 8 unit assertions passed (5 deterministic rules + invalid JSON fallback + crash fallback + script detection)"


def run_t3_t4_40_questions(client: GeminiClient) -> tuple[bool, bool, str, str, dict[str, Any]]:
    confusion: dict[str, Counter[str]] = {c: Counter() for c in VALID_CATEGORIES}
    cat_total: Counter[str] = Counter()
    cat_correct: Counter[str] = Counter()
    rule_resolved = 0
    model_counts: Counter[str] = Counter()
    mistakes: list[str] = []
    advice_to_fact = 0

    for idx, (expected_cat, expected_lang, q) in enumerate(DATASET_40, 1):
        res = route_question(q, client=client)
        pred_cat = res["category"]
        confusion[expected_cat][pred_cat] += 1
        cat_total[expected_cat] += 1
        if res.get("rule_based"):
            rule_resolved += 1
        if res.get("model_used"):
            model_counts[str(res["model_used"])] += 1

        if pred_cat == expected_cat:
            cat_correct[expected_cat] += 1
        else:
            mistakes.append(f"Q{idx} [{expected_lang}] exp={expected_cat} pred={pred_cat} ({'rule' if res['rule_based'] else 'llm'}): {q}")

        if expected_cat == "advice" and pred_cat == "fact":
            advice_to_fact += 1

    total = len(DATASET_40)
    total_correct = sum(cat_correct.values())
    overall_acc = (total_correct / total) * 100.0
    advice_recall = (cat_correct["advice"] / max(1, cat_total["advice"])) * 100.0
    rule_frac = (rule_resolved / total) * 100.0

    t3_pass = (overall_acc >= 85.0) and (advice_recall == 100.0) and (advice_to_fact == 0)
    t4_pass = True  # Informational metric reporting fraction resolved by rules only

    per_cat_str = " | ".join(
        f"{c}: {cat_correct[c]}/{cat_total[c]} ({cat_correct[c]/max(1, cat_total[c])*100:.1f}%)"
        for c in VALID_CATEGORIES
    )
    msg3 = (
        f"Overall accuracy: {total_correct}/{total} ({overall_acc:.1f}%, target >=85%) | "
        f"Advice recall: {advice_recall:.1f}% (advice->fact leaks: {advice_to_fact}) | {per_cat_str}"
    )
    msg4 = f"Rules-only resolution (0 API calls): {rule_resolved}/{total} ({rule_frac:.1f}%) | LLM router calls: {total - rule_resolved}/{total}"

    info = {
        "overall_acc": overall_acc,
        "total_correct": total_correct,
        "total": total,
        "cat_total": dict(cat_total),
        "cat_correct": dict(cat_correct),
        "confusion": {k: dict(v) for k, v in confusion.items()},
        "rule_resolved": rule_resolved,
        "rule_frac": rule_frac,
        "model_counts": dict(model_counts),
        "mistakes": mistakes,
        "advice_recall": advice_recall,
    }
    return t3_pass, t4_pass, msg3, msg4, info


def run_t5_ask_live_6_cases(client: GeminiClient) -> tuple[bool, str, dict[str, Any]]:
    cases = [
        ("fact_found", "03_dbs_mitc", "What collateral or security is deposited for this facility?"),
        ("fact_not_found", "03_dbs_mitc", "Can Bitcoin or cryptocurrency be accepted as collateral for this loan?"),
        ("explain_term", "03_dbs_mitc", "What does foreclosure mean?"),
        ("calculation", "03_dbs_mitc", "Calculate my monthly EMI on a Rs. 500000 gold loan at 9% for 24 months"),
        ("advice", "03_dbs_mitc", "Should I sign this gold loan agreement?"),
        ("off_topic", "03_dbs_mitc", "Who won the cricket world cup in 2023?"),
    ]

    failures: list[str] = []
    details_list: list[str] = []
    model_counts: Counter[str] = Counter()

    for label, doc_id, q in cases:
        res = ask(doc_id, q, client=client, verify=True)
        for req in ("category", "status", "answer", "evidence", "model_used", "router_fallback"):
            if req not in res:
                failures.append(f"{label}: missing key '{req}'")

        if res.get("model_used"):
            model_counts[str(res["model_used"])] += 1
        cat = res.get("category")
        ans = res.get("answer", "")
        status = res.get("status")

        if label == "fact_found":
            if cat != "fact" or status != "ok" or not res.get("evidence"):
                failures.append(f"fact_found unexpected: cat={cat}, status={status}, ev={len(res.get('evidence', []))}")
        elif label == "fact_not_found":
            if cat != "fact" or status != "not_found":
                failures.append(f"fact_not_found unexpected: cat={cat}, status={status}")
        elif label == "explain_term":
            if cat != "explain_term" or "general explanation, not from your document" not in ans.lower():
                failures.append(f"explain_term missing required label: cat={cat}, ans={ans[:80]}")
            if not res.get("evidence"):
                failures.append("explain_term did not attach verified document quote even though 'foreclosure' is in 03_dbs_mitc")
        elif label == "calculation":
            if cat != "calculation" or status != "ok" or res.get("result") != Decimal("22842.37"):
                failures.append(f"calculation contract broken: cat={cat}, status={status}, ans={ans}")
            if "estimate only" not in ans.lower() or not res.get("formula_name") or not res.get("inputs"):
                failures.append(f"calculation result missing formula, inputs, or estimate disclaimer: {res}")
        elif label == "advice":
            if cat != "advice" or status != "refused":
                failures.append(f"advice unexpected: cat={cat}, status={status}")
            low_ans = ans.lower()
            if "information" not in low_ans or "not legal or financial advice" not in low_ans or "cannot recommend" not in low_ans:
                failures.append(f"advice refusal missing neutral disclaimer: {ans}")
            if any(bad in low_ans for bad in ("yes, you should", "i recommend signing", "go ahead and sign", "do not sign")):
                failures.append(f"advice gave a personal recommendation: {ans}")
        elif label == "off_topic":
            if cat != "off_topic" or status != "off_topic":
                failures.append(f"off_topic unexpected: cat={cat}, status={status}")

        details_list.append(
            f"{label}: cat={cat}, status={status}, ev={len(res.get('evidence', []))}, model={res.get('model_used')}"
        )

    passed = len(failures) == 0
    return passed, " | ".join(details_list), {"failures": failures, "model_counts": dict(model_counts)}


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("=" * 88)
    print("TEST SUITE: STAGE 2d (QUESTION ROUTER & ask() PIPELINE)")
    print("=" * 88)

    p1, m1 = test_t1_leak_scan()
    print(f"[{'PASS' if p1 else 'FAIL'}] T1: API Key Leak Scan -> {m1}")

    p2, m2 = test_t2_router_unit_tests()
    print(f"[{'PASS' if p2 else 'FAIL'}] T2: Router Unit Tests (Fake LLM, No API) -> {m2}")

    client = GeminiClient()
    calls_before = client.api_calls_made

    p3, p4, m3, m4, t3_info = run_t3_t4_40_questions(client)
    print(f"[{'PASS' if p3 else 'FAIL'}] T3: 40-Question Router Accuracy -> {m3}")
    print(f"[{'PASS' if p4 else 'FAIL'}] T4: Rules-Only Resolution -> {m4}")

    p5, m5, t5_info = run_t5_ask_live_6_cases(client)
    print(f"[{'PASS' if p5 else 'FAIL'}] T5: ask() Live 6-Case Verification -> {m5}")
    if t5_info["failures"]:
        for fail_msg in t5_info["failures"]:
            print(f"       * Failure: {fail_msg}")

    live_calls_first_pass = client.api_calls_made - calls_before

    # T6: Cached repeat run across all 40 router queries + 6 ask() cases (must make 0 new API calls)
    calls_before_repeat = client.api_calls_made
    for _, _, q in DATASET_40:
        _ = route_question(q, client=client)
    for _, doc_id, q in [
        ("fact_found", "03_dbs_mitc", "What collateral or security is deposited for this facility?"),
        ("fact_not_found", "03_dbs_mitc", "Can Bitcoin or cryptocurrency be accepted as collateral for this loan?"),
        ("explain_term", "03_dbs_mitc", "What does foreclosure mean?"),
        ("calculation", "03_dbs_mitc", "Calculate my monthly EMI on a Rs. 500000 gold loan at 9% for 24 months"),
        ("advice", "03_dbs_mitc", "Should I sign this gold loan agreement?"),
        ("off_topic", "03_dbs_mitc", "Who won the cricket world cup in 2023?"),
    ]:
        _ = ask(doc_id, q, client=client, verify=True)
    repeat_calls = client.api_calls_made - calls_before_repeat

    p6 = (live_calls_first_pass <= 60) and (repeat_calls == 0)
    print(
        f"[{'PASS' if p6 else 'FAIL'}] T6: API Budget & Cached Repeat -> "
        f"live calls={live_calls_first_pass} (<=60), cached repeat calls={repeat_calls} (target 0)"
    )

    print("\n--- Per-Category Accuracy & Confusion Matrix (40 Questions) ---")
    print(f"{'Expected \\ Pred':<14} | " + " | ".join(f"{c:<12}" for c in VALID_CATEGORIES) + " | Acc")
    print("-" * 92)
    for exp in VALID_CATEGORIES:
        row_counts = t3_info["confusion"].get(exp, {})
        tot = t3_info["cat_total"].get(exp, 0)
        cor = t3_info["cat_correct"].get(exp, 0)
        cells = " | ".join(f"{row_counts.get(pred, 0):<12}" for pred in VALID_CATEGORIES)
        print(f"{exp:<14} | {cells} | {cor}/{tot} ({cor/max(1,tot)*100:.1f}%)")

    if t3_info["mistakes"]:
        print("\nMisclassified questions:")
        for mk in t3_info["mistakes"]:
            print(f"  * {mk}")

    print("=" * 88)
    print(f"Router LLM model(s) used: {t3_info['model_counts'] or 'None (100% rules)'}")
    print(f"ask() LLM model(s) used:  {t5_info['model_counts']}")
    overall = p1 and p2 and p3 and p4 and p5 and p6
    print(f"OVERALL RESULT: {'PASS' if overall else 'FAIL'}")
    print("=" * 88)

    if not overall:
        sys.exit(1)


if __name__ == "__main__":
    main()
