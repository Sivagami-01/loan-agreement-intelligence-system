import fitz, json, re
from pathlib import Path
from bs4 import BeautifulSoup

SOURCES = {
    "indian": ("data/raw/08_indian_bank_loans", "*.pdf", None),
    "edgar":  ("data/raw/02_sec_edgar_loans",   "*.htm*", 100),
    "cuad":   ("data/raw/01_cuad",              "*.pdf", 60),
}
OUT = Path("data/processed/parsed")

def bad_text(t):
    t = t.strip()
    if len(t) < 50:
        return True                      # empty page, probably scanned
    letters = sum(c.isalpha() for c in t)
    garbage = t.count("\ufffd") + t.count("(cid:")
    return letters / len(t) < 0.5 or garbage > 5

def parse_pdf(path):
    pages = []
    with fitz.open(path) as doc:
        for i, p in enumerate(doc, 1):
            text = p.get_text()
            pages.append({"page": i, "text": text, "needs_ocr": bad_text(text)})
    return pages

def parse_html(path):
    raw = Path(path).read_bytes().decode("utf-8", errors="ignore")
    text = BeautifulSoup(raw, "lxml").get_text("\n")
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    pages, cur = [], ""
    for para in text.split("\n\n"):
        if len(cur) + len(para) > 3000 and cur:
            pages.append(cur); cur = ""
        cur += para + "\n\n"
    if cur.strip():
        pages.append(cur)
    return [{"page": i, "text": t, "needs_ocr": False} for i, t in enumerate(pages, 1)]

for name, (folder, pattern, limit) in SOURCES.items():
    files = sorted(Path(folder).rglob(pattern))
    if limit:
        files = files[:limit]
    out_dir = OUT / name
    out_dir.mkdir(parents=True, exist_ok=True)
    total_pages = ocr_pages = ok = 0
    for f in files:
        try:
            pages = parse_pdf(f) if f.suffix.lower() == ".pdf" else parse_html(f)
        except Exception as e:
            print("FAIL", f.name[:50], type(e).__name__)
            continue
        out_file = out_dir / (re.sub(r"[^A-Za-z0-9._-]+", "_", f.stem)[:80] + ".json")
        out_file.write_text(json.dumps({"source": str(f), "pages": pages}, ensure_ascii=False), encoding="utf-8")
        total_pages += len(pages)
        ocr_pages += sum(p["needs_ocr"] for p in pages)
        ok += 1
    print(f"{name:7} docs: {ok}/{len(files)}  pages: {total_pages}  need OCR/garbled: {ocr_pages}")