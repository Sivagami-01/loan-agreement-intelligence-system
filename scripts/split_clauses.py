from __future__ import annotations

import csv
import hashlib
import json
import re
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SHEET = ROOT / "data" / "processed_v1" / "annotation_sheets" / "key_info_sheet.csv"
ZIP_PATH = ROOT / "data" / "friend" / "01_loan_agreements" / "publicly_filed_contracts.zip"
TEXT_DIR = ROOT / "data" / "friend" / "01_loan_agreements" / "publicly_filed_contracts"
OUTPUT = ROOT / "data" / "processed" / "parsed" / "annotation60"
FAILURES = OUTPUT / "failures.csv"
MAX_CLAUSE_CHARS = 5000
csv.field_size_limit(20_000_000)

HEADING = re.compile(
    r"(?im)^[ \t]*(?:"
    r"(?:ARTICLE|SECTION|SCHEDULE|EXHIBIT)\s+[A-Z0-9IVXLCDM]+[^\r\n]{0,150}"
    r"|\d+(?:\.\d+)*(?:\([A-Za-z0-9]+\))*[.)]?\s+[A-Z][^\r\n]{1,150}"
    r"|[IVXLCDM]{1,8}[.)]\s+[A-Z][^\r\n]{1,150}"
    r")[ \t]*$"
)


def read_sheet() -> list[dict[str, str]]:
    with SHEET.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    documents: dict[str, dict[str, str]] = {}
    for row in rows:
        doc_id = row.get("doc_id", "").strip()
        if doc_id:
            documents.setdefault(doc_id, row)
    return list(documents.values())


def normalize(value: str) -> str:
    return value.replace("\\", "/").strip("/").casefold()


def load_text(
    doc_id: str,
    archive: zipfile.ZipFile | None,
    zip_names: list[str],
) -> tuple[str, str, str]:
    wanted = normalize(doc_id)
    if archive is not None:
        exact = [name for name in zip_names if normalize(name) == wanted]
        if len(exact) == 1:
            return archive.read(exact[0]).decode("utf-8", errors="replace"), "zip", exact[0]
        suffix = [
            name for name in zip_names
            if normalize(name).endswith("/" + wanted)
        ]
        if len(suffix) == 1:
            return archive.read(suffix[0]).decode("utf-8", errors="replace"), "zip", suffix[0]
        basename = wanted.rsplit("/", 1)[-1]
        candidates = [
            name for name in zip_names
            if normalize(name).rsplit("/", 1)[-1] == basename
        ]
        if len(candidates) == 1:
            text = archive.read(candidates[0]).decode("utf-8", errors="replace")
            with SHEET.open(encoding="utf-8-sig", newline="") as stream:
                evidence = [
                    (row.get("evidence_excerpt") or "").strip()
                    for row in csv.DictReader(stream)
                    if normalize(row.get("doc_id", "")) == wanted
                    and (row.get("evidence_excerpt") or "").strip()
                ]
            if any(quote in text for quote in evidence):
                return text, "zip", candidates[0]

    folder_path = TEXT_DIR / Path(doc_id.replace("/", "\\"))
    if folder_path.is_file():
        return folder_path.read_text(encoding="utf-8", errors="replace"), "folder", str(folder_path)
    raise FileNotFoundError(f"document not found in ZIP or unpacked folder: {doc_id}")


def trimmed_span(text: str, start: int, end: int) -> tuple[int, int] | None:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return (start, end) if start < end else None


def paragraph_spans(text: str, start: int, end: int) -> list[tuple[int, int]]:
    spans = []
    cursor = start
    for match in re.finditer(r"\n[ \t]*\n+", text[start:end]):
        boundary = start + match.start()
        span = trimmed_span(text, cursor, boundary)
        if span:
            spans.append(span)
        cursor = start + match.end()
    span = trimmed_span(text, cursor, end)
    if span:
        spans.append(span)
    return spans


def split_long_span(text: str, start: int, end: int) -> list[tuple[int, int]]:
    paragraphs = paragraph_spans(text, start, end)
    if not paragraphs:
        return []
    chunks: list[tuple[int, int]] = []
    chunk_start = chunk_end = -1
    for para_start, para_end in paragraphs:
        if para_end - para_start > MAX_CLAUSE_CHARS:
            if chunk_start >= 0 and chunk_end > chunk_start:
                chunks.append((chunk_start, chunk_end))
            chunk_start = chunk_end = -1
            cursor = para_start
            while cursor < para_end:
                limit = min(para_end, cursor + MAX_CLAUSE_CHARS)
                if limit < para_end:
                    cut = text.rfind(" ", cursor, limit)
                    if cut > cursor:
                        limit = cut
                span = trimmed_span(text, cursor, limit)
                if span:
                    chunks.append(span)
                cursor = max(limit, cursor + 1)
            continue
        if chunk_start < 0:
            chunk_start, chunk_end = para_start, para_end
        elif para_end - chunk_start <= MAX_CLAUSE_CHARS:
            chunk_end = para_end
        else:
            chunks.append((chunk_start, chunk_end))
            chunk_start, chunk_end = para_start, para_end
    if chunk_start >= 0 and chunk_end > chunk_start:
        chunks.append((chunk_start, chunk_end))
    return chunks


def make_spans(text: str) -> list[tuple[int, int]]:
    matches = list(HEADING.finditer(text))
    boundaries = sorted(set([0] + [match.start() for match in matches]))
    spans: list[tuple[int, int]] = []
    for index, start in enumerate(boundaries):
        end = boundaries[index + 1] if index + 1 < len(boundaries) else len(text)
        segment = trimmed_span(text, start, end)
        if not segment:
            continue
        if segment[1] - segment[0] > MAX_CLAUSE_CHARS:
            spans.extend(split_long_span(text, *segment))
        else:
            spans.append(segment)
    if not spans:
        for start, end in paragraph_spans(text, 0, len(text)):
            spans.extend(
                split_long_span(text, start, end)
                if end - start > MAX_CLAUSE_CHARS
                else [(start, end)]
            )
    return spans


def safe_stem(doc_id: str) -> str:
    basename = Path(doc_id.replace("\\", "/")).stem
    clean = re.sub(r"[^A-Za-z0-9._-]+", "_", basename)[:90] or "document"
    digest = hashlib.sha256(doc_id.encode("utf-8")).hexdigest()[:10]
    return f"{clean}_{digest}.json"


def main() -> None:
    documents = read_sheet()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    failures: list[dict[str, str]] = []
    archive = None
    if ZIP_PATH.is_file():
        try:
            archive = zipfile.ZipFile(ZIP_PATH)
        except (OSError, zipfile.BadZipFile) as exc:
            print(f"ZIP unavailable, will use unpacked fallback: {type(exc).__name__}: {exc}")
    zip_names = [
        name for name in archive.namelist()
        if name.casefold().endswith(".txt")
    ] if archive is not None else []
    try:
        for index, row in enumerate(documents, 1):
            doc_id = row["doc_id"].strip()
            print(f"[{index}/{len(documents)}] Splitting {doc_id}", flush=True)
            try:
                text, source_kind, source_path = load_text(doc_id, archive, zip_names)
                spans = make_spans(text)
                clauses: list[dict[str, Any]] = []
                for clause_index, (start, end) in enumerate(spans, 1):
                    clause_text = text[start:end]
                    heading = next(
                        (line.strip() for line in clause_text.splitlines() if line.strip()),
                        "",
                    )
                    clauses.append({
                        "clause_id": f"C{clause_index:04d}",
                        "heading": heading[:200],
                        "text": clause_text,
                        "start_char": start,
                        "end_char": end,
                        "char_count": len(clause_text),
                        "citation": f"{doc_id}#C{clause_index:04d}",
                    })
                destination = OUTPUT / safe_stem(doc_id)
                temporary = destination.with_suffix(".json.tmp")
                temporary.write_text(
                    json.dumps({
                        "doc_id": doc_id,
                        "source_kind": source_kind,
                        "source_path": source_path,
                        "machine_generated": True,
                        "segmentation": "heading/paragraph heuristic; not human reviewed",
                        "clauses": clauses,
                    }, ensure_ascii=False),
                    encoding="utf-8",
                )
                temporary.replace(destination)
                print(
                    f"  source={source_kind}; clauses={len(clauses)}; "
                    f"output={destination.name}",
                    flush=True,
                )
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                failures.append({"doc_id": doc_id, "error": error})
                print(f"  FAILURE: {error}", flush=True)
    finally:
        if archive is not None:
            archive.close()

    with FAILURES.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["doc_id", "error"])
        writer.writeheader()
        writer.writerows(failures)
    print(
        f"Finished: {len(documents) - len(failures)}/{len(documents)} documents; "
        f"failures={len(failures)}; output={OUTPUT.relative_to(ROOT)}",
        flush=True,
    )


if __name__ == "__main__":
    main()
