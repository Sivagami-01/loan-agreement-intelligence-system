"""src/risk/prefilter.py

Deterministic keyword/phrase pre-filter for Stage 4a-2 (whole-document risk scan).

Grounded strictly in docs/labeling_guideline.md risk category definitions and
general loan-agreement terminology (Financial terms, Repayment, Penalties and
charges, Collateral, Default conditions, Termination, Covenants). No test-set
tuning is performed here.
"""

from __future__ import annotations

import re
from typing import Any

# Organised by guideline risk category and general commercial/consumer loan triggers.
# Patterns use regex word boundaries where short, or prefix matching for stems.
GUIDELINE_KEYWORD_PATTERNS: tuple[tuple[str, str], ...] = (
    # Financial terms
    ("interest", r"\binterest\b"),
    ("rate_of_interest", r"\b(?:rate of interest|loan rate|effective rate|roi|base rate|prime rate|libor|sofr|repo rate|eblr|mclr|benchmark|floating rate|fixed rate|default rate|annual percentage rate|apr)\b"),
    ("margin_spread_reset", r"\b(?:margin|spread|basis points?|bps|reset|per annum|p\.a\.)\b"),
    ("principal_amount", r"\b(?:principal|loan amount|commit\w*|credit facility|facility amount|credit limit|sanction(?:ed)?|drawdown|disburs\w*)\b"),
    # Repayment
    ("repayment_terms", r"\b(?:repay\w*|prepay\w*|pre-pay\w*|foreclos\w*|amortiz\w*|amortis\w*|install?ment\w*|emi|maturity|matur(?:e|ing)|waterfall|application of payments?|balloon|pro rata|closure)\b"),
    ("payable_due", r"\b(?:due and payable|payable on|payment date|schedule of payment)\b"),
    # Penalties and charges
    ("penalties_fees", r"\b(?:penal\w*|penalt\w*|late (?:fee|charge|payment)|overdue|surcharge|bounce|dishonou?r\w*|liquidated damages|breakage)\b"),
    ("charges_expenses", r"\b(?:fees?|charges?|stamp duty|processing fee|commitment fee|upfront fee|administrative fee|legal cost\w*|recovery cost\w*|collection cost\w*|indemnif\w*|reimburs\w*|compensat\w*)\b"),
    # Collateral
    ("collateral_security", r"\b(?:collateral\w*|securit(?:y|ies|ize|ise)\w*|mortgage\w*|pledg\w*|hypothecat\w*|lien\w*|encumb\w*|guarant(?:or|ee|y)\w*|suret(?:y|ies)|pledgor|property|premises|gold|jewels?|original documents?)\b"),
    ("enforcement_asset", r"\b(?:sarfaesi|reposses\w*|possession|seiz\w*|auction\w*|title deed\w*|insur\w*|valuat\w*|margin call|legal process|without notice)\b"),
    # Default conditions
    ("default_triggers", r"\b(?:default\w*|event of default|breach\w*|cross-default|cross default|non-payment|nonpayment|fail(?:s|ed|ure)? to pay|delinquen\w*|npa|non-performing|sma)\b"),
    ("insolvency_cure", r"\b(?:insolven\w*|bankrupt\w*|winding up|liquidat\w*|receivership|material adverse|misrepresent\w*|cure period|grace period|notice of default)\b"),
    # Termination
    ("termination_accel", r"\b(?:terminat\w*|accelerat\w*|immediately due|recall(?:able|ed|ing)?|cancel(?:l?ation|l?ed)?|suspend\w*|revok\w*|rescind\w*|declare due|demand immediate|demand repayment|enforce\w*)\b"),
    # Covenants
    ("covenant_undertaking", r"\b(?:covenant\w*|undertak\w*|shall not|must not|agrees not to|prohibit\w*|negative pledge|pari passu|subordinat\w*|change of control|prior written consent)\b"),
    ("financial_ratios", r"\b(?:net worth|leverage|debt[- ]to[- ]equity|debt service|coverage ratio|ebitda|ebit|tangible net|working capital|financial ratio\w*)\b"),
    ("reporting_inspection", r"\b(?:financial statement\w*|audit\w*|inspect\w*|books and records|deliver(?:ing)? notice|notify|notice to (?:the )?(?:bank|lender)|furnish|credit bureau|cibil|cic|disclos\w*|credit verification)\b"),
    ("restrictions_transfers", r"\b(?:dispos(?:e|al)|sell|transfer|assign\w*|merger|amalgam\w*|dividend\w*|distribution\w*|additional debt|indebtedness)\b"),
    # General legal/financial risk remedies & powers
    ("lender_powers_remedies", r"\b(?:set-?off|set off|withhold\w*|gross-?up|gross up|sole discretion|waiver|remed(?:y|ies)|arbitration|jurisdiction|recover\w*)\b"),
)

_COMPILED_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (name, re.compile(pat, re.IGNORECASE)) for name, pat in GUIDELINE_KEYWORD_PATTERNS
)


def match_keywords(text: str) -> list[str]:
    """Return list of matched rule group names for clause text."""
    if not text:
        return []
    hits: list[str] = []
    for name, rx in _COMPILED_PATTERNS:
        if rx.search(text):
            hits.append(name)
    return hits


def is_risk_candidate(text: str) -> bool:
    """Return True if clause text triggers any guideline/loan-risk keyword."""
    return bool(match_keywords(text))


def prefilter_clauses(
    clauses: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Partition splitter clauses into (passed, dropped) deterministically."""
    passed: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    for item in clauses:
        hits = match_keywords(str(item.get("text", "")))
        enriched = dict(item)
        enriched["matched_keywords"] = hits
        if hits:
            passed.append(enriched)
        else:
            dropped.append(enriched)
    return passed, dropped
