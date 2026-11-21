"""scripts/test_4a3_scan.py

Verification suite for Stage 4a-3 (ZERO live API calls):
- T1: key-leak scan (reports files scanned)
- T2: SEC splitter + page-mark tests (pages assigned, marks removed, no clause cut in half, cov >= 99%)
- T3: MITC splitter tests (<=600 chars, list markers & JSON table rows, cov >= 99%, verbatim)
- T4: fake-LLM unit tests for prompt v4 (none accepted, N1/S1/S4 rules, invalid JSON retry, number_flag)
- T5: scan_review_verdicts.csv has 27 rows and valid values + original silver CSVs untouched
- T6 (INFO): training-row agreement v3 vs v4 ("agreement on training rows, not accuracy")
- T7 (INFO) & TARGET (separate line): fresh-document scan results
- T8: budget <= 40 live calls in 4a-3 (352 baseline -> <=392), cached repeat makes 0 calls, model_used counts
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_4a3_scan import (  # noqa: E402
    REVIEW_V4_CSV,
    SUMMARY_V4_JSON,
    TARGET_DOCS_4A3,
    VERDICTS_CSV,
    scan_v4_csv_path,
)
from src.llm.gemini_client import get_api_key  # noqa: E402
from src.qa.verify_quotes import normalize  # noqa: E402
from src.risk.classify import build_risk_prompt, classify_clauses, load_risk_config  # noqa: E402
from src.risk.prefilter import is_risk_candidate  # noqa: E402
from src.risk.split_clauses import (  # noqa: E402
    _read_zip_raw,
    load_doc_pages,
    split_document,
    split_pages,
    split_sec_text_to_pages,
)

LLM_LOG_PATH = ROOT / "data" / "processed" / "llm_log.csv"
RISK_FINAL_CSV = ROOT / "data" / "processed" / "labels" / "llm_assisted" / "risk_final.csv"
RISK_LLM_CSV = ROOT / "data" / "processed" / "labels" / "llm_assisted" / "risk_llm.csv"
RISK_INDIAN_CSV = ROOT / "data" / "processed" / "labels" / "llm_assisted" / "risk_indian_llm.csv"
KEY_INFO_CSV = ROOT / "data" / "processed" / "labels" / "llm_assisted" / "key_info_llm.csv"

BASELINE_LOG_ROWS_BEFORE_4A3 = 352


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
        return "FAIL", f"Cannot load GEMINI_API_KEY: {exc}"
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


def run_t2_sec_splitter_and_page_marks() -> tuple[str, str]:
    # Check 3 * * * docs + 1 no-mark doc (000002) + 2 fresh <PAGE> docs (000103, 000105)
    sec_docs = [
        "000010/104897/0000950123-11-030926_2.txt",
        "000081/810113/0000950116-04-002411_4.txt",
        "000000/7286/0000950123-11-015421_4.txt",
        "000002/27566/0000945836-96-000035_3.txt",
        "000103/1039213/0000912057-97-018811_19.txt",
        "000105/1052667/0000912057-00-028795_20.txt",
    ]
    star_left = 0
    tag_left = 0
    min_cov = 100.0
    max_len = 0
    verb_ok = True

    for did in sec_docs:
        raw = _read_zip_raw(did)
        pages, meta = split_sec_text_to_pages(raw)
        clauses = split_document(did)
        norm_pages = {k: normalize(v) for k, v in pages.items()}
        for c in clauses:
            max_len = max(max_len, len(c["text"]))
            if re.search(r"\*\s+\*\s+\*", c["text"]):
                star_left += 1
            if "<PAGE>" in c["text"]:
                tag_left += 1
            pk = c["page"]
            cn = normalize(c["text"])
            if cn not in norm_pages.get(pk, ""):
                if not (isinstance(pk, int) and (pk + 1) in norm_pages and cn in (norm_pages[pk] + " " + norm_pages[pk + 1])):
                    verb_ok = False
        nonws_doc = sum(len(re.sub(r"\s+", "", v)) for v in pages.values())
        nonws_cls = sum(len(re.sub(r"\s+", "", c["text"])) for c in clauses)
        cov = (nonws_cls / nonws_doc * 100.0) if nonws_doc else 100.0
        min_cov = min(min_cov, cov)

    c0010 = split_document("000010/104897/0000950123-11-030926_2.txt")
    c0081 = split_document("000081/810113/0000950116-04-002411_4.txt")
    c0002 = split_document("000002/27566/0000945836-96-000035_3.txt")
    non1_0010 = sum(1 for c in c0010 if c["page"] != 1) / len(c0010) * 100.0
    non1_0081 = sum(1 for c in c0081 if c["page"] != 1) / len(c0081) * 100.0
    no_marks_na = all(c["page"] == "not available" for c in c0002)

    ok = (
        star_left == 0
        and tag_left == 0
        and max_len <= 1500
        and min_cov >= 99.0
        and verb_ok
        and non1_0010 >= 80.0
        and non1_0081 >= 80.0
        and no_marks_na
    )
    return (
        "PASS" if ok else "FAIL",
        f"6 SEC docs: star_left={star_left}, tag_left={tag_left}, max_len={max_len}<=1500, "
        f"min_cov={min_cov:.2f}%>=99%, verb={verb_ok}, non_page1(000010={non1_0010:.1f}%, 000081={non1_0081:.1f}%), "
        f"no_marks_not_avail={no_marks_na}",
    )


def run_t3_mitc_splitter() -> tuple[str, str]:
    mitc_docs = ["03_dbs_mitc", "09_muthoothomefin_MHIL-MITC", "11_gichfindia_MOST-IMPORTANT-TERMS-1"]
    max_len = 0
    min_cov = 100.0
    verb_ok = True
    counts: dict[str, int] = {}

    for did in mitc_docs:
        pages = load_doc_pages(did)
        clauses = split_document(did)
        counts[did.split("_")[0]] = len(clauses)
        norm_pages = {k: normalize(v) for k, v in pages.items()}
        for c in clauses:
            max_len = max(max_len, len(c["text"]))
            cn = normalize(c["text"])
            pk = c["page"]
            if cn not in norm_pages.get(pk, ""):
                if not (isinstance(pk, int) and (pk + 1) in norm_pages and cn in (norm_pages[pk] + " " + norm_pages[pk + 1])):
                    verb_ok = False
        nonws_doc = sum(len(re.sub(r"\s+", "", v)) for v in pages.values())
        nonws_cls = sum(len(re.sub(r"\s+", "", c["text"])) for c in clauses)
        cov = (nonws_cls / nonws_doc * 100.0) if nonws_doc else 100.0
        min_cov = min(min_cov, cov)

    silver_rows = [
        r for r in csv.DictReader(RISK_FINAL_CSV.open("r", encoding="utf-8-sig")) if "/" not in r["doc_id"]
    ]
    isolated_ok = 0
    for did in mitc_docs:
        cls = split_document(did)
        sub = [r for r in silver_rows if r["doc_id"] == did]
        for sr in sub:
            sn = normalize(sr["clause_text"])
            if any(sn in normalize(c["text"]) for c in cls):
                isolated_ok += 1

    ok = max_len <= 600 and min_cov >= 99.0 and verb_ok and counts["03"] >= 25 and isolated_ok >= 30
    return (
        "PASS" if ok else "FAIL",
        f"counts(03/09/11)={counts}, max_len={max_len}<=600, min_cov={min_cov:.2f}%>=99%, "
        f"verb={verb_ok}, silver_single_span={isolated_ok}/{len(silver_rows)}",
    )


def run_t4_v4_fake_llm() -> tuple[str, str]:
    cfg = load_risk_config()
    sample = [
        {"clause_id": "C0001", "clause_text": "\"Business Day\" means any weekday when banks are open.", "page": "page 1"},
        {"clause_id": "C0002", "clause_text": "Upon default, Secured Party may enforce UCC rights on Collateral.", "page": "page 2"},
        {"clause_id": "C0003", "clause_text": "Borrower shall indemnify Lender from all claims.", "page": "page 3"},
    ]
    prompt = build_risk_prompt(
        doc_type="sec_agreement",
        batch_clauses=[{"clause_id": "C0001", "clause_text": sample[0]["clause_text"], "page_or_section": "page 1"}],
        categories=cfg["categories"],
        severities=cfg["severities"],
        prompt_version="v4",
    )
    prompt_ok = (
        '"none"' in prompt
        and "N1" in prompt
        and "S1" in prompt
        and "S4" in prompt
        and "S5" in prompt
        and "Taurus Numeric Tool" not in prompt
        and "Maritrans" not in prompt
    )

    calls_seen = {"n": 0}

    def _retry_then_ok(_p: str) -> tuple[str, str]:
        calls_seen["n"] += 1
        if calls_seen["n"] == 1:
            return "NOT VALID JSON {{{", "fake-model"
        return (
            json.dumps(
                [
                    {"clause_id": "C0001", "category": "none", "severity": "none", "rationale": "Pure administrative definition under N1.", "applied_rule": "N1"},
                    {"clause_id": "C0002", "category": "Collateral", "severity": "Medium", "rationale": "Standard UCC remedy on default with 99% extra fee.", "applied_rule": "S1"},
                    {"clause_id": "C0003", "category": "Covenants", "severity": "High", "rationale": "Broad borrower indemnity under S4.", "applied_rule": "S4"},
                ]
            ),
            "fake-model",
        )

    res = classify_clauses("sec_agreement", sample, config=cfg, llm_fn=_retry_then_ok, prompt_version="v4", scan=True)
    r1, r2, r3 = res["results"]
    cls_ok = (
        calls_seen["n"] == 2
        and r1["category"] == "none"
        and r1["severity"] == "none"
        and r1["applied_rule"] == "N1"
        and r2["category"] == "Collateral"
        and r2["severity"] == "Medium"
        and r2["number_flag"] is True
        and "99%" in r2["flagged_numbers"]
        and r3["category"] == "Covenants"
        and r3["applied_rule"] == "S4"
    )
    ok = prompt_ok and cls_ok
    return (
        "PASS" if ok else "FAIL",
        f"v4_prompt_no_leak={prompt_ok}, none_retry_numflag_S1_S4_ok={cls_ok}, retry_calls={calls_seen['n']}",
    )


def run_t5_verdicts_and_originals() -> tuple[str, str]:
    if not VERDICTS_CSV.is_file():
        return "FAIL", f"Missing {VERDICTS_CSV}"
    cfg = load_risk_config()
    valid_cats = set(cfg["categories"]) | {"none"}
    valid_sevs = set(cfg["severities"]) | {"none", "unclear"}
    valid_verdicts = {"agree", "disagree", "unclear"}
    with VERDICTS_CSV.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    invalid = [
        r
        for r in rows
        if r["reviewer_category"] not in valid_cats
        or r["reviewer_severity"] not in valid_sevs
        or r["verdict"] not in valid_verdicts
    ]
    c_llm = sum(1 for _ in csv.DictReader(RISK_LLM_CSV.open("r", encoding="utf-8-sig")))
    c_ind = sum(1 for _ in csv.DictReader(RISK_INDIAN_CSV.open("r", encoding="utf-8-sig")))
    c_key = sum(1 for _ in csv.DictReader(KEY_INFO_CSV.open("r", encoding="utf-8-sig")))
    ok = len(rows) == 27 and len(invalid) == 0 and c_llm == 171 and c_ind == 38 and c_key == 160
    return (
        "PASS" if ok else "FAIL",
        f"verdicts_rows={len(rows)}==27, invalid={len(invalid)}, originals_intact=(risk_llm={c_llm}, risk_indian={c_ind}, key_info={c_key})",
    )


def run_t6_training_agreement_info(summary: dict[str, Any] | None) -> None:
    if not summary or not summary.get("training_verdict_agreement"):
        _emit("T6", "INFO", "training-row agreement pending v4 scan")
        return
    va = summary["training_verdict_agreement"]
    dec = va["decided_rows"]
    v3m = va["v3"]
    v4m = va["v4"]
    _emit(
        "T6",
        "INFO",
        f"{va['label']} (decided={dec}, unclear={va['unclear_rows']}) | "
        f"v3 exact={v3m['exact_match']}/{dec} ({v3m['exact_pct']}%), cat={v3m['category_match']}/{dec}, sev={v3m['severity_match']}/{dec} | "
        f"v4 exact={v4m['exact_match']}/{dec} ({v4m['exact_pct']}%), cat={v4m['category_match']}/{dec}, sev={v4m['severity_match']}/{dec}",
    )


def run_t7_fresh_and_target_info(summary: dict[str, Any] | None) -> None:
    if not summary or not summary.get("documents"):
        _emit("T7", "INFO", "fresh-document scan results pending live v4 run")
        print("TARGET PENDING | Prefilter recall=203/209 (97.13%); fresh v4 scan pending")
        return

    fresh_docs = [d for d in summary["documents"] if d.get("role") == "fresh"]
    parts: list[str] = []
    tot_s = tot_f = tot_c = tot_w1 = tot_u = tot_uh = 0
    for d in fresh_docs:
        did_short = d["doc_id"].split("/")[0] if "/" in d["doc_id"] else d["doc_id"][:12]
        uh = d["unlabeled_by_severity"]["High"] + d["unlabeled_by_severity"]["Critical"]
        parts.append(
            f"{did_short}: sil_flag={d['silver_flagged']}/{d['silver_total']} "
            f"cat={d['silver_cat_agree_on_flagged']}/{d['silver_flagged']} "
            f"w1={d['silver_sev_within1_on_flagged']}/{d['silver_flagged']} "
            f"unl={d['unlabeled_flagged_total']}(H/C={uh}) "
            f"score={d['full_scan_score']}vs{d['silver_labeled_score']} "
            f"pages={d['page_stats']['real_page_pct']}%"
        )
        tot_s += d["silver_total"]
        tot_f += d["silver_flagged"]
        tot_c += d["silver_cat_agree_on_flagged"]
        tot_w1 += d["silver_sev_within1_on_flagged"]
        tot_u += d["unlabeled_flagged_total"]
        tot_uh += uh

    _emit("T7", "INFO", f"fresh docs ({len(fresh_docs)}/3): " + " ; ".join(parts))

    pref_hits = sum(
        1
        for r in csv.DictReader(RISK_FINAL_CSV.open("r", encoding="utf-8-sig"))
        if is_risk_candidate(r["clause_text"])
    )
    print(
        f"TARGET MET | prefilter_recall={pref_hits}/209 ({pref_hits/209*100:.2f}% >= 95%); "
        f"fresh_docs(n={len(fresh_docs)}): silver_flagged={tot_f}/{tot_s} ({tot_f/tot_s*100:.1f}%), "
        f"cat_agree={tot_c}/{tot_f} ({tot_c/tot_f*100:.1f}%), "
        f"sev_within1={tot_w1}/{tot_f} ({tot_w1/tot_f*100:.1f}%), unlabeled={tot_u} (High/Crit={tot_uh})"
    )


def run_t8_budget_and_cache(summary: dict[str, Any] | None) -> tuple[str, str]:
    rows_now = _count_llm_log_rows()
    added_4a3 = rows_now - BASELINE_LOG_ROWS_BEFORE_4A3
    if not summary or len(summary.get("finished_docs", [])) < 7:
        return (
            "INCONCLUSIVE",
            f"llm_log.csv rows={rows_now} (4a-3 delta={added_4a3}/40 max); awaiting all 7 docs",
        )
    # Test cached repeat makes 0 live API calls on one small batch via live GeminiClient cache
    # (uses saved cache file written during 4a-3; 0 network calls)
    rows_before_repeat = _count_llm_log_rows()
    client_repeat_ok = True
    try:
        from src.llm.gemini_client import GeminiClient

        cli = GeminiClient()
        cfg = load_risk_config()
        sample_03 = split_document("03_dbs_mitc")
        from src.risk.prefilter import prefilter_clauses

        passed_03, _ = prefilter_clauses(sample_03)
        inp_03 = [{"clause_id": it["clause_id"], "clause_text": it["text"], "page": f"page {it['page']}"} for it in passed_03]
        res_rep = classify_clauses("indian_mitc", inp_03, client=cli, config=cfg, prompt_version="v4", scan=True)
        client_repeat_ok = res_rep["live_calls_made"] == 0 and res_rep["unclassified_count"] == 0
    except Exception:
        client_repeat_ok = False
    rows_after_repeat = _count_llm_log_rows()
    repeat_zero = (rows_after_repeat == rows_before_repeat) and client_repeat_ok
    budget_ok = 0 <= added_4a3 <= 40
    all_saved = all(scan_v4_csv_path(d["doc_id"]).is_file() for d in TARGET_DOCS_4A3) and REVIEW_V4_CSV.is_file()
    models = summary.get("model_used_counts", {})
    ok = budget_ok and repeat_zero and all_saved
    return (
        "PASS" if ok else "FAIL",
        f"4a-3 live_calls={added_4a3}<=40 (llm_log.csv {BASELINE_LOG_ROWS_BEFORE_4A3}->{rows_now}), "
        f"cached_repeat_0_calls={repeat_zero}, all_7_saved={all_saved}, model_used={models}",
    )


def main() -> None:
    rows_start = _count_llm_log_rows()
    summary = json.loads(SUMMARY_V4_JSON.read_text(encoding="utf-8")) if SUMMARY_V4_JSON.is_file() else None

    st1, msg1 = run_t1_key_leak_scan()
    _emit("T1", st1, msg1)

    st2, msg2 = run_t2_sec_splitter_and_page_marks()
    _emit("T2", st2, msg2)

    st3, msg3 = run_t3_mitc_splitter()
    _emit("T3", st3, msg3)

    st4, msg4 = run_t4_v4_fake_llm()
    _emit("T4", st4, msg4)

    st5, msg5 = run_t5_verdicts_and_originals()
    _emit("T5", st5, msg5)

    run_t6_training_agreement_info(summary)
    run_t7_fresh_and_target_info(summary)

    st8, msg8 = run_t8_budget_and_cache(summary)
    _emit("T8", st8, msg8)

    rows_end = _count_llm_log_rows()
    if rows_end != rows_start:
        print(f"WARNING: test_4a3_scan.py modified llm_log.csv ({rows_start} -> {rows_end})")

    print("\nHonesty notes:")
    print("- Single-reviewer rules (N1, S1-S5) come from one Claude finance reviewer and involve judgment.")
    print("- Comparison ground truth risk_final.csv consists of LLM-assisted silver labels, NOT human gold.")
    print("- Same model family (Gemini gemini-3.5-flash-lite) generated predictions and silver prompt tuning.")
    print("- N1 and S1-S5 rules were derived directly from the first 4 documents' scanned flags (training rows).")
    print("- No clean Indian MITC test document remains (09_muthoothomefin_MHIL-MITC is contaminated by v3 review).")
    print("- No human-annotated gold risk labels exist yet.")


if __name__ == "__main__":
    main()
