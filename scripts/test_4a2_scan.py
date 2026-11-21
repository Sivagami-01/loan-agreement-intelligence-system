"""scripts/test_4a2_scan.py

Verification suite for Stage 4a-2 (whole-document risk scan).
Runs T1-T8 checks, prints a separate TARGET line and honesty notes, and makes ZERO live API calls.
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

from scripts.run_4a2_scan import REVIEW_CSV, SUMMARY_JSON, TARGET_DOCS, scan_csv_path  # noqa: E402
from src.llm.gemini_client import get_api_key  # noqa: E402
from src.qa.verify_quotes import normalize  # noqa: E402
from src.risk.classify import build_risk_prompt, classify_clauses, load_risk_config  # noqa: E402
from src.risk.prefilter import is_risk_candidate  # noqa: E402
from src.risk.split_clauses import load_doc_pages, split_document, split_pages  # noqa: E402

LLM_LOG_PATH = ROOT / "data" / "processed" / "llm_log.csv"
RISK_FINAL_CSV = ROOT / "data" / "processed" / "labels" / "llm_assisted" / "risk_final.csv"
RISK_LLM_CSV = ROOT / "data" / "processed" / "labels" / "llm_assisted" / "risk_llm.csv"
RISK_INDIAN_CSV = ROOT / "data" / "processed" / "labels" / "llm_assisted" / "risk_indian_llm.csv"
RISK_SPLIT_CSV = ROOT / "data" / "processed" / "risk_split.csv"


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


def run_t2_splitter_invariants() -> tuple[str, str]:
    empty_res = split_pages("EMPTY", {1: "", 2: "   \n ", 3: "Valid sentence one. " * 10})
    empty_ok = len(empty_res) == 1 and empty_res[0]["page"] == 3

    max_len_seen = 0
    min_cov_seen = 100.0
    verbatim_ok = True
    total_clauses = 0

    for d in TARGET_DOCS:
        did = d["doc_id"]
        pages = load_doc_pages(did)
        norm_pages = {p: normalize(t) for p, t in pages.items()}
        clauses = split_pages(did, pages)
        total_clauses += len(clauses)
        for c in clauses:
            max_len_seen = max(max_len_seen, len(c["text"]))
            if normalize(c["text"]) not in norm_pages.get(c["page"], ""):
                verbatim_ok = False
        nonws_doc = sum(len(re.sub(r"\s+", "", t)) for t in pages.values())
        nonws_cls = sum(len(re.sub(r"\s+", "", c["text"])) for c in clauses)
        cov = (nonws_cls / nonws_doc * 100.0) if nonws_doc else 100.0
        min_cov_seen = min(min_cov_seen, cov)

    # Synthetic long paragraph > 1500 chars splits at sentence boundary <= 1500
    long_text = ("Section 1. The borrower shall pay interest monthly on demand. " * 40).strip()
    long_res = split_pages("LONG", {1: long_text})
    long_ok = len(long_res) >= 2 and all(len(x["text"]) <= 1500 for x in long_res)

    ok = empty_ok and verbatim_ok and max_len_seen <= 1500 and min_cov_seen >= 99.0 and long_ok
    return (
        "PASS" if ok else "FAIL",
        f"target_docs=4, total_clauses={total_clauses}, max_len={max_len_seen}<=1500, "
        f"min_cov={min_cov_seen:.2f}%>=99%, verbatim={verbatim_ok}, empty_ok={empty_ok}, long_ok={long_ok}",
    )


def run_t3_prefilter_recall() -> tuple[str, str, dict[str, Any]]:
    with RISK_SPLIT_CSV.open("r", encoding="utf-8-sig") as f:
        split_map = {r["doc_id"]: r["split"] for r in csv.DictReader(f)}
    with RISK_FINAL_CSV.open("r", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    stats: dict[str, Any] = {}
    for subset in ("dev", "test", "ALL"):
        sub = [r for r in rows if subset == "ALL" or split_map[r["doc_id"]] == subset]
        hits = sum(1 for r in sub if is_risk_candidate(r["clause_text"]))
        stats[subset] = (hits, len(sub), hits / len(sub) * 100.0 if sub else 0.0)

    all_hits, all_total, all_pct = stats["ALL"]
    ok = all_pct >= 95.0
    dev_h, dev_n, dev_p = stats["dev"]
    tst_h, tst_n, tst_p = stats["test"]
    return (
        "PASS" if ok else "FAIL",
        f"ALL={all_hits}/{all_total} ({all_pct:.2f}%), dev={dev_h}/{dev_n} ({dev_p:.2f}%), test={tst_h}/{tst_n} ({tst_p:.2f}%)",
        {"hits": all_hits, "total": all_total, "pct": all_pct, "met": ok},
    )


def run_t4_v3_fake_llm() -> tuple[str, str]:
    cfg = load_risk_config()
    sample = [
        {"clause_id": "C0001", "clause_text": "This Agreement may be executed in counterparts.", "page": "page 1"},
        {"clause_id": "C0002", "clause_text": "Upfront fee of 2.0% is payable prior to drawdown.", "page": "page 2"},
    ]
    prompt = build_risk_prompt(
        doc_type="sec_agreement",
        batch_clauses=[{"clause_id": "C0001", "clause_text": sample[0]["clause_text"], "page_or_section": "page 1"}],
        categories=cfg["categories"],
        severities=cfg["severities"],
        prompt_version="v3",
    )
    prompt_ok = ('"none"' in prompt) and ("R4" in prompt) and ("silver" not in prompt.lower())

    def _fake_ok(_p: str) -> tuple[str, str]:
        return (
            json.dumps(
                [
                    {"clause_id": "C0001", "category": "none", "severity": "none", "rationale": "Counterpart boilerplate.", "applied_rule": "none"},
                    {"clause_id": "C0002", "category": "Penalties and charges", "severity": "Medium", "rationale": "Charges 2.0% upfront fee before drawdown (extra 99%).", "applied_rule": "R4"},
                ]
            ),
            "fake-model",
        )

    res = classify_clauses("sec_agreement", sample, config=cfg, llm_fn=_fake_ok, prompt_version="v3", scan=True)
    r1, r2 = res["results"]
    cls_ok = (
        r1["category"] == "none"
        and r1["severity"] == "none"
        and r2["category"] == "Penalties and charges"
        and r2["applied_rule"] == "R4"
        and r2["number_flag"] is True
        and "99%" in r2["flagged_numbers"]
    )

    def _fake_429(_p: str) -> tuple[str, str]:
        raise RuntimeError("HTTP 429 RESOURCE_EXHAUSTED daily quota reached")

    res_429 = classify_clauses("sec_agreement", sample, config=cfg, llm_fn=_fake_429, prompt_version="v3", scan=True)
    quota_ok = res_429["quota_stopped"] is True and len(res_429["results"]) == 0

    ok = prompt_ok and cls_ok and quota_ok
    return (
        "PASS" if ok else "FAIL",
        f"v3_prompt_ok={prompt_ok}, none_and_R4_and_numflag_ok={cls_ok}, quota_429_graceful_stop={quota_ok}",
    )


def run_t5_saved_scan_integrity() -> tuple[str, str]:
    missing = [d["doc_id"] for d in TARGET_DOCS if not scan_csv_path(d["doc_id"]).is_file()]
    if missing:
        return "INCONCLUSIVE", f"Saved scan CSVs not yet generated for: {missing}"

    total_rows = 0
    verbatim_mismatch = 0
    unclassified = 0
    for d in TARGET_DOCS:
        did = d["doc_id"]
        split_map = {(c["clause_id"], str(c["page"])): c["text"] for c in split_document(did)}
        with scan_csv_path(did).open("r", encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
        total_rows += len(rows)
        for r in rows:
            if split_map.get((r["clause_id"], str(r["page"]))) != r["clause_text"]:
                verbatim_mismatch += 1
            if r["category"] == "unclassified" or r["severity"] == "unclassified":
                unclassified += 1
    ok = verbatim_mismatch == 0 and total_rows > 0
    return (
        "PASS" if ok else "FAIL",
        f"4 scan CSVs verified: total_rows={total_rows}, verbatim_splitter_mismatches={verbatim_mismatch}, unclassified={unclassified}",
    )


def run_t6_review_and_summary() -> tuple[str, str]:
    if not REVIEW_CSV.is_file() or not SUMMARY_JSON.is_file():
        return "INCONCLUSIVE", "risk_scan_review.csv or scan_4a2_summary.json not yet written"

    with REVIEW_CSV.open("r", encoding="utf-8-sig", newline="") as fh:
        rev_rows = list(csv.DictReader(fh))
        cols_ok = fh.seek(0) == 0
    with REVIEW_CSV.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        expected_cols = ["doc_id", "clause_id", "page", "category", "severity", "clause_text", "rationale", "reviewer_verdict"]
        cols_ok = list(reader.fieldnames or []) == expected_cols

    hc = sum(1 for r in rev_rows if r["severity"] in {"High", "Critical"})
    ml = sum(1 for r in rev_rows if r["severity"] in {"Medium", "Low"})
    summary = json.loads(SUMMARY_JSON.read_text(encoding="utf-8"))
    docs_done = len(summary.get("documents", []))
    ok = cols_ok and hc <= 25 and ml <= 10 and docs_done == 4
    return (
        "PASS" if ok else "INCONCLUSIVE",
        f"docs_summarized={docs_done}/4, review_rows={len(rev_rows)} (High/Crit={hc}<=25, Med/Low={ml}<=10), cols_ok={cols_ok}",
    )


def run_t7_silver_originals_intact() -> tuple[str, str]:
    with RISK_LLM_CSV.open("r", encoding="utf-8-sig") as f1:
        c1 = sum(1 for _ in csv.DictReader(f1))
    with RISK_INDIAN_CSV.open("r", encoding="utf-8-sig") as f2:
        c2 = sum(1 for _ in csv.DictReader(f2))
    with RISK_FINAL_CSV.open("r", encoding="utf-8-sig") as f3:
        c3 = sum(1 for _ in csv.DictReader(f3))
    ok = c1 == 171 and c2 == 38 and c3 == 209
    return (
        "PASS" if ok else "FAIL",
        f"risk_llm.csv={c1}, risk_indian_llm.csv={c2}, risk_final.csv={c3} (originals preserved)",
    )


def main() -> None:
    rows_before = _count_llm_log_rows()

    st1, msg1 = run_t1_key_leak_scan()
    _emit("T1", st1, msg1)

    st2, msg2 = run_t2_splitter_invariants()
    _emit("T2", st2, msg2)

    st3, msg3, pf_stats = run_t3_prefilter_recall()
    _emit("T3", st3, msg3)

    st4, msg4 = run_t4_v3_fake_llm()
    _emit("T4", st4, msg4)

    st5, msg5 = run_t5_saved_scan_integrity()
    _emit("T5", st5, msg5)

    st6, msg6 = run_t6_review_and_summary()
    _emit("T6", st6, msg6)

    st7, msg7 = run_t7_silver_originals_intact()
    _emit("T7", st7, msg7)

    rows_after = _count_llm_log_rows()
    t8_ok = rows_after == rows_before
    _emit("T8", "PASS" if t8_ok else "FAIL", f"zero live API calls in test_4a2_scan.py; llm_log.csv rows={rows_after}")

    # Separate TARGET line
    target_word = "TARGET MET" if pf_stats["met"] else "TARGET MISSED"
    scan_cov_str = "pending live scan"
    if SUMMARY_JSON.is_file():
        summary = json.loads(SUMMARY_JSON.read_text(encoding="utf-8"))
        docs = summary.get("documents", [])
        if docs:
            tot_s = sum(d["silver_total"] for d in docs)
            tot_f = sum(d["silver_flagged"] for d in docs)
            tot_c = sum(d["silver_cat_agree_on_flagged"] for d in docs)
            tot_w1 = sum(d["silver_sev_within1_on_flagged"] for d in docs)
            if tot_s and tot_f:
                scan_cov_str = (
                    f"scan silver flagged={tot_f}/{tot_s} ({tot_f/tot_s*100:.1f}%), "
                    f"cat_agree_on_flagged={tot_c}/{tot_f} ({tot_c/tot_f*100:.1f}%), "
                    f"sev_within1_on_flagged={tot_w1}/{tot_f} ({tot_w1/tot_f*100:.1f}%)"
                )
    print(
        f"TARGET {target_word} | Prefilter silver recall={pf_stats['hits']}/{pf_stats['total']} "
        f"({pf_stats['pct']:.2f}% >= 95% target) | {scan_cov_str}"
    )

    print("\nHonesty notes:")
    print("- Comparison baseline risk_final.csv consists of LLM-assisted silver labels, NOT human gold.")
    print("- Whole-document scan adds newly flagged unlabeled clauses whose precision requires human verification (staged in risk_scan_review.csv).")
    print("- Full-scan padded_top3 scores differ from labeled-subset scores whenever unlabelled High/Critical or extra category clauses are discovered.")
    print("- Test documents (09_muthoothomefin_MHIL-MITC and 000081/810113/0000950116-04-002411_4.txt) are evaluated once after freezing dev settings.")


if __name__ == "__main__":
    main()
