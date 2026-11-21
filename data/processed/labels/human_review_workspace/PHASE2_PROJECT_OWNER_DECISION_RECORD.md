# Phase 2 Project-Owner Decision Record

**Project owner:** Shiva  
**Authorization:** User confirmed authorization to make these project-owner decisions.  
**Decision date:** 2026-11-16  
**Decision status:** All five policy decisions below are **APPROVED** by the project owner.

These are policy decisions only. They do not approve, finalize, or create a Gold dataset.

## 1. Partial release — NOT PERMITTED

**Approved decision:** Do not finalize the 60 non-UNCLEAR records separately while the four UNCLEAR cases remain pending. Resolve all four cases through recorded independent review or expert adjudication before finalization. Preserve the requirement for an explicit finalization decision.

## 2. Second-review scope — UNCERTAINTY-TRIGGERED

**Approved decision:** Require an independent second review when the uncertainty conditions in the annotation guide apply. Record each required review independently. Do not claim any review has been completed unless supporting evidence exists.

## 3. Source hashes — PER DOCUMENT

**Approved decision:** Record one SHA-256 hash for each original source document in versioned dataset provenance metadata. Link each hash unambiguously to its document and version.

## 4. Reviewer provenance — RECORD EACH REVIEW EVENT

**Approved decision:** Record reviewer name or approved identifier, review date, decision, and rationale at record level. Preserve original and second-review values, quotes, and reasons when disagreements occur. Record adjudicator decisions and rationales without overwriting history. Maintain dataset-level version and reviewer metadata as well.

## 5. AES Ohio — EXCLUDED UNTIL ORIGINAL AGREEMENT IS AVAILABLE

**Approved decision:** Do not infer original-agreement labels from an amendment. Prepare and review AES Ohio separately if the original agreement becomes available. Do not treat its exclusion as automatic proof that the full five-document benchmark scope is complete.

## Current Phase 2 status — no finalization

- The 64 existing candidate records remain `CANDIDATE_NOT_FINAL`.
- The four UNCLEAR cases remain unresolved and require independent review or expert adjudication:
  1. DBS — `03_dbs_mitc` — `prepayment_terms`
  2. Bajaj Housing Finance — `13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi` — `late_payment_or_default_interest`
  3. Bajaj Housing Finance — `13_bajajhousingfinance_MITC-Retail__Secured_and_Unsecured_-Hindi` — `guarantees`
  4. Muthoot Homefin — `09_muthoothomefin_MHIL-MITC` — `prepayment_terms`
- Bajaj visual verification remains outstanding.
- Muthoot pages 5–7 remain uninspected.
- No final Gold dataset has been approved or created.
- Approval of these five policy decisions is **not** approval of the final dataset.
- Phase 3 must not start.
