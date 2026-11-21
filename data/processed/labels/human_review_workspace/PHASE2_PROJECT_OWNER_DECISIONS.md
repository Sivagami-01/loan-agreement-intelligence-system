# Phase 2 Project-Owner Decisions

**Purpose:** Record explicit project-owner decisions on the unresolved finalization rules below. This request does not make decisions, approve records, or authorize creation of a final Gold dataset.

## Current candidate status

The handover states: “The consolidated candidate contains 64 records across four documents, with 16 fields per document. Every row is marked `CANDIDATE_NOT_FINAL`.” (`PHASE2_PROVISIONAL_GOLD_HANDOVER.md`, line 7.) It also states that the four UNCLEAR values remain blank and their queue entries remain pending (line 30). Treat this dataset as provisional, not final Gold.

## Decisions requested

For each item, the project owner should enter a decision, any conditions, their name, and the decision date. No selection or decision has been pre-filled.

### 1. Partial release

**Question:** May the 60 non-UNCLEAR records be finalized separately while the four UNCLEAR records remain pending?

**Existing wording**

- Register: “Human-reviewed with evidence and second review” and “Do not create/approve before review and adjudication.” (`GOLD_LABEL_FILE_REGISTER.csv`, line 11.)
- Checklist: “Complete the four pending UNCLEAR reviews or expert adjudications and record each decision and rationale.” (`PHASE2_KEY_INFO_FINALIZATION_CHECKLIST.md`, line 66.)

**Practical consequence:** A “yes” would permit a 60-record final dataset that excludes the four unresolved fields; a “no” would keep finalization blocked until those cases are resolved. Specify whether excluded fields/documents affect dataset completeness.

**Project-owner decision:** ____________________________________

**Conditions / rationale:** ____________________________________

**Owner name:** ____________________  **Date:** ____________________

### 2. Second-review scope

**Question:** Is independent second review required for every record, or only records with uncertainty?

**Existing wording**

- Guide: “Ask for a second reviewer when wording, cross-references, OCR, conditions, or party roles are uncertain. A second review must be independent and recorded.” (`HUMAN_ANNOTATION_GUIDE.md`, line 59.)
- Register: “Human-reviewed with evidence and second review.” (`GOLD_LABEL_FILE_REGISTER.csv`, line 11.)

**Practical consequence:** The guide identifies uncertainty-triggered review; the register does not specify whether its final-dataset requirement applies to every row. The decision determines the required review workload and record-level sign-off.

**Project-owner decision:** [ ] Every record  [ ] Only records with uncertainty  [ ] Other: __________

**Conditions / rationale:** ____________________________________

**Owner name:** ____________________  **Date:** ____________________

### 3. Source-hash granularity

**Question:** Must each row contain its source SHA-256, or is one hash per document in dataset metadata sufficient?

**Existing wording**

- Guide: “Record dataset version, source hash, guideline version, reviewers, dates, disagreements, and adjudication.” (`HUMAN_ANNOTATION_GUIDE.md`, line 66.)
- Checklist: “Record the required final metadata: dataset version, source hash, guideline version, reviewer identities and dates, disagreements, and adjudication.” (`PHASE2_KEY_INFO_FINALIZATION_CHECKLIST.md`, line 67.)

**Practical consequence:** The wording requires a source hash but does not state whether it is per row, per document, or dataset-level. Specify the granularity and where the hash or hashes must be stored.

**Project-owner decision:** [ ] Per row  [ ] Per document  [ ] Dataset-level  [ ] Other: __________

**Required location / rationale:** ____________________________________

**Owner name:** ____________________  **Date:** ____________________

### 4. Reviewer provenance

**Question:** Which reviewer name, date, decision, and rationale fields are mandatory, and where must they be recorded?

**Existing wording**

- Guide: “A second review must be independent and recorded.” (`HUMAN_ANNOTATION_GUIDE.md`, line 59.)
- Guide: “If reviewers disagree, preserve both initial values, quotes, and reasons. A designated adjudicator should resolve the disagreement with a rationale; do not overwrite the history.” (line 60.)
- Guide: “Record dataset version, source hash, guideline version, reviewers, dates, disagreements, and adjudication.” (line 66.)
- Checklist: Muthoot and CITGO rows “do not identify the user or date in each `reviewer_reason`”; it asks to “Confirm whether this is sufficient per-row traceability before finalization.” (`PHASE2_KEY_INFO_FINALIZATION_CHECKLIST.md`, line 55.)

**Practical consequence:** The guide requires reviewer/date and disagreement/adjudication information, but does not prescribe a form, file, field names, or per-row versus dataset-level placement. The decision will define the traceability needed for final sign-off.

**Project-owner decision — required fields and scope:** ______________________________

**Required recording location / rationale:** ______________________________

**Owner name:** ____________________  **Date:** ____________________

### 5. AES Ohio

**Question:** May AES Ohio remain excluded from the current Phase 2 dataset until its original agreement is available?

**Existing wording**

- Phase Status: “Blocked because the original agreement is not confirmed available in the workspace records; no candidate labels are prepared for it.” (`GOLD_LABEL_PHASE_STATUS.md`, line 9.)
- Handover: “AES Ohio is excluded from the 64-record dataset.” It further says: “Confirm availability of the original agreement before preparing or including an AES Ohio candidate.” (`PHASE2_PROVISIONAL_GOLD_HANDOVER.md`, line 53.)
- Checklist: “Keep AES Ohio excluded unless and until its original agreement is confirmed available and its labels are reviewed.” (`PHASE2_KEY_INFO_FINALIZATION_CHECKLIST.md`, line 68.)

**Practical consequence:** Confirm whether AES Ohio remains outside the current dataset while blocked, and whether that exclusion affects Phase 2 completion. No labels should be inferred from an amendment.

**Project-owner decision:** [ ] Exclude until original agreement is available  [ ] Other: __________

**Conditions / rationale:** ____________________________________

**Owner name:** ____________________  **Date:** ____________________

## Pending review and source-verification items

The following four cases remain UNCLEAR, with blank proposed values and pending reviews (`PHASE2_PROVISIONAL_GOLD_HANDOVER.md`, lines 28–35):

1. DBS — `03_dbs_mitc` — `prepayment_terms`
2. Bajaj Housing Finance — `13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi` — `late_payment_or_default_interest`
3. Bajaj Housing Finance — `13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi` — `guarantees`
4. Muthoot Homefin — `09_muthoothomefin_MHIL-MITC` — `prepayment_terms`

Outstanding visual-verification limitations recorded in the workspace:

- **Bajaj Housing Finance:** Visual verification remains outstanding (`GOLD_LABEL_PHASE_STATUS.md`, line 11; `GOLD_LABEL_FILE_REGISTER.csv`, line 14).
- **Muthoot Homefin:** Pages 5–7 were not visually inspected (`GOLD_LABEL_PHASE_STATUS.md`, line 11; `GOLD_LABEL_FILE_REGISTER.csv`, line 15).

No decision in this document resolves these reviews, changes any status, or approves a final dataset.
