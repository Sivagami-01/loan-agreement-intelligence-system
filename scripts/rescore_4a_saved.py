"""scripts/rescore_4a_saved.py

Re-scores the ALREADY SAVED Stage 4a predictions (data/processed/risk_pred_dev.csv
and data/processed/risk_pred_test.csv) against the updated silver labels in
risk_final.csv WITHOUT making any API calls or changing any prompt/prediction.
Reports OLD vs NEW metrics side-by-side and refreshes reference columns/confusion
matrices cleanly.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.risk.evaluate import (  # noqa: E402
    CATEGORIES,
    SEVERITIES,
    cm_csv_path,
    compute_metrics,
    load_final_rows,
    load_prediction_rows,
    pred_csv_path,
    save_confusion_matrix_csv,
)


def _summarize(split_name: str, old_m: dict[str, Any], new_m: dict[str, Any]) -> None:
    oc, nc = old_m["category"], new_m["category"]
    os_, ns = old_m["severity"], new_m["severity"]
    print(f"\n=== {split_name.upper()} (n={new_m['n']}) : OLD vs NEW (post-hoc R4 + IM10 label cleanup) ===")
    print(
        f"  Category Accuracy : {oc['accuracy']*100:5.1f}% -> {nc['accuracy']*100:5.1f}% "
        f"({int(round(oc['accuracy']*old_m['n']))} -> {int(round(nc['accuracy']*new_m['n']))}/{new_m['n']})"
    )
    print(f"  Category Macro-F1 : {oc['macro_f1']*100:5.1f}% -> {nc['macro_f1']*100:5.1f}%")
    print(
        f"  Severity Exact    : {os_['accuracy']*100:5.1f}% -> {ns['accuracy']*100:5.1f}% "
        f"({int(round(os_['accuracy']*old_m['n']))} -> {int(round(ns['accuracy']*new_m['n']))}/{new_m['n']})"
    )
    print(f"  Severity Macro-F1 : {os_['macro_f1']*100:5.1f}% -> {ns['macro_f1']*100:5.1f}%")
    print(
        f"  Within-1 Severity : {old_m['within_one_rate']*100:5.1f}% -> {new_m['within_one_rate']*100:5.1f}% "
        f"({old_m['within_one_count']} -> {new_m['within_one_count']}/{new_m['n']})"
    )
    print(
        f"  Critical Recall   : {old_m['critical_tp']}/{old_m['critical_support']} -> "
        f"{new_m['critical_tp']}/{new_m['critical_support']}"
    )
    print("  Per-category F1 (OLD -> NEW):")
    for cat in CATEGORIES:
        op, np_ = oc["per_class"][cat], nc["per_class"][cat]
        print(
            f"    {cat:22s}: {op['f1']*100:5.1f}% (n={op['support']:2d}) -> {np_['f1']*100:5.1f}% (n={np_['support']:2d})"
        )


def main() -> None:
    final_map = {(r["doc_id"], r["clause_id"]): r for r in load_final_rows()}

    for split in ("dev", "test"):
        old_rows = load_prediction_rows(split)
        old_m = compute_metrics(old_rows)

        new_rows: list[dict[str, str]] = []
        changed_truth = 0
        for row in old_rows:
            updated = dict(row)
            truth = final_map[(row["doc_id"], row["clause_id"])]
            if (
                updated["true_category"] != truth["final_category"]
                or updated["true_severity"] != truth["final_severity"]
            ):
                changed_truth += 1
            updated["true_category"] = truth["final_category"]
            updated["true_severity"] = truth["final_severity"]
            # Preserve pred_category, pred_severity, pred_rationale, applied_rule, number_flag, model_used verbatim
            assert updated["pred_category"] == row["pred_category"]
            assert updated["pred_severity"] == row["pred_severity"]
            assert updated["pred_rationale"] == row["pred_rationale"]
            new_rows.append(updated)

        new_m = compute_metrics(new_rows)
        _summarize(split, old_m, new_m)
        print(f"  Reference rows changed in {split}: {changed_truth}")

        p_path = pred_csv_path(split)
        fieldnames = list(old_rows[0].keys())
        with p_path.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(new_rows)

        save_confusion_matrix_csv(
            cm_csv_path(split, "category"),
            new_m["category"]["confusion_matrix"],
            CATEGORIES,
            new_m["category"]["pred_cols"],
        )
        save_confusion_matrix_csv(
            cm_csv_path(split, "severity"),
            new_m["severity"]["confusion_matrix"],
            SEVERITIES,
            new_m["severity"]["pred_cols"],
        )


if __name__ == "__main__":
    main()
