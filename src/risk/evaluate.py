"""src/risk/evaluate.py

Shared evaluation, confusion-matrix export, and prediction CSV utilities for Stage 4a.
Compares predicted categories/severities against silver labels in risk_final.csv.
"""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Any

from src.llm.gemini_client import GeminiClient
from src.risk.classify import classify_clauses, load_risk_config

ROOT = Path(__file__).resolve().parents[2]
FINAL_CSV = ROOT / "data" / "processed" / "labels" / "llm_assisted" / "risk_final.csv"
SPLIT_CSV = ROOT / "data" / "processed" / "risk_split.csv"
PROCESSED_DIR = ROOT / "data" / "processed"

CATEGORIES = [
    "Financial terms",
    "Repayment",
    "Penalties and charges",
    "Collateral",
    "Default conditions",
    "Termination",
    "Covenants",
]
SEVERITIES = ["Low", "Medium", "High", "Critical"]
SEV_INDEX = {name: i for i, name in enumerate(SEVERITIES)}


def pred_csv_path(split: str) -> Path:
    return PROCESSED_DIR / f"risk_pred_{split}.csv"


def cm_csv_path(split: str, axis: str) -> Path:
    return PROCESSED_DIR / f"risk_cm_{split}_{axis}.csv"


def _doc_type_for(doc_id: str) -> str:
    return "sec_agreement" if ("/" in doc_id or "\\" in doc_id) else "indian_mitc"


def load_split_map() -> dict[str, str]:
    with SPLIT_CSV.open("r", encoding="utf-8-sig", newline="") as fh:
        return {r["doc_id"]: r["split"] for r in csv.DictReader(fh)}


def load_final_rows() -> list[dict[str, str]]:
    with FINAL_CSV.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def load_prediction_rows(split: str) -> list[dict[str, str]]:
    path = pred_csv_path(split)
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _class_metrics_and_cm(
    y_true: list[str],
    y_pred: list[str],
    labels: list[str],
) -> dict[str, Any]:
    pred_cols = list(labels) + ["unclassified"]
    cm: dict[str, dict[str, int]] = {t: {p: 0 for p in pred_cols} for t in labels}
    for yt, yp in zip(y_true, y_pred):
        col = yp if yp in labels else "unclassified"
        if yt in cm:
            cm[yt][col] += 1

    per_class: dict[str, dict[str, Any]] = {}
    f1_sum = 0.0
    for lbl in labels:
        tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == lbl and yp == lbl)
        fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt != lbl and yp == lbl)
        fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == lbl and yp != lbl)
        support = sum(1 for yt in y_true if yt == lbl)
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
        f1_sum += f1
        per_class[lbl] = {
            "precision": prec,
            "recall": rec,
            "f1": f1,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "support": support,
        }

    n = len(y_true)
    acc = sum(1 for yt, yp in zip(y_true, y_pred) if yt == yp) / n if n > 0 else 0.0
    macro_f1 = f1_sum / len(labels) if labels else 0.0
    return {
        "n": n,
        "accuracy": acc,
        "macro_f1": macro_f1,
        "per_class": per_class,
        "confusion_matrix": cm,
        "pred_cols": pred_cols,
    }


def compute_metrics(rows: list[dict[str, str]]) -> dict[str, Any]:
    y_true_cat = [r["true_category"] for r in rows]
    y_pred_cat = [r["pred_category"] for r in rows]
    y_true_sev = [r["true_severity"] for r in rows]
    y_pred_sev = [r["pred_severity"] for r in rows]

    cat_m = _class_metrics_and_cm(y_true_cat, y_pred_cat, CATEGORIES)
    sev_m = _class_metrics_and_cm(y_true_sev, y_pred_sev, SEVERITIES)

    n = len(rows)
    within_one = sum(
        1
        for yt, yp in zip(y_true_sev, y_pred_sev)
        if yt in SEV_INDEX and yp in SEV_INDEX and abs(SEV_INDEX[yt] - SEV_INDEX[yp]) <= 1
    )
    within_one_rate = within_one / n if n > 0 else 0.0

    crit_stats = sev_m["per_class"]["Critical"]
    crit_support = crit_stats["support"]
    crit_tp = crit_stats["tp"]
    crit_f1 = crit_stats["f1"] if crit_support >= 5 else None

    unclassified_cat = sum(1 for yp in y_pred_cat if yp not in CATEGORIES)
    unclassified_sev = sum(1 for yp in y_pred_sev if yp not in SEVERITIES)
    flagged_nums = sum(1 for r in rows if str(r.get("number_flag", "")).lower() == "true")
    model_counts = Counter(r.get("model_used", "") for r in rows if r.get("model_used"))

    return {
        "n": n,
        "category": cat_m,
        "severity": sev_m,
        "within_one_count": within_one,
        "within_one_rate": within_one_rate,
        "critical_tp": crit_tp,
        "critical_support": crit_support,
        "critical_recall": crit_stats["recall"],
        "critical_f1": crit_f1,
        "unclassified_category": unclassified_cat,
        "unclassified_severity": unclassified_sev,
        "flagged_numbers": flagged_nums,
        "model_counts": dict(model_counts),
    }


def save_confusion_matrix_csv(path: Path, cm: dict[str, dict[str, int]], row_labels: list[str], col_labels: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["true\\pred"] + col_labels)
        for rl in row_labels:
            w.writerow([rl] + [cm[rl][cl] for cl in col_labels])


def evaluate_split(
    split: str,
    prompt_version: str | None = None,
    client: GeminiClient | None = None,
    force: bool = False,
    save_outputs: bool = True,
) -> dict[str, Any]:
    """Runs or loads predictions for `split` ("dev" or "test") and returns metrics."""
    if split not in {"dev", "test"}:
        raise ValueError(f"Unsupported split={split!r}")

    cfg = load_risk_config()
    ver = prompt_version or str(cfg.get("prompt_version", "v1"))

    if split == "test" and pred_csv_path("test").is_file() and not force:
        print(
            f"WARNING: {pred_csv_path('test').relative_to(ROOT)} already exists; "
            "refusing to rerun test without --force. Reporting saved test metrics."
        )
        rows = load_prediction_rows("test")
        metrics = compute_metrics(rows)
        if save_outputs:
            save_confusion_matrix_csv(
                cm_csv_path("test", "category"),
                metrics["category"]["confusion_matrix"],
                CATEGORIES,
                metrics["category"]["pred_cols"],
            )
            save_confusion_matrix_csv(
                cm_csv_path("test", "severity"),
                metrics["severity"]["confusion_matrix"],
                SEVERITIES,
                metrics["severity"]["pred_cols"],
            )
        return {
            "split": split,
            "prompt_version": rows[0].get("prompt_version", ver) if rows else ver,
            "reused_saved": True,
            "calls_made": 0,
            "live_calls_made": 0,
            "model_used_counts": {},
            "fallback_calls": 0,
            "rows": rows,
            "metrics": metrics,
        }

    if client is None:
        client = GeminiClient()

    split_map = load_split_map()
    all_rows = load_final_rows()
    subset = [r for r in all_rows if split_map.get(r["doc_id"]) == split]

    # Classify separately by doc_type ("sec_agreement" vs "indian_mitc") without passing silver labels
    by_type_indices: dict[str, list[int]] = {"sec_agreement": [], "indian_mitc": []}
    for i, r in enumerate(subset):
        by_type_indices[_doc_type_for(r["doc_id"])].append(i)

    pred_by_idx: dict[int, dict[str, Any]] = {}
    total_calls = 0
    total_live = 0
    total_fallbacks = 0
    batch_model_counts: Counter[str] = Counter()
    all_errors: list[str] = []

    for doc_type, idx_list in by_type_indices.items():
        if not idx_list:
            continue
        clauses_payload = [
            {"clause_id": subset[i]["clause_id"], "clause_text": subset[i]["clause_text"]}
            for i in idx_list
        ]
        res = classify_clauses(
            doc_type=doc_type,
            clauses=clauses_payload,
            client=client,
            config=cfg,
            prompt_version=ver,
        )
        total_calls += int(res["calls_made"])
        total_live += int(res["live_calls_made"])
        total_fallbacks += int(res["fallback_calls"])
        batch_model_counts.update(res["model_used_counts"])
        all_errors.extend(res.get("errors", []))
        for orig_i, pred in zip(idx_list, res["results"]):
            pred_by_idx[orig_i] = pred

    out_rows: list[dict[str, str]] = []
    for i, truth in enumerate(subset):
        p = pred_by_idx[i]
        t_sev = truth["final_severity"]
        p_sev = p["severity"]
        sev_diff = (
            abs(SEV_INDEX[t_sev] - SEV_INDEX[p_sev])
            if (t_sev in SEV_INDEX and p_sev in SEV_INDEX)
            else 99
        )
        out_rows.append(
            {
                "doc_id": truth["doc_id"],
                "clause_id": truth["clause_id"],
                "split": split,
                "doc_type": _doc_type_for(truth["doc_id"]),
                "prompt_version": ver,
                "true_category": truth["final_category"],
                "pred_category": p["category"],
                "true_severity": t_sev,
                "pred_severity": p_sev,
                "severity_diff": str(sev_diff),
                "applied_rule": p["applied_rule"],
                "number_flag": "true" if p["number_flag"] else "false",
                "flagged_numbers": "; ".join(p["flagged_numbers"]),
                "pred_rationale": p["rationale"],
                "model_used": p["model_used"],
            }
        )

    metrics = compute_metrics(out_rows)

    if save_outputs:
        p_csv = pred_csv_path(split)
        p_csv.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = list(out_rows[0].keys()) if out_rows else []
        if fieldnames:
            with p_csv.open("w", encoding="utf-8", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=fieldnames)
                w.writeheader()
                w.writerows(out_rows)

        save_confusion_matrix_csv(
            cm_csv_path(split, "category"),
            metrics["category"]["confusion_matrix"],
            CATEGORIES,
            metrics["category"]["pred_cols"],
        )
        save_confusion_matrix_csv(
            cm_csv_path(split, "severity"),
            metrics["severity"]["confusion_matrix"],
            SEVERITIES,
            metrics["severity"]["pred_cols"],
        )

    return {
        "split": split,
        "prompt_version": ver,
        "reused_saved": False,
        "calls_made": total_calls,
        "live_calls_made": total_live,
        "model_used_counts": dict(batch_model_counts),
        "fallback_calls": total_fallbacks,
        "errors": all_errors,
        "rows": out_rows,
        "metrics": metrics,
    }


def format_metrics_summary(split: str, metrics: dict[str, Any], prompt_version: str = "") -> str:
    cat = metrics["category"]
    sev = metrics["severity"]
    crit_f1_str = "omitted (<5 support)" if metrics["critical_f1"] is None else f"{metrics['critical_f1']*100:.1f}%"
    lines = [
        f"Split: {split.upper()} (n={metrics['n']}, prompt={prompt_version})",
        f"  Category: accuracy={cat['accuracy']*100:.1f}% ({int(round(cat['accuracy']*metrics['n']))}/{metrics['n']}), macro-F1={cat['macro_f1']*100:.1f}% (unclassified={metrics['unclassified_category']})",
        f"  Severity: exact={sev['accuracy']*100:.1f}% ({int(round(sev['accuracy']*metrics['n']))}/{metrics['n']}), macro-F1={sev['macro_f1']*100:.1f}%, within-1-level={metrics['within_one_rate']*100:.1f}% ({metrics['within_one_count']}/{metrics['n']}), unclassified={metrics['unclassified_severity']}",
        f"  Critical recall: {metrics['critical_tp']}/{metrics['critical_support']} ({metrics['critical_recall']*100:.1f}%), Critical F1: {crit_f1_str}",
        f"  Numeric guardrail flags: {metrics['flagged_numbers']}/{metrics['n']}",
    ]
    return "\n".join(lines)
