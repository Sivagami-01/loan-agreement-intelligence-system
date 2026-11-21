"""src/risk/score.py

Stage 4b / 4b-fix: Deterministic document-level risk scoring (0-100) from classified clauses.
Zero LLM / API calls. Identical input clauses in any order produce identical output.
Supports methods: "mean_top3", "padded_top3", "max", and "blend".
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCORE_CONFIG = ROOT / "config" / "score.yaml"

CANONICAL_CATEGORIES = [
    "Default conditions",
    "Penalties and charges",
    "Financial terms",
    "Repayment",
    "Collateral",
    "Termination",
    "Covenants",
]
LEVEL_ORDER = {"Low": 0, "Moderate": 1, "High": 2, "Critical": 3}
VALID_METHODS = {"mean_top3", "padded_top3", "max", "blend"}


def load_score_config(config_path: Path | None = None) -> dict[str, Any]:
    """Loads Stage 4b scoring settings from config/score.yaml."""
    path = config_path or DEFAULT_SCORE_CONFIG
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _parse_page_sort_key(raw_page: Any) -> tuple[int, int, str]:
    """Normalizes page into a deterministic ascending sort key."""
    if raw_page is None or str(raw_page).strip() == "":
        return (1, 0, "")
    if isinstance(raw_page, (int, float)):
        return (0, int(raw_page), str(int(raw_page)))
    txt = str(raw_page).strip()
    m = re.search(r"\d+", txt)
    if m:
        return (0, int(m.group(0)), txt)
    return (1, 0, txt)


def _display_page(raw_page: Any) -> str:
    if raw_page is None:
        return "not available"
    txt = str(raw_page).strip()
    if not txt or txt.lower() in {"not available", "n/a", "?", "none"}:
        return "not available"
    if txt.isdigit():
        return txt
    m = re.search(r"\d+", txt)
    return m.group(0) if m else txt


def _evidence_strength(n_clauses: int) -> str:
    if n_clauses >= 3:
        return "strong"
    if n_clauses >= 1:
        return "limited"
    return "none"


def _score_to_level(score: float, thresholds: dict[str, Any]) -> str:
    low_max = float(thresholds.get("low_max", 25.0))
    mod_max = float(thresholds.get("moderate_max", 50.0))
    high_max = float(thresholds.get("high_max", 75.0))
    if score < low_max:
        return "Low"
    if score < mod_max:
        return "Moderate"
    if score < high_max:
        return "High"
    return "Critical"


def score_document(
    clauses: list[dict[str, Any]],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Deterministically computes 0-100 document risk score and explainable drivers.

    Each item in `clauses` expects:
        clause_id, category, severity, quote (or clause_text), page, rationale.
    """
    cfg = config if config is not None else load_score_config()
    method = str(cfg.get("method", "mean_top3"))
    if method not in VALID_METHODS:
        raise ValueError(f"Unsupported scoring method={method!r}; expected one of {sorted(VALID_METHODS)}")

    top_n = max(1, int(cfg.get("top_n", 3)))
    padding_pts = int(cfg.get("padding_points", 1))
    floor_rule = bool(cfg.get("floor_rule", True))
    floor_min_level = str(cfg.get("floor_min_level", "High"))
    points_map: dict[str, int] = {str(k): int(v) for k, v in (cfg.get("points") or {}).items()}
    weights_map: dict[str, float] = {str(k): float(v) for k, v in (cfg.get("weights") or {}).items()}
    thresholds: dict[str, Any] = dict(cfg.get("thresholds") or {})
    max_pts = float(max(points_map.values())) if points_map else 4.0

    grouped: dict[str, list[dict[str, Any]]] = {cat: [] for cat in weights_map}
    has_critical = False
    missing_page_count = 0

    for raw in clauses:
        cat = str(raw.get("category", "") or "").strip()
        sev = str(raw.get("severity", "") or "").strip()
        if cat not in weights_map or sev not in points_map:
            continue
        pts = points_map[sev]
        if sev == "Critical":
            has_critical = True
        cid = str(raw.get("clause_id", "") or "").strip()
        quote = str(raw.get("quote") if raw.get("quote") is not None else raw.get("clause_text", "") or "").strip()
        rationale = str(raw.get("rationale", "") or "").strip()
        raw_page = raw.get("page")
        disp_page = _display_page(raw_page)
        if disp_page == "not available":
            missing_page_count += 1
        grouped[cat].append(
            {
                "clause_id": cid,
                "category": cat,
                "severity": sev,
                "points": pts,
                "quote": quote,
                "page": disp_page,
                "_page_key": _parse_page_sort_key(raw_page),
                "rationale": rationale,
            }
        )

    categories_out: list[dict[str, Any]] = []
    missing_categories: dict[str, str] = {}
    all_contributing_clauses: list[dict[str, Any]] = []
    top_driver_per_category: list[dict[str, Any]] = []
    raw_total_score = 0.0

    for cat, weight in weights_map.items():
        items = sorted(
            grouped[cat],
            key=lambda x: (-x["points"], x["_page_key"], x["clause_id"], x["quote"]),
        )
        n_cat = len(items)
        ev_strength = _evidence_strength(n_cat)

        if n_cat == 0:
            missing_categories[cat] = "No clause found"
            categories_out.append(
                {
                    "name": cat,
                    "weight": weight,
                    "risk": 0.0,
                    "points_contributed": 0.0,
                    "n_clauses": 0,
                    "evidence_strength": ev_strength,
                    "status": "No clause found",
                    "top_clauses": [],
                }
            )
            top_driver_per_category.append(
                {
                    "category": cat,
                    "clause_id": None,
                    "severity": None,
                    "page": "not available",
                    "quote": "No clause found",
                    "contribution": 0.0,
                }
            )
            continue

        top_slice = items[:top_n]
        k = len(top_slice)
        pad_slots = max(0, top_n - k)

        if method == "padded_top3":
            total_slots = top_n
            slot_sum = sum(it["points"] for it in top_slice) + pad_slots * padding_pts
            cat_risk = slot_sum / (max_pts * total_slots)
        else:
            mean_risk = (sum(it["points"] for it in top_slice) / k) / max_pts
            max_risk = top_slice[0]["points"] / max_pts
            if method == "mean_top3":
                cat_risk = mean_risk
            elif method == "max":
                cat_risk = max_risk
            else:  # "blend"
                cat_risk = 0.5 * (mean_risk + max_risk)

        cat_contrib = 100.0 * weight * cat_risk
        raw_total_score += cat_contrib

        used_clauses = top_slice[:1] if method == "max" else top_slice
        top_clauses_out: list[dict[str, Any]] = []
        for idx, it in enumerate(used_clauses):
            if method == "padded_top3":
                c_contrib = 100.0 * weight * it["points"] / (max_pts * top_n)
            elif method == "mean_top3":
                c_contrib = 100.0 * weight * it["points"] / (max_pts * k)
            elif method == "max":
                c_contrib = 100.0 * weight * it["points"] / max_pts
            else:  # "blend"
                mean_part = 0.5 * 100.0 * weight * it["points"] / (max_pts * k)
                max_part = (0.5 * 100.0 * weight * it["points"] / max_pts) if idx == 0 else 0.0
                c_contrib = mean_part + max_part

            entry = {
                "clause_id": it["clause_id"],
                "category": it["category"],
                "severity": it["severity"],
                "points": it["points"],
                "contribution": c_contrib,
                "quote": it["quote"],
                "page": it["page"],
                "rationale": it["rationale"],
                "is_padding": False,
                "_page_key": it["_page_key"],
            }
            top_clauses_out.append({k2: v2 for k2, v2 in entry.items() if k2 != "_page_key"})
            all_contributing_clauses.append(entry)

        if method == "padded_top3" and pad_slots > 0:
            pad_contrib = 100.0 * weight * (pad_slots * padding_pts) / (max_pts * top_n)
            top_clauses_out.append(
                {
                    "clause_id": "PADDING",
                    "category": cat,
                    "severity": "Low",
                    "points": pad_slots * padding_pts,
                    "n_padded_slots": pad_slots,
                    "contribution": pad_contrib,
                    "quote": "padding (missing clauses counted as Low)",
                    "page": "not available",
                    "rationale": f"{pad_slots} missing slot(s) padded as Low ({padding_pts} point each).",
                    "is_padding": True,
                }
            )

        categories_out.append(
            {
                "name": cat,
                "weight": weight,
                "risk": round(cat_risk, 6),
                "points_contributed": round(cat_contrib, 6),
                "n_clauses": n_cat,
                "evidence_strength": ev_strength,
                "status": "scored",
                "top_clauses": top_clauses_out,
            }
        )
        first_real = next((c for c in top_clauses_out if not c.get("is_padding")), None)
        if first_real is not None:
            top_driver_per_category.append(
                {
                    "category": cat,
                    "clause_id": first_real["clause_id"],
                    "severity": first_real["severity"],
                    "page": first_real["page"],
                    "quote": " ".join(first_real["quote"].split())[:180],
                    "contribution": round(first_real["contribution"], 4),
                }
            )

    score = round(raw_total_score, 1)
    level_before_floor = _score_to_level(score, thresholds)
    level = level_before_floor
    critical_floor_applied = False

    if floor_rule and has_critical:
        if LEVEL_ORDER.get(level, 0) < LEVEL_ORDER.get(floor_min_level, 2):
            level = floor_min_level
            critical_floor_applied = True

    if critical_floor_applied:
        level_explanation = (
            f"Level raised to {level} because a Critical clause was found; "
            f"the score alone would be {level_before_floor}."
        )
    else:
        level_explanation = f"Level {level} matches score {score:.1f} (Critical floor not needed)."

    all_contributing_clauses.sort(
        key=lambda x: (-x["contribution"], -x["points"], x["_page_key"], x["clause_id"], x["category"])
    )
    top_drivers = [
        {
            "clause_id": d["clause_id"],
            "category": d["category"],
            "severity": d["severity"],
            "points": d["points"],
            "contribution": round(d["contribution"], 4),
            "quote": d["quote"],
            "page": d["page"],
        }
        for d in all_contributing_clauses[:5]
    ]

    if method == "padded_top3":
        formula_text = (
            f"method=padded_top3 (top_n={top_n}, padding_pts={padding_pts}, floor_rule={floor_rule}): "
            "score = round(100 * sum(weight * category_risk), 1); "
            "category_risk = (sum(top 3 points) + missing_slots*1) / 12 (0 if no clause); "
            "bands <25 Low, 25-<50 Moderate, 50-<75 High, >=75 Critical."
        )
    else:
        formula_text = (
            f"method={method} (top_n={top_n}, floor_rule={floor_rule}): "
            "score = round(100 * sum(weight * category_risk), 1); "
            "category_risk = mean(top 3 severity points Low=1..Critical=4) / 4; "
            "bands <25 Low, 25-<50 Moderate, 50-<75 High, >=75 Critical."
        )

    notes: list[str] = []
    if missing_page_count > 0:
        notes.append(
            f"{missing_page_count} clause(s) show page 'not available' because source labels omit page numbers."
        )

    return {
        "score": score,
        "raw_score": raw_total_score,
        "level": level,
        "level_before_floor": level_before_floor,
        "critical_floor_applied": critical_floor_applied,
        "level_explanation": level_explanation,
        "method": method,
        "categories": categories_out,
        "missing_categories": missing_categories,
        "top_drivers": top_drivers,
        "top_driver_per_category": top_driver_per_category,
        "formula_text": formula_text,
        "notes": notes,
    }
