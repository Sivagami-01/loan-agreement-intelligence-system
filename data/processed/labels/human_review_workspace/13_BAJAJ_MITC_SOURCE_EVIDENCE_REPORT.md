# Bajaj Housing Finance MITC — AI-Assisted Source Evidence Report

**Status: USER-APPROVED — all 16 candidate entries approved as written by the user on 2026-11-16. This records the user's decision; it is not independent expert/legal validation or second-review approval, and does not by itself finalize Gold Labels.**

## Scope and method

- Document ID: `13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi`
- Read-only sources: `data\raw\08_indian_bank_loans\13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi.pdf` and `data\processed\ingested\13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi.txt`.
- The 15 CSV columns follow `KEY_INFO_HUMAN_REVIEW_TEMPLATE.csv`. Since that schema has no dedicated `evidence_status` column, each CSV `reviewer_reason` begins with `AI-assisted draft; evidence_status=...`. `gold_status` is `PENDING_REVIEW` and is a workflow state, not an evidence status. Machine/silver predictions, reviewer confidence, human review and second-review fields are left blank.
- The prior evidence review compared PDF wording and page references against the PDF text layer. The quotation corrections recorded here use the permitted ingested text for the loan-amount and loan-tenure form fields, and omit the unverified blank-rate formula rather than reconstructing it. This was text inspection, not visual verification or legal review.
- The ingested text has 29 `[[PAGE n]]` markers in order. It is not a fully faithful transcription: the first-page opening phrase is garbled in the ingested text, and the interest tables on pages 2–3 are reflowed. For example, the PDF text reads “agreed to between” while the ingested text reads “90660 to between”. The blank-rate formula fragment did not match exactly after whitespace normalization and is omitted from the candidate quote. Other selected key passages were present in their ingested page blocks. Hindi extraction contains OCR-like substitutions and fragmented words. The PDF remains the evidence source where the two differ.
- This MITC is a general product-level form. Blank fields, alternative checkboxes, charge bands and examples are not customer-specific values. No companion Loan Agreement, Sanction Letter, repayment schedule, or Schedule of Charges was supplied.

## Field-by-field draft findings

### 1. `document_title` — EXPLICIT
- **Proposed value:** MOST IMPORTANT TERMS AND CONDITIONS (MITC)
- **Source:** Page 1, title.
- **Quote:** “MOST IMPORTANT TERMS AND CONDITIONS (MITC)”
- **Reason / caveat:** The English title is clear. The accompanying Hindi heading is extraction-degraded. This identifies the product-level MITC, not an executed customer agreement.

### 2. `agreement_date` — NOT_PRESENT
- **Proposed value:** None.
- **Source:** Pages 1–29, document-wide absence check.
- **Quote:** None; no date statement or date-specific cross-reference was found in this MITC.
- **Reason / caveat:** No agreement or execution date is stated in this MITC. Page 1's general references to transaction documents do not establish that a date is recorded in any of them. `NOT_PRESENT` is limited to this MITC and does not mean the complete loan arrangement lacks a date.

### 3. `borrowers` — EXPLICIT
- **Proposed value:** Generic Borrower/Customer and Borrower(s)/Co-Borrower(s); no customer-specific identity is completed.
- **Source:** Page 1, opening paragraph; page 29, execution provisions.
- **Quotes:** “between BAJAJ HOUSING FINANCE LIMITED (“BHFL” or “the Lender”) and the Borrower (“the Borrower” or “the Customer”)” / “the Borrower and all Co-Borrowers agree to be bound by such terms and conditions contained in the MITC in relation to the Loan”
- **Reason / caveat:** The opening definition and page 29 electronic execution wording support generic Borrower and Co-Borrower roles. The form does not identify a particular borrower's name; role labels are not customer identities.

### 4. `lenders` — EXPLICIT
- **Proposed value:** Bajaj Housing Finance Limited (BHFL), identified as the Lender.
- **Source:** Page 1, opening paragraph.
- **Quote:** “BAJAJ HOUSING FINANCE LIMITED (“BHFL” or “the Lender”)”
- **Reason / caveat:** The institution is expressly identified.

### 5. `agents` — EXPLICIT
- **Proposed value:** The Lender may take possession of Property on which Security is created, itself or through recovery agents or attorneys it appoints; no individual agent is identified.
- **Source:** Page 12, Section 10, recovery of overdues (continuation).
- **Quote:** “Take possession of the Property, if any, on which Security is so created whether by itself or through any of the recovery agents or attorneys as may be appointed by the Lender.”
- **Reason / caveat:** This is a general remedy concerning property on which security is created. The MITC does not name a recovery agent or attorney for an individual loan.

### 6. `loan_or_commitment_amount` — DEFERRED
- **Proposed value:** None.
- **Source:** Page 1, Loan Amount form field.
- **Quote:** “१. LOANAMOUNT / लोन राशि: _.___.__.____”
- **Reason / caveat:** The amount field is blank. Fee percentages and sanctioned-amount bands elsewhere do not establish this borrower's amount. The Hindi label is degraded in the PDF text layer.
- **Dependency:** Sanction Letter and Loan Agreement.

### 7. `interest_rate` — DEFERRED
- **Proposed value:** The form lists floating, fixed and dual-rate alternatives. Floating rates are described by benchmark plus spread; the applicable benchmark/rate fields and rate type are blank or unselected. No customer-specific rate is supplied.
- **Source:** Pages 2–4, Section 3, Interest Type and interest-rate revision/conversion terms.
- **Quotes:** “Floating Rate of Interest” / “Fixed rate of Interest” / “Dual Rate Loan” / “BHFL FRR / बीएचएफएि एफआरआर + Spread / स्प्रेड = Applicable Floating Rate of Interest / िागू फ्िोटटिंग ब्याज दर” / “The Borrower agrees that the Annualized Rate of Interest shall be computed basis the applicable BHFL FRR and/or Sambhav FRR and/or REBLR applicable on date of commencement of Floating Rate Tenure.” / “the applicable fixed Annualized Rate of Interest shall be 200 bps i.e. 2% (two per cent) per annum higher than the floating Annualized Rate of Interest applicable prior to the conversion.”
- **Reason / caveat:** Pages 2–3 show alternatives, benchmark-plus-spread formulas and blank rate fields; page 3 says the applicable benchmark is set at commencement of the Floating Rate Tenure, and page 4 describes rate revision/conversion. No checkbox or customer-specific rate is completed. Table layout is reflowed in the ingested text, so retain the alternatives and blanks rather than choosing a rate.
- **Dependency:** Sanction Letter and Loan Agreement.

### 8. `repayment_terms` — EXPLICIT
- **Proposed value:** General terms require EMIs/monthly instalments and other outstanding dues by due dates; each instalment comprises principal and interest within the loan tenure. The individual tenure is blank, and the actual repayment mode and system-generated schedule are loan-specific/not supplied.
- **Source:** Page 2, EMI note; page 5, Section 4, Loan Tenure; page 10, Section 9, Repayment of the Loan.
- **Quotes:** “A system generated repayment schedule of the loan will be shared separately.” / “4. LOAN TENURE/ लोि की अवथध: ____ months / िहीने” / “The Borrower agrees to repay the EMIs/Monthly Instalments and the other Outstanding Dues to BHFL on or before the respective Due Dates by any of the repayment modes as set out in the Loan Agreement or the Top-Up Loan Addendum” / “The EMI/Monthly Instalment amount shall be arrived at so as to comprise the repayment of the Loan Amount and payment of Interest calculated on the basis of the Interest Rate within the Loan Tenure.”
- **Reason / caveat:** The general due-date obligation and principal/interest composition are explicit. Page 5 tenure is a blank form field; the actual EMI, selected mode and individual repayment schedule are not supplied and should not be inferred.
- **Dependency:** Loan Agreement, Top-Up Loan Addendum and separate repayment schedule.

### 9. `maturity_termination_date` — DEFERRED
- **Proposed value:** None.
- **Source:** Page 5, Section 4, Loan Tenure.
- **Quote:** “4. LOAN TENURE/ लोन की अवधि: ____ months / महीने”
- **Reason / caveat:** The tenure is blank; no customer-specific maturity or termination date is stated. Do not infer a duration.
- **Dependency:** Sanction Letter, Loan Agreement and repayment schedule.

### 10. `fees` — EXPLICIT
- **Proposed value:** Conditional fee schedule examples: processing up to 4% of loan amount plus GST for Home Loan/LAP, Top-Up and Unsecured Loans; switch fees up to 2% of principal outstanding plus GST; secured-loan Mortgage Origination Fee up to Rs. 10,000 plus GST; legal/technical fee Rs. 5,000 plus GST; fixed-to-floating conversion up to 3% on stated principal/undisbursed or Flexi Limit bases; floating-to-fixed conversion up to 1% on stated bases; Flexi processing up to 2%; Flexi maintenance up to 1% on stated tenure-specific bases. Separate conditional CPC examples apply monthly to specified non-compliance/product categories. These are schedule examples, not customer-specific charges.
- **Source:** Page 16, Section 16 rows 1–3; pages 17–20, fee/conversion/Flexi rows; page 21, conditional IMGC fee; pages 23–25, CPC schedule.
- **Quotes:** “The Fees/Charges as mentioned below are indicative of the maximum amount payable as such Fee/Charge by the Borrower. The Fees/Charges as mentioned in the Loan Documents detail the exact amount payable.” / “Fees for Home Loan/ Loan Against Property” / “Fees for Top-Up Loan” / “Fees for Unsecured Loan” / “Up to 4% of loan amount + GST as applicable” / “Up to 2% of principal outstanding + GST as applicable” / “Up to Rs. 10000 + GST as applicable” / “Rs 5,000 + GST as applicable” / “For Term Loans:- Up to 3% + GST as applicable of principal outstanding + undisbursed amount (if any).” / “For Flexi Term Loans or Flexi Hybrid Loans:- Up to 3% + GST as applicable on Flexi Limit + undisbursed amount (if any).” / “For Term Loans:- Up to 1% + GST as applicable of principal outstanding + undisbursed amount (if any).” / “Up to 2% of loan amount + GST as applicable” / “Up to 1% of the available Flexi Loan Limit + GST as applicable” / “Below mentioned fee / charge is applicable for cases where Mortgage Guarantee will be availed from India Mortgage Guarantee Company (IMGC).” / “At Actuals (Up to 1.70% of loan amount) + GST as applicable” / “Non-adherence to any terms and conditions, representations, warranties, covenants as defined in the Loan Agreement or Sanction Letter or on occurrence of any Event of Default” / “90 days from first disburse ment date” / “Home Loan (HL)/Loan Against Property (LAP)” / “3,000/-” / “Top Up/ Unsecured” / “500/-” / “The Charges mentioned above are as applicable on the date of signing this MITC. These charges are subject to modification”
- **Reason / caveat:** Pages 16–18: processing fees up to 4% for the listed loan types; switch fees up to 2% of principal outstanding; secured-loan MOF up to Rs. 10,000; legal/technical fee Rs. 5,000 for property valuation/title search/encumbrance certificate; and fixed-to-floating conversion up to 3% on the stated Term Loan or Flexi bases. Pages 19–20: floating-to-fixed conversion up to 1% on the corresponding bases, Flexi processing up to 2% of loan amount, and Flexi maintenance up to 1% on the stated tenure-specific base. Page 21's Mortgage Guarantee fee is conditional on obtaining a mortgage guarantee from IMGC (up to 1.70% of loan amount plus GST), not proof of a personal guarantor. Pages 23–25 list CPC separately; the cited non-adherence/Event of Default row is conditional and lists Rs. 3,000 for HL/LAP and Rs. 500 for Top-Up/Unsecured after 90 days from first disbursement. The table notes charges apply as of MITC signing and may change. The PDF text layer wraps the CPC trigger word across lines as “disburse” / “ment”; the visual table should be checked by the human reviewer. These are examples, not selected borrower-specific charges. Exact charges and current applicability depend on Loan Documents and the latest Schedule of Charges; flattened tables require human verification.
- **Dependency:** Loan Documents and latest Schedule of Charges.

### 11. `late_payment_or_default_interest` — UNCLEAR
- **Proposed value:** The MITC separates several items: Section 10 refers to interest on delayed payment; page 26 states compounded interest on an unpaid instalment at the applicable loan rate from due date to remediation; LPC and Bounce Charges are separately listed penal charges. For loans sanctioned on/after July 1, 2026, the page 22 table shows LPC of Rs. 3–Rs. 4,000 per day by sanctioned-amount band and product, and bounce charges of Rs. 500–Rs. 10,000 per dishonour. Earlier sanctions are referred to executed Loan Documents. The LPC start timing is unclear because page 21 says calculation starts from the unpaid/partially-paid EMI date, while page 22 says the table charge is per day from 31st DPD.
- **Source:** Page 11, Section 10; page 21, Section 25, Penal Charges; page 22, dated LPC/Bounce table; page 23, earlier-sanction reference; pages 25–26, charge exclusions; page 26, Section 26, Delayed Payment Interest.
- **Quotes:** “Charge interest on delayed payment, applicable Penal Charges including Bounce Charges, Late Payment Charges & Covenant Perfection Charges.” / “Late Payment Charges (LPC)- calculated daily for each EMI starting from the date of Unpaid / Partially paid EMI till full due EMI amount has been received, as mentioned in below table.” / “Sanctioned Loan Amount (For loans sanctioned on or after July 01, 2026)” / “Late Payment Charges (LPC)^ (chargeable per day from 31st DPD (Days Past Due) for every partially or fully overdue EMI)” / “Bounce Charges ^ (for every dishonour of cheque / ECS / NACH)” / “For Bounce and LPC Charges applicable to loans sanctioned till June 30, 2026, please refer the executed Loan Documents.” / “Interest on outstanding EMI shall be levied on the amount of unpaid Instalment from the due date till the date of remediation and shall be charged at the applicable rate of interest on the said loan. This interest shall be compounded.”
- **Reason / caveat:** The timing statements on pages 21 and 22 conflict; this draft does not choose between them. The page 22 amount-band table applies only to sanctions on/after July 1, 2026; loans sanctioned through June 30, 2026 are directed to executed Loan Documents. Page 26 compounded interest, LPC, Bounce Charges, CPC and the general Section 10 delayed-payment reference are not interchangeable. The specific customer's sanction date, product and amount band are unknown. The charge-exclusion note on pages 25–26 is limited to specified loans extended exclusively for associated HL/LAP fees, charges and insurance premium when created with that loan; later insurance-premium loans are not within that exclusion.
- **Dependency:** Executed Loan Documents for loans sanctioned through June 30, 2026; account-specific Loan Documents for applicable rates and charges.

### 12. `prepayment_terms` — EXPLICIT
- **Proposed value:** Conditional part/full prepayment and foreclosure charges vary by sanction date, rate type, loan purpose and product. For loans sanctioned through Dec. 31, 2025, floating-rate loans to individuals/non-individuals except for business purpose have nil part/full charges across Term Loan, Flexi Term and Flexi Hybrid products. For business-purpose floating-rate loans and all fixed-rate borrowers, Term Loan charges are 4% of the part-payment amount or principal outstanding; Flexi Term and Flexi Hybrid part-prepayment charges are nil, while full-prepayment charges are 4% of the available Flexi Loan Limit, with Flexi Hybrid full-prepayment charge based on sanctioned amount during Flexi Interest Only tenure and available Flexi Loan Limit during Flexi Term tenure. For loans sanctioned on/after Jan. 1, 2026, floating-rate individual and MSE categories have nil part/full charges across these products; specified business-purpose non-individual (other than MSE) and fixed-rate categories follow the stated 4%/nil product bases. Applicable GST is additional; the own-sources exception is for Housing Loans; dual-rate charges follow the rate status on payment day. Page 4 separately allows no-extra-charge foreclosure within 60 days if a rate change is to the Borrower's disadvantage. Foreclosure-letter issuance is 21 days; Flexi Term/Hybrid part-prepayment charges are stated as nil.
- **Source:** Page 4, rate-change foreclosure paragraph; pages 26–28, Pre-Payment Charges and conditions.
- **Quotes:** “If such change is to the disadvantage of the Borrower, the Borrower may within 60 days and without notice foreclose the Loan account without paying any extra charges or interest.” / “A. For loans sanctioned till December 31, 2025” / “Floating Rate Loans to Individuals / non-Individuals except for Business purpose” / “Part Prepayment Charges” / “Nil” / “Full Prepayment Charges” / “Nil” / “Floating Rate Loans to Individual / non-Individuals for Business purpose” / “Fixed Rate Loans: All Borrowers (including individuals) **” / “Term Loan” / “Flexi Term Loan” / “Flexi Hybrid Loan” / “4%* on Part Payment Amount” / “4%* on Principal Outstanding” / “4%* on the available Flexi Loan Limit” / “4%* on Sanctioned Amount during Flexi Interest Only Loan Repayment Tenure; and” / “4%* on the available Flexi Loan Limit during Flexi Term Loan Tenure” / “* GST as applicable will be payable by the Borrower in addition to the Prepayment Charges.” / “**Nil for Housing Loan closed by the borrower out of their own sources.” / “B. For loans sanctioned on January 01, 2026 or later” / “Floating rate loans to individuals &” / “Floating rate loans to Micro & Small Enterprise (MSE) borrowers” / “Part Prepayment Charges” / “Nil” / “Full Prepayment Charges” / “Nil” / “Floating rate loans to non-Individuals (Other than MSE borrowers) for Business purpose &” / “Fixed Rate Loans: All Borrowers (including individuals) **” / “Note: In case of Dual rate loans (fixed for initial period and then floating), the Foreclosure / Part payment charges will be applicable as per the status (fixed/floating) of the loan as on Foreclosure / Part payment day.” / “Issuance of Foreclosure letter: 21 days from the date of request.” / “Part Pre-Payment charges from Flexi Term Loans and/or Flexi Hybrid Loans will be NIL.”
- **Reason / caveat:** The tables are conditional, not universal. For both sanction-date cohorts, the stated nil categories span all three product types. The other specified business-purpose/fixed-rate group has 4% Term Loan part/full charges; Flexi part charges are nil; Flexi Term full charge is 4% of available Flexi Loan Limit; Flexi Hybrid full charge is 4% of sanctioned amount during Flexi Interest Only tenure and 4% of available Flexi Loan Limit during Flexi Term tenure. Footnotes add GST and the own-sources Housing Loan exception. Dual-rate charges depend on fixed/floating status on the payment date. Page 4's 60-day wording applies only where a rate change is to the Borrower's disadvantage; do not generalize it. No customer's sanction date, rate type, purpose or product is identified.
- **Dependency:** Loan Documents for the applicable product, purpose, rate type and sanction-date category.

### 13. `collateral_security` — EXPLICIT
- **Proposed value:** For a secured loan, the general definition includes a charge over property offered as security and/or other collateral/security in favour of BHFL, including mortgage or another form BHFL deems fit. Actual property/security particulars are in Loan Documents. The security clauses do not apply to an unsecured loan.
- **Source:** Page 8, Section 6, Security.
- **Quotes:** “The charge created / to be created against the Property/ies offered as security in favour of BHFL and / or any other collateral / security as may be created in favour of BHFL is/are considered as the security of the loan, which is detailed in Loan Documents. The Security shall mean and include mortgage, guarantee and any other form of security as deemed fit by BHFL for securing the loan and submitted by the Borrower accordingly.” / “NOTE: If it is an Unsecured Loan, the aforementioned clauses w.r.t. to security shall not be applicable.”
- **Reason / caveat:** Section 6 defines possible security forms and expressly excludes those security clauses for unsecured loans. It does not identify any customer's actual property, charge or instrument; those particulars are in Loan Documents.
- **Dependency:** Loan Documents for actual property/security particulars.

### 14. `guarantees` — UNCLEAR
- **Proposed value:** Section 6 includes guarantee as one possible form of security, but no personal guarantor or specific guarantee obligation is identified.
- **Source:** Page 8, Section 6, Security.
- **Quote:** “The Security shall mean and include mortgage, guarantee and any other form of security as deemed fit by BHFL for securing the loan and submitted by the Borrower accordingly.”
- **Reason / caveat:** The general definition does not establish that a personal guarantee applies to this loan. The Mortgage Guarantee fee on page 21 is conditional and is not proof of a personal guarantor.
- **Dependency:** Loan Documents for any actual guarantee requirement or instrument.

### 15. `events_of_default` — DEFERRED
- **Proposed value:** An Event of Default is referred to as an event mentioned in the Loan Agreement and other Loan Documents. This MITC describes consequences and remedies but does not enumerate the underlying default triggers.
- **Source:** Pages 10–12, Section 10, Brief Procedure for Recovery of Overdues.
- **Quote:** “On occurrence of any event of default as mentioned in the Loan Agreement and other Loan Documents (“Event of Default”), all outstanding amounts owed by the Borrower to BHFL shall become payable forthwith”
- **Reason / caveat:** The wording defers the events themselves to unavailable documents. The acceleration, default-interest and security-enforcement remedies in this section are consequences, not a complete list of default events.
- **Dependency:** Loan Agreement and other Loan Documents.

### 16. `governing_law` — NOT_PRESENT
- **Proposed value:** None.
- **Source:** Page 11, Section 10, recovery of overdues.
- **Quote:** “Exercise such other rights and remedies as may be available to the Company under applicable law during the pendency of the Loan.”
- **Reason / caveat:** No clause selecting governing law was identified in this MITC. The quote is a general reference to applicable law for remedies, not a governing-law clause. This finding is limited to this MITC and does not establish whether the unprovided Loan Agreement contains such a clause.

## Evidence-status counts

| Status | Count |
|---|---:|
| EXPLICIT | 8 |
| DEFERRED | 4 |
| UNCLEAR | 2 |
| NOT_PRESENT | 2 |
| **Total** | **16** |

## Human review and limitations

The user reviewed the 16 displayed candidate entries and approved all 16 as written on 2026-11-16, including the existing EXPLICIT, DEFERRED, UNCLEAR and NOT_PRESENT evidence classifications. This records only the user's decision; no independent expert or legal validation, or second-review approval, is claimed, and the set is not thereby finalized as Gold Labels. The proposed values remain scoped to the product-level MITC; missing customer-specific values have not been inferred. OCR quality and Hindi extraction degradation remain caveats. The bilingual interest/fee tables have reflowed text layout, and outstanding visual verification is still required. Sanction-date applicability and all transaction-specific documents also require human verification.
