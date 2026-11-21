from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.ingest import DEFAULT_OUT_DIR, ingest_pdf_page


def demo(pdf_path_str: str, page_number_str: str) -> int:
    pdf_path = Path(pdf_path_str)
    if not pdf_path.is_file():
        print(f"Error: PDF file not found at '{pdf_path}'", file=sys.stderr)
        return 1

    try:
        page_number = int(page_number_str)
    except ValueError:
        print(f"Error: Page number must be an integer, got '{page_number_str}'", file=sys.stderr)
        return 1

    # Check if pre-ingested JSON already exists
    ingested_json = DEFAULT_OUT_DIR / f"{pdf_path.stem}.json"
    page_data = None
    total_pages = None

    if ingested_json.is_file():
        try:
            payload = json.loads(ingested_json.read_text(encoding="utf-8"))
            total_pages = payload.get("total_pages")
            for p in payload.get("pages", []):
                if int(p.get("page", -1)) == page_number:
                    page_data = p
                    break
        except Exception:
            pass

    # If not found in pre-ingested JSON, extract live
    if page_data is None:
        try:
            with fitz.open(pdf_path) as doc:
                total_pages = doc.page_count
                if page_number < 1 or page_number > total_pages:
                    print(
                        f"Error: Page number {page_number} is out of range. "
                        f"PDF has {total_pages} page(s) (1..{total_pages}).",
                        file=sys.stderr,
                    )
                    return 1
                page_data = ingest_pdf_page(doc[page_number - 1], page_number, pdf_path.name)
        except Exception as exc:
            print(f"Error reading PDF '{pdf_path}': {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1

    text = page_data.get("text", "")
    source = page_data.get("source", "unknown")
    quality = page_data.get("quality", "unknown")
    ocr_used = page_data.get("ocr_used", False)
    ocr_conf = page_data.get("ocr_confidence")
    ocr_lang = page_data.get("ocr_language")
    detected_script = page_data.get("detected_script")
    tables = page_data.get("tables", [])

    print("=" * 70)
    print("DEMO INGESTION VIEWER")
    print("=" * 70)
    print(f"Document:         {pdf_path.name}")
    print(f"Full Path:        {pdf_path.resolve()}")
    print(f"Page Number:      {page_number} of {total_pages}")
    print(f"Extraction Source: {source} (ocr_used={ocr_used})")
    print(f"Quality Verdict:  {quality}")
    if detected_script:
        print(f"Detected Script:  {detected_script}")
    if ocr_used:
        print(f"OCR Language:     {ocr_lang}")
        print(f"OCR Confidence:   {ocr_conf}%" if ocr_conf is not None else "OCR Confidence:   n/a")
    print(f"Tables Extracted: {len(tables)}")
    print(f"Text Length:      {len(text)} characters, {len(text.split())} words")
    print("-" * 70)
    print("EXTRACTED TEXT:")
    print("-" * 70)
    if text.strip():
        # Encode safely to avoid windows cp1252 print errors
        try:
            print(text)
        except UnicodeEncodeError:
            safe_text = text.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(
                sys.stdout.encoding or "utf-8"
            )
            print(safe_text)
    else:
        print("[PAGE HAS NO EXTRACTED TEXT OR IS EMPTY]")
    print("=" * 70)

    if tables:
        print(f"\nSTRUCTURED TABLES ON PAGE {page_number} ({len(tables)} table(s)):")
        for idx, tab in enumerate(tables, 1):
            print(f"\n--- Table {idx} ({tab.get('row_count', 0)} rows x {tab.get('col_count', 0)} cols) ---")
            cols = tab.get("columns", [])
            if cols:
                print("Columns: " + " | ".join(cols[:6]) + ("..." if len(cols) > 6 else ""))
            for r_idx, row in enumerate(tab.get("rows", [])[:5]):
                preview = " | ".join(str(c).replace("\n", " ") for c in row[:6])
                print(f"Row {r_idx + 1}: {preview}")
            if tab.get("row_count", 0) > 5:
                print(f"... ({tab.get('row_count') - 5} more rows)")
        print("=" * 70)

    return 0


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    parser = argparse.ArgumentParser(
        description="Demo viewer: inspect extracted text and quality verdict for a PDF page."
    )
    parser.add_argument("pdf_path", help="Path to PDF document.")
    parser.add_argument("page_number", help="1-based page number to inspect.")
    args = parser.parse_args()

    sys.exit(demo(args.pdf_path, args.page_number))


if __name__ == "__main__":
    main()
