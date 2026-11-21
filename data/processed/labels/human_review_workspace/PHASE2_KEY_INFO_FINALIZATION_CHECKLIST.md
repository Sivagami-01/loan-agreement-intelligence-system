# Phase 2 Key-Information Gold Finalization Checklist

**Audit date:** 2026-11-16  
**Scope:** Read-only audit of the four key-information candidate batches and the current consolidated candidate dataset. This checklist does not approve any record as final Gold.

## Approved owner decisions implemented — no finalization

The project owner approved the policy decisions recorded in `PHASE2_PROJECT_OWNER_DECISION_RECORD.md` on 2026-11-16. Partial release of the 60 non-UNCLEAR rows is **not permitted**; all four UNCLEAR cases must be resolved by recorded independent review or expert adjudication before finalization, followed by an explicit finalization decision. Second review is **uncertainty-triggered**, not a blanket requirement for every record. Source hashes are recorded once per original document in versioned provenance metadata. Each review event requires reviewer identity, actual date, decision, and rationale at record level. AES Ohio remains excluded until its original agreement is available.

The four original-source SHA-256 values are recorded in `PHASE2_KEY_INFO_SOURCE_PROVENANCE.csv`. Dataset version remains `PENDING_OWNER_ASSIGNMENT`; the guide's version is not explicitly established in the workspace. The 64 candidate rows and all candidate labels remain unchanged and `CANDIDATE_NOT_FINAL`.

## Audit results

### 1. Candidate record total — PASS

The consolidated `KEY_INFO_GOLD_CANDIDATE_NOT_FINAL.csv` contains 64 records across DBS, Bajaj Housing Finance, Muthoot Homefin, and CITGO. All 64 rows have `dataset_status=CANDIDATE_NOT_FINAL`. AES Ohio is not included.

### 2. Fields and uniqueness — PASS

Each document has 16 records. There are four distinct document IDs and 64 unique document-field pairs; no duplicate pairs were found.

### 3. User-acceptance history — PASS

All 64 records have `human_reviewed=TRUE` and an acceptance marker in `reviewer_reason`. The Phase Status records the user's acceptance of all 64 candidate entries. DBS and Bajaj reviewer reasons include user/date attribution; Muthoot and CITGO reasons record `ACCEPT AS WRITTEN` without user/date attribution in each row. This is not independent review or final Gold approval.

### 4. Evidence-status totals — PASS

| Evidence status | Records |
|---|---:|
| EXPLICIT | 32 |
| DEFERRED | 19 |
| NOT_PRESENT | 9 |
| UNCLEAR | 4 |

These are evidence classifications, not approval counts.

### 5. Unresolved UNCLEAR records — PENDING

The four records remain unresolved:

- DBS (`03_dbs_mitc`) — `prepayment_terms`
- Bajaj Housing Finance (`13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi`) — `late_payment_or_default_interest`
- Bajaj Housing Finance (`13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi`) — `guarantees`
- Muthoot Homefin (`09_muthoothomefin_MHIL-MITC`) — `prepayment_terms`

### 6. Blank values and queue state — PASS

All four proposed Gold values remain blank. The four corresponding entries in `PHASE2_UNCLEAR_INDEPENDENT_REVIEW_QUEUE.csv` remain `PENDING`; no reviewer decision is recorded.

### 7. Second review and adjudication — PENDING

No completed second review or adjudication is recorded. DBS has `second_review_status=NOT_STARTED` on all 16 rows; the other 48 candidate rows have blank second-review status. Under the approved owner decision and annotation guide, independent second review is required when the guide's uncertainty conditions apply; it is not required as a blanket step for every record. All four UNCLEAR queue entries remain pending, and no partial Gold release is permitted while they remain unresolved.

### 8. AES Ohio — BLOCKED

The Phase Status says the original agreement is not confirmed available and no candidate labels are prepared. Do not infer labels from an amendment or include AES Ohio until the original agreement is confirmed available.

### 9. Documentation and metadata gaps — PENDING

- The source-provenance manifest records one verified SHA-256 per original source document. The dataset version remains `PENDING_OWNER_ASSIGNMENT`; the guide version is blank because no explicit version is established in the workspace.
- Row-level review-event provenance is incomplete. Reviewer identities are not separately recorded in the four candidate CSVs. The Muthoot and CITGO rows carry `ACCEPT AS WRITTEN` without a row-level review date; the Phase Status and existing records do not supply a date for those row-level events. Do not infer Shiva as the annotator from the separate policy decision record, and do not invent review dates.
- The independent-review queue, adjudication packet, and decision worksheet are preparation/tracking material only. The four UNCLEAR cases remain PENDING, with reviewer decisions blank.
- `KEY_INFO_GOLD_APPROVED.csv` remains `FUTURE_NOT_CREATED` in the register. Its final dataset metadata is therefore not yet recorded.
- Bajaj visual verification is partial: pages 1–4, 8, 11–12, 16–22, and 25–28 were inspected; pages 23–24 and any unlisted pages are not claimed as visually checked. OCR substitutions, bilingual reflow, and table associations remain caveats.
- Muthoot pages 5–7 were not visually inspected. The current PDF viewer continued to display page 1 after page-navigation attempts; the page 3 prepayment schedule was not visually reverified. Its status remains UNCLEAR.

### 10. Conditions before creating `KEY_INFO_GOLD_APPROVED.csv` — PENDING

Do not create the approved dataset until all applicable conditions below are met:

1. Check every final annotation against its original agreement, as required by the guide; resolve source-evidence gaps that affect a label.
2. Complete and independently record second review where the annotation guide's uncertainty conditions apply. Do not require or claim a blanket second review for every record.
3. Complete the four pending UNCLEAR reviews or expert adjudications and record each decision and rationale. Keep any value blank if the evidence remains unresolved; do not infer a value.
4. Record the required final metadata: assigned dataset version, per-document source hashes, guideline version if explicitly established, reviewer identity and actual date for each review event, decisions and rationales, disagreements, and adjudication history.
5. Keep AES Ohio excluded unless and until its original agreement is confirmed available and its labels are reviewed.
6. Resolve row-level reviewer identity/date provenance gaps before sign-off; do not treat policy-decision approval as annotation-review provenance.

## Files inspected

- `KEY_INFO_GOLD_CANDIDATE_NOT_FINAL.csv`
- `03_DBS_MITC_KEY_INFO_HUMAN_REVIEW_DRAFT.csv`
- `13_BAJAJ_MITC_KEY_INFO_HUMAN_REVIEW_DRAFT.csv`
- `09_MUTHOOT_HOMEFIN_KEY_INFO_HUMAN_REVIEW_DRAFT.csv`
- `CITGO_KEY_INFO_HUMAN_REVIEW_DRAFT.csv`
- `PHASE2_UNCLEAR_INDEPENDENT_REVIEW_QUEUE.csv`
- `PHASE2_UNCLEAR_ADJUDICATION_PACKET.md`
- `GOLD_LABEL_FILE_REGISTER.csv`
- `GOLD_LABEL_PHASE_STATUS.md`
- `HUMAN_ANNOTATION_GUIDE.md`

