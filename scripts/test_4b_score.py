"""scripts/test_4b_score.py

Verification suite for Stage 4b & 4b-fix (ZERO API calls).
Keeps all mean_top3 tests (T1-T8), tests padded_top3 worked example, dilution=0,
monotonicity, determinism, transparency fields, and evaluates the pre-registered
decision rule cleanly.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_4b_scores import load_clauses_by_doc  # noqa: E402
from src.llm.gemini_client import get_api_key  # noqa: E402
from src.risk.score import CANONICAL_CATEGORIES, LEVEL_ORDER, load_score_config, score_document  # noqa: E402

LLM_LOG_PATH = ROOT / "data" / "processed" / "llm_log.csv"
NEXT_SEVERITY = {"Low": "Medium", "Medium": "High", "High": "Critical"}

WORKED_EXAMPLE_CLAUSES = [
    {"clause_id": "D1", "category": "Default conditions", "severity": "High", "quote": "d high", "page": 1, "rationale": ""},
    {"clause_id": "D2", "category": "Default conditions", "severity": "Medium", "quote": "d med", "page": 2, "rationale": ""},
    {"clause_id": "P1", "category": "Penalties and charges", "severity": "Low", "quote": "p low1", "page": 3, "rationale": ""},
    {"clause_id": "P2", "category": "Penalties and charges", "severity": "Low", "quote": "p low2", "page": 4, "rationale": ""},
    {"clause_id": "P3", "category": "Penalties and charges", "severity": "Medium", "quote": "p med", "page": 5, "rationale": ""},
    {"clause_id": "P4", "category": "Penalties and charges", "severity": "High", "quote": "p high", "page": 6, "rationale": ""},
    {"clause_id": "F1", "category": "Financial terms", "severity": "Medium", "quote": "f med", "page": 7, "rationale": ""},
    {"clause_id": "C1", "category": "Collateral", "severity": "High", "quote": "c high", "page": 8, "rationale": ""},
    {"clause_id": "T1", "category": "Termination", "severity": "Critical", "quote": "t crit", "page": 9, "rationale": ""},
    {"clause_id": "V1", "category": "Covenants", "severity": "Low", "quote": "v low", "page": 10, "rationale": ""},
]


def _emit(tid: str, status: str, detail: str) -> None:
    print(f"{tid} {status} | {detail}")


def _count_llm_log_rows() -> int:
    if not LLM_LOG_PATH.is_file():
        return 0
    with LLM_LOG_PATH.open("r", encoding="utf-8", errors="ignore") as fh:
        return sum(1 for _ in fh)


def run_t1_key_leak_scan() -> tuple[str, str]:
    try:
        api_key = get_api_key()
    except Exception as exc:
        return "FAIL", f"Cannot load GEMINI_API_KEY for scan: {exc}"
    if not api_key or len(api_key) < 8:
        return "FAIL", "GEMINI_API_KEY missing or invalid"

    key_bytes = api_key.encode("utf-8")
    scanned = 0
    leaks: list[str] = []
    for rel_dir in ("data/processed", "scripts", "src", "config", "docs"):
        base = ROOT / rel_dir
        if not base.is_dir():
            continue
        for p in base.rglob("*"):
            if not p.is_file():
                continue
            scanned += 1
            try:
                if key_bytes in p.read_bytes():
                    leaks.append(str(p.relative_to(ROOT)))
            except OSError:
                continue
    if leaks:
        return "FAIL", f"Scanned {scanned} files; key leaked in {leaks}"
    return "PASS", f"Scanned {scanned} files across data/processed, scripts, src, config, docs; 0 leaks"


def run_t2_config_check() -> tuple[str, str]:
    cfg = load_score_config()
    weights = cfg.get("weights", {})
    w_sum = sum(float(v) for v in weights.values())
    th = cfg.get("thresholds", {})
    low_m = float(th.get("low_max", 0))
    mod_m = float(th.get("moderate_max", 0))
    high_m = float(th.get("high_max", 0))
    ordered = 0 < low_m < mod_m < high_m <= 100
    ok = (
        abs(w_sum - 1.0) < 1e-9
        and set(weights.keys()) == set(CANONICAL_CATEGORIES)
        and ordered
        and cfg.get("method") in {"mean_top3", "padded_top3"}
        and int(cfg.get("top_n", 0)) == 3
    )
    return (
        "PASS" if ok else "FAIL",
        f"weights_sum={w_sum:.6f}, thresholds=({low_m}, {mod_m}, {high_m}), method={cfg.get('method')}, floor={cfg.get('floor_rule')}",
    )


def run_t3_mean_worked_example() -> tuple[str, str]:
    cfg = dict(load_score_config(), method="mean_top3")
    res = score_document(WORKED_EXAMPLE_CLAUSES, cfg)
    cat_map = {c["name"]: c for c in res["categories"]}
    risks = [cat_map[c]["risk"] for c in CANONICAL_CATEGORIES]
    expected_risks = [0.625, 0.5, 0.5, 0.0, 0.75, 1.0, 0.25]
    risks_ok = all(abs(a - b) < 1e-6 for a, b in zip(risks, expected_risks))

    def_clauses = {c["clause_id"]: c["contribution"] for c in cat_map["Default conditions"]["top_clauses"]}
    def_ok = abs(def_clauses["D1"] - 9.375) < 1e-6 and abs(def_clauses["D2"] - 6.25) < 1e-6
    contrib_sum = sum(c["contribution"] for cat in res["categories"] for c in cat["top_clauses"])
    sum_ok = abs(round(contrib_sum, 1) - res["score"]) < 1e-6 and abs(contrib_sum - res["raw_score"]) < 1e-6

    ok = (
        res["score"] == 51.9
        and res["level"] == "High"
        and res["level_before_floor"] == "High"
        and res["critical_floor_applied"] is False
        and "Repayment" in res["missing_categories"]
        and risks_ok
        and def_ok
        and sum_ok
    )
    return (
        "PASS" if ok else "FAIL",
        f"mean_top3 worked example: score={res['score']}, level={res['level']}, contrib_sum={contrib_sum:.3f}",
    )


def _check_determinism_and_extremes(method: str) -> tuple[bool, str]:
    cfg = dict(load_score_config(), method=method)
    silver_docs, _ = load_clauses_by_doc("silver")
    rng = random.Random(42)

    shuffle_ok = True
    for clauses in silver_docs.values():
        ref = score_document(clauses, cfg)
        for _ in range(3):
            shuffled = list(clauses)
            rng.shuffle(shuffled)
            if score_document(shuffled, cfg) != ref:
                shuffle_ok = False
                break

    empty_res = score_document([], cfg)
    empty_ok = (
        empty_res["score"] == 0.0
        and empty_res["level"] == "Low"
        and len(empty_res["missing_categories"]) == 7
        and all(c["evidence_strength"] == "none" for c in empty_res["categories"])
    )

    all_crit = [
        {"clause_id": f"K{i}", "category": cat, "severity": "Critical", "quote": "q", "page": i, "rationale": ""}
        for i, cat in enumerate(CANONICAL_CATEGORIES, 1)
    ]
    max_res = score_document(all_crit, cfg)
    expected_max_score = 50.0 if method == "padded_top3" else 100.0
    expected_max_level = "High" if method == "padded_top3" else "Critical"
    max_ok = max_res["score"] == expected_max_score and max_res["level"] == expected_max_level

    # Also verify "not available" page display & evidence_strength levels
    no_page_doc = [
        {"clause_id": "X1", "category": "Default conditions", "severity": "High", "quote": "q1", "page": "", "rationale": ""},
        {"clause_id": "X2", "category": "Covenants", "severity": "Low", "quote": "q2", "page": 1, "rationale": ""},
        {"clause_id": "X3", "category": "Covenants", "severity": "Low", "quote": "q3", "page": 2, "rationale": ""},
        {"clause_id": "X4", "category": "Covenants", "severity": "Low", "quote": "q4", "page": 3, "rationale": ""},
    ]
    np_res = score_document(no_page_doc, cfg)
    np_cats = {c["name"]: c for c in np_res["categories"]}
    page_ok = (
        any(d["page"] == "not available" for d in np_res["top_drivers"])
        and np_cats["Default conditions"]["evidence_strength"] == "limited"
        and np_cats["Covenants"]["evidence_strength"] == "strong"
        and np_cats["Repayment"]["evidence_strength"] == "none"
    )

    ok = shuffle_ok and empty_ok and max_ok and page_ok
    return ok, f"{method}: shuffle={shuffle_ok}, empty=({empty_res['score']},{empty_res['level']}), 1_crit_per_cat=({max_res['score']},{max_res['level']}), transparency={page_ok}"


def _check_monotonicity(method: str) -> tuple[bool, int, int]:
    cfg = dict(load_score_config(), method=method)
    silver_docs, _ = load_clauses_by_doc("silver")
    checked = 0
    violations = 0
    for clauses in silver_docs.values():
        base = score_document(clauses, cfg)
        for idx, cl in enumerate(clauses):
            sev = cl["severity"]
            if sev not in NEXT_SEVERITY:
                continue
            checked += 1
            upgraded = [dict(c) for c in clauses]
            upgraded[idx]["severity"] = NEXT_SEVERITY[sev]
            new_res = score_document(upgraded, cfg)
            if (
                new_res["raw_score"] + 1e-9 < base["raw_score"]
                or new_res["score"] < base["score"]
                or LEVEL_ORDER[new_res["level"]] < LEVEL_ORDER[base["level"]]
            ):
                violations += 1
    return violations == 0 and checked > 0, checked, violations


def run_t4_determinism() -> tuple[str, str]:
    ok_m, msg_m = _check_determinism_and_extremes("mean_top3")
    ok_p, msg_p = _check_determinism_and_extremes("padded_top3")
    return ("PASS" if (ok_m and ok_p) else "FAIL"), f"{msg_m} | {msg_p}"


def run_t5_monotonicity() -> tuple[str, str]:
    ok_m, chk_m, vio_m = _check_monotonicity("mean_top3")
    ok_p, chk_p, vio_p = _check_monotonicity("padded_top3")
    return (
        "PASS" if (ok_m and ok_p) else "FAIL",
        f"mean_top3 ({chk_m} upgrades, violations={vio_m}); padded_top3 ({chk_p} upgrades, violations={vio_p})",
    )


def run_t6_floor_rule() -> tuple[str, str]:
    cfg_floor = dict(load_score_config(), method="mean_top3")
    cfg_no_floor = dict(cfg_floor, floor_rule=False)
    single_crit = [
        {"clause_id": "X1", "category": "Covenants", "severity": "Critical", "quote": "Seizure without notice.", "page": 1, "rationale": ""}
    ]
    res_on = score_document(single_crit, cfg_floor)
    res_off = score_document(single_crit, cfg_no_floor)

    ok = (
        res_on["score"] == 5.0
        and res_on["level_before_floor"] == "Low"
        and LEVEL_ORDER[res_on["level"]] >= LEVEL_ORDER["High"]
        and res_on["critical_floor_applied"] is True
        and "Level raised to High because a Critical clause was found; the score alone would be Low." == res_on["level_explanation"]
        and res_off["level"] == "Low"
        and res_off["critical_floor_applied"] is False
    )
    return (
        "PASS" if ok else "FAIL",
        f"single Critical Covenants clause: score={res_on['score']}, with_floor=({res_on['level']}, "
        f"before={res_on['level_before_floor']}, applied={res_on['critical_floor_applied']}), without_floor={res_off['level']}",
    )


def run_t7_dilution_info() -> None:
    cfg_base = load_score_config()
    one_high = [{"clause_id": "H1", "category": "Default conditions", "severity": "High", "quote": "Default", "page": 1, "rationale": ""}]
    with_two_low = one_high + [
        {"clause_id": "L1", "category": "Default conditions", "severity": "Low", "quote": "Notice 1", "page": 2, "rationale": ""},
        {"clause_id": "L2", "category": "Default conditions", "severity": "Low", "quote": "Notice 2", "page": 3, "rationale": ""},
    ]
    lines: list[str] = []
    for method in ("mean_top3", "padded_top3", "max", "blend"):
        mcfg = dict(cfg_base, method=method, floor_rule=False)
        s1 = score_document(one_high, mcfg)["score"]
        s2 = score_document(with_two_low, mcfg)["score"]
        lines.append(f"{method}: {s1:.1f} -> {s2:.1f} (delta={s2 - s1:+.1f})")
    print(
        "T7 INFO (dilution test: 1 High -> 1 High + 2 Low in Default conditions) | "
        + "; ".join(lines)
        + " | mean_top3 and blend lower the score when harmless Low clauses are added; padded_top3 and max are immune (delta=0.0)."
    )


def run_t9_padded_worked_example_and_zero_dilution() -> tuple[str, str]:
    cfg = dict(load_score_config(), method="padded_top3")
    res = score_document(WORKED_EXAMPLE_CLAUSES, cfg)
    cat_map = {c["name"]: c for c in res["categories"]}
    risks_3dp = [round(cat_map[c]["risk"], 3) for c in CANONICAL_CATEGORIES]
    expected_3dp = [0.5, 0.5, 0.333, 0.0, 0.417, 0.5, 0.25]
    risks_ok = risks_3dp == expected_3dp

    # Verify padding lines and sum of contributions
    pad_lines = [
        c
        for cat in res["categories"]
        for c in cat["top_clauses"]
        if c.get("quote") == "padding (missing clauses counted as Low)"
    ]
    contrib_sum = sum(c["contribution"] for cat in res["categories"] for c in cat["top_clauses"])
    sum_ok = abs(round(contrib_sum, 1) - res["score"]) < 1e-6 and abs(contrib_sum - res["raw_score"]) < 1e-6

    # Verify dilution = 0 across ALL categories and starting counts 1 or 2 with any severity
    dilution_zero = True
    for cat in CANONICAL_CATEGORIES:
        for base_sevs in (["Low"], ["Medium"], ["High"], ["Critical"], ["High", "Medium"], ["Critical", "Low"]):
            base_clauses = [
                {"clause_id": f"B{i}", "category": cat, "severity": s, "quote": "b", "page": i + 1, "rationale": ""}
                for i, s in enumerate(base_sevs)
            ]
            s_base = score_document(base_clauses, cfg)["raw_score"]
            for extra in (1, 2, 3):
                added = base_clauses + [
                    {"clause_id": f"L{j}", "category": cat, "severity": "Low", "quote": "l", "page": 50 + j, "rationale": ""}
                    for j in range(extra)
                ]
                if abs(score_document(added, cfg)["raw_score"] - s_base) > 1e-9:
                    dilution_zero = False

    # Verify single-clause category max risk <= 0.5
    single_crit_max_risk = max(
        c["risk"]
        for c in score_document(
            [{"clause_id": "S1", "category": "Default conditions", "severity": "Critical", "quote": "q", "page": 1, "rationale": ""}],
            cfg,
        )["categories"]
    )

    ok = (
        risks_ok
        and res["score"] == 37.9
        and res["level_before_floor"] == "Moderate"
        and res["level"] == "High"
        and res["critical_floor_applied"] is True
        and res["level_explanation"] == "Level raised to High because a Critical clause was found; the score alone would be Moderate."
        and len(pad_lines) == 5  # Default(1), Financial(2), Collateral(2), Termination(2), Covenants(2); Penalties>=3, Repayment=0
        and sum_ok
        and dilution_zero
        and single_crit_max_risk <= 0.5 + 1e-9
    )
    return (
        "PASS" if ok else "FAIL",
        f"padded_top3 worked example: score={res['score']}, before={res['level_before_floor']}, after={res['level']}, "
        f"risks={risks_3dp}, pad_lines={len(pad_lines)}, contrib_sum={contrib_sum:.4f}, "
        f"dilution_zero={dilution_zero}, max_1clause_risk={single_crit_max_risk:.3f}",
    )


def evaluate_pre_registered_decision_rule() -> tuple[bool, bool, bool, bool]:
    cfg_p = dict(load_score_config(), method="padded_top3")
    # (a) adding Low clauses to a category with 1 or 2 clauses never changes the score
    a_ok = True
    for cat in CANONICAL_CATEGORIES:
        for base_sevs in (["Low"], ["Medium"], ["High"], ["Critical"], ["High", "Medium"]):
            base_clauses = [
                {"clause_id": f"A{i}", "category": cat, "severity": s, "quote": "a", "page": i + 1, "rationale": ""}
                for i, s in enumerate(base_sevs)
            ]
            s0 = score_document(base_clauses, cfg_p)["score"]
            for n_add in (1, 2):
                added = base_clauses + [
                    {"clause_id": f"X{j}", "category": cat, "severity": "Low", "quote": "x", "page": 20 + j, "rationale": ""}
                    for j in range(n_add)
                ]
                if score_document(added, cfg_p)["score"] != s0:
                    a_ok = False
    # (b) monotonic on all clauses of all 13 docs
    b_ok, _, _ = _check_monotonicity("padded_top3")
    # (c) 1-clause category risk <= 0.5
    c_ok = True
    for cat in CANONICAL_CATEGORIES:
        for sev in ("Low", "Medium", "High", "Critical"):
            res = score_document(
                [{"clause_id": "C1", "category": cat, "severity": sev, "quote": "q", "page": 1, "rationale": ""}],
                cfg_p,
            )
            cat_r = next(c["risk"] for c in res["categories"] if c["name"] == cat)
            if cat_r > 0.5 + 1e-9:
                c_ok = False
    return (a_ok and b_ok and c_ok), a_ok, b_ok, c_ok


def run_t10_top_driver_per_category() -> tuple[str, str]:
    cfg = dict(load_score_config(), method="padded_top3")
    res = score_document(WORKED_EXAMPLE_CLAUSES, cfg)
    drivers = res.get("top_driver_per_category")
    if not isinstance(drivers, list) or len(drivers) != len(CANONICAL_CATEGORIES):
        return "FAIL", f"expected {len(CANONICAL_CATEGORIES)} entries in top_driver_per_category, got {drivers!r}"
    by_cat = {d["category"]: d for d in drivers}
    cats_ok = [d["category"] for d in drivers] == CANONICAL_CATEGORIES
    repay = by_cat.get("Repayment", {})
    repay_ok = (
        repay.get("clause_id") is None
        and repay.get("quote") == "No clause found"
        and repay.get("contribution") == 0.0
    )
    default_d = by_cat.get("Default conditions", {})
    default_ok = (
        default_d.get("clause_id") == "D1"
        and default_d.get("severity") == "High"
        and str(default_d.get("page")) == "1"
        and default_d.get("quote") == "d high"
        and default_d.get("contribution", 0.0) > 0.0
    )
    term_d = by_cat.get("Termination", {})
    term_ok = (
        term_d.get("clause_id") == "T1"
        and term_d.get("severity") == "Critical"
        and str(term_d.get("page")) == "9"
        and term_d.get("contribution", 0.0) > 0.0
    )
    ok = cats_ok and repay_ok and default_ok and term_ok
    return (
        "PASS" if ok else "FAIL",
        f"top_driver_per_category: entries={len(drivers)}, cats_ok={cats_ok}, empty_ok={repay_ok}, populated_ok={default_ok and term_ok}",
    )


def main() -> None:
    rows_before = _count_llm_log_rows()

    st1, msg1 = run_t1_key_leak_scan()
    _emit("T1", st1, msg1)

    st2, msg2 = run_t2_config_check()
    _emit("T2", st2, msg2)

    st3, msg3 = run_t3_mean_worked_example()
    _emit("T3", st3, msg3)

    st4, msg4 = run_t4_determinism()
    _emit("T4", st4, msg4)

    st5, msg5 = run_t5_monotonicity()
    _emit("T5", st5, msg5)

    st6, msg6 = run_t6_floor_rule()
    _emit("T6", st6, msg6)

    run_t7_dilution_info()

    st9, msg9 = run_t9_padded_worked_example_and_zero_dilution()
    _emit("T9", st9, msg9)

    st10, msg10 = run_t10_top_driver_per_category()
    _emit("T10", st10, msg10)

    adopted, chk_a, chk_b, chk_c = evaluate_pre_registered_decision_rule()
    status_word = "ADOPTED" if adopted else "NOT ADOPTED"
    active_default = load_score_config().get("method")
    print(
        f"DECISION_RULE INFO: {status_word} | (a) zero_dilution_1_or_2={chk_a}, "
        f"(b) monotonic_all_13_docs={chk_b}, (c) single_clause_max_risk_le_0.5={chk_c} | "
        f"config/score.yaml default={active_default}"
    )

    rows_after = _count_llm_log_rows()
    t8_ok = rows_after == rows_before
    _emit("T8", "PASS" if t8_ok else "FAIL", f"zero API calls; llm_log.csv rows before={rows_before}, after={rows_after}")

    print("\nHonesty notes:")
    print("- The 209 clauses are only clauses a labeler selected as risk clauses, so a full-document scan will give different mixes.")
    print("- SEC agreements and MITCs are not directly comparable (MITCs have few covenant clauses).")
    print("- Thresholds come from the plan, not calibrated on data.")
    print("- Scores built from silver labels or classifier predictions; no human-validated ranking yet.")


if __name__ == "__main__":
    main()
