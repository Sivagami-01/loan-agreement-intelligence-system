# Phase 2 Provisional Gold-Label Handover

**Status:** Provisional candidate reference only. This handover does not approve any record as final Gold, record an independent review, or create an approved dataset.

## Approved owner policy and current provenance state

The five policy decisions in `PHASE2_PROJECT_OWNER_DECISION_RECORD.md` were approved by project owner Shiva on 2026-11-16. They are policy approval only, not final-dataset approval:

- Partial release of the 60 non-UNCLEAR records is **not permitted**. Resolve all four UNCLEAR cases through recorded independent review or expert adjudication before finalization.
- Independent second review is uncertainty-triggered under the annotation guide, not a blanket requirement for every record. Record each required review independently.
- Record one SHA-256 per original source document in versioned provenance metadata. The four source hashes are in `PHASE2_KEY_INFO_SOURCE_PROVENANCE.csv`; dataset version is `PENDING_OWNER_ASSIGNMENT`, and no explicit guideline version is established.
- Each review event requires reviewer identity, actual review date, decision, and rationale at record level. The existing candidate rows do not provide all required provenance; missing reviewer identities and the Muthoot/CITGO row-level dates remain pending.
- AES Ohio remains excluded until its original agreement is available; exclusion does not establish completion of a five-document benchmark.

All 64 records remain `CANDIDATE_NOT_FINAL`. No independent review or adjudication is claimed complete, and no final Gold dataset has been approved or created.

## Candidate dataset

The consolidated candidate contains 64 records across four documents, with 16 fields per document. Every row is marked `CANDIDATE_NOT_FINAL`.

| Document | Document ID | Records |
|---|---|---:|
| DBS | `03_dbs_mitc` | 16 |
| Bajaj Housing Finance | `13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi` | 16 |
| Muthoot Homefin | `09_muthoothomefin_MHIL-MITC` | 16 |
| CITGO | `000101/1011746/0000950129-03-001503_8.txt` | 16 |
| **Total** | **4 documents** | **64** |

Evidence-status totals are:

| Evidence status | Records |
|---|---:|
| EXPLICIT | 32 |
| DEFERRED | 19 |
| NOT_PRESENT | 9 |
| UNCLEAR | 4 |

These are evidence classifications, not independent review or final approval decisions.

## Pending UNCLEAR cases

All four proposed Gold values remain blank. Each corresponding queue entry remains `PENDING`.

- `03_dbs_mitc` - `prepayment_terms`
- `13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi` - `late_payment_or_default_interest`
- `13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi` - `guarantees`
- `09_muthoothomefin_MHIL-MITC` - `prepayment_terms`

No independent second review or expert adjudication is recorded as completed.

## Provisional reference use for Antigravity

Antigravity may use the consolidated candidate dataset as a provisional key-information reference, retaining its `CANDIDATE_NOT_FINAL` status and evidence classifications. Use the queue, adjudication packet, and decision worksheet only to understand which four records remain unresolved and what review is pending. These materials are not completed decisions and must not be used to imply that the UNCLEAR cases have been resolved.

Keep this key-information candidate work separate from the risk-clause Silver-label workflow. No active Antigravity output was inspected or modified for this handover.

## Not final approved Gold

Do not treat the candidate dataset, the per-document candidate CSVs, the queue, the adjudication packet, or the decision worksheet as `KEY_INFO_GOLD_APPROVED.csv` or as final approved Gold. The 64 user-accepted entries record user decisions only. The Phase Status claims no completed independent second review, expert review, or legal approval. The register lists `KEY_INFO_GOLD_APPROVED.csv` as `FUTURE_NOT_CREATED` and `NOT_YET_APPROVED`, requiring human review and evidence, plus independent second review where uncertainty conditions apply.

The register now includes the consolidated `KEY_INFO_GOLD_CANDIDATE_NOT_FINAL.csv` as a provisional, non-approved artifact; its exact location is listed below.

## AES Ohio blocker

AES Ohio is excluded from the 64-record dataset. The Phase Status says its original agreement is not confirmed available in the workspace records and no candidate labels are prepared. Do not infer labels from an amendment. Confirm availability of the original agreement before preparing or including an AES Ohio candidate.

## Conditions before final Gold approval

1. Complete and independently record second review where the annotation guide's uncertainty conditions apply; do not require or claim blanket review of every row.
2. Resolve all four UNCLEAR cases through recorded independent review or expert adjudication before finalization. Keep each proposed value blank unless the review establishes a value from evidence; record the reviewer identity, actual date, decision, and rationale.
3. Complete source follow-up before finalization. Bajaj visual inspection is partial (pages 1–4, 8, 11–12, 16–22, and 25–28); pages 23–24 and any unlisted pages are not claimed as visually checked, and OCR/table-layout caveats remain. For Muthoot, pages 5–7 were not visually inspected; the current viewer did not confirm page 3 or pages 5–7 despite navigation attempts, and the image-based prepayment schedule remains unclear.
4. Resolve the row-level reviewer identity/date provenance gaps. The separate project-owner policy approval does not fill annotation-review provenance.
5. Obtain an explicit finalization decision only after all applicable review, source, and provenance gates pass. Do not create or approve `KEY_INFO_GOLD_APPROVED.csv` while the four UNCLEAR cases or other required gates remain pending.
6. Keep AES Ohio out unless its original agreement is confirmed available and its labels are separately prepared and reviewed.

## Exact file locations

All paths below are under `C:\finalYear\data\processed\labels\human_review_workspace\`.

| Purpose | File |
|---|---|
| Consolidated provisional candidate dataset | `KEY_INFO_GOLD_CANDIDATE_NOT_FINAL.csv` |
| Four-case pending review queue | `PHASE2_UNCLEAR_INDEPENDENT_REVIEW_QUEUE.csv` |
| UNCLEAR adjudication context | `PHASE2_UNCLEAR_ADJUDICATION_PACKET.md` |
| Blank independent-review decision worksheet | `PHASE2_UNCLEAR_INDEPENDENT_REVIEW_DECISIONS.md` |
| Gold-label file register | `GOLD_LABEL_FILE_REGISTER.csv` |
| Current phase status | `GOLD_LABEL_PHASE_STATUS.md` |
| Per-document source hashes and verification notes | `PHASE2_KEY_INFO_SOURCE_PROVENANCE.csv` |
| This handover | `PHASE2_PROVISIONAL_GOLD_HANDOVER.md` |
