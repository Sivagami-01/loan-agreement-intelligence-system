import json
from pathlib import Path
from collections import Counter

RANGES = {"Devanagari": (0x0900, 0x097F), "Bengali": (0x0980, 0x09FF),
          "Gurmukhi": (0x0A00, 0x0A7F), "Malayalam": (0x0D00, 0x0D7F)}

def scripts(text):
    c = Counter()
    for ch in text:
        o = ord(ch)
        for name, (a, b) in RANGES.items():
            if a <= o <= b:
                c[name] += 1
                break
        else:
            if ch.isalpha():
                c["Latin/other"] += 1
    return c

base = Path("data/processed/parsed")
out = open("data/processed/indian_samples.txt", "w", encoding="utf-8")

print("=== INDIAN PDFs")
for f in sorted((base / "indian").glob("*.json")):
    d = json.loads(f.read_text(encoding="utf-8"))
    pages = d["pages"]
    total = scripts(" ".join(p["text"] for p in pages))
    flagged = [p["page"] for p in pages if p["needs_ocr"]]
    print(f"{f.name[:60]:60} pages={len(pages):3} flagged={flagged} scripts={dict(total.most_common(3))}")
    mid = pages[len(pages) // 2]
    out.write(f"\n##### {f.name} | page {mid['page']}\n{mid['text'][:600]}\n")

print("\n=== CUAD docs with flagged pages")
for f in sorted((base / "cuad").glob("*.json")):
    d = json.loads(f.read_text(encoding="utf-8"))
    flagged = [p["page"] for p in d["pages"] if p["needs_ocr"]]
    if flagged:
        print(f"{f.name[:60]:60} pages={len(d['pages']):3} flagged={flagged}")
out.close()
print("\nSamples saved to data/processed/indian_samples.txt")