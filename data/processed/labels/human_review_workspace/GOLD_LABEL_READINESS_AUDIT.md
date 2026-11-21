# Gold-label readiness audit

Audit scope: stable documentation, Stage 3a schemas and saved results, and existing annotation files outside the active silver-label output area. No files in `data\processed\labels\llm_assisted` were opened or changed. No API calls were made. The original readiness assessment below is a historical baseline; the dated current-inventory update supersedes it where candidate counts, user decisions, or AES Ohio source availability are concerned. Candidate user acceptance is not final Gold-label approval.

## Current key-information inventory update — 2026-11-16

- Four candidate CSVs are present in the authorized workspace, with their corresponding evidence reports: DBS, Bajaj Housing Finance, Muthoot Homefin, and CITGO. Each contains 16 fields, for 64 entries total. The user accepted all 64 entries (16 per document).
- The CITGO CSV now records literal `human_reviewed=TRUE` for all 16 rows. The other three candidate CSVs also record `human_reviewed=TRUE` for all 48 rows. This records user decisions only; it does not claim independent expert, legal, or second-review approval, and does not create a finalized Gold dataset.
- Evidence statuses across the 64 rows remain EXPLICIT 32, DEFERRED 19, NOT_PRESENT 9, and UNCLEAR 4. These classifications are separate from approval.
- Workspace evidence reports identify the DBS, Bajaj, and Muthoot original PDFs and ingested text as sources reviewed. The CITGO report identifies filing-derived agreement text; no separate PDF/HTML counterpart is reported. This update relies on those workspace records and does not reopen source documents.
- Bajaj visual verification remains outstanding. The Muthoot report says pages 5–7 were not visually inspected; its prepayment schedule remains unclear. No complete visual inspection is claimed.
- AES Ohio remains blocked: the original agreement is not confirmed available in the workspace evidence. Its 16 rows in the blank template are not a prepared candidate batch, and no labels are inferred from an amendment.
- The file register now separately identifies the four user-approved candidate batches and their reports as **not finalized Gold**. `KEY_INFO_GOLD_APPROVED.csv` remains a future, uncreated dataset requiring review and second review. DBS records `second_review_status=NOT_STARTED`; no completed second review is claimed for any batch.
- Phase 1 is complete. The Phase 2 inventory corrections were validated on 2026-11-16; Phase 2 itself remains in progress. Phase 3 remains pending Antigravity's explicit release; restricted active outputs remain unaccessed.

## A. Existing human-reference status

### Approved key-information reference

[`gold_standard_extraction_v1.csv`](../../../friend/04_annotated_data/gold_standard_extraction_v1.csv) contains **27 records across 3 documents**, with 9 shared fields per document:

| Document | Records | KNOWN | UNAVAILABLE_MISSING_SCHEDULE |
|---|---:|---:|---:|
| Brown-Forman — `000001/14693/0000950144-06-011821_2.txt` | 9 | 8 | 1 |
| Caterpillar — `000001/18230/0001104659-11-052126_5.txt` | 9 | 9 | 0 |
| GATX — `000004/40211/0000950123-11-048775_2.txt` | 9 | 9 | 0 |
| **Total** | **27** | **26** | **1** |

Columns: `document_id`, `source_path`, `field`, `gold_value`, `gold_status`, `evidence_quote`, `evidence_location`, reviewer/decision/rationale/date and approval fields, source SHA-256, guide version, adjudication metadata, and prior-prediction fields. Each row has a status and evidence quote; the single blank `gold_value` is paired with `UNAVAILABLE_MISSING_SCHEDULE`, not an unclassified omission.

The file records `APPROVED` and `GOLD_STANDARD_APPROVED` for all 27 rows and states “Lead” review/approval. However, the same rows also contain initial annotation statuses `DRAFT_PENDING_STUDENT_CONFIRMATION` (18) or `STUDENT_DECISION_ACCEPTED_PENDING_LEAD_REVIEW` (9); reviewer identity is “Lead (personal name not recorded),” and verification/adjudication reviewer identities are `NOT_RECORDED`. The cited `Lead_Final_Approval_Record.md` was not found in the inspected documentation locations. **Conclusion:** the dataset is explicitly recorded as human/lead-reviewed and approved, but its reviewer identity and approval evidence are not independently authenticated here; resolve the status-history discrepancy before relying on it as an unquestioned benchmark.

This set covers only 9 of the extractor's 16 fields and is not one of the five Stage 3a live benchmark documents listed below.

### Other human review or proposed labels (not approved gold)

| File | Records / documents | Observed state | Audit treatment |
|---|---:|---|---|
| [`manual_gold_review_initial_3.csv`](../../../friend/04_annotated_data/manual_gold_review_initial_3.csv) | 27 / 3 | Human-value and evidence columns are populated, but all 27 `reviewer_status` values are `needs_review`. | Human-review material, **not approved gold**. |
| [`caterpillar_first_review.csv`](../../../friend/04_annotated_data/caterpillar_first_review.csv) | 13 / 1 | Statuses: 10 `supported`, 2 `partially supported`, 1 `requires more evidence`; notes document some user confirmations. | Partial review record, **not a final approved dataset**. |
| [`loan_agreement_batch_2_review.csv`](../../../friend/04_annotated_data/loan_agreement_batch_2_review.csv) | 72 / 8 | All 72 `proposal_status` values are `PROPOSED_NEEDS_HUMAN_REVIEW`; 45 have `ACCEPTED AS PROPOSED` in `reviewer_decision`, but all `final_approval_status` entries are blank. | Proposed labels with some recorded decisions, **not approved gold**. |
| [`key_fields_template.csv`](../../../friend/04_annotated_data/key_fields_template.csv) | 100 / 100 | Candidate document IDs with blank label fields and `needs_review`. | Queue/template, not annotations. |
| [`clause_annotations_template.csv`](../../../friend/04_annotated_data/clause_annotations_template.csv) | 0 / 0 | Header only. | Blank template. |
| [`qa_evaluation_candidates.csv`](../../../friend/04_annotated_data/qa_evaluation_candidates.csv) | 36 / 3 | Source-backed QA evaluation candidates, separate from extraction and risk labels. | Do not count as key-info or risk gold. |

### Existing silver labels and active-work isolation

The stable report documents 10-document Stage 1 **LLM-assisted key-field silver** output at `data\processed\labels\llm_assisted\key_info_llm.csv`: 160 rows, 10 documents, 133 found, 18 `NOT_PRESENT`, 9 `UNCLEAR`, 142 quotes reported as verified and 0 reported quote failures. These figures are quoted from the stable report and **were not independently rechecked** because the `llm_assisted` area is active and was excluded from inspection. They are AI-assisted silver labels, not human gold. The active risk-clause silver output was not accessed.

No separate, stable silver-label data file outside that active output area was identified in the reviewed sources.

## B. Stage 3a benchmark and required reference fields

[`scripts/test_3a_extract.py`](../../../../scripts/test_3a_extract.py) identifies these five Stage 3a live benchmark documents:

1. `03_dbs_mitc`
2. `13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi`
3. `0000027430-25-000005_aesohio10qex10120250630q2`
4. `09_muthoothomefin_MHIL-MITC`
5. `CITGO (000101/1011746/0000950129-03-001503_8.txt)`

**Historical source-availability finding from the original audit:** all five were listed in the saved Stage 3a report/results; the four shorter documents' page-text files were reported present, and the original publicly filed contract ZIP was reported to contain the identified CITGO member. The original audit generalized that the original source documents were available for review. **Current qualification (2026-11-16):** that historical generalization does not confirm AES Ohio's original agreement. AES remains blocked because its source is not confirmed in the current workspace evidence. The four candidate batches' source qualifications are summarized in the dated update above; no source files were reopened for this update.

The extraction schema in [`config/extract.yaml`](../../../../config/extract.yaml) requires these 16 fields per document (80 review rows total):

`document_title`, `agreement_date`, `borrowers`, `lenders`, `agents`, `loan_or_commitment_amount`, `interest_rate`, `repayment_terms`, `maturity_termination_date`, `fees`, `late_payment_or_default_interest`, `prepayment_terms`, `collateral_security`, `guarantees`, `events_of_default`, `governing_law`.

The benchmark originals are available, but this audit did not establish that any referenced Note, fee Schedule, security instrument, amendment, or other side document is included alongside each agreement. Use `DEFERRED`/`deferral` only when the reviewed contract expressly points elsewhere; record the referenced document and whether it was available. For example, Brown-Forman's existing gold record specifically notes its absent Schedule 2.01 and uses `UNAVAILABLE_MISSING_SCHEDULE`.

The original 80-row template leaves `silver_prediction`, proposed gold values, evidence, and reviewer decisions blank. The four candidate CSVs listed in the dated update are separate review records; no prediction is automatically approved. Existing Stage 3a benchmark results are machine evaluation outputs, not human labels.

## C. Risk-clause review readiness

The existing [`clause_annotations_template.csv`](../../../friend/04_annotated_data/clause_annotations_template.csv) schema is `document_id`, `page_number`, `clause_text`, `clause_type`, `risk_category`, `severity`, `evidence`, `reviewer_notes`, `review_status`; it currently has no data rows.

The user brief says seven categories, but [`docs\labeling_guideline.md`](../../../../docs/labeling_guideline.md) actually defines **eight**: `Financial terms`, `Repayment`, `Penalties and charges`, `Collateral`, `Default conditions`, `Termination`, `Covenants`, and `Other`. The new blank template and guide preserve the guideline's exact eight categories instead of deleting or renaming one. Severity values are exactly `Low`, `Medium`, `High`, and `Critical`. No gold category or severity is prefilled.

Risk-clause review is deferred until the active silver generation is complete and its output is explicitly safe to inspect.

## D. Safe evaluation of future approved gold

- Evaluate the Stage 3a extractor against key-info gold only after an annotation is fully reviewed and approved. Keep its prediction and human reference in separate columns/files and report coverage by field and document.
- Evaluate a risk classifier separately against risk-clause gold using the exact agreed category/severity rubric. Quote existence is a source-integrity check, not proof that the label is correct.
- Keep approved evaluation labels read-only and out of prompt examples, tuning, training, calibration, or feature-selection data.
- Split by **document**, not clause or row, before any tuning. Keep every clause and annotation from a document in one partition to prevent leakage.
- Preserve the pre-registered Metric A rules and prior reported scores unchanged. Any new metric or matching change must be named and reported separately; do not overwrite historical results.
- Record disagreement, each reviewer decision, rationale, evidence, dates, and an independent adjudicator's resolution. Do not claim expert adjudication unless a qualified reviewer actually performs and records it.

## E. Unresolved items and recommended pilot

1. Confirm the existing 27-row gold file's contradictory initial/final status fields and provide the cited approval record or correct its provenance through an authorized process (outside this workspace).
2. Confirm whether the contract-specific Notes/Schedules and amendments are available before marking any referenced term `DEFERRED` versus `UNAVAILABLE`.
3. Resolve the guideline's eight-category taxonomy against the task's “seven categories” wording before conducting risk annotation. Until then, follow the versioned guideline exactly.
4. **Historical recommendation, superseded by the 2026-11-16 inventory update:** begin with the `03_dbs_mitc` pilot and obtain a second independent review before calling labels approved gold. Four candidate batches have since received user-acceptance decisions; no second review or final Gold approval is claimed.
5. Do not begin risk gold review until Antigravity's risk-silver work is complete and the output folder is released for inspection.

At the time of the original readiness assessment, this workspace contained review-ready templates only. As of 2026-11-16, it also contains four user-approved key-information candidate batches (64 entries total), but no finalized approved key-information Gold dataset and no approved risk-clause Gold labels.
