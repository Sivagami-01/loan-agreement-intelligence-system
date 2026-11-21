# Beginner guide to human loan-contract annotation

This guide helps organize review; it does not make the reviewer a finance or legal expert. Every final annotation must be checked against the original agreement. AI suggestions and quote-presence checks are not approval.

## Before you start

1. Confirm the document ID, version, and source. If an amendment is the assigned document, annotate what that amendment says; do not silently substitute the base agreement.
2. Keep machine predictions and silver suggestions separate from the human decision. Do not copy a suggestion into the gold field without independently checking the contract.
3. Read the full operative sentence or clause and any definitions it relies on. Record a short, exact quote and page/section.
4. Preserve amounts, currency, percentages, dates, limits, and conditions exactly as written. Do not calculate a value the document does not state.

## Key-information fields

- **Parties and title:** Use the title and party roles expressly stated. A lender's agent is not automatically a lender; an affiliate or guarantor is not automatically a borrower.
- **Financial amount versus fee/penalty:** Principal, facility limit, or commitment is the amount advanced or made available. A processing, commitment, legal, or agency charge is a fee. A late charge or increased rate triggered by default is a penalty/default cost. Do not treat acquisition prices, examples, balances, or fees as loan principal.
- **Interest:** Record the contract's fixed rate or the full variable-rate formula, benchmark, spread/margin, and reset terms where stated. Do not calculate a current floating rate using outside market data.
- **Repayment versus prepayment:** Repayment is the scheduled or mandatory return of principal (installments, dates, maturity). Prepayment is an early optional or mandatory payment outside that schedule, including notice, restrictions, premium, and exceptions.
- **Maturity and termination:** Keep final maturity separate from commitment termination or cancellation. Note extensions and conditions. Do not turn a conditional date into a calendar date unless the contract supplies the required facts.
- **Collateral and security:** Identify property or rights actually pledged, charged, or subject to a security interest. A promise not to create liens is a covenant, not itself a grant of collateral.
- **Guarantees:** Record an express guarantee and the guarantor. Do not infer a guarantee from an affiliate relationship, joint liability language, or collateral alone.
- **Default:** Capture the actual event, amount/materiality threshold, notice, cure period, and consequence. A heading or defined term is not enough; find the operative trigger.
- **Covenants:** These are promises or restrictions about conduct, reporting, financial tests, or assets. Quote the exact duty and any threshold, exceptions, and deadline. Do not infer that a breach is an event of default unless the agreement says so or expressly incorporates it.
- **Governing law:** Record the law governing the agreement, not the venue, signing location, or a different referenced document.

### Explicit term, absent term, and cross-reference

- **Explicit:** The contract states the value or obligation in the reviewed document. Quote it and record its page/section.
- **Not present:** After searching the complete reviewed document, the term is not stated. Use the project's `not_present`-style status; leave the value blank. Silence is not permission to infer a customary term.
- **Deferred:** The contract expressly sends the reader to a Note, Schedule, fee letter, security agreement, or other document. Record the exact reference and whether that referenced document was available. If absent, do not fill its value from context.
- **Unclear:** The text conflicts, is incomplete, illegible, or cannot be interpreted safely. Leave the proposed gold value blank, describe the issue, and request a second review or expert adjudication.

## Risk-clause categories

Use the exact categories in [`docs\labeling_guideline.md`](../../../../docs/labeling_guideline.md):

1. `Financial terms`
2. `Repayment`
3. `Penalties and charges`
4. `Collateral`
5. `Default conditions`
6. `Termination`
7. `Covenants`
8. `Other`

The task request refers to seven categories, but the current guideline lists eight, including `Other`. Do not remove, combine, or rename a category without an explicit decision to version the guideline. Select the category that best describes the obligation or consequence in the actual clause; do not treat a category as a legal conclusion.

Use exactly these severity values:

- **Low:** Routine notice or administrative duty, limited direct financial effect, feasible response.
- **Medium:** Meaningful but bounded duty/payment/default trigger, especially with notice, cure period, materiality threshold, or limited scope.
- **High:** Substantial financial, operational, or asset consequences; broad restriction; or significant default/remedy exposure with limited protection.
- **Critical:** Potential immediate loss of the facility or major assets, broad acceleration/termination, or severe insolvency/cross-default consequences affecting the exposure.

Severity is a human assessment in context, not a lookup from the category. Consider scope, trigger, discretion, cure time, amount/exposure, and practical ability to comply. Examples in the guideline calibrate judgment; they are not automatic labels.

## Review confidence, disagreements, and escalation

- Record confidence as a reviewer judgment (for example, `high`, `medium`, `low`) and explain uncertainty; do not treat confidence as evidence.
- Ask for a second reviewer when wording, cross-references, OCR, conditions, or party roles are uncertain. A second review must be independent and recorded.
- If reviewers disagree, preserve both initial values, quotes, and reasons. A designated adjudicator should resolve the disagreement with a rationale; do not overwrite the history.
- Request expert/legal review when the issue needs legal interpretation, ambiguous enforceability, complex financial calculations, or a consequential clause the reviewers cannot confidently classify. Do not claim expert approval unless it is actually obtained and recorded.
- An exact quote verifies only that the words occur in the cited source. It does **not** prove that the selected field, category, or severity is correct.

## Safe handling for evaluation

Once approved, freeze gold labels as read-only evaluation references. Do not use evaluation labels for model training, prompt examples, threshold tuning, or calibration. Split train/development/test by whole document, never by individual clause from the same agreement. Preserve the pre-registered Metric A calculation and report any new method separately. Record dataset version, source hash, guideline version, reviewers, dates, disagreements, and adjudication.
