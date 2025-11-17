import kagglehub
from dotenv import load_dotenv
import os

load_dotenv()

print(os.environ.get("KAGGLEHUB_CACHE"))  # 測試是否讀到
# Download latest version
path = kagglehub.dataset_download("tmdb/tmdb-movie-metadata")

print("Path to dataset files:", path)
