from __future__ import annotations

import csv
import re
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SHEETS = ROOT / "data" / "processed_v1" / "annotation_sheets"
ZIP_PATH = ROOT / "data" / "friend" / "01_loan_agreements" / "publicly_filed_contracts.zip"
TEXT_DIR = ROOT / "data" / "friend" / "01_loan_agreements" / "publicly_filed_contracts"
GUIDELINE = ROOT / "docs" / "labeling_guideline.md"
OUT_DIR = ROOT / "data" / "processed"
CONTEXT_REPORT = OUT_DIR / "labels" / "context_empty_decision.csv"
QUOTE_REPORT = OUT_DIR / "guideline_quote_check.csv"
csv.field_size_limit(20_000_000)

CONTEXT_FIELDS = [
    "doc_id", "field_name", "machine_candidate_value", "evidence_excerpt",
    "source_kind", "source_path", "exact_evidence_found", "context_before",
    "context_after", "human_value", "human_status", "risk_category",
    "severity", "rationale", "question", "answer",
]
QUOTE_FIELDS = [
    "doc_id", "quote_length", "verification", "raw_line", "source_kind",
    "source_path",
]


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames or [], list(reader)


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def normalize_member(value: str) -> str:
    return value.replace("\\", "/").strip("/").casefold()


def read_source(
    doc_id: str,
    zip_file: zipfile.ZipFile | None,
    zip_names: list[str],
) -> tuple[str, str, str]:
    wanted = normalize_member(doc_id)
    if zip_file is not None:
        exact = [name for name in zip_names if normalize_member(name) == wanted]
        if len(exact) == 1:
            return zip_file.read(exact[0]).decode("utf-8", errors="replace"), "zip", exact[0]
        suffix = [
            name for name in zip_names
            if normalize_member(name).endswith("/" + wanted)
        ]
        if len(suffix) == 1:
            return zip_file.read(suffix[0]).decode("utf-8", errors="replace"), "zip", suffix[0]
    folder_path = TEXT_DIR / Path(doc_id.replace("/", "\\"))
    if folder_path.is_file():
        return folder_path.read_text(encoding="utf-8", errors="replace"), "folder", str(folder_path)
    raise FileNotFoundError(f"source not found in ZIP or unpacked folder: {doc_id}")


def quote_examples() -> list[tuple[str, str]]:
    examples = []
    pattern = re.compile(r'^-\s*“(.*?)”\s+—\s+`([^`]+)`\s*$', re.MULTILINE)
    for match in pattern.finditer(GUIDELINE.read_text(encoding="utf-8")):
        examples.append((match.group(2), match.group(1)))
    return examples


def verify_quote(
    quote: str,
    text: str,
) -> tuple[str, int | str]:
    exact_at = text.find(quote)
    if exact_at >= 0:
        return "EXACT_RAW", text.count("\n", 0, exact_at) + 1
    pattern = re.compile(r"\s+".join(re.escape(part) for part in quote.split()))
    whitespace_match = pattern.search(text)
    if whitespace_match:
        return "WHITESPACE_ONLY", text.count("\n", 0, whitespace_match.start()) + 1
    return "NOT_FOUND", ""


def make_context_review() -> tuple[list[dict[str, Any]], list[str]]:
    _, sheet_rows = read_csv(SHEETS / "key_info_sheet.csv")
    rows = []
    failures = []
    cache: dict[str, tuple[str, str, str]] = {}
    with zipfile.ZipFile(ZIP_PATH) as zip_file:
        zip_names = [
            member for member in zip_file.namelist()
            if member.casefold().endswith(".txt")
        ]
        for index, row in enumerate(sheet_rows, 1):
            doc_id = row.get("doc_id", "")
            try:
                if doc_id not in cache:
                    cache[doc_id] = read_source(doc_id, zip_file, zip_names)
                text, source_kind, source_path = cache[doc_id]
                evidence = row.get("evidence_excerpt", "") or ""
                location = text.find(evidence) if evidence else -1
                before = text[max(0, location - 500):location] if location >= 0 else ""
                after = text[
                    location + len(evidence):location + len(evidence) + 500
                ] if location >= 0 else ""
                rows.append({
                    "doc_id": doc_id,
                    "field_name": row.get("field_name", ""),
                    "machine_candidate_value": row.get("machine_candidate_value", ""),
                    "evidence_excerpt": evidence,
                    "source_kind": source_kind,
                    "source_path": source_path,
                    "exact_evidence_found": bool(location >= 0),
                    "context_before": before,
                    "context_after": after,
                    "human_value": "",
                    "human_status": "",
                    "risk_category": "",
                    "severity": "",
                    "rationale": "",
                    "question": "",
                    "answer": "",
                })
            except Exception as exc:
                failures.append(f"row {index} ({doc_id}): {type(exc).__name__}: {exc}")
                rows.append({
                    "doc_id": doc_id,
                    "field_name": row.get("field_name", ""),
                    "machine_candidate_value": row.get("machine_candidate_value", ""),
                    "evidence_excerpt": row.get("evidence_excerpt", ""),
                    "source_kind": "",
                    "source_path": "",
                    "exact_evidence_found": False,
                    "human_value": "",
                    "human_status": "",
                    "risk_category": "",
                    "severity": "",
                    "rationale": "",
                    "question": "",
                    "answer": "",
                })
            if index % 100 == 0 or index == len(sheet_rows):
                print(f"[Context {index}/{len(sheet_rows)}] processed", flush=True)
    return rows, failures


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not ZIP_PATH.is_file():
        raise FileNotFoundError(f"Expected ZIP source is missing: {ZIP_PATH}")

    quote_rows = []
    quote_failures = []
    cache: dict[str, tuple[str, str, str]] = {}
    examples = quote_examples()
    with zipfile.ZipFile(ZIP_PATH) as zip_file:
        zip_names = [
            member for member in zip_file.namelist()
            if member.casefold().endswith(".txt")
        ]
        for index, (doc_id, quote) in enumerate(examples, 1):
            try:
                if doc_id not in cache:
                    cache[doc_id] = read_source(doc_id, zip_file, zip_names)
                text, source_kind, source_path = cache[doc_id]
                status, line = verify_quote(quote, text)
                quote_rows.append({
                    "doc_id": doc_id, "quote_length": len(quote),
                    "verification": status, "raw_line": line,
                    "source_kind": source_kind, "source_path": source_path,
                })
                if status != "EXACT_RAW":
                    quote_failures.append((doc_id, quote, status))
                print(
                    f"[Quote {index}/{len(examples)}] {doc_id}: "
                    f"{status}; length={len(quote)}; raw_line={line}",
                    flush=True,
                )
            except Exception as exc:
                quote_failures.append((doc_id, quote, f"{type(exc).__name__}: {exc}"))
                quote_rows.append({
                    "doc_id": doc_id, "quote_length": len(quote),
                    "verification": "SOURCE_ERROR", "raw_line": "",
                    "source_kind": "", "source_path": "",
                })
                print(f"[Quote {index}/{len(examples)}] SOURCE ERROR: {exc}", flush=True)

    write_csv(QUOTE_REPORT, QUOTE_FIELDS, quote_rows)
    print(
        f"Quote check: {len(examples)} examples; "
        f"{sum(row['verification'] == 'EXACT_RAW' for row in quote_rows)} exact; "
        f"{len(quote_failures)} need attention. Report: {QUOTE_REPORT.relative_to(ROOT)}",
        flush=True,
    )

    context_rows, context_failures = make_context_review()
    write_csv(CONTEXT_REPORT, CONTEXT_FIELDS, context_rows)
    empty_decisions = sum(
        not any(row.get(field) for field in (
            "human_value", "human_status", "risk_category", "severity",
            "rationale", "question", "answer",
        ))
        for row in context_rows
    )
    print(
        f"Context review: {len(context_rows)} rows; {empty_decisions} decisions empty; "
        f"{len(context_failures)} source failures. "
        f"Report: {CONTEXT_REPORT.relative_to(ROOT)}",
        flush=True,
    )
    for failure in [*quote_failures, *context_failures]:
        print(f"FAILURE: {failure}", flush=True)


if __name__ == "__main__":
    main()
