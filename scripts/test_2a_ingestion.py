from __future__ import annotations

import csv
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import fitz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.ingest import (
    DEFAULT_OUT_DIR,
    INDIAN_SCOPE_CSV,
    SCRIPT_RANGES,
    get_batch_files,
)


def run_tests() -> int:
    print("=" * 75)
    print("STAGE 2a INGESTION TEST SUITE")
    print("=" * 75)

    batch_files = get_batch_files()
    total_batch_count = len(batch_files)
    print(f"Batch definition: {total_batch_count} expected files "
          f"(16 Indian, 20 CUAD, 10 SEC EDGAR loans)")

    ingested_dir = DEFAULT_OUT_DIR
    if not ingested_dir.is_dir():
        print(f"\n[FAIL] Ingestion output directory not found: {ingested_dir}")
        print("Please run 'python scripts/ingest.py --batch' first.")
        return 1

    # Load summary if present
    summary_file = ingested_dir / "ingestion_summary.json"
    summary_data = {}
    if summary_file.is_file():
        try:
            summary_data = json.loads(summary_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Load all output documents corresponding to batch files
    loaded_docs: list[dict[str, Any]] = []
    missing_outputs: list[str] = []

    for group, src_path in batch_files:
        stem = src_path.stem
        json_path = ingested_dir / f"{stem}.json"
        txt_path = ingested_dir / f"{stem}.txt"
        if not json_path.is_file() or not txt_path.is_file():
            missing_outputs.append(f"{stem} (missing json or txt)")
            continue
        try:
            doc_data = json.loads(json_path.read_text(encoding="utf-8"))
            doc_data["_src_path"] = src_path
            doc_data["_group"] = group
            doc_data["_txt_path"] = txt_path
            loaded_docs.append(doc_data)
        except Exception as exc:
            missing_outputs.append(f"{stem} (error reading json: {exc})")

    check_results: list[tuple[str, bool, str]] = []

    # -------------------------------------------------------------
    # Check 1: crashes = 0 on all files in the batch
    # -------------------------------------------------------------
    crash_details = summary_data.get("crash_details", [])
    recorded_crashes = len(crash_details)
    unprocessed_count = total_batch_count - len(loaded_docs)
    total_crashes = recorded_crashes + (unprocessed_count if not crash_details else 0)

    check_1_pass = (total_crashes == 0) and (len(loaded_docs) == total_batch_count)
    check_1_msg = (
        f"Crashes: {total_crashes} / {total_batch_count} files. "
        f"Successfully loaded: {len(loaded_docs)}/{total_batch_count} files."
    )
    if missing_outputs:
        check_1_msg += f" Missing/failed: {', '.join(missing_outputs[:3])}"
    check_results.append(("1. Crashes = 0 on all files in batch", check_1_pass, check_1_msg))

    # -------------------------------------------------------------
    # Check 2: for every PDF, number of pages in output equals PDF page count
    # -------------------------------------------------------------
    pdf_docs = [d for d in loaded_docs if d.get("format") == "pdf" or d["_src_path"].suffix.lower() == ".pdf"]
    pdf_matched = 0
    pdf_mismatches: list[str] = []

    for d in pdf_docs:
        src_path = d["_src_path"]
        try:
            with fitz.open(src_path) as doc:
                src_pages = doc.page_count
        except Exception as exc:
            pdf_mismatches.append(f"{src_path.name}: fitz open failed ({exc})")
            continue

        out_pages = len(d.get("pages", []))
        if src_pages == out_pages:
            pdf_matched += 1
        else:
            pdf_mismatches.append(f"{src_path.name}: source={src_pages} vs output={out_pages}")

    check_2_pass = (pdf_matched == len(pdf_docs)) and (len(pdf_docs) > 0)
    check_2_msg = f"PDFs verified: {pdf_matched}/{len(pdf_docs)} matched source page count exactly."
    if pdf_mismatches:
        check_2_msg += f" Mismatches: {'; '.join(pdf_mismatches[:3])}"
    check_results.append(("2. Output page count == PDF page count", check_2_pass, check_2_msg))

    # -------------------------------------------------------------
    # Check 3: share of pages with non-empty text or explicitly flagged empty
    # -------------------------------------------------------------
    total_pages_checked = 0
    valid_pages = 0
    empty_pages_count = 0

    for d in loaded_docs:
        for p in d.get("pages", []):
            total_pages_checked += 1
            has_text = len(p.get("text", "").strip()) > 0
            is_flagged_empty = p.get("is_empty") is True
            if is_flagged_empty:
                empty_pages_count += 1
            if has_text or is_flagged_empty:
                valid_pages += 1

    share_valid = (valid_pages / total_pages_checked * 100.0) if total_pages_checked else 0.0
    check_3_pass = (total_pages_checked > 0) and (valid_pages == total_pages_checked)
    check_3_msg = (
        f"Pages verified: {valid_pages}/{total_pages_checked} ({share_valid:.2f}%). "
        f"Flagged empty: {empty_pages_count}."
    )
    check_results.append(("3. Non-empty or flagged-empty share == 100%", check_3_pass, check_3_msg))

    # -------------------------------------------------------------
    # Check 4: count of pages OCR'd per file/language, avg time per page & per doc
    # -------------------------------------------------------------
    ocr_per_file: dict[str, int] = {}
    ocr_per_lang: Counter[str] = Counter()
    total_ocr_pages = 0
    total_doc_time = 0.0

    for d in loaded_docs:
        doc_time = d.get("processing_time_seconds", 0.0)
        total_doc_time += doc_time
        doc_ocr_count = 0
        for p in d.get("pages", []):
            if p.get("ocr_used"):
                total_ocr_pages += 1
                doc_ocr_count += 1
                lang = p.get("ocr_language") or "unknown"
                ocr_per_lang[lang] += 1
        if doc_ocr_count > 0:
            ocr_per_file[d["filename"]] = doc_ocr_count

    avg_time_per_doc = (total_doc_time / len(loaded_docs)) if loaded_docs else 0.0
    avg_time_per_page = (total_doc_time / total_pages_checked) if total_pages_checked else 0.0

    check_4_pass = total_ocr_pages > 0 and len(loaded_docs) > 0
    check_4_msg = (
        f"OCR pages: {total_ocr_pages} across {len(ocr_per_file)} files. "
        f"Per language: {dict(ocr_per_lang)}. "
        f"Avg time/doc: {avg_time_per_doc:.3f}s, Avg time/page: {avg_time_per_page:.4f}s."
    )
    check_results.append(("4. OCR counts and processing timing", check_4_pass, check_4_msg))

    # -------------------------------------------------------------
    # Check 5: count of tables extracted per file
    # -------------------------------------------------------------
    tables_per_file: dict[str, int] = {}
    total_tables = 0

    for d in loaded_docs:
        t_count = len(d.get("tables", []))
        total_tables += t_count
        if t_count > 0:
            tables_per_file[d["filename"]] = t_count

    check_5_pass = total_tables > 0 and len(tables_per_file) > 0
    check_5_msg = (
        f"Total tables: {total_tables} extracted across {len(tables_per_file)} files. "
        f"Top table files: {dict(list(tables_per_file.items())[:4])}."
    )
    check_results.append(("5. Count of tables extracted per file", check_5_pass, check_5_msg))

    # -------------------------------------------------------------
    # Check 6: 5 random Indian pages marked GOOD have expected script share > 50%
    # -------------------------------------------------------------
    indian_good_pages: list[tuple[str, int, str, str]] = []
    for d in loaded_docs:
        if d.get("_group") != "indian":
            continue
        fname = d["filename"]
        for p in d.get("pages", []):
            script = p.get("detected_script")
            quality = p.get("quality")
            if script in ("devanagari", "bengali", "gurmukhi", "malayalam") and quality == "GOOD":
                indian_good_pages.append((fname, p["page"], script, p["text"]))

    check_6_pass = True
    check_6_details = []
    if len(indian_good_pages) < 5:
        check_6_pass = False
        check_6_msg = f"Insufficient Indian GOOD pages found: {len(indian_good_pages)} (expected >= 5)."
    else:
        rng = random.Random(42)
        sample = rng.sample(indian_good_pages, 5)
        for fname, p_num, script, text in sample:
            s_start, s_end = SCRIPT_RANGES[script]
            script_chars = sum(1 for c in text if s_start <= ord(c) <= s_end)
            latin_chars = sum(1 for c in text if "a" <= c.lower() <= "z")
            denom = script_chars + latin_chars
            share = script_chars / max(1, denom)
            check_6_details.append(f"{fname[:25]}#p{p_num}({script[:3]}={share:.1%})")
            if share <= 0.50:
                check_6_pass = False

        check_6_msg = (
            f"Pool of GOOD Indic pages: {len(indian_good_pages)}. "
            f"5 sampled shares: {', '.join(check_6_details)}. "
            f"All > 50%: {check_6_pass}."
        )
    check_results.append(("6. 5 random GOOD Indian pages have script share > 50%", check_6_pass, check_6_msg))

    # -------------------------------------------------------------
    # Check 7: [[PAGE n]] markers in .txt are consecutive with no gaps
    # -------------------------------------------------------------
    gapless_files = 0
    gap_failures: list[str] = []

    for d in loaded_docs:
        txt_path = d["_txt_path"]
        txt_content = txt_path.read_text(encoding="utf-8")
        markers = [int(m) for m in re.findall(r"\[\[PAGE\s+(\d+)\]\]", txt_content)]
        expected_markers = list(range(1, len(d.get("pages", [])) + 1))

        if markers == expected_markers and len(markers) > 0:
            gapless_files += 1
        else:
            gap_failures.append(f"{txt_path.name}: markers={markers[:5]}... expected 1..{len(expected_markers)}")

    check_7_pass = (gapless_files == len(loaded_docs)) and (len(loaded_docs) > 0)
    check_7_msg = f"Consecutive gapless markers: {gapless_files}/{len(loaded_docs)} .txt files verified."
    if gap_failures:
        check_7_msg += f" Failures: {'; '.join(gap_failures[:3])}"
    check_results.append(("7. [[PAGE n]] markers consecutive with no gaps", check_7_pass, check_7_msg))

    # -------------------------------------------------------------
    # Summary Display
    # -------------------------------------------------------------
    print("\nRESULTS SUMMARY:")
    print("-" * 75)
    all_passed = True
    for title, status, msg in check_results:
        status_str = "PASS" if status else "FAIL"
        if not status:
            all_passed = False
        print(f"[{status_str}] {title}")
        print(f"       {msg}")

    print("=" * 75)
    if all_passed:
        print("OVERALL: PASS (7/7 checks passed)")
    else:
        print("OVERALL: FAIL (one or more checks failed)")
    print("=" * 75)

    return 0 if all_passed else 1


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    sys.exit(run_tests())


if __name__ == "__main__":
    main()
