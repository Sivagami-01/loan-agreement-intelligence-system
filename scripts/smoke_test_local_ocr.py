from __future__ import annotations

import io
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import fitz
from PIL import Image
import pytesseract


ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "data" / "raw" / "08_indian_bank_loans"
TESSDATA = ROOT / "data" / "processed" / "tessdata"
LOG = ROOT / "data" / "processed" / "app_smoke_test.txt"
PDFS = {
    "eng": ("03_dbs_mitc.pdf", 1),
    "hin": ("13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi.pdf", 1),
    "ben": ("16_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Bengali_1_.pdf", 1),
    "pan": ("15_bajajhousingfinance_E-MITC_-_Retail_Secured_and_Unsecured_-_Punjabi_1_.pdf", 1),
    "mal": ("12_bajajhousingfinance_MITC_-_Retail_Secured_and_Unsecured_-_Malayalam.pdf", 1),
}


def tesseract_executable() -> str | None:
    found = shutil.which("tesseract")
    if found:
        return found
    candidate = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    return str(candidate) if candidate.is_file() else None


def main() -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    output = [f"OCR smoke test: {datetime.now().astimezone().isoformat(timespec='seconds')}"]
    executable = tesseract_executable()
    if not executable:
        output.append("Tesseract executable: MISSING")
        LOG.write_text("\n".join(output) + "\n", encoding="utf-8")
        print(output[-1])
        return
    pytesseract.pytesseract.tesseract_cmd = executable
    os.environ["TESSDATA_PREFIX"] = str(TESSDATA)
    output.append(f"Tesseract executable: {executable}")
    try:
        version = subprocess.run(
            [executable, "--version"], capture_output=True, text=True, timeout=20, check=True
        ).stdout.splitlines()[0]
        output.append(version)
        print(version)
    except Exception as exc:
        output.append(f"Version query failed: {type(exc).__name__}: {exc}")

    pack_failures = 0
    for index, (language, (filename, page_number)) in enumerate(PDFS.items(), 1):
        pdf_path = PDF_DIR / filename
        print(f"[{index}/{len(PDFS)}] OCR smoke test language={language}", flush=True)
        try:
            if not (TESSDATA / f"{language}.traineddata").is_file():
                raise FileNotFoundError(f"traineddata missing: {language}")
            with fitz.open(pdf_path) as document:
                pixmap = document[page_number - 1].get_pixmap(matrix=fitz.Matrix(300 / 72, 300 / 72), alpha=False)
            image = Image.open(io.BytesIO(pixmap.tobytes("png")))
            config = "--psm 6"
            data = pytesseract.image_to_data(
                image, lang=f"{language}+eng" if language != "eng" else "eng",
                config=config, output_type=pytesseract.Output.DICT,
            )
            text_count = sum(bool(token.strip()) for token in data.get("text", []))
            confidence_values = []
            for value in data.get("conf", []):
                try:
                    confidence = float(value)
                    if confidence >= 0:
                        confidence_values.append(confidence)
                except (TypeError, ValueError):
                    pass
            mean_confidence = (
                round(sum(confidence_values) / len(confidence_values), 2)
                if confidence_values else None
            )
            result = f"{language}: PASS; file={filename}; page={page_number}; token_count={text_count}; mean_confidence={mean_confidence}"
            output.append(result)
            print(f"  {result}")
        except Exception as exc:
            pack_failures += 1
            result = f"{language}: FAIL; file={filename}; page={page_number}; error={type(exc).__name__}: {exc}"
            output.append(result)
            print(f"  {result}", flush=True)
    output.append(f"OCR pack failures: {pack_failures}/{len(PDFS)}")
    LOG.write_text("\n".join(output) + "\n", encoding="utf-8")
    print(f"Wrote {LOG.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
