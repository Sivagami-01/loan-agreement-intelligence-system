from __future__ import annotations

import csv
import difflib
import io
import json
import os
import re
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import fitz
from PIL import Image
import pytesseract


ROOT = Path(__file__).resolve().parents[1]
INDIAN_JSON = ROOT / "data" / "processed" / "parsed" / "indian"
CUAD_JSON = ROOT / "data" / "processed" / "parsed" / "cuad"
PDF_DIR = ROOT / "data" / "raw" / "08_indian_bank_loans"
TESSDATA = ROOT / "data" / "processed" / "tessdata"
OUT = ROOT / "data" / "processed"
PARSED_OCR = OUT / "parsed_ocr"
PAGE_REPORT = OUT / "page_verification.csv"
CANDIDATES = OUT / "ocr_candidates.csv"
HARD_BAD = OUT / "hard_bad_pages.csv"
FAILURES = OUT / "ocr_processing_failures.csv"
SCOPE_REPORT = OUT / "indian_source_scope.csv"
sys.path.insert(0, str(ROOT))
from tools.verify_indian_text import analyze, expected_script  # noqa: E402


PAGE_FIELDS = [
    "file", "page", "expected_script", "parser_needs_ocr", "source_status",
    "ocr_status", "source_script_share", "ocr_script_share", "latin_letter_share",
    "private_use_count", "cid_count", "non_alphanumeric_share",
    "ocr_non_alphanumeric_share", "source_letter_count", "ocr_letter_count",
    "ocr_confidence_mean", "sequence_similarity", "word_jaccard",
    "source_word_coverage", "candidate_for_ocr", "candidate_reason",
    "machine_verdict", "error",
]
CANDIDATE_FIELDS = [
    "file", "page", "source_status", "parser_needs_ocr", "candidate_reason",
    "ocr_status", "source_script_share", "ocr_script_share",
    "sequence_similarity", "word_jaccard", "ocr_confidence_mean",
]
FAILURE_FIELDS = ["dataset", "file", "page", "error"]
LANGUAGE_HINTS = {
    "hindi": "hin",
    "devanagari": "hin",
    "bengali": "ben",
    "bangla": "ben",
    "punjabi": "pan",
    "gurmukhi": "pan",
    "malayalam": "mal",
}
csv.field_size_limit(20_000_000)


def atomic_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def resolve_pdf(source: str, folder: Path) -> Path:
    candidate = Path(source.replace("\\", os.sep))
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    if candidate.is_file():
        return candidate
    fallback = folder / Path(source.replace("\\", "/")).name
    if fallback.is_file():
        return fallback
    raise FileNotFoundError(f"PDF not found from parsed source {source!r}")


def language_for(filename: str) -> str:
    name = filename.casefold()
    for hint, language in LANGUAGE_HINTS.items():
        if hint in name:
            return language
    return "eng"


def ocr_page(page: fitz.Page, language: str) -> tuple[str, float | None]:
    pixmap = page.get_pixmap(matrix=fitz.Matrix(300 / 72, 300 / 72), alpha=False)
    image = Image.open(io.BytesIO(pixmap.tobytes("png"))).convert("RGB")
    languages = f"{language}+eng" if language != "eng" else "eng"
    data = pytesseract.image_to_data(
        image, lang=languages, config="--psm 6", output_type=pytesseract.Output.DICT
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
            value = float(raw)
        except (TypeError, ValueError):
            continue
        if value >= 0:
            confidences.append(value)
    confidence = sum(confidences) / len(confidences) if confidences else None
    return text, confidence


def normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold()).strip()


def words(text: str) -> list[str]:
    return re.findall(r"\w+", text.casefold(), flags=re.UNICODE)


def comparison(source: str, ocr: str) -> tuple[float, float, float]:
    source_norm, ocr_norm = normalized(source), normalized(ocr)
    similarity = difflib.SequenceMatcher(None, source_norm, ocr_norm, autojunk=False).ratio()
    source_words, ocr_words = set(words(source)), set(words(ocr))
    union = source_words | ocr_words
    jaccard = len(source_words & ocr_words) / len(union) if union else 0.0
    coverage = len(source_words & ocr_words) / len(source_words) if source_words else 0.0
    return similarity, jaccard, coverage


def maybe_float(value: Any) -> float | str:
    return round(value, 4) if isinstance(value, (float, int)) else ""


def main() -> None:
    executable = os.environ.get("TESSERACT_CMD") or shutil.which("tesseract")
    if not executable:
        installed = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        if installed.is_file():
            executable = str(installed)
    if not executable:
        raise FileNotFoundError("Tesseract executable was not found on PATH or in Program Files")
    pytesseract.pytesseract.tesseract_cmd = executable
    os.environ["TESSDATA_PREFIX"] = str(TESSDATA)
    if not (TESSDATA / "eng.traineddata").is_file():
        raise FileNotFoundError(f"Required English tessdata missing from {TESSDATA}")

    excluded_sources: set[str] = set()
    if SCOPE_REPORT.is_file():
        with SCOPE_REPORT.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                if row.get("in_scope_for_loan_corpus", "").casefold() in {"false", "0", "no"}:
                    excluded_sources.add(row.get("filename", "").casefold())
    indian_files = []
    for path in sorted(INDIAN_JSON.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            source_name = Path(str(payload.get("source", path.stem))).name.casefold()
            if source_name not in excluded_sources:
                indian_files.append(path)
            else:
                print(f"Skipping out-of-scope PDF parse: {source_name}", flush=True)
        except Exception as exc:
            print(f"Cannot inspect {path.name} for scope; including it: {type(exc).__name__}: {exc}")
    page_rows: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []
    hard_bad_rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    total_pages = 0

    for index, json_path in enumerate(indian_files, 1):
        print(f"[Indian {index}/{len(indian_files)}] {json_path.name}", flush=True)
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            pages = payload.get("pages", [])
            source = str(payload.get("source", ""))
            pdf_path = resolve_pdf(source, PDF_DIR)
            script = expected_script(json_path.name + " " + source)
            language = language_for(json_path.name + " " + source)
            output_pages: list[dict[str, Any]] = []
            with fitz.open(pdf_path) as document:
                for page_info in pages:
                    number = int(page_info.get("page", 0))
                    total_pages += 1
                    text = str(page_info.get("text", ""))
                    needs_ocr = bool(page_info.get("needs_ocr"))
                    try:
                        if number < 1 or number > document.page_count:
                            raise IndexError(
                                f"page {number} outside PDF page range 1..{document.page_count}"
                            )
                        ocr_text, confidence = ocr_page(document[number - 1], language)
                        source_metrics, source_status, source_flags = analyze(text, script)
                        ocr_metrics, ocr_status, _ = analyze(ocr_text, script)
                        similarity, jaccard, coverage = comparison(text, ocr_text)
                        reasons = []
                        if needs_ocr:
                            reasons.append("parser needs_ocr")
                        if source_status != "GOOD":
                            reasons.append(f"source text {source_status.lower()}")
                        if source_status == "BAD":
                            hard_bad_rows.append({
                                "file": json_path.name, "page": number,
                                "expected_script": script or "",
                                "source_status": source_status,
                                "source_script_share": maybe_float(
                                    source_metrics.get("expected_script_share")
                                ),
                                "private_use_count": source_metrics["private_use_count"],
                                "cid_count": source_metrics["cid_count"],
                                "non_alphanumeric_share": maybe_float(
                                    source_metrics["non_alphanumeric_share"]
                                ),
                                "hard_rule_flags": "; ".join(source_flags),
                                "parser_needs_ocr": needs_ocr,
                            })
                        candidate = bool(reasons)
                        if source_status == "BAD" and ocr_status == "GOOD":
                            verdict = "OCR_RECOVERS_EXPECTED_SCRIPT"
                        elif source_status != "GOOD" and ocr_status != "GOOD":
                            verdict = "OCR_REMAINS_SUSPICIOUS"
                        elif similarity >= 0.60 and jaccard >= 0.30:
                            verdict = "EXTRACTION_AND_OCR_OVERLAP"
                        else:
                            verdict = "TEXTS_DIFFER; MANUAL_REVIEW"
                        row = {
                            "file": json_path.name,
                            "page": number,
                            "expected_script": script or "",
                            "parser_needs_ocr": needs_ocr,
                            "source_status": source_status,
                            "ocr_status": ocr_status,
                            "source_script_share": maybe_float(
                                source_metrics.get("expected_script_share")
                            ),
                            "ocr_script_share": maybe_float(
                                ocr_metrics.get("expected_script_share")
                            ),
                            "latin_letter_share": maybe_float(
                                source_metrics["latin_letter_share"]
                            ),
                            "private_use_count": source_metrics["private_use_count"],
                            "cid_count": source_metrics["cid_count"],
                            "non_alphanumeric_share": maybe_float(
                                source_metrics["non_alphanumeric_share"]
                            ),
                            "ocr_non_alphanumeric_share": maybe_float(
                                ocr_metrics["non_alphanumeric_share"]
                            ),
                            "source_letter_count": source_metrics["letter_count"],
                            "ocr_letter_count": ocr_metrics["letter_count"],
                            "ocr_confidence_mean": maybe_float(confidence),
                            "sequence_similarity": maybe_float(similarity),
                            "word_jaccard": maybe_float(jaccard),
                            "source_word_coverage": maybe_float(coverage),
                            "candidate_for_ocr": candidate,
                            "candidate_reason": "; ".join(reasons),
                            "machine_verdict": verdict,
                            "error": "",
                        }
                        page_rows.append(row)
                        if candidate:
                            candidate_rows.append({
                                key: row[key] for key in CANDIDATE_FIELDS
                            })
                            output_pages.append({
                                "page": number,
                                "text": ocr_text,
                                "original_text": text,
                                "needs_ocr": True,
                                "machine_metrics": row,
                            })
                    except Exception as exc:
                        error = f"{type(exc).__name__}: {exc}"
                        failures.append({
                            "dataset": "indian", "file": json_path.name,
                            "page": number, "error": error,
                        })
                        page_rows.append({
                            "file": json_path.name, "page": number,
                            "expected_script": script or "", "parser_needs_ocr": needs_ocr,
                            "source_status": "", "ocr_status": "", "error": error,
                        })
                    print(
                        f"  page {number}/{len(pages)} ({language}); "
                        f"verified {len(page_rows)} page(s) total",
                        flush=True,
                    )
                    atomic_csv(PAGE_REPORT, PAGE_FIELDS, page_rows)
                    atomic_csv(CANDIDATES, CANDIDATE_FIELDS, candidate_rows)
                    atomic_csv(HARD_BAD, [
                        "file", "page", "expected_script", "source_status",
                        "source_script_share", "private_use_count", "cid_count",
                        "non_alphanumeric_share", "hard_rule_flags", "parser_needs_ocr",
                    ], hard_bad_rows)
                    atomic_csv(FAILURES, FAILURE_FIELDS, failures)
            if output_pages:
                atomic_json(
                    PARSED_OCR / "indian" / json_path.name,
                    {"source": source, "machine_generated": True, "pages": output_pages},
                )
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            failures.append({
                "dataset": "indian", "file": json_path.name, "page": "",
                "error": error,
            })
            atomic_csv(FAILURES, FAILURE_FIELDS, failures)
            print(f"  FILE FAILURE: {error}", flush=True)

    cuad_files = sorted(CUAD_JSON.glob("*.json"))
    flagged: list[tuple[Path, dict[str, Any], str]] = []
    for json_path in cuad_files:
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            source = str(payload.get("source", ""))
            for page_info in payload.get("pages", []):
                if page_info.get("needs_ocr"):
                    flagged.append((json_path, page_info, source))
        except Exception as exc:
            failures.append({
                "dataset": "cuad", "file": json_path.name, "page": "",
                "error": f"{type(exc).__name__}: {exc}",
            })

    print(f"CUAD pages flagged for OCR: {len(flagged)}", flush=True)
    cuad_outputs: dict[Path, dict[str, Any]] = {}
    for index, (json_path, page_info, source) in enumerate(flagged, 1):
        print(f"[CUAD {index}/{len(flagged)}] {json_path.name} page {page_info.get('page')}", flush=True)
        try:
            pdf_path = resolve_pdf(source, ROOT / "data" / "raw" / "01_cuad")
            number = int(page_info.get("page", 0))
            with fitz.open(pdf_path) as document:
                if number < 1 or number > document.page_count:
                    raise IndexError(
                        f"page {number} outside PDF page range 1..{document.page_count}"
                    )
                ocr_text, confidence = ocr_page(document[number - 1], "eng")
            result = cuad_outputs.setdefault(
                json_path,
                {"source": source, "machine_generated": True, "pages": []},
            )
            result["pages"].append({
                "page": number,
                "text": ocr_text,
                "original_text": str(page_info.get("text", "")),
                "needs_ocr": True,
                "ocr_confidence_mean": maybe_float(confidence),
            })
            atomic_json(PARSED_OCR / "cuad" / json_path.name, result)
        except Exception as exc:
            failures.append({
                "dataset": "cuad", "file": json_path.name,
                "page": page_info.get("page", ""),
                "error": f"{type(exc).__name__}: {exc}",
            })
            print(f"  PAGE FAILURE: {type(exc).__name__}: {exc}", flush=True)
        atomic_csv(FAILURES, FAILURE_FIELDS, failures)

    print(
        f"Finished Indian pages={total_pages}, OCR candidates={len(candidate_rows)}, "
        f"hard-rule BAD={len(hard_bad_rows)}, CUAD flagged={len(flagged)}, "
        f"failures={len(failures)}.",
        flush=True,
    )
    print(f"Reports: {PAGE_REPORT.relative_to(ROOT)}, {CANDIDATES.relative_to(ROOT)}", flush=True)
    if failures:
        print(f"Failures logged: {FAILURES.relative_to(ROOT)}", flush=True)


if __name__ == "__main__":
    main()
