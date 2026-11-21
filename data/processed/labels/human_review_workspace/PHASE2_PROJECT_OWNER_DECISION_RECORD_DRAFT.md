# Phase 2 Project-Owner Decision Record — Draft

**Status:** Draft for owner review only. Every option below is **PROPOSED — NOT APPROVED**. This document does not record an owner decision, establish anyone's authority, approve a candidate, or authorize finalization.

## Owner completion fields

**Project-owner name:** ____________________________________

**Decision date:** ____________________________________

**Authorization confirmation (owner to complete):** ____________________________________

**Overall final approval / authorization:** ____________________________________

## Decisions for owner review

### 1. Partial release of the 60 non-UNCLEAR records

**Proposed option — PROPOSED — NOT APPROVED:** Do not finalize the 60 non-UNCLEAR records as a partial Gold dataset while the four UNCLEAR cases remain pending. Reconsider only after the pending cases have a recorded independent review or adjudication and the owner explicitly decides whether a partial release is permitted.

**Reason:** The decision request quotes the register's requirement, “Human-reviewed with evidence and second review,” and the checklist instruction to “Complete the four pending UNCLEAR reviews or expert adjudications and record each decision and rationale.” The documents do not expressly authorize a 60-record partial release.

**Conditions and limitations:** This is a conservative proposal, not a finding that partial release is prohibited. An owner-approved partial release would need to define how excluded unresolved fields affect dataset completeness. No finalization is authorized by this draft.

**Project-owner decision:** ____________________________________

**Owner name:** ____________________  **Date:** ____________________

### 2. Independent second-review scope

**Proposed option — PROPOSED — NOT APPROVED:** Require independent second review for records where the guide's uncertainty triggers apply, rather than automatically requiring a second reviewer for every record; clarify the register's broader wording before finalization.

**Reason:** The guide says: “Ask for a second reviewer when wording, cross-references, OCR, conditions, or party roles are uncertain. A second review must be independent and recorded.” The register's “Human-reviewed with evidence and second review” wording does not specify whether this is per-row or limited to uncertain records.

**Conditions and limitations:** Do not treat this proposal as an exemption from the register's review gate. The owner must define which uncertainty triggers require review and whether a second-review record is required for every row. No second review is claimed as completed.

**Project-owner decision:** ____________________________________

**Owner name:** ____________________  **Date:** ____________________

### 3. Source SHA-256 granularity

**Proposed option — PROPOSED — NOT APPROVED:** Record one SHA-256 for each source document in the final dataset's provenance metadata or manifest, linked unambiguously to that document and its version.

**Reason:** The guide requires recording “dataset version, source hash, guideline version, reviewers, dates, disagreements, and adjudication,” but does not state whether the source hash is per row, per document, or dataset-level.

**Conditions and limitations:** This proposal treats the source document as the hashed unit; it does not waive source identification or version tracking. The owner must specify the required metadata location and whether row-level hashes are also required by the final schema.

**Project-owner decision:** ____________________________________

**Owner name:** ____________________  **Date:** ____________________

### 4. Reviewer provenance fields and recording location

**Proposed option — PROPOSED — NOT APPROVED:** For each review event, record reviewer name or approved identifier, review date, decision, and rationale at record level. Preserve initial and second-review values, quotations, and reasons when reviewers disagree, and record the adjudicator's decision and rationale. Keep dataset-level reviewer and version metadata as well.

**Reason:** The guide requires a second review to be “independent and recorded,” requires preserving both reviewers' initial values, quotes, and reasons when they disagree, and calls for recording reviewers, dates, disagreements, and adjudication. The decision request notes that the guide does not prescribe a form, field names, or per-row versus dataset-level placement.

**Conditions and limitations:** These fields and their record-level placement are proposals, not established requirements. The owner must confirm required fields and the authoritative recording location. Do not invent reviewer identities, dates, decisions, or rationales.

**Project-owner decision:** ____________________________________

**Owner name:** ____________________  **Date:** ____________________

### 5. AES Ohio exclusion

**Proposed option — PROPOSED — NOT APPROVED:** Keep AES Ohio excluded from the current four-document dataset until its original agreement is confirmed available; prepare and review it separately if the source becomes available.

**Reason:** The decision request records that the original agreement is not confirmed available and quotes the handover: “AES Ohio is excluded from the 64-record dataset.” It also says to confirm the original agreement's availability before preparing or including an AES Ohio candidate.

**Conditions and limitations:** Do not infer labels from an amendment. Exclusion from this candidate dataset does not itself establish that Phase 2 may be declared complete.

**Project-owner decision:** ____________________________________

**Owner name:** ____________________  **Date:** ____________________

## Current unresolved items

The following four cases remain UNCLEAR and pending; their proposed values remain blank:

1. DBS — `03_dbs_mitc` — `prepayment_terms`
2. Bajaj Housing Finance — `13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi` — `late_payment_or_default_interest`
3. Bajaj Housing Finance — `13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi` — `guarantees`
4. Muthoot Homefin — `09_muthoothomefin_MHIL-MITC` — `prepayment_terms`

Outstanding source-verification items identified in the decision request:

- **Bajaj Housing Finance:** Visual verification remains outstanding.
- **Muthoot Homefin:** Pages 5–7 were not visually inspected.

The current 64-row candidate remains provisional and marked `CANDIDATE_NOT_FINAL`; it is not final approved Gold. Nothing in this draft changes a review status or creates or approves a Gold dataset.
