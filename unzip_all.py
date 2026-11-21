import zipfile, os, glob

# exact zip name (without .zip, lowercase) -> target folder
RULES = [
    ("acord",      "05_acord"),        # "ACORD Dataset & ReadMe"
    ("contract-nli", "07_contractnli"),  # "contract-nli"
    ("sroie",      "12_sroie"),        # "SROIE2019-2026..."
    ("dataset",    "11_funsd"),        # "dataset" (FUNSD)
]

for z in glob.glob("zips/*.zip"):
    stem = os.path.splitext(os.path.basename(z))[0].lower()
    # exact-name match first, then startswith, so "ACORD Dataset" is never mistaken for "dataset"
    target = None
    for key, folder in RULES:
        if stem == key or (key != "dataset" and stem.startswith(key)):
            target = folder
            break
    if not target:
        print("NO MATCH, move by hand:", z)
        continue
    out = f"data/raw/{target}"
    os.makedirs(out, exist_ok=True)
    with zipfile.ZipFile(z) as f:
        f.extractall(out)
        print("OK  ", os.path.basename(z), "->", out, "| first items:", f.namelist()[:3])