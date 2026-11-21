import os
os.environ["KAGGLEHUB_CACHE"] = "data/raw/10_home_credit"

from datasets import load_dataset
from PIL import Image
import kagglehub

Image.MAX_IMAGE_PIXELS = None

# DocVQA-2026: stored in your folder instead of the default cache
ds = load_dataset("VLR-CVC/DocVQA-2026", split="val", cache_dir="data/raw/13_docvqa")
print("DocVQA samples:", len(ds))

# Home Credit (you must have joined the competition on Kaggle)
path = kagglehub.competition_download("home-credit-default-risk")
print("Home Credit saved at:", path)