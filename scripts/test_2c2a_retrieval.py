"""scripts/test_2c2a_retrieval.py

Test Suite for Stage 2c-2a: Pure-Python BM25 Chunk Retrieval & Retrieval-Backed QA.
Verifies:
T1: Imports work; no API key in any output, cache, or log file.
T2: Chunker unit tests (no API): every chunk has page, no chunk crosses page,
    full coverage, Hindi text not broken mid-character, empty page does not crash.
T3: BM25 unit tests on tiny fake corpus (no API): rare query word ranks first;
    results are deterministic.
T4: Retrieval-only benchmark (no API): friend's 36 source-verified Q&A
    (data/friend/04_annotated_data/qa_evaluation_candidates.csv; 35 usable) +
    8 fact questions from 2c-1. Reports Hit@1, Hit@3, Hit@5, Hit@8 vs 30.7% baseline.
    PASS if crashes=0 and Hit@8 >= 30.7%.
T5: End-to-end QA with force_retrieval=True on the same 3 docs and 12 questions
    as 2c-1 (max 15 API calls, cached). Compares to 2c-1 whole-doc numbers and
    reports model_used counts. PASS if crashes=0 and verified-quote rate >= 95%.
T6: Over-limit document test (>400,000 chars in data/processed/ingested) WITHOUT
    forcing, or prints "SKIPPED: no document over limit".
"""

from __future__ import annotations

import csv
import json
import re
import sys
import unicodedata
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.llm.gemini_client import GeminiClient, get_api_key
from src.qa.answer import answer_question, load_qa_config
from src.qa.chunker import chunk_document, chunk_page
from src.qa.retrieve import BM25Index, load_retrieval_config, retrieve, tokenize
from src.qa.verify_quotes import normalize

LOG_FILE = ROOT / "data" / "processed" / "llm_log.csv"
GEMINI_CACHE_DIR = ROOT / "data" / "processed" / "cache" / "gemini"
RETRIEVAL_CACHE_DIR = ROOT / "data" / "processed" / "retrieval_cache"
INGESTED_DIR = ROOT / "data" / "processed" / "ingested"
FRIEND_QA_CSV = ROOT / "data" / "friend" / "04_annotated_data" / "qa_evaluation_candidates.csv"
FRIEND_ZIP = ROOT / "data" / "friend" / "01_loan_agreements" / "publicly_filed_contracts.zip"


def _split_edgar_pages(raw_text: str) -> dict[int, str]:
    """Splits raw SEC EDGAR .txt contracts on <PAGE> markers into page_num -> text."""
    parts = re.split(r"<PAGE>\s*(\d*)", raw_text)
    pages: dict[int, str] = {}
    if len(parts) > 1:
        cur_page = 0
        if parts[0].strip():
            cur_page = 1
            pages[1] = parts[0]
        for i in range(1, len(parts), 2):
            explicit_num = parts[i].strip()
            body = parts[i + 1]
            if explicit_num:
                p_num = int(explicit_num)
            else:
                cur_page += 1
                p_num = cur_page
            pages[p_num] = (pages[p_num] + "\n" + body) if p_num in pages else body
    else:
        pages[1] = raw_text
    return pages


def test_t1_imports_and_key_safety() -> tuple[bool, str]:
    try:
        api_key = get_api_key()
    except Exception as exc:
        return False, f"Failed to retrieve API key: {exc}"

    if not api_key or len(api_key) < 10:
        return False, "API key is missing or too short."

    files_to_scan: list[Path] = [
        LOG_FILE,
        ROOT / "config" / "qa.yaml",
        ROOT / "config" / "retrieval.yaml",
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

    return True, f"Imports OK; 0 API key leaks across {scanned} files (logs, config, Gemini & retrieval caches)"


def test_t2_chunker_unit_tests() -> tuple[bool, str]:
    # 1. Multi-page document with empty page, English clause paragraphs, and long Hindi page
    hindi_sentence = (
        "ब्याज दर प्रति वर्ष 8.50% तय की गई है और यदि ब्याज दर में बदलाव उधारकर्ता के प्रतिकूल है "
        "तो वह 60 दिनों के भीतर बिना किसी अतिरिक्त शुल्क के लोन खाता बंद कर सकता है। "
    )
    hindi_long = (hindi_sentence * 25).strip()
    english_long = (
        "1. Facility Amount.\nThe Lender agrees to advance up to $5,000,000.\n\n"
        "2. Prepayment.\nNo prepayment penalty applies on floating rate advances.\n\n"
    ) * 20

    pages = {
        1: english_long.strip(),
        2: "",
        3: "   \n\t  ",
        4: hindi_long,
    }

    chunks = chunk_document("unit_test_doc", pages, chunk_chars=500, chunk_overlap=50)
    if not chunks:
        return False, "Chunker produced 0 chunks on non-empty document."

    # Check fields and page boundaries
    for ch in chunks:
        for req in ("doc_id", "page", "chunk_id", "text"):
            if req not in ch:
                return False, f"Chunk missing required key '{req}': {ch}"
        if ch["page"] not in (1, 4):
            return False, f"Empty page produced unexpected chunk on page {ch['page']}"
        # Ensure chunk text is strictly a substring of its OWN page (no cross-page leak)
        if ch["text"] not in pages[ch["page"]]:
            return False, f"Chunk text crossed page boundary or mutated source on page {ch['page']}"
        # Ensure no chunk starts with a Unicode combining mark or splits Hindi mid-grapheme
        first_char = ch["text"][0]
        if unicodedata.category(first_char).startswith("M"):
            return False, f"Chunk started mid-character with combining mark {repr(first_char)}"
        last_char = ch["text"][-1]
        if last_char in {"\u094D", "\u09CD", "\u0A4D", "\u0D4D"}:
            return False, f"Chunk ended immediately after Indic Virama {repr(last_char)} (broken conjunct)"

    # Full character coverage check on Page 1 and Page 4
    for p_num in (1, 4):
        p_text = pages[p_num]
        covered = [False] * len(p_text)
        for ch in chunks:
            if ch["page"] == p_num:
                for idx in range(ch["char_start"], ch["char_end"]):
                    covered[idx] = True
        if not all(covered):
            missed_cnt = covered.count(False)
            return False, f"Page {p_num} lost {missed_cnt} characters during chunking!"

    return True, f"All chunker checks passed ({len(chunks)} chunks; page boundaries, full coverage, Hindi grapheme safety, empty page)"


def test_t3_bm25_unit_tests() -> tuple[bool, str]:
    fake_chunks = [
        {
            "doc_id": "fake",
            "page": 1,
            "chunk_id": "fake::p1::c0",
            "text": "The borrower shall pay standard interest charges monthly on the principal amount.",
            "char_start": 0,
            "char_end": 80,
        },
        {
            "doc_id": "fake",
            "page": 2,
            "chunk_id": "fake::p2::c0",
            "text": "Special prepayment charges and quetzalcoatl collateral waiver apply only to gold ornaments.",
            "char_start": 0,
            "char_end": 90,
        },
        {
            "doc_id": "fake",
            "page": 3,
            "chunk_id": "fake::p3::c0",
            "text": "Default notice must be delivered in writing to the borrower office within ten business days.",
            "char_start": 0,
            "char_end": 91,
        },
        {
            "doc_id": "fake",
            "page": 4,
            "chunk_id": "fake::p4::c0",
            "text": "यदि ब्याज दर में बदलाव प्रतिकूल हो तो ६० दिनों के भीतर फोरक्लोज़ किया जा सकता है।",
            "char_start": 0,
            "char_end": 80,
        },
    ]

    index = BM25Index(doc_id="fake", chunks=fake_chunks, k1=1.5, b=0.75)

    # Check rare query word ranks first
    res1 = index.score_query("What is the quetzalcoatl waiver?")
    res2 = index.score_query("What is the quetzalcoatl waiver?")
    if not res1 or res1[0]["chunk_id"] != "fake::p2::c0":
        return False, f"Rare word chunk did not rank first: got {res1[0]['chunk_id'] if res1 else None}"

    # Check determinism
    ids1 = [(r["chunk_id"], r["score"]) for r in res1]
    ids2 = [(r["chunk_id"], r["score"]) for r in res2]
    if ids1 != ids2:
        return False, f"BM25 results were non-deterministic: {ids1} vs {ids2}"

    # Check Hindi tokenization keeps combining marks and ranks page 4 first
    res_hi = index.score_query("ब्याज फोरक्लोज़")
    if not res_hi or res_hi[0]["chunk_id"] != "fake::p4::c0" or res_hi[0]["score"] <= 0:
        return False, f"Hindi BM25 ranking failed: {res_hi}"

    # Check stopword handling: English stopwords removed, Indic words intact
    tok_en = tokenize("the loan is in New York")
    tok_hi = tokenize("ब्याज और दर")
    if "the" in tok_en or "loan" not in tok_en:
        return False, f"English stopword filtering unexpected: {tok_en}"
    if tok_hi != ["ब्याज", "और", "दर"]:
        return False, f"Hindi tokenization broke combining marks or dropped words: {tok_hi}"

    return True, "BM25 unit tests passed (rare term ranked #1, deterministic scores, Indic combining marks preserved)"


def test_t4_retrieval_benchmark() -> tuple[bool, str, dict[str, Any]]:
    if not FRIEND_QA_CSV.is_file() or not FRIEND_ZIP.is_file():
        return False, "Friend QA file or contracts zip missing.", {}

    # Load 3 SEC contracts strictly read-only from zip archive in memory
    docs_pages: dict[str, dict[int, str]] = {}
    with zipfile.ZipFile(FRIEND_ZIP, "r") as zf:
        for doc_id, member in [
            ("AAR", "000000/1750/0000895813-98-000136_4.txt"),
            ("Zila", "000082/827156/0000950153-01-500650_2.txt"),
            ("CITGO", "000101/1011746/0000950129-03-001503_8.txt"),
        ]:
            raw = zf.read(member).decode("utf-8", errors="ignore")
            docs_pages[doc_id] = _split_edgar_pages(raw)

    with FRIEND_QA_CSV.open("r", encoding="utf-8", errors="ignore") as f:
        friend_rows = list(csv.DictReader(f))

    eval_items: list[dict[str, Any]] = []
    skipped_friend = 0
    for row in friend_rows:
        clause = row.get("supporting_clause_exact", "").strip()
        if not clause:
            skipped_friend += 1
            continue
        eval_items.append({
            "id": row["case_id"],
            "doc_id": row["document_id"],
            "question": row["question"],
            "quote": clause,
            "doc_pages": docs_pages[row["document_id"]],
        })

    # Add the 8 fact questions from 2c-1 using their verified evidence quotes
    fact_2c1 = [
        ("2c1-Q1", "0000027430-25-000005_aesohio10qex10120250630q2", "Who is the Borrower in this First Amendment?"),
        ("2c1-Q2", "0000027430-25-000005_aesohio10qex10120250630q2", "What is the date of the original Term Loan Agreement referenced in Recital A?"),
        ("2c1-Q3", "0000027430-25-000005_aesohio10qex10120250630q2", "Which state's laws govern this Amendment?"),
        ("2c1-Q4", "03_dbs_mitc", "What collateral or security is deposited for this facility?"),
        ("2c1-Q5", "03_dbs_mitc", "What are the two types of interest rate mentioned in the document?"),
        ("2c1-Q6", "03_dbs_mitc", "Are prepayment or foreclosure charges levied on floating interest rate loans?"),
        ("2c1-Q7", "13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi", "अगर ब्याज दर में बदलाव उधारकर्ता के प्रतिकूल है तो वह कितने दिनों के भीतर बिना किसी अतिरिक्त शुल्क के लोन खाता बंद कर सकता है?"),
        ("2c1-Q8", "13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi", "बैंक हॉलिडे के कारण पेमेंट क्रेडिट होने में T+ कितने दिनों से अधिक का समय लग सकता है?"),
    ]
    # Use cached answers from 2c-1 (0 API calls) to get verified quotes for 2c1-Q1..Q8
    client = GeminiClient()
    for cid, did, q in fact_2c1:
        ans = answer_question(did, q, client=client, force_retrieval=False)
        ev_quotes = [e["quote"] for e in ans.get("evidence", []) if e.get("quote")]
        eval_items.append({
            "id": cid,
            "doc_id": did,
            "question": q,
            "quotes": ev_quotes,
            "doc_pages": None,
        })

    hits = {1: 0, 3: 0, 5: 0, 8: 0}
    missed: list[dict[str, Any]] = []
    crashes = 0

    for item in eval_items:
        try:
            top_chunks = retrieve(
                doc_id=item["doc_id"],
                question=item["question"],
                top_k=8,
                doc_pages=item["doc_pages"],
            )
        except Exception as exc:
            crashes += 1
            missed.append({
                "id": item["id"],
                "question": item["question"],
                "reason": f"Exception: {exc}",
            })
            continue

        candidate_quotes = item.get("quotes") or ([item["quote"]] if item.get("quote") else [])
        norm_candidates = [normalize(q) for q in candidate_quotes if q]

        first_hit_rank: int | None = None
        for ch in top_chunks:
            chunk_norm = normalize(ch["text"])
            if any(nq in chunk_norm for nq in norm_candidates):
                first_hit_rank = int(ch["rank"])
                break

        if first_hit_rank is not None:
            for k in (1, 3, 5, 8):
                if first_hit_rank <= k:
                    hits[k] += 1
        else:
            top_pages = [(c["rank"], c["page"], round(c["score"], 2)) for c in top_chunks[:3]]
            missed.append({
                "id": item["id"],
                "question": item["question"],
                "reason": f"Verified quote not in top-8 chunks (top3 rank/page/score: {top_pages})",
            })

    total = len(eval_items)
    metrics = {
        "friend_file": str(FRIEND_QA_CSV.relative_to(ROOT)),
        "friend_total": len(friend_rows),
        "friend_usable": len(friend_rows) - skipped_friend,
        "friend_skipped": skipped_friend,
        "total_eval": total,
        "crashes": crashes,
        "hit1": hits[1] / max(1, total) * 100.0,
        "hit3": hits[3] / max(1, total) * 100.0,
        "hit5": hits[5] / max(1, total) * 100.0,
        "hit8": hits[8] / max(1, total) * 100.0,
        "hits": hits,
        "missed": missed,
    }

    passed = (crashes == 0) and (metrics["hit8"] >= 30.7)
    details = (
        f"Used {metrics['friend_usable']}/{metrics['friend_total']} friend Q&A ({metrics['friend_file']}) "
        f"+ {len(fact_2c1)} 2c-1 Q&A = {total} total | Crashes: {crashes} | "
        f"Hit@1={metrics['hit1']:.1f}% ({hits[1]}/{total}), "
        f"Hit@3={metrics['hit3']:.1f}% ({hits[3]}/{total}), "
        f"Hit@5={metrics['hit5']:.1f}% ({hits[5]}/{total}) [baseline: 30.7%], "
        f"Hit@8={metrics['hit8']:.1f}% ({hits[8]}/{total})"
    )
    return passed, details, metrics


def test_t5_end_to_end_force_retrieval() -> tuple[bool, str, dict[str, Any]]:
    client = GeminiClient()
    initial_api_calls = client.api_calls_made

    test_cases = [
        # Document 1: English SEC Agreement
        ("0000027430-25-000005_aesohio10qex10120250630q2", "fact", "Who is the Borrower in this First Amendment?", ["dayton power", "aes ohio"]),
        ("0000027430-25-000005_aesohio10qex10120250630q2", "fact", "What is the date of the original Term Loan Agreement referenced in Recital A?", ["august 14, 2024", "august 14 2024"]),
        ("0000027430-25-000005_aesohio10qex10120250630q2", "fact", "Which state's laws govern this Amendment?", ["new york"]),
        # Document 2: Indian English MITC
        ("03_dbs_mitc", "fact", "What collateral or security is deposited for this facility?", ["gold", "ornaments"]),
        ("03_dbs_mitc", "fact", "What are the two types of interest rate mentioned in the document?", ["fixed", "floating"]),
        ("03_dbs_mitc", "fact", "Are prepayment or foreclosure charges levied on floating interest rate loans?", ["no", "prepayment", "floating"]),
        # Document 3: Hindi MITC
        ("13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi", "fact", "अगर ब्याज दर में बदलाव उधारकर्ता के प्रतिकूल है तो वह कितने दिनों के भीतर बिना किसी अतिरिक्त शुल्क के लोन खाता बंद कर सकता है?", ["60"]),
        ("13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi", "fact", "बैंक हॉलिडे के कारण पेमेंट क्रेडिट होने में T+ कितने दिनों से अधिक का समय लग सकता है?", ["t+1", "1"]),
        # 4 Not-in-document questions
        ("0000027430-25-000005_aesohio10qex10120250630q2", "not_found", "What is the annual interest rate percentage for this loan?", []),
        ("03_dbs_mitc", "not_found", "Can Bitcoin or cryptocurrency be accepted as collateral for this loan?", []),
        ("13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi", "not_found", "What is the penalty fee if the borrower buys property in London?", []),
        ("03_dbs_mitc", "not_found", "What is the maximum home loan amount allowed under this policy?", []),
    ]

    crashes = 0
    json_valid_count = 0
    total_quotes = 0
    verified_quotes = 0
    not_found_correct = 0
    fact_correct = 0
    model_counts: Counter[str] = Counter()
    failures: list[str] = []

    print("\n--- T5: Running End-to-End 12-Question Evaluation with force_retrieval=True ---")
    for idx, (doc_id, q_type, question, expected) in enumerate(test_cases, 1):
        try:
            res = answer_question(doc_id, question, client=client, force_retrieval=True)
        except Exception as exc:
            crashes += 1
            failures.append(f"Q{idx}: CRASH {exc}")
            print(f"  [{idx}/12] CRASH: {exc}")
            continue

        if not res.get("retrieval_used"):
            failures.append(f"Q{idx}: retrieval_used was False despite force_retrieval=True")

        m_used = str(res.get("model_used") or "unknown")
        model_counts[m_used] += 1

        flags = res.get("flags", [])
        if "invalid_json_response" not in flags:
            json_valid_count += 1

        status = res.get("status")
        answer = res.get("answer", "")
        evidence = res.get("evidence", [])
        raw_ev = res.get("raw_evidence", evidence)

        if q_type == "fact":
            total_quotes += len(raw_ev)
            verified_quotes += len(evidence)
            norm_ans = normalize(answer)
            ans_matches = any(normalize(exp) in norm_ans for exp in expected)
            if status == "ok" and ans_matches and len(evidence) > 0:
                fact_correct += 1
                print(
                    f"  [{idx}/12] PASS (Fact) | pages={res.get('retrieved_pages')} | "
                    f"model={m_used} | quotes={len(evidence)}/{len(raw_ev)}"
                )
            else:
                failures.append(f"Q{idx}: status={status}, ans_matches={ans_matches}, quotes={len(evidence)}/{len(raw_ev)}")
                print(
                    f"  [{idx}/12] FAIL (Fact) | status={status}, pages={res.get('retrieved_pages')}, "
                    f"ans={answer[:50]!r}"
                )
        else:
            is_nf = (status == "not_found") or ("not found in this document" in normalize(answer))
            if is_nf:
                not_found_correct += 1
                print(
                    f"  [{idx}/12] PASS (Not-Found) | pages={res.get('retrieved_pages')} | model={m_used}"
                )
            else:
                failures.append(f"Q{idx}: expected not_found, got status={status}, ans={answer[:60]!r}")
                print(f"  [{idx}/12] FAIL (Not-Found) | status={status}, ans={answer[:50]!r}")

    new_calls = client.api_calls_made - initial_api_calls
    json_valid_rate = json_valid_count / len(test_cases) * 100.0
    verified_quote_rate = (verified_quotes / max(1, total_quotes)) * 100.0 if total_quotes > 0 else 0.0
    not_found_rate = not_found_correct / 4 * 100.0
    fact_rate = fact_correct / 8 * 100.0

    metrics = {
        "crashes": crashes,
        "new_api_calls": new_calls,
        "json_valid_rate": json_valid_rate,
        "verified_quote_rate": verified_quote_rate,
        "verified_quotes": verified_quotes,
        "total_quotes": total_quotes,
        "not_found_correct": not_found_correct,
        "not_found_rate": not_found_rate,
        "fact_correct": fact_correct,
        "fact_rate": fact_rate,
        "model_counts": dict(model_counts),
        "failures": failures,
    }

    passed = (crashes == 0) and (verified_quote_rate >= 95.0) and (new_calls <= 15)
    details = (
        f"Crashes: {crashes} | API calls: {new_calls} | "
        f"JSON valid: {json_valid_rate:.1f}% (vs 2c-1: 100.0%) | "
        f"Verified quotes: {verified_quote_rate:.1f}% ({verified_quotes}/{total_quotes}, vs 2c-1: 100.0%) | "
        f"Not-found: {not_found_correct}/4 ({not_found_rate:.1f}%, vs 2c-1: 100.0%) | "
        f"Fact acc: {fact_correct}/8 ({fact_rate:.1f}%, vs 2c-1: 100.0%) | "
        f"model_used={dict(model_counts)}"
    )
    return passed, details, metrics


def test_t6_over_limit_document() -> tuple[bool, str]:
    qa_cfg = load_qa_config()
    limit = int(qa_cfg.get("max_doc_chars_for_whole_doc", 400000))

    over_limit_docs: list[Path] = []
    max_len = 0
    for txt_path in sorted(INGESTED_DIR.glob("*.txt")):
        length = len(txt_path.read_text(encoding="utf-8", errors="ignore"))
        if length > max_len:
            max_len = length
        if length > limit:
            over_limit_docs.append(txt_path)

    if not over_limit_docs:
        msg = f"SKIPPED: no document over limit (max in data/processed/ingested is {max_len:,} chars <= {limit:,})"
        return True, msg

    target_doc = over_limit_docs[0].stem
    client = GeminiClient()
    q1 = answer_question(target_doc, "Who are the borrower and lender parties?", client=client)
    q2 = answer_question(target_doc, "What is the maturity date or loan term?", client=client)
    if not (q1.get("retrieval_used") and q2.get("retrieval_used")):
        return False, f"Document {target_doc} (> {limit}) did not trigger automatic retrieval!"
    return True, f"Auto-retrieval triggered on {target_doc} ({max_len:,} chars): q1={q1.get('status')}, q2={q2.get('status')}"


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("=" * 80)
    print("TEST SUITE: STAGE 2c-2a (PURE-PYTHON BM25 RETRIEVAL)")
    print("=" * 80)

    p1, m1 = test_t1_imports_and_key_safety()
    print(f"[{'PASS' if p1 else 'FAIL'}] T1: Imports & API Key Safety")
    print(f"       Details: {m1}")

    p2, m2 = test_t2_chunker_unit_tests()
    print(f"[{'PASS' if p2 else 'FAIL'}] T2: Chunker Unit Tests (No API)")
    print(f"       Details: {m2}")

    p3, m3 = test_t3_bm25_unit_tests()
    print(f"[{'PASS' if p3 else 'FAIL'}] T3: BM25 Unit Tests on Tiny Corpus (No API)")
    print(f"       Details: {m3}")

    p4, m4, t4_metrics = test_t4_retrieval_benchmark()
    print(f"[{'PASS' if p4 else 'FAIL'}] T4: Retrieval-Only Benchmark (Friend 35 + 2c-1 8 = 43 Q&A)")
    print(f"       Details: {m4}")
    missed = t4_metrics.get("missed", [])
    if missed:
        print(f"       Missed Questions ({len(missed)}):")
        for item in missed[:15]:
            print(f"         - [{item['id']}] {item['question']}")
            print(f"           Reason: {item['reason']}")

    p5, m5, t5_metrics = test_t5_end_to_end_force_retrieval()
    print(f"[{'PASS' if p5 else 'FAIL'}] T5: End-to-End QA with force_retrieval=True")
    print(f"       Details: {m5}")
    if t5_metrics.get("failures"):
        for fmsg in t5_metrics["failures"]:
            print(f"         - Failure: {fmsg}")

    p6, m6 = test_t6_over_limit_document()
    tag6 = "SKIP" if m6.startswith("SKIPPED:") else ("PASS" if p6 else "FAIL")
    print(f"[{tag6}] T6: Real Document Over {load_qa_config().get('max_doc_chars_for_whole_doc', 400000):,} Chars (No Forcing)")
    print(f"       Details: {m6}")

    overall = p1 and p2 and p3 and p4 and p5 and p6
    print("=" * 80)
    print(f"OVERALL RESULT: {'PASS' if overall else 'FAIL'}")
    print("=" * 80)

    if not overall:
        sys.exit(1)


if __name__ == "__main__":
    main()
