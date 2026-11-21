"""scripts/test_3a_fix.py

Verification test suite for Stage 3a-fix (transparent value matcher).
Tests:
  T1: API key leak scan (0 leaks).
  T2: Matcher unit tests (no API).
  T3: Strict & lenient F1 vs LLM-assisted silver labels (separate numbers + match counts).
  T4: Strict & lenient field-match rate vs human-verified gold (27 cells, overall + per doc).
  T5: Mismatch CSV exists, required columns present, every non-match listed with empty who_is_right.
  T6: New live API calls <= 20 and 0 new calls on a cached repeat.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.eval_3a_matches import (
    FIX_RESULTS_JSON,
    GOLD_CSV,
    REVIEW_CSV,
    SILVER_CSV,
    SNAPSHOT_JSON,
    evaluate_gold,
    evaluate_silver,
    load_cached_extractions,
    run_eval,
)
from src.extract.match_values import values_match
from src.llm.gemini_client import GeminiClient, get_api_key

LOG_FILE = ROOT / "data" / "processed" / "llm_log.csv"
GEMINI_CACHE_DIR = ROOT / "data" / "processed" / "cache" / "gemini"
RESULTS_3A_JSON = ROOT / "data" / "processed" / "extract_3a_results.json"


def test_t1_key_leaks() -> tuple[bool, str]:
    api_key = get_api_key()
    if not api_key or len(api_key) < 10:
        return False, "GEMINI_API_KEY missing or invalid."

    files_to_scan: list[Path] = [
        ROOT / "src" / "extract" / "match_values.py",
        ROOT / "scripts" / "eval_3a_matches.py",
        ROOT / "scripts" / "test_3a_fix.py",
        ROOT / "docs" / "WORK_REPORT.md",
        LOG_FILE,
        RESULTS_3A_JSON,
        SNAPSHOT_JSON,
        FIX_RESULTS_JSON,
        REVIEW_CSV,
    ]
    if GEMINI_CACHE_DIR.is_dir():
        files_to_scan.extend(GEMINI_CACHE_DIR.glob("*.json"))

    leaks = 0
    scanned = 0
    for f in files_to_scan:
        if f.is_file():
            scanned += 1
            if api_key in f.read_text(encoding="utf-8", errors="ignore"):
                leaks += 1
    return leaks == 0, f"Scanned {scanned} files; leaks={leaks}"


def test_t2_matcher_unit_tests() -> tuple[bool, str]:
    cases: list[tuple[str, str, str, str, str]] = [
        ("money_million", "loan_or_commitment_amount", "USD 30,000,000", "$30 million", "normalized"),
        ("party_na", "lenders", "Citizens Bank, N.A.", "Citizens Bank", "normalized"),
        ("party_inc_the", "borrowers", "The Acme Corp., LLC", "Acme Inc.", "normalized"),
        ("percent_zeros", "interest_rate", "8.5%", "8.50%", "normalized"),
        ("date_iso", "agreement_date", "February 1, 2011", "2011-02-01", "normalized"),
        ("date_ordinal", "agreement_date", "1st day of February, 2011", "February 1, 2011", "normalized"),
        ("exact_ws", "document_title", "  CREDIT   AGREEMENT ", "credit agreement", "exact"),
        ("years_diff", "maturity_termination_date", "5 years", "7 years", "no"),
        ("days_diff", "events_of_default", "30 days", "60 days", "no"),
        ("ambig_numeric_date", "agreement_date", "03/04/2025", "04/03/2025", "no"),
        ("unrelated", "governing_law", "State of New York", "Quarterly commitment fee payable", "no"),
        ("partial_fee", "fees", "Documentation fee of $500", "$500.00 documentation fee payable", "partial"),
    ]
    failures: list[str] = []
    for cname, field, pred, ref, expected in cases:
        res = values_match(field, pred, ref)
        if res["match"] != expected:
            failures.append(f"{cname}: got {res['match']} ({res['reason']}), expected {expected}")

    ok = len(failures) == 0
    return ok, f"{len(cases) - len(failures)}/{len(cases)} unit cases passed" + (f"; FAILURES: {failures}" if failures else "")


def test_t3_silver(eval_payload: dict[str, Any]) -> tuple[bool, str]:
    s = eval_payload["silver"]
    c = s["counts"]
    sp, sr, sf1 = s["strict"]["precision"], s["strict"]["recall"], s["strict"]["f1"]
    lp, lr, lf1 = s["lenient"]["precision"], s["lenient"]["recall"], s["lenient"]["f1"]
    ok = s["total_rows"] == 48 and s["definitive_rows"] == 41 and sf1 <= lf1
    msg = (
        f"counts(exact={c['exact']}, norm={c['normalized']}, partial={c['partial']}, no={c['no']}, TN={s['tn']}, UNCLEAR={s['unclear_rows']}) | "
        f"STRICT(exact+norm) P={sp:.1%} R={sr:.1%} F1={sf1:.1%} | "
        f"LENIENT(+partial) P={lp:.1%} R={lr:.1%} F1={lf1:.1%}"
    )
    return ok, msg


def test_t4_gold(eval_payload: dict[str, Any]) -> tuple[bool, str]:
    g = eval_payload["gold"]
    c = g["counts"]
    per_doc_str = "; ".join(
        f"{agr}: strict={d['exact']+d['normalized']}/{d['total']} ({d['strict_rate']:.1%}), "
        f"lenient={d['exact']+d['normalized']+d['partial']}/{d['total']} ({d['lenient_rate']:.1%})"
        for agr, d in sorted(g["per_doc"].items())
    )
    ok = g["total_cells"] == 27 and g["strict_matches"] <= g["lenient_matches"]
    msg = (
        f"counts(27 cells: exact={c['exact']}, norm={c['normalized']}, partial={c['partial']}, no={c['no']}) | "
        f"STRICT={g['strict_matches']}/27 ({g['strict_rate']:.1%}) | "
        f"LENIENT={g['lenient_matches']}/27 ({g['lenient_rate']:.1%}) | "
        f"per_doc=[{per_doc_str}]"
    )
    return ok, msg


def test_t5_mismatch_csv(eval_payload: dict[str, Any], non_matches: list[dict[str, Any]]) -> tuple[bool, str]:
    if not REVIEW_CSV.is_file():
        return False, f"Missing {REVIEW_CSV}"

    with open(REVIEW_CSV, encoding="utf-8", newline="") as fh:
        csv_rows = list(csv.DictReader(fh))

    required_cols = {
        "dataset", "doc", "field", "predicted_value", "reference_value",
        "predicted_quote", "reference_quote", "rule_result", "who_is_right",
    }
    if not csv_rows:
        return False, "Mismatch CSV has 0 rows."
    cols = set(csv_rows[0].keys())
    missing_cols = required_cols - cols
    if missing_cols:
        return False, f"Missing columns in mismatch CSV: {sorted(missing_cols)}"

    empty_who = all(r.get("who_is_right", "") == "" for r in csv_rows)
    s = eval_payload["silver"]
    g = eval_payload["gold"]
    expected_rows = (
        s["counts"]["partial"]
        + s["counts"]["no"]
        + s["strict"]["fp"] - (s["counts"]["partial"] + s["counts"]["no"])  # over NOT_PRESENT FPs
        + s["unclear_rows"]
        + g["counts"]["partial"]
        + g["counts"]["no"]
    )
    # Wait: count exact expected cleanly from non_matches list returned by evaluate_silver + evaluate_gold
    expected_from_eval = len(non_matches)
    all_match_count = len(csv_rows) == expected_from_eval

    ok = empty_who and all_match_count and expected_from_eval > 0
    return ok, (
        f"rows={len(csv_rows)} (expected {expected_from_eval}: "
        f"silver_strict_non_matches+unclear + gold_strict_non_matches), "
        f"who_is_right_all_empty={empty_who}, cols_ok=True"
    )


def test_t6_budget_and_cached_repeat(first_run_new_calls: int) -> tuple[bool, str]:
    client = GeminiClient()
    before = client.api_calls_made
    payload_repeat, _ = run_eval(use_snapshot=True, client=client)
    # Also verify GeminiClient disk cache directly on silver+gold if already cached in bulk/main
    with open(SILVER_CSV, encoding="utf-8-sig", newline="") as fh:
        silver_docs = sorted({r["doc_id"].strip() for r in csv.DictReader(fh)})
    with open(GOLD_CSV, encoding="utf-8-sig", newline="") as fh:
        gold_docs = sorted({(r.get("document_id") or r.get("\ufeffdocument_id") or "").strip() for r in csv.DictReader(fh)})
    _, direct_cache_new_calls = load_cached_extractions(silver_docs + gold_docs, client=client, use_snapshot=False)
    repeat_calls = client.api_calls_made - before
    ok = first_run_new_calls <= 20 and payload_repeat["new_live_calls"] == 0 and direct_cache_new_calls == 0 and repeat_calls == 0
    return ok, (
        f"first_run_new_calls={first_run_new_calls} (limit <=20); "
        f"cached_repeat_new_calls={repeat_calls} (snapshot={payload_repeat['new_live_calls']}, "
        f"direct_gemini_cache={direct_cache_new_calls}, cache_hits={client.cache_hits})"
    )


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("=" * 92)
    print("STAGE 3a-fix TEST SUITE: Transparent Value Matcher & Re-Scoring")
    print("=" * 92)

    client = GeminiClient(min_interval_seconds=8.0, request_timeout=90.0)
    eval_payload, non_matches = run_eval(use_snapshot=True, client=client)

    t1_ok, t1_msg = test_t1_key_leaks()
    print(f"[{'PASS' if t1_ok else 'FAIL'}] T1 Key leak scan: {t1_msg}")

    t2_ok, t2_msg = test_t2_matcher_unit_tests()
    print(f"[{'PASS' if t2_ok else 'FAIL'}] T2 Matcher unit tests (no API): {t2_msg}")

    t3_ok, t3_msg = test_t3_silver(eval_payload)
    print(f"[{'PASS' if t3_ok else 'FAIL'}] T3 Silver strict & lenient F1: {t3_msg}")

    t4_ok, t4_msg = test_t4_gold(eval_payload)
    print(f"[{'PASS' if t4_ok else 'FAIL'}] T4 Human gold strict & lenient rate: {t4_msg}")

    t5_ok, t5_msg = test_t5_mismatch_csv(eval_payload, non_matches)
    print(f"[{'PASS' if t5_ok else 'FAIL'}] T5 Mismatch CSV completeness: {t5_msg}")

    t6_ok, t6_msg = test_t6_budget_and_cached_repeat(eval_payload["new_live_calls"])
    print(f"[{'PASS' if t6_ok else 'FAIL'}] T6 Budget & cached repeat: {t6_msg}")

    t1_post_ok, t1_post_msg = test_t1_key_leaks()
    print(f"[{'PASS' if t1_post_ok else 'FAIL'}] T1 Post-run leak scan: {t1_post_msg}")

    # Honest plain-words verdict
    s_len_f1 = eval_payload["silver"]["lenient"]["f1"]
    s_str_f1 = eval_payload["silver"]["strict"]["f1"]
    g_len = eval_payload["gold"]["lenient_rate"]
    verdict = "good" if (s_len_f1 >= 0.80 and eval_payload["silver"]["strict"]["precision"] >= 0.60) else "risky"
    print(
        f"\nPLAIN-WORDS VERDICT: {verdict.upper()} — Silver strict F1 is {s_str_f1:.1%} and lenient F1 is {s_len_f1:.1%} "
        f"(gold strict={eval_payload['gold']['strict_rate']:.1%}, lenient={g_len:.1%}); "
        f"review {len(non_matches)} non-matches in {REVIEW_CSV.name} (mark who_is_right)."
    )

    overall = t1_ok and t1_post_ok and t2_ok and t3_ok and t4_ok and t5_ok and t6_ok
    print(f"\nOVERALL STAGE 3a-fix SUITE: {'PASS' if overall else 'FAIL'}")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
