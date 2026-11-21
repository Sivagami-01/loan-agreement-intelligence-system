"""src/qa/doc_loader.py

Document loader helper for ingested files in data/processed/ingested/.
Shared by src/qa/retrieve.py and src/qa/answer.py to avoid circular imports.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INGESTED_DIR = ROOT / "data" / "processed" / "ingested"


def load_document(doc_id: str) -> tuple[str, dict[int, str]]:
    """Loads document full text and per-page mapping from data/processed/ingested.

    Args:
        doc_id: filename or stem of ingested document.

    Returns:
        (full_text_with_markers, doc_pages_dict)
    """
    stem = Path(doc_id).stem
    json_path = INGESTED_DIR / f"{stem}.json"
    txt_path = INGESTED_DIR / f"{stem}.txt"

    doc_pages: dict[int, str] = {}
    full_text = ""

    # 1. Prefer structured JSON if present
    if json_path.is_file():
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            pages_list = data.get("pages", [])
            for p in pages_list:
                p_num = int(p.get("page", 0))
                p_text = str(p.get("text", ""))
                if p_num > 0:
                    doc_pages[p_num] = p_text
        except Exception:
            pass

    # 2. Load plain text with [[PAGE n]] markers
    if txt_path.is_file():
        try:
            full_text = txt_path.read_text(encoding="utf-8")
            if not doc_pages:
                pattern = re.compile(r"\[\[PAGE\s+(\d+)\]\]")
                parts = pattern.split(full_text)
                if len(parts) > 1:
                    for i in range(1, len(parts), 2):
                        p_num = int(parts[i])
                        p_text = parts[i + 1]
                        doc_pages[p_num] = p_text
        except Exception:
            pass

    # If full_text wasn't loaded from txt, reconstruct it from doc_pages
    if not full_text and doc_pages:
        reconstructed = []
        for p_num in sorted(doc_pages.keys()):
            reconstructed.append(f"[[PAGE {p_num}]]\n{doc_pages[p_num]}")
        full_text = "\n\n".join(reconstructed)

    return full_text, doc_pages
