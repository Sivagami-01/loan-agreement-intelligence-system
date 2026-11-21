"""scripts/demo_ocr_compare.py

Demo CLI for OCR Engine Comparison: Tesseract vs Gemini Vision.
Usage:
    python scripts/demo_ocr_compare.py "<pdf path>" <page number>

Example:
    python scripts/demo_ocr_compare.py "data/raw/08_indian_bank_loans/13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi.pdf" 7
"""

from __future__ import annotations

import argparse
import io
import os
import shutil
import sys
import time
import unicodedata
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image
import pytesseract
from rapidfuzz.distance import Levenshtein

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.llm.gemini_client import GeminiClient

TESSDATA_DIR = ROOT / "data" / "processed" / "tessdata"
GEMINI_PROMPT = "transcribe all text exactly, keep line breaks, no commentary"


def setup_tesseract() -> str | None:
    executable = os.environ.get("TESSERACT_CMD") or shutil.which("tesseract")
    if not executable:
        installed = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        if installed.is_file():
            executable = str(installed)
    if executable:
        pytesseract.pytesseract.tesseract_cmd = executable
    if TESSDATA_DIR.is_dir():
        os.environ["TESSDATA_PREFIX"] = str(TESSDATA_DIR)
    return executable


def detect_script(text: str, filename: str) -> tuple[str, str]:
    """Detects script name and Tesseract language code."""
    script_ranges = {
        "devanagari": (0x0900, 0x097F, "hin"),
        "bengali": (0x0980, 0x09FF, "ben"),
        "gurmukhi": (0x0A00, 0x0A7F, "pan"),
        "malayalam": (0x0D00, 0x0D7F, "mal"),
    }
    counts: dict[str, int] = {}
    for char in text:
        code = ord(char)
        for sname, (start, end, lcode) in script_ranges.items():
            if start <= code <= end:
                counts[sname] = counts.get(sname, 0) + 1
                break

    if counts:
        best_script = max(counts, key=counts.get)  # type: ignore[arg-type]
        if counts[best_script] >= 10:
            return best_script, script_ranges[best_script][2]

    # Fallback to filename hints
    fname = filename.lower()
    if "hindi" in fname or "devanagari" in fname:
        return "devanagari", "hin"
    elif "bengali" in fname or "bangla" in fname:
        return "bengali", "ben"
    elif "punjabi" in fname or "gurmukhi" in fname:
        return "gurmukhi", "pan"
    elif "malayalam" in fname:
        return "malayalam", "mal"

    return "latin", "eng"


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text or "")
    lines = [" ".join(line.split()) for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines).strip()


def calculate_cer(reference: str, hypothesis: str) -> float:
    ref_norm = normalize_text(reference)
    hyp_norm = normalize_text(hypothesis)
    if not ref_norm and not hyp_norm:
        return 0.0
    if not ref_norm:
        return 1.0
    dist = Levenshtein.distance(ref_norm, hyp_norm)
    return round(dist / max(1, len(ref_norm)), 4)


def demo_page(pdf_path: str | Path, page_num: int) -> None:
    pdf_file = Path(pdf_path).resolve()
    if not pdf_file.is_file():
        print(f"Error: PDF file not found at '{pdf_path}'")
        sys.exit(1)

    setup_tesseract()
    client = GeminiClient()

    doc = fitz.open(pdf_file)
    if page_num < 1 or page_num > len(doc):
        print(f"Error: Page number {page_num} out of bounds (1..{len(doc)})")
        sys.exit(1)

    page = doc[page_num - 1]
    ref_text = page.get_text()
    ref_norm = normalize_text(ref_text)
    script_name, lang_code = detect_script(ref_text, pdf_file.name)

    print("=" * 80)
    print(f"OCR COMPARISON DEMO: TESSERACT vs GEMINI VISION")
    print("=" * 80)
    print(f"Document:        {pdf_file.name}")
    print(f"Page Number:     {page_num} of {len(doc)}")
    print(f"Detected Script: {script_name} (lang: {lang_code})")
    print(f"Text Layer Size: {len(ref_norm)} characters (Normalized NFC)")
    print("-" * 80)

    # Render page to JPEG
    pix = page.get_pixmap(matrix=fitz.Matrix(150 / 72, 150 / 72), alpha=False)
    img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    img_bytes = buf.getvalue()

    # 1. Tesseract
    print("Running Tesseract OCR (with eng+lang)...", flush=True)
    lang_arg = f"{lang_code}+eng" if lang_code != "eng" else "eng"
    t0 = time.time()
    tess_text = pytesseract.image_to_string(img, lang=lang_arg, config="--psm 6")
    tess_time = time.time() - t0
    tess_cer = calculate_cer(ref_norm, tess_text)

    # 2. Gemini
    print("Running Gemini Vision OCR...", flush=True)
    t0 = time.time()
    try:
        gemini_text = client.generate(
            GEMINI_PROMPT,
            image_bytes=img_bytes,
            mime_type="image/jpeg",
            model_alias="main",
        )
        gemini_time = time.time() - t0
        gemini_cer = calculate_cer(ref_norm, gemini_text)
    except Exception as exc:
        gemini_text = f"[Gemini Vision unavailable: {exc}]"
        gemini_time = time.time() - t0
        gemini_cer = 1.0

    # Display comparison
    print("\n" + "=" * 80)
    print("--- REFERENCE (PyMuPDF Text Layer Excerpt) ---")
    print("-" * 80)
    print(ref_norm[:400] + ("..." if len(ref_norm) > 400 else ""))

    print("\n" + "=" * 80)
    print(f"--- ENGINE 1: TESSERACT ({lang_arg}) ---")
    print(f"Time Taken:  {tess_time:.2f}s")
    print(f"Output Size: {len(normalize_text(tess_text))} chars")
    print(f"CER:         {tess_cer * 100:.2f}%")
    print("-" * 80)
    print(normalize_text(tess_text)[:400] + ("..." if len(tess_text) > 400 else ""))

    print("\n" + "=" * 80)
    print("--- ENGINE 2: GEMINI VISION ---")
    print(f"Time Taken:  {gemini_time:.2f}s")
    print(f"Output Size: {len(normalize_text(gemini_text))} chars")
    print(f"CER:         {gemini_cer * 100:.2f}%")
    print("-" * 80)
    print(normalize_text(gemini_text)[:400] + ("..." if len(gemini_text) > 400 else ""))

    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)
    if abs(tess_cer - gemini_cer) < 0.01:
        print(f"TIE: Both engines achieved comparable accuracy (Tesseract: {tess_cer*100:.1f}%, Gemini: {gemini_cer*100:.1f}%)")
    elif gemini_cer < tess_cer:
        diff = (tess_cer - gemini_cer) * 100
        print(f"WINNER: Gemini Vision (CER: {gemini_cer*100:.1f}% vs Tesseract: {tess_cer*100:.1f}%, +{diff:.1f}% lower error)")
    else:
        diff = (gemini_cer - tess_cer) * 100
        print(f"WINNER: Tesseract (CER: {tess_cer*100:.1f}% vs Gemini: {gemini_cer*100:.1f}%, +{diff:.1f}% lower error)")

    print(f"Speed comparison: Tesseract {tess_time:.2f}s vs Gemini {gemini_time:.2f}s")
    print("=" * 80 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Demo OCR engine comparison on a PDF page")
    parser.add_argument("pdf_path", type=str, help="Path to PDF document")
    parser.add_argument("page_number", type=int, help="1-based page number")
    args = parser.parse_args()

    demo_page(args.pdf_path, args.page_number)


if __name__ == "__main__":
    main()
