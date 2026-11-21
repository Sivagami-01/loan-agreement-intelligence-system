"""scripts/run_4b_scores.py

Stage 4b-fix runner (ZERO API calls):
Scores all 13 labeled documents on BOTH silver labels (risk_final.csv) and
saved classifier predictions (risk_pred_dev.csv / risk_pred_test.csv) under BOTH
mean_top3 and padded_top3, prints side-by-side comparisons and spreads, and writes:
  - data/processed/risk_scores_silver.csv (mean_top3 + method column)
  - data/processed/risk_scores_pred.csv   (mean_top3 + method column)
  - data/processed/risk_scores_silver_padded.csv (padded_top3 + method column)
  - data/processed/risk_scores_pred_padded.csv   (padded_top3 + method column)
"""

from __future__ import annotations

import csv
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

csv.field_size_limit(2**31 - 1)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.risk.score import CANONICAL_CATEGORIES, load_score_config, score_document  # noqa: E402

FINAL_CSV = ROOT / "data" / "processed" / "labels" / "llm_assisted" / "risk_final.csv"
SPLIT_CSV = ROOT / "data" / "processed" / "risk_split.csv"
PRED_DEV_CSV = ROOT / "data" / "processed" / "risk_pred_dev.csv"
PRED_TEST_CSV = ROOT / "data" / "processed" / "risk_pred_test.csv"

OUT_SILVER = ROOT / "data" / "processed" / "risk_scores_silver.csv"
OUT_PRED = ROOT / "data" / "processed" / "risk_scores_pred.csv"
OUT_SILVER_PADDED = ROOT / "data" / "processed" / "risk_scores_silver_padded.csv"
OUT_PRED_PADDED = ROOT / "data" / "processed" / "risk_scores_pred_padded.csv"

LEVELS = ["Low", "Moderate", "High", "Critical"]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def extract_page_from_rationale(rationale: str) -> str:
    m = re.search(r"\[[^\]]*?\bPage\s+(\d+)", rationale or "", re.IGNORECASE)
    return m.group(1) if m else ""


def doc_type_for(doc_id: str) -> str:
    return "sec_agreement" if ("/" in doc_id or "\\" in doc_id) else "indian_mitc"


def _average_ranks(values: list[float]) -> list[float]:
    n = len(values)
    indexed = sorted(enumerate(values), key=lambda kv: kv[1])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i + 1
        while j < n and indexed[j][1] == indexed[i][1]:
            j += 1
        avg_r = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[indexed[k][0]] = avg_r
        i = j
    return ranks


def spearman_rank_corr(xs: list[float], ys: list[float]) -> float:
    if len(xs) != len(ys) or len(xs) < 2:
        return 0.0
    rx = _average_ranks(xs)
    ry = _average_ranks(ys)
    mx = sum(rx) / len(rx)
    my = sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = sum((a - mx) ** 2 for a in rx)
    dy = sum((b - my) ** 2 for b in ry)
    den = math.sqrt(dx * dy)
    if den == 0.0:
        return 1.0 if rx == ry else 0.0
    return num / den


def load_clauses_by_doc(source: str = "silver") -> tuple[dict[str, list[dict[str, Any]]], dict[str, str]]:
    split_map = {r["doc_id"]: r["split"] for r in _read_csv(SPLIT_CSV)}
    final_rows = _read_csv(FINAL_CSV)
    final_map = {(r["doc_id"], r["clause_id"]): r for r in final_rows}

    by_doc: dict[str, list[dict[str, Any]]] = defaultdict(list)

    if source == "silver":
        for r in final_rows:
            by_doc[r["doc_id"]].append(
                {
                    "clause_id": r["clause_id"],
                    "category": r["final_category"],
                    "severity": r["final_severity"],
                    "quote": r["clause_text"],
                    "page": extract_page_from_rationale(r["rationale"]),
                    "rationale": r["rationale"],
                }
            )
    elif source == "pred":
        pred_rows = _read_csv(PRED_DEV_CSV) + _read_csv(PRED_TEST_CSV)
        for p in pred_rows:
            orig = final_map[(p["doc_id"], p["clause_id"])]
            by_doc[p["doc_id"]].append(
                {
                    "clause_id": p["clause_id"],
                    "category": p["pred_category"],
                    "severity": p["pred_severity"],
                    "quote": orig["clause_text"],
                    "page": extract_page_from_rationale(orig["rationale"]),
                    "rationale": p.get("pred_rationale", ""),
                }
            )
    else:
        raise ValueError(f"Unknown source={source!r}")

    return dict(by_doc), split_map


def _format_driver_page(page: str) -> str:
    return f"p.{page}" if page and page != "not available" else "page not available"


def _format_top3_drivers(res: dict[str, Any]) -> str:
    parts: list[str] = []
    for d in res["top_drivers"][:3]:
        pg = _format_driver_page(d["page"])
        short_q = " ".join(d["quote"].split())[:80]
        parts.append(f"{d['clause_id']} ({d['category']}/{d['severity']}, {pg}, {d['contribution']:.2f}): {short_q}")
    return " | ".join(parts)


def score_all_docs(
    by_doc: dict[str, list[dict[str, Any]]],
    split_map: dict[str, str],
    cfg: dict[str, Any],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for doc_id in sorted(by_doc):
        clauses = by_doc[doc_id]
        res = score_document(clauses, cfg)
        cats_present = sum(1 for c in res["categories"] if c["n_clauses"] > 0)
        records.append(
            {
                "doc_id": doc_id,
                "doc_type": doc_type_for(doc_id),
                "split": split_map.get(doc_id, ""),
                "n_clauses": len(clauses),
                "categories_present": cats_present,
                "method": res["method"],
                "score": res["score"],
                "level": res["level"],
                "level_before_floor": res["level_before_floor"],
                "floor_applied": "true" if res["critical_floor_applied"] else "false",
                "level_explanation": res["level_explanation"],
                "top_3_drivers": _format_top3_drivers(res),
                "result": res,
            }
        )
    records.sort(key=lambda r: (-r["score"], r["doc_id"]))
    return records


def write_scores_csv(path: Path, records: list[dict[str, Any]]) -> None:
    fieldnames = [
        "doc_id",
        "doc_type",
        "split",
        "n_clauses",
        "categories_present",
        "method",
        "score",
        "level",
        "floor_applied",
        "top_3_drivers",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for r in records:
            w.writerow(
                {
                    "doc_id": r["doc_id"],
                    "doc_type": r["doc_type"],
                    "split": r["split"],
                    "n_clauses": r["n_clauses"],
                    "categories_present": r["categories_present"],
                    "method": r["method"],
                    "score": f"{r['score']:.1f}",
                    "level": r["level"],
                    "floor_applied": r["floor_applied"],
                    "top_3_drivers": r["top_3_drivers"],
                }
            )


def _spread_stats(records: list[dict[str, Any]]) -> dict[str, Any]:
    scores = [float(r["score"]) for r in records]
    lvl_c = Counter(r["level"] for r in records)
    return {
        "n": len(records),
        "min": min(scores) if scores else 0.0,
        "median": statistics.median(scores) if scores else 0.0,
        "max": max(scores) if scores else 0.0,
        "levels": {lv: lvl_c[lv] for lv in LEVELS},
    }


def _comparison_stats(silver_recs: list[dict[str, Any]], pred_recs: list[dict[str, Any]]) -> dict[str, Any]:
    s_map = {r["doc_id"]: r for r in silver_recs}
    p_map = {r["doc_id"]: r for r in pred_recs}
    doc_ids = sorted(s_map)
    s_scores = [s_map[d]["score"] for d in doc_ids]
    p_scores = [p_map[d]["score"] for d in doc_ids]
    rho = spearman_rank_corr(s_scores, p_scores)
    gaps = [(abs(s_map[d]["score"] - p_map[d]["score"]), s_map[d]["score"], p_map[d]["score"], d) for d in doc_ids]
    mae = sum(g[0] for g in gaps) / len(gaps)
    max_gap, max_s, max_p, max_doc = max(gaps, key=lambda x: x[0])
    same_lvl = sum(1 for d in doc_ids if s_map[d]["level"] == p_map[d]["level"])
    all_share_one_level = (
        len({r["level"] for r in silver_recs}) <= 1
        or len({r["level"] for r in pred_recs}) <= 1
    )
    level_changes: list[dict[str, str]] = []
    for d in doc_ids:
        sr, pr = s_map[d], p_map[d]
        if sr["level"] != pr["level"]:
            s_fl = sr["floor_applied"] == "true"
            p_fl = pr["floor_applied"] == "true"
            if s_fl != p_fl:
                cause = (
                    "Critical floor applied in silver only"
                    if s_fl
                    else "Critical floor applied in predicted only"
                )
            else:
                cause = "raw score band difference"
            level_changes.append(
                {
                    "doc_id": d,
                    "silver_level": sr["level"],
                    "pred_level": pr["level"],
                    "cause": cause,
                }
            )
    return {
        "rho": rho,
        "mae": mae,
        "same_level": same_lvl,
        "n": len(doc_ids),
        "all_share_one_level": all_share_one_level,
        "level_changes": level_changes,
        "max_gap": max_gap,
        "max_doc": max_doc,
        "max_silver": max_s,
        "max_pred": max_p,
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    base_cfg = load_score_config()
    cfg_mean = dict(base_cfg, method="mean_top3")
    cfg_padded = dict(base_cfg, method="padded_top3")

    silver_docs, split_map = load_clauses_by_doc("silver")
    pred_docs, _ = load_clauses_by_doc("pred")

    mean_silver = score_all_docs(silver_docs, split_map, cfg_mean)
    mean_pred = score_all_docs(pred_docs, split_map, cfg_mean)
    pad_silver = score_all_docs(silver_docs, split_map, cfg_padded)
    pad_pred = score_all_docs(pred_docs, split_map, cfg_padded)

    # Save 4b files (with method="mean_top3") and new *_padded.csv files (method="padded_top3")
    write_scores_csv(OUT_SILVER, mean_silver)
    write_scores_csv(OUT_PRED, mean_pred)
    write_scores_csv(OUT_SILVER_PADDED, pad_silver)
    write_scores_csv(OUT_PRED_PADDED, pad_pred)

    ms_map = {r["doc_id"]: r for r in mean_silver}
    mp_map = {r["doc_id"]: r for r in mean_pred}
    ps_map = {r["doc_id"]: r for r in pad_silver}
    pp_map = {r["doc_id"]: r for r in pad_pred}

    print(f"Active config default method: {base_cfg.get('method')}")
    print("\n=== SIDE-BY-SIDE SCORE TABLE: mean_top3 vs padded_top3 (sorted by padded_top3 silver) ===")
    print("rank | doc_id | type | split | mean_silv | mean_pred | pad_silv | pad_pred | pad_silv_lvl(before->after) | pad_pred_lvl(before->after)")
    for rank, r in enumerate(pad_silver, 1):
        did = r["doc_id"]
        ms, mp, ps, pp = ms_map[did], mp_map[did], ps_map[did], pp_map[did]
        print(
            f"{rank:2d} | {did:44s} | {r['doc_type']:13s} | {r['split']:4s} | "
            f"{ms['score']:5.1f} {ms['level'][:3]} | {mp['score']:5.1f} {mp['level'][:3]} | "
            f"{ps['score']:5.1f}    | {pp['score']:5.1f}    | "
            f"{ps['level_before_floor']}->{ps['level']} (fl={ps['floor_applied']}) | "
            f"{pp['level_before_floor']}->{pp['level']} (fl={pp['floor_applied']})"
        )

    print("\n=== SPREAD COMPARISON (mean_top3 vs padded_top3) ===")
    for mlabel, s_recs, p_recs in [
        ("mean_top3", mean_silver, mean_pred),
        ("padded_top3", pad_silver, pad_pred),
    ]:
        print(f"\nMethod: {mlabel}")
        for tag, recs in [("Silver ALL", s_recs), ("Silver SEC", [x for x in s_recs if x["doc_type"] == "sec_agreement"]), ("Silver MITC", [x for x in s_recs if x["doc_type"] == "indian_mitc"]), ("Pred ALL", p_recs), ("Pred SEC", [x for x in p_recs if x["doc_type"] == "sec_agreement"]), ("Pred MITC", [x for x in p_recs if x["doc_type"] == "indian_mitc"])]:
            st = _spread_stats(recs)
            print(
                f"  {tag:12s} (n={st['n']:2d}): min={st['min']:4.1f}, median={st['median']:4.1f}, "
                f"max={st['max']:4.1f}, levels={st['levels']}"
            )
        cmp_s = _comparison_stats(s_recs, p_recs)
        print(
            f"  Silver vs Pred [{mlabel}]: Spearman rho={cmp_s['rho']:.4f}, MAE={cmp_s['mae']:.2f}, "
            f"largest_gap={cmp_s['max_gap']:.1f} ({cmp_s['max_doc']}: silver={cmp_s['max_silver']:.1f}, pred={cmp_s['max_pred']:.1f})"
        )
        same_note = " (uninformative when all documents share a level)" if cmp_s["all_share_one_level"] else ""
        print(f"  same level count: {cmp_s['same_level']}/{cmp_s['n']}{same_note}")
        chg = cmp_s["level_changes"]
        print(f"  Silver vs Pred level changes: {len(chg)}/{cmp_s['n']}")
        for ch in chg:
            print(
                f"    - {ch['doc_id']}: {ch['silver_level']} -> {ch['pred_level']} (cause: {ch['cause']})"
            )

    print("\n=== NOTE ON PAGE NUMBERS ===")
    print("Note: Two documents (000002/27566/0000945836-96-000035_3.txt and 000081/810113/0000950116-04-002411_4.txt) have no page numbers in the silver labels; missing pages display as 'not available'.")

    print("\n=== TOP 3 DRIVERS PER DOCUMENT (padded_top3 silver, high -> low) ===")
    for rank, r in enumerate(pad_silver, 1):
        res = r["result"]
        ev_summary = ", ".join(f"{c['name'][:4]}={c['evidence_strength']}({c['n_clauses']})" for c in res["categories"])
        print(f"{rank:2d}. {r['doc_id']} | score={r['score']:.1f} | {res['level_explanation']} | {ev_summary}")
        for idx, d in enumerate(res["top_drivers"][:3], 1):
            short_q = " ".join(d["quote"].split())[:130]
            print(
                f"    #{idx}: {d['clause_id']} | {d['category']} | {d['severity']} | "
                f"page={d['page']} | contrib={d['contribution']:.2f} | \"{short_q}\""
            )


if __name__ == "__main__":
    main()
