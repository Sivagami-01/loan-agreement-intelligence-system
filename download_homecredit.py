import os
os.environ["KAGGLEHUB_CACHE"] = "data/raw/10_home_credit"
import kagglehub

path = kagglehub.competition_download("home-credit-default-risk")
print("Home Credit saved at:", path)
