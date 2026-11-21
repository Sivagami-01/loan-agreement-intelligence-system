from __future__ import annotations

import csv
import html
import re
import zipfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
SHEETS = ROOT / "data" / "processed_v1" / "annotation_sheets"
LABELS = ROOT / "data" / "processed" / "labels"
TEXT_DIR = ROOT / "data" / "friend" / "01_loan_agreements" / "publicly_filed_contracts"
ZIP_PATH = ROOT / "data" / "friend" / "01_loan_agreements" / "publicly_filed_contracts.zip"
FIELDS = SHEETS / "key_info_sheet.csv"
RISK = SHEETS / "risk_clause_sheet.csv"
QA = SHEETS / "qa_sheet.csv"
RISK_CATEGORIES = [
    "financial terms", "repayment", "penalties and charges", "collateral",
    "default conditions", "termination", "covenants", "other",
]
SEVERITIES = ["", "Low", "Medium", "High", "Critical"]
KEYWORDS = {
    "financial terms": r"interest|rate|principal|commitment|amount|fee",
    "repayment": r"repay|payment|installment|instalment|amortiz",
    "penalties and charges": r"penalty|default interest|late charge|fee|charge",
    "collateral": r"collateral|security interest|secured|lien|pledge",
    "default conditions": r"default|bankrupt|insolven|failure to pay|accelerat",
    "termination": r"terminat|matur|expire|commitments have been terminated",
    "covenants": r"covenant|shall not|maintain|undertake|obligation",
}
csv.field_size_limit(20_000_000)


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames or [], list(reader)


def save_rows(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    LABELS.mkdir(parents=True, exist_ok=True)
    output_columns = list(columns)
    if "timestamp" not in output_columns:
        output_columns.append("timestamp")
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=output_columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def load_saved(path: Path, keys: tuple[str, ...]) -> dict[tuple[str, ...], dict[str, str]]:
    if not path.exists():
        return {}
    _, rows = read_rows(path)
    return {tuple(row.get(key, "") for key in keys): row for row in rows}


def timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def normalize_member(value: str) -> str:
    return value.replace("\\", "/").strip("/").casefold()


@st.cache_data(show_spinner=False)
def source_indexes() -> tuple[dict[str, list[str]], dict[str, list[str]], dict[str, list[str]], dict[str, list[str]]]:
    zip_exact: dict[str, list[str]] = defaultdict(list)
    zip_basename: dict[str, list[str]] = defaultdict(list)
    if ZIP_PATH.is_file():
        try:
            with zipfile.ZipFile(ZIP_PATH) as archive:
                for member in archive.namelist():
                    if not member.casefold().endswith(".txt"):
                        continue
                    normalized = normalize_member(member)
                    zip_exact[normalized].append(member)
                    zip_basename[normalized.rsplit("/", 1)[-1]].append(member)
        except (OSError, zipfile.BadZipFile) as exc:
            st.error(f"Cannot index the contract ZIP: {exc}")

    folder_exact: dict[str, list[str]] = defaultdict(list)
    folder_basename: dict[str, list[str]] = defaultdict(list)
    if TEXT_DIR.is_dir():
        for path in TEXT_DIR.rglob("*.txt"):
            relative = path.relative_to(TEXT_DIR).as_posix()
            normalized = normalize_member(relative)
            folder_exact[normalized].append(relative)
            folder_basename[normalized.rsplit("/", 1)[-1]].append(relative)
    return dict(zip_exact), dict(zip_basename), dict(folder_exact), dict(folder_basename)


@st.cache_data(show_spinner=False)
def evidence_quotes(doc_id: str) -> tuple[str, ...]:
    _, rows = read_rows(FIELDS)
    return tuple(
        dict.fromkeys(
            (row.get("evidence_excerpt") or "").strip()
            for row in rows
            if normalize_member(row.get("doc_id", "")) == normalize_member(doc_id)
            and (row.get("evidence_excerpt") or "").strip()
        )
    )


def source_candidate(
    doc_id: str,
    exact: dict[str, list[str]],
    basenames: dict[str, list[str]],
    *,
    is_zip: bool,
    quotes: tuple[str, ...],
) -> tuple[str | None, str, str]:
    normalized_id = normalize_member(doc_id)
    candidates = exact.get(normalized_id, [])
    if len(candidates) == 1:
        return candidates[0], "exact path (case-insensitive)", ""
    if len(candidates) > 1:
        return None, "", "multiple case-insensitive exact-path matches"
    suffix_matches = sorted(
        {
            entry
            for normalized_name, entries in exact.items()
            if normalized_name.endswith("/" + normalized_id)
            for entry in entries
        }
    )
    if len(suffix_matches) == 1:
        return suffix_matches[0], "unique path suffix (prefix ignored)", ""
    if len(suffix_matches) > 1:
        return None, "", "multiple suffix matches"

    basename = normalized_id.rsplit("/", 1)[-1]
    matches = basenames.get(basename, [])
    if not matches:
        return None, "", "no matching path"
    if len(matches) > 1:
        return None, "", f"ambiguous basename ({len(matches)} matches)"
    candidate = matches[0]
    try:
        if is_zip:
            with zipfile.ZipFile(ZIP_PATH) as archive:
                text = archive.read(candidate).decode("utf-8", errors="replace")
        else:
            text = (TEXT_DIR / Path(candidate)).read_text(encoding="utf-8", errors="replace")
    except (OSError, KeyError, zipfile.BadZipFile) as exc:
        return None, "", f"candidate read failed: {type(exc).__name__}: {exc}"
    if not any(quote in text for quote in quotes):
        return None, "", "unique basename rejected: sheet evidence quote not found exactly"
    return candidate, "basename match, verify automatically", ""


@st.cache_data(show_spinner=False)
def resolve_document_source(doc_id: str) -> tuple[str, str, str]:
    zip_exact, zip_basenames, folder_exact, folder_basenames = source_indexes()
    quotes = evidence_quotes(doc_id)
    errors = []
    for label, exact, basenames, is_zip in (
        ("zip", zip_exact, zip_basenames, True),
        ("folder", folder_exact, folder_basenames, False),
    ):
        candidate, how, reason = source_candidate(
            doc_id, exact, basenames, is_zip=is_zip, quotes=quotes
        )
        if candidate:
            return label, candidate, how
        if reason and reason != "no matching path":
            errors.append(f"{label}: {reason}")
    return "", "", "; ".join(errors) or "not found in ZIP or unpacked folder"


@st.cache_data(show_spinner=False)
def document_text(doc_id: str) -> str:
    source, member, reason = resolve_document_source(doc_id)
    if source == "zip":
        try:
            with zipfile.ZipFile(ZIP_PATH) as archive:
                return archive.read(member).decode("utf-8", errors="replace")
        except (OSError, KeyError, zipfile.BadZipFile) as exc:
            st.error(f"Cannot read document {doc_id} from the ZIP: {exc}")
            return ""
    if source == "folder":
        try:
            return (TEXT_DIR / Path(member)).read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            st.error(f"Cannot read document {doc_id} from the unpacked folder: {exc}")
            return ""
    st.warning(f"Document text unavailable for {doc_id}: {reason}.")
    return ""


def highlighted_context(doc_id: str, evidence: str) -> None:
    text = document_text(doc_id)
    if not text:
        st.warning("Document text is unavailable in the ZIP and unpacked contract folder.")
        return
    evidence = evidence or ""
    at = text.find(evidence) if evidence else -1
    if at < 0:
        excerpt = text[:1800]
        st.caption("Evidence was not found verbatim; showing the beginning of the document.")
        st.text_area("Document text", excerpt, height=180, key=f"document_{doc_id}")
        return
    start, end = max(0, at - 600), min(len(text), at + len(evidence) + 600)
    before = html.escape(text[start:at])
    exact = html.escape(text[at:at + len(evidence)])
    after = html.escape(text[at + len(evidence):end])
    st.markdown(
        f'<div style="white-space:pre-wrap;max-height:300px;overflow:auto">'
        f'{before}<mark>{exact}</mark>{after}</div>',
        unsafe_allow_html=True,
    )


def key_fields_tab(docs: list[str]) -> None:
    columns, rows = read_rows(FIELDS)
    if not docs:
        st.info("No documents are available with the current filter.")
        return
    rows = [row for row in rows if row["doc_id"] in set(docs)]
    saved_path = LABELS / "key_info_labeled.csv"
    saved = load_saved(saved_path, ("doc_id", "field_name"))
    total = len(rows)
    done = sum(bool(saved.get((r["doc_id"], r["field_name"]), {}).get("human_status", "").strip()) for r in rows)
    st.progress(done / max(total, 1), text=f"Key fields: {done}/{total} reviewed")
    doc = st.selectbox("Document", docs, key="key_doc")
    for row in (r for r in rows if r["doc_id"] == doc):
        key = (doc, row["field_name"])
        prior = saved.get(key, {})
        st.markdown(f"**{row['field_name']}**")
        st.caption(f"Machine-proposed value: {row.get('machine_candidate_value') or '(none)'}")
        evidence = row.get("evidence_excerpt", "")
        st.caption("Machine-proposed evidence (verify against source):")
        st.code(evidence or "(none)", language=None)
        highlighted_context(doc, evidence)
        with st.form(f"key_{doc}_{row['field_name']}"):
            candidate = row.get("machine_candidate_value", "")
            initial_value = prior.get("human_value", candidate)
            value = st.text_input("Human value (edit only after checking)", value=initial_value, key=f"value_{doc}_{row['field_name']}")
            status = prior.get("human_status", "")
            cols = st.columns(4)
            actions = [
                cols[0].form_submit_button("Correct"),
                cols[1].form_submit_button("Edit"),
                cols[2].form_submit_button("Not present"),
                cols[3].form_submit_button("Unsure"),
            ]
        if any(actions):
            if actions[0]:
                chosen_status, chosen_value = "correct", value
            elif actions[1]:
                chosen_status, chosen_value = "corrected", value
            elif actions[2]:
                chosen_status, chosen_value = "not_present", ""
            else:
                chosen_status, chosen_value = "unsure", ""
            saved[key] = {
                **row, "human_value": chosen_value, "human_status": chosen_status,
                "annotator": prior.get("annotator", ""), "notes": prior.get("notes", ""),
                "timestamp": timestamp(),
            }
            save_rows(saved_path, columns, [saved[k] for k in sorted(saved)])
            st.success(f"Saved {row['field_name']} as {chosen_status}.")
            st.rerun()


def suggested_category(text: str) -> str:
    order = (
        "penalties and charges", "collateral", "default conditions", "repayment",
        "termination", "covenants", "financial terms",
    )
    for category in order:
        pattern = KEYWORDS[category]
        if re.search(pattern, text, re.IGNORECASE):
            return category
    return ""


def risk_tab(docs: list[str]) -> None:
    columns, all_rows = read_rows(RISK)
    if not docs:
        st.info("No documents are available with the current filter.")
        return
    rows = [row for row in all_rows if row["doc_id"] in set(docs)]
    saved_path = LABELS / "risk_labeled.csv"
    saved = load_saved(saved_path, ("doc_id", "clause_id"))
    reviewed = sum(
        all(saved.get((r["doc_id"], r["clause_id"]), {}).get(k, "").strip() for k in ("risk_category", "severity", "rationale"))
        for r in rows
    )
    st.progress(reviewed / max(len(rows), 1), text=f"Risk clauses fully labeled: {reviewed}/{len(rows)}")
    doc = st.selectbox("Document", docs, key="risk_doc")
    current = [r for r in rows if r["doc_id"] == doc]
    current.sort(key=lambda r: (r.get("keyword_hit", "").casefold() != "true", r.get("clause_id", "")))
    st.caption(f"Showing {min(20, len(current))} of {len(current)} clauses; keyword hits first.")
    for row in current[:20]:
        key = (doc, row["clause_id"])
        prior = saved.get(key, {})
        text = row.get("clause_text", "")
        suggestion = suggested_category(text)
        with st.expander(f"{row.get('clause_id', '')} — {row.get('clause_heading', '')[:100]}"):
            st.write(text)
            st.caption(f"Suggested by keyword rule: {suggestion or 'no suggestion'}")
            with st.form(f"risk_{doc}_{row['clause_id']}"):
                category_options = [""] + RISK_CATEGORIES
                prior_category = prior.get("risk_category", "")
                category_index = category_options.index(prior_category) if prior_category in category_options else 0
                category = st.selectbox("Risk category", category_options, index=category_index, key=f"cat_{doc}_{row['clause_id']}")
                prior_severity = prior.get("severity", "")
                severity_index = SEVERITIES.index(prior_severity) if prior_severity in SEVERITIES else 0
                severity = st.selectbox("Severity", SEVERITIES, index=severity_index, key=f"sev_{doc}_{row['clause_id']}")
                rationale = st.text_area("Rationale", value=prior.get("rationale", ""), key=f"rat_{doc}_{row['clause_id']}")
                submitted = st.form_submit_button("Save risk label")
            if submitted:
                saved[key] = {**row, "risk_category": category, "severity": severity, "rationale": rationale,
                              "annotator": prior.get("annotator", ""), "timestamp": timestamp()}
                save_rows(saved_path, columns, [saved[k] for k in sorted(saved)])
                st.success("Risk label saved.")
                st.rerun()


def qa_tab(docs: list[str]) -> None:
    columns, all_rows = read_rows(QA)
    if not docs:
        st.info("No documents are available with the current filter.")
        return
    rows = [row for row in all_rows if row["doc_id"] in set(docs)]
    saved_path = LABELS / "qa_labeled.csv"
    saved = load_saved(saved_path, ("doc_id", "qa_row"))
    occurrence: dict[str, int] = {}
    reviewed = 0
    for row in rows:
        doc_id = row["doc_id"]
        row_index = occurrence.get(doc_id, 0)
        occurrence[doc_id] = row_index + 1
        prior = saved.get((doc_id, str(row_index)), {})
        reviewed += all(prior.get(k, "").strip() for k in ("question", "answer", "supporting_text"))
    st.progress(reviewed / max(len(rows), 1), text=f"Q&A rows complete: {reviewed}/{len(rows)}")
    doc = st.selectbox("Document", docs, key="qa_doc")
    doc_rows = [r for r in rows if r["doc_id"] == doc][:4]
    text = document_text(doc)
    segment_size = 6000
    segments = [text[offset:offset + segment_size] for offset in range(0, len(text), segment_size)] or [""]
    segment_number = st.selectbox(
        "Document text segment", range(1, len(segments) + 1), key=f"qa_segment_{doc}"
    )
    st.text_area(
        "Source document text (select/copy an exact passage)",
        segments[segment_number - 1],
        height=230,
        key=f"qa_source_{doc}_{segment_number}",
    )
    for index, row in enumerate(doc_rows):
        key = (doc, str(index))
        prior = saved.get(key, {})
        st.markdown(f"**Question {index + 1}**")
        with st.form(f"qa_{doc}_{index}"):
            question = st.text_input("Question", value=prior.get("question", ""), key=f"q_{doc}_{index}")
            answer = st.text_area("Answer", value=prior.get("answer", ""), key=f"a_{doc}_{index}")
            selected = st.text_area("Selected text (paste exact passage)", key=f"selection_{doc}_{index}")
            supporting = st.text_area(
                "Supporting text", value=prior.get("supporting_text", ""), key=f"s_{doc}_{index}"
            )
            copy_selection = st.form_submit_button("Copy selected text to supporting text")
            save = st.form_submit_button("Save Q&A")
        if copy_selection or save:
            saved[key] = {
                **row, "qa_row": str(index), "question": question, "answer": answer,
                "supporting_text": selected if copy_selection else supporting, "annotator": prior.get("annotator", ""),
                "timestamp": timestamp(),
            }
            save_rows(saved_path, columns + ["qa_row"], [saved[k] for k in sorted(saved)])
            if copy_selection:
                st.info("Selected exact text copied into the supporting text label.")
            else:
                st.success("Q&A row saved.")
            st.rerun()


def main() -> None:
    st.set_page_config(page_title="Loan Agreement Label Review", layout="wide")
    st.title("Loan Agreement Label Review")
    st.caption("Machine proposals are not gold labels. Human fields stay unlabelled until you explicitly save a choice.")
    _, key_rows = read_rows(FIELDS)
    document_order = list(dict.fromkeys(row["doc_id"] for row in key_rows))
    doc_limit = st.sidebar.number_input(
        "N documents (in sheet order)", min_value=1, max_value=60, value=30, step=1
    )
    only_available = st.sidebar.checkbox("Only documents with available text", value=True)
    candidates = document_order[:int(doc_limit)]
    source_results = {}
    with st.spinner("Checking text availability (ZIP first, unpacked folder fallback)..."):
        for index, doc_id in enumerate(candidates, 1):
            source_results[doc_id] = resolve_document_source(doc_id)
            print(f"[review app] source check {index}/{len(candidates)}: {doc_id}", flush=True)
    available = [
        doc_id for doc_id in candidates
        if source_results[doc_id][0]
    ]
    skipped = [doc_id for doc_id in candidates if not source_results[doc_id][0]]
    st.info(
        f"Documents in range: {len(candidates)}; available: {len(available)}; "
        f"skipped: {len(skipped)}; source preference: ZIP, then unpacked folder."
    )
    if skipped:
        with st.expander("Skipped document IDs and reasons"):
            for doc_id in skipped:
                st.write(f"`{doc_id}` — {source_results[doc_id][2]}")
    docs = available if only_available else candidates
    tabs = st.tabs(["Key fields", "Risk clauses", "Q&A"])
    with tabs[0]:
        key_fields_tab(docs)
    with tabs[1]:
        risk_tab(docs)
    with tabs[2]:
        qa_tab(docs)


if __name__ == "__main__":
    main()
