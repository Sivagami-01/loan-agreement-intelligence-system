# Phase 2 UNCLEAR Adjudication Packet

This packet covers the four records in the independent-review queue. All four candidate `proposed_gold_value` cells are blank and must remain blank until the uncertainty is resolved. The queue status is `PENDING` for every case. User acceptance of a candidate does not resolve its UNCLEAR evidence status and is not an independent review or expert adjudication.

The quotations, locators, and review context below are copied or summarized only from the candidate CSVs, the queue, and the corresponding evidence reports. No reviewer identity, decision, or approval is supplied in this packet.

## Case 1: DBS - prepayment_terms

- **Document ID:** `03_dbs_mitc`
- **Field:** `prepayment_terms`
- **Existing evidence status:** `UNCLEAR` (candidate `gold_status` is `HUMAN_APPROVED`; its reviewer reason retains the evidence status as `UNCLEAR`)
- **Queue status:** `PENDING`
- **Candidate record:** [03_DBS_MITC_KEY_INFO_HUMAN_REVIEW_DRAFT.csv](./03_DBS_MITC_KEY_INFO_HUMAN_REVIEW_DRAFT.csv)
- **Evidence report:** [03_DBS_MITC_SOURCE_EVIDENCE_REPORT.md](./03_DBS_MITC_SOURCE_EVIDENCE_REPORT.md)
- **Queue record:** [PHASE2_UNCLEAR_INDEPENDENT_REVIEW_QUEUE.csv](./PHASE2_UNCLEAR_INDEPENDENT_REVIEW_QUEUE.csv)
- **Proposed Gold value:** **Must remain blank until resolved.**
- **Verified page status:** Page 2 rendered and checked; the quoted language is legible. The issue is the ambiguity in the charge exception, not a rendering failure.

**Relevant source quote**

> The Borrower may, with the prior approval of DBS Bank, prepay the Borrower's Dues, in full or in part, subject to such terms as may be stipulated by DBS Bank (including payment of pre-payment charges). | However, no prepayment/foreclosure charges will be charged on loans where the interest rate is floating/ fixed, and foreclosure is made after the fixed period (during which the fixed interest rate applies), where after the floating/Fixed interest rate becomes applicable.

**Page/section locator:** Page 2; VIII. PREPAYMENT AND FORECLOSURE.

**Why it remains UNCLEAR / missing information:** The permission for full or partial prepayment and the need for prior approval are stated, but the exception uses inconsistent wording (`floating/ fixed` and `floating/Fixed`). The text does not establish how the rate type, fixed period, and foreclosure-charge exception relate. The candidate defers to the Loan Agreement and records that it was not supplied with the source PDF.

**Independent reviewer needs to verify:** Determine whether the cited wording supports a clear interpretation and whether the referenced Loan Agreement is needed to establish applicable charges. Do not infer or normalize the exception if the available documents do not resolve it.

**Possible outcomes for the reviewer:**
- Confirm a source-supported value.
- Confirm that the value must remain blank because the source evidence is insufficient.
- Return for additional source evidence.

**Reviewer decision:**  

**Decision rationale:**  

## Case 2: Bajaj Housing Finance - late_payment_or_default_interest

- **Document ID:** `13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi`
- **Field:** `late_payment_or_default_interest`
- **Existing evidence status:** `UNCLEAR` (recorded in the candidate reviewer reason)
- **Queue status:** `PENDING`
- **Candidate record:** [13_BAJAJ_MITC_KEY_INFO_HUMAN_REVIEW_DRAFT.csv](./13_BAJAJ_MITC_KEY_INFO_HUMAN_REVIEW_DRAFT.csv)
- **Evidence report:** [13_BAJAJ_MITC_SOURCE_EVIDENCE_REPORT.md](./13_BAJAJ_MITC_SOURCE_EVIDENCE_REPORT.md)
- **Queue record:** [PHASE2_UNCLEAR_INDEPENDENT_REVIEW_QUEUE.csv](./PHASE2_UNCLEAR_INDEPENDENT_REVIEW_QUEUE.csv)
- **Proposed Gold value:** **Must remain blank until resolved.**
- **Verified page status:** Pages 23 and 24 rendered and checked. The pages show the CPC table with trigger points and amounts; the remaining issue is whether the page 21/22/23 wording can be reconciled and whether loan-specific terms are deferred to executed loan documents.

**Relevant source quotes**

> Charge interest on delayed payment, applicable Penal Charges including Bounce Charges, Late Payment Charges & Covenant Perfection Charges.

> Late Payment Charges (LPC)- calculated daily for each EMI starting from the date of Unpaid / Partially paid EMI till full due EMI amount has been received, as mentioned in below table. LPC shall be accounted on receipt basis. These charges will not be Capitalized.

> Late Payment Charges (LPC)^ (chargeable per day from 31st DPD (Days Past Due) for every partially or fully overdue EMI)

> For Bounce and LPC Charges applicable to loans sanctioned till June 30, 2026, please refer the executed Loan Documents.

> Interest on outstanding EMI shall be levied on the amount of unpaid Instalment from the due date till the date of remediation and shall be charged at the applicable rate of interest on the said loan. This interest shall be compounded.

**Page/section locators:** Page 11, Section 10; page 21, Section 25, Penal Charges; page 22, dated LPC/Bounce table; page 23, earlier-sanction reference; pages 25-26, charge exclusions; page 26, Section 26, Delayed Payment Interest.

**Why it remains UNCLEAR / missing information:** The page 21 prose says LPC calculation begins on the unpaid or partially paid EMI date, while the page 22 table says the charge is from the 31st DPD. The candidate does not reconcile these statements. The candidate also records that sanction date, product, amount band, and applicable customer-specific documents are unknown. Section 26 delayed-payment interest, LPC, Bounce Charges, and CPC must not be conflated.

**Independent reviewer needs to verify:** Compare the cited wording and table context, determine whether the LPC timing conflict can be resolved from the evidence, and keep interest distinct from the separate charges. Check applicable sanction date, product, and amount band only if customer-specific application is being determined; the candidate defers earlier-sanction and account-specific terms to executed Loan Documents. Do not choose a conflicting timing or infer missing customer details.

**Possible outcomes for the reviewer:**
- Confirm a source-supported value.
- Confirm that the value must remain blank because the source evidence is insufficient.
- Return for additional source evidence.

**Reviewer decision:**  

**Decision rationale:**  

## Case 3: Bajaj Housing Finance - guarantees

- **Document ID:** `13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi`
- **Field:** `guarantees`
- **Existing evidence status:** `UNCLEAR` (recorded in the candidate reviewer reason)
- **Queue status:** `PENDING`
- **Candidate record:** [13_BAJAJ_MITC_KEY_INFO_HUMAN_REVIEW_DRAFT.csv](./13_BAJAJ_MITC_KEY_INFO_HUMAN_REVIEW_DRAFT.csv)
- **Evidence report:** [13_BAJAJ_MITC_SOURCE_EVIDENCE_REPORT.md](./13_BAJAJ_MITC_SOURCE_EVIDENCE_REPORT.md)
- **Queue record:** [PHASE2_UNCLEAR_INDEPENDENT_REVIEW_QUEUE.csv](./PHASE2_UNCLEAR_INDEPENDENT_REVIEW_QUEUE.csv)
- **Proposed Gold value:** **Must remain blank until resolved.**
- **Verified page status:** The general security definition on page 8 is clear and rendered; the ambiguity is not a rendering issue but the absence of a customer-specific guarantee instrument or guarantor identity.

**Relevant source quote**

> The Security shall mean and include mortgage, guarantee and any other form of security as deemed fit by BHFL for securing the loan and submitted by the Borrower accordingly.

**Page/section locator:** Page 8 - Section 6, Security.

**Why it remains UNCLEAR / missing information:** The definition lists guarantee as one possible form of security, but does not establish that a guarantee is required for this loan, identify a personal guarantor, or specify an actual guarantee instrument. The candidate notes that a conditional Mortgage Guarantee fee is not proof of a personal guarantor.

**Independent reviewer needs to verify:** Determine from the applicable Loan Documents whether an actual guarantee obligation or instrument exists and what it establishes. Do not infer an obligation, guarantor, or guarantee type from the general security definition or the fee reference.

**Possible outcomes for the reviewer:**
- Confirm a source-supported value.
- Confirm that the value must remain blank because the source evidence is insufficient.
- Return for additional source evidence.

**Reviewer decision:**  

**Decision rationale:**  

## Case 4: Muthoot Homefin - prepayment_terms

- **Document ID:** `09_muthoothomefin_MHIL-MITC`
- **Field:** `prepayment_terms`
- **Existing evidence status:** `UNCLEAR`
- **Queue status:** `PENDING`
- **Candidate record:** [09_MUTHOOT_HOMEFIN_KEY_INFO_HUMAN_REVIEW_DRAFT.csv](./09_MUTHOOT_HOMEFIN_KEY_INFO_HUMAN_REVIEW_DRAFT.csv)
- **Evidence report:** [09_MUTHOOT_HOMEFIN_SOURCE_EVIDENCE_REPORT.md](./09_MUTHOOT_HOMEFIN_SOURCE_EVIDENCE_REPORT.md)
- **Queue record:** [PHASE2_UNCLEAR_INDEPENDENT_REVIEW_QUEUE.csv](./PHASE2_UNCLEAR_INDEPENDENT_REVIEW_QUEUE.csv)
- **Proposed Gold value:** **Must remain blank until resolved.**
- **Verified page status:** Pages 3, 5, 6, and 7 rendered and checked. Page 3 shows the row 12 heading, but the actual rate cells are not legible; pages 5–7 were inspected and do not resolve the row 12 prepayment schedule. The prepayment question remains unresolved by the visible evidence.

**Relevant source quote**

> Part Prepayment / foreclosure charges on Loan || Foreclosure / Part prepayment within 12 months of disbursement || Continuation of 12th Point

**Page/section locator:** Page 3; Section 3, row 12, with continuation noted on page 3.

**Why it remains UNCLEAR / missing information:** The candidate and evidence report describe an image-based schedule, but the text layer does not transcribe its cells and the schedule rates and row/cell associations were not reliably verified in the available rendering. The candidate records that applicability may depend on product, rate type, payment source, sanction date, and amount band.

**Independent reviewer needs to verify:** Establish whether a legible schedule and its continuation provide reliable rates and cell associations, and determine any applicable customer-specific conditions from evidence. Do not assign a rate or condition until those details are verifiable.

**Possible outcomes for the reviewer:**
- Confirm a source-supported value.
- Confirm that the value must remain blank because the source evidence is insufficient.
- Return for additional source evidence.

**Reviewer decision:**  

**Decision rationale:**  

## Project-owner adjudication section (consolidated decision form)

This section is for project-owner adjudication only. It does not satisfy the independent-review requirement and does not finalize the dataset. The queue remains `PENDING` until a genuine review/adjudication is recorded.

### Case 1 — DBS, `prepayment_terms`
- **Exact source evidence and locator:** Page 2; VIII. PREPAYMENT AND FORECLOSURE. Quote: "The Borrower may, with the prior approval of DBS Bank, prepay ... subject to such terms ... including payment of pre-payment charges." Followed by the exception about floating/fixed-rate prepayment after the fixed period.
- **Current evidence status:** `UNCLEAR`
- **What is known:** The MITC states prepayment is allowed with prior approval and identifies a prepayment-charge exception based on fixed/floating rate terms.
- **What remains uncertain:** The draft text uses inconsistent wording ("floating/ fixed" and "floating/Fixed"); the MITC does not resolve how the exception applies or whether the referenced Loan Agreement is required.
- **Why a definitive value cannot currently be assigned:** The customer-specific fixed/floating rate treatment and applicable charge terms are not established within the MITC; the source defers to the Loan Agreement, which is not supplied.
- **Precise adjudication question:** Does the original source language clearly establish when prepayment charges do or do not apply, or must the value remain blank because the MITC does not resolve the exception without the referenced Loan Agreement?
- **Project-owner decision:** A / B / C
- **Decision rationale:**
- **Reviewer/adjudicator identity:**
- **Decision date:**
- **Additional evidence required:**

### Case 2 — Bajaj, `late_payment_or_default_interest`
- **Exact source evidence and locator:** Page 11 Section 10; page 21 Section 25; page 22 LPC/Bounce table; page 23 earlier-sanction reference; pages 25–26 exclusions; page 26 Section 26 Delayed Payment Interest.
- **Current evidence status:** `UNCLEAR`
- **What is known:** The MITC states delayed payment interest, LPC, Bounce Charges, CPC, and compounded interest on outstanding EMI; the page-22 table identifies charges by product band and sanction date.
- **What remains uncertain:** The page-21 prose says LPC is calculated daily starting on unpaid/partially paid EMI date, while the page-22 table says it is charged from 31st DPD; sanctions before/after 30 June 2026 and product-specific terms are keyed to separate documents.
- **Why a definitive value cannot currently be assigned:** The source references executed Loan Documents and customer-specific product/date conditions that are not supplied; the draft could not safely reconcile the timing conflict or assign a single universal default-interest value.
- **Precise adjudication question:** Can the MITC itself resolve the LPC timing conflict and product-specific applicability, or must the field remain blank because the document expressly defers the relevant terms to other loan documents and customer-specific facts?
- **Project-owner decision:** A / B / C
- **Decision rationale:**
- **Reviewer/adjudicator identity:**
- **Decision date:**
- **Additional evidence required:**

### Case 3 — Bajaj, `guarantees`
- **Exact source evidence and locator:** Page 8; Section 6, Security. Quote: "The Security shall mean and include mortgage, guarantee and any other form of security as deemed fit by BHFL for securing the loan and submitted by the Borrower accordingly."
- **Current evidence status:** `UNCLEAR`
- **What is known:** The document places guarantee within a general security definition and includes a mortgage-guarantee fee concept on a later page.
- **What remains uncertain:** The MITC does not identify a guarantor, a guarantee instrument, the form of guarantee, or whether a guarantee is required for the specific customer or product.
- **Why a definitive value cannot currently be assigned:** The general security language is not proof of a required personal guarantee or a customer-specific guarantee obligation; no actual guarantor or guarantee instrument is supplied in the MITC.
- **Precise adjudication question:** Does the original source establish that a personal guarantee is required for this loan or must the field remain blank because the document only lists guarantee as one possible security form and not a specific required obligation?
- **Project-owner decision:** A / B / C
- **Decision rationale:**
- **Reviewer/adjudicator identity:**
- **Decision date:**
- **Additional evidence required:**

### Case 4 — Muthoot, `prepayment_terms`
- **Exact source evidence and locator:** Page 3; Section 3, row 12; continuation stated on the same page. Quote: "Part Prepayment / foreclosure charges on Loan || Foreclosure / Part prepayment within 12 months of disbursement || Continuation of 12th Point."
- **Current evidence status:** `UNCLEAR`
- **What is known:** The MITC includes a row heading for part prepayment/foreclosure charges and indicates that the schedule continues on page 3.
- **What remains uncertain:** The actual schedule rates, conditions, and cell associations are not legible in the rendered page; the visible evidence does not provide a reliable rate or product-specific application.
- **Why a definitive value cannot currently be assigned:** The rendered page does not provide a readable rate table or clear cell mapping. The guidance states not to infer rates or customer-specific pairings from illegible evidence.
- **Precise adjudication question:** Is there a readable, source-supported prepayment schedule in the original document that establishes the applicable charge rate and condition, or must the field remain blank because the schedule cells remain illegible and customer-specific applicability is not verifiable?
- **Project-owner decision:** A / B / C
- **Decision rationale:**
- **Reviewer/adjudicator identity:**
- **Decision date:**
- **Additional evidence required:**

## Project-owner closure note
- The queue entries remain `PENDING` until a genuine review/adjudication is recorded.
- The other 60 candidate records remain unchanged.
- `CANDIDATE_NOT_FINAL` remains unchanged.
- `KEY_INFO_GOLD_APPROVED.csv` is not created.
- Phase 2 remains blocked pending actual adjudication and documentation of the four unresolved fields.

## Project-owner adjudication — four unresolved cases

This is one consolidated project-owner decision form. A project-owner decision is not an independent second review and does not automatically satisfy the independent-review requirement. Keep each queue entry `PENDING` until the required independent review or adjudication is genuinely completed and recorded. Do not populate a proposed Gold value before the evidence supports it.

For each case, choose one outcome:
- **A.** Approve a specific value only if the original source and any necessary applicable loan documents support it.
- **B.** Retain a blank value and `UNCLEAR` status because available evidence is insufficient; record the limitation.
- **C.** Request additional source documents or qualified expert review.

### 1. DBS — `prepayment_terms`
- **Evidence and locator:** The MITC states that the borrower may prepay in full or part with prior DBS approval, subject to terms including prepayment charges. Its exception refers to “floating/ fixed” rates and foreclosure after the fixed period. Page 2, Section VIII, “PREPAYMENT AND FORECLOSURE.”
- **Current status:** `UNCLEAR`; proposed Gold value is blank.
- **Known:** Prepayment permission, prior approval, and a charge exception are stated.
- **Uncertain / why no definitive value:** The exception wording is inconsistent, and the MITC does not establish how the rate type and fixed period interact. The referenced Loan Agreement is unavailable, so customer-specific charge terms cannot be confirmed.
- **Decision question:** Does the source and applicable Loan Agreement establish a definite prepayment-charge rule, or should the value remain blank as insufficiently evidenced?
- **Project-owner decision (A/B/C):**
- **Decision rationale:**
- **Reviewer/adjudicator identity, if applicable:**
- **Decision date:**
- **Additional evidence required:**

### 2. Bajaj — `late_payment_or_default_interest`
- **Evidence and locator:** The MITC discusses delayed-payment interest and separate LPC, Bounce Charges, and CPC. Page 21, Section 25, says LPC is calculated from the unpaid/partially-paid EMI date; the page 22 table says LPC is chargeable from 31st DPD. Page 23 directs loans sanctioned through June 30, 2026 to executed Loan Documents; page 26, Section 26, addresses compounded interest on unpaid instalments.
- **Current status:** `UNCLEAR`; proposed Gold value is blank.
- **Known:** Interest and multiple distinct charge types are described, with table entries dependent on product and sanction date.
- **Uncertain / why no definitive value:** The stated LPC start times conflict, and customer sanction date, product, amount band, and applicable executed Loan Documents are not established. These terms cannot safely be combined into one universal value.
- **Decision question:** Do the source and applicable executed Loan Documents establish the relevant timing and customer-specific terms without conflating interest with other charges, or should the value remain blank?
- **Project-owner decision (A/B/C):**
- **Decision rationale:**
- **Reviewer/adjudicator identity, if applicable:**
- **Decision date:**
- **Additional evidence required:**

### 3. Bajaj — `guarantees`
- **Evidence and locator:** The MITC says security “shall mean and include mortgage, guarantee and any other form of security as deemed fit by BHFL” (page 8, Section 6, “Security”).
- **Current status:** `UNCLEAR`; proposed Gold value is blank.
- **Known:** Guarantee is named as one possible form of security.
- **Uncertain / why no definitive value:** The MITC does not identify a guarantor, guarantee instrument, or customer-specific guarantee obligation. The general definition does not prove that a guarantee is required for this loan.
- **Decision question:** Do applicable Loan Documents establish an actual guarantee obligation and its scope, or should the value remain blank because the MITC only lists a possible security form?
- **Project-owner decision (A/B/C):**
- **Decision rationale:**
- **Reviewer/adjudicator identity, if applicable:**
- **Decision date:**
- **Additional evidence required:**

### 4. Muthoot — `prepayment_terms`
- **Evidence and locator:** The MITC page 3, Section 3, row 12, identifies “Part Prepayment / foreclosure charges on Loan” and “Foreclosure / Part prepayment within 12 months of disbursement,” followed by “Continuation of 12th Point.”
- **Current status:** `UNCLEAR`; proposed Gold value is blank.
- **Known:** A prepayment/foreclosure schedule is referenced in row 12.
- **Uncertain / why no definitive value:** The rendered schedule rate cells and row/cell associations are not legible; pages 5–7 do not resolve them. Product, rate type, payment source, sanction date, and amount-band applicability are not established.
- **Decision question:** Is there readable source evidence and applicable customer information sufficient to assign a prepayment value, or should it remain blank because the schedule cannot be reliably interpreted?
- **Project-owner decision (A/B/C):**
- **Decision rationale:**
- **Reviewer/adjudicator identity, if applicable:**
- **Decision date:**
- **Additional evidence required:**
