from __future__ import annotations

import csv
import zipfile
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "processed_v1" / "annotation_sheets"
LABELS = ROOT / "data" / "processed" / "labels"
REPORT = LABELS / "progress.md"
TEXT_DIR = ROOT / "data" / "friend" / "01_loan_agreements" / "publicly_filed_contracts"
ZIP_PATH = ROOT / "data" / "friend" / "01_loan_agreements" / "publicly_filed_contracts.zip"
csv.field_size_limit(20_000_000)


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames or [], list(reader)


def count_status(input_name: str, output_name: str, key: tuple[str, ...], complete, partial) -> tuple[int, int, int]:
    _, source_rows = read_csv(SOURCE / input_name)
    _, saved_rows = read_csv(LABELS / output_name)
    saved = {tuple(row.get(col, "") for col in key): row for row in saved_rows}
    occurrence: dict[str, int] = {}
    source_keys = []
    for row in source_rows:
        values = []
        for column in key:
            if column == "qa_row" and not row.get(column):
                doc_id = row.get("doc_id", "")
                values.append(str(occurrence.get(doc_id, 0)))
                occurrence[doc_id] = occurrence.get(doc_id, 0) + 1
            else:
                values.append(row.get(column, ""))
        source_keys.append(tuple(values))
    complete_count = sum(1 for row_key in source_keys if complete(saved.get(row_key, {})))
    partial_count = sum(
        1 for row_key in source_keys
        if not complete(saved.get(row_key, {})) and partial(saved.get(row_key, {}))
    )
    return len(source_rows), complete_count, partial_count


def document_source_counts() -> tuple[int, int, int]:
    _, rows = read_csv(SOURCE / "key_info_sheet.csv")
    doc_ids = list(dict.fromkeys(row.get("doc_id", "").replace("\\", "/").lstrip("/") for row in rows))
    evidence = {
        doc_id: [
            (row.get("evidence_excerpt") or "").strip()
            for row in rows
            if row.get("doc_id", "").replace("\\", "/").lstrip("/") == doc_id
            and (row.get("evidence_excerpt") or "").strip()
        ]
        for doc_id in doc_ids
    }
    zip_members: dict[str, list[str]] = {}
    if ZIP_PATH.is_file():
        try:
            with zipfile.ZipFile(ZIP_PATH) as archive:
                for name in archive.namelist():
                    if name.lower().endswith(".txt"):
                        zip_members.setdefault(name.replace("\\", "/").strip("/").casefold(), []).append(name)
        except (OSError, zipfile.BadZipFile) as exc:
            print(f"WARNING: cannot inspect source ZIP: {type(exc).__name__}: {exc}")
    folder_members: dict[str, list[str]] = {}
    if TEXT_DIR.is_dir():
        for path in TEXT_DIR.rglob("*.txt"):
            relative = path.relative_to(TEXT_DIR).as_posix()
            folder_members.setdefault(relative.casefold(), []).append(relative)

    zip_count = folder_count = missing = 0
    for doc_id in doc_ids:
        normalized = doc_id.casefold()

        def find(index: dict[str, list[str]]) -> tuple[str | None, str]:
            direct = index.get(normalized, [])
            if len(direct) == 1:
                return direct[0], "exact path"
            suffix = sorted({
                entry for name, entries in index.items()
                if name.endswith("/" + normalized) for entry in entries
            })
            if len(suffix) == 1:
                return suffix[0], "path suffix"
            basename_matches = [
                entry for name, entries in index.items()
                if name.rsplit("/", 1)[-1] == normalized.rsplit("/", 1)[-1]
                for entry in entries
            ]
            if len(basename_matches) == 1:
                return basename_matches[0], "basename"
            return None, "no unique path"

        zip_entry, zip_match = find(zip_members)
        if zip_entry:
            if zip_match != "basename":
                zip_count += 1
                continue
            try:
                with zipfile.ZipFile(ZIP_PATH) as archive:
                    text = archive.read(zip_entry).decode("utf-8", errors="replace")
                if any(quote in text for quote in evidence[doc_id]):
                    zip_count += 1
                    continue
            except (OSError, KeyError, zipfile.BadZipFile) as exc:
                print(f"WARNING: ZIP basename evidence check failed for {doc_id}: {exc}")

        folder_entry, folder_match = find(folder_members)
        if folder_entry:
            if folder_match != "basename":
                folder_count += 1
                continue
            try:
                text = (TEXT_DIR / Path(folder_entry)).read_text(encoding="utf-8", errors="replace")
                if any(quote in text for quote in evidence[doc_id]):
                    folder_count += 1
                    continue
            except OSError as exc:
                print(f"WARNING: folder basename evidence check failed for {doc_id}: {exc}")
        missing += 1
    return zip_count, folder_count, missing


def main() -> None:
    LABELS.mkdir(parents=True, exist_ok=True)
    fields = count_status(
        "key_info_sheet.csv", "key_info_labeled.csv", ("doc_id", "field_name"),
        lambda r: bool(r.get("human_status", "").strip()),
        lambda r: any(r.get(k, "").strip() for k in ("human_status", "human_value", "notes")),
    )
    clauses = count_status(
        "risk_clause_sheet.csv", "risk_labeled.csv", ("doc_id", "clause_id"),
        lambda r: all(r.get(k, "").strip() for k in ("risk_category", "severity", "rationale")),
        lambda r: any(r.get(k, "").strip() for k in ("risk_category", "severity", "rationale")),
    )
    qa = count_status(
        "qa_sheet.csv", "qa_labeled.csv", ("doc_id", "qa_row"),
        lambda r: all(r.get(k, "").strip() for k in ("question", "answer", "supporting_text")),
        lambda r: any(r.get(k, "").strip() for k in ("question", "answer", "supporting_text")),
    )
    source_zip, source_unpacked, source_missing = document_source_counts()
    source_total = source_zip + source_unpacked + source_missing
    rows = [
        ("Key fields", fields),
        ("Risk clauses", clauses),
        ("Q&A rows", qa),
    ]
    lines = [
        "# Labeling progress",
        "",
        f"Updated: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        "",
        f"Document text sources (ZIP preferred): {source_zip}/{source_total} in ZIP, "
        f"{source_unpacked}/{source_total} unpacked fallback, {source_missing} unavailable.",
        "",
        "| Tab | Total | Complete | Partial | Remaining |",
        "|---|---:|---:|---:|---:|",
    ]
    for label, (total, complete, partial) in rows:
        lines.append(f"| {label} | {total} | {complete} | {partial} | {total - complete} |")
        print(f"{label}: {complete}/{total} complete; {partial} partial; {total - complete} remain.")
    print(
        f"Key-info document text (ZIP preferred): {source_zip}/{source_total} in ZIP, "
        f"{source_unpacked}/{source_total} unpacked fallback, {source_missing} unavailable."
    )
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Progress report written: {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
