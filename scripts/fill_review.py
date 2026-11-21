import csv
from pathlib import Path
csv.field_size_limit(2**31 - 1)
p = Path(r"data\processed\extract_3a_mismatch_review_filled.csv")
rows = list(csv.DictReader(p.open(encoding="utf-8-sig", newline="")))
print("COLUMNS:", list(rows[0].keys()))
print()
for n in (1, 7, 8, 16, 19, 20, 32, 54):
    r = rows[n - 1]
    print(f"--- row {n} | who_is_right = {r.get('who_is_right')}")
    for k, v in r.items():
        if k != "who_is_right":
            print(f"   {k}: {str(v)[:70]}")