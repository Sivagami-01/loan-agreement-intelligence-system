from __future__ import annotations

import csv
import os
import re
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SHEETS = ROOT / "data" / "processed_v1" / "annotation_sheets"
RISK_SHEET = SHEETS / "risk_clause_sheet.csv"
MODEL_DIR = ROOT / "data" / "processed" / "models" / "huggingface"
OUTPUT = ROOT / "data" / "processed" / "retrieval_eval.csv"
SUMMARY = ROOT / "data" / "processed" / "retrieval_eval_summary.md"
LOG = ROOT / "data" / "processed" / "retrieval_eval.log"
MODEL_NAME = "intfloat/multilingual-e5-small"
RESULT_FIELDS = [
    "doc_id", "field_name", "relevant_clause_count", "hit_at_1",
    "hit_at_3", "hit_at_5", "reciprocal_rank", "top1_citation",
    "top1_same_document",
]
csv.field_size_limit(20_000_000)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold()).strip()


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def load_corpus() -> tuple[list[str], list[str], int]:
    citation_ids: list[str] = []
    passage_texts: list[str] = []
    rows = read_csv(RISK_SHEET)
    for index, row in enumerate(rows, 1):
        doc_id = row.get("doc_id", "")
        clause_id = row.get("clause_id", "")
        text = str(row.get("clause_text", "")).strip()
        if doc_id and text:
            citation_ids.append(f"{doc_id}#{clause_id}")
            passage_texts.append(
                f"passage: {row.get('clause_heading', '')}\n{text}"
            )
        if index % 100 == 0 or index == len(rows):
            print(f"[Corpus {index}/{len(rows)}] risk-clause rows processed", flush=True)
    failures = 0
    return citation_ids, passage_texts, failures


def prepare_queries(
    citation_ids: list[str],
    passage_texts: list[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    sheet_rows = read_csv(SHEETS / "key_info_sheet.csv")
    query_rows: list[dict[str, Any]] = []
    query_texts: list[str] = []
    normalized_passages = [normalized(text.removeprefix("passage:")) for text in passage_texts]
    for row in sheet_rows:
        doc_id = row.get("doc_id", "")
        field_name = row.get("field_name", "")
        value = row.get("machine_candidate_value", "")
        evidence = row.get("evidence_excerpt", "")
        if not value.strip() or not evidence.strip():
            continue
        evidence_norm = normalized(evidence)
        relevant = [
            i for i, citation in enumerate(citation_ids)
            if citation.startswith(doc_id + "#")
            and evidence_norm in normalized_passages[i]
        ]
        if not relevant:
            continue
        query_rows.append({
            "doc_id": doc_id,
            "field_name": field_name,
            "relevant_indices": relevant,
        })
        query_texts.append(f"query: {field_name}\n{value}")

    print(
        f"Machine-evidence proxy queries prepared: {len(query_rows)}; "
        f"source rows skipped (blank or evidence unmatched): "
        f"{len(sheet_rows) - len(query_rows)}.",
        flush=True,
    )
    return query_rows, query_texts


def main() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    os.environ["HF_HOME"] = str(MODEL_DIR)
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    log_lines = [
        f"Model: {MODEL_NAME}",
        "Mode: local embeddings + FAISS; no hosted inference or answer generation.",
    ]
    try:
        citation_ids, passages, corpus_failures = load_corpus()
        if not passages:
            raise RuntimeError("No risk-clause passages found in risk_clause_sheet.csv.")
        query_rows, query_texts = prepare_queries(citation_ids, passages)
        if not query_texts:
            raise RuntimeError(
                "No machine-evidence proxy queries matched a clause; retrieval metrics unavailable."
            )

        from sentence_transformers import SentenceTransformer
        import faiss

        print(
            f"Loading {MODEL_NAME} locally (weights cached under data\\processed\\models)...",
            flush=True,
        )
        model = SentenceTransformer(
            MODEL_NAME,
            cache_folder=str(MODEL_DIR),
            device="cpu",
            trust_remote_code=False,
        )
        model.max_seq_length = 256
        passage_vectors = model.encode(
            passages,
            batch_size=32,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).astype(np.float32, copy=False)
        query_vectors = model.encode(
            query_texts,
            batch_size=32,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).astype(np.float32, copy=False)

        index = faiss.IndexFlatIP(passage_vectors.shape[1])
        index.add(passage_vectors)
        distances, indices = index.search(query_vectors, 5)
        results = []
        reciprocal_ranks = []
        hits = {1: 0, 3: 0, 5: 0}
        for i, query in enumerate(query_rows):
            relevant = set(query["relevant_indices"])
            retrieved = [int(value) for value in indices[i] if value >= 0]
            ranks = [rank for rank, item in enumerate(retrieved, 1) if item in relevant]
            first_rank = min(ranks) if ranks else 0
            reciprocal = 1 / first_rank if first_rank else 0.0
            reciprocal_ranks.append(reciprocal)
            for cutoff in hits:
                if any(item in relevant for item in retrieved[:cutoff]):
                    hits[cutoff] += 1
            top1 = retrieved[0] if retrieved else -1
            results.append({
                "doc_id": query["doc_id"],
                "field_name": query["field_name"],
                "relevant_clause_count": len(relevant),
                "hit_at_1": bool(any(item in relevant for item in retrieved[:1])),
                "hit_at_3": bool(any(item in relevant for item in retrieved[:3])),
                "hit_at_5": bool(any(item in relevant for item in retrieved[:5])),
                "reciprocal_rank": round(reciprocal, 6),
                "top1_citation": citation_ids[top1] if top1 >= 0 else "",
                "top1_same_document": (
                    citation_ids[top1].startswith(query["doc_id"] + "#")
                    if top1 >= 0 else False
                ),
            })
        write_csv(OUTPUT, RESULT_FIELDS, results)
        count = len(results)
        summary_lines = [
            "# Local retrieval-only baseline",
            "",
            f"- Corpus: {len(passages):,} risk-clause passages from "
            f"{len({citation.split('#', 1)[0] for citation in citation_ids})} annotation documents.",
            f"- Queries evaluated: {count:,}; corpus file failures: {corpus_failures}.",
            f"- Encoder: `{MODEL_NAME}`; CPU, local model weights; FAISS inner-product "
            "index over L2-normalized embeddings.",
            "- This is a **machine-evidence proxy**, not gold-label evaluation: queries use "
            "field names plus machine-proposed candidate values, and relevant passages are "
            "located by matching the sheet's machine evidence quote. No human labels or "
            "answers were generated.",
            "- Q&A sheet rows remain blank; no Q&A benchmark could be evaluated without "
            "human-written questions and answers.",
            "",
            "| Metric | Result |",
            "|---|---:|",
        ]
        for cutoff in (1, 3, 5):
            summary_lines.append(
                f"| Hit@{cutoff} | {hits[cutoff]}/{count} "
                f"({hits[cutoff] / max(1, count):.1%}) |"
            )
        summary_lines.append(
            f"| MRR@5 | {sum(reciprocal_ranks) / max(1, count):.4f} |"
        )
        summary_lines.extend([
            "",
            f"Per-query machine-only outcomes: `{OUTPUT.relative_to(ROOT)}`.",
            "Do not interpret these proxy metrics as human-validated performance.",
        ])
        SUMMARY.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
        log_lines.extend([
            f"Corpus passages: {len(passages)}",
            f"Queries evaluated: {count}",
            *(f"Hit@{cutoff}: {hits[cutoff]}/{count}" for cutoff in (1, 3, 5)),
            f"MRR@5: {sum(reciprocal_ranks) / max(1, count):.4f}",
            f"Per-query output: {OUTPUT.relative_to(ROOT)}",
            f"Summary: {SUMMARY.relative_to(ROOT)}",
        ])
        print("\n".join(log_lines), flush=True)
    except Exception as exc:
        log_lines.append(f"FAILED: {type(exc).__name__}: {exc}")
        print(log_lines[-1], flush=True)
        LOG.write_text("\n".join(log_lines) + "\n", encoding="utf-8")
        raise
    LOG.write_text("\n".join(log_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
