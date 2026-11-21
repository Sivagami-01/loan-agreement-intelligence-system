"""src/qa/retrieve.py

Pure-Python BM25 Retriever for Long Documents (Stage 2c-2a).
- Unicode-safe tokenizer supporting English, Hindi, Bengali, Punjabi, and Malayalam
  (preserves Unicode combining marks and virama conjuncts).
- Removes a compact English stop-word list for English tokens.
- Pure-Python Okapi BM25 scoring (k1=1.5, b=0.75) with deterministic tie-breaking.
- Caches chunked BM25 indexes in data/processed/retrieval_cache/.
"""

from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any
import json

import yaml

from src.qa.doc_loader import load_document
from src.qa.chunker import chunk_document

ROOT = Path(__file__).resolve().parents[2]
RETRIEVAL_CONFIG_FILE = ROOT / "config" / "retrieval.yaml"
RETRIEVAL_CACHE_DIR = ROOT / "data" / "processed" / "retrieval_cache"

# Build Unicode combining-mark class once at import time so re.findall keeps
# Indic matras/viramas attached to base letters instead of splitting mid-word.
_COMBINING_MARKS = "".join(
    chr(cp) for cp in range(0x10000) if unicodedata.category(chr(cp)).startswith("M")
)
_WORD_RE = re.compile(
    r"(?:[^\W_]|[" + re.escape(_COMBINING_MARKS) + r"\u200C\u200D])+"
)

ENGLISH_STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "but", "by",
    "can", "could", "did", "do", "does", "for", "from", "had", "has", "have",
    "he", "her", "here", "his", "how", "i", "if", "in", "into", "is", "it",
    "its", "may", "me", "my", "of", "on", "or", "our", "she", "should", "so",
    "such", "that", "the", "their", "them", "there", "these", "they", "this",
    "those", "to", "was", "we", "were", "what", "when", "where", "which",
    "who", "whom", "why", "will", "with", "would", "you", "your",
})


def load_retrieval_config() -> dict[str, Any]:
    if RETRIEVAL_CONFIG_FILE.is_file():
        try:
            data = yaml.safe_load(RETRIEVAL_CONFIG_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {
        "chunk_chars": 2000,
        "chunk_overlap": 200,
        "top_k": 8,
        "bm25_k1": 1.5,
        "bm25_b": 0.75,
        "max_prompt_chars": 60000,
        "force_retrieval": False,
    }


def _is_primarily_english(text: str) -> bool:
    """Checks if the alphabetic content of text is English/Latin."""
    latin = 0
    non_latin_alpha = 0
    for ch in text:
        if ch.isalpha():
            if ch.isascii():
                latin += 1
            else:
                non_latin_alpha += 1
    return latin > 0 and latin >= non_latin_alpha


def tokenize(text: str, remove_english_stopwords: bool | None = None) -> list[str]:
    """Unicode-aware lowercase word & number tokenizer.

    Preserves Unicode combining marks (Hindi, Bengali, Punjabi, Malayalam).
    Applies English stop-word removal only for English text (or ASCII tokens).
    """
    if not text:
        return []

    norm = unicodedata.normalize("NFC", str(text)).lower()
    raw_tokens = _WORD_RE.findall(norm)

    # Keep tokens that contain at least one letter or digit (skip stray joiners/marks)
    tokens = [tok for tok in raw_tokens if any(ch.isalnum() for ch in tok)]
    if not tokens:
        return []

    if remove_english_stopwords is None:
        use_stopwords = _is_primarily_english(norm)
    else:
        use_stopwords = remove_english_stopwords

    if use_stopwords:
        filtered = [
            tok for tok in tokens
            if not (tok.isascii() and tok in ENGLISH_STOPWORDS)
        ]
        # Guard against all-stopword queries becoming empty
        if filtered:
            return filtered

    return tokens


class BM25Index:
    """Pure-Python Okapi BM25 index over document chunks."""

    def __init__(
        self,
        doc_id: str,
        chunks: list[dict[str, Any]],
        k1: float = 1.5,
        b: float = 0.75,
        tf_list: list[dict[str, int]] | None = None,
        df: dict[str, int] | None = None,
        avgdl: float | None = None,
    ) -> None:
        self.doc_id = doc_id
        self.chunks = chunks
        self.k1 = float(k1)
        self.b = float(b)
        self.n_docs = len(chunks)

        if tf_list is not None and df is not None and avgdl is not None:
            self.tf_list = tf_list
            self.df = df
            self.avgdl = avgdl
            self.doc_lens = [sum(tf.values()) for tf in tf_list]
        else:
            self.tf_list = []
            self.df = {}
            self.doc_lens = []
            for ch in chunks:
                toks = tokenize(ch.get("text", ""))
                counts = Counter(toks)
                self.tf_list.append(dict(counts))
                self.doc_lens.append(len(toks))
                for term in counts:
                    self.df[term] = self.df.get(term, 0) + 1
            self.avgdl = (sum(self.doc_lens) / self.n_docs) if self.n_docs > 0 else 0.0

    def score_query(self, question: str) -> list[dict[str, Any]]:
        if self.n_docs == 0:
            return []

        q_tokens = tokenize(question)
        if not q_tokens:
            # Fallback: try without stopword removal
            q_tokens = tokenize(question, remove_english_stopwords=False)
        if not q_tokens:
            return []

        avgdl = self.avgdl if self.avgdl > 0 else 1.0
        q_counts = Counter(q_tokens)

        scored: list[tuple[float, int, int, str, int]] = []
        for idx, ch in enumerate(self.chunks):
            tf = self.tf_list[idx]
            dl = self.doc_lens[idx]
            score = 0.0

            for term, q_freq in q_counts.items():
                freq = tf.get(term, 0)
                if freq == 0:
                    continue
                n_q = self.df.get(term, 0)
                # Non-negative BM25 IDF variant suited for single-doc chunk retrieval
                idf = math.log(((self.n_docs - n_q + 0.5) / (n_q + 0.5)) + 1.0)
                denom = freq + self.k1 * (1.0 - self.b + self.b * (dl / avgdl))
                tf_norm = (freq * (self.k1 + 1.0)) / denom
                score += idf * tf_norm * q_freq

            scored.append((
                score,
                -int(ch.get("page", 0)),
                -int(ch.get("char_start", 0)),
                str(ch.get("chunk_id", "")),
                idx,
            ))

        # Deterministic sort: highest score first, then earliest page, earliest offset, chunk_id
        scored.sort(key=lambda item: (-item[0], -item[1], -item[2], item[3]))

        results: list[dict[str, Any]] = []
        for rank, (score, _neg_page, _neg_start, _cid, idx) in enumerate(scored, 1):
            chunk_copy = dict(self.chunks[idx])
            chunk_copy["score"] = round(float(score), 6)
            chunk_copy["rank"] = rank
            results.append(chunk_copy)

        return results

    def to_cache_dict(self, content_hash: str, chunk_chars: int, chunk_overlap: int) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "content_hash": content_hash,
            "chunk_chars": chunk_chars,
            "chunk_overlap": chunk_overlap,
            "bm25_k1": self.k1,
            "bm25_b": self.b,
            "avgdl": self.avgdl,
            "df": self.df,
            "chunks": self.chunks,
            "tf_list": self.tf_list,
        }

    @classmethod
    def from_cache_dict(cls, data: dict[str, Any]) -> BM25Index:
        return cls(
            doc_id=str(data["doc_id"]),
            chunks=list(data["chunks"]),
            k1=float(data.get("bm25_k1", 1.5)),
            b=float(data.get("bm25_b", 0.75)),
            tf_list=list(data["tf_list"]),
            df=dict(data["df"]),
            avgdl=float(data["avgdl"]),
        )


def _compute_pages_hash(doc_pages: dict[int, str], config: dict[str, Any]) -> str:
    hasher = hashlib.sha256()
    hasher.update(
        f"cc={config.get('chunk_chars')}|co={config.get('chunk_overlap')}|"
        f"k1={config.get('bm25_k1')}|b={config.get('bm25_b')}|".encode("utf-8")
    )
    for p_num in sorted(doc_pages.keys()):
        hasher.update(f"[{p_num}]".encode("utf-8"))
        hasher.update(doc_pages[p_num].encode("utf-8", errors="ignore"))
    return hasher.hexdigest()


def _safe_cache_filename(doc_id: str) -> str:
    stem = Path(doc_id).stem
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("_")
    return f"{safe or 'doc'}.json"


def build_or_load_index(
    doc_id: str,
    doc_pages: dict[int, str] | None = None,
    config: dict[str, Any] | None = None,
    use_cache: bool = True,
) -> BM25Index:
    """Builds a BM25 index over document chunks, loading/saving in retrieval_cache."""
    if config is None:
        config = load_retrieval_config()

    chunk_chars = int(config.get("chunk_chars", 2000))
    chunk_overlap = int(config.get("chunk_overlap", 200))
    k1 = float(config.get("bm25_k1", 1.5))
    b = float(config.get("bm25_b", 0.75))

    if doc_pages is None:
        _full_text, doc_pages = load_document(doc_id)

    if not doc_pages:
        return BM25Index(doc_id=doc_id, chunks=[], k1=k1, b=b)

    content_hash = _compute_pages_hash(doc_pages, config)
    cache_path = RETRIEVAL_CACHE_DIR / _safe_cache_filename(doc_id)

    if use_cache and cache_path.is_file():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            if cached.get("content_hash") == content_hash:
                return BM25Index.from_cache_dict(cached)
        except Exception:
            pass

    chunks = chunk_document(
        doc_id=doc_id,
        doc_pages=doc_pages,
        chunk_chars=chunk_chars,
        chunk_overlap=chunk_overlap,
    )
    index = BM25Index(doc_id=doc_id, chunks=chunks, k1=k1, b=b)

    if use_cache:
        try:
            RETRIEVAL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(
                json.dumps(
                    index.to_cache_dict(content_hash, chunk_chars, chunk_overlap),
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        except Exception:
            pass

    return index


def retrieve(
    doc_id: str,
    question: str,
    top_k: int | None = None,
    doc_pages: dict[int, str] | None = None,
    config: dict[str, Any] | None = None,
    use_cache: bool = True,
) -> list[dict[str, Any]]:
    """Retrieves the top_k BM25 chunks for a question from a document."""
    if config is None:
        config = load_retrieval_config()

    k = int(top_k if top_k is not None else config.get("top_k", 8))
    index = build_or_load_index(
        doc_id=doc_id,
        doc_pages=doc_pages,
        config=config,
        use_cache=use_cache,
    )
    ranked = index.score_query(question)
    return ranked[:k]
