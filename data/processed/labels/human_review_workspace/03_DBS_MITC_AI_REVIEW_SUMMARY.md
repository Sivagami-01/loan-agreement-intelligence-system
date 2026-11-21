# 03_dbs_mitc — AI-assisted review summary

**Review status:** AI-assisted recommendations for human review only. This report does not approve any Gold Labels.

## Document and source

- **Document ID:** `03_dbs_mitc`
- **Source document:** `data\raw\08_indian_bank_loans\03_dbs_mitc.pdf` (two-page DBS Most Important Terms and Conditions for a gold loan).
- **Reviewed draft:** `03_DBS_MITC_KEY_INFO_HUMAN_REVIEW_DRAFT.csv`
- **Reference guidance:** `HUMAN_ANNOTATION_GUIDE.md`

The original PDF was inspected locally. Recommendations below are not independent human decisions.

## Field-by-field AI review

| Field | Proposed value in draft | Evidence status | AI review recommendation | Simple explanation |
|---|---|---|---|---|
| `document_title` | Most Important Terms and Conditions (MITC) | EXPLICIT | Retain as a supported document title; human reviewer should confirm it is the requested title representation. | The document identifies itself as an MITC. |
| `agreement_date` | — | NOT_PRESENT | Keep blank; do not infer a date from the file or related documents. | No agreement, effective, publication, or revision date appears in this MITC. |
| `borrowers` | — | NOT_PRESENT | Keep blank; do not treat a general borrower reference or eligibility group as a named borrower. | This product-level MITC names no customer-specific borrower. |
| `lenders` | DBS Bank | EXPLICIT | Retain as a proposed value, subject to human confirmation of the institution's intended name. | The text identifies DBS Bank in its description of the loan agreement. |
| `agents` | — | NOT_PRESENT | Keep blank unless an agent is identified in the complete reviewed document. | No administrative, facility, or collateral agent is named. |
| `loan_or_commitment_amount` | — | DEFERRED | Leave unresolved pending the Loan Agreement and Transaction Documents. | The amount depends on gold value and the bank's security margin; no numeric amount is given. |
| `interest_rate` | — | DEFERRED | Leave the applicable rate unresolved pending the Loan Agreement and related terms. | Fixed or floating interest is described, but the borrower's rate is not supplied. |
| `repayment_terms` | Possible modes stated: Bullet Repayment or Monthly Interest; this MITC does not establish which mode applies to a particular borrower or the actual repayment schedule. | DEFERRED | Retain only as a statement of possible modes; request the Loan Agreement and Repayment Schedule to establish the selected mode and schedule. | The MITC lists modes but does not say which one applies or give actual dates and amounts. |
| `maturity_termination_date` | — | DEFERRED | Leave unresolved pending the Loan Agreement and Repayment Schedule; do not infer tenure. | No maturity date or numeric loan term is stated here. |
| `fees` | — | DEFERRED | Leave unresolved pending the Schedule of Charges; do not rely on the placeholder website link. | The MITC refers elsewhere for fee amounts and gives no actual fees. |
| `late_payment_or_default_interest` | Penal charges are mentioned for unpaid dues on their due dates or a Material Breach; their amount and calculation are not provided in this MITC. | DEFERRED | Keep the distinction between mentioned penal charges and an unstated rate. Do not infer a separate default-interest rate. | The triggers are described, but the amount or calculation is not. |
| `prepayment_terms` | Prepayment is described as requiring prior DBS Bank approval and may be full or partial; the exception/charge wording needs review. | UNCLEAR | Request human clarification and the Loan Agreement before resolving the charge exception. | The approval and full/partial options are stated, but the exception sentence is ambiguous. |
| `collateral_security` | Gold, gold jewels, or gold ornaments deposited with DBS Bank secure the stated facility obligations. | EXPLICIT | Retain only as a proposed summary of the security wording in this MITC; check whether the task requires the separate security instrument. | The document says deposited gold/gold ornaments secure the facility obligations. |
| `guarantees` | — | NOT_PRESENT | Keep blank; do not infer a guarantee from collateral or borrower references. | No guarantor or guarantee obligation is identified in this MITC. |
| `events_of_default` | The MITC lists examples (a)–(i); see the dedicated list below. | DEFERRED | Treat the examples as partial only. Review the referenced Standard Terms and Loan Agreement before describing the full events. | The MITC says “inter alia” and points to fuller provisions elsewhere. |
| `governing_law` | — | NOT_PRESENT | Keep blank unless an actual governing-law clause is found in the reviewed source. | Saying the facility is governed by the Loan Agreement does not name a governing jurisdiction. |

`—` means the draft's proposed-value cell is blank; no replacement value is suggested here.

## Events of Default examples (a)–(i)

Page 2, Section X, “EVENT(S) OF DEFAULT” lists these examples:

1. **(a) Loan Agreement default or breach:** payment default, breach of a Loan Agreement provision, fraud, misrepresentation, or concealment of material facts.
2. **(b) Borrower financial distress:** death, business failure, insolvency, or reasonable apprehension of insolvency/bankruptcy proceedings.
3. **(c) Defective or questionable assets:** defects in title, ownership challenges, or assets found to be spurious or inferior in quality.
4. **(d) Wilful default or insolvency proceedings:** declaration as a wilful defaulter or initiation of insolvency/bankruptcy proceedings.
5. **(e) Legal impairment or inability to pay:** actions making performance unlawful or the borrower's admitted inability to pay debts when due.
6. **(f) Events under other DBS agreements:** an event of default (or a potential event) under another DBS Bank agreement, or events that could materially adversely affect DBS Bank.
7. **(g) Gold value decline:** reduction in gold-jewel value due to market-price changes.
8. **(h) Legal action against borrower:** statutory notices for attachment, distress, execution, or arrest on theft or robbery charges.
9. **(i) Erroneous gold valuation:** erroneous valuation due to collusion between the gold appraiser and the borrower or related persons.

This is the MITC's listed set of examples, not a conclusion that these are the complete operative events. The MITC says “include inter alia” and refers to Clause VI of the Standard Terms and the Loan Agreement for fuller provisions.

## Unresolved issues

- **Missing Loan Agreement:** Not supplied with the reviewed source; several customer-specific terms and full default provisions refer to it.
- **Missing Standard Terms:** The Standard Terms and Conditions for Facilities Against Gold and Gold Ornaments, including the cited Clause VI, were not supplied.
- **Missing Repayment Schedule:** Not supplied; the selected repayment mode, dates, and actual schedule remain unresolved.
- **Missing Schedule of Charges:** Not supplied; the MITC's website reference is a placeholder rather than a usable URL.
- **Ambiguous prepayment exception wording:** The sentence concerning floating/fixed rates and foreclosure after the fixed period is difficult to interpret; do not resolve it without human clarification and the relevant contract documents.
- **Other referenced materials:** The MITC also refers to Transaction Documents and other financing documents; these were not supplied for this review.

## Status counts

Counts are taken from the 16 draft rows:

| Evidence status | Count |
|---|---:|
| EXPLICIT | 3 |
| NOT_PRESENT | 5 |
| DEFERRED | 7 |
| UNCLEAR | 1 |
| **Total** | **16** |

## Limitations

This is an AI-assisted review summary based on the draft, annotation guide, and original MITC PDF. It is not independent human approval, legal validation, or expert review. It does not establish that the draft's proposed values are correct, and it does not fill any blank field. The referenced transaction documents are unavailable, so some terms cannot be determined from this MITC alone. A human must compare every proposed annotation with the complete applicable agreement before any approval.

## Second review

**Status: PENDING**

No independent second reviewer decision or adjudication is recorded in this report.
