import requests, time, os
from collections import Counter

HEADERS = {"User-Agent": "Sivagami sivagameee@gmail.com"}   # use your real name and email
OUT = "data/raw/02_sec_edgar_loans"
os.makedirs(OUT, exist_ok=True)

QUERIES = ['"loan agreement"', '"credit agreement"', '"term loan agreement"', '"loan and security agreement"']
LIMIT = 300
KEEP = ("EX-10", "EX-4", "EX-99")
saved = len(os.listdir(OUT))
print("Already have:", saved)
seen_types = Counter()

def search(q, start):
    params = {"q": q, "forms": "8-K,10-K,10-Q",
              "dateRange": "custom", "startdt": "2018-01-01", "enddt": "2026-11-01", "from": start}
    try:
        r = requests.get("https://efts.sec.gov/LATEST/search-index",
                         params=params, headers=HEADERS, timeout=(10, 30))
        return r.json().get("hits", {}).get("hits", [])
    except Exception as e:
        print("  search error:", e)
        return []

for q in QUERIES:
    for start in range(0, 1000, 100):
        hits = search(q, start)
        print(f"{q} from {start}: {len(hits)} results | saved so far: {saved}")
        if not hits:
            break
        for h in hits:
            src = h.get("_source", {})
            ftype = str(src.get("file_type", "")).upper()
            seen_types[ftype] += 1
            if not ftype.startswith(KEEP):
                continue
            adsh, filename = h["_id"].split(":")
            cik = src["ciks"][0].lstrip("0")
            link = f"https://www.sec.gov/Archives/edgar/data/{cik}/{adsh.replace('-','')}/{filename}"
            path = os.path.join(OUT, f"{adsh}_{filename}")
            if os.path.exists(path):
                continue
            try:
                d = requests.get(link, headers=HEADERS, timeout=(10, 30))
                d.raise_for_status()
                open(path, "wb").write(d.content)
                saved += 1
                print("OK  ", saved, link)
            except Exception as e:
                print("SKIP", link, type(e).__name__)
            time.sleep(0.2)
            if saved >= LIMIT:
                print("File types seen:", seen_types.most_common(10))
                raise SystemExit("Reached limit")
        time.sleep(1)

print("File types seen:", seen_types.most_common(10))