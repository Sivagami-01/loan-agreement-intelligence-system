from __future__ import annotations

import csv
import zipfile
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SHEET = ROOT / "data" / "processed_v1" / "annotation_sheets" / "key_info_sheet.csv"
ZIP_PATH = ROOT / "data" / "friend" / "01_loan_agreements" / "publicly_filed_contracts.zip"
TEXT_DIR = ROOT / "data" / "friend" / "01_loan_agreements" / "publicly_filed_contracts"
OUTPUT = ROOT / "data" / "processed" / "unresolved_docs.csv"
REQUESTS = ROOT / "data" / "processed" / "files_to_request.txt"
csv.field_size_limit(20_000_000)


def normalize(value: str) -> str:
    return value.replace("\\", "/").strip("/").casefold()


def read_sheet() -> tuple[list[str], list[dict[str, str]], list[str]]:
    with SHEET.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
        doc_ids = list(dict.fromkeys(row.get("doc_id", "").strip() for row in rows if row.get("doc_id")))
    return reader.fieldnames or [], rows, doc_ids


def make_index(names: list[str]) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    exact: dict[str, list[str]] = defaultdict(list)
    basenames: dict[str, list[str]] = defaultdict(list)
    for name in names:
        cleaned = normalize(name)
        exact[cleaned].append(name)
        basenames[cleaned.rsplit("/", 1)[-1]].append(name)
    return exact, basenames


def evidence_for(rows: list[dict[str, str]], doc_id: str) -> list[str]:
    return list(
        dict.fromkeys(
            (row.get("evidence_excerpt") or "").strip()
            for row in rows
            if row.get("doc_id", "").strip().replace("\\", "/") == doc_id.replace("\\", "/")
            and (row.get("evidence_excerpt") or "").strip()
        )
    )


def resolve_from_index(
    doc_id: str,
    exact: dict[str, list[str]],
    basename_index: dict[str, list[str]],
    read_text,
    evidence: list[str],
) -> tuple[str, str, str] | None:
    normalized_id = normalize(doc_id)
    exact_matches = exact.get(normalized_id, [])
    if len(exact_matches) == 1:
        return exact_matches[0], "exact path (case-insensitive)", "exact path"
    if len(exact_matches) > 1:
        return None

    suffix_matches = sorted(
        {
            entry
            for normalized_name, entries in exact.items()
            if normalized_name.endswith("/" + normalized_id)
            for entry in entries
        }
    )
    if len(suffix_matches) == 1:
        return suffix_matches[0], "unique path suffix (prefix ignored)", "prefix/suffix match"
    if len(suffix_matches) > 1:
        return None

    basename = normalized_id.rsplit("/", 1)[-1]
    candidates = basename_index.get(basename, [])
    if len(candidates) == 1:
        candidate = candidates[0]
        try:
            text = read_text(candidate)
        except Exception:
            return None
        if any(quote in text for quote in evidence):
            return candidate, "unique basename; exact machine-evidence quote verified", "basename match, verify automatically"
    return None


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    headers, sheet_rows, doc_ids = read_sheet()
    first_30 = set(doc_ids[:30])
    errors: list[str] = []
    zip_exact: dict[str, list[str]] = {}
    zip_basenames: dict[str, list[str]] = {}
    archive = None
    if ZIP_PATH.is_file():
        try:
            archive = zipfile.ZipFile(ZIP_PATH)
            zip_exact, zip_basenames = make_index(
                [name for name in archive.namelist() if name.casefold().endswith(".txt")]
            )
        except (OSError, zipfile.BadZipFile) as exc:
            errors.append(f"ZIP index failed: {type(exc).__name__}: {exc}")
            print(errors[-1], flush=True)

    folder_names = []
    if TEXT_DIR.is_dir():
        folder_names = [path.relative_to(TEXT_DIR).as_posix() for path in TEXT_DIR.rglob("*.txt")]
    folder_exact, folder_basenames = make_index(folder_names)

    def zip_read(name: str) -> str:
        if archive is None:
            raise FileNotFoundError("source ZIP is unavailable")
        return archive.read(name).decode("utf-8", errors="replace")

    def folder_read(name: str) -> str:
        return (TEXT_DIR / Path(name)).read_text(encoding="utf-8", errors="replace")

    result_rows = []
    resolved_count = 0
    for index, doc_id in enumerate(doc_ids, 1):
        print(f"[{index}/{len(doc_ids)}] Resolving {doc_id}", flush=True)
        evidence = evidence_for(sheet_rows, doc_id)
        match = None
        source = ""
        if archive is not None:
            try:
                match = resolve_from_index(doc_id, zip_exact, zip_basenames, zip_read, evidence)
                if match:
                    source = "zip"
            except Exception as exc:
                errors.append(f"{doc_id}: ZIP read failed: {type(exc).__name__}: {exc}")
                print(errors[-1], flush=True)
        if match is None:
            try:
                match = resolve_from_index(doc_id, folder_exact, folder_basenames, folder_read, evidence)
                if match:
                    source = "folder"
            except Exception as exc:
                errors.append(f"{doc_id}: folder read failed: {type(exc).__name__}: {exc}")
                print(errors[-1], flush=True)

        if match:
            _, how_matched, _ = match
            reason = ""
            resolved_count += 1
        else:
            how_matched = ""
            reason = (
                "basename was ambiguous or evidence quote was not found"
                if doc_id.rsplit("/", 1)[-1].casefold() in zip_basenames
                or doc_id.rsplit("/", 1)[-1].casefold() in folder_basenames
                else "no matching path in ZIP or unpacked folder"
            )
        result_rows.append(
            {
                "doc_id": doc_id,
                "in_first_30": "yes" if doc_id in first_30 else "no",
                "source": source,
                "how_matched": how_matched,
                "reason": reason,
            }
        )

    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=["doc_id", "in_first_30", "source", "how_matched", "reason"],
        )
        writer.writeheader()
        writer.writerows(result_rows)
    unresolved = [row for row in result_rows if not row["source"]]
    if unresolved:
        REQUESTS.write_text(
            "Documents not found in the ZIP or unpacked folder:\n"
            + "\n".join(row["doc_id"] for row in unresolved)
            + "\n",
            encoding="utf-8",
        )
    first_resolved = sum(row["in_first_30"] == "yes" and bool(row["source"]) for row in result_rows)
    print(
        f"Resolved {resolved_count}/{len(doc_ids)} total; "
        f"{first_resolved}/30 first-30 documents; unresolved {len(unresolved)}.",
        flush=True,
    )
    if errors:
        print(f"Source-resolution failures: {len(errors)} (logged above).", flush=True)
    if archive is not None:
        archive.close()


if __name__ == "__main__":
    main()
