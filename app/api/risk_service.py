"""app/api/risk_service.py

Stage 7a-2b whole-document risk scan + deterministic padded_top3 scoring wrapper.
Reuses frozen Stage 4a-4 v5 classification (src/risk/classify.py + severity_rules.py)
and Stage 4b-fix padded_top3 scoring (src/risk/score.py) without modifying src/.
Re-verifies every returned quote on the server before returning or scoring.
"""

from __future__ import annotations

import math
from typing import Any

from app.api.doc_bridge import (
    load_uploaded_document,
    load_uploaded_meta,
    load_uploaded_table_rows_by_page,
)
from src.qa.verify_quotes import verify_evidence
from src.risk.classify import classify_clauses, load_risk_config
from src.risk.prefilter import prefilter_clauses
from src.risk.score import load_score_config, score_document
from src.risk.split_clauses import split_pages

RISK_SAMPLE_RANGE = "41.2-51.7"
RISK_LABELS = ["automated estimate", "information, not advice"]
RISK_DISPLAY_NOTE = (
    "Never display the risk level alone; always show the numeric score (0-100), "
    "the 7-category breakdown with evidence_strength, any Critical floor "
    "level_explanation, Critical clauses, and sample_range (41.2-51.7)."
)


def _infer_doc_type_and_mode(doc_id: str, full_text: str) -> tuple[str, bool]:
    """Determines (doc_type, mitc_mode) for an uploaded document."""
    meta = load_uploaded_meta(doc_id)
    fname = str(meta.get("filename", "") or "").lower()
    ext = str(meta.get("ext", "") or "").lower()
    head = full_text[:4000].upper()

    sec_markers = ("FIRST AMENDMENT", "SECOND AMENDMENT", "THIRD AMENDMENT", "EXHIBIT 10", "ARTICLE I", "SECTION 1.")
    if "mitc" in fname:
        return "indian_mitc", True
    if ext == ".txt" or fname.startswith("000") or len(full_text) > 60000 or any(m in head for m in sec_markers):
        return "sec_agreement", False
    return "indian_mitc", True


def run_risk_analysis(
    doc_id: str,
    client: Any,
    task_budget: int = 15,
) -> dict[str, Any]:
    """Runs v5 risk scan + server quote verification + padded_top3 scoring."""
    full_text, doc_pages = load_uploaded_document(doc_id)
    doc_type, mitc_mode = _infer_doc_type_and_mode(doc_id, full_text)
    table_rows = load_uploaded_table_rows_by_page(doc_id) if mitc_mode else None

    split_items = split_pages(
        doc_id=doc_id,
        doc_pages=doc_pages,
        mitc_mode=mitc_mode,
        table_rows_by_page=table_rows,
        stitch_page_breaks=True,
    )
    passed_items, _ = prefilter_clauses(split_items)

    risk_cfg = load_risk_config()
    batch_size = max(1, int(risk_cfg.get("scan_batch_size", 20)))
    scan_max_calls = int(risk_cfg.get("scan_max_calls", 60))
    prompt_ver = str(risk_cfg.get("scan_prompt_version", "v5"))
    effective_max_calls = min(scan_max_calls, max(0, int(task_budget)))

    needed_batches = math.ceil(len(passed_items) / batch_size) if passed_items else 0
    if needed_batches > effective_max_calls or needed_batches > scan_max_calls:
        # Existing Stage 4a-4 scan has no chunked retrieval fallback; return cleanly with 0 API calls.
        return {
            "status": "needs_retrieval",
            "reason": (
                f"Document requires {needed_batches} scan batches ({len(passed_items)} prefiltered clauses), "
                f"exceeding limit ({effective_max_calls}); no retrieval fallback in frozen v5 scan."
            ),
            "doc_id": doc_id,
            "doc_type": doc_type,
            "prompt_version": prompt_ver,
            "page_count": len(doc_pages),
            "clauses_total": len(split_items),
            "clauses_prefiltered": len(passed_items),
            "batches_needed": needed_batches,
            "task_budget": int(task_budget),
            "sample_range": RISK_SAMPLE_RANGE,
            "labels": list(RISK_LABELS),
            "display_note": RISK_DISPLAY_NOTE,
            "flagged_clauses": [],
            "critical_clauses": [],
            "quotes_checked": 0,
            "quotes_verified": 0,
            "unverified_dropped": 0,
        }

    score_cfg = load_score_config()
    weights_map = set((score_cfg.get("weights") or {}).keys())
    points_map = set((score_cfg.get("points") or {}).keys())

    if not passed_items:
        empty_score = score_document([], score_cfg)
        return {
            "status": "ok",
            "doc_id": doc_id,
            "doc_type": doc_type,
            "prompt_version": prompt_ver,
            "page_count": len(doc_pages),
            "clauses_total": len(split_items),
            "clauses_prefiltered": 0,
            "flagged_count": 0,
            "critical_count": 0,
            "quotes_checked": 0,
            "quotes_verified": 0,
            "unverified_dropped": 0,
            "flagged_clauses": [],
            "critical_clauses": [],
            "sample_range": RISK_SAMPLE_RANGE,
            "labels": list(RISK_LABELS),
            "display_note": RISK_DISPLAY_NOTE,
            "evidence_strength": {c["name"]: c["evidence_strength"] for c in empty_score["categories"]},
            "budget_stopped": False,
            "quota_stopped": False,
            "errors": [],
            **empty_score,
        }

    run_risk_cfg = dict(risk_cfg)
    run_risk_cfg["scan_max_calls"] = effective_max_calls
    classify_input = [
        {
            "clause_id": it["clause_id"],
            "clause_text": it["text"],
            "page": f"page {it['page']}",
        }
        for it in passed_items
    ]
    cls_res = classify_clauses(
        doc_type=doc_type,
        clauses=classify_input,
        client=client,
        config=run_risk_cfg,
        prompt_version=prompt_ver,
        scan=True,
    )

    if cls_res.get("quota_stopped") or cls_res.get("budget_stopped"):
        return {
            "status": "budget_or_quota_stopped",
            "doc_id": doc_id,
            "doc_type": doc_type,
            "prompt_version": prompt_ver,
            "budget_stopped": bool(cls_res.get("budget_stopped")),
            "quota_stopped": bool(cls_res.get("quota_stopped")),
            "errors": list(cls_res.get("errors", [])),
        }

    # Never mask an API/network scan failure as 0.0 Low risk (mirrors scripts/run_4a4_scan.py)
    if cls_res.get("errors") and int(cls_res.get("unclassified_count", 0)) >= len(classify_input):
        return {
            "status": "scan_failed",
            "doc_id": doc_id,
            "doc_type": doc_type,
            "prompt_version": prompt_ver,
            "budget_stopped": False,
            "quota_stopped": False,
            "errors": list(cls_res.get("errors", [])),
        }

    src_by_id = {it["clause_id"]: it for it in passed_items}
    flagged_clauses: list[dict[str, Any]] = []
    critical_clauses: list[dict[str, Any]] = []
    score_inputs: list[dict[str, Any]] = []

    quotes_checked = 0
    quotes_verified = 0
    unverified_dropped = 0

    for pred in cls_res.get("results", []):
        cat = str(pred.get("category", "") or "").strip()
        sev = str(pred.get("severity", "") or "").strip()
        if cat not in weights_map or sev not in points_map:
            continue

        cid = str(pred.get("clause_id", "") or "").strip()
        src_item = src_by_id.get(cid, {})
        raw_quote = str(src_item.get("text", "") or "").strip()
        raw_page = src_item.get("page")

        quotes_checked += 1
        v_ev, _v_flags = verify_evidence(
            doc_pages,
            [{"quote": raw_quote, "page": raw_page}],
        )
        if not v_ev:
            unverified_dropped += 1
            continue

        quotes_verified += 1
        verified_page = v_ev[0]["page"]
        verified_quote = v_ev[0]["quote"]
        explanation = str(pred.get("severity_explanation", "") or "").strip()

        clause_record: dict[str, Any] = {
            "clause_id": cid,
            "category": cat,
            "clause_type": str(pred.get("clause_type", "") or ""),
            "severity": sev,
            "severity_explanation": explanation,
            "explain": explanation,
            "severity_rule": str(pred.get("severity_rule", pred.get("applied_rule", "")) or ""),
            "features": dict(pred.get("features") or {}),
            "rationale": str(pred.get("rationale", "") or ""),
            "quote": verified_quote,
            "page": verified_page,
            "verified": True,
            "model_used": str(pred.get("model_used", "") or ""),
        }
        flagged_clauses.append(clause_record)
        if sev == "Critical":
            critical_clauses.append(clause_record)

        score_inputs.append(
            {
                "clause_id": cid,
                "category": cat,
                "severity": sev,
                "quote": verified_quote,
                "page": verified_page,
                "rationale": clause_record["rationale"],
            }
        )

    score_res = score_document(score_inputs, score_cfg)
    ev_strength_map = {c["name"]: c["evidence_strength"] for c in score_res["categories"]}

    return {
        "status": "ok",
        "doc_id": doc_id,
        "doc_type": doc_type,
        "prompt_version": prompt_ver,
        "page_count": len(doc_pages),
        "clauses_total": len(split_items),
        "clauses_prefiltered": len(passed_items),
        "flagged_count": len(flagged_clauses),
        "critical_count": len(critical_clauses),
        "quotes_checked": quotes_checked,
        "quotes_verified": quotes_verified,
        "unverified_dropped": unverified_dropped,
        "flagged_clauses": flagged_clauses,
        "critical_clauses": critical_clauses,
        "sample_range": RISK_SAMPLE_RANGE,
        "labels": list(RISK_LABELS),
        "display_note": RISK_DISPLAY_NOTE,
        "evidence_strength": ev_strength_map,
        "budget_stopped": False,
        "quota_stopped": False,
        "errors": list(cls_res.get("errors", [])),
        **score_res,
    }
