"""scripts/test_4a_risk.py

Verification suite for Stage 4a (risk clause classifier).
Prints PASS/FAIL/INCONCLUSIVE for T1-T6, separate TARGET MET / TARGET MISSED lines for T7,
and the required silver-vs-silver honesty lines at the end.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.build_risk_final import check_final_counts, check_r3_rationales
from src.llm.gemini_client import GeminiClient, get_api_key, load_model_config
from src.risk.classify import classify_clauses, load_risk_config
from src.risk.evaluate import (
    compute_metrics,
    evaluate_split,
    format_metrics_summary,
    load_final_rows,
    load_prediction_rows,
    load_split_map,
    pred_csv_path,
)

RUNS_META_PATH = ROOT / "data" / "processed" / "risk_4a_runs.json"


def _emit(tid: str, status: str, detail: str) -> None:
    print(f"{tid} {status} | {detail}")


def run_t1_key_leak_scan() -> tuple[str, str]:
    try:
        api_key = get_api_key()
    except Exception as exc:
        return "INCONCLUSIVE", f"Cannot obtain GEMINI_API_KEY to scan: {exc}"
    if not api_key or len(api_key) < 8:
        return "INCONCLUSIVE", "GEMINI_API_KEY too short/missing."

    key_bytes = api_key.encode("utf-8")
    scan_roots = ("data/processed", "scripts", "src", "config", "docs")
    scanned = 0
    leaked_files: list[str] = []

    for rel_dir in scan_roots:
        base = ROOT / rel_dir
        if not base.is_dir():
            continue
        for p in base.rglob("*"):
            if not p.is_file():
                continue
            scanned += 1
            try:
                data = p.read_bytes()
            except OSError:
                continue
            if key_bytes in data:
                leaked_files.append(str(p.relative_to(ROOT)))

    if leaked_files:
        return "FAIL", f"Scanned {scanned} files across 5 dirs; key found in {leaked_files}"
    return "PASS", f"Scanned {scanned} files across data/processed, scripts, src, config, docs; 0 leaks"


def run_t2_unit_tests() -> tuple[str, str]:
    cfg = load_risk_config()
    checks: list[tuple[str, bool, str]] = []

    # 1. Invalid JSON retry (succeeds on 2nd try)
    attempt_counter = {"n": 0}

    def retry_then_ok_llm(prompt: str) -> tuple[str, str]:
        attempt_counter["n"] += 1
        if attempt_counter["n"] == 1:
            return "NOT VALID JSON AT ALL", "fake-bulk"
        return (
            json.dumps([
                {
                    "clause_id": "U1",
                    "category": "Repayment",
                    "severity": "Medium",
                    "rationale": "Monthly payment schedule.",
                    "applied_rule": "none",
                }
            ]),
            "fake-bulk",
        )

    r_retry = classify_clauses(
        "sec_agreement",
        [{"clause_id": "U1", "clause_text": "Pay monthly.", "page": "p.1"}],
        config=cfg,
        llm_fn=retry_then_ok_llm,
    )
    checks.append(
        (
            "invalid_json_retry_succeeds",
            attempt_counter["n"] == 2
            and r_retry["calls_made"] == 2
            and r_retry["results"][0]["category"] == "Repayment"
            and r_retry["results"][0]["severity"] == "Medium",
            f"attempts={attempt_counter['n']} res={r_retry['results']}",
        )
    )

    # 2. Persistent invalid JSON -> unclassified after retry
    bad_calls = {"n": 0}

    def always_bad_llm(prompt: str) -> tuple[str, str]:
        bad_calls["n"] += 1
        return "{broken json", "fake-bulk"

    r_fail_json = classify_clauses(
        "sec_agreement",
        [{"clause_id": "U2", "clause_text": "Default after 10 days."}],
        config=cfg,
        llm_fn=always_bad_llm,
    )
    checks.append(
        (
            "persistent_invalid_json_unclassified",
            bad_calls["n"] == 2
            and r_fail_json["results"][0]["category"] == "unclassified"
            and r_fail_json["results"][0]["severity"] == "unclassified",
            f"calls={bad_calls['n']} res={r_fail_json['results']}",
        )
    )

    # 3. Invalid category / severity -> unclassified, plus invented-number flag & silver non-leak
    captured_prompts: list[str] = []

    def inspect_prompt_and_respond(prompt: str) -> tuple[str, str]:
        captured_prompts.append(prompt)
        return (
            json.dumps([
                {
                    "clause_id": "U3",
                    "category": "ImaginaryCategory",
                    "severity": "Extreme",
                    "rationale": "Imposes a 25% surcharge and $999 penalty.",
                    "applied_rule": "R2",
                },
                {
                    "clause_id": "U4",
                    "category": "Default conditions",
                    "severity": "Medium",
                    "rationale": "Grants a 10 day cure period.",
                    "applied_rule": "R2",
                },
            ]),
            "fake-bulk",
        )

    sentinel_clauses = [
        {
            "clause_id": "U3",
            "clause_text": "Lender may inspect borrower records on reasonable notice.",
            "page": "p.4",
            "risk_category": "SENTINEL_ORIG_CAT_AAA",
            "severity": "SENTINEL_ORIG_SEV_AAA",
            "final_category": "SENTINEL_FINAL_CAT_BBB",
            "final_severity": "SENTINEL_FINAL_SEV_BBB",
            "rationale": "SENTINEL_SILVER_RATIONALE_UNIQUE_999",
        },
        {
            "clause_id": "U4",
            "clause_text": "Failure to pay continuing for 10 days after notice.",
            "page": "p.9",
            "final_category": "Default conditions",
            "final_severity": "Medium",
            "rationale": "SENTINEL_SILVER_RATIONALE_SECOND_888",
        },
    ]
    r_guard = classify_clauses(
        "indian_mitc",
        sentinel_clauses,
        config=cfg,
        llm_fn=inspect_prompt_and_respond,
    )
    prompt_text = captured_prompts[0] if captured_prompts else ""
    sentinels = [
        "SENTINEL_ORIG_CAT_AAA",
        "SENTINEL_ORIG_SEV_AAA",
        "SENTINEL_FINAL_CAT_BBB",
        "SENTINEL_FINAL_SEV_BBB",
        "SENTINEL_SILVER_RATIONALE_UNIQUE_999",
        "SENTINEL_SILVER_RATIONALE_SECOND_888",
    ]
    leaked_sentinels = [s for s in sentinels if s in prompt_text]
    res_u3, res_u4 = r_guard["results"][0], r_guard["results"][1]

    checks.append(
        (
            "invalid_cat_and_sev_unclassified",
            res_u3["category"] == "unclassified" and res_u3["severity"] == "unclassified",
            f"u3={res_u3}",
        )
    )
    checks.append(
        (
            "invented_number_flagged",
            res_u3["number_flag"] is True and len(res_u3["flagged_numbers"]) >= 1,
            f"u3_flag={res_u3['number_flag']} missing={res_u3['flagged_numbers']}",
        )
    )
    checks.append(
        (
            "valid_number_not_flagged",
            res_u4["number_flag"] is False and res_u4["flagged_numbers"] == [],
            f"u4_flag={res_u4['number_flag']} missing={res_u4['flagged_numbers']}",
        )
    )
    checks.append(
        (
            "silver_never_in_prompt",
            len(leaked_sentinels) == 0,
            f"leaked={leaked_sentinels}",
        )
    )

    failures = [f"{name} ({detail})" for name, passed, detail in checks if not passed]
    if failures:
        return "FAIL", f"{len(checks) - len(failures)}/{len(checks)} passed; failures={failures}"
    return "PASS", f"{len(checks)}/{len(checks)} offline unit checks passed (0 API calls)"


def run_t3_step0_checks() -> tuple[str, str]:
    ok_d, info_d = check_final_counts()
    ok_e, r3_cnt, r3_bad = check_r3_rationales()
    if ok_d and ok_e:
        return (
            "PASS",
            f"total={info_d['total']}, all 7 cat & 4 sev counts exact, R3 '[borrower-protective]' rationales={r3_cnt}/8",
        )
    return (
        "FAIL",
        f"counts_ok={ok_d} ({info_d['categories']} / {info_d['severities']}), r3_ok={ok_e} (count={r3_cnt}, bad={r3_bad})",
    )


def run_t4_dev_metrics() -> tuple[str, str, dict[str, Any] | None]:
    p_dev = pred_csv_path("dev")
    if not p_dev.is_file():
        return "FAIL", f"Missing {p_dev.relative_to(ROOT)} (run dev evaluation first)", None
    rows = load_prediction_rows("dev")
    m = compute_metrics(rows)
    prompt_ver = rows[0].get("prompt_version", "?") if rows else "?"
    summary = (
        f"n={m['n']} prompt={prompt_ver} | "
        f"cat_acc={m['category']['accuracy']*100:.1f}% cat_macroF1={m['category']['macro_f1']*100:.1f}% | "
        f"sev_exact={m['severity']['accuracy']*100:.1f}% sev_macroF1={m['severity']['macro_f1']*100:.1f}% "
        f"within_1={m['within_one_rate']*100:.1f}% | "
        f"crit_recall={m['critical_tp']}/{m['critical_support']} | num_flags={m['flagged_numbers']}"
    )
    ok = m["n"] == 143 and m["category"]["accuracy"] >= 0
    return ("PASS" if ok else "FAIL"), summary, m


def run_t5_test_metrics(force: bool) -> tuple[str, str, dict[str, Any] | None]:
    p_test = pred_csv_path("test")
    if not p_test.is_file() and not force:
        # First-time execution allowed if test hasn't been run yet
        client = GeminiClient()
        res = evaluate_split("test", client=client, force=False, save_outputs=True)
        m = res["metrics"]
    else:
        res = evaluate_split("test", force=force, save_outputs=force)
        m = res["metrics"]

    crit_str = f"{m['critical_tp']}/{m['critical_support']}"
    if m["critical_support"] < 5:
        crit_str += " (F1 omitted: <5 examples)"
    else:
        crit_str += f" (F1={m['critical_f1']*100:.1f}%)"

    summary = (
        f"n={m['n']} prompt={res['prompt_version']} reused_saved={res['reused_saved']} | "
        f"cat_acc={m['category']['accuracy']*100:.1f}% cat_macroF1={m['category']['macro_f1']*100:.1f}% | "
        f"sev_exact={m['severity']['accuracy']*100:.1f}% sev_macroF1={m['severity']['macro_f1']*100:.1f}% "
        f"within_1={m['within_one_rate']*100:.1f}% | "
        f"crit_recall={crit_str} | num_flags={m['flagged_numbers']}"
    )
    ok = m["n"] == 66
    return ("PASS" if ok else "FAIL"), summary, m


def run_t6_budget_and_cache() -> tuple[str, str]:
    cfg = load_risk_config()
    max_calls = int(cfg.get("max_calls", 40))
    configured_model = load_model_config().get(str(cfg.get("model_role", "bulk")), "gemini-3.5-flash-lite")

    # 1. Inspect recorded runs budget & model counts
    total_live = 0
    history: list[dict[str, Any]] = []
    if RUNS_META_PATH.is_file():
        history = json.loads(RUNS_META_PATH.read_text(encoding="utf-8"))
        total_live = sum(int(h.get("live_calls_made", 0)) for h in history)

    pred_models: Counter[str] = Counter()
    for sp in ("dev", "test"):
        p = pred_csv_path(sp)
        if p.is_file():
            for r in load_prediction_rows(sp):
                m_name = r.get("model_used", "")
                if m_name:
                    pred_models[m_name] += 1

    # 2. Cached repeat on one dev document batch must make 0 new live calls
    split_map = load_split_map()
    dev_sec_rows = [
        {"clause_id": r["clause_id"], "clause_text": r["clause_text"]}
        for r in load_final_rows()
        if split_map.get(r["doc_id"]) == "dev" and "/" in r["doc_id"]
    ][: int(cfg.get("batch_size", 12))]

    client = GeminiClient()
    repeat_res = classify_clauses(
        "sec_agreement",
        dev_sec_rows,
        client=client,
        config=cfg,
        prompt_version=str(cfg.get("prompt_version", "v1")),
    )
    repeat_live = int(repeat_res["live_calls_made"])

    batch_models: Counter[str] = Counter()
    for h in history:
        batch_models.update(h.get("model_used_counts", {}))
    fallback_batches = sum(cnt for m, cnt in batch_models.items() if m != configured_model)

    detail = (
        f"total_live_calls={total_live}/{max_calls}, cached_repeat_live_calls={repeat_live}, "
        f"configured={configured_model}, batch_model_counts={dict(batch_models)}, "
        f"row_model_counts={dict(pred_models)}, fallback_batches={fallback_batches}"
    )
    if fallback_batches > 0:
        detail += f" | WARNING: {fallback_batches} batch call(s) fell back from {configured_model}"

    ok = total_live <= max_calls and repeat_live == 0 and repeat_res["calls_made"] >= 1
    return ("PASS" if ok else "FAIL"), detail


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Stage 4a risk classifier test suite")
    parser.add_argument("--force", action="store_true", help="Allow rerunning test split even if risk_pred_test.csv exists")
    args = parser.parse_args()

    t1_st, t1_msg = run_t1_key_leak_scan()
    _emit("T1", t1_st, t1_msg)

    t2_st, t2_msg = run_t2_unit_tests()
    _emit("T2", t2_st, t2_msg)

    t3_st, t3_msg = run_t3_step0_checks()
    _emit("T3", t3_st, t3_msg)

    t4_st, t4_msg, _ = run_t4_dev_metrics()
    _emit("T4", t4_st, t4_msg)

    t5_st, t5_msg, test_m = run_t5_test_metrics(force=args.force)
    _emit("T5", t5_st, t5_msg)

    t6_st, t6_msg = run_t6_budget_and_cache()
    _emit("T6", t6_st, t6_msg)

    # T7 target lines — NEVER print PASS for a target!
    if test_m is None:
        print("T7_CATEGORY TARGET MISSED | no test metrics available")
        print("T7_SEVERITY TARGET MISSED | no test metrics available")
    else:
        cat_f1 = test_m["category"]["macro_f1"]
        sev_f1 = test_m["severity"]["macro_f1"]
        cat_tag = "TARGET MET" if cat_f1 >= 0.70 else "TARGET MISSED"
        sev_tag = "TARGET MET" if sev_f1 >= 0.70 else "TARGET MISSED"
        print(f"T7_CATEGORY {cat_tag} | test category macro-F1={cat_f1*100:.1f}% (target >= 70.0%)")
        print(f"T7_SEVERITY {sev_tag} | test severity macro-F1={sev_f1*100:.1f}% (target >= 70.0%)")

    print("\nHonesty notes:")
    print("- Silver-vs-silver & optimistic: labels came from ChatGPT (docs 01-03) and an unknown Antigravity model, the classifier is a Gemini bulk model, and rules R1-R3 were derived from the same rows.")
    print("- No human gold yet: all metrics measure agreement with LLM-assisted silver labels (risk_final.csv), not human-annotated gold.")


if __name__ == "__main__":
    main()
