import zipfile, os, re
from datasets import load_dataset

# 1. Unzip CUAD safely (shortens long filenames instead of crashing)
dest = os.path.abspath("data/raw/01_cuad")
skipped = 0
with zipfile.ZipFile("data/raw/01_cuad/CUAD_v1.zip") as z:
    for m in z.infolist():
        if m.is_dir():
            continue
        folder, name = os.path.split(m.filename)
        stem, ext = os.path.splitext(name)
        stem = re.sub(r"\s+", " ", stem).strip()[:80]   # collapse spaces, cut length
        target_dir = os.path.join(dest, folder)
        os.makedirs(target_dir, exist_ok=True)
        target = os.path.join(target_dir, stem + ext)
        try:
            with z.open(m) as src, open(target, "wb") as out:
                out.write(src.read())
        except Exception as e:
            skipped += 1
            print("SKIP", m.filename[:80], type(e).__name__)
print("OK   CUAD unzipped | skipped:", skipped)

# 2. Retry the two failed Hugging Face downloads
def try_load(name, config, folder):
    for rev in [None, "refs/convert/parquet"]:
        try:
            ds = load_dataset(name, config, revision=rev) if rev else load_dataset(name, config)
            ds.save_to_disk(f"data/raw/{folder}")
            print("OK  ", folder, "| revision:", rev)
            return
        except Exception as e:
            print("FAIL", folder, "| revision:", rev, "|", str(e)[:200])

try_load("coastalcph/lex_glue", "ledgar", "04_ledgar")
try_load("allenai/multi_lexsum", "v20230518", "16_multilexsum")