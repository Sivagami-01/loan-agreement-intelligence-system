from __future__ import annotations

import csv
import hashlib
from pathlib import Path

from crawl_official_pdfs import (
    PDF_DIR,
    REPORT_DIR,
    SOURCES_FILE,
    allowed_https,
    pdf_metadata,
)


OUTPUT = REPORT_DIR / "indian_source_scope.csv"
FIELDS = [
    "filename", "sha256", "source_url", "official_url",
    "in_scope_for_loan_corpus", "document_type", "language", "reason",
]


def sources_by_filename() -> dict[str, str]:
    result = {}
    if not SOURCES_FILE.is_file():
        return result
    for line in SOURCES_FILE.read_text(encoding="utf-8-sig").splitlines():
        fields = line.split("\t")
        if len(fields) >= 2 and not fields[1].casefold().startswith("unknown"):
            result[fields[0]] = fields[1]
    return result


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    sources = sources_by_filename()
    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    rows = []
    for index, path in enumerate(pdfs, 1):
        source_url = sources.get(path.name, "")
        try:
            content = path.read_bytes()
            doc_type, language, eligible = pdf_metadata(
                content, source_url or path.name
            )
            official = allowed_https(source_url) if source_url else ""
            in_scope = eligible and (not source_url or bool(official))
            if source_url and not official:
                reason = "source URL is not HTTPS on an allowlisted lender/RBI domain"
            elif in_scope and source_url:
                reason = "document type verified from PDF title/opening text and official source URL"
            elif in_scope:
                reason = "pre-existing document type verified; original URL not recorded"
            elif source_url:
                reason = (
                    "exploratory crawl PDF outside requested document types; retained "
                    "in raw folder to honor the no-delete rule"
                )
            else:
                reason = "document type could not be verified from title/opening text"
            row = {
                "filename": path.name,
                "sha256": hashlib.sha256(content).hexdigest(),
                "source_url": source_url,
                "official_url": official,
                "in_scope_for_loan_corpus": in_scope,
                "document_type": doc_type,
                "language": language,
                "reason": reason,
            }
        except Exception as exc:
            row = {
                "filename": path.name,
                "sha256": "",
                "source_url": source_url,
                "official_url": "",
                "in_scope_for_loan_corpus": False,
                "document_type": "",
                "language": "",
                "reason": f"scope check failed: {type(exc).__name__}: {exc}",
            }
        rows.append(row)
        print(
            f"[{index}/{len(pdfs)}] {path.name}: "
            f"in_scope={row['in_scope_for_loan_corpus']}; "
            f"type={row['document_type']}; language={row['language']}",
            flush=True,
        )

    temporary = OUTPUT.with_suffix(".csv.tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(OUTPUT)
    valid = sum(bool(row["in_scope_for_loan_corpus"]) for row in rows)
    print(
        f"Scope classification: {valid}/{len(rows)} PDFs in scope; "
        f"report={OUTPUT.relative_to(OUTPUT.parents[1])}",
        flush=True,
    )


if __name__ == "__main__":
    main()
