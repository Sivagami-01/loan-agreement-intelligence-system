import requests, os, re
from urllib.parse import urlparse, unquote

OUT = "data/raw/08_indian_bank_loans"
os.makedirs(OUT, exist_ok=True)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

urls = [u.strip() for u in open("url.txt", encoding="utf-8") if u.strip().startswith("http")]
ok, failed = 0, []

for i, url in enumerate(urls, 1):
    name = unquote(os.path.basename(urlparse(url).path)) or f"file_{i}.pdf"
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)[:70]
    host = urlparse(url).netloc.replace("www.", "").split(".")[0]
    path = os.path.join(OUT, f"{i:02d}_{host}_{name}")
    if not path.lower().endswith(".pdf"):
        path += ".pdf"
    if os.path.exists(path):
        print("HAVE", i, name)
        ok += 1
        continue
    try:
        r = requests.get(url, headers=HEADERS, timeout=(10, 60))
        r.raise_for_status()
        if not r.content.startswith(b"%PDF"):
            raise ValueError("not a PDF (site returned a web page)")
        open(path, "wb").write(r.content)
        print("OK  ", i, f"{len(r.content)//1024} KB", name)
        ok += 1
    except Exception as e:
        print("FAIL", i, type(e).__name__, str(e)[:60], "|", url[:70])
        failed.append(url)

print(f"\nDone: {ok} saved, {len(failed)} failed")
for u in failed:
    print("Download by hand:", u)