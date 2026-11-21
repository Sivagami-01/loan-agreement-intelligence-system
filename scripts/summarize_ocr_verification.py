from __future__ import annotations

import csv
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE_REPORT = ROOT / "data" / "processed" / "page_verification.csv"
INDIAN_PARSED = ROOT / "data" / "processed" / "parsed" / "indian"
PARSED_OCR = ROOT / "data" / "processed" / "parsed_ocr"
OUT = ROOT / "data" / "processed"
THRESHOLD_REPORT = OUT / "threshold_proposal_v2.md"
SUMMARY_REPORT = OUT / "ocr_verification_summary.md"
FLAG_REPORT = OUT / "parser_ocr_flag_crosscheck.csv"
FIELDS = [
    "file", "page", "source_status", "ocr_status", "candidate_for_ocr",
    "machine_verdict",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def value(row: dict[str, str], key: str) -> float | None:
    try:
        return float(row.get(key, ""))
    except (TypeError, ValueError):
        return None


def percentile(numbers: list[float], proportion: float) -> float | None:
    if not numbers:
        return None
    ordered = sorted(numbers)
    position = (len(ordered) - 1) * proportion
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def fmt(value_: float | None, percent: bool = False) -> str:
    if value_ is None:
        return "—"
    return f"{value_:.1%}" if percent else f"{value_:.3f}"


def write_flag_crosscheck(page_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    input_files = {row["file"] for row in page_rows}
    by_page = {
        (row["file"], str(row["page"])): row
        for row in page_rows
    }
    results = []
    for path in sorted(INDIAN_PARSED.glob("*.json")):
        if path.name not in input_files:
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        for page in payload.get("pages", []):
            if not page.get("needs_ocr"):
                continue
            number = str(page.get("page", ""))
            verified = by_page.get((path.name, number), {})
            results.append({
                "file": path.name,
                "page": number,
                "source_status": verified.get("source_status", "MISSING"),
                "ocr_status": verified.get("ocr_status", ""),
                "candidate_for_ocr": verified.get("candidate_for_ocr", ""),
                "machine_verdict": verified.get("machine_verdict", ""),
            })
    with FLAG_REPORT.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(results)
    return results


def count_ocr_pages(folder: Path) -> int:
    count = 0
    if not folder.is_dir():
        return count
    for path in folder.glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        count += len(payload.get("pages", []))
    return count


def main() -> None:
    page_rows = read_csv(PAGE_REPORT)
    if not page_rows:
        raise RuntimeError(f"No OCR page rows found in {PAGE_REPORT}")

    by_file: dict[str, Counter[str]] = defaultdict(Counter)
    by_status: dict[str, list[dict[str, str]]] = defaultdict(list)
    candidates = []
    for row in page_rows:
        by_file[row["file"]][row["source_status"]] += 1
        by_status[row["source_status"]].append(row)
        if row.get("candidate_for_ocr", "").casefold() == "true":
            candidates.append(row)
    hard_bad = read_csv(OUT / "hard_bad_pages.csv")
    failures = read_csv(OUT / "ocr_processing_failures.csv")
    parser_flags = write_flag_crosscheck(page_rows)
    indian_ocr_pages = count_ocr_pages(PARSED_OCR / "indian")
    cuad_ocr_pages = count_ocr_pages(PARSED_OCR / "cuad")

    file_lines = [
        "| Parsed file | Pages | GOOD | SUSPICIOUS | BAD | OCR candidates |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for filename in sorted(by_file):
        counts = by_file[filename]
        candidate_count = sum(
            row["file"] == filename
            and row.get("candidate_for_ocr", "").casefold() == "true"
            for row in page_rows
        )
        total = sum(counts.values())
        file_lines.append(
            f"| `{filename}` | {total} | {counts['GOOD']} | "
            f"{counts['SUSPICIOUS']} | {counts['BAD']} | {candidate_count} |"
        )

    metric_lines = [
        "| Source class | Pages | Source script share p10 / p50 / p90 | "
        "OCR script share p50 | OCR confidence p50 | Similarity p50 | "
        "Word Jaccard p50 |",
        "|---|---:|---|---:|---:|---:|---:|",
    ]
    for status in ("GOOD", "SUSPICIOUS", "BAD"):
        rows = by_status.get(status, [])
        source_shares = [
            item for row in rows
            if (item := value(row, "source_script_share")) is not None
        ]
        ocr_shares = [
            item for row in rows
            if (item := value(row, "ocr_script_share")) is not None
        ]
        confidence = [
            item for row in rows
            if (item := value(row, "ocr_confidence_mean")) is not None
        ]
        similarities = [
            item for row in rows
            if (item := value(row, "sequence_similarity")) is not None
        ]
        jaccards = [
            item for row in rows
            if (item := value(row, "word_jaccard")) is not None
        ]
        metric_lines.append(
            f"| {status} | {len(rows)} | "
            f"{fmt(percentile(source_shares, .10), True)} / "
            f"{fmt(percentile(source_shares, .50), True)} / "
            f"{fmt(percentile(source_shares, .90), True)} | "
            f"{fmt(percentile(ocr_shares, .50), True)} | "
            f"{fmt(percentile(confidence, .50))} | "
            f"{fmt(percentile(similarities, .50), True)} | "
            f"{fmt(percentile(jaccards, .50), True)} |"
        )

    threshold_lines = [
        "# OCR-based threshold reassessment (v2)",
        "",
        "## Active rule",
        "",
        "- Expected-script share below **0.12**: BAD.",
        "- Expected-script share below **0.40**: SUSPICIOUS.",
        "- Non-alphanumeric symbol ratio above **0.45** (at least 30 visible characters): BAD.",
        "- Keep hard corruption rules: fewer than 20 letters, any private-use or replacement "
        "character, any `(cid:...)`, or an 8+ character symbol run is BAD.",
        "",
        "## Evidence from 300-DPI OCR comparison",
        "",
        f"- Pages evaluated: {len(page_rows)}; source classes: "
        f"{sum(len(by_status.get(s, [])) for s in ('GOOD', 'SUSPICIOUS', 'BAD'))}.",
        f"- Hard-rule BAD pages: {len(hard_bad)}; OCR candidate pages: {len(candidates)}.",
        "- Candidate pages are machine triage only. OCR output and the source/OCR metrics are "
        "not human review or gold labels.",
        "",
        *metric_lines,
        "",
        "## Proposal",
        "",
        "**Retain 0.12 / 0.40 / 0.45. Do not adopt the earlier 0.10 / 0.30 / 0.65 trial.** "
        "The OCR comparisons are useful for identifying pages that merit review, but OCR "
        "agreement is not a truth label: a high overlap can preserve the same extraction error, "
        "and a low overlap can result from OCR/layout differences on bilingual tables. No "
        "threshold change is justified without hand-checking the rendered pages against the "
        "PDF images.",
        "",
        "The historical `threshold_proposal.md` is marked superseded; this v2 assessment is "
        "the current recommendation.",
    ]
    THRESHOLD_REPORT.write_text("\n".join(threshold_lines) + "\n", encoding="utf-8")

    planned = 26
    combined_candidates = len(candidates) + cuad_ocr_pages
    report_lines = [
        "# OCR verification summary",
        "",
        f"- Parsed Indian files/pages checked: {len(by_file)} / {len(page_rows)}.",
        f"- Current-rule classes: GOOD={sum(by_file[f]['GOOD'] for f in by_file)}, "
        f"SUSPICIOUS={sum(by_file[f]['SUSPICIOUS'] for f in by_file)}, "
        f"BAD={sum(by_file[f]['BAD'] for f in by_file)}.",
        f"- OCR candidates: {len(candidates)} Indian pages; {len(hard_bad)} are hard-rule BAD.",
        f"- Flagged parser pages cross-checked: {len(parser_flags)}; "
        f"{sum(row['candidate_for_ocr'].casefold() == 'true' for row in parser_flags)} "
        "are OCR candidates under the current rule.",
        f"- OCR results saved: {indian_ocr_pages} candidate Indian pages and "
        f"{cuad_ocr_pages} CUAD pages.",
        f"- OCR failures: {len(failures)}.",
        f"- Planned set: {planned} pages (7 parser-flagged Indian + 19 CUAD). "
        f"Expanded candidate set: {combined_candidates} pages "
        f"({combined_candidates - planned:+d} versus plan).",
        "",
        "## Indian per-file counts",
        "",
        *file_lines,
        "",
        "## Parser-flag cross-check",
        "",
        "| File | Page | Source class | OCR class | Candidate | Machine verdict |",
        "|---|---:|---|---|---|---|",
    ]
    for row in parser_flags:
        report_lines.append(
            f"| `{row['file']}` | {row['page']} | {row['source_status']} | "
            f"{row['ocr_status']} | {row['candidate_for_ocr']} | "
            f"{row['machine_verdict']} |"
        )
    report_lines.extend([
        "",
        f"Detailed page metrics: `{PAGE_REPORT.relative_to(ROOT)}`.",
        f"Candidate list: `{(OUT / 'ocr_candidates.csv').relative_to(ROOT)}`.",
        f"Hard-rule BAD list: `{(OUT / 'hard_bad_pages.csv').relative_to(ROOT)}`.",
        f"Parsed OCR output: `{PARSED_OCR.relative_to(ROOT)}`.",
        f"Threshold recommendation: `{THRESHOLD_REPORT.relative_to(ROOT)}`.",
    ])
    SUMMARY_REPORT.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(
        f"Summary written. Indian pages={len(page_rows)}; "
        f"GOOD={sum(by_file[f]['GOOD'] for f in by_file)}; "
        f"SUSPICIOUS={sum(by_file[f]['SUSPICIOUS'] for f in by_file)}; "
        f"BAD={sum(by_file[f]['BAD'] for f in by_file)}; "
        f"candidates={len(candidates)}; hard BAD={len(hard_bad)}; "
        f"CUAD OCR={cuad_ocr_pages}; failures={len(failures)}.",
        flush=True,
    )


if __name__ == "__main__":
    main()
