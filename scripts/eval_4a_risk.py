"""scripts/eval_4a_risk.py

Runs Stage 4a evaluation on dev (v1 / v2 prompt tuning) or test (once after freeze),
prints category and severity metrics + confusion matrices, and saves predictions
and confusion-matrix CSVs under data/processed/.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.llm.gemini_client import GeminiClient
from src.risk.evaluate import (
    CATEGORIES,
    SEVERITIES,
    evaluate_split,
    format_metrics_summary,
)

RUNS_META_PATH = ROOT / "data" / "processed" / "risk_4a_runs.json"


def print_confusion_matrix(title: str, cm: dict[str, dict[str, int]], row_labels: list[str], col_labels: list[str]) -> None:
    print(f"\n{title}:")
    header = ["true\\pred"] + col_labels
    print("  " + " | ".join(f"{h[:11]:>11}" for h in header))
    for rl in row_labels:
        vals = [f"{cm[rl][cl]:>11}" for cl in col_labels]
        print(f"  {rl[:11]:>11} | " + " | ".join(vals))


def print_per_class(title: str, per_class: dict[str, dict[str, float | int]], suppress_crit_f1: bool = False) -> None:
    print(f"\n{title}:")
    for lbl, stats in per_class.items():
        if suppress_crit_f1 and lbl == "Critical" and int(stats["support"]) < 5:
            print(
                f"  {lbl:22s}: recall={stats['tp']}/{stats['support']} ({float(stats['recall'])*100:.1f}%), F1=n/a (<5 support)"
            )
        else:
            print(
                f"  {lbl:22s}: P={float(stats['precision'])*100:5.1f}% R={float(stats['recall'])*100:5.1f}% F1={float(stats['f1'])*100:5.1f}% (n={stats['support']})"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 4a risk classifier evaluator")
    parser.add_argument("--split", choices=["dev", "test"], required=True)
    parser.add_argument("--prompt-version", default=None, help="Override config/risk.yaml prompt_version (e.g. v1, v2)")
    parser.add_argument("--force", action="store_true", help="Required to rerun test if risk_pred_test.csv exists")
    args = parser.parse_args()

    client = GeminiClient()
    res = evaluate_split(
        split=args.split,
        prompt_version=args.prompt_version,
        client=client,
        force=args.force,
        save_outputs=True,
    )
    m = res["metrics"]
    print(format_metrics_summary(args.split, m, prompt_version=res["prompt_version"]))
    print(
        f"Calls made={res['calls_made']}, live API calls={res['live_calls_made']}, "
        f"model_used={res['model_used_counts']}, fallbacks={res['fallback_calls']}"
    )
    if res.get("errors"):
        print(f"API/Network errors ({len(res['errors'])}): {res['errors'][:3]}")
    print_per_class("Category per-class", m["category"]["per_class"])
    print_per_class("Severity per-class", m["severity"]["per_class"], suppress_crit_f1=True)
    print_confusion_matrix("Category confusion matrix", m["category"]["confusion_matrix"], CATEGORIES, m["category"]["pred_cols"])
    print_confusion_matrix("Severity confusion matrix", m["severity"]["confusion_matrix"], SEVERITIES, m["severity"]["pred_cols"])

    if res.get("errors") and not res.get("model_used_counts"):
        raise SystemExit(1)

    # Record run stats cleanly for auditability and T6 budget reporting
    history = []
    if RUNS_META_PATH.is_file():
        try:
            history = json.loads(RUNS_META_PATH.read_text(encoding="utf-8"))
        except Exception:
            history = []
    if not isinstance(history, list):
        history = []
    if not res["reused_saved"]:
        history.append({
            "split": args.split,
            "prompt_version": res["prompt_version"],
            "calls_made": res["calls_made"],
            "live_calls_made": res["live_calls_made"],
            "model_used_counts": res["model_used_counts"],
            "fallback_calls": res["fallback_calls"],
            "category_accuracy": round(m["category"]["accuracy"], 4),
            "category_macro_f1": round(m["category"]["macro_f1"], 4),
            "severity_exact_accuracy": round(m["severity"]["accuracy"], 4),
            "severity_macro_f1": round(m["severity"]["macro_f1"], 4),
            "within_one_rate": round(m["within_one_rate"], 4),
            "critical_tp": m["critical_tp"],
            "critical_support": m["critical_support"],
            "flagged_numbers": m["flagged_numbers"],
        })
        RUNS_META_PATH.write_text(json.dumps(history, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
