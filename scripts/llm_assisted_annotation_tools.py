from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
import zipfile
from collections import Counter, defaultdict
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ZIP_PATH = ROOT / "data" / "friend" / "01_loan_agreements" / "publicly_filed_contracts.zip"
SHEETS = ROOT / "data" / "processed_v1" / "annotation_sheets"
OUTPUT = ROOT / "data" / "processed" / "labels" / "llm_assisted"
KEY_SHEET = SHEETS / "key_info_sheet.csv"
RISK_SHEET = SHEETS / "risk_clause_sheet.csv"
QA_SHEET = SHEETS / "qa_sheet.csv"
FIELDS = [
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
LABEL_SOURCE = "claude_code_llm_assisted"
MODEL = "unknown model; session tool: Antigravity"
LABEL_DATE = date.today().isoformat()
MIN_CHARS = 30_000
MAX_CHARS = 225_000
MAX_DOCS = 30
csv.field_size_limit(50_000_000)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def norm_doc_id(value: str) -> str:
    return value.replace("\\", "/").lstrip("/")


def member_index(archive: zipfile.ZipFile) -> dict[str, str]:
    return {
        norm_doc_id(name).casefold(): name
        for name in archive.namelist()
        if name.casefold().endswith(".txt")
    }


def resolve_member(doc_id: str, index: dict[str, str]) -> str | None:
    target = norm_doc_id(doc_id).casefold()
    exact = index.get(target)
    if exact:
        return exact
    matches = [member for key, member in index.items() if key.endswith("/" + target)]
    return matches[0] if len(matches) == 1 else None


def load_selected(upper_chars: int = MAX_CHARS, limit: int = MAX_DOCS) -> list[dict[str, Any]]:
    key_rows = read_csv(KEY_SHEET)
    doc_ids = sorted({norm_doc_id(row["doc_id"]) for row in key_rows if row.get("doc_id")})
    selected = []
    with zipfile.ZipFile(ZIP_PATH) as archive:
        index = member_index(archive)
        for doc_id in doc_ids:
            member = resolve_member(doc_id, index)
            if member is None:
                raise FileNotFoundError(f"ZIP member not found uniquely for {doc_id}")
            text = archive.read(member).decode("utf-8", errors="replace")
            if MIN_CHARS <= len(text) <= upper_chars:
                selected.append({
                    "doc_id": doc_id,
                    "member": member,
                    "chars": len(text),
                    "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                })
    return sorted(selected, key=lambda row: (row["chars"], row["doc_id"]))[:limit]


def exact_quote_in_source(quote: str, source: str) -> bool:
    if not quote:
        return False
    if quote in source:
        return True
    normalize = lambda value: re.sub(r"\s+", " ", value).strip()
    return normalize(quote) in normalize(source)


def append_validated_rows(
    filename: str,
    rows: list[dict[str, Any]],
    fields: list[str],
    primary_key: tuple[str, ...],
) -> tuple[int, int]:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / filename
    existing = read_csv(path) if path.is_file() else []
    existing_by_key = {
        tuple(row.get(field, "") for field in primary_key): row
        for row in existing
    }
    seen = {
        key for key, row in existing_by_key.items()
        if row.get("llm_verified", "true").casefold() == "true"
    }
    replace_keys = set(existing_by_key) - seen
    sources = source_texts()
    accepted = []
    rejected = 0
    for row in rows:
        key = tuple(str(row.get(field, "")) for field in primary_key)
        if key in seen:
            continue
        doc_id = norm_doc_id(str(row.get("doc_id", "")))
        quote_fields = [
            field for field in (
                "llm_evidence_quote", "clause_text", "supporting_quote",
                "concise_evidence_quotes", "detailed_evidence_quotes",
            )
            if field in row
        ]
        quote_values = []
        for field in quote_fields:
            raw_quote = str(row.get(field, "")).strip()
            if field.endswith("evidence_quotes"):
                quote_values.extend(item.strip() for item in raw_quote.split(" || ") if item.strip())
            elif raw_quote:
                quote_values.append(raw_quote)
        quotes_valid = all(exact_quote_in_source(quote, sources.get(doc_id, "")) for quote in quote_values)
        value = str(
            row.get("llm_value", row.get("answer", row.get("concise_summary", "")))
        ).strip()
        no_quote_exception = value in {"NOT_PRESENT", "NOT_IN_DOCUMENT"}
        has_quote = bool(quote_values)
        verified = bool(row.get("llm_verified", True)) and quotes_valid and (has_quote or no_quote_exception)
        if not verified:
            row["llm_value"] = ""
            if "answer" in row and value != "NOT_IN_DOCUMENT":
                row["answer"] = ""
            if "risk_category" in row:
                row["risk_category"] = ""
                row["severity"] = ""
                row["rationale"] = ""
            if "concise_summary" in row:
                row["concise_summary"] = ""
                row["detailed_summary"] = ""
            row["llm_verified"] = "false"
            note = str(row.get("note", "")).strip()
            row["note"] = (note + "; " if note else "") + "Value discarded because supporting quote failed source verification."
            rejected += 1
        else:
            row["llm_verified"] = "true"
        row.update({
            "doc_id": doc_id,
            "label_source": LABEL_SOURCE,
            "model": MODEL,
            "date": LABEL_DATE,
            "pass_id": row.get("pass_id", "pass1"),
        })
        accepted.append(row)
        seen.add(key)
    if accepted:
        retained = [
            row for row in existing
            if tuple(row.get(field, "") for field in primary_key) not in replace_keys
        ]
        temporary = path.with_suffix(path.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(retained)
            writer.writerows(accepted)
        temporary.replace(path)
    return len(accepted), rejected


def append_json_rows(json_path: Path) -> None:
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    field_tables = {
        "key_info_llm.csv": (
            ["doc_id", "field_name", "llm_value", "llm_evidence_quote", "llm_location",
             "llm_verified", "note", "label_source", "model", "date", "pass_id"],
            ("doc_id", "field_name"),
        ),
        "risk_llm.csv": (
            ["doc_id", "clause_id", "clause_text", "risk_category", "severity", "rationale",
             "llm_verified", "label_source", "model", "date", "pass_id"],
            ("doc_id", "clause_id"),
        ),
        "qa_llm.csv": (
            ["doc_id", "question", "answer", "supporting_quote", "section", "llm_verified",
             "label_source", "model", "date", "pass_id"],
            ("doc_id", "question"),
        ),
        "summaries_llm.csv": (
            ["doc_id", "concise_summary", "concise_evidence_quotes", "detailed_summary",
             "detailed_evidence_quotes", "llm_verified", "note", "label_source", "model", "date",
             "pass_id"],
            ("doc_id",),
        ),
        "key_info_pass2.csv": (
            ["doc_id", "field_name", "llm_value", "llm_evidence_quote", "llm_location",
             "llm_verified", "note", "label_source", "model", "date", "pass_id"],
            ("doc_id", "field_name"),
        ),
        "risk_pass2.csv": (
            ["doc_id", "clause_id", "clause_text", "risk_category", "severity", "rationale",
             "llm_verified", "label_source", "model", "date", "pass_id"],
            ("doc_id", "clause_id"),
        ),
    }
    for filename, rows in payload.items():
        if filename not in field_tables:
            raise ValueError(f"Unsupported output table: {filename}")
        fields, primary_key = field_tables[filename]
        inserted, rejected = append_validated_rows(filename, rows, fields, primary_key)
        print(f"{filename}: appended {inserted}; quote-verification rejects {rejected}")


def source_texts() -> dict[str, str]:
    key_rows = read_csv(KEY_SHEET)
    doc_ids = sorted({norm_doc_id(row["doc_id"]) for row in key_rows if row.get("doc_id")})
    result = {}
    with zipfile.ZipFile(ZIP_PATH) as archive:
        index = member_index(archive)
        for doc_id in doc_ids:
            member = resolve_member(doc_id, index)
            if member:
                result[doc_id] = archive.read(member).decode("utf-8", errors="replace")
    return result


def batch_inspect(batch_number: int) -> None:
    selected = load_selected()
    start = batch_number * 3
    docs = selected[start : start + 3]
    if not docs:
        raise ValueError(f"No documents in batch {batch_number + 1}")
    keys = read_csv(KEY_SHEET)
    clauses = read_csv(RISK_SHEET)
    with zipfile.ZipFile(ZIP_PATH) as archive:
        index = member_index(archive)
        for doc in docs:
            text = archive.read(doc["member"]).decode("utf-8", errors="replace")
            print(f"\n{'=' * 100}\nDOC {doc['doc_id']} | {doc['chars']} chars | member={doc['member']}")
            print("--- Document opening ---")
            print(text[:1300])
            print("--- Headings / section-like lines ---")
            headings = [
                line.strip() for line in text.splitlines()
                if 2 <= len(line.strip()) <= 160
                and (
                    line.strip().isupper()
                    or re.match(r"^\s*(?:section\s+)?\d+(?:\.\d+)*[.)]?\s+\S", line, re.I)
                )
            ]
            for heading in headings[:60]:
                print(heading)
            print("--- Machine candidates and source evidence (verify, do not trust) ---")
            for row in keys:
                if norm_doc_id(row.get("doc_id", "")) == doc["doc_id"]:
                    print(
                        f"FIELD {row.get('field_name')}: candidate={row.get('machine_candidate_value','')!r}; "
                        f"evidence={row.get('evidence_excerpt','')!r}"
                    )
            print("--- Source-matched risk clauses ---")
            for row in clauses:
                if norm_doc_id(row.get("doc_id", "")) == doc["doc_id"]:
                    clause = row.get("clause_text", "")
                    print(
                        f"CLAUSE {row.get('clause_id')} heading={row.get('clause_heading','')!r} "
                        f"keyword_hit={row.get('keyword_hit','')!r}\n{clause}"
                    )
            print("--- Targeted source contexts ---")
            terms = re.compile(
                r"borrower|lender|agent|principal|commitment|interest rate|maturity|"
                r"repay|prepay|collateral|security interest|guarant|default|governing law|fee|"
                r"effective date|agreement dated",
                re.I,
            )
            seen = set()
            for match in terms.finditer(text):
                begin, end = max(0, match.start() - 230), min(len(text), match.end() + 330)
                key = begin // 900
                if key in seen:
                    continue
                seen.add(key)
                snippet = re.sub(r"[ \t]+", " ", text[begin:end])
                print(f"[offset {begin}:{end}] {snippet}")
                if len(seen) >= 12:
                    break


def batch_inspect_key(batch_number: int) -> None:
    selected = load_selected()
    docs = selected[batch_number * 3 : batch_number * 3 + 3]
    if not docs:
        raise ValueError(f"No documents in batch {batch_number + 1}")
    keys = read_csv(KEY_SHEET)
    with zipfile.ZipFile(ZIP_PATH) as archive:
        index = member_index(archive)
        for doc in docs:
            member = resolve_member(doc["doc_id"], index)
            if member is None:
                raise FileNotFoundError(f"ZIP member not found for {doc['doc_id']}")
            text = archive.read(member).decode("utf-8", errors="replace")
            print(f"\nDOC {doc['doc_id']} | {doc['chars']} chars")
            print("OPENING:", re.sub(r"\s+", " ", text[:950]).strip())
            print("CANDIDATES:")
            for row in keys:
                if norm_doc_id(row.get("doc_id", "")) == doc["doc_id"]:
                    print(
                        f"{row.get('field_name')}: candidate={row.get('machine_candidate_value','')!r}; "
                        f"evidence={row.get('evidence_excerpt','')!r}"
                    )
            print("SOURCE CHECKS:")
            patterns = [
                r"dated as of|dated this|made as of|entered into as of",
                r"Borrower|Borrowers",
                r"Lender|Bank|Administrative Agent|Agent",
                r"commitment|principal amount|aggregate amount",
                r"interest rate|bear interest|Reference Rate|LIBOR",
                r"repay|installment|maturity|expiration date",
                r"fee|charge|premium",
                r"default rate|late payment",
                r"prepay",
                r"collateral|security interest|mortgage",
                r"guarant",
                r"Events? of Default|Event of Default",
                r"governed by|governing law",
            ]
            for pattern in patterns:
                match = re.search(pattern, text, re.I)
                if match:
                    start = max(0, match.start() - 115)
                    end = min(len(text), match.end() + 260)
                    print(f"[{match.start()}] {re.sub(r'[ \\t]+', ' ', text[start:end]).strip()}")


def completed_docs(path: Path, field_key: str) -> set[str]:
    if not path.is_file():
        return set()
    rows = read_csv(path)
    by_doc: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        by_doc[norm_doc_id(row.get("doc_id", ""))].add(row.get(field_key, ""))
    return {
        doc_id for doc_id, values in by_doc.items()
        if field_key != "field_name" or set(FIELDS).issubset(values)
    }


def status() -> None:
    selected = load_selected()
    print(f"Selected {len(selected)} shortest documents in {MIN_CHARS:,}-{MAX_CHARS:,} chars:")
    for rank, row in enumerate(selected, 1):
        print(f"{rank:02d}\t{row['chars']}\t{row['doc_id']}")
    expected_docs = {row["doc_id"] for row in selected}
    for filename, field_key, expected_rows in [
        ("key_info_llm.csv", "field_name", 16),
        ("risk_llm.csv", "clause_id", 0),
        ("qa_llm.csv", "question", 0),
        ("summaries_llm.csv", "doc_id", 1),
        ("key_info_pass2.csv", "field_name", 16),
        ("risk_pass2.csv", "clause_id", 0),
    ]:
        path = OUTPUT / filename
        done = completed_docs(path, field_key)
        print(f"{filename}: complete docs={len(done & expected_docs)}/{len(expected_docs)}")


def validate_rows() -> tuple[list[tuple[str, int, str]], Counter[str]]:
    texts = source_texts()
    failures: list[tuple[str, int, str]] = []
    totals: Counter[str] = Counter()
    for filename, quote_fields in [
        ("key_info_llm.csv", ["llm_evidence_quote"]),
        ("risk_llm.csv", ["clause_text"]),
        ("qa_llm.csv", ["supporting_quote"]),
        ("summaries_llm.csv", ["concise_evidence_quotes", "detailed_evidence_quotes"]),
        ("key_info_pass2.csv", ["llm_evidence_quote"]),
        ("risk_pass2.csv", ["clause_text"]),
    ]:
        path = OUTPUT / filename
        if not path.is_file():
            continue
        rows = read_csv(path)
        for row_number, row in enumerate(rows, 2):
            doc_id = norm_doc_id(row.get("doc_id", ""))
            source = texts.get(doc_id, "")
            for field in quote_fields:
                quote = row.get(field, "").strip()
                value = row.get("llm_value", row.get("answer", ""))
                if field.endswith("evidence_quotes"):
                    quotes = [item.strip() for item in quote.split(" || ") if item.strip()]
                else:
                    quotes = [quote] if quote else []
                if value and value not in {"NOT_PRESENT", "UNCLEAR", "NOT_IN_DOCUMENT"} and not quotes:
                    failures.append((filename, row_number, f"nonempty value has no quote in {field}"))
                    totals["unverified"] += 1
                    continue
                for item in quotes:
                    if not exact_quote_in_source(item, source):
                        failures.append((filename, row_number, f"quote mismatch in {field}"))
                        totals["unverified"] += 1
                    else:
                        totals["verified"] += 1
                if row.get("llm_verified", "true").casefold() == "false" and value:
                    failures.append((filename, row_number, "unverified row retains a value"))
    return failures, totals


def print_metrics() -> None:
    selected = {row["doc_id"] for row in load_selected()}
    for filename in ["key_info_llm.csv", "risk_llm.csv", "qa_llm.csv", "summaries_llm.csv"]:
        path = OUTPUT / filename
        if not path.is_file():
            print(f"{filename}: not created")
            continue
        rows = [row for row in read_csv(path) if norm_doc_id(row.get("doc_id", "")) in selected]
        verified = sum(row.get("llm_verified", "true").casefold() == "true" for row in rows)
        unclear = sum(
            row.get("llm_value", "").strip() == "UNCLEAR"
            or row.get("answer", "").strip() == "UNCLEAR"
            for row in rows
        )
        severity = Counter(row.get("severity", "") for row in rows if row.get("severity"))
        print(
            f"{filename}: rows={len(rows)}, verified={verified}/{len(rows)} "
            f"({verified / max(1, len(rows)):.1%}), UNCLEAR={unclear}/{len(rows)} "
            f"({unclear / max(1, len(rows)):.1%}), severity={dict(severity)}"
        )
    failures, quote_counts = validate_rows()
    print(f"Quote checks: exact-or-whitespace verified={quote_counts['verified']}; failures={len(failures)}")
    for item in failures[:30]:
        print("QUOTE FAILURE:", *item)


def cohen_kappa(first: list[str], second: list[str]) -> float | None:
    if not first or len(first) != len(second):
        return None
    labels = sorted(set(first) | set(second))
    observed = sum(a == b for a, b in zip(first, second)) / len(first)
    expected = sum(
        (first.count(label) / len(first)) * (second.count(label) / len(second))
        for label in labels
    )
    return (observed - expected) / (1 - expected) if expected != 1 else 1.0


def agreement() -> None:
    pass1_key = OUTPUT / "key_info_llm.csv"
    pass2_key = OUTPUT / "key_info_pass2.csv"
    pass1_risk = OUTPUT / "risk_llm.csv"
    pass2_risk = OUTPUT / "risk_pass2.csv"
    key_a = {(norm_doc_id(r["doc_id"]), r["field_name"]): r for r in read_csv(pass1_key)}
    key_b = {(norm_doc_id(r["doc_id"]), r["field_name"]): r for r in read_csv(pass2_key)}
    common = sorted(set(key_a) & set(key_b))
    similarities = [
        SequenceMatcher(
            None,
            key_a[k].get("llm_value", "").casefold(),
            key_b[k].get("llm_value", "").casefold(),
        ).ratio()
        for k in common
    ]
    risk_a = {(norm_doc_id(r["doc_id"]), r["clause_id"]): r for r in read_csv(pass1_risk)}
    risk_b = {(norm_doc_id(r["doc_id"]), r["clause_id"]): r for r in read_csv(pass2_risk)}
    risk_common = sorted(set(risk_a) & set(risk_b))
    severity_a = [risk_a[k].get("severity", "") for k in risk_common]
    severity_b = [risk_b[k].get("severity", "") for k in risk_common]
    kappa = cohen_kappa(severity_a, severity_b)
    report = [
        "# LLM-assisted annotation agreement",
        "",
        "Pass 2 was created from source text independently; pass-1 labels were not used as input.",
        "",
        f"- Key fields compared: {len(common)}.",
        f"- Mean fuzzy string similarity: {sum(similarities) / max(1, len(similarities)):.4f}.",
        f"- Exact field agreement: {sum(a == b for a, b in zip((key_a[k].get('llm_value','') for k in common), (key_b[k].get('llm_value','') for k in common)))}/{len(common)}.",
        f"- Risk clauses compared: {len(risk_common)}.",
        f"- Severity Cohen's kappa: {kappa if kappa is not None else 'unavailable'}.",
        "",
        "Agreement measures consistency between two LLM-assisted passes only; neither pass is human gold.",
    ]
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "agreement_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect and validate LLM-assisted labels.")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--inspect-batch", type=int, help="zero-based batch index; three docs per batch")
    parser.add_argument("--inspect-key-batch", type=int, help="zero-based key-field batch index")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--metrics", action="store_true")
    parser.add_argument("--agreement", action="store_true")
    parser.add_argument("--append-json", type=Path, help="append one manually reviewed batch JSON")
    args = parser.parse_args()
    if args.inspect_batch is not None:
        batch_inspect(args.inspect_batch)
    if args.inspect_key_batch is not None:
        batch_inspect_key(args.inspect_key_batch)
    if args.status:
        status()
    if args.validate:
        failures, counts = validate_rows()
        print(f"Verified quotes: {counts['verified']}; failures: {len(failures)}")
        for failure in failures:
            print("QUOTE FAILURE:", *failure)
        if failures:
            raise SystemExit(1)
    if args.metrics:
        print_metrics()
    if args.agreement:
        agreement()
    if args.append_json is not None:
        append_json_rows(args.append_json)
    if not any((args.status, args.inspect_batch is not None, args.inspect_key_batch is not None, args.validate, args.metrics, args.agreement, args.append_json is not None)):
        parser.print_help()


if __name__ == "__main__":
    main()
