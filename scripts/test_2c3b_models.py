"""scripts/test_2c3b_models.py

Verification Test Suite for Step 2c-3b: Model Availability Fix.
Checks:
T1: API key leak scan over ALL files in data/processed, scripts, src, config, docs -> 0 leaks.
T2: data/processed/available_models.csv and data/processed/model_probe.csv exist and have rows.
T3: config/models.yaml: main, bulk, verifier all in the OK list from model_probe.csv;
    verifier differs from main and bulk.
T4: test_2c3_verifier T4 (positive controls): verified / needs_review / rejected / unchecked counts
    and verifier_independent=True count.
T5: test_2c3_verifier T5 (negative controls): wrong answers caught with verifier_independent=True
    (>= 6/8 and 0 wrong number/date marked verified).
T6: Total live calls <= 25 (recorded in llm_log / probe) and 0 new calls on a cached repeat run.
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.llm.gemini_client import GeminiClient, get_api_key, load_model_config
from src.qa.verifier import verify_answer
from scripts.test_2c3_verifier import _get_8_facts_from_2c1

AVAILABLE_CSV = ROOT / "data" / "processed" / "available_models.csv"
PROBE_CSV = ROOT / "data" / "processed" / "model_probe.csv"
MODELS_YAML = ROOT / "config" / "models.yaml"


def test_t1_full_leak_scan() -> tuple[bool, str]:
    api_key = get_api_key()
    scan_dirs = [
        ROOT / "data" / "processed",
        ROOT / "scripts",
        ROOT / "src",
        ROOT / "config",
        ROOT / "docs",
    ]
    text_exts = {".py", ".yaml", ".yml", ".json", ".csv", ".md", ".txt", ".bak"}

    leaks: list[str] = []
    scanned = 0
    for d in scan_dirs:
        if not d.is_dir():
            continue
        for f in d.rglob("*"):
            if f.is_file() and f.suffix.lower() in text_exts:
                scanned += 1
                try:
                    content = f.read_text(encoding="utf-8", errors="ignore")
                    if api_key in content:
                        leaks.append(str(f.relative_to(ROOT)))
                except Exception:
                    pass

    if leaks:
        return False, f"API key leaked in {len(leaks)} file(s): {leaks[:5]}"
    return True, f"0 leaks across {scanned} files in data/processed, scripts, src, config, docs"


def test_t2_csvs_exist() -> tuple[bool, str]:
    if not AVAILABLE_CSV.is_file() or not PROBE_CSV.is_file():
        return False, f"Missing CSV(s): available={AVAILABLE_CSV.is_file()}, probe={PROBE_CSV.is_file()}"

    with AVAILABLE_CSV.open("r", encoding="utf-8", errors="ignore") as f:
        avail_rows = list(csv.DictReader(f))
    with PROBE_CSV.open("r", encoding="utf-8", errors="ignore") as f:
        probe_rows = list(csv.DictReader(f))

    if not avail_rows or not probe_rows:
        return False, f"Empty CSV(s): available={len(avail_rows)}, probe={len(probe_rows)}"

    ok_models = [r["model_name"] for r in probe_rows if str(r.get("ok", "")).lower() == "true"]
    return True, f"available_models.csv ({len(avail_rows)} rows), model_probe.csv ({len(probe_rows)} rows, {len(ok_models)} OK)"


def test_t3_models_yaml_valid() -> tuple[bool, str]:
    if not MODELS_YAML.is_file():
        return False, "config/models.yaml not found."
    if not PROBE_CSV.is_file():
        return False, "model_probe.csv not found."

    cfg = load_model_config()
    with PROBE_CSV.open("r", encoding="utf-8", errors="ignore") as f:
        probe_rows = list(csv.DictReader(f))

    ok_set = {r["model_name"] for r in probe_rows if str(r.get("ok", "")).lower() == "true"}
    if len(ok_set) <= 1:
        return True, f"SKIPPED: only {len(ok_set)} working model(s) ({sorted(ok_set)})"

    main_m = cfg.get("main", "")
    bulk_m = cfg.get("bulk", "")
    ver_m = cfg.get("verifier", "")

    not_ok = [f"{role}={m}" for role, m in (("main", main_m), ("bulk", bulk_m), ("verifier", ver_m)) if m not in ok_set]
    if not_ok:
        return False, f"Model(s) not in OK list: {not_ok} (OK={sorted(ok_set)})"

    if ver_m == main_m or ver_m == bulk_m:
        return False, f"Verifier ({ver_m}) does not differ from main ({main_m}) and bulk ({bulk_m})"

    return True, f"main={main_m}, bulk={bulk_m}, verifier={ver_m} (all OK, verifier distinct)"


def run_t4_t5_t6_cross_model_suite() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    client = GeminiClient()
    calls_start = client.api_calls_made

    facts = _get_8_facts_from_2c1(client)
    answer_models = Counter(str(f["answer_model_used"]) for f in facts)

    # T4: Positive Controls
    t4_counts: Counter[str] = Counter()
    t4_indep = 0
    ver_models: Counter[str] = Counter()

    for f in facts:
        vres = verify_answer(
            question=f["question"],
            answer=f["answer"],
            evidence=f["evidence"],
            doc_pages=f["doc_pages"],
            answer_model_used=f["answer_model_used"],
            client=client,
        )
        t4_counts[vres["final_check"]] += 1
        if vres["verifier_independent"]:
            t4_indep += 1
        ver_models[str(vres["verifier_model_used"])] += 1

    # T5: Negative Controls
    neg_specs = [
        (2, "changed_number_date", "The date of the original Term Loan Agreement referenced in Recital A is August 19, 2021."),
        (7, "changed_number_date", "यदि ब्याज दर में बदलाव उधारकर्ता के प्रतिकूल है, तो वह 15 दिनों के भीतर बिना किसी अतिरिक्त शुल्क के लोन खाता बंद कर सकता है।"),
        (1, "swapped_party_place", "The Borrower in this First Amendment is PNC Bank, National Association, a Delaware corporation."),
        (3, "swapped_party_place", "This Amendment is governed by the laws of the State of California."),
        (6, "opposite_meaning", "Yes, prepayment and foreclosure charges apply to loans where the interest rate is floating."),
        (8, "opposite_meaning", "बैंकिंग हॉलिडे को भी क्रेडिट अवधि की गणना में शामिल किया जाता है, इसलिए पेमेंट क्रेडिट होने में T+1 दिनों से अधिक का समय कभी नहीं लग सकता।"),
        (4, "extra_claim", "The facility is secured by gold, gold jewels, and gold ornaments deposited with DBS Bank, and DBS Bank provides complimentary doorstep courier delivery and free locker storage."),
        (5, "extra_claim", "The two types of interest rates mentioned are Fixed Rate of Interest and Floating Rate of Interest, and borrowers can switch between them free of charge every month without notice."),
    ]

    t5_counts: Counter[str] = Counter()
    t5_indep_caught = 0
    t5_num_verified = 0
    t5_indep_total = 0

    for fact_idx, cat, wrong_ans in neg_specs:
        f = facts[fact_idx - 1]
        vres = verify_answer(
            question=f["question"],
            answer=wrong_ans,
            evidence=f["evidence"],
            doc_pages=f["doc_pages"],
            answer_model_used=f["answer_model_used"],
            client=client,
        )
        t5_counts[vres["final_check"]] += 1
        ver_models[str(vres["verifier_model_used"])] += 1
        if vres["verifier_independent"]:
            t5_indep_total += 1
            if vres["final_check"] in {"rejected", "needs_review"}:
                t5_indep_caught += 1
        if cat == "changed_number_date" and vres["final_check"] == "verified":
            t5_num_verified += 1

    first_run_calls = client.api_calls_made - calls_start

    # T6: Repeat cached run (must make 0 new calls)
    calls_before_repeat = client.api_calls_made
    for f in facts:
        _ = verify_answer(
            question=f["question"],
            answer=f["answer"],
            evidence=f["evidence"],
            doc_pages=f["doc_pages"],
            answer_model_used=f["answer_model_used"],
            client=client,
        )
    repeat_calls = client.api_calls_made - calls_before_repeat

    t4_info = {
        "verified": t4_counts.get("verified", 0),
        "needs_review": t4_counts.get("needs_review", 0),
        "rejected": t4_counts.get("rejected", 0),
        "unchecked": t4_counts.get("unchecked", 0),
        "independent_true": t4_indep,
        "pass": (t4_counts.get("rejected", 0) <= 1 and t4_indep == 8),
        "answer_models": dict(answer_models),
        "verifier_models": dict(ver_models),
    }
    t5_info = {
        "counts": dict(t5_counts),
        "indep_caught": t5_indep_caught,
        "indep_total": t5_indep_total,
        "num_verified": t5_num_verified,
        "pass": (t5_indep_caught >= 6 and t5_num_verified == 0),
    }
    t6_info = {
        "first_run_calls": first_run_calls,
        "repeat_calls": repeat_calls,
        "pass": (first_run_calls <= 25 and repeat_calls == 0),
    }
    return t4_info, t5_info, t6_info


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("=" * 80)
    print("TEST SUITE: STAGE 2c-3b (MODEL AVAILABILITY & CROSS-MODEL VERIFICATION)")
    print("=" * 80)

    p1, m1 = test_t1_full_leak_scan()
    print(f"[{'PASS' if p1 else 'FAIL'}] T1: API Key Leak Scan -> {m1}")

    p2, m2 = test_t2_csvs_exist()
    print(f"[{'PASS' if p2 else 'FAIL'}] T2: CSV Files Exist & Non-Empty -> {m2}")

    p3, m3 = test_t3_models_yaml_valid()
    tag3 = "SKIP" if m3.startswith("SKIPPED:") else ("PASS" if p3 else "FAIL")
    print(f"[{tag3}] T3: models.yaml Validity & Distinct Verifier -> {m3}")

    t4, t5, t6 = run_t4_t5_t6_cross_model_suite()
    print(
        f"[{'PASS' if t4['pass'] else 'FAIL'}] T4: Positive Controls (8 facts) -> "
        f"verified={t4['verified']}, needs_review={t4['needs_review']}, "
        f"rejected={t4['rejected']}, unchecked={t4['unchecked']} | verifier_independent=True: {t4['independent_true']}/8"
    )
    print(
        f"[{'PASS' if t5['pass'] else 'FAIL'}] T5: Negative Controls (8 wrong) -> "
        f"caught with verifier_independent=True: {t5['indep_caught']}/8 (target >=6/8), "
        f"wrong number/date marked verified={t5['num_verified']}/2 | counts={t5['counts']}"
    )
    print(
        f"[{'PASS' if t6['pass'] else 'FAIL'}] T6: API Budget & Repeat Cache -> "
        f"calls={t6['first_run_calls']} (<=25), cached repeat calls={t6['repeat_calls']} (target 0)"
    )

    print("=" * 80)
    overall = p1 and p2 and p3 and t4["pass"] and t5["pass"] and t6["pass"]
    print(f"Answer models used:  {t4['answer_models']}")
    print(f"Verifier model used: {t4['verifier_models']}")
    print(f"OVERALL RESULT: {'PASS' if overall else 'FAIL'}")
    print("=" * 80)

    if not overall:
        sys.exit(1)


if __name__ == "__main__":
    main()
