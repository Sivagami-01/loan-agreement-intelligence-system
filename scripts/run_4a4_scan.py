"""scripts/run_4a4_scan.py

Stage 4a-4: Prompt v5 (structured clause_type + boolean features) with
config/severity_rules.yaml deterministic rule-table scoring.

Evaluates 10 documents:
- 7 training/previously-scanned docs (silver-labeled; 65 finance-review rows come from them)
- 3 NEW hold-out docs (never reviewed; no rule tuned on them):
    * 000104/1041426/0000950144-99-003055_2.txt (smallest unscanned dev SEC, 111 clauses)
    * 000087/876645/0000891618-03-004250_9.txt  (2nd smallest unscanned dev SEC, 163 clauses)
    * 04_dbs_mitc-ahl                           (smaller unlabeled MITC, 60 clauses; no silver)

Writes:
- data/processed/risk_scan_v5_<slug>.csv (all 10 documents)
- data/processed/risk_scan_review_v5.csv (ALL flagged High/Critical + 10 random Med/Low from 3 hold-outs)
- data/processed/scan_4a4_summary.json
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_4a2_scan import (  # noqa: E402
    PROCESSED_DIR,
    REVIEW_CSV_COLUMNS,
    SEVERITY_INDEX,
    _evaluate_doc_scan,
    _load_silver_by_doc,
    _load_v2_preds_by_doc,
    doc_slug,
)
from scripts.run_4a3_scan import (  # noqa: E402
    TARGET_DOCS_4A3,
    V3_REVIEW_CSV,
    VERDICTS_CSV,
    _match_v3_row_to_v4,
    _page_stats,
    scan_v4_csv_path,
)
from scripts.run_4a3_scan import REVIEW_V4_CSV  # noqa: E402
from src.llm.gemini_client import GeminiClient  # noqa: E402
from src.risk.classify import classify_clauses, load_risk_config  # noqa: E402
from src.risk.prefilter import prefilter_clauses  # noqa: E402
from src.risk.split_clauses import split_document  # noqa: E402

REVIEW_V5_CSV = PROCESSED_DIR / "risk_scan_review_v5.csv"
SUMMARY_V5_JSON = PROCESSED_DIR / "scan_4a4_summary.json"

SCAN_V5_COLUMNS = [
    "doc_id",
    "clause_id",
    "continuation_of",
    "page",
    "clause_text",
    "prefilter_passed",
    "matched_keywords",
    "category",
    "severity",
    "clause_type",
    "features",
    "severity_rule",
    "severity_explanation",
    "rationale",
    "number_flag",
    "flagged_numbers",
    "model_used",
    "parse_error",
    "prompt_version",
]

TARGET_DOCS_4A4: list[dict[str, str]] = [
    {"doc_id": "03_dbs_mitc", "doc_type": "indian_mitc", "split": "dev", "role": "reviewed"},
    {"doc_id": "000010/104897/0000950123-11-030926_2.txt", "doc_type": "sec_agreement", "split": "dev", "role": "reviewed"},
    {"doc_id": "09_muthoothomefin_MHIL-MITC", "doc_type": "indian_mitc", "split": "test", "role": "reviewed"},
    {"doc_id": "000081/810113/0000950116-04-002411_4.txt", "doc_type": "sec_agreement", "split": "test", "role": "reviewed"},
    {"doc_id": "000103/1039213/0000912057-97-018811_19.txt", "doc_type": "sec_agreement", "split": "test", "role": "reviewed"},
    {"doc_id": "000105/1052667/0000912057-00-028795_20.txt", "doc_type": "sec_agreement", "split": "test", "role": "reviewed"},
    {"doc_id": "11_gichfindia_MOST-IMPORTANT-TERMS-1", "doc_type": "indian_mitc", "split": "dev", "role": "reviewed"},
    # 3 NEW hold-out documents (never reviewed, no rule tuned on them)
    {"doc_id": "000104/1041426/0000950144-99-003055_2.txt", "doc_type": "sec_agreement", "split": "dev", "role": "holdout"},
    {"doc_id": "000087/876645/0000891618-03-004250_9.txt", "doc_type": "sec_agreement", "split": "dev", "role": "holdout"},
    {"doc_id": "04_dbs_mitc-ahl", "doc_type": "indian_mitc", "split": "unlabeled_holdout", "role": "holdout"},
]


def scan_v5_csv_path(doc_id: str) -> Path:
    return PROCESSED_DIR / f"risk_scan_v5_{doc_slug(doc_id)}.csv"


def _write_scan_v5_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=SCAN_V5_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _read_scan_csv(path: Path, doc_id: str | None = None) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    cont_map: dict[str, str] | None = None
    for r in rows:
        r["page"] = int(r["page"]) if str(r["page"]).isdigit() else r["page"]
        if "continuation_of" not in r and doc_id is not None:
            if cont_map is None:
                cont_map = {c["clause_id"]: c.get("continuation_of", "") for c in split_document(doc_id)}
            r["continuation_of"] = cont_map.get(r["clause_id"], "")
    return rows


def _run_dry_summary(selected: list[dict[str, str]], batch_size: int, max_calls: int) -> None:
    print(f"=== STAGE 4a-4 PRE-API DRY RUN (batch_size={batch_size}, max_calls={max_calls}) ===")
    tot_cls = 0
    tot_pass = 0
    tot_calls = 0
    for d in selected:
        cls = split_document(d["doc_id"])
        passed, dropped = prefilter_clauses(cls)
        calls = (len(passed) + batch_size - 1) // batch_size
        ps = _page_stats(cls)
        tot_cls += len(cls)
        tot_pass += len(passed)
        tot_calls += calls
        print(
            f"  [{d['role']:8s}|{d['split']:15s}] {d['doc_type']:13s} | {d['doc_id']:45s} | "
            f"split={len(cls):3d} | pass={len(passed):3d} | drop={len(dropped):2d} | calls={calls:2d} | pages={ps['page_range']}"
        )
    print(
        f"TOTAL: docs={len(selected)}, split_clauses={tot_cls}, "
        f"prefilter_passed={tot_pass}, estimated_calls={tot_calls} / budget={max_calls}"
    )


def _compute_65_verdict_agreement(
    v4_by_doc: dict[str, list[dict[str, Any]]],
    v5_by_doc: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Compare v4 and v5 against all 65 finance-review verdicts (27 R1 + 38 R2; skip unclear)."""
    if not VERDICTS_CSV.is_file() or not V3_REVIEW_CSV.is_file() or not REVIEW_V4_CSV.is_file():
        return {}
    with VERDICTS_CSV.open("r", encoding="utf-8-sig", newline="") as fh:
        verdicts = list(csv.DictReader(fh))
    with V3_REVIEW_CSV.open("r", encoding="utf-8-sig", newline="") as fh:
        v3_rev = {(r["doc_id"], r["clause_id"]): r for r in csv.DictReader(fh)}
    with REVIEW_V4_CSV.open("r", encoding="utf-8-sig", newline="") as fh:
        v4_rev = {(r["doc_id"], r["clause_id"]): r for r in csv.DictReader(fh)}

    v4_idx_map = {
        did: {r["clause_id"]: r for r in rows} for did, rows in v4_by_doc.items()
    }
    v5_idx_map = {
        did: {r["clause_id"]: r for r in rows} for did, rows in v5_by_doc.items()
    }

    counts = {
        "v4": {"cat": 0, "sev": 0, "exact": 0},
        "v5": {"cat": 0, "sev": 0, "exact": 0},
    }
    decided = 0
    unclear = 0
    details: list[dict[str, Any]] = []

    for v in verdicts:
        did = v["doc_id"]
        cid = v["clause_id"]
        rnd = str(v.get("round", "")).strip()
        rcat = v["reviewer_category"].strip()
        rsev = v["reviewer_severity"].strip()
        verd = v["verdict"].strip()

        # Source clause text from corresponding review CSV
        if rnd == "1":
            src_row = v3_rev.get((did, cid), {})
            v4_row = _match_v3_row_to_v4(src_row.get("clause_text", ""), v4_by_doc.get(did, []))
            v5_row = _match_v3_row_to_v4(src_row.get("clause_text", ""), v5_by_doc.get(did, []))
        else:
            src_row = v4_rev.get((did, cid), {})
            v4_row = v4_idx_map.get(did, {}).get(cid) or _match_v3_row_to_v4(src_row.get("clause_text", ""), v4_by_doc.get(did, []))
            v5_row = v5_idx_map.get(did, {}).get(cid)
            if v5_row is None or src_row.get("clause_text", "")[:40] != (v5_row.get("clause_text", "")[:40] if v5_row else ""):
                m5 = _match_v3_row_to_v4(src_row.get("clause_text", ""), v5_by_doc.get(did, []))
                if m5 is not None:
                    v5_row = m5

        v4c = v4_row["category"] if v4_row else "MISSING"
        v4s = v4_row["severity"] if v4_row else "MISSING"
        v5c = v5_row["category"] if v5_row else "MISSING"
        v5s = v5_row["severity"] if v5_row else "MISSING"

        if verd == "unclear" or rsev == "unclear":
            unclear += 1
            details.append({"round": rnd, "doc_id": did, "cid": cid, "reviewer": f"{rcat}/{rsev}", "v4": f"{v4c}/{v4s}", "v5": f"{v5c}/{v5s}", "unclear": True})
            continue

        decided += 1
        for tag, pc, ps in (("v4", v4c, v4s), ("v5", v5c, v5s)):
            c_ok = pc == rcat
            s_ok = ps == rsev
            counts[tag]["cat"] += int(c_ok)
            counts[tag]["sev"] += int(s_ok)
            counts[tag]["exact"] += int(c_ok and s_ok)

        details.append({"round": rnd, "doc_id": did, "cid": cid, "reviewer": f"{rcat}/{rsev}", "v4": f"{v4c}/{v4s}", "v5": f"{v5c}/{v5s}", "unclear": False})

    return {
        "label": "training rows: the rule table was designed with these in view",
        "total_rows": len(verdicts),
        "decided": decided,
        "unclear": unclear,
        "v4": {
            "cat_agree": counts["v4"]["cat"],
            "cat_pct": round(counts["v4"]["cat"] / decided * 100.0, 1) if decided else 0.0,
            "sev_exact": counts["v4"]["sev"],
            "sev_pct": round(counts["v4"]["sev"] / decided * 100.0, 1) if decided else 0.0,
            "exact": counts["v4"]["exact"],
            "exact_pct": round(counts["v4"]["exact"] / decided * 100.0, 1) if decided else 0.0,
        },
        "v5": {
            "cat_agree": counts["v5"]["cat"],
            "cat_pct": round(counts["v5"]["cat"] / decided * 100.0, 1) if decided else 0.0,
            "sev_exact": counts["v5"]["sev"],
            "sev_pct": round(counts["v5"]["sev"] / decided * 100.0, 1) if decided else 0.0,
            "exact": counts["v5"]["exact"],
            "exact_pct": round(counts["v5"]["exact"] / decided * 100.0, 1) if decided else 0.0,
        },
        "details": details,
    }


def _write_holdout_review_csv(holdout_flagged: list[dict[str, Any]]) -> dict[str, int]:
    """Write ALL flagged High/Critical + 10 random Med/Low clauses from the 3 hold-out docs."""
    high_crit = [r for r in holdout_flagged if r.get("severity") in {"Critical", "High"}]
    high_crit.sort(
        key=lambda r: (
            0 if r["severity"] == "Critical" else 1,
            str(r["doc_id"]),
            int(r["page"]) if str(r["page"]).isdigit() else 999999,
            str(r["clause_id"]),
        )
    )
    med_low = [r for r in holdout_flagged if r.get("severity") in {"Medium", "Low"}]
    rng = random.Random(42)
    med_low_sample = rng.sample(med_low, min(10, len(med_low)))
    med_low_sample.sort(
        key=lambda r: (
            str(r["doc_id"]),
            int(r["page"]) if str(r["page"]).isdigit() else 999999,
            str(r["clause_id"]),
        )
    )
    combined = high_crit + med_low_sample
    with REVIEW_V5_CSV.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=REVIEW_CSV_COLUMNS)
        writer.writeheader()
        for r in combined:
            writer.writerow(
                {
                    "doc_id": r["doc_id"],
                    "clause_id": r["clause_id"],
                    "page": r["page"],
                    "category": r["category"],
                    "severity": r["severity"],
                    "clause_text": r["clause_text"],
                    "rationale": f"{r['rationale']} | {r.get('severity_explanation', '')}",
                    "reviewer_verdict": "",
                }
            )
    return {
        "holdout_high_critical_all": len(high_crit),
        "holdout_medium_low_pool": len(med_low),
        "holdout_medium_low_sampled": len(med_low_sample),
        "total_review_rows": len(combined),
    }


def _pick_sample_explanations(v5_by_doc: dict[str, list[dict[str, Any]]]) -> list[dict[str, str]]:
    """Select sample explain() outputs (Critical if any, High, Medium, Low, none)."""
    wanted = ["Critical", "High", "Medium", "Low", "none"]
    samples: list[dict[str, str]] = []
    all_rows = [r for rows in v5_by_doc.values() for r in rows]
    for sev in wanted:
        cand = next(
            (
                r
                for r in all_rows
                if r.get("severity") == sev and r.get("model_used") != "prefilter" and r.get("severity_explanation")
            ),
            None,
        )
        if cand is not None:
            samples.append(
                {
                    "doc_id": cand["doc_id"],
                    "clause_id": cand["clause_id"],
                    "category": cand["category"],
                    "severity": sev,
                    "explanation": cand["severity_explanation"],
                    "snippet": " ".join(cand["clause_text"].split())[:110],
                }
            )
    return samples


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 4a-4 whole-document risk scan (v5 + rule table)")
    parser.add_argument("--dry-run", action="store_true", help="Print clause, prefilter, and API call estimates without API calls")
    parser.add_argument("--group", choices=["reviewed", "holdout", "all"], default="all", help="Document group to process")
    parser.add_argument("--from-saved", action="store_true", help="Evaluate from saved risk_scan_v5_*.csv files (0 API calls)")
    args = parser.parse_args()

    risk_cfg = load_risk_config()
    batch_size = int(risk_cfg.get("scan_batch_size", 20))
    max_calls = int(risk_cfg.get("scan_max_calls", 60))
    prompt_ver = str(risk_cfg.get("scan_prompt_version", "v5"))

    selected = [d for d in TARGET_DOCS_4A4 if args.group == "all" or d["role"] == args.group]

    if args.dry_run:
        _run_dry_summary(selected, batch_size=batch_size, max_calls=max_calls)
        return

    silver_by_doc = _load_silver_by_doc()
    v2_by_doc = _load_v2_preds_by_doc()

    client = None if args.from_saved else GeminiClient()
    t0 = time.perf_counter()

    v5_summaries: list[dict[str, Any]] = []
    v5_by_doc: dict[str, list[dict[str, Any]]] = {}
    holdout_flagged_all: list[dict[str, Any]] = []
    model_counts_total: dict[str, int] = {}
    finished_docs: list[str] = []
    stopped_reason: str | None = None
    total_live_calls = 0

    for d in selected:
        doc_id = d["doc_id"]
        doc_type = d["doc_type"]
        split_name = d["split"]
        role = d["role"]
        out_path = scan_v5_csv_path(doc_id)

        if args.from_saved:
            if not out_path.is_file():
                continue
            scan_rows = _read_scan_csv(out_path, doc_id=doc_id)
            doc_calls = 0
            doc_live_calls = 0
            doc_seconds = 0.0
            doc_models: dict[str, int] = {}
            for r in scan_rows:
                m = str(r.get("model_used", ""))
                if m and m != "prefilter":
                    doc_models[m] = doc_models.get(m, 0) + 1
                    model_counts_total[m] = model_counts_total.get(m, 0) + 1
        else:
            assert client is not None
            doc_t0 = time.perf_counter()
            split_items = split_document(doc_id)
            passed_items, _ = prefilter_clauses(split_items)
            classify_input = [
                {
                    "clause_id": it["clause_id"],
                    "clause_text": it["text"],
                    "page": f"page {it['page']}",
                }
                for it in passed_items
            ]
            res = classify_clauses(
                doc_type=doc_type,
                clauses=classify_input,
                client=client,
                config=risk_cfg,
                prompt_version=prompt_ver,
                scan=True,
            )
            doc_seconds = round(time.perf_counter() - doc_t0, 2)
            doc_calls = res["calls_made"]
            doc_live_calls = res["live_calls_made"]
            total_live_calls += doc_live_calls
            doc_models = res["model_used_counts"]
            for m, cnt in doc_models.items():
                model_counts_total[m] = model_counts_total.get(m, 0) + cnt

            if res.get("quota_stopped") or res.get("budget_stopped"):
                reason = "quota_429" if res.get("quota_stopped") else "budget_cap"
                stopped_reason = f"{reason} during {doc_id} (errors={res.get('errors')})"
                print(f"[STOPPED EARLY] {stopped_reason}. Finished docs ({len(finished_docs)}): {finished_docs}")
                break
            if res.get("errors") and res.get("unclassified_count", 0) >= len(classify_input):
                stopped_reason = f"api_failure during {doc_id} (errors={res.get('errors')[:2]})"
                print(f"[FAILED] {stopped_reason}")
                break

            pred_by_id = {r["clause_id"]: r for r in res["results"]}
            passed_ids = {it["clause_id"]: it for it in passed_items}
            scan_rows = []
            for it in split_items:
                cid = it["clause_id"]
                cont_of = it.get("continuation_of", "")
                if cid in passed_ids:
                    pred = pred_by_id[cid]
                    scan_rows.append(
                        {
                            "doc_id": doc_id,
                            "clause_id": cid,
                            "continuation_of": cont_of,
                            "page": it["page"],
                            "clause_text": it["text"],
                            "prefilter_passed": True,
                            "matched_keywords": "; ".join(passed_ids[cid].get("matched_keywords", [])),
                            "category": pred["category"],
                            "severity": pred["severity"],
                            "clause_type": pred.get("clause_type", ""),
                            "features": json.dumps(pred.get("features", {}), sort_keys=True),
                            "severity_rule": pred.get("severity_rule", ""),
                            "severity_explanation": pred.get("severity_explanation", ""),
                            "rationale": pred["rationale"],
                            "number_flag": pred["number_flag"],
                            "flagged_numbers": "; ".join(str(x) for x in pred["flagged_numbers"]),
                            "model_used": pred["model_used"],
                            "parse_error": pred["parse_error"],
                            "prompt_version": prompt_ver,
                        }
                    )
                else:
                    scan_rows.append(
                        {
                            "doc_id": doc_id,
                            "clause_id": cid,
                            "continuation_of": cont_of,
                            "page": it["page"],
                            "clause_text": it["text"],
                            "prefilter_passed": False,
                            "matched_keywords": "",
                            "category": "none",
                            "severity": "none",
                            "clause_type": "prefilter_dropped",
                            "features": "{}",
                            "severity_rule": "PREFILTER_DROPPED",
                            "severity_explanation": "Severity none because: prefilter_dropped; no risk keyword",
                            "rationale": "[prefilter-dropped] No guideline or loan-risk keyword triggered.",
                            "number_flag": False,
                            "flagged_numbers": "",
                            "model_used": "prefilter",
                            "parse_error": False,
                            "prompt_version": prompt_ver,
                        }
                    )
            _write_scan_v5_csv(out_path, scan_rows)
            print(f"[SAVED] {out_path.name} | calls={doc_calls} (live={doc_live_calls}), seconds={doc_seconds:.1f}, models={doc_models}")

        finished_docs.append(doc_id)
        v5_by_doc[doc_id] = scan_rows
        sil = silver_by_doc.get(doc_id, [])
        metrics, unlabeled_flagged, _ = _evaluate_doc_scan(
            doc_id=doc_id,
            doc_type=doc_type,
            split_name=split_name,
            scan_rows=scan_rows,
            silver_rows=sil,
            v2_rows=v2_by_doc.get(doc_id, []),
        )
        pstats = _page_stats(scan_rows)
        sev_counts = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0, "none": 0, "unclassified": 0}
        from scripts.run_4a2_scan import _collapse_continuations

        for r in _collapse_continuations(scan_rows):
            if r["severity"] in sev_counts:
                sev_counts[r["severity"]] += 1
            else:
                sev_counts["unclassified"] += 1

        metrics["role"] = role
        metrics["page_stats"] = pstats
        metrics["severity_counts"] = sev_counts
        metrics["calls_made"] = doc_calls
        metrics["live_calls_made"] = doc_live_calls
        metrics["seconds"] = doc_seconds
        metrics["model_used_counts"] = doc_models
        v5_summaries.append(metrics)

        if role == "holdout":
            flagged_hold = [
                r
                for r in _collapse_continuations(scan_rows)
                if r["category"] not in {"none", "unclassified", ""} and r["severity"] in SEVERITY_INDEX
            ]
            holdout_flagged_all.extend(flagged_hold)

        delta = round(metrics["full_scan_score"] - metrics["silver_labeled_score"], 1) if sil else None
        delta_s = f"{delta:+.1f}" if delta is not None else "n/a(no silver)"
        print(
            f"[{role:8s}|{split_name:15s}] {doc_id} | split={metrics['splitter_clauses']} pass={metrics['prefilter_passed']} "
            f"sevs={sev_counts} | sil_flag={metrics['silver_flagged']}/{metrics['silver_total']} | "
            f"cat={metrics['silver_cat_agree_on_flagged']}/{metrics['silver_flagged']} | "
            f"exact={metrics['silver_sev_exact_on_flagged']}/{metrics['silver_flagged']} | "
            f"w1={metrics['silver_sev_within1_on_flagged']}/{metrics['silver_flagged']} | "
            f"unl={metrics['unlabeled_flagged_total']} {metrics['unlabeled_by_severity']} | "
            f"score={metrics['full_scan_score']} ({metrics['full_scan_level']}) vs sil={metrics['silver_labeled_score'] if sil else 'n/a'} delta={delta_s}"
        )

    # Re-evaluate saved v4 docs (Step 1 fixes applied uniformly!) for exact v4 vs v5 comparison
    v4_by_doc: dict[str, list[dict[str, Any]]] = {}
    v4_summaries: dict[str, dict[str, Any]] = {}
    for d in TARGET_DOCS_4A3:
        p4 = scan_v4_csv_path(d["doc_id"])
        if p4.is_file():
            r4 = _read_scan_csv(p4, doc_id=d["doc_id"])
            v4_by_doc[d["doc_id"]] = r4
            m4, _, _ = _evaluate_doc_scan(
                doc_id=d["doc_id"],
                doc_type=d["doc_type"],
                split_name=d["split"],
                scan_rows=r4,
                silver_rows=silver_by_doc.get(d["doc_id"], []),
                v2_rows=v2_by_doc.get(d["doc_id"], []),
            )
            v4_summaries[d["doc_id"]] = m4

    verdict_65 = _compute_65_verdict_agreement(v4_by_doc, v5_by_doc)
    if verdict_65:
        v4m = verdict_65["v4"]
        v5m = verdict_65["v5"]
        dec = verdict_65["decided"]
        print(
            f"\n65-ROW VERDICT AGREEMENT ({verdict_65['label']}; decided={dec}, unclear={verdict_65['unclear']}):\n"
            f"  v4: cat={v4m['cat_agree']}/{dec} ({v4m['cat_pct']}%), sev_exact={v4m['sev_exact']}/{dec} ({v4m['sev_pct']}%), exact={v4m['exact']}/{dec} ({v4m['exact_pct']}%)\n"
            f"  v5: cat={v5m['cat_agree']}/{dec} ({v5m['cat_pct']}%), sev_exact={v5m['sev_exact']}/{dec} ({v5m['sev_pct']}%), exact={v5m['exact']}/{dec} ({v5m['exact_pct']}%)"
        )

    samples = _pick_sample_explanations(v5_by_doc)
    if samples:
        print("\n=== 5 SAMPLE explain() TEXTS ===")
        for s in samples:
            print(f"  [{s['severity']:8s}] {s['doc_id']} {s['clause_id']} ({s['category']}): {s['explanation']}")

    review_stats = _write_holdout_review_csv(holdout_flagged_all)
    total_seconds = round(time.perf_counter() - t0, 2)
    payload = {
        "prompt_version": prompt_ver,
        "group_arg": args.group,
        "finished_docs": finished_docs,
        "stopped_reason": stopped_reason,
        "total_live_calls": total_live_calls,
        "total_seconds": total_seconds,
        "model_used_counts": model_counts_total,
        "verdict_agreement_65": verdict_65,
        "v4_comparison_7docs": v4_summaries,
        "holdout_review_sampling": review_stats,
        "sample_explanations": samples,
        "documents": v5_summaries,
    }
    SUMMARY_V5_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {REVIEW_V5_CSV.relative_to(ROOT)} ({review_stats})")
    print(f"Wrote {SUMMARY_V5_JSON.relative_to(ROOT)} in {total_seconds:.2f}s | models={model_counts_total}")


if __name__ == "__main__":
    main()
