"""scripts/test_3b_summary.py

Verification suite for Stage 3b (grounded plain-English SHORT and DETAILED summaries).
Tests:
  T1: API key leak scan (0 leaks).
  T2: Fake-LLM unit tests (0 API calls): invented number dropped, missing-cite sentence
      dropped, Devanagari-digit number matched, not_found field shown as "Not found in
      this document", deferred field shown as "Defined in another document", and no advice
      wording survives.
  T3: Live summaries on the 5 benchmark docs (03_dbs_mitc, 13_bajaj Hindi, aesohio,
      09_muthoot, CITGO): report short word count (<= 120), kept vs dropped sentences,
      kept sentence cite share (100%), and kept number verification share (100%).
  T4: Write data/processed/summary_review.csv (doc, section, sentence, pages, status)
      with NO verdict column filled.
  T5: Live call budget <= 30 and 0 new live calls on a cached repeat run.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.eval_3a_matches import _read_zip_doc_pages
from src.extract.extract_fields import extract_key_info
from src.llm.gemini_client import GeminiClient, get_api_key
from src.qa.doc_loader import load_document
from src.summarize.summarize import _has_advice_or_opinion, load_summarize_config, summarize_document

LOG_FILE = ROOT / "data" / "processed" / "llm_log.csv"
GEMINI_CACHE_DIR = ROOT / "data" / "processed" / "cache" / "gemini"
REVIEW_CSV = ROOT / "data" / "processed" / "summary_review.csv"
OUT_RESULTS_JSON = ROOT / "data" / "processed" / "summary_3b_results.json"

BENCHMARK_DOCS: list[tuple[str, dict[int, str] | None]] = [
    ("03_dbs_mitc", None),
    ("13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi", None),
    ("0000027430-25-000005_aesohio10qex10120250630q2", None),
    ("09_muthoothomefin_MHIL-MITC", None),
    ("CITGO (000101/1011746/0000950129-03-001503_8.txt)", _read_zip_doc_pages("000101/1011746/0000950129-03-001503_8.txt")),
]


def test_t1_key_leaks() -> tuple[bool, str]:
    api_key = get_api_key()
    if not api_key or len(api_key) < 10:
        return False, "GEMINI_API_KEY missing or invalid."

    files_to_scan: list[Path] = [
        ROOT / "config" / "summarize.yaml",
        ROOT / "src" / "summarize" / "summarize.py",
        ROOT / "scripts" / "demo_summarize.py",
        ROOT / "scripts" / "test_3b_summary.py",
        ROOT / "docs" / "WORK_REPORT.md",
        LOG_FILE,
        REVIEW_CSV,
        OUT_RESULTS_JSON,
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


def test_t2_unit_tests() -> tuple[bool, str]:
    cfg = load_summarize_config()
    fake_pages = {
        1: "Acme Bank lends Rs. 500,000 to Beta Corp. Interest rate is set in the Note. Prepayment charge is १५% after १५ days.",
        2: "Repayment is due monthly over २४ months starting May 1, 2025.",
    }
    fake_key_info = {
        "doc_id": "unit_3b_doc",
        "fields": [
            {"field": "lenders", "status": "verified", "value": "Acme Bank", "evidence": [{"quote": "Acme Bank lends", "page": 1}]},
            {"field": "borrowers", "status": "verified", "value": "Beta Corp", "evidence": [{"quote": "Beta Corp.", "page": 1}]},
            {"field": "loan_or_commitment_amount", "status": "verified", "value": "Rs. 500,000", "evidence": [{"quote": "Rs. 500,000", "page": 1}]},
            {"field": "interest_rate", "status": "deferred_to_other_document", "defers_to": "Note", "value": "", "evidence": [{"quote": "set in the Note.", "page": 1}]},
            {"field": "prepayment_terms", "status": "verified", "value": "15% after 15 days", "evidence": [{"quote": "Prepayment charge is १५% after १५ days.", "page": 1}]},
            {"field": "repayment_terms", "status": "verified", "value": "Monthly over 24 months starting May 1, 2025", "evidence": [{"quote": "Repayment is due monthly over २४ months starting May 1, 2025.", "page": 2}]},
            {"field": "governing_law", "status": "not_found", "value": "Not found in this document", "evidence": []},
        ],
    }

    def fake_llm(prompt: str) -> tuple[str, str]:
        payload = {
            "short_sentences": [
                {"text": "Acme Bank lends Rs. 500,000 to Beta Corp [p.1]."},
                # Invented number (18.5%) -> MUST be dropped
                {"text": "The fixed interest rate is 18.5% per year [p.1]."},
                # Missing page cite -> MUST be dropped
                {"text": "This loan has monthly installments."},
                # Advice wording -> MUST be dropped
                {"text": "You should consult a lawyer before signing [p.1]."},
                # Devanagari -> ASCII matched against source p.1 (१५% / १५ days) -> MUST be kept!
                {"text": "Prepayment carries a 15% charge after 15 days [p.1]."},
                {"text": "Monthly repayment runs for 24 months from May 1, 2025 [p.2]."},
            ],
            "detailed_sections": {
                "Parties": [
                    {"text": "Acme Bank is the lender and Beta Corp is the borrower [p.1]."},
                    {"text": "We recommend signing this agreement quickly [p.1]."},
                ],
                "Money": [{"text": "The sanctioned loan amount is Rs. 500,000 [p.1]."}],
                "Interest and repayment": [
                    {"text": "Repayment is monthly over 24 months starting May 1, 2025 [p.2]."},
                    {"text": "Late penalty is $999 per day [p.2]."},
                ],
                "Fees and penalties": [],
                "Prepayment": [{"text": "Early prepayment costs 15% after 15 days [p.1]."}],
                "Security and guarantees": [],
                "Default and termination": [],
                "Governing law": [],
            },
        }
        return json.dumps(payload), "fake-bulk-model"

    res = summarize_document(
        doc_id="unit_3b_doc",
        doc_pages=fake_pages,
        key_info=fake_key_info,
        config=cfg,
        llm_fn=fake_llm,
    )

    sents = res["sentences"]
    dropped_statuses = {(s["text"], s["status"]) for s in sents if s["status"] != "kept"}
    kept_short = [s for s in sents if s["section"] == "short" and s["status"] == "kept"]

    checks: list[tuple[str, bool, str]] = [
        ("invented_num_18_5_dropped", ("The fixed interest rate is 18.5% per year [p.1].", "dropped_unverified_number") in dropped_statuses, f"dropped={dropped_statuses}"),
        ("invented_num_999_dropped", ("Late penalty is $999 per day [p.2].", "dropped_unverified_number") in dropped_statuses, f"dropped={dropped_statuses}"),
        ("no_cite_dropped", ("This loan has monthly installments.", "dropped_no_cite") in dropped_statuses, f"dropped={dropped_statuses}"),
        ("devanagari_kept_prepay", any("15%" in s["text"] for s in kept_short), f"kept_short={kept_short}"),
        ("devanagari_kept_24_months", any("24 months" in s["text"] for s in kept_short), f"kept_short={kept_short}"),
        ("not_found_rendered", "Not found in this document" in res["detailed"] and "governing_law" in res["not_found_fields"], f"nf={res['not_found_fields']}"),
        ("deferred_rendered", "Defined in another document" in res["detailed"] and "interest_rate" in res["deferred_fields"], f"def={res['deferred_fields']}"),
        ("advice_dropped_all", not _has_advice_or_opinion(res["short"]) and not _has_advice_or_opinion(res["detailed"]), f"short={res['short']} | det={res['detailed']}"),
        ("short_word_limit", res["short_word_count"] <= cfg["short_max_words"], f"words={res['short_word_count']}"),
    ]

    failures = [f"{name} ({detail})" for name, passed, detail in checks if not passed]
    ok = len(failures) == 0
    return ok, f"{len(checks) - len(failures)}/{len(checks)} unit checks passed" + (f"; FAILURES: {failures}" if failures else "")


def run_live_5_docs(client: GeminiClient) -> tuple[bool, str, list[dict[str, Any]], list[dict[str, Any]], int]:
    cfg = load_summarize_config()
    short_limit = int(cfg.get("short_max_words", 120))
    before = client.api_calls_made

    doc_summaries: list[dict[str, Any]] = []
    review_rows: list[dict[str, Any]] = []
    all_pass = True

    for doc_id, custom_pages in BENCHMARK_DOCS:
        pages = custom_pages if custom_pages is not None else load_document(doc_id)[1]
        res = summarize_document(doc_id=doc_id, doc_pages=pages, client=client, config=cfg)

        sents = res["sentences"]
        kept = [s for s in sents if s["status"] == "kept"]
        dropped = [s for s in sents if s["status"] != "kept"]

        kept_with_cite = sum(1 for s in kept if len(s["pages"]) > 0)
        cite_share = (kept_with_cite / len(kept)) if kept else 1.0

        total_nums = 0
        found_nums = 0
        for s in kept:
            ext = s["numbers_checked"].get("extracted", [])
            miss = s["numbers_checked"].get("missing", [])
            total_nums += len(ext)
            found_nums += max(0, len(ext) - len(miss))
        num_share = (found_nums / total_nums) if total_nums > 0 else 1.0

        short_wc = res["short_word_count"]
        doc_ok = (
            short_wc <= short_limit
            and len(kept) > 0
            and cite_share == 1.0
            and num_share == 1.0
        )
        if not doc_ok:
            all_pass = False

        doc_summaries.append({
            "doc_id": doc_id,
            "model_used": res["model_used"],
            "short_words": short_wc,
            "kept_sentences": len(kept),
            "dropped_sentences": len(dropped),
            "kept_with_cite_share": cite_share,
            "kept_numbers_total": total_nums,
            "kept_numbers_found": found_nums,
            "kept_numbers_share": num_share,
            "not_found_fields": res["not_found_fields"],
            "deferred_fields": res["deferred_fields"],
            "flags": res["flags"],
            "short": res["short"],
            "detailed": res["detailed"],
        })

        for s in sents:
            review_rows.append({
                "doc": doc_id,
                "section": s["section"],
                "sentence": s["text"],
                "pages": ",".join(str(p) for p in s["pages"]),
                "status": s["status"],
            })

    new_calls = client.api_calls_made - before
    msg = (
        f"5 docs summarized; all_docs_ok={all_pass}; new_calls={new_calls}; "
        f"review_sentences={len(review_rows)}"
    )
    return all_pass, msg, doc_summaries, review_rows, new_calls


def write_review_csv(review_rows: list[dict[str, Any]]) -> tuple[bool, str]:
    REVIEW_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["doc", "section", "sentence", "pages", "status"]
    with open(REVIEW_CSV, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(review_rows)

    with open(REVIEW_CSV, "r", encoding="utf-8", newline="") as fh:
        read_back = list(csv.DictReader(fh))
    cols = list(read_back[0].keys()) if read_back else []
    ok = REVIEW_CSV.is_file() and cols == fieldnames and len(read_back) == len(review_rows) and len(read_back) > 0
    return ok, f"Wrote {len(read_back)} rows with exact columns {cols} to {REVIEW_CSV.name}"


def test_t5_budget_and_cache(total_live_calls: int) -> tuple[bool, str]:
    cfg = load_summarize_config()
    max_calls = int(cfg.get("max_live_calls", 30))
    fresh_client = GeminiClient()
    before = fresh_client.api_calls_made

    for did, custom_pages in BENCHMARK_DOCS:
        pages = custom_pages if custom_pages is not None else load_document(did)[1]
        summarize_document(doc_id=did, doc_pages=pages, client=fresh_client, config=cfg)

    repeat_new_calls = fresh_client.api_calls_made - before
    ok = total_live_calls <= max_calls and repeat_new_calls == 0 and fresh_client.cache_hits > 0
    return ok, (
        f"total_live_calls={total_live_calls} (limit <={max_calls}); "
        f"cached_repeat_new_calls={repeat_new_calls} (cache_hits={fresh_client.cache_hits})"
    )


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("=" * 92, flush=True)
    print("STAGE 3b TEST SUITE: Plain-English Grounded Summaries (SHORT + DETAILED)", flush=True)
    print("=" * 92, flush=True)

    t1_ok, t1_msg = test_t1_key_leaks()
    print(f"[{'PASS' if t1_ok else 'FAIL'}] T1 Key leak scan: {t1_msg}", flush=True)

    t2_ok, t2_msg = test_t2_unit_tests()
    print(f"[{'PASS' if t2_ok else 'FAIL'}] T2 Unit tests (0 API calls): {t2_msg}", flush=True)

    client = GeminiClient(min_interval_seconds=6.5, request_timeout=75.0)
    t3_ok, t3_msg, t3_docs, review_rows, total_live = run_live_5_docs(client)
    print(f"[{'PASS' if t3_ok else 'FAIL'}] T3 Live 5 benchmark docs: {t3_msg}", flush=True)
    for d in t3_docs:
        print(
            f"   - {d['doc_id'][:46]:<46} | short_w={d['short_words']:3d} | "
            f"kept={d['kept_sentences']:2d} drop={d['dropped_sentences']:2d} | "
            f"cite={d['kept_with_cite_share']:.0%} | nums={d['kept_numbers_found']}/{d['kept_numbers_total']} ({d['kept_numbers_share']:.0%}) | "
            f"{d['model_used']}",
            flush=True,
        )

    t4_ok, t4_msg = write_review_csv(review_rows)
    print(f"[{'PASS' if t4_ok else 'FAIL'}] T4 Review CSV generated: {t4_msg}", flush=True)

    t5_ok, t5_msg = test_t5_budget_and_cache(total_live)
    print(f"[{'PASS' if t5_ok else 'FAIL'}] T5 Call budget & cached repeat: {t5_msg}", flush=True)

    t1_post_ok, t1_post_msg = test_t1_key_leaks()
    print(f"[{'PASS' if t1_post_ok else 'FAIL'}] T1 Post-run leak scan: {t1_post_msg}", flush=True)

    OUT_RESULTS_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_RESULTS_JSON.write_text(
        json.dumps(
            {
                "t1": {"passed": t1_ok and t1_post_ok, "msg": t1_post_msg},
                "t2": {"passed": t2_ok, "msg": t2_msg},
                "t3": {"passed": t3_ok, "msg": t3_msg, "docs": t3_docs},
                "t4": {"passed": t4_ok, "msg": t4_msg},
                "t5": {"passed": t5_ok, "msg": t5_msg, "total_live_calls": total_live},
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    overall = t1_ok and t1_post_ok and t2_ok and t3_ok and t4_ok and t5_ok
    print(f"\nOVERALL STAGE 3b SUITE: {'PASS' if overall else 'FAIL'}", flush=True)
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
