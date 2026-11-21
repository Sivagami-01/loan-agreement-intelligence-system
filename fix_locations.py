import csv, pathlib
csv.field_size_limit(2**31 - 1)

base = pathlib.Path(r"C:\finalYear\data\processed_v1")
for name in ["manifest.csv", "clean_loans.csv", "gold_extra.csv"]:
    p = base / name
    with p.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)
    for row in rows:
        row["location"] = "zip:" + row["doc_id"]
    with p.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print("fixed", name, len(rows))