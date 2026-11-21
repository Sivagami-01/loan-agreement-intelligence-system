import os, subprocess, requests
from datasets import load_dataset
from tqdm import tqdm

RAW = "data/raw"

def hf(name, folder, config=None):
    out = f"{RAW}/{folder}"
    os.makedirs(out, exist_ok=True)
    try:
        ds = load_dataset(name, config) if config else load_dataset(name)
        ds.save_to_disk(out)
        print("OK  ", folder)
    except Exception as e:
        print("FAIL", folder, e)

def run(cmd, label):
    r = subprocess.run(cmd, shell=True)
    print(("OK  " if r.returncode == 0 else "FAIL"), label)

def download(url, path):
    try:
        r = requests.get(url, stream=True)
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        with open(path, "wb") as f, tqdm(total=total, unit="B", unit_scale=True) as bar:
            for chunk in r.iter_content(1024 * 1024):
                f.write(chunk)
                bar.update(len(chunk))
        print("OK  ", path)
    except Exception as e:
        print("FAIL", path, e)

hf("theatticusproject/cuad", "01_cuad")
download("https://zenodo.org/records/4595826/files/CUAD_v1.zip", f"{RAW}/01_cuad/CUAD_v1.zip")
hf("coastalcph/lex_glue", "04_ledgar", "ledgar")
hf("naver-clova-ix/cord-v2", "14_cord")
hf("FiscalNote/billsum", "15_billsum")
hf("allenai/multi_lexsum", "16_multilexsum", "v20230518")

run(f"git clone https://github.com/AI4Bharat/IndicTrans2 {RAW}/17_indictrans2/repo", "17 IndicTrans2")
run(f"git clone https://github.com/facebookresearch/flores {RAW}/18_flores200/repo", "18 FLORES")

run(f"kaggle datasets download -d wordsforthewise/lending-club -p {RAW}/09_lending_club --unzip", "09 Lending Club")