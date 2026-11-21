"""scripts/build_risk_final.py

Builds data/processed/labels/llm_assisted/risk_final.csv by applying all entries
from risk_revisions.csv onto the untouched originals (risk_llm.csv and
risk_indian_llm.csv), keeping original columns plus final_category,
final_severity, revised (true/false), and revision_rule.
"""

from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path
from typing import Any

csv.field_size_limit(2**31 - 1)

ROOT = Path(__file__).resolve().parents[1]
LABELS_DIR = ROOT / "data" / "processed" / "labels" / "llm_assisted"
SOURCE_FILES = ("risk_llm.csv", "risk_indian_llm.csv")
REVISIONS_CSV = LABELS_DIR / "risk_revisions.csv"
FINAL_CSV = LABELS_DIR / "risk_final.csv"

EXPECTED_CATEGORIES = {
    "Financial terms": 20,
    "Covenants": 37,
    "Repayment": 32,
    "Penalties and charges": 35,
    "Collateral": 29,
    "Default conditions": 30,
    "Termination": 26,
}
EXPECTED_SEVERITIES = {
    "Low": 64,
    "Medium": 71,
    "High": 65,
    "Critical": 9,
}
EXPECTED_TOTAL = 209
EXPECTED_R3_COUNT = 8


def _extract_rule_tag(reason: str) -> str:
    txt = (reason or "").strip()
    upper = txt.upper()
    if upper.startswith("REVIEW"):
        return "REVIEW"
    prefix = txt.split(":", 1)[0]
    tags = re.findall(r"\bR[1234]\b", prefix.upper())
    if tags:
        return "+".join(dict.fromkeys(tags))
    tags_any = re.findall(r"\b(?:R[1234]|REVIEW)\b", upper)
    return "+".join(dict.fromkeys(tags_any)) if tags_any else "OTHER"


def _apply_borrower_protective_prefix(rationale: str) -> str:
    text = (rationale or "").strip()
    if text.lower().startswith("[borrower-protective]"):
        # Canonicalize exact lowercase tag case
        return "[borrower-protective]" + text[len("[borrower-protective]") :]
    return f"[borrower-protective] {text}"


def load_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        return list(reader.fieldnames or []), list(reader)


def build_final() -> list[dict[str, str]]:
    base_rows: list[dict[str, str]] = []
    orig_fieldnames: list[str] = []
    by_key: dict[tuple[str, str], dict[str, str]] = {}

    for fn in SOURCE_FILES:
        cols, rows = load_rows(LABELS_DIR / fn)
        if not orig_fieldnames:
            orig_fieldnames = cols
        for r in rows:
            item = dict(r)
            item["final_category"] = item["risk_category"]
            item["final_severity"] = item["severity"]
            item["revised"] = "false"
            item["revision_rule"] = ""
            key = (item["doc_id"], item["clause_id"])
            if key in by_key:
                raise ValueError(f"Duplicate clause key {key} across base files.")
            by_key[key] = item
            base_rows.append(item)

    _, rev_rows = load_rows(REVISIONS_CSV)
    rules_by_key: dict[tuple[str, str], list[str]] = {}

    for rv in rev_rows:
        key = (rv["doc_id"], rv["clause_id"])
        if key not in by_key:
            raise KeyError(f"Revision key not found in base files: {key}")
        row = by_key[key]
        row["final_category"] = rv["new_category"].strip()
        row["final_severity"] = rv["new_severity"].strip()
        row["revised"] = "true"

        tag = _extract_rule_tag(rv["reason"])
        rule_list = rules_by_key.setdefault(key, [])
        if tag not in rule_list:
            rule_list.append(tag)
        row["revision_rule"] = "; ".join(rule_list)

        if "R3" in tag:
            row["rationale"] = _apply_borrower_protective_prefix(row["rationale"])

    out_fields = orig_fieldnames + [
        "final_category",
        "final_severity",
        "revised",
        "revision_rule",
    ]
    FINAL_CSV.parent.mkdir(parents=True, exist_ok=True)
    with FINAL_CSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=out_fields)
        writer.writeheader()
        writer.writerows(base_rows)

    return base_rows


def check_final_counts(rows: list[dict[str, str]] | None = None) -> tuple[bool, dict[str, Any]]:
    if rows is None:
        _, rows = load_rows(FINAL_CSV)
    cat_counts = dict(Counter(r["final_category"] for r in rows))
    sev_counts = dict(Counter(r["final_severity"] for r in rows))
    ok = (
        len(rows) == EXPECTED_TOTAL
        and cat_counts == EXPECTED_CATEGORIES
        and sev_counts == EXPECTED_SEVERITIES
    )
    return ok, {
        "total": len(rows),
        "categories": cat_counts,
        "severities": sev_counts,
        "expected_categories": EXPECTED_CATEGORIES,
        "expected_severities": EXPECTED_SEVERITIES,
    }


def check_r3_rationales() -> tuple[bool, int, list[tuple[str, str]]]:
    _, rev_rows = load_rows(REVISIONS_CSV)
    _, final_rows = load_rows(FINAL_CSV)
    final_map = {(r["doc_id"], r["clause_id"]): r for r in final_rows}

    r3_keys = [
        (r["doc_id"], r["clause_id"])
        for r in rev_rows
        if "R3" in _extract_rule_tag(r["reason"])
    ]
    bad: list[tuple[str, str]] = []
    good = 0
    for key in r3_keys:
        row = final_map.get(key)
        if row and (row.get("rationale") or "").startswith("[borrower-protective]"):
            good += 1
        else:
            bad.append(key)
    ok = (len(r3_keys) == EXPECTED_R3_COUNT) and (good == EXPECTED_R3_COUNT) and not bad
    return ok, good, bad


def main() -> None:
    rows = build_final()
    ok_counts, details = check_final_counts(rows)
    ok_r3, r3_count, r3_bad = check_r3_rationales()

    print(f"Wrote {len(rows)} rows to {FINAL_CSV.relative_to(ROOT)}")
    print(f"Categories: {details['categories']}")
    print(f"Severities: {details['severities']}")
    print(f"Step 0d count check: {'PASS' if ok_counts else 'FAIL'}")
    print(f"Step 0e R3 '[borrower-protective]' rationale check: count={r3_count}/{EXPECTED_R3_COUNT} ({'PASS' if ok_r3 else f'FAIL bad={r3_bad}'})")

    _, ind_rows = load_rows(LABELS_DIR / "risk_indian_llm.csv")
    im10 = [r for r in ind_rows if r["doc_id"] == "03_dbs_mitc" and r["clause_id"] == "IM10"]
    if im10:
        print("\n=== Step 0f FULL clause_text of 03_dbs_mitc IM10 ===")
        print(im10[0]["clause_text"])

    if not (ok_counts and ok_r3):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
