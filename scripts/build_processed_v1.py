from __future__ import annotations

import csv
import bisect
import hashlib
import json
import math
import random
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(r"C:\dataset_loan")
LOAN_DIR = ROOT / "01_loan_agreements-20261110T071036Z-1-001" / "01_loan_agreements"
ANNOTATION_DIR = ROOT / "04_annotated_data-20261110T071045Z-1-001" / "04_annotated_data"
CUAD_DIR = ROOT / "02_cuad-20261110T071043Z-1-001" / "02_cuad"
OUTPUT = ROOT / "processed_v1"
SHEETS = OUTPUT / "annotation_sheets"
ZIP_PATH = LOAN_DIR / "publicly_filed_contracts.zip"
INVENTORY_PATH = ANNOTATION_DIR / "loan_agreement_candidate_inventory.csv"
JSONL_PATH = ANNOTATION_DIR / "provisional_machine_extraction_v1.jsonl"

ERRORS: list[str] = []
COUNTS: dict[str, int] = {}
MANIFEST: list[dict[str, str]] = []
CLEAN: list[dict[str, str]] = []
GOLD_DOCS: set[str] = set()
SELECTED_DOCS: list[dict[str, str]] = []
CONTROL: dict[str, Any] = {}
BREAKPOINTS: dict[str, Any] = {}
EXTRACTION: dict[str, dict[str, Any]] = {}
REVIEW_ROWS: list[dict[str, str]] = []
GOLD_EXTRA: list[dict[str, str]] = []
PREVIOUS_CLEAN_IDS: set[str] = set()
LEGACY_CLEAN_IDS: set[str] = set()
ANNOTATION_DUPLICATES_REMOVED = 0
DEDUPLICATE_DOCS_ADDED_BACK = 0

CANONICAL_ALIASES = {
    "repayment": "repayment_terms",
    "default": "events_of_default",
    "collateral_or_security": "collateral_security",
    "maturity_or_termination_date": "maturity_termination_date",
}

SHEET_FIELDS = [
    "document_title",
    "agreement_date",
    "borrowers",
    "lenders",
    "agents",
    "loan_or_commitment_amount",
    "interest_rate",
    "repayment_terms",
    "maturity_termination_date",
    "fees",
    "late_payment_or_default_interest",
    "prepayment_terms",
    "collateral_security",
    "guarantees",
    "events_of_default",
    "governing_law",
]

EXTRACTION_ALIASES = {
    "document_title": ["document_title", "title"],
    "agreement_date": ["agreement_date", "date"],
    "borrowers": ["borrowers", "borrower"],
    "lenders": ["lenders", "lender"],
    "agents": ["agents", "agent", "administrative_agent"],
    "loan_or_commitment_amount": [
        "loan_or_commitment_amount",
        "loan_amount",
        "commitment_amount",
        "principal_amount",
    ],
    "interest_rate": ["interest_rate"],
    "repayment_terms": ["repayment_terms", "repayment"],
    "maturity_termination_date": [
        "maturity_termination_date",
        "maturity_or_termination_date",
        "maturity_date",
        "termination_date",
    ],
    "fees": ["fees"],
    "late_payment_or_default_interest": [
        "late_payment_or_default_interest",
        "default_interest",
    ],
    "prepayment_terms": ["prepayment_terms", "prepayment"],
    "collateral_security": ["collateral_security", "collateral_or_security"],
    "guarantees": ["guarantees", "guarantee"],
    "events_of_default": ["events_of_default", "default"],
    "governing_law": ["governing_law"],
}

ENGLISH_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "in", "is", "it", "of", "on", "or", "that", "the", "this", "to",
    "under", "with", "will", "shall", "may", "any", "such", "each",
}
NON_ENGLISH_WORDS = {
    "de", "la", "el", "los", "las", "que", "und", "der", "die",
    "das", "et", "le", "les", "des", "du", "une", "un", "por",
    "para", "con", "del", "en", "il", "che", "di", "della",
}


def log_error(step: str, exc: BaseException) -> None:
    message = f"{step}: {type(exc).__name__}: {exc}"
    ERRORS.append(message)
    print(f"ERROR {message}", file=sys.stderr, flush=True)


def run_step(name: str, function: Any) -> None:
    try:
        function()
    except Exception as exc:
        log_error(name, exc)


def clip(value: Any, limit: int = 100) -> str:
    if value is None:
        text = ""
    elif isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    else:
        text = str(value)
    text = text.replace("\r", " ").replace("\n", " ")
    return text if len(text) <= limit else text[: limit - 3] + "..."


def csv_encoding(path: Path) -> str:
    try:
        with path.open("r", encoding="utf-8-sig", errors="strict") as stream:
            stream.read(4096)
        return "utf-8-sig"
    except UnicodeDecodeError:
        return "cp1252"


def iter_csv(path: Path) -> Iterable[dict[str, str]]:
    encoding = csv_encoding(path)
    with path.open("r", encoding=encoding, errors="replace", newline="") as stream:
        yield from csv.DictReader(stream)


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})
            count += 1
    return count


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as stream:
        return json.load(stream)


def walk_schema(value: Any, path: str, fields: dict[str, dict[str, str]]) -> None:
    if isinstance(value, list):
        for item in value:
            walk_schema(item, path, fields)
        return
    if isinstance(value, dict):
        for key, child in value.items():
            dynamic_key = len(value) > 100 or str(key).isdigit()
            segment = "<key>" if dynamic_key else str(key)
            field_path = f"{path}.{segment}" if path else segment
            detail = fields.setdefault(
                field_path,
                {"types": "", "example": ""},
            )
            type_name = type(child).__name__
            types = set(filter(None, detail["types"].split(", ")))
            types.add(type_name)
            detail["types"] = ", ".join(sorted(types))
            if not detail["example"] and child is not None:
                detail["example"] = clip(child)
            if isinstance(child, dict):
                walk_schema(child, field_path, fields)
            elif isinstance(child, list) and child:
                item_path = f"{field_path}[]"
                item_detail = fields.setdefault(item_path, {"types": "", "example": ""})
                for item in child:
                    item_type = type(item).__name__
                    item_types = set(filter(None, item_detail["types"].split(", ")))
                    item_types.add(item_type)
                    item_detail["types"] = ", ".join(sorted(item_types))
                    if not item_detail["example"] and item is not None:
                        item_detail["example"] = clip(item)
                    if isinstance(item, (dict, list)):
                        walk_schema(item, item_path, fields)


def schema_report() -> None:
    roots = [
        ("01_loan_agreements", LOAN_DIR),
        ("02_cuad", CUAD_DIR),
        ("04_annotated_data", ANNOTATION_DIR),
    ]
    lines = [
        "# Input data schema",
        "",
        "Schema inventory of the supplied 01, 02 (contextual CUAD), and 04 data folders. "
        "Examples are clipped to at most 100 characters. Row counts exclude CSV headers.",
        "",
    ]
    csv_paths: list[Path] = []
    json_paths: list[Path] = []
    jsonl_paths: list[Path] = []
    zip_paths: list[Path] = []
    txt_counts: dict[str, int] = {}
    for label, root in roots:
        files = list(root.rglob("*"))
        csv_paths.extend(p for p in files if p.is_file() and (p.suffix.lower() == ".csv" or p.suffix.lower() == ".bak"))
        json_paths.extend(p for p in files if p.is_file() and p.suffix.lower() == ".json")
        jsonl_paths.extend(p for p in files if p.is_file() and p.suffix.lower() == ".jsonl")
        zip_paths.extend(p for p in files if p.is_file() and p.suffix.lower() == ".zip")
        txt_counts[label] = sum(1 for p in files if p.is_file() and p.suffix.lower() == ".txt")

    lines.extend(["## File type inventory", ""])
    lines.append(f"- CSV and CSV-formatted backup files: {len(csv_paths)}")
    lines.append(f"- JSON files: {len(json_paths)}")
    lines.append(f"- JSONL files: {len(jsonl_paths)}")
    lines.append(f"- ZIP archives: {len(zip_paths)}")
    for label, count in txt_counts.items():
        lines.append(f"- `.txt` files in {label}: {count}")
    lines.extend(["", "## CSV and backup files", ""])

    csv_row_counts: dict[str, int] = {}
    for path in sorted(csv_paths):
        header: list[str] = []
        samples: dict[str, str] = {}
        row_count = 0
        encoding = csv_encoding(path)
        with path.open("r", encoding=encoding, errors="replace", newline="") as stream:
            reader = csv.DictReader(stream)
            header = reader.fieldnames or []
            for row in reader:
                row_count += 1
                for name in header:
                    if name not in samples and row.get(name, ""):
                        samples[name] = clip(row[name])
        csv_row_counts[path.name] = row_count
        lines.append(f"### `{path.relative_to(ROOT)}`")
        lines.append(f"- Data rows: {row_count}; columns: {len(header)}; detected text encoding: {encoding}")
        if header:
            lines.append("| Column | Example (max 100 chars) |")
            lines.append("|---|---|")
            for name in header:
                lines.append(f"| `{name}` | `{samples.get(name, '')}` |")
        else:
            lines.append("- No header row was found.")
        lines.append("")

    classification_rows = csv_row_counts.get(
        "loan_agreement_candidate_inventory.csv", 0
    )
    lines.insert(
        lines.index("## CSV and backup files") + 1,
        f"- **Large classification table:** `loan_agreement_candidate_inventory.csv` "
        f"({classification_rows:,} rows; `review_status` carries document classification).",
    )
    lines.extend(["## JSON files", ""])
    for path in sorted(json_paths):
        value = load_json(path)
        fields: dict[str, dict[str, str]] = {}
        if isinstance(value, dict):
            walk_schema(value, "", fields)
            row_count = len(value)
            root_desc = f"Top-level object with {row_count} keys"
            example_key = next(iter(value), "")
            lines.append(f"### `{path.relative_to(ROOT)}`")
            lines.append(f"- {root_desc}; example top-level key: `{clip(example_key)}`")
        elif isinstance(value, list):
            row_count = len(value)
            for item in value:
                walk_schema(item, "[]", fields)
            lines.append(f"### `{path.relative_to(ROOT)}`")
            lines.append(f"- Top-level array with {row_count} items")
        else:
            lines.append(f"### `{path.relative_to(ROOT)}`")
            lines.append(f"- Top-level value type: `{type(value).__name__}`")
        lines.append("| Key / nested field | Type(s) | Example (max 100 chars) |")
        lines.append("|---|---|---|")
        for name, detail in sorted(fields.items()):
            lines.append(f"| `{name}` | `{detail['types']}` | `{detail['example']}` |")
        lines.append("")

    lines.extend(["## JSONL files", ""])
    for path in sorted(jsonl_paths):
        count = 0
        fields: dict[str, dict[str, str]] = {}
        with path.open("r", encoding="utf-8-sig", errors="replace") as stream:
            for raw in stream:
                if not raw.strip():
                    continue
                count += 1
                if count == 1:
                    walk_schema(json.loads(raw), "", fields)
                if count % 500 == 0:
                    print(f"Schema: {count} JSONL records in {path.name}", flush=True)
        lines.append(f"### `{path.relative_to(ROOT)}`")
        lines.append(f"- Records: {count}")
        lines.append("| Key / nested field | Type(s) | Example (max 100 chars) |")
        lines.append("|---|---|---|")
        for name, detail in sorted(fields.items()):
            lines.append(f"| `{name}` | `{detail['types']}` | `{detail['example']}` |")
        lines.append("")

    lines.extend(["## ZIP archives", ""])
    for path in sorted(zip_paths):
        with zipfile.ZipFile(path) as archive:
            members = [info for info in archive.infolist() if not info.is_dir()]
            first = next((item for item in members if item.filename.lower().endswith(".txt")), None)
            example = ""
            if first:
                with archive.open(first) as stream:
                    example = stream.read(100).decode("utf-8", errors="replace")
            lines.append(f"### `{path.relative_to(ROOT)}`")
            lines.append(f"- File members: {len(members)}; example member: `{clip(first.filename if first else '')}`")
            lines.append(f"- Member schema: ZIP path/name, uncompressed byte size, compressed byte size; text members are UTF-8/byte-decoded with replacement for this example.")
            lines.append(f"- Example text (max 100 chars): `{clip(example)}`")
            lines.append("")

    lines.extend(
        [
            "## Plain-text documents",
            "",
            "The 01 corpus uses `.txt` contract documents. Each document's value is decoded text; "
            "document ID/path is the corresponding relative path. The manifest contains per-document "
            "character lengths and SHA-256 values. Example text from the first available unpacked file:",
            "",
        ]
    )
    sample_text = ""
    unpacked = LOAN_DIR / "publicly_filed_contracts"
    sample_path = next(iter(sorted(unpacked.rglob("*.txt"))), None) if unpacked.exists() else None
    if sample_path:
        sample_text = sample_path.read_bytes()[:100].decode("utf-8", errors="replace")
    lines.append(f"- Example (max 100 chars): `{clip(sample_text)}`")
    OUTPUT.joinpath("SCHEMA.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    COUNTS["schema_csv_files"] = len(csv_paths)
    COUNTS["schema_json_files"] = len(json_paths)
    COUNTS["schema_jsonl_files"] = len(jsonl_paths)


def load_metadata() -> None:
    global CONTROL, BREAKPOINTS
    CONTROL = load_json(LOAN_DIR / "main_control_file.json")
    BREAKPOINTS = load_json(LOAN_DIR / "breakpoint_file.json")
    print(
        f"Metadata loaded: {len(CONTROL)} control entries, {len(BREAKPOINTS)} breakpoint entries",
        flush=True,
    )


def decode_stats(source: Any) -> tuple[str, int, int, str]:
    digest = hashlib.sha256()
    decoder = None
    char_count = 0
    replacements = 0
    sample_parts: list[str] = []
    sample_len = 0
    while True:
        block = source.read(1024 * 1024)
        if not block:
            break
        digest.update(block)
        if decoder is None:
            import codecs

            decoder = codecs.getincrementaldecoder("utf-8-sig")("replace")
        text = decoder.decode(block, final=False)
        char_count += len(text)
        replacements += text.count("\ufffd")
        if sample_len < 100_000:
            keep = text[: 100_000 - sample_len]
            sample_parts.append(keep)
            sample_len += len(keep)
    if decoder is None:
        import codecs

        decoder = codecs.getincrementaldecoder("utf-8-sig")("replace")
    final_text = decoder.decode(b"", final=True)
    char_count += len(final_text)
    replacements += final_text.count("\ufffd")
    if sample_len < 100_000:
        sample_parts.append(final_text[: 100_000 - sample_len])
    return digest.hexdigest(), char_count, replacements, "".join(sample_parts)


def language_guess(text: str) -> str:
    words = re.findall(r"[A-Za-zÀ-ÿ]+", text[:100_000].lower())
    if len(words) < 20:
        return "unknown"
    english_hits = sum(word in ENGLISH_WORDS for word in words)
    other_hits = sum(word in NON_ENGLISH_WORDS for word in words)
    accented = sum(any(ord(ch) > 127 for ch in word) for word in words)
    if english_hits / len(words) >= 0.035 and accented / len(words) < 0.08:
        return "English (heuristic)"
    if accented / len(words) >= 0.08 or (
        other_hits / len(words) >= 0.025 and english_hits / len(words) < 0.02
    ):
        return "non-English (heuristic)"
    return "unknown"


def get_document_stats(
    doc_id: str, archive: zipfile.ZipFile, inventory: dict[str, str]
) -> tuple[dict[str, str], str]:
    local_path = LOAN_DIR / "publicly_filed_contracts" / Path(doc_id)
    if local_path.is_file():
        with local_path.open("rb") as stream:
            sha, chars, replacements, sample = decode_stats(stream)
        location = f"unpacked\\publicly_filed_contracts\\{doc_id.replace('/', chr(92))}"
    else:
        with archive.open(doc_id) as stream:
            sha, chars, replacements, sample = decode_stats(stream)
        location = f"zip:{doc_id}"
    metadata = CONTROL.get(doc_id, {})
    if not metadata:
        metadata = CONTROL.get(doc_id.replace("\\", "/"), {})
    status = inventory.get("review_status", "")
    dup_group = inventory.get("duplicate_group", "")
    canonical = inventory.get("canonical_duplicate_document_id", "")
    row = {
        "doc_id": doc_id,
        "location": location,
        "company": str(metadata.get("company") or inventory.get("company") or ""),
        "contract_year": str(metadata.get("year") or ""),
        "filing_index_page": str(metadata.get("index_page") or ""),
        "primary_contract": str(metadata.get("primary_contract") if metadata.get("primary_contract") is not None else ""),
        "classification_status": status,
        "duplicate_flag": "false",
        "sha256": sha,
        "character_length": str(chars),
        "language_guess": language_guess(sample),
        "has_covenant_breakpoints": "false",
        "_encoding_replacements": str(replacements),
        "_boilerplate": "false",
        "_sample": sample,
        "_duplicate_group": dup_group,
        "_canonical_duplicate_document_id": canonical,
    }
    bp = BREAKPOINTS.get(doc_id, {})
    covenant = bp.get("covenant_section", {}) if isinstance(bp, dict) else {}
    has_bp = any(
        isinstance(section, dict) and bool(section.get("breakpoints"))
        for section in covenant.values()
    ) if isinstance(covenant, dict) else False
    row["has_covenant_breakpoints"] = "true" if has_bp else "false"
    visible = re.sub(r"<[^>]*>", " ", sample)
    visible = re.sub(r"(?is)<!--.*?-->", " ", visible)
    visible_chars = len(re.sub(r"[^A-Za-z0-9]", "", visible))
    row["_boilerplate"] = "true" if visible_chars < 500 else "false"
    row["_encoding_replacements"] = str(replacements)
    return row, sample


def apply_duplicate_flags(
    rows: list[dict[str, str]], inventory_by_id: dict[str, dict[str, str]]
) -> dict[str, list[dict[str, str]]]:
    global LEGACY_CLEAN_IDS
    hash_groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        hash_groups[row["sha256"]].append(row)
    canonical_conflicts = 0
    for group in hash_groups.values():
        if len(group) == 1:
            group[0]["duplicate_flag"] = "false"
            continue
        member_ids = {row["doc_id"] for row in group}
        references = {
            (inventory_by_id.get(row["doc_id"], {}).get("canonical_duplicate_document_id") or "").strip()
            for row in group
        }
        references.discard("")
        valid_references = references & member_ids
        if len(valid_references) == 1:
            canonical_id = next(iter(valid_references))
        else:
            canonical_id = min(member_ids)
            if len(references) > 1 or (references and not valid_references):
                canonical_conflicts += 1
        for row in group:
            row["duplicate_flag"] = "false" if row["doc_id"] == canonical_id else "true"
            row["_canonical_duplicate_document_id"] = canonical_id
    COUNTS["sha256_duplicate_groups"] = sum(len(group) > 1 for group in hash_groups.values())
    COUNTS["hash_duplicate_documents"] = sum(
        len(group) for group in hash_groups.values() if len(group) > 1
    )
    COUNTS["duplicate_flagged_documents"] = sum(
        row["duplicate_flag"] == "true" for row in rows
    )
    COUNTS["duplicate_canonical_reference_conflicts"] = canonical_conflicts
    LEGACY_CLEAN_IDS = set()
    for row in rows:
        inventory = inventory_by_id.get(row["doc_id"], {})
        legacy_duplicate = (
            len(hash_groups[row["sha256"]]) > 1
            or row["classification_status"].strip().upper() == "DUPLICATE"
            or bool(inventory.get("duplicate_group"))
            or bool(inventory.get("canonical_duplicate_document_id"))
        )
        if (
            row["classification_status"] == "LIKELY_LOAN_AGREEMENT"
            and row["primary_contract"] == "1"
            and not legacy_duplicate
            and int(row["character_length"]) >= 5000
        ):
            LEGACY_CLEAN_IDS.add(row["doc_id"])
    COUNTS["legacy_clean_documents"] = len(LEGACY_CLEAN_IDS)
    return hash_groups


def build_manifest() -> None:
    global MANIFEST
    inventory_rows = list(iter_csv(INVENTORY_PATH))
    if not inventory_rows:
        raise ValueError("Candidate inventory is empty.")
    archive = zipfile.ZipFile(ZIP_PATH)
    archive_names = set(archive.namelist())
    if len(inventory_rows) != len({row.get("document_id", "") for row in inventory_rows}):
        raise ValueError("Candidate inventory contains duplicate document IDs.")
    absent = [row["document_id"] for row in inventory_rows if row["document_id"] not in archive_names]
    if absent:
        raise ValueError(f"{len(absent)} inventory IDs are missing from the ZIP; first: {absent[0]}")

    temp_rows: list[dict[str, str]] = []
    for index, inventory_row in enumerate(inventory_rows, 1):
        row, _ = get_document_stats(inventory_row["document_id"], archive, inventory_row)
        temp_rows.append(row)
        if index % 500 == 0:
            print(f"Manifest: processed {index:,}/{len(inventory_rows):,} documents", flush=True)
    archive.close()

    inventory_by_id = {row["document_id"]: row for row in inventory_rows}
    hash_groups = apply_duplicate_flags(temp_rows, inventory_by_id)
    MANIFEST.extend(temp_rows)

    fields = [
        "doc_id", "location", "company", "contract_year", "filing_index_page",
        "primary_contract", "classification_status", "duplicate_flag", "sha256",
        "character_length", "language_guess", "has_covenant_breakpoints",
    ]
    write_csv(OUTPUT / "manifest.csv", fields, MANIFEST)
    COUNTS["manifest_documents"] = len(MANIFEST)
    COUNTS["hash_duplicate_documents"] = sum(
        len(group) for sha, group in hash_groups.items() if len(group) > 1
    )
    COUNTS["duplicate_flagged_documents"] = sum(
        row["duplicate_flag"] == "true" for row in MANIFEST
    )
    COUNTS["encoding_problem_documents"] = sum(
        int(row["_encoding_replacements"]) > 0 for row in MANIFEST
    )
    COUNTS["boilerplate_only_documents"] = sum(row["_boilerplate"] == "true" for row in MANIFEST)
    COUNTS["non_english_documents"] = sum(
        row["language_guess"] == "non-English (heuristic)" for row in MANIFEST
    )
    COUNTS["empty_documents"] = sum(int(row["character_length"]) == 0 for row in MANIFEST)
    COUNTS["tiny_documents"] = sum(int(row["character_length"]) < 5000 for row in MANIFEST)


def read_machine_extractions() -> None:
    global EXTRACTION
    with JSONL_PATH.open("r", encoding="utf-8-sig", errors="replace") as stream:
        for index, line in enumerate(stream, 1):
            if not line.strip():
                continue
            item = json.loads(line)
            doc_id = item.get("document_id", "")
            if doc_id:
                EXTRACTION[doc_id] = item.get("fields") or {}
            if index % 500 == 0:
                print(f"Machine extraction: read {index:,} JSONL lines", flush=True)
    COUNTS["machine_extraction_documents"] = len(EXTRACTION)


def review_sources() -> list[Path]:
    return sorted(ANNOTATION_DIR.glob("batch_review_*.csv")) + [
        ANNOTATION_DIR / "caterpillar_first_review.csv"
    ]


def normalize_review_status(value: str) -> str:
    return re.sub(r"[\s-]+", "_", (value or "").strip().casefold())


def canonical_field(field: str) -> str:
    normalized = (field or "").strip()
    return CANONICAL_ALIASES.get(normalized.casefold(), normalized)


def resolve_review_document_id(
    record: dict[str, str], known_doc_ids: set[str]
) -> str:
    for field in ("document_id", "source_path", "source_file"):
        candidate = (record.get(field) or "").strip().replace("\\", "/")
        if candidate in known_doc_ids:
            return candidate
        parts = candidate.split("/")
        for index, part in enumerate(parts):
            if part.casefold() == "publicly_filed_contracts":
                suffix = "/".join(parts[index + 1 :])
                if suffix in known_doc_ids:
                    return suffix
        for doc_id in known_doc_ids:
            if candidate.endswith("/" + doc_id):
                return doc_id
    return ""


def normalize_annotations() -> None:
    global REVIEW_ROWS, GOLD_DOCS, ANNOTATION_DUPLICATES_REMOVED
    GOLD_DOCS.clear()
    known_doc_ids = {row["doc_id"] for row in MANIFEST}
    sources = [path for path in review_sources() if path.is_file()]
    if len(sources) != 21:
        raise ValueError(f"Expected 21 per-document review CSVs; found {len(sources)}.")
    source_headers: list[str] = []
    mapping: dict[str, str] = {}
    out_rows: list[dict[str, str]] = []
    for path in sources:
        encoding = csv_encoding(path)
        with path.open("r", encoding=encoding, errors="replace", newline="") as stream:
            reader = csv.DictReader(stream)
            headers = reader.fieldnames or []
            for header in headers:
                if header not in source_headers:
                    source_headers.append(header)
            for record in reader:
                original_name = record.get("field_name", "")
                canonical_name = canonical_field(original_name)
                if original_name:
                    mapping[original_name] = canonical_name
                status = record.get("review_status", "")
                normalized = {key: (value or "") for key, value in record.items() if key}
                normalized["original_field_name"] = original_name
                normalized["original_value"] = record.get("candidate_value", "")
                normalized["field_name"] = canonical_name
                normalized["review_status"] = normalize_review_status(status)
                normalized["source_file"] = path.name
                out_rows.append(normalized)
                if normalized["review_status"] in {"source_verified", "manual_verification"}:
                    doc_id = resolve_review_document_id(record, known_doc_ids)
                    if doc_id:
                        GOLD_DOCS.add(doc_id)

    out_fields = source_headers.copy()
    for name in ("original_field_name", "original_value", "source_file"):
        if name not in out_fields:
            out_fields.append(name)
    if "field_name" not in out_fields:
        out_fields.append("field_name")
    if "review_status" not in out_fields:
        out_fields.append("review_status")
    unique_rows: list[dict[str, str]] = []
    seen_rows: set[tuple[str, str, str, str]] = set()
    for row in out_rows:
        key = (
            row.get("document_id", ""),
            row.get("field_name", ""),
            row.get("candidate_value", ""),
            row.get("review_status", ""),
        )
        if key in seen_rows:
            continue
        seen_rows.add(key)
        unique_rows.append(row)
    ANNOTATION_DUPLICATES_REMOVED = len(out_rows) - len(unique_rows)
    write_csv(OUTPUT / "annotations_normalized.csv", out_fields, unique_rows)
    write_csv(
        OUTPUT / "field_mapping.csv",
        ["original_field_name", "canonical_field_name"],
        [
            {"original_field_name": name, "canonical_field_name": canonical}
            for name, canonical in sorted(mapping.items(), key=lambda item: item[0].casefold())
        ],
    )
    REVIEW_ROWS = unique_rows

    # Search all supplied CSVs for the exact human-verification status values.
    for path in sorted(ANNOTATION_DIR.glob("*.csv")):
        for row in iter_csv(path):
            status = normalize_review_status(row.get("review_status", ""))
            manual = normalize_review_status(row.get("manual_verification", ""))
            if status in {"source_verified", "manual_verification"} or manual in {
                "source_verified", "manual_verification"
            }:
                doc_id = resolve_review_document_id(row, known_doc_ids)
                if doc_id:
                    GOLD_DOCS.add(doc_id)
    COUNTS["normalized_review_rows"] = len(unique_rows)
    COUNTS["normalized_duplicate_rows_removed"] = ANNOTATION_DUPLICATES_REMOVED
    COUNTS["review_csv_files"] = len(sources)
    COUNTS["gold_review_documents"] = len(GOLD_DOCS)
    COUNTS["field_mappings"] = len(mapping)


def make_clean_set_and_splits() -> None:
    global CLEAN, GOLD_EXTRA, DEDUPLICATE_DOCS_ADDED_BACK
    statuses = Counter(row["classification_status"] for row in MANIFEST)
    independent_removed = {
        "not_likely_loan_agreement": sum(
            row["classification_status"] != "LIKELY_LOAN_AGREEMENT" for row in MANIFEST
        ),
        "not_primary_contract": sum(row["primary_contract"] != "1" for row in MANIFEST),
        "duplicate": sum(row["duplicate_flag"] == "true" for row in MANIFEST),
        "length_under_5000": sum(int(row["character_length"]) < 5000 for row in MANIFEST),
    }
    eligible: list[dict[str, str]] = []
    sequential = Counter()
    for row in MANIFEST:
        if row["classification_status"] != "LIKELY_LOAN_AGREEMENT":
            sequential["not_likely_loan_agreement"] += 1
        elif row["primary_contract"] != "1":
            sequential["not_primary_contract"] += 1
        elif row["duplicate_flag"] == "true":
            sequential["duplicate"] += 1
        elif int(row["character_length"]) < 5000:
            sequential["length_under_5000"] += 1
        else:
            eligible.append(dict(row))

    companies: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in eligible:
        company = row["company"] or f"__NO_COMPANY__:{row['doc_id']}"
        companies[company].append(row)
    gold_companies = {
        row["company"] or f"__NO_COMPANY__:{row['doc_id']}"
        for row in MANIFEST
        if row["doc_id"] in GOLD_DOCS
    }
    rng = random.Random(42)
    other_companies = [company for company in companies if company not in gold_companies]
    rng.shuffle(other_companies)
    ordered = sorted(other_companies, key=lambda company: len(companies[company]), reverse=True)

    total_docs = len(eligible)
    targets = {"train": total_docs * 0.70, "val": total_docs * 0.15, "test": total_docs * 0.15}
    assigned = Counter()
    assignments: dict[str, str] = {company: "test" for company in gold_companies}
    assigned["test"] = sum(len(companies[company]) for company in gold_companies)
    for company in ordered:
        size = len(companies[company])
        candidates = ["train", "val", "test"]
        # Assign to the split with the largest remaining proportional deficit.
        score = {
            split: (targets[split] - assigned[split]) / max(targets[split], 1)
            for split in candidates
        }
        split = max(candidates, key=lambda name: (score[name], -candidates.index(name)))
        assignments[company] = split
        assigned[split] += size

    for row in eligible:
        company = row["company"] or f"__NO_COMPANY__:{row['doc_id']}"
        row["split"] = assignments[company]
        CLEAN.append(row)
    clean_doc_ids = {row["doc_id"] for row in CLEAN}
    GOLD_EXTRA = []
    for row in MANIFEST:
        if row["doc_id"] not in GOLD_DOCS or row["doc_id"] in clean_doc_ids:
            continue
        extra = {
            key: value
            for key, value in row.items()
            if not key.startswith("_")
        }
        extra["split"] = "test"
        extra["gold_extra"] = "true"
        failures = []
        if row["classification_status"] != "LIKELY_LOAN_AGREEMENT":
            failures.append("classification_not_likely_loan_agreement")
        if row["primary_contract"] != "1":
            failures.append("primary_contract_not_1")
        if row["duplicate_flag"] == "true":
            failures.append("duplicate")
        if int(row["character_length"]) < 5000:
            failures.append("under_5000_characters")
        extra["clean_exclusion_reason"] = ";".join(failures)
        GOLD_EXTRA.append(extra)
    fields = [
        "doc_id", "location", "company", "contract_year", "filing_index_page",
        "primary_contract", "classification_status", "duplicate_flag", "sha256",
        "character_length", "language_guess", "has_covenant_breakpoints", "split",
    ]
    write_csv(OUTPUT / "clean_loans.csv", fields, CLEAN)
    write_csv(
        OUTPUT / "gold_extra.csv",
        fields + ["gold_extra", "clean_exclusion_reason"],
        GOLD_EXTRA,
    )
    DEDUPLICATE_DOCS_ADDED_BACK = len(
        {row["doc_id"] for row in CLEAN} - LEGACY_CLEAN_IDS
    )

    split_companies = {
        split: {
            row["company"] or f"__NO_COMPANY__:{row['doc_id']}"
            for row in CLEAN if row["split"] == split
        }
        for split in ("train", "val", "test")
    }
    reviewed_outside_clean = [
        row for row in MANIFEST
        if row["doc_id"] in GOLD_DOCS and row["doc_id"] not in clean_doc_ids
    ]
    overlaps = {
        "train_val": len(split_companies["train"] & split_companies["val"]),
        "train_test": len(split_companies["train"] & split_companies["test"]),
        "val_test": len(split_companies["val"] & split_companies["test"]),
    }
    report_lines = [
        "# Clean-set filter report",
        "",
        f"- Input documents: {len(MANIFEST)}",
        f"- Clean documents: {len(CLEAN)}",
        f"- Classification counts: {dict(sorted(statuses.items()))}",
        "",
        "## Removed counts by individual reason",
        "",
        "Counts below are independent (a document may fail more than one condition):",
        "",
    ]
    report_lines.extend(f"- {name}: {count}" for name, count in independent_removed.items())
    report_lines.extend(
        [
            "",
            "## Exclusive first-failure counts",
            "",
            "These sequential counts are mutually exclusive and sum with the clean set to the input total:",
            "",
        ]
    )
    report_lines.extend(f"- {name}: {sequential[name]}" for name in independent_removed)
    report_lines.extend(
        [
            "",
            "## Split counts and group isolation",
            "",
            f"- Train: {sum(row['split'] == 'train' for row in CLEAN)}",
            f"- Val: {sum(row['split'] == 'val' for row in CLEAN)}",
            f"- Test: {sum(row['split'] == 'test' for row in CLEAN)}",
            f"- Human-verified documents identified in review data: {len(GOLD_DOCS)}",
            f"- Gold-reviewed documents forced to test: {sum(row['doc_id'] in GOLD_DOCS for row in CLEAN)}",
            f"- Additional human-verified gold_extra documents in test: {len(GOLD_EXTRA)}",
            f"- Documents added back by canonical SHA-256 deduplication: {DEDUPLICATE_DOCS_ADDED_BACK}",
            f"- Company overlaps (train/val, train/test, val/test): {overlaps['train_val']}, {overlaps['train_test']}, {overlaps['val_test']}",
            f"- Zero company overlap: {'yes' if not any(overlaps.values()) else 'NO'}",
            "",
            "Human-verified review rows are resolved through document IDs and recorded source paths. "
            "All reviewed companies are assigned to test. Gold documents that fail clean-set filters are "
            "listed separately in gold_extra.csv and remain part of the test set without being mixed into clean_loans.csv.",
            "",
            "Reviewed documents outside the clean set:",
            "",
        ]
    )
    for row in reviewed_outside_clean:
        reasons = []
        if row["classification_status"] != "LIKELY_LOAN_AGREEMENT":
            reasons.append("classification is not LIKELY_LOAN_AGREEMENT")
        if row["primary_contract"] != "1":
            reasons.append("primary_contract is not 1")
        if row["duplicate_flag"] == "true":
            reasons.append("duplicate")
        if int(row["character_length"]) < 5000:
            reasons.append("under 5,000 characters")
        report_lines.append(f"- `{row['doc_id']}`: {', '.join(reasons)}")
    report_lines.extend(
        [
            "",
            "For repeated SHA-256 hashes, only non-canonical copies are duplicate-flagged; canonical copies are "
            "selected from canonical_duplicate_document_id or, when absent, the lexically smallest doc_id. Grouping by company "
            "uses the recorded company value. Rows with a missing company are isolated by document ID.",
            "",
            "The split assignment is seeded with 42 and assigns whole companies to approximate document-level "
            "70/15/15 targets; companies containing gold-reviewed documents are forced into test.",
            "",
        ]
    )
    OUTPUT.joinpath("filter_report.md").write_text("\n".join(report_lines), encoding="utf-8")
    COUNTS.update(
        {
            "clean_documents": len(CLEAN),
            "duplicates_added_back": DEDUPLICATE_DOCS_ADDED_BACK,
            "gold_extra_documents": len(GOLD_EXTRA),
            "train_documents": sum(row["split"] == "train" for row in CLEAN),
            "val_documents": sum(row["split"] == "val" for row in CLEAN),
            "test_documents": sum(row["split"] == "test" for row in CLEAN),
            "train_val_company_overlap": overlaps["train_val"],
            "train_test_company_overlap": overlaps["train_test"],
            "val_test_company_overlap": overlaps["val_test"],
            "gold_reviewed_clean_documents": sum(
                row["doc_id"] in GOLD_DOCS for row in CLEAN
            ),
        }
    )


def allocate_year_stratified(rows: list[dict[str, str]], count: int) -> list[dict[str, str]]:
    if len(rows) < count:
        raise ValueError(f"Need {count} annotation documents; only {len(rows)} are eligible.")
    bins: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        bins[row["contract_year"] or "unknown"].append(row)

    exact = {key: count * len(group) / len(rows) for key, group in bins.items()}
    allocations = {key: math.floor(value) for key, value in exact.items()}
    remainder = count - sum(allocations.values())
    for key in sorted(bins, key=lambda item: (-(exact[item] - allocations[item]), item)):
        if remainder <= 0:
            break
        if allocations[key] < len(bins[key]):
            allocations[key] += 1
            remainder -= 1

    rng = random.Random(42)
    selected: list[dict[str, str]] = []
    for key in sorted(bins):
        group = list(bins[key])
        rng.shuffle(group)
        selected.extend(group[: allocations[key]])
    rng.shuffle(selected)
    return selected


def evenly_sample(rows: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    if count >= len(rows):
        return list(rows)
    if count <= 0:
        return []
    if count == 1:
        return [rows[len(rows) // 2]]
    indices = [
        round(index * (len(rows) - 1) / (count - 1))
        for index in range(count)
    ]
    return [rows[index] for index in indices]


def value_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def candidate_for(fields: dict[str, Any], target: str) -> tuple[str, str]:
    for alias in EXTRACTION_ALIASES[target]:
        record = fields.get(alias)
        if not isinstance(record, dict):
            continue
        value = value_text(record.get("proposed_value"))
        evidence = value_text(record.get("evidence"))
        if value or evidence:
            return value, evidence
    return "", ""


def read_document_text(doc_id: str) -> str:
    local_path = LOAN_DIR / "publicly_filed_contracts" / Path(doc_id)
    if local_path.is_file():
        raw = local_path.read_bytes()
    else:
        with zipfile.ZipFile(ZIP_PATH) as archive:
            raw = archive.read(doc_id)
    return raw.decode("utf-8-sig", errors="replace")


HEADING_RE = re.compile(
    r"(?im)^[ \t]*(?:(?:Section|Sec\.)\s+\d+(?:\.\d+)*(?:[A-Za-z])?\.?[^\r\n]*|ARTICLE\s+[IVXLCDM0-9]+[^\r\n]*)"
)

RISK_KEYWORDS = (
    "default", "penalt", "late charge", "prepay", "fee", "interest rate",
    "collateral", "security interest", "guarant", "terminat",
    "acceleration", "covenant",
)
RISK_KEYWORD_RE = re.compile("|".join(re.escape(word) for word in RISK_KEYWORDS), re.IGNORECASE)


def clause_segments(text: str) -> list[tuple[str, str, int]]:
    matches = list(HEADING_RE.finditer(text))
    if not matches:
        stripped = text.strip()
        if not stripped:
            return []
        first = next((line.strip() for line in stripped.splitlines() if line.strip()), "")
        start = text.find(stripped)
        return [(first, stripped, start)]
    segments: list[tuple[str, str, int]] = []
    if matches[0].start() > 0:
        preface = text[: matches[0].start()].strip()
        if preface:
            first = next((line.strip() for line in preface.splitlines() if line.strip()), "")
            segments.append((first, preface, text.find(preface)))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.start() : end].strip()
        if block:
            heading = match.group(0).strip()
            segments.append((heading, block, match.start()))
    return segments


def clause_is_in_control_range(
    doc_id: str, line_number: int, control: dict[str, Any]
) -> bool:
    for section_type in ("default_section", "covenant_section"):
        sections = control.get(section_type, {})
        if not isinstance(sections, dict):
            continue
        for section in sections.values():
            if not isinstance(section, dict):
                continue
            top = section.get("top_line")
            bottom = section.get("bottom_line")
            if (
                isinstance(top, int)
                and isinstance(bottom, int)
                and top <= line_number <= bottom
            ):
                return True
    return False


def scoped_clause_segments(
    doc_id: str, text: str, control: dict[str, Any]
) -> list[tuple[str, str, int]]:
    source_lines = text.splitlines(keepends=True)
    if not source_lines:
        return []
    line_offsets = [0]
    for source_line in source_lines:
        line_offsets.append(line_offsets[-1] + len(source_line))

    segments: list[tuple[str, str, int]] = []
    seen_ranges: set[tuple[int, int]] = set()
    if isinstance(control, dict):
        for section_type in ("default_section", "covenant_section"):
            sections = control.get(section_type, {})
            breakpoint_sections = BREAKPOINTS.get(doc_id) or {}
            breakpoint_sections = (
                breakpoint_sections.get(section_type, {})
                if isinstance(breakpoint_sections, dict)
                else {}
            )
            if not isinstance(sections, dict) or not isinstance(breakpoint_sections, dict):
                continue
            for section_id, section in sections.items():
                if not isinstance(section, dict):
                    continue
                top = section.get("top_line")
                bottom = section.get("bottom_line")
                if not isinstance(top, int) or not isinstance(bottom, int) or top < 1:
                    continue
                start_line = max(0, top - 1)
                stop_line = min(len(source_lines), bottom)
                if stop_line <= start_line:
                    continue
                bp_section = breakpoint_sections.get(section_id)
                points = bp_section.get("breakpoints", []) if isinstance(bp_section, dict) else []
                relative_lines = sorted(
                    {
                        point["line"]
                        for point in points
                        if isinstance(point, dict)
                        and isinstance(point.get("line"), int)
                        and point["line"] >= 0
                    }
                )
                boundaries = sorted(
                    {
                        min(start_line + point, stop_line)
                        for point in relative_lines
                        if start_line + point < stop_line
                    }
                )
                if not boundaries or boundaries[0] != start_line:
                    boundaries.insert(0, start_line)
                boundaries.append(stop_line)
                for left, right in zip(boundaries, boundaries[1:]):
                    if right <= left or (left, right) in seen_ranges:
                        continue
                    seen_ranges.add((left, right))
                    clause_text = "".join(source_lines[left:right]).strip()
                    if not clause_text:
                        continue
                    heading = next(
                        (line.strip() for line in clause_text.splitlines() if line.strip()),
                        "",
                    )
                    segments.append((heading, clause_text, line_offsets[left]))

    for heading, clause_text, offset in clause_segments(text):
        line_number = bisect.bisect_right(line_offsets, offset)
        if clause_is_in_control_range(doc_id, line_number, control):
            continue
        if RISK_KEYWORD_RE.search(clause_text):
            segments.append((heading, clause_text, offset))
    return segments


def make_annotation_sheets() -> None:
    global SELECTED_DOCS
    candidates = [
        row for row in CLEAN
        if row["split"] == "test"
        and row["doc_id"] not in GOLD_DOCS
        and 30_000 <= int(row["character_length"]) <= 400_000
    ]
    SELECTED_DOCS = allocate_year_stratified(candidates, 60)
    key_rows: list[dict[str, str]] = []
    eligible_clauses: dict[str, list[dict[str, Any]]] = {}
    for index, row in enumerate(SELECTED_DOCS, 1):
        doc_id = row["doc_id"]
        extracted = EXTRACTION.get(doc_id, {})
        if not isinstance(extracted, dict):
            extracted = {}
        for field in SHEET_FIELDS:
            value, evidence = candidate_for(extracted, field)
            key_rows.append(
                {
                    "doc_id": doc_id,
                    "field_name": field,
                    "machine_candidate_value": value,
                    "evidence_excerpt": evidence,
                    "human_value": "",
                    "human_status": "",
                    "annotator": "",
                    "notes": "",
                }
            )
        text = read_document_text(doc_id)
        control = CONTROL.get(doc_id) or {}
        clauses = []
        for heading, clause_text, offset in scoped_clause_segments(doc_id, text, control):
            keyword_hit = bool(RISK_KEYWORD_RE.search(clause_text))
            clauses.append(
                {
                    "doc_id": doc_id,
                    "clause_heading": heading,
                    "clause_text": clause_text,
                    "keyword_hit": "true" if keyword_hit else "false",
                }
            )
        eligible_clauses[doc_id] = clauses
        if index % 500 == 0:
            print(f"Annotation sheets: processed {index:,}/60 documents", flush=True)

    quotas = {doc_id: min(25, len(clauses)) for doc_id, clauses in eligible_clauses.items()}
    target_clause_count = min(1500, sum(len(clauses) for clauses in eligible_clauses.values()))
    while sum(quotas.values()) < target_clause_count:
        available = [
            doc_id for doc_id, clauses in eligible_clauses.items()
            if quotas[doc_id] < len(clauses)
        ]
        if not available:
            break
        doc_id = min(available, key=lambda item: (quotas[item], item))
        quotas[doc_id] += 1

    risk_rows: list[dict[str, str]] = []
    for doc_id in sorted(eligible_clauses):
        chosen = evenly_sample(eligible_clauses[doc_id], quotas[doc_id])
        for clause_index, clause in enumerate(chosen, 1):
            risk_rows.append(
                {
                    **clause,
                    "clause_id": f"C{clause_index:04d}",
                    "risk_category": "",
                    "severity": "",
                    "rationale": "",
                    "annotator": "",
                }
            )

    write_csv(
        SHEETS / "key_info_sheet.csv",
        [
            "doc_id", "field_name", "machine_candidate_value", "evidence_excerpt",
            "human_value", "human_status", "annotator", "notes",
        ],
        key_rows,
    )
    write_csv(
        SHEETS / "risk_clause_sheet.csv",
        [
            "doc_id", "clause_id", "clause_heading", "clause_text", "keyword_hit",
            "risk_category", "severity", "rationale", "annotator",
        ],
        risk_rows,
    )
    write_csv(
        SHEETS / "qa_sheet.csv",
        ["doc_id", "question", "answer", "supporting_text", "clause_id", "annotator"],
        [
            {"doc_id": row["doc_id"]}
            for row in SELECTED_DOCS[:30]
            for _ in range(4)
        ],
    )
    COUNTS["annotation_documents"] = len(SELECTED_DOCS)
    COUNTS["key_info_rows"] = len(key_rows)
    COUNTS["risk_clause_rows"] = len(risk_rows)
    COUNTS["qa_documents"] = min(30, len(SELECTED_DOCS))
    COUNTS["qa_rows"] = min(30, len(SELECTED_DOCS)) * 4
    COUNTS["risk_clause_documents"] = len(eligible_clauses)
    COUNTS["risk_clause_target"] = target_clause_count
    COUNTS["risk_clause_min_per_document"] = min(quotas.values(), default=0)
    COUNTS["risk_clause_max_per_document"] = max(quotas.values(), default=0)
    COUNTS["risk_clause_per_document"] = {
        doc_id: quotas[doc_id] for doc_id in sorted(quotas)
    }


def quality_report() -> None:
    sorted_rows = sorted(MANIFEST, key=lambda row: (int(row["character_length"]), row["doc_id"]))
    shortest = sorted_rows[:20]
    longest = sorted_rows[-20:][::-1]
    encoding_rows = [
        row for row in MANIFEST if int(row["_encoding_replacements"]) > 0
    ]
    tiny_rows = [row for row in MANIFEST if int(row["character_length"]) < 5000]
    boilerplate_rows = [row for row in MANIFEST if row["_boilerplate"] == "true"]
    non_english_rows = [
        row for row in MANIFEST if row["language_guess"] == "non-English (heuristic)"
    ]

    def table(rows: list[dict[str, str]]) -> list[str]:
        output = ["| doc_id | chars | language | encoding replacements |", "|---|---:|---|---:|"]
        output.extend(
            f"| `{row['doc_id']}` | {row['character_length']} | {row['language_guess']} | {row['_encoding_replacements']} |"
            for row in rows
        )
        return output

    lines = [
        "# Data quality report",
        "",
        f"- Documents checked: {len(MANIFEST)}",
        f"- Empty files (0 decoded characters): {COUNTS.get('empty_documents', 0)}",
        f"- Tiny files (<5,000 decoded characters): {len(tiny_rows)}",
        f"- Files with UTF-8 replacement characters: {len(encoding_rows)} "
        f"({sum(int(row['_encoding_replacements']) for row in encoding_rows)} replacement characters)",
        f"- Boilerplate-only heuristic matches: {len(boilerplate_rows)}",
        f"- Non-English heuristic matches: {len(non_english_rows)}",
        "",
        "Encoding is evaluated as streaming UTF-8-with-BOM decoding using replacement for malformed byte sequences; "
        "replacement-character counts are reported. Language labels are heuristic only: English uses common English "
        "function words, and non-English uses accented-letter/common non-English-word thresholds; remaining files "
        "are marked unknown. Boilerplate-only means fewer than 500 ASCII letters/digits remain in the first "
        "100,000 decoded characters after HTML-tag removal; it is a screening heuristic, not a human judgment.",
        "",
        "## Encoding-problem documents (first 100)",
        "",
    ]
    lines.extend(table(encoding_rows[:100]))
    lines.extend(["", "## Tiny documents (first 100)", ""])
    lines.extend(table(tiny_rows[:100]))
    lines.extend(["", "## Boilerplate-only heuristic matches (first 100)", ""])
    lines.extend(table(boilerplate_rows[:100]))
    lines.extend(["", "## Non-English heuristic matches (first 100)", ""])
    lines.extend(table(non_english_rows[:100]))
    lines.extend(["", "## 20 shortest documents", ""])
    lines.extend(table(shortest))
    lines.extend(["", "## 20 longest documents", ""])
    lines.extend(table(longest))
    OUTPUT.joinpath("quality_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_error_log() -> None:
    if ERRORS:
        OUTPUT.joinpath("processing_errors.log").write_text(
            "\n".join(ERRORS) + "\n", encoding="utf-8"
        )
    else:
        COUNTS["processing_errors"] = 0
        OUTPUT.joinpath("processing_errors.log").write_text(
            "No unresolved processing errors.\n", encoding="utf-8"
        )


def write_readme() -> None:
    outputs = [
        "SCHEMA.md", "manifest.csv", "clean_loans.csv", "filter_report.md",
        "gold_extra.csv", "annotations_normalized.csv", "field_mapping.csv",
        "quality_report.md", "CHANGES.md",
        "annotation_sheets/key_info_sheet.csv",
        "annotation_sheets/risk_clause_sheet.csv",
        "annotation_sheets/qa_sheet.csv",
    ]
    if ERRORS or (OUTPUT / "processing_errors.log").exists():
        outputs.append("processing_errors.log")
    lines = [
        "# Processed v1 outputs",
        "",
        "All generated files are in `processed_v1`; source files were read-only and were not extracted or modified.",
        "",
        "## Output files",
        "",
        "- `SCHEMA.md`: CSV/backup columns and row counts; JSON/JSONL keys and examples; ZIP member counts; text document inventory and examples. Includes CUAD as contextual schema only.",
        "- `manifest.csv`: one row per candidate inventory document with `contract_year`. Uses unpacked files when present and streams remaining content directly from the ZIP; SHA-256 and decoded character length are calculated from the actual bytes.",
        "- `clean_loans.csv`: LIKELY_LOAN_AGREEMENT, primary_contract=1, canonical SHA-256 copy, and at least 5,000 characters; company-grouped split included.",
        "- `gold_extra.csv`: human-verified gold documents outside the clean filters, explicitly retained in test as gold_extra.",
        "- `filter_report.md`: independent and exclusive filter removal counts plus split counts and company-overlap checks.",
        "- `annotations_normalized.csv`: merged rows from the 21 per-document review CSVs; field aliases normalized, review statuses casefolded and separator-normalized, and source field/value retained.",
        "- `field_mapping.csv`: observed input field-name to canonical field-name mapping.",
        "- `quality_report.md`: encoding, size, boilerplate, language heuristics, and shortest/longest document reports.",
        "- `annotation_sheets/key_info_sheet.csv`: 60 test documents in the 30,000-400,000 character range, stratified by contract year, with 16 requested fields.",
        "- `annotation_sheets/risk_clause_sheet.csv`: about 1,500 relevant clauses from those 60 documents, filtered by main-control ranges or risk-keyword matches and balanced across documents; label columns blank.",
        "- `annotation_sheets/qa_sheet.csv`: four blank QA rows for each of 30 selected test documents.",
        "- `CHANGES.md`: requested changes, deduplication effect, gold extras, sample counts, and clause counts per document.",
    ]
    lines.extend(f"- `{name}`" for name in outputs if name == "processing_errors.log")
    lines.extend(["", "## Final counts", ""])
    keys = [
        ("manifest_documents", "Manifest documents"),
        ("clean_documents", "Clean documents"),
        ("train_documents", "Train documents"),
        ("val_documents", "Validation documents"),
        ("test_documents", "Test documents"),
        ("gold_review_documents", "Human-verified documents identified"),
        ("gold_reviewed_clean_documents", "Clean gold-reviewed documents forced to test"),
        ("gold_extra_documents", "Gold-extra documents in test"),
        ("duplicates_added_back", "Documents added back by canonical hash deduplication"),
        ("hash_duplicate_documents", "Documents in repeated SHA-256 groups"),
        ("duplicate_flagged_documents", "Duplicate-flagged documents"),
        ("normalized_review_rows", "Normalized review rows"),
        ("normalized_duplicate_rows_removed", "Duplicate normalized rows removed"),
        ("sha256_duplicate_groups", "Repeated SHA-256 groups"),
        ("field_mappings", "Observed field mappings"),
        ("annotation_documents", "Annotation-sheet documents"),
        ("key_info_rows", "Key-info rows"),
        ("risk_clause_rows", "Risk-clause rows"),
        ("risk_clause_target", "Risk clause target"),
        ("risk_clause_min_per_document", "Minimum risk clauses per selected document"),
        ("risk_clause_max_per_document", "Maximum risk clauses per selected document"),
        ("qa_documents", "QA-sheet documents"),
        ("qa_rows", "Blank QA rows"),
        ("encoding_problem_documents", "Documents with encoding replacements"),
        ("empty_documents", "Empty documents"),
        ("tiny_documents", "Documents under 5,000 characters"),
        ("boilerplate_only_documents", "Boilerplate heuristic matches"),
        ("non_english_documents", "Non-English heuristic matches"),
        ("train_val_company_overlap", "Train/validation company overlap"),
        ("train_test_company_overlap", "Train/test company overlap"),
        ("val_test_company_overlap", "Validation/test company overlap"),
    ]
    lines.extend(f"- {label}: {COUNTS.get(key, 'not produced')}" for key, label in keys)
    lines.extend(
        [
            "",
            "Document-level split assignment is deterministic (seed 42) and whole companies remain in one split. "
            "Companies containing records with the exact normalized status `source_verified` or "
            "`manual_verification` are assigned to test. No risk category, severity, rationale, question, answer, "
            "or human annotation value is generated.",
            "",
        ]
    )
    OUTPUT.joinpath("README.md").write_text("\n".join(lines), encoding="utf-8")


def write_changes() -> None:
    split_counts = Counter(row["split"] for row in CLEAN)
    clause_counts = COUNTS.get("risk_clause_per_document", {})
    lines = [
        "# Changes and refreshed counts",
        "",
        "Updated by `scripts/build_processed_v1.py`. Existing source data was read-only.",
        "",
        "## Changes made",
        "",
        "- Repeated SHA-256 groups now retain one canonical document: the inventory's `canonical_duplicate_document_id` when it identifies a member of that hash group; otherwise the lexically smallest `doc_id`. Only the non-canonical group members are duplicate-flagged.",
        "- Standardized the year column as `contract_year` in manifest and clean-set outputs.",
        "- All three human-verified gold documents are assigned to the test set. Any reviewed document outside clean criteria is listed separately in `gold_extra.csv`.",
        "- Selected 60 non-gold test documents between 30,000 and 400,000 characters, stratified by `contract_year`.",
        "- Risk clauses are limited to control-file `default_section`/`covenant_section` ranges or clauses matching the requested keyword list. The set is balanced toward 25 clauses per document and capped at 1,500 total.",
        f"- Risk keywords: {', '.join(RISK_KEYWORDS)}.",
        "- Created four blank QA rows for each of 30 selected documents.",
        "- Removed duplicate normalized annotation rows using `(document_id, field_name, candidate_value, review_status)` as the de-duplication key.",
        "",
        "## Counts",
        "",
        f"- Manifest documents: {len(MANIFEST)}",
        f"- Repeated SHA-256 groups: {COUNTS.get('sha256_duplicate_groups', 0)}",
        f"- Documents in repeated SHA-256 groups: {COUNTS.get('hash_duplicate_documents', 0)}",
        f"- Non-canonical duplicate copies flagged: {COUNTS.get('duplicate_flagged_documents', 0)}",
        f"- Clean documents under the previous duplicate rule: {COUNTS.get('legacy_clean_documents', len(LEGACY_CLEAN_IDS))}",
        f"- Clean documents after this change: {len(CLEAN)}",
        f"- Documents added back by canonical hash deduplication: {DEDUPLICATE_DOCS_ADDED_BACK}",
        f"- Gold documents identified: {len(GOLD_DOCS)}",
        f"- Clean gold documents in test: {sum(row['doc_id'] in GOLD_DOCS for row in CLEAN)}",
        f"- Additional `gold_extra` documents in test: {len(GOLD_EXTRA)}",
        f"- Train / validation / test clean counts: {split_counts.get('train', 0)} / {split_counts.get('val', 0)} / {split_counts.get('test', 0)}",
        f"- Company overlaps between clean splits: {COUNTS.get('train_val_company_overlap', 0)} / {COUNTS.get('train_test_company_overlap', 0)} / {COUNTS.get('val_test_company_overlap', 0)}",
        f"- Normalized annotation rows after de-duplication: {COUNTS.get('normalized_review_rows', 0)}",
        f"- Duplicate annotation rows removed: {ANNOTATION_DUPLICATES_REMOVED}",
        f"- Annotation-sheet documents: {COUNTS.get('annotation_documents', 0)}",
        f"- Key-info rows: {COUNTS.get('key_info_rows', 0)}",
        f"- Risk clause rows: {COUNTS.get('risk_clause_rows', 0)} (target {COUNTS.get('risk_clause_target', 0)})",
        f"- QA documents / blank rows: {COUNTS.get('qa_documents', 0)} / {COUNTS.get('qa_rows', 0)}",
        "",
        "## Risk clauses per selected document",
        "",
        "| doc_id | clauses |",
        "|---|---:|",
    ]
    lines.extend(
        f"| `{doc_id}` | {count} |"
        for doc_id, count in sorted(clause_counts.items())
    )
    lines.append("")
    OUTPUT.joinpath("CHANGES.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    global MANIFEST, CLEAN, PREVIOUS_CLEAN_IDS
    OUTPUT.mkdir(parents=True, exist_ok=True)
    SHEETS.mkdir(parents=True, exist_ok=True)
    if (OUTPUT / "clean_loans.csv").is_file():
        PREVIOUS_CLEAN_IDS = {
            row.get("doc_id", "")
            for row in iter_csv(OUTPUT / "clean_loans.csv")
            if row.get("doc_id")
        }
    if "--schema-only" in sys.argv:
        schema_report()
        print(f"Schema report refreshed: {OUTPUT / 'SCHEMA.md'}", flush=True)
        return
    if "--refresh-existing" in sys.argv or "--sheets-only" in sys.argv:
        load_metadata()
        MANIFEST = list(iter_csv(OUTPUT / "manifest.csv"))
        inventory_rows = list(iter_csv(INVENTORY_PATH))
        inventory_by_id = {row["document_id"]: row for row in inventory_rows}
        apply_duplicate_flags(MANIFEST, inventory_by_id)
        manifest_fields = [
            "doc_id", "location", "company", "contract_year", "filing_index_page",
            "primary_contract", "classification_status", "duplicate_flag", "sha256",
            "character_length", "language_guess", "has_covenant_breakpoints",
        ]
        write_csv(OUTPUT / "manifest.csv", manifest_fields, MANIFEST)
        CLEAN = []
        COUNTS["manifest_documents"] = len(MANIFEST)
        read_machine_extractions()
        normalize_annotations()
        make_clean_set_and_splits()
        companies_by_split = {
            split: {
                row["company"] or f"__NO_COMPANY__:{row['doc_id']}"
                for row in CLEAN if row.get("split") == split
            }
            for split in ("train", "val", "test")
        }
        COUNTS["train_val_company_overlap"] = len(
            companies_by_split["train"] & companies_by_split["val"]
        )
        COUNTS["train_test_company_overlap"] = len(
            companies_by_split["train"] & companies_by_split["test"]
        )
        COUNTS["val_test_company_overlap"] = len(
            companies_by_split["val"] & companies_by_split["test"]
        )
        quality_text = (OUTPUT / "quality_report.md").read_text(encoding="utf-8")
        quality_patterns = {
            "empty_documents": r"Empty files \(0 decoded characters\): (\d+)",
            "tiny_documents": r"Tiny files \(<5,000 decoded characters\): (\d+)",
            "encoding_problem_documents": r"Files with UTF-8 replacement characters: (\d+)",
            "boilerplate_only_documents": r"Boilerplate-only heuristic matches: (\d+)",
            "non_english_documents": r"Non-English heuristic matches: (\d+)",
        }
        for key, pattern in quality_patterns.items():
            match = re.search(pattern, quality_text)
            if match:
                COUNTS[key] = int(match.group(1))
        make_annotation_sheets()
        write_error_log()
        write_changes()
        write_readme()
        print("\nFINAL COUNTS", json.dumps(COUNTS, sort_keys=True), flush=True)
        return
    run_step("schema", schema_report)
    run_step("metadata", load_metadata)
    run_step("manifest", build_manifest)
    run_step("machine_extractions", read_machine_extractions)
    run_step("annotation_normalization", normalize_annotations)
    run_step("clean_set_and_splits", make_clean_set_and_splits)
    run_step("annotation_sheets", make_annotation_sheets)
    run_step("quality_report", quality_report)
    write_error_log()
    run_step("changes_report", write_changes)
    run_step("readme", write_readme)
    if ERRORS:
        OUTPUT.joinpath("processing_errors.log").write_text(
            "\n".join(ERRORS) + "\n", encoding="utf-8"
        )
    print("\nFINAL COUNTS", json.dumps(COUNTS, sort_keys=True), flush=True)
    if ERRORS:
        print(f"Completed with {len(ERRORS)} error(s); see {OUTPUT / 'processing_errors.log'}", flush=True)
    else:
        print("Completed without logged errors.", flush=True)


if __name__ == "__main__":
    main()
