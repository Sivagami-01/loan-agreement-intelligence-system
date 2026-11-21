# Phase 2 Unresolved-Case Policy Amendment Proposal

> **PROPOSED — NOT APPROVED — NO DATASET FINALIZATION AUTHORIZED**

- **Proposal status:** `NOT APPROVED`
- **Prepared:** 2026-11-17
- **Proposal document version:** Draft 1.0 (proposal revision only; not a dataset or guideline version)
- **Effective date:** None. No change takes effect unless the required project-owner and academic-methodology approvals below are recorded.
- **Current Phase 2 state:** `CANDIDATE_NOT_FINAL`; four uncertainty-triggered review cases remain unresolved.

## 1. Purpose and current situation

The project owner has confirmed that a separate independent reviewer is not currently available. This document proposes ways to handle four unresolved Key-Information cases transparently. It does not amend the active policy, resolve any case, record a review, or authorize a Gold dataset.

The current candidate set contains 64 records: 16 each for DBS, Bajaj Housing Finance, Muthoot Homefin, and CITGO. The four target fields have blank proposed Gold values and remain evidence-status `UNCLEAR`; their independent-review queue entries are `PENDING`. All 64 records remain `CANDIDATE_NOT_FINAL`.

The current project-owner policy prohibits releasing the other 60 records separately while the four uncertainty cases remain unresolved. No final Gold dataset exists. The absence of an independent reviewer does not turn AI analysis into independent review or make the source evidence more complete.

## 2. Existing approved policy and rule that would need amendment

The project owner approved the following Phase 2 policies on 2026-11-16, as recorded in `PHASE2_PROJECT_OWNER_DECISION_RECORD.md`:

1. **Partial release not permitted:** Do not finalize the 60 non-UNCLEAR records separately while the four UNCLEAR cases remain unresolved. Resolve all four through recorded independent review or expert adjudication before finalization.
2. **Second review is uncertainty-triggered:** Required review must be independently recorded; do not claim completion without evidence.
3. **Provenance:** Record source hashes per document and preserve reviewer identity, date, decision, rationale, and review history.
4. **AES Ohio:** Excluded until its original agreement is available.

Option B would directly amend policy 1 for a scoped 60-field evaluation subset. It would not satisfy or waive policy 2 for the four excluded cases. No owner decision is being made or changed by this proposal. Academic-methodology approval is not documented.

## 3. Four unresolved cases

### DBS — `prepayment_terms`

- **Current record:** `03_dbs_mitc`; evidence status `UNCLEAR`; proposed Gold value blank; queue `PENDING`. The candidate's `gold_status=HUMAN_APPROVED` reflects the user's prior acceptance of the candidate as written, not independent review or resolution.
- **Evidence:** Page 2, Section VIII, "PREPAYMENT AND FORECLOSURE." The MITC states that full or partial prepayment requires prior DBS approval and may be subject to charges. Its exception contains the inconsistent wording "floating/ fixed" and "floating/Fixed."
- **Why insufficient / unsafe to label definitively:** The source does not establish a single clear relationship among rate type, the fixed period, foreclosure, and the charge exception. Assigning a charge rule would require interpretation not safely supported by the available wording.
- **Missing information:** The referenced customer-specific Loan Agreement and applicable transaction terms are unavailable.
- **Why AI is not independent review:** AI can point out the wording and missing document, but it is not a separate human reviewer, cannot establish an independent human judgment or reviewer provenance, and cannot supply the absent Loan Agreement.

### Bajaj Housing Finance — `late_payment_or_default_interest`

- **Current record:** `13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi`; evidence status `UNCLEAR`; proposed Gold value blank; queue `PENDING`. Candidate `gold_status=PENDING_REVIEW`.
- **Evidence:** Page 21, Section 25, says LPC is calculated daily starting from the unpaid/partially-paid EMI date. Page 22 describes LPC as chargeable per day from 31st DPD. Page 23 refers loans sanctioned through June 30, 2026 to executed Loan Documents. Section 26 on page 26 separately describes compounded interest on unpaid instalments at the applicable loan rate. Bounce Charges and CPC are separate charge types; pages 23-24 display CPC material.
- **Why insufficient / unsafe to label definitively:** It is not established whether the EMI-date and 31st-DPD wording describes distinct stages or a conflict. The source also has sanction-date, product, amount-band and exclusion conditions. Combining LPC, delayed-payment interest, Bounce Charges, or CPC into one asserted rule would be unsafe.
- **Missing information:** Customer sanction date, product, amount band, relevant exclusions, and applicable executed/account-specific Loan Documents.
- **Why AI is not independent review:** AI can map the competing wording but cannot provide an independently accountable human interpretation or determine missing customer-specific facts and documents.

### Bajaj Housing Finance — `guarantees`

- **Current record:** Same Bajaj document; evidence status `UNCLEAR`; proposed Gold value blank; queue `PENDING`. Candidate `gold_status=PENDING_REVIEW`.
- **Evidence:** Page 8, Section 6, "Security," includes guarantee as one possible form of security. The source report notes that a conditional Mortgage Guarantee fee is not proof of a personal guarantor.
- **Why insufficient / unsafe to label definitively:** A general list of possible security forms does not establish that this particular loan has a guarantee, identify a guarantor, or define an actual guarantee obligation.
- **Missing information:** Applicable executed Loan Documents, any signed guarantee instrument, the guarantor's identity, and the scope of any obligation.
- **Why AI is not independent review:** AI cannot convert general language into a customer-specific guarantee or independently verify an unavailable instrument.

### Muthoot Homefin — `prepayment_terms`

- **Current record:** `09_muthoothomefin_MHIL-MITC`; evidence status `UNCLEAR`; proposed Gold value blank; queue `PENDING`. Candidate `gold_status=UNCLEAR`.
- **Evidence:** Page 3, Section 3, row 12, identifies part-prepayment/foreclosure charges and refers to a continuation. The embedded schedule's rate cells and cell associations are not reliably legible. Pages 5-7 do not supply the missing prepayment schedule details.
- **Why insufficient / unsafe to label definitively:** A rate or condition cannot safely be assigned from unreadable table cells or uncertain row/cell alignment.
- **Missing information:** A legible authoritative schedule and the customer's product, rate type, payment source, sanction date, amount band, and applicable customer-specific terms.
- **Why AI is not independent review:** AI cannot make unreadable cells legible by inference, provide missing customer data, or serve as an independent human reviewer.

## 4. Policy options

### Option A — Keep Phase 2 blocked

Keep all 64 records exactly as they are until a genuine independent reviewer or appropriately qualified expert becomes available. Maintain the four blank values, `UNCLEAR` evidence statuses, and `PENDING` queue entries. Do not finalize a scored Gold set.

- **Advantages:** Complies with the currently approved no-partial-release rule; preserves the original 64-field scope; avoids implying that exclusions or a single-annotator opinion resolve uncertainty.
- **Limitations:** No scored Gold evaluation set can be released under the present rule while the four cases remain unresolved; progress depends on obtaining review capacity or additional evidence.

### Option B — Exclude four unresolved cases from the scored Gold evaluation set

Subject to explicit project-owner approval **and** confirmation that the registered project methodology and academic supervisor permit this revised scope:

- Retain all 64 original candidate records unchanged for traceability.
- Keep the four values blank and their evidence status `UNCLEAR`; keep them unresolved and do not mark independent review or expert adjudication complete.
- Create an exclusion register recording, for each case, document ID, field, reason, source limitation, and the approved exclusion decision.
- Allow only the 60 otherwise eligible records to proceed through final QA, and only if all other evidence, provenance, and approval gates pass.
- Report scored-set coverage as **60 of 64 candidate fields**. Do not report 64/64 coverage or imply the four were resolved.
- Disclose the four exclusions and reasons in the approved methodology and project limitations.
- Do not count excluded cases as correct, incorrect, or successfully resolved; exclude them from both numerator and denominator of scored metrics.
- Never delete the four candidate rows or silently drop them from the audit trail.

This is a revised evaluation scope. It is not independent review, expert adjudication, or evidence that the four labels are correct. It does not itself constitute approval of the remaining 60 rows or completion of all Phase 2 work.

- **Advantages:** Could provide a clearly bounded scored subset without fabricating decisions, if the methodology permits.
- **Limitations:** Changes the evaluation denominator and intended scope; requires formal approval and explicit reporting. Without academic/supervisor authorization, this option must not be used.

### Option C — Single-annotator adjudication

Permit the original annotator/project owner to make a documented final decision after reviewing the evidence, but only if the project methodology and academic supervisor formally allow this approach.

- This is **not** an independent second review.
- It is **not** expert adjudication unless the decision-maker actually has and documents the required expertise.
- The annotator/owner relationship must be verified rather than assumed.
- Disclose the single-annotator method and resulting limitation.
- A decision cannot create missing source evidence, make illegible schedule cells readable, or establish customer-specific terms absent from the source.
- If evidence remains insufficient, the value must remain blank and `UNCLEAR`; an owner decision cannot justify unsupported certainty.
- **Advantages:** Could permit a human-owned decision record without falsely claiming independence, if formally allowed.
- **Limitations:** Higher risk of confirmation bias and weaker validation; does not meet the currently approved independent-review rule without an explicit policy amendment.

## 5. Recommendation

**Recommended current action: Option A.** No approval from the academic supervisor or registered methodology has been recorded to exclude the four fields. Therefore the currently approved no-partial-release rule remains in effect and Phase 2 must stay blocked.

**Conditional proposal:** Seek formal approval for Option B as the most transparent route to a usable scored subset if, and only if, the academic supervisor and registered methodology permit exclusion. If they approve it, retain the four cases unchanged in the 64-record audit trail, create the approved exclusion register, and report a 60/64 coverage limit. If they do not approve Option B, continue with Option A. Option C is not recommended unless the methodology explicitly permits single-annotator adjudication and its limitations are accepted in writing.

## 6. Proposed replacement wording for the relevant policy

The following is proposed wording only. It has no effect unless the project owner and required academic-methodology authority approve it:

> **Scoped evaluation subset when uncertainty-triggered review is unavailable (proposed replacement for the no-partial-release rule):** The four records listed in the approved unresolved-case exclusion register may remain blank and `UNCLEAR`, and may be excluded from a separately identified scored Gold evaluation subset, only after written approval from the project owner and confirmation that the registered project methodology and academic supervisor permit the revised scope. All 64 original candidate records must remain preserved for traceability. The 60 included records may proceed through final QA only after each independently passes all applicable evidence, reviewer-provenance, source-provenance, and approval gates. The exclusion register must identify each excluded document ID and field, the evidence limitation, the reason for exclusion, and the approving authority/date. Excluded cases are unresolved; they must not be counted as correct, incorrect, or resolved, must not be silently deleted, and remain eligible for a later independent review or qualified expert adjudication. Report the scored-set coverage as 60 of 64 candidate fields and disclose the scope change and limitations. This scoped subset does not constitute completion of the original 64-field review scope.

The uncertainty-triggered independent-review rule remains in force for the four unresolved records. Option B changes only whether a separately approved 60-field subset may be scored; it does not claim that the four cases have been reviewed or adjudicated.

## 7. Dataset coverage and evaluation implications

| Scope | Candidate records retained | Scored, if approved and all gates pass | Treatment of four unresolved fields |
|---|---:|---:|---|
| Current approved scope | 64 | None while the current no-partial-release rule applies | Blank, `UNCLEAR`, pending review |
| Option A | 64 | None until all required gates pass | Retained and unresolved |
| Option B, conditional | 64 in the traceability dataset | 60 of 64 candidate fields | Four excluded from scoring, not resolved |
| Option C, conditional | 64 | Only if the methodology allows single-annotator decisions and all other gates pass | Individually decided with the single-annotator limitation disclosed; insufficient evidence stays blank/`UNCLEAR` |

Under Option B, evaluation metrics must use only eligible scored records and explicitly state the denominator. The excluded cases must not contribute to any score as successes, failures, negatives, or resolved labels. Preserve both the original 64-row candidate file and the exclusion register. Do not characterize a 60-field subset as a 64-field complete benchmark.

No option in this proposal authorizes creating `KEY_INFO_GOLD_APPROVED.csv` now. Any later deliverable requires the applicable written approvals and completion of the corresponding QA, evidence, and provenance gates.

## 8. Transparency and limitations statement

The four records remain uncertain for source-specific reasons: ambiguous DBS prepayment wording and a missing Loan Agreement; Bajaj's timing/applicability and charge-type questions plus missing customer-specific terms; absence of a customer-specific Bajaj guarantee instrument; and unreadable Muthoot prepayment schedule cells plus missing customer-specific details. These limitations cannot be cured by AI analysis.

AI analysis is preparation support, not independent human review. Exclusion is a scoring-scope decision, not a substantive label. Single-annotator adjudication is not independent review and is not expert adjudication without documented qualification. No source limitation, reviewer identity, date, approval, or Gold value may be invented. No decision in this proposal is effective yet.

## 9. Project-owner decision fields

- **Selected option:** A / B / C / Defer
- **Decision:** APPROVE / REJECT / DEFER
- **Decision rationale:**
- **For Option B, approve revised 60/64 scored scope:** YES / NO / NOT APPLICABLE
- **For Option B, approve creation of an exclusion register after all required approvals:** YES / NO / NOT APPLICABLE
- **Project-owner name or approved identifier:**
- **Decision date:**
- **Signature or recorded approval reference:**

## 10. Academic supervisor / methodology approval fields

Complete if Option B or C is selected, or if otherwise required by the registered methodology.

- **Registered methodology / protocol reference and version:**
- **Does the methodology permit this change?** YES / NO / PENDING
- **Academic supervisor name and role:**
- **For Option B, approval to exclude four unresolved fields and report 60/64 coverage:** APPROVE / REJECT / PENDING
- **For Option C, approval to use a disclosed single-annotator decision process:** APPROVE / REJECT / PENDING
- **Required methodology amendment or limitations disclosure:**
- **Decision date:**
- **Signature or recorded approval reference:**

## 11. Effective date, version, and superseded-decision references

- **Proposal version:** Draft 1.0. This is only the revision identifier for this proposal document; it does not assign a dataset or guideline version.
- **Effective date:** Not effective. If approved, enter the date on which all required project-owner and academic-methodology approvals are recorded: ____________________.
- **Current decisions referenced:** `PHASE2_PROJECT_OWNER_DECISION_RECORD.md`, approved 2026-11-16, especially Decision 1 (no partial release), Decision 2 (uncertainty-triggered second review), and Decision 4 (review-event provenance); `HUMAN_ANNOTATION_GUIDE.md`; `PHASE2_KEY_INFO_FINALIZATION_CHECKLIST.md`.
- **Superseded status:** None. This proposal does not supersede or modify any current decision. If approved, only the no-partial-release rule would be replaced to the limited extent stated in the approved amendment; all other applicable review, evidence, provenance, and approval rules remain in force unless separately amended in writing.

## Current outcome

`PROPOSED — NOT APPROVED — NO DATASET FINALIZATION AUTHORIZED`

The active policy remains Option A until the required amendment approvals, if any, are recorded. The four values remain blank and `UNCLEAR`; the queue remains pending; all 64 records remain `CANDIDATE_NOT_FINAL`. No exclusion register, final Gold dataset, or Phase 3 work is authorized by this proposal.
