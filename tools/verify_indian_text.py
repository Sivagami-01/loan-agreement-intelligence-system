from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
PARSED_DIR = ROOT / "data" / "processed" / "parsed" / "indian"
PDF_DIR = ROOT / "data" / "raw" / "08_indian_bank_loans"
IMAGE_DIR = ROOT / "data" / "processed" / "review_images"
REPORT = ROOT / "data" / "processed" / "indian_text_report.md"
SCRIPT_RANGES = {
    "devanagari": (0x0900, 0x097F),
    "bengali": (0x0980, 0x09FF),
    "gurmukhi": (0x0A00, 0x0A7F),
    "malayalam": (0x0D00, 0x0D7F),
}
LANGUAGE_HINTS = {
    "hindi": "devanagari",
    "devanagari": "devanagari",
    "bengali": "bengali",
    "bangla": "bengali",
    "punjabi": "gurmukhi",
    "gurmukhi": "gurmukhi",
    "malayalam": "malayalam",
}
CURRENT_THRESHOLDS = {
    "bad_script_share": 0.12,
    "suspicious_script_share": 0.40,
    "symbol_share": 0.45,
}
PROPOSED_THRESHOLDS = {
    "bad_script_share": 0.10,
    "suspicious_script_share": 0.30,
    "symbol_share": 0.65,
}


def expected_script(name: str) -> str | None:
    lowered = name.casefold()
    for hint, script in LANGUAGE_HINTS.items():
        if hint in lowered:
            return script
    return None


def analyze(
    text: str,
    expected: str | None,
    thresholds: dict[str, float] | None = None,
) -> tuple[dict[str, float | int | None], str, list[str]]:
    thresholds = thresholds or CURRENT_THRESHOLDS
    letters = [char for char in text if char.isalpha()]
    counts = Counter()
    latin_letters = 0
    for char in letters:
        code = ord(char)
        if "LATIN" in unicodedata.name(char, ""):
            latin_letters += 1
        for script, (start, end) in SCRIPT_RANGES.items():
            if start <= code <= end:
                counts[script] += 1
                break
        else:
            counts["latin_or_other"] += 1

    denominator = max(1, len(letters))
    expected_share = counts.get(expected, 0) / denominator if expected else None
    latin_share = latin_letters / denominator
    private_use_count = sum(unicodedata.category(char) == "Co" for char in text)
    cid_count = len(re.findall(r"\(cid:\s*\d+\)", text, re.IGNORECASE))
    non_alphanumeric_share = sum(not char.isalnum() for char in text) / max(1, len(text))
    visible = [char for char in text if not char.isspace()]
    symbol_share = sum(
        not char.isalnum() and unicodedata.category(char)[0] not in {"M"}
        for char in visible
    ) / max(1, len(visible))
    replacement_count = text.count("\ufffd")
    symbol_run = bool(re.search(r"(?:[^\w\s]){8,}", text))
    flags = []
    if private_use_count:
        flags.append(f"private-use characters ({private_use_count})")
    if cid_count:
        flags.append(f"(cid:...) strings ({cid_count})")
    if symbol_share > thresholds["symbol_share"] and len(visible) >= 30:
        flags.append(f"high symbol ratio ({symbol_share:.0%})")
    if replacement_count:
        flags.append(f"replacement characters ({replacement_count})")
    if symbol_run:
        flags.append("long random-symbol run")

    metrics: dict[str, float | int | None] = {
        "expected_script_share": expected_share,
        "latin_letter_share": latin_share,
        "private_use_count": private_use_count,
        "cid_count": cid_count,
        "non_alphanumeric_share": non_alphanumeric_share,
        "symbol_share": symbol_share,
        "letter_count": len(letters),
    }
    if not text.strip() or len(letters) < 20 or cid_count:
        status = "BAD"
    elif (
        private_use_count
        or replacement_count
        or symbol_run
        or symbol_share > thresholds["symbol_share"] and len(visible) >= 30
        or expected_share is not None
        and expected_share < thresholds["bad_script_share"]
    ):
        status = "BAD"
    elif (
        expected_share is not None
        and expected_share < thresholds["suspicious_script_share"]
    ):
        status = "SUSPICIOUS"
    else:
        status = "GOOD"
    return metrics, status, flags


def render_page(source: Path, page_number: int, output: Path) -> None:
    with fitz.open(source) as document:
        if page_number < 1 or page_number > document.page_count:
            raise IndexError(f"page {page_number} is outside 1..{document.page_count}")
        pixmap = document[page_number - 1].get_pixmap(matrix=fitz.Matrix(1.7, 1.7), alpha=False)
        output.parent.mkdir(parents=True, exist_ok=True)
        pixmap.save(output)


def parse_thresholds(value: str | None) -> dict[str, float]:
    if value is None:
        return CURRENT_THRESHOLDS.copy()
    result = CURRENT_THRESHOLDS.copy()
    for item in value.split(","):
        key, separator, raw_number = item.partition("=")
        if not separator or key not in result:
            raise ValueError(f"Invalid threshold {item!r}. Expected bad_script_share, suspicious_script_share, or symbol_share.")
        result[key] = float(raw_number)
    if not (
        0 <= result["bad_script_share"]
        < result["suspicious_script_share"]
        <= 1
        and 0 <= result["symbol_share"] <= 1
    ):
        raise ValueError("Script shares must satisfy 0 <= bad < suspicious <= 1; symbol_share must be between 0 and 1.")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify Indian-language page text and render pages for review.")
    parser.add_argument(
        "--thresholds",
        help="Override thresholds as comma-separated key=value pairs; e.g. bad_script_share=0.10,suspicious_script_share=0.30,symbol_share=0.65. Writes indian_text_report_v2.md.",
    )
    args = parser.parse_args()
    thresholds = parse_thresholds(args.thresholds)
    report_path = (
        ROOT / "data" / "processed" / "indian_text_report_v2.md"
        if args.thresholds
        else REPORT
    )
    files = sorted(PARSED_DIR.glob("*.json"))
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Indian-language text verification",
        "",
        "Expected-script share is measured among alphabetic characters; Latin/other is reported separately. "
        "Pages are heuristic triage, not a translation-quality judgment.",
        "",
        "| Parsed file | Pages | Good | Suspicious | Bad | Pages to look at |",
        "|---|---:|---:|---:|---:|---|",
    ]
    failures: list[str] = []
    overall = Counter()
    lines.insert(
        3,
        f"Thresholds: bad expected-script share < {thresholds['bad_script_share']:.2f}; "
        f"suspicious < {thresholds['suspicious_script_share']:.2f}; "
        f"symbol ratio > {thresholds['symbol_share']:.2f}.",
    )
    for index, file_path in enumerate(files, 1):
        print(f"[{index}/{len(files)}] Checking {file_path.name}", flush=True)
        try:
            document = json.loads(file_path.read_text(encoding="utf-8"))
            pages = document.get("pages", [])
            expected = expected_script(file_path.name + " " + str(document.get("source", "")))
            stats = Counter()
            review_pages: list[str] = []
            pdf_source = Path(str(document.get("source", "")))
            if not pdf_source.is_absolute():
                pdf_source = ROOT / pdf_source
            if not pdf_source.exists():
                matching = list(PDF_DIR.glob(f"{file_path.stem}.pdf"))
                if matching:
                    pdf_source = matching[0]
            for page in pages:
                page_number = int(page.get("page", 0))
                text = str(page.get("text", ""))
                metrics, status, flags = analyze(text, expected, thresholds)
                stats[status] += 1
                overall[status] += 1
                if status != "GOOD":
                    review_pages.append(str(page_number))
                    if pdf_source.exists() and page_number:
                        image = IMAGE_DIR / f"{file_path.stem}_page_{page_number:04d}.png"
                        try:
                            render_page(pdf_source, page_number, image)
                        except Exception as exc:
                            failures.append(f"{file_path.name} page {page_number}: render failed: {exc}")
            if review_pages and not pdf_source.exists():
                failures.append(f"{file_path.name}: source PDF not found; images not rendered")
            lines.append(
                f"| `{file_path.name}` | {len(pages)} | {stats['GOOD']} | {stats['SUSPICIOUS']} | "
                f"{stats['BAD']} | {', '.join(review_pages) or '—'} |"
            )
            print(
                f"  {file_path.name}: pages={len(pages)} GOOD={stats['GOOD']} "
                f"SUSPICIOUS={stats['SUSPICIOUS']} BAD={stats['BAD']}",
                flush=True,
            )
        except Exception as exc:
            failures.append(f"{file_path.name}: {type(exc).__name__}: {exc}")
            lines.append(f"| `{file_path.name}` | — | — | — | — | processing failed |")
    lines.extend(["", f"**Totals:** {overall['GOOD']} good, {overall['SUSPICIOUS']} suspicious, {overall['BAD']} bad pages."])
    lines.append(f"**Review images:** `{IMAGE_DIR.relative_to(ROOT)}`.")
    if failures:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in failures)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Finished: {len(files)} files; {overall['GOOD']} GOOD, {overall['SUSPICIOUS']} SUSPICIOUS, {overall['BAD']} BAD pages.", flush=True)
    print(f"Report: {report_path.relative_to(ROOT)}", flush=True)
    if failures:
        print(f"Failures logged: {len(failures)}", flush=True)


if __name__ == "__main__":
    main()
