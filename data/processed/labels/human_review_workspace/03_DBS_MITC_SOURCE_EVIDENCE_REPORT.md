# 03_dbs_mitc — HUMAN REVIEW DRAFT source-evidence report

**Status:** Human review draft only. This is not approved Gold Labels and is not legal or expert review.

## Sources checked

- Full two-page ingested text: `data\processed\ingested\03_dbs_mitc.txt` (`[[PAGE 1]]` and `[[PAGE 2]]`).
- Original two-page source PDF: `data\raw\08_indian_bank_loans\03_dbs_mitc.pdf`. Its text was read locally from the PDF; no API or network call was made. The text was checked against the ingested text for the quoted terms.
- The sibling raw-source folder contains no accompanying copy of the specific referenced `Loan Agreement`, `Standard Terms and Conditions For Facilities Against Gold And Gold Ornaments`, `Transaction Documents`, `Repayment Schedule`, or `Schedule of Charges`. The MITC's fees section has the literal placeholder `<<<Link of website to be added>>>>`; it is not a usable link.

Quotes in the worksheet preserve source wording; line-wrap whitespace is normalized for readability. Page references refer to the page markers in the ingested source and the original PDF.

## Field-by-field outcome

| Field | Draft evidence status | Proposed value / evidence summary |
|---|---|---|
| `document_title` | EXPLICIT | Identifies itself as “Most Important Terms and Conditions (MITC).” |
| `agreement_date` | NOT_PRESENT | No execution, effective, publication, or revision date appears in the complete two-page source. |
| `borrowers` | NOT_PRESENT | Generic “Borrower(s)” references and an eligibility statement appear, but no customer/borrower is named. |
| `lenders` | EXPLICIT | DBS Bank is expressly named. |
| `agents` | NOT_PRESENT | No agent is named. |
| `loan_or_commitment_amount` | DEFERRED | No numeric amount; the amount depends on gold/security margin and referenced Loan Agreement/Transaction Documents. |
| `interest_rate` | DEFERRED | Fixed rate is deferred to the Loan Agreement; floating rate is described as RBI Policy Repo Rate-linked, but the applicable customer rate is absent. |
| `repayment_terms` | DEFERRED | Bullet repayment or monthly interest are stated as possible modes; selected mode and schedule/due dates are referred to the Loan Agreement and Repayment Schedule. |
| `maturity_termination_date` | DEFERRED | No date or numeric tenure appears; the Loan Agreement and Repayment Schedule are referenced generally, but are unavailable. |
| `fees` | DEFERRED | The MITC points to the Schedule of Charges; fee values and a usable website address are absent. |
| `late_payment_or_default_interest` | DEFERRED | A penal-charge trigger is stated, but rate/amount is not; charges are linked to the Loan Agreement. |
| `prepayment_terms` | UNCLEAR | Prior approval and full/partial prepayment are stated. The rate/period exception sentence is ambiguous, and applicable charges need clarification. |
| `collateral_security` | EXPLICIT | Gold/gold jewels/gold ornaments deposited with DBS Bank are stated as security. |
| `guarantees` | NOT_PRESENT | No guarantor or guarantee obligation is identified in the complete MITC. |
| `events_of_default` | DEFERRED | The MITC lists example events, but calls them non-exhaustive and points to Clause VI of missing Standard Terms and the Loan Agreement. |
| `governing_law` | NOT_PRESENT | No jurisdiction or governing-law clause appears; a general statement that the Loan Agreement governs is not itself a governing-law term. |

### Direct evidence versus unresolved references

Fields classified `EXPLICIT` with a proposed value: `document_title`, `lenders`, `collateral_security`.

Other fields have relevant direct wording but their requested value is incomplete or cross-referenced: `loan_or_commitment_amount`, `interest_rate`, `repayment_terms`, `maturity_termination_date`, `fees`, `late_payment_or_default_interest`, `prepayment_terms`, and `events_of_default`. Those rows keep the status `DEFERRED` or `UNCLEAR` rather than implying the missing transaction-specific terms are known.

Fields classified `NOT_PRESENT`: `agreement_date`, `borrowers`, `agents`, `guarantees`, and `governing_law`.

The raw folder has another DBS MITC filename, `04_dbs_mitc-ahl.pdf`; it was not treated as one of this document's referenced transaction-specific documents.

## Review boundaries

- `machine_prediction` and all final decision/approval columns in the worksheet are blank.
- Proposed values are confined to wording supported by this MITC; they are not final human decisions.
- No missing value was inferred from customary loan terms or from the separate MITC file.
- A second reviewer should resolve the prepayment exception ambiguity and review all proposed statuses against the original agreement before any labels are approved.
