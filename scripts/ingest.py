from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import shutil
import sys
import time
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

import fitz
from bs4 import BeautifulSoup
from PIL import Image
import pytesseract

ROOT = Path(__file__).resolve().parents[1]
TESSDATA_DIR = ROOT / "data" / "processed" / "tessdata"
PARSED_OCR_DIR = ROOT / "data" / "processed" / "parsed_ocr"
DEFAULT_OUT_DIR = ROOT / "data" / "processed" / "ingested"
INDIAN_SCOPE_CSV = ROOT / "data" / "processed" / "indian_source_scope.csv"

SCRIPT_RANGES = {
    "devanagari": (0x0900, 0x097F),
    "bengali": (0x0980, 0x09FF),
    "gurmukhi": (0x0A00, 0x0A7F),
    "malayalam": (0x0D00, 0x0D7F),
}

LANGUAGE_HINTS = {
    "hindi": ("devanagari", "hin"),
    "devanagari": ("devanagari", "hin"),
    "bengali": ("bengali", "ben"),
    "bangla": ("bengali", "ben"),
    "punjabi": ("gurmukhi", "pan"),
    "gurmukhi": ("gurmukhi", "pan"),
    "malayalam": ("malayalam", "mal"),
}


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


def detect_script_from_text(text: str) -> str | None:
    if not text:
        return None
    counts = Counter()
    for char in text:
        code = ord(char)
        for script, (start, end) in SCRIPT_RANGES.items():
            if start <= code <= end:
                counts[script] += 1
                break
    if not counts:
        return None
    top_script, count = counts.most_common(1)[0]
    if count >= 10:
        return top_script
    return None


def detect_page_script(doc_filename: str, page_text: str | None = None) -> tuple[str | None, str]:
    if page_text:
        detected = detect_script_from_text(page_text)
        if detected:
            lang_code = {
                "devanagari": "hin",
                "bengali": "ben",
                "gurmukhi": "pan",
                "malayalam": "mal",
            }.get(detected, "eng")
            return detected, lang_code

    lowered = doc_filename.casefold()
    for hint, (script, lang_code) in LANGUAGE_HINTS.items():
        if hint in lowered:
            return script, lang_code

    return None, "eng"


def check_page_quality(text: str, script: str | None) -> tuple[str, dict[str, Any]]:
    clean_text = text.strip()
    if not clean_text:
        return "BAD", {"is_empty": True, "reason": "empty_text"}

    cid_count = len(re.findall(r"\(cid:\s*\d+\)", text, re.IGNORECASE))
    pua_count = sum(0xE000 <= ord(c) <= 0xF8FF for c in text)
    replacement_count = text.count("\ufffd")
    symbol_run = bool(re.search(r"(?:[^\w\s]){8,}", text))

    if cid_count > 0 or pua_count > 0 or replacement_count > 0:
        return "BAD", {
            "is_empty": False,
            "cid_count": cid_count,
            "pua_count": pua_count,
            "replacement_count": replacement_count,
            "symbol_run": symbol_run,
            "reason": "severe_corruption",
        }

    if script in SCRIPT_RANGES:
        s_start, s_end = SCRIPT_RANGES[script]
        script_chars = sum(1 for c in text if s_start <= ord(c) <= s_end)
        latin_chars = sum(1 for c in text if "a" <= c.lower() <= "z")
        total_letters = script_chars + latin_chars
        script_share = script_chars / max(1, total_letters)

        metrics = {
            "is_empty": False,
            "script_chars": script_chars,
            "latin_chars": latin_chars,
            "total_letters": total_letters,
            "script_share": round(script_share, 4),
            "symbol_run": symbol_run,
        }

        if total_letters < 20 or symbol_run or script_share < 0.12:
            return "BAD", metrics
        elif script_share < 0.50:
            return "SUSPICIOUS", metrics
        else:
            return "GOOD", metrics
    else:
        letters = sum(1 for c in text if c.isalpha())
        visible = [c for c in text if not c.isspace()]
        symbol_share = (
            sum(not c.isalnum() and unicodedata.category(c)[0] not in {"M"} for c in visible)
            / max(1, len(visible))
            if visible
            else 0.0
        )

        metrics = {
            "is_empty": False,
            "letters": letters,
            "symbol_share": round(symbol_share, 4),
            "symbol_run": symbol_run,
        }

        if len(clean_text) < 50 or letters < 20 or symbol_run or symbol_share > 0.45:
            return "BAD", metrics
        elif letters / max(1, len(clean_text)) < 0.40:
            return "SUSPICIOUS", metrics
        else:
            return "GOOD", metrics


def extract_tables_from_page(page: fitz.Page, page_number: int) -> list[dict[str, Any]]:
    tables_data: list[dict[str, Any]] = []
    try:
        tabs = page.find_tables()
        for t_idx, tab in enumerate(tabs.tables):
            extracted = tab.extract()
            if not extracted:
                continue
            cleaned_rows = [
                [str(cell).strip() if cell is not None else "" for cell in row]
                for row in extracted
            ]
            if not any(any(cell for cell in row) for row in cleaned_rows):
                continue
            cols: list[str] = []
            if hasattr(tab, "header") and tab.header and tab.header.names:
                cols = [str(c).strip() if c is not None else "" for c in tab.header.names]
            elif cleaned_rows:
                cols = list(cleaned_rows[0])
            tables_data.append({
                "page": page_number,
                "table_index": t_idx + 1,
                "bbox": [round(float(c), 2) for c in tab.bbox] if hasattr(tab, "bbox") and tab.bbox else [],
                "row_count": len(cleaned_rows),
                "col_count": len(cleaned_rows[0]) if cleaned_rows else 0,
                "columns": cols,
                "rows": cleaned_rows,
            })
    except Exception as exc:
        print(f"Warning: table extraction on page {page_number} encountered: {exc}", flush=True)
    return tables_data


def get_cached_ocr(doc_name: str, page_number: int) -> tuple[str, float | None] | None:
    json_candidates = [
        PARSED_OCR_DIR / "indian" / (Path(doc_name).stem + ".json"),
        PARSED_OCR_DIR / "cuad" / (Path(doc_name).stem + ".json"),
    ]
    for candidate in json_candidates:
        if candidate.is_file():
            try:
                data = json.loads(candidate.read_text(encoding="utf-8"))
                for page_entry in data.get("pages", []):
                    if int(page_entry.get("page", -1)) == page_number:
                        ocr_text = str(page_entry.get("text", ""))
                        conf = page_entry.get("ocr_confidence_mean")
                        if conf is None and "machine_metrics" in page_entry:
                            conf = page_entry["machine_metrics"].get("ocr_confidence_mean")
                        return ocr_text, float(conf) if conf is not None else None
            except Exception:
                pass
    return None


def run_ocr(page: fitz.Page, lang_code: str, dpi: int = 200) -> tuple[str, float | None]:
    setup_tesseract()
    pixmap = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72), alpha=False)
    image = Image.open(io.BytesIO(pixmap.tobytes("png"))).convert("RGB")
    lang_pack = f"{lang_code}+eng" if lang_code != "eng" else "eng"
    data = pytesseract.image_to_data(
        image, lang=lang_pack, config="--psm 3", output_type=pytesseract.Output.DICT
    )
    lines: dict[tuple[int, int, int], list[str]] = {}
    for index, raw in enumerate(data.get("text", [])):
        token = str(raw).strip()
        if not token:
            continue
        line_key = (
            int(data["block_num"][index]),
            int(data["par_num"][index]),
            int(data["line_num"][index]),
        )
        lines.setdefault(line_key, []).append(token)
    text = "\n".join(" ".join(tokens) for tokens in lines.values())
    confidences = []
    for raw in data.get("conf", []):
        try:
            val = float(raw)
            if val >= 0:
                confidences.append(val)
        except (TypeError, ValueError):
            continue
    confidence = round(sum(confidences) / len(confidences), 2) if confidences else None
    return text, confidence


def ingest_pdf_page(
    page: fitz.Page,
    page_number: int,
    doc_filename: str,
) -> dict[str, Any]:
    raw_text = page.get_text()
    script, lang_code = detect_page_script(doc_filename, raw_text)
    initial_quality, initial_metrics = check_page_quality(raw_text, script)
    tables = extract_tables_from_page(page, page_number)

    needs_ocr = initial_quality == "BAD" or initial_metrics.get("is_empty")

    ocr_used = False
    ocr_confidence: float | None = None
    ocr_language: str | None = None
    final_text = raw_text
    final_quality = initial_quality

    if needs_ocr:
        cached = get_cached_ocr(doc_filename, page_number)
        if cached:
            ocr_text, ocr_conf = cached
        else:
            setup_tesseract()
            ocr_text, ocr_conf = run_ocr(page, lang_code)

        ocr_quality, ocr_metrics = check_page_quality(ocr_text, script)
        ocr_used = True
        ocr_confidence = ocr_conf
        ocr_language = f"{lang_code}+eng" if lang_code != "eng" else "eng"
        final_text = ocr_text
        final_quality = ocr_quality

    is_empty = len(final_text.strip()) == 0

    return {
        "page": page_number,
        "text": final_text,
        "source": "ocr" if ocr_used else "text_layer",
        "quality": final_quality,
        "ocr_used": ocr_used,
        "ocr_confidence": ocr_confidence,
        "ocr_language": ocr_language,
        "detected_script": script,
        "is_empty": is_empty,
        "tables": tables,
    }


def ingest_pdf(path: Path | str, out_dir: Path = DEFAULT_OUT_DIR) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"Input PDF not found: {file_path}")

    start_time = time.time()
    pages_data: list[dict[str, Any]] = []
    all_tables: list[dict[str, Any]] = []

    with fitz.open(file_path) as doc:
        for page_number, page in enumerate(doc, 1):
            page_info = ingest_pdf_page(page, page_number, file_path.name)
            pages_data.append(page_info)
            if page_info["tables"]:
                all_tables.extend(page_info["tables"])

    duration = round(time.time() - start_time, 3)
    ocr_pages_count = sum(1 for p in pages_data if p["ocr_used"])

    payload: dict[str, Any] = {
        "source": str(file_path.resolve()),
        "filename": file_path.name,
        "format": "pdf",
        "total_pages": len(pages_data),
        "processing_time_seconds": duration,
        "ocr_pages_count": ocr_pages_count,
        "tables_count": len(all_tables),
        "pages": pages_data,
        "tables": all_tables,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    out_json = out_dir / f"{file_path.stem}.json"
    out_txt = out_dir / f"{file_path.stem}.txt"

    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    txt_lines: list[str] = []
    for p in pages_data:
        txt_lines.append(f"[[PAGE {p['page']}]]\n{p['text'].strip()}")
    full_text = "\n\n".join(txt_lines) + "\n"
    out_txt.write_text(full_text, encoding="utf-8")

    return payload


def ingest_html(path: Path | str, out_dir: Path = DEFAULT_OUT_DIR) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"Input HTML file not found: {file_path}")

    start_time = time.time()
    raw_bytes = file_path.read_bytes()
    raw_str = raw_bytes.decode("utf-8", errors="ignore")

    soup = BeautifulSoup(raw_str, "lxml")
    for element in soup(["script", "style"]):
        element.decompose()

    all_tables: list[dict[str, Any]] = []
    for t_idx, t in enumerate(soup.find_all("table"), 1):
        rows = []
        for tr in t.find_all("tr"):
            row = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if any(row):
                rows.append(row)
        if rows:
            all_tables.append({
                "page": 1,
                "table_index": t_idx,
                "bbox": [],
                "row_count": len(rows),
                "col_count": max(len(r) for r in rows),
                "columns": rows[0],
                "rows": rows,
            })

    text = soup.get_text("\n")
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    chunks: list[str] = []
    cur = ""
    for para in text.split("\n\n"):
        if len(cur) + len(para) > 3000 and cur:
            chunks.append(cur)
            cur = ""
        cur += para + "\n\n"
    if cur.strip():
        chunks.append(cur)

    if not chunks:
        chunks = [""]

    pages_data: list[dict[str, Any]] = []
    for i, chunk in enumerate(chunks, 1):
        quality, metrics = check_page_quality(chunk, None)
        pages_data.append({
            "page": i,
            "text": chunk.strip(),
            "source": "text_layer",
            "quality": quality,
            "ocr_used": False,
            "ocr_confidence": None,
            "ocr_language": None,
            "detected_script": None,
            "is_empty": len(chunk.strip()) == 0,
            "tables": [t for t in all_tables if t["page"] == i] if i == 1 else [],
        })

    duration = round(time.time() - start_time, 3)

    payload: dict[str, Any] = {
        "source": str(file_path.resolve()),
        "filename": file_path.name,
        "format": "html",
        "total_pages": len(pages_data),
        "processing_time_seconds": duration,
        "ocr_pages_count": 0,
        "tables_count": len(all_tables),
        "pages": pages_data,
        "tables": all_tables,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    out_json = out_dir / f"{file_path.stem}.json"
    out_txt = out_dir / f"{file_path.stem}.txt"

    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    txt_lines: list[str] = []
    for p in pages_data:
        txt_lines.append(f"[[PAGE {p['page']}]]\n{p['text'].strip()}")
    full_text = "\n\n".join(txt_lines) + "\n"
    out_txt.write_text(full_text, encoding="utf-8")

    return payload


def ingest_file(path: Path | str, out_dir: Path = DEFAULT_OUT_DIR) -> dict[str, Any]:
    target = Path(path)
    suffix = target.suffix.lower()
    if suffix == ".pdf":
        return ingest_pdf(target, out_dir)
    elif suffix in (".htm", ".html"):
        return ingest_html(target, out_dir)
    else:
        raise ValueError(f"Unsupported file extension {suffix} for {target}")


def get_batch_files() -> list[tuple[str, Path]]:
    batch_files: list[tuple[str, Path]] = []

    # 1. 16 qualifying Indian PDFs
    if INDIAN_SCOPE_CSV.is_file():
        with INDIAN_SCOPE_CSV.open(encoding="utf-8-sig") as stream:
            for row in csv.DictReader(stream):
                if row.get("in_scope_for_loan_corpus", "").casefold() in ("true", "1"):
                    pdf_path = ROOT / "data" / "raw" / "08_indian_bank_loans" / row["filename"]
                    if pdf_path.is_file():
                        batch_files.append(("indian", pdf_path))

    # 2. 20 CUAD PDFs
    cuad_candidates = sorted((ROOT / "data" / "raw" / "01_cuad").rglob("*.pdf"))[:20]
    for c_path in cuad_candidates:
        batch_files.append(("cuad", c_path))

    # 3. 10 SEC EDGAR loans
    edgar_candidates = sorted((ROOT / "data" / "raw" / "02_sec_edgar_loans").glob("*.htm*"))[:10]
    for e_path in edgar_candidates:
        batch_files.append(("edgar", e_path))

    return batch_files


def run_batch(out_dir: Path = DEFAULT_OUT_DIR) -> None:
    batch_files = get_batch_files()
    print(f"Starting batch ingestion for {len(batch_files)} documents...", flush=True)

    out_dir.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, Any]] = []
    crashes: list[dict[str, Any]] = []

    total_start = time.time()
    for index, (group, file_path) in enumerate(batch_files, 1):
        print(f"[{index}/{len(batch_files)}] ({group}) {file_path.name} ... ", end="", flush=True)
        try:
            result = ingest_file(file_path, out_dir)
            pages_count = result["total_pages"]
            ocr_count = result["ocr_pages_count"]
            tabs_count = result["tables_count"]
            sec = result["processing_time_seconds"]
            print(f"OK ({pages_count} pages, {ocr_count} OCR, {tabs_count} tables, {sec}s)", flush=True)
            manifest.append({
                "group": group,
                "file": file_path.name,
                "pages": pages_count,
                "ocr_pages": ocr_count,
                "tables": tabs_count,
                "duration": sec,
                "status": "SUCCESS",
            })
        except Exception as exc:
            print(f"FAILED: {type(exc).__name__}: {exc}", flush=True)
            crashes.append({
                "group": group,
                "file": file_path.name,
                "error": f"{type(exc).__name__}: {exc}",
            })
            manifest.append({
                "group": group,
                "file": file_path.name,
                "status": "ERROR",
                "error": str(exc),
            })

    total_time = round(time.time() - total_start, 2)
    summary_path = out_dir / "ingestion_summary.json"
    summary_path.write_text(
        json.dumps({
            "total_files": len(batch_files),
            "successful": len(manifest) - len(crashes),
            "crashes": len(crashes),
            "total_duration_seconds": total_time,
            "manifest": manifest,
            "crash_details": crashes,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nBatch complete: {len(manifest) - len(crashes)}/{len(batch_files)} succeeded. Crashes: {len(crashes)}. Total time: {total_time}s.")
    print(f"Outputs written to: {out_dir}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    parser = argparse.ArgumentParser(
        description="Ingest PDFs and contracts: per-page text, quality check, OCR fallback, table extraction."
    )
    parser.add_argument("path", nargs="?", default=None, help="Path to PDF or HTML file to ingest.")
    parser.add_argument("--batch", action="store_true", help="Run batch ingestion on 16 Indian + 20 CUAD + 10 EDGAR documents.")
    parser.add_argument("--out-dir", default=None, help="Directory to save ingested JSON and TXT files.")

    args = parser.parse_args()
    out_dir = Path(args.out_dir) if args.out_dir else DEFAULT_OUT_DIR

    if args.batch:
        run_batch(out_dir)
    elif args.path:
        path = Path(args.path)
        print(f"Ingesting {path} ...", flush=True)
        res = ingest_file(path, out_dir)
        print(f"Finished {path.name}: {res['total_pages']} pages, {res['ocr_pages_count']} OCR'd, {res['tables_count']} tables in {res['processing_time_seconds']}s.")
        print(f"Output: {out_dir / (path.stem + '.json')} and .txt")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
