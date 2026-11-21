# Loan Agreement Labeling Guideline

## Principles

- Treat each proposed value as a machine suggestion, not a gold label. Verify it against the original text.
- Copy evidence exactly, including punctuation, capitalization, and wording. Do not silently correct OCR or grammar in an evidence quote; record the issue separately.
- Use `not_present` only after checking the relevant document. Use `unclear` when the document is ambiguous or unreadable. Keep the value blank for both. Do not guess.
- Use the agreement as written. Do not infer a fact from business practice, a different document, or external research.
- For a field with several values, include each clearly identified party/term and enough context to distinguish them.

## Key fields

| Field | Definition / what counts | What does not count | Not present / unclear |
|---|---|---|---|
| `document_title` | The title or named type of this document, normally on its first page. | A file name, a table-of-contents heading, or the title of a referenced document. | Blank with `not_present` if no title is stated; use `unclear` if the scan/title is illegible. |
| `agreement_date` | The date the agreement is dated, made, or entered into. Record the stated date as written. | Filing date, effective date of a separate amendment, signature date of an unrelated exhibit. | Distinguish an expressly stated effective date from the agreement date; mark `unclear` if conflicting dates cannot be resolved. |
| `borrowers` | Each entity or person expressly identified as borrower, co-borrower, or borrower party. | Guarantors, affiliates, subsidiaries, or account parties not identified as borrowers. | List all borrowers. Use `unclear` when party roles conflict or cannot be read. |
| `lenders` | Each lender, noteholder, or lending institution identified as a lender under this agreement. | Administrative/servicing agents solely in their agent capacity; lenders named only in an unrelated agreement. | Capture multiple lenders and any stated collective label. Do not substitute the agent for the lender group. |
| `agents` | Administrative, collateral, paying, or other agents expressly appointed by the agreement. | A lender merely acting as lender, counsel, or a broker not appointed as agent. | Identify the role and party where stated; use `unclear` if the role is ambiguous. |
| `loan_or_commitment_amount` | Stated principal, facility amount, commitment, or maximum amount available under this agreement. Include currency and whether the amount is a cap, tranche, or aggregate when specified. | A fee, outstanding balance on a later date, or an amount appearing only in a definition for another agreement. | Do not calculate unstated totals. Mark `unclear` if amounts conflict without a stated controlling amount. |
| `interest_rate` | Regular interest rate, benchmark, margin/spread, fixed/floating terms, and clearly stated method needed to determine the rate. | Default/late-payment interest (use its dedicated field), a rate in an unrelated example, or a market rate not incorporated by reference. | Preserve variable-rate language and reference index; do not calculate a current rate. |
| `repayment_terms` | Principal repayment schedule, installments, payment dates, maturity repayment, and mandatory prepayments that repay principal. | Interest-only payment dates or optional prepayment rights without a required repayment. | Record frequency and amounts if stated; do not derive an amortization schedule. |
| `maturity_termination_date` | Stated maturity date, final due date, or agreement/commitment termination date and any clearly stated extension option. | A date defined only for a separate note, a reporting date, or an amendment’s signing date. | Keep maturity distinct from termination where both exist. Mark `unclear` if trigger/date cannot be determined. |
| `fees` | Origination, commitment, agency, arrangement, closing, transaction, or other expressly payable charges, including how/when payable if stated. | Interest and default interest; penalties may be captured here only if the clause imposes a fee/charge (also label risk as appropriate). | Do not infer fees from market practice. |
| `late_payment_or_default_interest` | Increased interest, default rate, or additional interest/charge triggered by late payment or another default. | Ordinary interest rate without a default trigger. | Capture trigger and rate/amount; mark `unclear` if the trigger or rate is unreadable. |
| `prepayment_terms` | Borrower’s optional or mandatory right/duty to prepay, notice requirements, minimums, timing, premium, and exceptions. | Scheduled installments already captured as repayment terms. | Record whether prepayment is permitted, restricted, or subject to a premium; do not infer a right from silence. |
| `collateral_security` | Property, assets, accounts, or rights pledged/charged; security interest or lien granted; and related perfection/security documents if expressly identified. | A general financial covenant, an unsecured representation, or a lien mentioned only as a prohibited act. | Distinguish actual granted security from a restriction on liens. |
| `guarantees` | A guarantee or guarantor obligation supporting payment/performance, including the guarantor where identified. | Security over assets without a guarantee; an affiliate mentioned without a guarantee undertaking. | Do not infer a guarantee from “joint and several” unless the text creates it. |
| `events_of_default` | Events expressly constituting default, including cure periods, notice requirements, materiality thresholds, and resulting remedies when stated. | Ordinary covenants without a default consequence; a default in a different instrument unless incorporated or made a cross-default. | Capture the trigger and qualifiers; mark `unclear` if the condition or cure period cannot be read. |
| `governing_law` | The jurisdiction whose law governs interpretation/enforcement of this agreement. | Venue, jurisdiction/consent-to-suit, place of signing, or a choice-of-law clause for another document. | Record the named jurisdiction as written. Use `unclear` for conflicting or unreadable terms. |

## Risk categories

Choose the category that best describes the obligation or consequence in the quoted clause. The categories are descriptive, not legal conclusions.

| Category | Use for |
|---|---|
| Financial terms | Amounts, rates, benchmark/margin changes, financial ratios, and financial calculation terms. |
| Repayment | Scheduled or mandatory payment, repayment timing, and prepayment obligations. |
| Penalties and charges | Default interest, late fees, premiums, indemnity costs, and other financial consequences. |
| Collateral | Security interests, liens, collateral maintenance, realization, and guarantees tied to secured exposure. |
| Default conditions | Events of default, cure periods, cross-default, insolvency triggers, and acceleration after default. |
| Termination | Maturity, termination rights, commitment cancellation, and post-termination obligations. |
| Covenants | Affirmative/negative undertakings, financial tests, reporting, and restrictions on conduct. |
| Other | Material provisions not fitting the above, including procedural or governing-law terms. |

## Severity

Severity is a human assessment of the clause's potential impact in context. Consider scope, trigger, discretion, cure period, amount/exposure, and practical ability to comply. These are calibration examples, not automatic labels.

### Consistency rules (R1–R3)

- **R1 (Category)**: Promises about financial ratios, minimum net worth, leverage, reporting, or inspection are `Covenants`. `Financial terms` is only for interest rate, margin, amount, fees, and benchmark terms.
- **R2 (Severity)**: Routine, market-standard clauses (standard negative covenants, default triggers with a cure period, normal cash-waterfall mechanics) are capped at `Medium`. `High` needs at least one of: no or very short cure period, a large or retroactive charge, or strong lender powers over the borrower or collateral. `Critical` needs automatic acceleration or termination without notice, or loss of the main collateral. Default conditions clauses only define the trigger. They are Critical only if the clause itself says the default is automatic and immediate with acceleration or collateral loss; otherwise High at most.
- **R3 (Borrower-protective)**: Borrower-protective clauses (for example, the lender pays the borrower if it delays returning documents) are `Low` and the rationale must start with `"[borrower-protective]"`.
- **R4 (Fees vs interest terms)**: Fees charged to the borrower = `Penalties and charges`; interest rate and rate-reset terms = `Financial terms`.

Verification note: each example quote is checked against the ZIP source first, with the unpacked text folder as fallback; all examples must match character-for-character.

### Low

Routine information/notice or administrative obligations with limited direct financial effect and a feasible response period.

- “promptly after the occurrence thereof, notice of any Default or Event of Default;” — `000070/709283/0000709283-03-000001_5.txt`
- “Borrower will furnish the Bank within a reasonable period of time such” — `000074/749872/0000950152-01-001872_2.txt`

### Medium

Meaningful but bounded duties or payment/default triggers, especially where there is notice, a cure period, materiality threshold, or limited scope.

- “(d) The Borrower or any of its Significant Subsidiaries shall fail to pay any” — `000002/21665/0000950130-02-005479_4.txt`
- “the Borrower shall fail to pay any principal of any Loan or” — `000075/750004/0000922423-04-002111_8.txt`

### High

Substantial financial, operational, or asset consequences; broad restrictions; or default/remedy triggers with significant exposure and limited protection.

- “Create, incur, assume or suffer to exist any Lien upon any of its property, assets or revenues, whether now owned or hereafter acquired, other than the following:” — `000080/801898/0000801898-05-000120_4.txt`
- “any Subsidiary to create, incur or suffer to exist any Lien upon any of its property or assets as security for Indebtedness” — `000000/8063/0000950152-08-004105_2.txt`

### Critical

Potential immediate loss of the facility/major assets, broad acceleration or termination, or severe insolvency/cross-default consequences affecting the whole exposure.

- “(e) Involuntary Insolvency Proceedings. The appointment of a receiver, trustee, custodian or officer performing similar functions for the Borrower or any Subsidiary” — `000000/8063/0000950152-08-004105_2.txt`
- “(g) Cross Default Under Other Agreements. If the Borrowers or any of their Subsidiaries shall (i) default in any payment with respect to any of the Existing Bonds” — `000000/8063/0000950152-08-004105_2.txt`

## Interpretation rules

1. **Amendments:** A document amendment changes only the terms it expressly amends. Record the amendment’s own date separately from the base agreement date. If reviewing a base agreement alone, do not silently substitute later terms; note an amendment reference as context. If reviewing an amendment, quote the amendment and identify the clause it changes.
2. **Definitions versus operative clauses:** A definition explains a term; it is not itself an obligation unless the agreement makes it operative. Label the operative clause and read definitions only as needed to understand its scope. Do not treat a defined “Event of Default” label as an actual trigger without its operative conditions.
3. **Tables of contents:** Use a table of contents only as a navigation aid. Do not treat headings or page references as evidence for field values or risk labels; verify the substantive clause.
4. **Multiple lenders:** Record each lender when identified. Preserve the document’s collective term (for example, “Lenders” or “Required Lenders”) and any voting/agent role; do not collapse the group into the administrative agent.
5. **Evidence:** Every evidence quote must be copied exactly from the source document. Keep it short and sufficient to support the value; include surrounding text only when needed to preserve the condition or qualification. Never create an evidence quote from a summary.
6. **Uncertain text:** If OCR/scan quality prevents exact reading, mark the item `unclear`, keep the proposed/human value blank unless a readable portion is independently supported, and flag the document/page for review.

## Whole-document scan and severity rules (N1, S1–S5 — from finance review, single reviewer)

- **N1 (`none`, non-risk filter — from finance review, single reviewer)**: `none` = pure definitions (UNLESS the definition states a rate, margin, fee, penalty, default trigger, or a repayment amount or date), representations and warranties about corporate status, financial statements or regulatory compliance, closing conditions, further-assurance and perfection mechanics, and headings.
- **S1 (Default remedies — from finance review, single reviewer)**: Standard remedies after an Event of Default (UCC secured-party rights, application of proceeds, attorney-in-fact for insurance claims, the lender's right to perform and charge costs, assignment of the loan by the lender) = `Medium`; `High` only if the lender gets something beyond the pledged asset (other property or guarantees, self-help without notice, sole-discretion choice of remedies across other collateral, joint and several liability across borrowers); `Critical` per `R2`.
- **S2 (Cross-default — from finance review, single reviewer)**: `High` if there is no cure period or it reaches affiliates or other lenders; `Medium` if it needs acceleration of the other debt or a cure period.
- **S3 (Pension / ERISA & regulatory defaults — from finance review, single reviewer)**: Pension (ERISA) and similar regulatory-event defaults with a notice period = `Medium`.
- **S4 (Indemnity — from finance review, single reviewer)**: Broad borrower indemnity = `Covenants` / `High` (precedent `000087` `R10`).
- **S5 (Routine reporting & insurance — from finance review, single reviewer)**: Routine reporting and standard insurance covenants = `Covenants` / `Low`.
