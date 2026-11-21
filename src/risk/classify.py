"""src/risk/classify.py

Stage 4a: Batched LLM clause risk classifier with guideline grounding,
dev-only severity calibration examples, strict anti-leakage sanitization,
JSON retry/unclassified fallback, and deterministic numeric guardrails.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

import yaml

from src.llm.gemini_client import GeminiClient, load_model_config
from src.qa.check_numbers import check_numbers
from src.risk.severity_rules import ALLOWED_CLAUSE_TYPES, ALLOWED_FEATURES, evaluate_clause_severity

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RISK_CONFIG = ROOT / "config" / "risk.yaml"
GUIDELINE_PATH = ROOT / "docs" / "labeling_guideline.md"

ALLOWED_DOC_TYPES = {"sec_agreement", "indian_mitc"}
ALLOWED_RULES = {"R1", "R2", "R3", "R4", "N1", "S1", "S2", "S3", "S4", "S5", "none"}

# Four short clause examples taken ONLY from dev documents (zero test documents,
# zero silver rationales from CSV). Used solely for severity calibration.
DEV_SEVERITY_EXAMPLES: list[tuple[str, str, str, str]] = [
    (
        "Low",
        "Penalties and charges",
        "Section 2.03 Commitment Fees. There are no commitment fees payable by the Borrower hereunder.",
        "Explicitly states no commitment fee is charged.",
    ),
    (
        "Medium",
        "Covenants",
        "Customer shall not sell, offer to sell, lease, rent, hire or in any other manner dispose, transfer or surrender use and possession of any Equipment;",
        "Standard negative covenant restricting unauthorized collateral disposal (capped at Medium under R2).",
    ),
    (
        "High",
        "Repayment",
        "No Loan Agreement is prepayable by Customer, in whole or in part, without the express written consent of Lender in its sole discretion.",
        "Total prepayment lockout subject to sole lender discretion.",
    ),
    (
        "Critical",
        "Collateral",
        "Lender may, with or without notice and without legal process, enter upon any property owned, leased or otherwise under the real or apparent control of Borrower",
        "Permits collateral seizure without notice or court process.",
    ),
]


def load_risk_config(config_path: Path | None = None) -> dict[str, Any]:
    """Loads Stage 4a classifier settings from config/risk.yaml."""
    path = config_path or DEFAULT_RISK_CONFIG
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _load_guideline_rules_text() -> str:
    """Reads the Risk categories, Severity, and R1-R3 sections from docs/labeling_guideline.md."""
    if not GUIDELINE_PATH.is_file():
        return ""
    text = GUIDELINE_PATH.read_text(encoding="utf-8")
    start = text.find("## Risk categories")
    end = text.find("## Interpretation rules")
    if start != -1 and end != -1 and end > start:
        section = text[start:end].strip()
    else:
        section = text.strip()
    # Exclude "Other" so the model strictly chooses among the 7 allowed categories.
    lines = [ln for ln in section.splitlines() if not ln.lstrip().startswith("| Other |")]
    return "\n".join(lines).strip()


def _sanitize_clause_for_prompt(clause: dict[str, Any]) -> dict[str, str]:
    """Extracts ONLY non-label fields so silver labels/rationales can never enter the prompt."""
    cid = str(clause.get("clause_id", "")).strip()
    raw_txt = clause.get("clause_text") if clause.get("clause_text") is not None else clause.get("text", "")
    ctext = " ".join(str(raw_txt or "").split()).strip()
    loc_parts: list[str] = []
    for key in ("page", "section", "page_section", "location"):
        val = str(clause.get(key, "") or "").strip()
        if val and val not in loc_parts:
            loc_parts.append(val)
    loc = " | ".join(loc_parts)
    out = {"clause_id": cid, "clause_text": ctext}
    if loc:
        out["page_or_section"] = loc
    return out


def _make_batches(clauses: list[dict[str, str]], batch_size: int) -> list[list[dict[str, str]]]:
    """Groups clauses into batches up to batch_size without duplicate clause_ids in one batch."""
    batches: list[list[dict[str, str]]] = []
    cur: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    limit = max(1, int(batch_size))
    for item in clauses:
        cid = item["clause_id"]
        if len(cur) >= limit or (cid and cid in seen_ids):
            batches.append(cur)
            cur = []
            seen_ids = set()
        cur.append(item)
        if cid:
            seen_ids.add(cid)
    if cur:
        batches.append(cur)
    return batches


def _v4_finance_review_rules() -> str:
    return (
        "\n3. FINANCE-REVIEW SCAN REFINEMENTS (N1, S1-S5 — apply whenever they match):\n"
        "   - `N1` (`none` / `none`): Pure definitions (UNLESS the definition states a rate, margin, fee, penalty, default trigger, or a repayment amount/date), representations and warranties about corporate status, historical financial statements or regulatory compliance, closing conditions, routine further-assurance/UCC-filing perfection mechanics, and standalone headings -> mark `category`: \"none\", `severity`: \"none\".\n"
        "   - `S1` (Default remedies): Standard post-default remedies (UCC secured-party rights over pledged collateral, application of collateral proceeds, attorney-in-fact for insurance claims, lender's right to perform on notice and charge costs, lender loan assignment/transfer) = `Medium`. Rate `High` ONLY if the lender gets something beyond the pledged asset (other property/guarantees, self-help repossession without notice, sole-discretion choice across other collateral, joint-and-several co-borrower liability); `Critical` only per `R2`.\n"
        "   - `S2` (Cross-default): `High` if there is NO cure period or it reaches affiliates or other lenders unconditionally; `Medium` if it requires acceleration of the other debt or expiration of an applicable cure period.\n"
        "   - `S3` (Pension/ERISA & regulatory defaults): Pension (ERISA) and similar regulatory-event default triggers with a notice/cure period = `Medium`.\n"
        "   - `S4` (Broad borrower indemnity): General/broad borrower indemnification clauses = `Covenants` / `High` (NOT Penalties and charges).\n"
        "   - `S5` (Routine reporting & insurance): Routine financial/default reporting and standard insurance-maintenance covenants = `Covenants` / `Low`.\n"
    )


def _v5_type_and_features_guidance() -> str:
    types_str = ", ".join(ALLOWED_CLAUSE_TYPES)
    feats_str = ", ".join(ALLOWED_FEATURES)
    return (
        "CLASSIFICATION DECISION CHECKLIST (v5 structured type + feature extraction — DO NOT output severity):\n"
        "1. CATEGORY (7 categories or `none`):\n"
        "   - `none`: Non-risk definitions (stating NO rate/margin/fee/penalty/default trigger/payment date or amount), corporate-status/financial-statement/regulatory representations, closing conditions, routine UCC filing/perfection mechanics, headings, and pure boilerplate (N1).\n"
        "   - `Financial terms` (R4): interest rate, rate-reset, benchmark/spread/margin, principal/facility amount, disbursement terms.\n"
        "   - `Penalties and charges` (R4): ALL borrower fees & charges (upfront, commitment, processing, admin, closing, legal, recovery, breakage, increased costs, stamp taxes, penal/default interest, late fees), or lender delay compensation.\n"
        "   - `Covenants` (R1/S4/S5): financial ratios, net worth, leverage, reporting, inspection, insurance, negative covenants restricting debt/sales/mergers/dividends/use-of-funds, third-party disclosures, disclaimers, and broad borrower indemnities (S4).\n"
        "   - `Repayment`: scheduled payments, amortization, balloons, direct/auto-debit, appropriation waterfall, prepayment/lockout terms.\n"
        "   - `Collateral`: liens, mortgages, pledges, negative pledges on collateral, guarantees, suretyship, LTV calls, default remedies on collateral/guarantees, title deed return.\n"
        "   - `Default conditions`: Event of Default triggers (payment default, insolvency, change of control, cross-default, other default triggers) and cure/grace periods.\n"
        "   - `Termination`: acceleration rights, commitment termination/cancellation, stated expiration/maturity dates, illegality termination/prepayment.\n"
        "2. CLAUSE_TYPE (choose EXACTLY ONE from this closed list):\n"
        f"   [{types_str}]\n"
        "   - RULE FOR DEFINITIONS: A definition that states a rate, fee, penalty, default trigger, or payment amount/date takes the type of what it states (`rate_term`, `fee_or_cost`, `cross_default`, `change_of_control_trigger`, `repayment` -> `other`/`rate_term`/etc.), otherwise `definition`.\n"
        "   - Use `borrower_protective` when the clause protects the borrower (e.g. one-time cure right, penalty-free prepayment, deed return SLA, delay compensation).\n"
        "   - Use `remedy_on_default` for post-default secured-party rights, proceeds application, lender right to perform, insurance attorney-in-fact, or loan transfer/defense waiver.\n"
        "   - Use `indemnity` for indemnification / hold-harmless / reimbursement-of-loss obligations (categorize broad borrower indemnities under `Covenants`).\n"
        "3. FEATURES (boolean dict; include all keys that are true, e.g. {\"automatic\": true}; omitted keys default to false):\n"
        f"   [{feats_str}]\n"
        "   - Only set a feature to true when clearly supported by the clause text:\n"
        "     * `automatic` + `no_notice`: clause itself states immediate automatic acceleration/termination/seizure without notice.\n"
        "     * `cure_or_grace_10_days_or_more`: explicitly gives >= 10 days cure/grace/notice period.\n"
        "     * `beyond_pledged_asset`: reaches property/guarantees outside the pledged asset; `self_help_without_notice`: entry/repossession without judicial process or notice; `joint_and_several`: explicit joint and several co-borrower liability.\n"
        "     * `broad_or_uncapped` & `survives_repayment`: broad indemnity covering any/all claims or expressly surviving repayment/termination.\n"
        "     * `penal_rate_or_default_charge`: penal/default interest or punitive overdue penalty rate/recovery charge (NOT routine breakage/increased costs/legal reimbursement/stamp tax).\n"
    )


def _prompt_version_guidance(prompt_version: str) -> str:
    if prompt_version.startswith("v5"):
        return _v5_type_and_features_guidance()
    if prompt_version.startswith("v4"):
        return _prompt_version_guidance("v3") + _v4_finance_review_rules()
    if prompt_version == "v3" or prompt_version.startswith("v3"):
        return (
            "CLASSIFICATION DECISION CHECKLIST (v3 whole-document scan — apply every boundary carefully):\n"
            "0. NON-RISK FILTER (`none`):\n"
            "   - Use `category`: \"none\", `severity`: \"none\" ONLY for pure boilerplate, table of contents, section headings without operative terms, signature blocks, party address blocks, definitions of purely administrative words (e.g. 'Business Day', 'Person'), counterpart/severability/governing-law mechanics, or harmless disclaimers that create NO borrower financial obligation, restriction, risk, penalty, security burden, default trigger, or termination/acceleration right.\n"
            "   - Do NOT mark a genuine risk/fee/rate/covenant/collateral/default/termination/repayment clause as `none` (and if it is borrower-protective under R3, classify its category and mark `Low` with `[borrower-protective] ` instead of `none`).\n"
            "1. CATEGORY BOUNDARIES:\n"
            "   - `Financial terms` (R4): ONLY interest rate, rate-reset, benchmark/spread/margin, and principal/facility/commitment amount or disbursement terms.\n"
            "   - `Penalties and charges` (R4): ALL fees and charges payable by the borrower (upfront fee, commitment fee, processing fee, administrative fee, closing fee, legal/recovery/audit/collection fees, default interest surcharges, late fees, penal charges, LIBOR breakage, cost indemnities), or lender delay compensation.\n"
            "   - `Covenants` (R1): promises or caps on financial ratios, minimum net worth, leverage, reporting, inspection, negative covenants restricting debt/sales/mergers/dividends/use-of-funds, third-party disclosures, and 'read the full agreement' disclaimers.\n"
            "   - `Repayment`: scheduled principal/interest payment dates, amortization/balloons, EMI appropriation order, direct/auto-debit payment mechanics, non-recourse payment waterfall limits, and prepayment rights/lockouts/restrictions.\n"
            "   - `Collateral`: granting/perfecting security interests/liens/mortgages/pledges, negative pledges against competing liens, guarantees/suretyship, LTV margin calls, collateral repossession/sale, title deed return rules/delays.\n"
            "   - `Default conditions`: Clauses defining WHAT EVENTS trigger an Event of Default (nonpayment, bankruptcy, judgment, cross-default definition, insecurity/price-drop default) and their cure/grace windows.\n"
            "   - `Termination`: Clauses giving remedies to terminate/cancel commitments or accelerate the loan after default (`declare terminated`, `declare immediately due`, Termination Notice), stated maturity/expiration dates, and irrevocable availability cutoffs.\n"
            "2. SEVERITY BOUNDARIES (check none -> R3 -> Low -> Medium -> High -> Critical):\n"
            "   - `none`: Non-risk boilerplate / pure mechanics (`category=\"none\"`, `severity=\"none\"`).\n"
            "   - `R3` (`Low` + rationale MUST start with `[borrower-protective] `): Clauses protecting the borrower (penalty-free prepayment right, lender pays borrower for delaying deed return, timeline to return original title deeds, ban on capitalizing unpaid penal charges, non-recourse personal liability shield, fee-free 60-day exit window).\n"
            "   - `Low`: Routine, baseline structural or fee/rate terms WITHOUT extra risk, punitive cost, restrictive covenant, or unilateral lender discretion (e.g., baseline credit limit, standard floating/Prime rate, scheduled maturity date, modest <=0.50% fee, routine reporting/inspection).\n"
            "   - `Medium`: Meaningful risk, cost, or restriction with bounded scope/protection per R2 (standard negative/financial covenants, default triggers with >=10d cure, +2% to +4% default surcharge, 5% late fee, 365/360 math, ordinary mortgages/pledges, foreclosure with notice).\n"
            "   - `High`: Needs >=1 of: (a) ZERO or VERY SHORT cure period (<=5d, immediate price-drop/cross-default/ownership-change EOD), (b) steep/punitive/retroactive charge (+5% default rate, >=18% p.a. overdue charge, heavy recovery fee, prepayment lockout or >=3% fee), or (c) strong unilateral lender power (optional acceleration/termination BY NOTICE, subjective insecurity/MAC, sole-discretion EOD, broad survival indemnity, cross-collateralization). Default conditions triggers alone without automatic acceleration or collateral loss are AT MOST High (never Critical).\n"
            "   - `Critical`: ONLY when the clause ITSELF states (a) AUTOMATIC acceleration or termination IMMEDIATELY AND WITHOUT NOTICE, OR (b) direct LOSS / SEIZURE / FORECLOSURE / AUCTION SALE of the main collateral without court process or notice / under SARFAESI auction.\n"
        )
    if prompt_version == "v2":
        return (
            "CLASSIFICATION DECISION CHECKLIST (v2 — apply every boundary carefully):\n"
            "1. CATEGORY BOUNDARIES:\n"
            "   - `Financial terms`: ONLY interest rate, margin/spread, credit/facility amount or limit definitions, closing/admin fees, benchmark/reset mechanics.\n"
            "   - `Covenants` (R1): promises or caps on financial ratios, minimum net worth, leverage, reporting, inspection, negative covenants restricting debt/sales/mergers/dividends/use-of-funds, third-party disclosures, and 'read the full agreement' disclaimers.\n"
            "   - `Repayment`: scheduled principal/interest payment dates, amortization/balloons, EMI appropriation order, direct/auto-debit payment mechanics, non-recourse payment waterfall limits, and prepayment rights/lockouts/restrictions.\n"
            "   - `Penalties and charges`: default interest surcharges, late payment fees, penal charges, recovery fees, audit charges, commitment-fee waivers/charges, LIBOR breakage/cost reimbursements.\n"
            "   - `Collateral`: granting/perfecting security interests/liens/mortgages/pledges, negative pledges against competing liens, guarantees/suretyship, LTV margin calls, collateral repossession/sale, title deed return rules/delays.\n"
            "   - `Default conditions`: Clauses defining WHAT EVENTS trigger an Event of Default (nonpayment, bankruptcy, judgment, cross-default definition, insecurity/price-drop default) and their cure/grace windows.\n"
            "   - `Termination`: Clauses giving remedies to terminate/cancel commitments or accelerate the loan after default (`declare terminated`, `declare immediately due`, Termination Notice), stated maturity/expiration dates, and irrevocable availability cutoffs.\n"
            "2. SEVERITY BOUNDARIES (check R3 -> Low -> Medium -> High -> Critical):\n"
            "   - `R3` (`Low` + rationale MUST start with `[borrower-protective] `): Clauses that protect the borrower rather than the lender (penalty-free prepayment right, lender pays borrower for delaying deed return, commitment to return original title deeds within a set timeline, ban on capitalizing unpaid penal charges, non-recourse personal liability shield, fee-free 60-day exit window on disadvantageous changes).\n"
            "   - `Low`: Routine, baseline structural or administrative terms WITHOUT extra risk, punitive cost, restrictive covenant, or unilateral lender discretion. Includes: baseline facility-amount/credit-limit definitions (`Credit Facility means $X`, `Maximum Commitment`), standard floating base rate or flat Prime rate definitions, normal scheduled maturity/commitment termination dates, routine monthly/quarterly interest or principal installment schedules (including standard 3-year/8-year payment dates), modest or standard closing/documentation/commitment fees (<= 0.50% or small flat admin fee), routine GAAP financial reporting / inspection / prompt-notice / general-use-of-proceeds / boilerplate priority/lien-perfection closing conditions, and normal administrative cash-waterfall mechanics (R2: leftover cash collateral reimbursement, Federal Reserve Bank assignment of lender advances).\n"
            "   - `Medium`: Meaningful risk, cost, or restriction with bounded scope/protection. Includes per R2: standard negative covenants (no extra debt, no asset sales, no mergers/liquidation, negative pledge, dividend block on default), standard financial covenants (minimum net worth, Debt/EBITDA, coverage ratios), default triggers WITH a substantive cure period (>= 10 days, e.g. 10-day payment grace, 30-day/60-day judgment cure, 30-day involuntary bankruptcy dismissal cure, 180-day management cure), moderate default/late surcharges (+2% to +4% default rate, 5% late fee after >=10d grace, 365/360 math, LIBOR breakage costs, 4.5% high interest spread, <=3.5% admin fee, balloon principal >30%), auto-debit authorizations, deposit-account lockups, ordinary mortgages/pledges, judicial/non-judicial foreclosure notices.\n"
            "   - `High`: Requires >=1 of: (a) ZERO or VERY SHORT cure period (<= 5 days, including 0 days principal / 3 days interest, immediate market-price-decline EOD, zero-threshold cross-default EOD, or >10% ownership-change EOD), (b) steep or punitive/retroactive charge (+5% default surcharge, >= 18% p.a. overdue charge, large recovery/enforcement fees, prepayment lockout or >= 3% / refinance fee, early termination fee on bank termination), or (c) strong unilateral lender power (optional acceleration/termination BY NOTICE, subjective insecurity/MAC default, unilateral advance-rate or net-worth adjustment, sole-discretion EOD determination, immediate overadvance recall without notice, broad survival indemnity, 1-year lawsuit limit, exclusive investment-banking mandate, unconditional suretyship without exhausting borrower, cross-collateralization, forced Event-of-Loss prepayment + premium). Per R2 clarification: Default conditions clauses ONLY defining a trigger without stating immediate automatic acceleration or collateral loss are AT MOST High (never Critical).\n"
            "   - `Critical`: ONLY when the clause ITSELF states (a) AUTOMATIC acceleration or termination IMMEDIATELY AND WITHOUT NOTICE (`automatically terminate... without notice`, `immediately and without notice... due and payable`), OR (b) direct LOSS / SEIZURE / FORECLOSURE / AUCTION SALE of the main collateral without court process or notice / under SARFAESI auction. Acceleration/termination `by notice` or `by written notice` is High, NOT Critical.\n"
        )
    return (
        "INSTRUCTIONS:\n"
        "- Classify each clause into EXACTLY ONE of the 7 allowed categories and EXACTLY ONE of the 4 allowed severities.\n"
        "- Apply rules R1, R2 (including the Default conditions clarification), and R3 faithfully.\n"
    )


def build_risk_prompt(
    doc_type: str,
    batch_clauses: list[dict[str, str]],
    categories: list[str],
    severities: list[str],
    prompt_version: str = "v1",
) -> str:
    """Builds the risk classification prompt using guideline rules and dev-only examples."""
    if doc_type not in ALLOWED_DOC_TYPES:
        raise ValueError(f"Unsupported doc_type={doc_type!r}; expected one of {sorted(ALLOWED_DOC_TYPES)}")

    doc_context = (
        "SEC corporate loan / credit agreement clauses."
        if doc_type == "sec_agreement"
        else "Indian bank/NBFC/HFC Most Important Terms & Conditions (MITC) clauses under RBI rules."
    )
    guideline_text = _load_guideline_rules_text()

    is_v5 = prompt_version.startswith("v5")
    is_v4 = prompt_version.startswith("v4")
    is_scan = prompt_version.startswith(("v3", "v4", "v5"))
    clauses_json = json.dumps(batch_clauses, indent=2, ensure_ascii=False)
    allowed_cats = list(categories) + (["none"] if is_scan and "none" not in categories else [])
    cats_str = ", ".join(f'"{c}"' for c in allowed_cats)

    if is_v5:
        v5_examples = (
            '- N1 pattern example -> {"category": "none", "clause_type": "definition", "features": {}, "rationale": "Pure administrative definition stating no financial rate, fee, trigger, or payment term."}\n'
            '- S1 pattern example -> {"category": "Collateral", "clause_type": "remedy_on_default", "features": {}, "rationale": "Standard post-default UCC secured-party remedy over pledged collateral without extra-asset reach or no-notice self-help."}\n'
            '- Critical acceleration pattern example -> {"category": "Termination", "clause_type": "acceleration_or_termination_right", "features": {"automatic": true, "no_notice": true}, "rationale": "Automatically accelerates all obligations immediately without notice upon bankruptcy."}\n'
        )
        return (
            f"You are a structured contract risk analyzer reviewing {doc_context}\n"
            "Classify each clause's `category`, `clause_type`, boolean `features`, and concise 1-sentence `rationale`.\n"
            "Do NOT output a `severity` field; severity is computed deterministically from `clause_type` and `features`.\n\n"
            f"{_prompt_version_guidance(prompt_version)}\n"
            "=== PATTERN EXAMPLES (SYNTHETIC) ===\n"
            f"{v5_examples}\n"
            "=== OUTPUT JSON CONTRACT ===\n"
            "Return ONLY a valid JSON array (no markdown fences or commentary), one object per input clause in exact order:\n"
            '[{"clause_id": "...", "category": "...", "clause_type": "...", "features": {"flag": true}, '
            '"rationale": "One short plain-English sentence."}]\n'
            f"Allowed categories (exact spelling, do NOT invent categories or use 'Other'): [{cats_str}]\n"
            "CRITICAL GROUNDING RULE FOR RATIONALE:\n"
            "- Write exactly one concise plain-English sentence.\n"
            "- NEVER include any number, date, percentage, or money amount in `rationale` unless that exact token appears in that clause's `clause_text`.\n"
            "- For non-risk N1 clauses, set `category` to `\"none\"` and `clause_type` to `definition`, `representation`, `closing_condition`, or `heading_or_boilerplate`.\n\n"
            f"INPUT CLAUSES ({len(batch_clauses)} items):\n{clauses_json}\n"
        )

    examples_lines = []
    for sev, cat, txt, note in DEV_SEVERITY_EXAMPLES:
        examples_lines.append(f'- {sev} example (Category: {cat}): "{txt}" -> {note}')
    if is_scan:
        examples_lines.append(
            '- none example (Category: none, Severity: none): '
            '"This Agreement may be executed in any number of counterparts, each of which shall be an original." '
            '-> Pure execution boilerplate with no borrower financial term, obligation, or risk.'
        )
    if is_v4:
        examples_lines.append(
            '- N1 pattern example (Category: none, Severity: none): '
            '"\\"Business Day\\" means any day other than a Saturday, Sunday, or legal holiday on which commercial banks are authorized to close." '
            '-> Pure administrative definition stating no rate, fee, penalty, default trigger, or repayment amount/date (N1).'
        )
        examples_lines.append(
            '- S1 pattern example (Category: Collateral, Severity: Medium): '
            '"Upon an Event of Default, Secured Party may exercise all standard rights and remedies of a secured creditor under the Uniform Commercial Code with respect to the Pledged Collateral." '
            '-> Standard post-default secured-party UCC remedy over pledged collateral without self-help without notice or extra-asset reach (S1).'
        )
    examples_block = "\n".join(examples_lines)

    sevs_str = ", ".join(f'"{s}"' for s in (list(severities) + (["none"] if is_scan and "none" not in severities else [])))
    if is_v4:
        rules_contract = '"R1"|"R2"|"R3"|"R4"|"N1"|"S1"|"S2"|"S3"|"S4"|"S5"|"none"'
        rules_label = "R1-R4 and N1, S1-S5"
    elif is_scan:
        rules_contract = '"R1"|"R2"|"R3"|"R4"|"none"'
        rules_label = "R1-R4"
    else:
        rules_contract = '"R1"|"R2"|"R3"|"none"'
        rules_label = "R1-R3"
    none_note = (
        '\n- If `category` is `"none"`, set `severity` to `"none"` and write one short sentence noting why it is non-risk boilerplate.'
        if is_scan
        else ""
    )

    return (
        f"You are a contract risk classifier reviewing {doc_context}\n"
        f"Follow the labeling guideline categories, severities, and rules {rules_label} below.\n\n"
        f"=== LABELING GUIDELINE (CATEGORIES, SEVERITY, {rules_label}) ===\n"
        f"{guideline_text}\n\n"
        f"{_prompt_version_guidance(prompt_version)}\n"
        "=== SEVERITY CALIBRATION EXAMPLES (DEV-ONLY) ===\n"
        f"{examples_block}\n\n"
        "=== OUTPUT JSON CONTRACT ===\n"
        "Return ONLY a valid JSON array (no markdown fences or commentary), one object per input clause in the exact same order:\n"
        '[{"clause_id": "...", "category": "...", "severity": "...", '
        f'"rationale": "One short plain-English sentence.", "applied_rule": {rules_contract}}}]\n'
        f"Allowed categories (exact spelling, do NOT invent new categories or use 'Other'): [{cats_str}]\n"
        f"Allowed severities (exact spelling): [{sevs_str}]\n"
        "CRITICAL GROUNDING RULE FOR RATIONALE:\n"
        "- Write exactly one concise plain-English sentence.\n"
        "- NEVER include any number, date, percentage, or money amount in `rationale` unless that exact number, date, or amount appears in that clause's `clause_text`.\n"
        f"- If `R3` applies (borrower-protective clause), start `rationale` with `[borrower-protective] `.{none_note}\n\n"
        f"INPUT CLAUSES ({len(batch_clauses)} items):\n{clauses_json}\n"
    )


def _strip_json_fences(raw_text: str) -> str:
    text = (raw_text or "").strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return text


def _parse_batch_json(raw_text: str) -> list[dict[str, Any]] | None:
    """Parses JSON list of clause objects from LLM text, returning None if malformed."""
    cleaned = _strip_json_fences(raw_text)
    if not cleaned:
        return None

    def _unwrap(obj: Any) -> list[dict[str, Any]] | None:
        if isinstance(obj, list):
            if obj and all(isinstance(x, dict) for x in obj):
                return obj
            return [] if isinstance(obj, list) and len(obj) == 0 else None
        if isinstance(obj, dict):
            for key in ("clauses", "results", "items", "predictions"):
                val = obj.get(key)
                if isinstance(val, list) and all(isinstance(x, dict) for x in val):
                    return val
            if "clause_id" in obj:
                return [obj]
        return None

    try:
        parsed = json.loads(cleaned)
        res = _unwrap(parsed)
        if res is not None:
            return res
    except json.JSONDecodeError:
        pass

    # Outermost bracket/brace recovery
    for start_ch, end_ch in (("[", "]"), ("{", "}")):
        s_idx = cleaned.find(start_ch)
        e_idx = cleaned.rfind(end_ch)
        if s_idx != -1 and e_idx > s_idx:
            try:
                parsed = json.loads(cleaned[s_idx : e_idx + 1])
                res = _unwrap(parsed)
                if res is not None:
                    return res
            except json.JSONDecodeError:
                continue
    return None


def _normalize_rule(raw_rule: Any) -> str:
    val = str(raw_rule or "").strip()
    if val in ALLOWED_RULES:
        return val
    upper = val.upper()
    for tag in ("R1", "R2", "R3", "R4", "N1", "S1", "S2", "S3", "S4", "S5"):
        if tag in upper:
            return tag
    return "none"


def _one_sentence(text: str) -> str:
    cleaned = " ".join((text or "").split()).strip()
    return cleaned


def _validate_prediction(
    inp: dict[str, str],
    raw_item: dict[str, Any] | None,
    valid_categories: set[str],
    valid_severities: set[str],
    model_used: str,
    allow_none: bool = False,
    rule_based_v5: bool = False,
) -> dict[str, Any]:
    cid = inp["clause_id"]
    ctext = inp["clause_text"]

    if raw_item is None:
        out = {
            "clause_id": cid,
            "category": "unclassified",
            "severity": "unclassified",
            "rationale": "",
            "applied_rule": "none",
            "number_flag": False,
            "flagged_numbers": [],
            "model_used": model_used,
            "parse_error": True,
        }
        if rule_based_v5:
            out.update(
                {
                    "clause_type": "unclassified",
                    "features": {},
                    "severity_rule": "PARSE_ERROR",
                    "severity_explanation": "Severity unclassified because: parse_error; none",
                }
            )
        return out

    raw_cat = str(raw_item.get("category", "") or "").strip()
    rationale = _one_sentence(str(raw_item.get("rationale", "") or ""))

    if rule_based_v5:
        # Strictly ignore any severity field if emitted by model; derive deterministically via rule table
        raw_ctype = str(raw_item.get("clause_type", "") or "").strip()
        raw_feats = raw_item.get("features") if isinstance(raw_item.get("features"), dict) else {}
        sev_eval = evaluate_clause_severity(
            {"clause_type": raw_ctype, "features": raw_feats, "clause_text": ctext}
        )
        ctype_out = sev_eval["clause_type"]
        if sev_eval["severity"] == "unclassified":
            category = "unclassified"
            severity = "unclassified"
            explanation = sev_eval["explanation"]
        elif sev_eval["category_override"] == "none":
            category = "none"
            severity = "none"
            explanation = sev_eval["explanation"]
        elif raw_cat.lower() == "none":
            category = "none"
            severity = "none"
            explanation = f"Severity none because: {ctype_out}; category marked none"
        else:
            category = raw_cat if raw_cat in valid_categories else "unclassified"
            severity = sev_eval["severity"] if category != "unclassified" else "unclassified"
            explanation = sev_eval["explanation"]

        pref = sev_eval.get("rationale_prefix", "")
        if pref and not rationale.lower().startswith(pref.strip().lower()):
            rationale = pref + rationale

        num_res = check_numbers(answer=rationale, evidence=[{"quote": ctext, "page": 1}], doc_pages=None)
        number_flag = not bool(num_res.get("all_found", True))
        flagged_numbers = list(num_res.get("missing", [])) if number_flag else []
        true_feats = {k: True for k, v in raw_feats.items() if k in ALLOWED_FEATURES and bool(v)}

        return {
            "clause_id": cid,
            "category": category,
            "severity": severity,
            "clause_type": ctype_out,
            "features": true_feats,
            "severity_rule": sev_eval["fired_rule"],
            "severity_explanation": explanation,
            "rationale": rationale,
            "applied_rule": sev_eval["fired_rule"],
            "number_flag": number_flag,
            "flagged_numbers": flagged_numbers,
            "model_used": model_used,
            "parse_error": False,
        }

    raw_sev = str(raw_item.get("severity", "") or "").strip()
    if allow_none and raw_cat.lower() == "none":
        category = "none"
        severity = "none"
    else:
        category = raw_cat if raw_cat in valid_categories else "unclassified"
        severity = raw_sev if raw_sev in valid_severities else "unclassified"
    applied_rule = _normalize_rule(raw_item.get("applied_rule"))

    num_res = check_numbers(answer=rationale, evidence=[{"quote": ctext, "page": 1}], doc_pages=None)
    number_flag = not bool(num_res.get("all_found", True))
    flagged_numbers = list(num_res.get("missing", [])) if number_flag else []

    return {
        "clause_id": cid,
        "category": category,
        "severity": severity,
        "rationale": rationale,
        "applied_rule": applied_rule,
        "number_flag": number_flag,
        "flagged_numbers": flagged_numbers,
        "model_used": model_used,
        "parse_error": False,
    }


def _is_quota_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(tok in msg for tok in ("429", "quota", "resource_exhausted", "rate limit", "daily"))


def classify_clauses(
    doc_type: str,
    clauses: list[dict[str, Any]],
    client: GeminiClient | None = None,
    config: dict[str, Any] | None = None,
    llm_fn: Callable[[str], tuple[str, str]] | None = None,
    prompt_version: str | None = None,
    scan: bool = False,
) -> dict[str, Any]:
    """Classifies clauses into risk category, severity, rationale, and applied_rule.

    Args:
        doc_type: "sec_agreement" or "indian_mitc".
        clauses: list of dicts with clause_id, clause_text (or text), optional page/section.
                 Silver labels and rationales are stripped and never reach the prompt.
        client: optional shared GeminiClient (for cache & cumulative call budget).
        config: optional config dict overriding config/risk.yaml.
        llm_fn: optional deterministic stub `(prompt) -> (raw_text, model_name)` for tests.
        prompt_version: overrides config prompt_version ("v1", "v2", "v3", ...).
        scan: if True, use Stage 4a-2 scan overrides (scan_batch_size, scan_max_calls,
              scan_prompt_version, allow "none" category, and stop cleanly on quota/budget).
    """
    if doc_type not in ALLOWED_DOC_TYPES:
        raise ValueError(f"Unsupported doc_type={doc_type!r}; expected one of {sorted(ALLOWED_DOC_TYPES)}")

    cfg = config if config is not None else load_risk_config()
    model_role = str(cfg.get("model_role", "bulk"))
    temperature = float(cfg.get("temperature", 0.0))
    if scan:
        batch_size = int(cfg.get("scan_batch_size", cfg.get("batch_size", 20)))
        max_calls = int(cfg.get("scan_max_calls", cfg.get("max_calls", 80)))
        ver = prompt_version or str(cfg.get("scan_prompt_version", cfg.get("prompt_version", "v3")))
    else:
        batch_size = int(cfg.get("batch_size", 12))
        max_calls = int(cfg.get("max_calls", 40))
        ver = prompt_version or str(cfg.get("prompt_version", "v1"))
    retry_limit = int(cfg.get("retry_on_invalid_json", 1))
    allow_none = scan or ver.startswith(("v3", "v4", "v5"))
    rule_based_v5 = ver.startswith("v5")

    categories = list(cfg.get("categories", []))
    severities = list(cfg.get("severities", []))
    valid_categories = set(categories)
    valid_severities = set(severities)

    models_cfg = load_model_config()
    configured_model = models_cfg.get(model_role, "gemini-3.5-flash-lite")

    if client is None and llm_fn is None:
        client = GeminiClient()

    sanitized = [_sanitize_clause_for_prompt(c) for c in clauses]
    batches = _make_batches(sanitized, batch_size)

    live_before = client.api_calls_made if client is not None else 0
    calls_made = 0
    budget_stopped = False
    quota_stopped = False
    model_used_counts: dict[str, int] = {}
    errors: list[str] = []
    all_results: list[dict[str, Any]] = []

    for batch in batches:
        prompt = build_risk_prompt(
            doc_type=doc_type,
            batch_clauses=batch,
            categories=categories,
            severities=severities,
            prompt_version=ver,
        )
        cur_prompt = prompt
        attempts = 1 + max(0, retry_limit)
        parsed_items: list[dict[str, Any]] | None = None
        batch_model = configured_model

        for attempt in range(attempts):
            if llm_fn is None:
                assert client is not None
                if client.api_calls_made >= max_calls:
                    budget_stopped = True
                    break
            calls_made += 1
            try:
                if llm_fn is not None:
                    raw_text, batch_model = llm_fn(cur_prompt)
                else:
                    assert client is not None
                    raw_text = client.generate(cur_prompt, model_alias=model_role, temperature=temperature)
                    batch_model = client.last_model_used or configured_model
            except Exception as exc:
                errors.append(f"{type(exc).__name__}: {str(exc)[:180]}")
                parsed_items = None
                if _is_quota_error(exc):
                    quota_stopped = True
                break

            model_used_counts[batch_model] = model_used_counts.get(batch_model, 0) + 1
            parsed_items = _parse_batch_json(raw_text)
            if parsed_items is not None:
                break
            if attempt + 1 < attempts:
                cur_prompt = (
                    "Previous output was NOT valid JSON array matching the schema. Return ONLY JSON array.\n\n"
                    + prompt
                )

        if budget_stopped or quota_stopped:
            break

        if parsed_items is None:
            for inp in batch:
                all_results.append(
                    _validate_prediction(
                        inp,
                        None,
                        valid_categories,
                        valid_severities,
                        batch_model,
                        allow_none=allow_none,
                        rule_based_v5=rule_based_v5,
                    )
                )
            continue

        by_id: dict[str, dict[str, Any]] = {}
        for item in parsed_items:
            cid = str(item.get("clause_id", "") or "").strip()
            if cid and cid not in by_id:
                by_id[cid] = item

        for idx, inp in enumerate(batch):
            matched = by_id.get(inp["clause_id"])
            if matched is None and idx < len(parsed_items):
                cand = parsed_items[idx]
                cand_id = str(cand.get("clause_id", "") or "").strip()
                if not cand_id or cand_id == inp["clause_id"]:
                    matched = cand
            all_results.append(
                _validate_prediction(
                    inp,
                    matched,
                    valid_categories,
                    valid_severities,
                    batch_model,
                    allow_none=allow_none,
                    rule_based_v5=rule_based_v5,
                )
            )

    live_after = client.api_calls_made if client is not None else 0
    fallback_calls = sum(cnt for m, cnt in model_used_counts.items() if m != configured_model)
    return {
        "doc_type": doc_type,
        "prompt_version": ver,
        "results": all_results,
        "calls_made": calls_made,
        "live_calls_made": live_after - live_before,
        "model_used_counts": model_used_counts,
        "configured_model": configured_model,
        "fallback_calls": fallback_calls,
        "flagged_number_count": sum(1 for r in all_results if r["number_flag"]),
        "unclassified_count": sum(
            1 for r in all_results if r["category"] == "unclassified" or r["severity"] == "unclassified"
        ),
        "budget_stopped": budget_stopped,
        "quota_stopped": quota_stopped,
        "errors": errors,
    }
