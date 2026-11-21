"""src/risk/severity_rules.py

Deterministic first-match severity rule evaluator for Stage 4a-4 (prompt v5).

Loads config/severity_rules.yaml. Given a clause dict containing:
- `clause_type` (one of the 21 closed types; unknown -> "unclassified")
- `features` (dict of booleans from the 15 closed features)
- optional `clause_text` (used ONLY to infer optional sub-context helpers
  `caused_by_illegality` and `taxes_or_routine_small_charge` when not
  explicitly set in features)

Exports:
- `ALLOWED_CLAUSE_TYPES`, `ALLOWED_FEATURES`, `load_severity_rules`
- `evaluate_clause_severity(clause, rules_cfg=None)` -> dict with `severity`,
  `category_override`, `rationale_prefix`, `fired_rule`, `fired_features`, `explanation`
- `explain(clause, rules_cfg=None)` -> `"Severity <X> because: <type>; <features that fired>"`
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RULES_PATH = ROOT / "config" / "severity_rules.yaml"

ILLEGALITY_RE = re.compile(r"\b(?:unlawful|illegal|illegality)\b", re.IGNORECASE)
TAX_OR_SMALL_FEE_RE = re.compile(
    r"\b(?:stamp\s+(?:or\s+other\s+similar\s+)?tax(?:es)?|no\s+commitment\s+fee|zero\s+fee|statutory\s+lev(?:y|ies))\b",
    re.IGNORECASE,
)


def load_severity_rules(path: Path | None = None) -> dict[str, Any]:
    """Load severity rule configuration from config/severity_rules.yaml."""
    target = path or DEFAULT_RULES_PATH
    with target.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


_DEFAULT_CFG = load_severity_rules()
ALLOWED_CLAUSE_TYPES: tuple[str, ...] = tuple(_DEFAULT_CFG.get("clause_types", []))
ALLOWED_FEATURES: tuple[str, ...] = tuple(_DEFAULT_CFG.get("features", []))


def _coerce_features(raw_features: Any, clause_text: str = "") -> dict[str, bool]:
    feat_in = raw_features if isinstance(raw_features, dict) else {}
    out: dict[str, bool] = {}
    for k in ALLOWED_FEATURES:
        out[k] = bool(feat_in.get(k, False))
    # Optional rule helper flags (can be passed explicitly in unit tests or inferred from text)
    if "caused_by_illegality" in feat_in:
        out["caused_by_illegality"] = bool(feat_in["caused_by_illegality"])
    else:
        out["caused_by_illegality"] = bool(clause_text and ILLEGALITY_RE.search(clause_text))

    if "taxes_or_routine_small_charge" in feat_in:
        out["taxes_or_routine_small_charge"] = bool(feat_in["taxes_or_routine_small_charge"])
    else:
        out["taxes_or_routine_small_charge"] = bool(
            clause_text
            and TAX_OR_SMALL_FEE_RE.search(clause_text)
            and not out["penal_rate_or_default_charge"]
            and not out["broad_or_uncapped"]
        )
    return out


def evaluate_clause_severity(
    clause: dict[str, Any],
    rules_cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Deterministically evaluate clause_type + features using first-match rules."""
    cfg = rules_cfg if rules_cfg is not None else load_severity_rules()
    valid_types = set(cfg.get("clause_types", ALLOWED_CLAUSE_TYPES))
    ctype = str(clause.get("clause_type", "") or "").strip()

    if ctype not in valid_types:
        return {
            "clause_type": "unclassified",
            "severity": "unclassified",
            "category_override": "unclassified",
            "rationale_prefix": "",
            "fired_rule": "UNKNOWN_TYPE",
            "fired_features": [],
            "explanation": f"Severity unclassified because: unknown clause_type {ctype!r}; none",
        }

    ctext = str(clause.get("clause_text") or clause.get("text") or "")
    feats = _coerce_features(clause.get("features"), clause_text=ctext)

    for rule in cfg.get("rules", []):
        if not rule.get("any_types"):
            if ctype not in rule.get("types", []):
                continue

        req_all = list(rule.get("all_features", []))
        if req_all and not all(feats.get(f, False) for f in req_all):
            continue

        req_any = list(rule.get("any_features", []))
        if req_any and not any(feats.get(f, False) for f in req_any):
            continue

        fired = [f for f in (req_all + [f for f in req_any if feats.get(f, False)]) if feats.get(f, False)]
        sev = str(rule["severity"])
        cat_override = rule.get("force_category")
        pref = str(rule.get("rationale_prefix", "") or "")
        if not fired:
            fired_desc = str(rule.get("reason", "default rule"))
        else:
            fired_desc = ", ".join(fired)

        explanation = f"Severity {sev} because: {ctype}; {fired_desc}"
        return {
            "clause_type": ctype,
            "severity": sev,
            "category_override": cat_override,
            "rationale_prefix": pref,
            "fired_rule": str(rule["id"]),
            "fired_features": fired,
            "explanation": explanation,
        }

    return {
        "clause_type": "unclassified",
        "severity": "unclassified",
        "category_override": "unclassified",
        "rationale_prefix": "",
        "fired_rule": "NO_MATCH",
        "fired_features": [],
        "explanation": f"Severity unclassified because: {ctype}; no rule matched",
    }


def explain(clause: dict[str, Any], rules_cfg: dict[str, Any] | None = None) -> str:
    """Return human-readable severity explanation: 'Severity <X> because: <type>; <features that fired>'."""
    return str(evaluate_clause_severity(clause, rules_cfg=rules_cfg)["explanation"])
