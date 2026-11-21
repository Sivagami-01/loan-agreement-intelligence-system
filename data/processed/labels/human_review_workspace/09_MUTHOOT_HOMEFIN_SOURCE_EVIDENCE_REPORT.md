# Muthoot Homefin MITC - Key-Information Candidate Evidence Report

**Document ID:** `09_muthoothomefin_MHIL-MITC`  
**Source PDF:** `data\raw\08_indian_bank_loans\09_muthoothomefin_MHIL-MITC.pdf`  
**Text layer:** `data\processed\ingested\09_muthoothomefin_MHIL-MITC.txt`  
**Draft CSV:** `data\processed\labels\human_review_workspace\09_MUTHOOT_HOMEFIN_KEY_INFO_HUMAN_REVIEW_DRAFT.csv`

## Scope and status

This is a user-reviewed and user-approved key-information candidate describing only the seven-page MITC. The user explicitly accepted all 16 proposed values as written, including rows with `EXPLICIT`, `DEFERRED`, `NOT_PRESENT`, and `UNCLEAR` evidence statuses. The CSV records each decision as `ACCEPT AS WRITTEN` and `human_reviewed=TRUE`; its existing `proposed_gold_value` cells are unchanged and serve as the accepted values. This approval does not resolve missing customer-specific or referenced information and does not substitute for the executed customer-specific loan agreement, sanction letter, repayment schedule, or guarantee instrument.

The CSV follows the existing template schema exactly and contains one record per required field. `reviewer_confidence` and `second_review_status` remain blank. No reviewer identity is recorded, and no independent second-review, expert validation, or legal approval is claimed.

## Human approval record

- **Decision:** ACCEPT ALL 16 AS WRITTEN.
- **Rows recorded:** 16 of 16; `reviewer_reason=ACCEPT AS WRITTEN`, `human_reviewed=TRUE`.
- **Evidence statuses:** Preserved as 7 `EXPLICIT`, 6 `DEFERRED`, 2 `NOT_PRESENT`, and 1 `UNCLEAR`. Acceptance does not change or resolve any evidence status.
- **Scope:** This decision applies only to the 16 Muthoot Homefin key-information entries. It is not a second review, expert validation, or legal approval.
- **Other review fields:** `reviewer_confidence` and `second_review_status` remain blank; no reviewer identity is asserted.

## Field inventory

| Field | Evidence status | PDF page(s) | Candidate conclusion |
|---|---|---:|---|
| `document_title` | EXPLICIT | 1 | MITC title; the borrower prompt, sanctioned amount and tenure fields are unfilled, supporting the generic-form qualification |
| `agreement_date` | DEFERRED | 7 | Execution/date field is uncompleted in this copy |
| `borrowers` | DEFERRED | 1, 7 | Generic borrower prompt; no named borrower |
| `lenders` | EXPLICIT | 1 | Muthoot Homefin (India) Ltd. (MHIL) |
| `agents` | NOT_PRESENT | 6 | No contractual loan-agent appointment is stated in this MITC; authorized MHIL recovery representatives may visit for default-related collection/inspection and are not treated as an agent appointment |
| `loan_or_commitment_amount` | DEFERRED | 1 | Amount-in-figures and words fields are blank |
| `interest_rate` | DEFERRED | 1 | Generic rate alternatives and RPLR structure; selected rate/markup is blank |
| `repayment_terms` | EXPLICIT | 1, 6 | Generic EMI, Pre-EMI interest on amounts actually disbursed, EMI composition and NACH/PDC fallback; actual schedule remains customer-specific |
| `maturity_termination_date` | DEFERRED | 1 | Tenure field is blank; no customer-specific maturity date |
| `fees` | EXPLICIT | 2-4 | Fee schedule and representative administrative, statutory, conversion, dishonour, visit, retrieval, enforcement, court, publication, document-delay and cancellation rows quoted; row-layout caveats retained |
| `late_payment_or_default_interest` | EXPLICIT | 2 | Penal charge of 24.00% p.a. on overdue/defaulted amount for the delay period |
| `prepayment_terms` | UNCLEAR | 3 | Image-based schedule and continuation are present, but rates and cell associations were not reliably verified; applicability remains unresolved |
| `collateral_security` | EXPLICIT | 5 | General mortgage security in favor of MHIL; property particulars blank |
| `guarantees` | DEFERRED | 1, 5 | Optional generic guarantor fields, no named/completed guarantor |
| `events_of_default` | EXPLICIT | 6 | MITC describes non-payment, breach, recall, statutory recovery actions and mortgage enforcement; not a complete loan-agreement EOD list |
| `governing_law` | NOT_PRESENT | 6 | No governing-law clause stated in this MITC; the quoted SARFAESI text is contextual statutory-procedure wording, not a choice-of-law clause |

### Evidence-status counts

- **EXPLICIT:** 7
- **DEFERRED:** 6
- **NOT_PRESENT:** 2
- **UNCLEAR:** 1
- **Total:** 16 unique fields

`NOT_PRESENT` means not stated in this MITC only. It does not establish that the term is absent from the complete loan arrangement. `DEFERRED` means customer-specific or referenced material is needed. `UNCLEAR` is used where the available evidence is ambiguous or incomplete.

## Visual and text-layer observations

- **Page 1:** Visually inspected in this correction pass. The title and lender identity are visible. Borrower, application number, amount, tenure and selected interest-rate fields are generic/unfilled. The source sentence on interest capitalization visibly and textually ends "except to the extent"; it is incomplete in the source, not a text-layer omission.
- **Page 2:** Visually inspected in this correction pass. Fee rows 1-6 are visible. Row 1 repeats timing language across columns; row 4's payable-timing cell appears blank. The 24.00% p.a. penal charge is associated with overdue/defaulted amounts. Delayed CERSAI charge creation has separate time bands.
- **Page 3:** Visually inspected in this correction pass. Fee rows 7-12 are visible. Conversion fees are 0.50% of principal outstanding and any undisbursed amount; dishonour is INR 600; technical visit is INR 750 plus applicable taxes; document retrieval is INR 500 plus applicable taxes. Row 12 has embedded image-based schedule tables. Their detailed rates and row/cell applicability are not reliably legible in the available view and are not stated in the CSV.
- **Page 4:** Visually inspected in this correction pass. Rows 13-22 include notice, possession, court filing, order execution, publication, arbitration, cheque-related legal action, Lok Adalat, delayed document/charge-release compensation, and pre-disbursement loan-cancellation expenses.
- **Page 5:** The ingested text layer contains general mortgage-security wording, blank property particulars and generic guarantor prompts. This page was not visually inspected in this correction pass.
- **Page 6:** The ingested text layer contains generic EMI/Pre-EMI mechanics, NACH/PDC wording, overdue recovery procedures and NPA/SMA definitions. These do not identify a borrower-specific repayment schedule. This page was not visually inspected in this correction pass.
- **Page 7:** The ingested text layer contains customer-service/grievance information and borrower acknowledgement/signature prompts, including an uncompleted date field. This page was not visually inspected in this correction pass.

Page-specific quotations in the CSV were checked against the corresponding `[[PAGE n]]` sections in the ingested text layer. Page references were checked against the ordered page markers. PDF pages 1-4 were visually inspected in this correction pass; no visual verification is claimed for pages 5-7.

## Prepayment uncertainty (must be preserved)

Row 12 is an image-based part-prepayment/foreclosure schedule with a continuation on page 3. The text layer does not transcribe the schedule cells. Although page 3 was visually inspected, the available rendering does not allow reliable verification of the rates or cell/row associations. No percentage or condition is asserted in the candidate. Schedule applicability remains unresolved and depends on a legible schedule plus the customer's product, rate type, payment source, sanction date and any amount band.

## Quote and page-reference validation

- The `agents` and `governing_law` fields are `NOT_PRESENT` only within this MITC. Their CSV values now explicitly identify the recovery-representative and SARFAESI quotations as context, not direct evidence of a contractual appointment or governing-law clause.
- Updated quotations for `document_title`, `agents`, `repayment_terms`, `fees`, `prepayment_terms`, `events_of_default` and `governing_law` were checked against the cited page sections in the ingested text. Multi-page fields cite all applicable pages in `page_number`.
- Page markers `[[PAGE 1]]` through `[[PAGE 7]]` are present and ordered in the ingested text.
- Page 3's embedded prepayment schedules are a known text-layer omission. The candidate retains `UNCLEAR` and does not assert schedule percentages or row/cell alignment.
- Fee-table row associations noted as visually ambiguous on pages 2-3 have not been silently normalized.

## Validation checklist

- [x] Exactly 16 records, one per required field; all field names unique.
- [x] CSV header matches the template's 15-column schema exactly.
- [x] Each row has 15 columns; no missing, duplicate, or malformed field records found.
- [x] Supporting quotations and page references checked against the ingested text layer.
- [x] Visual/table-layout limitations are stated.
- [x] Prepayment schedule uncertainty is explicitly preserved.
- [x] No percentages or prepayment cell associations are asserted without reliable evidence.
- [x] All 16 user decisions are recorded as `ACCEPT AS WRITTEN` and `human_reviewed=TRUE`; reviewer confidence and second-review fields remain blank.
- [x] User approval is limited to these 16 entries; no independent expert, legal, or second-review validation is claimed.
- [x] No claim is made that terms absent from this MITC are absent from the complete loan arrangement.

## Batch evidence-traceability corrections

| Field | Correction recorded | Evidence/status result |
|---|---|---|
| `document_title` | Added the generic borrower prompt and blank amount/tenure fields to the title quotation. | Title and generic-form qualification supported; `EXPLICIT` unchanged. |
| `agents` | Clarified that the authorized recovery representatives are not a contractual agent appointment and limited the finding to this MITC; quoted the recovery/inspection context. | `NOT_PRESENT` unchanged; no conclusion about the complete loan arrangement. |
| `repayment_terms` | Added the exact EMI-composition, interest-on-amount-actually-disbursed and NACH/PDC fallback quotations. | Generic mechanics supported; `EXPLICIT` unchanged; no customer-specific schedule inferred. |
| `fees` | Added representative exact fee-row quotations across pages 2-4 and retained row 1/row 4 layout caveats. | Generic fee schedule supported; `EXPLICIT` unchanged; no missing timing or amount inferred. |
| `prepayment_terms` | Removed unverified percentages and row/cell claims; stated that the inspected rendering does not permit reliable mapping. | `UNCLEAR` retained; applicability limitations preserved. |
| `events_of_default` | Added the exact continuation about statutory recovery actions and mortgage enforcement. | MITC-level recovery wording supported; `EXPLICIT` unchanged; not represented as a complete negotiated default clause. |
| `governing_law` | Clarified that the SARFAESI passage concerns statutory recovery procedure, not contractual governing law; scoped the conclusion to this MITC. | `NOT_PRESENT` unchanged; no inference about the complete loan agreement. |

The evidence-traceability corrections above preserve the source evidence and statuses. The user's explicit approval is recorded separately in the Human approval record.

## Remaining unresolved matters

1. Customer-specific borrower, loan amount, selected interest rate, tenure, maturity and execution date.
2. Any named/obligated guarantor and the actual guarantee instrument.
3. Whether a contractual agent exists in the complete loan documents.
4. Prepayment schedule rates and row/cell applicability, including product, rate type, payment source, sanction date and any amount-band conditions.
5. Whether the full executed loan agreement contains a maturity/termination term or governing-law clause not reproduced in this MITC.
6. Inconsistent or incomplete fee-table layout noted for page 2 rows 1 and 4.

## Isolation and side effects

Only the two requested Muthoot workspace files were modified. No source, template, shared documentation, script, configuration, or other project file was modified. No API calls were made. Restricted `data\processed\labels\llm_assisted\` and Antigravity active outputs were not accessed.
