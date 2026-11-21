# 03_dbs_mitc — Final AI Evidence Audit

**Review designation:** AI-assisted review only. This is not independent human approval, legal validation, or finalized Gold labels.

## 1. Document and source

- **Document ID:** `03_dbs_mitc`
- **Source document:** `data\raw\08_indian_bank_loans\03_dbs_mitc.pdf`
- **Document length:** 2 pages.
- **Inputs reviewed:** The existing key-information draft CSV, prior AI-review summary, independent-review worksheet, human annotation guide, and the original PDF, as authorized.

No companion agreement was searched for or obtained. A document described as missing below means it was not supplied as part of this review.

## 2. Review methodology

Each proposed value, evidence status, quote, and page/section was checked against the original PDF locally. PDF line breaks and whitespace were normalized for comparison only; the words in the source quotes were not paraphrased. The original draft contained 20 quoted fragments across 13 field records; one exact reset-date passage was added to the interest-rate evidence and one exact charge-period passage to the penal-charge evidence, for **22 quoted fragments across 13 field records** checked in this audit. Three fields classified `NOT_PRESENT` have no supporting quote because the complete two-page MITC was reviewed and no direct term was located. Each of those rows has a non-empty audit assessment explaining the absence.

The review distinguishes a term expressly stated in this product-level MITC from a customer-specific value deferred to another contract. Generic borrower eligibility was not treated as a named borrower, collateral was not treated as a guarantee, penal charges were not turned into an unstated default-interest rate, and the Events of Default list was not treated as exhaustive.

The CSV preserves the source draft's proposed-value and evidence-status columns in `original_proposed_value` and `original_evidence_status`. `AI_reviewed_value` is a review summary, not a human correction or approval. All human, reviewer, second-review, and final-Gold fields are blank.

## 3. Field-by-field results

| Field | AI-reviewed value/status | Evidence review and recommendation |
|---|---|---|
| `document_title` | “Most Important Terms and Conditions (MITC)” — **EXPLICIT** | Introductory wording on page 1 supports the document identification. Retain as a proposed identification; it is not a separate title heading. |
| `agreement_date` | Blank — **NOT_PRESENT** | No execution, effective, publication, or revision date was identified in the complete two-page MITC. This is scoped to this MITC only. |
| `borrowers` | Blank — **NOT_PRESENT** | “Individual Indian Residents” is a product eligibility description, and “Borrower(s)” is generic. Neither names a customer-specific borrower. |
| `lenders` | “DBS Bank” — **EXPLICIT** | Page 1, Section II names DBS Bank in the statement about the agreement between borrower(s) and DBS Bank. Do not infer a more specific entity or branch. |
| `agents` | Blank — **NOT_PRESENT** | No administrative, facility, or collateral agent is named in the complete MITC. Do not treat the bank as an agent merely because it is named as lender. |
| `loan_or_commitment_amount` | Blank — **DEFERRED** | Page 1, Section VI says the sanctioned amount is subject to gold value and the bank's security margin, but gives no customer-specific amount. Leave unresolved pending the Loan Agreement and Transaction Documents. |
| `interest_rate` | No customer-specific rate — **DEFERRED** | Page 1, Section III says the fixed rate is in the Loan Agreement and describes a floating rate linked to the RBI Policy Repo Rate. It also gives a standard reset-date mechanism. These are product terms, not the particular borrower's applicable rate; do not calculate or infer one. |
| `repayment_terms` | Possible modes: Bullet Repayment or Monthly Interest; selected mode and actual schedule not established — **DEFERRED** | Page 1, Section VII identifies possible modes but refers rates, due dates, and the Repayment Schedule to the Loan Agreement and schedule. Leave actual schedule unresolved. |
| `maturity_termination_date` | Blank — **DEFERRED** | No date or numeric tenure is stated. The document refers to the Loan Agreement and Repayment Schedule; neither gives a value in this MITC. |
| `fees` | Blank — **DEFERRED** | Page 1, Section IV points to the Schedule of Charges. The displayed website address is a placeholder; no fee amount is provided. |
| `late_payment_or_default_interest` | Penal-charge triggers mentioned; amount/calculation not provided, and no separate default-interest rate is stated — **DEFERRED** | Page 1, Section V covers unpaid dues and Material Breach and says charges are over and above applicable charges/interest in the Loan Agreement. It also states charges for a Material Breach run from breach until cure. The amount/calculation is not in this MITC; do not infer a separate rate. |
| `prepayment_terms` | Prior approval and full/partial prepayment stated; charge exception unclear — **UNCLEAR** | Page 2, Section VIII has an exception sentence using “floating/ fixed” and “floating/Fixed” around the fixed period. Preserve the uncertainty pending human clarification and the Loan Agreement. |
| `collateral_security` | Gold/gold jewels/gold ornaments deposited with DBS Bank are stated as security — **EXPLICIT** | Page 2, Section IX expressly describes deposited gold as security for facility obligations. This is collateral, not evidence of a guarantee. Further terms may be in separate financing documents. |
| `guarantees` | Blank — **NOT_PRESENT** | No guarantor or guarantee obligation is identified in the complete MITC. Do not infer a guarantee from the collateral language. |
| `events_of_default` | Examples (a)–(i) are listed, but full set is deferred — **DEFERRED** | The exact list is in Page 2, Section X and begins “include inter alia.” Page 1, Section VI separately points to Clause VI of the Standard Terms for the full description. Treat the list as examples, not exhaustive. |
| `governing_law` | Blank — **NOT_PRESENT** | Page 1 says the facility is governed by the Loan Agreement, but this MITC names no jurisdiction or governing law. The status applies to this MITC only. |

## 4. Evidence and quote verification

- All quoted source fragments included in the audited worksheet were checked against the original PDF. **22 of 22 fragments matched** after whitespace/line-wrap normalization.
- The three `NOT_PRESENT` records without quotes are `agreement_date`, `agents`, and `guarantees`. For each, the full two-page MITC was reviewed and the worksheet records why no direct supporting quote exists.
- Page references were checked against the PDF: Sections I–VII are on page 1; Sections VIII–X are on page 2. The Events of Default examples are specifically on page 2, Section X. Page 1, Section VI contains a separate cross-reference to the fuller Standard Terms.
- A quote matching the PDF verifies textual presence only; it does not itself establish that an extraction interpretation is correct.

## 5. Status meanings

- **EXPLICIT:** The reviewed MITC directly states the proposed information. The status does not establish human approval.
- **NOT_PRESENT:** The information was not stated in this MITC after reviewing both pages. It does not mean the information is absent from the entire loan arrangement.
- **DEFERRED:** The MITC refers to another document or transaction-specific terms for the value; the referenced document was not supplied.
- **UNCLEAR:** The source contains wording that cannot be interpreted confidently for the requested field. Do not resolve by guessing.

## 6. Missing companion documents

The following were not supplied for this review, and their contents were not sought:

- Loan Agreement
- Standard Terms and Conditions for Facilities Against Gold and Gold Ornaments (including the cited Clause VI)
- Repayment Schedule
- Schedule of Charges

The MITC also references Transaction Documents and other financing documents; these were not supplied either.

## 7. Ambiguities and unresolved issues

1. **Prepayment exception:** Page 2's exception about “floating/ fixed” rates and foreclosure after the fixed period is ambiguous. Human review of the governing wording and missing Loan Agreement is required.
2. **Customer-specific values:** Amount, applicable interest rate, repayment mode/schedule, maturity/tenure, and fees cannot be settled from this product-level MITC.
3. **Penal charges:** The MITC describes triggers and a Material Breach charging period but does not state an amount/calculation. It does not support inventing a separate default-interest rate.
4. **Events of Default:** Examples (a)–(i) are introduced by “include inter alia,” and the MITC points to fuller Standard Terms. Do not treat this list as exhaustive.
5. **Fields not present in this MITC:** No customer-specific borrower, agent, guarantee, agreement date, or governing-law jurisdiction is named here.

## 8. Final status counts

Counts are preserved from the original draft; no evidence status was changed:

| AI-reviewed status | Count |
|---|---:|
| EXPLICIT | 3 |
| NOT_PRESENT | 5 |
| DEFERRED | 7 |
| UNCLEAR | 1 |
| **Total** | **16** |

## 9. Limitations and human-validation recommendations

This review covers only the two-page MITC and the specified existing review materials. It cannot establish terms in missing companion documents, resolve the ambiguous prepayment exception, or authenticate any transaction-specific value. A human reviewer should check the proposed field interpretation against the complete applicable contract package, confirm the ambiguous wording, and record a separate decision and rationale. A second independent review remains necessary before any dataset is approved.

## 10. Review status

**AI-assisted review only; not independent human approval, legal validation, or finalized Gold labels.** No human or second-review decision is recorded, and no Gold approval is claimed.

**Second human review status: PENDING.**
