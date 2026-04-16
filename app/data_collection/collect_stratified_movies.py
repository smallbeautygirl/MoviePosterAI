from __future__ import annotations

import json
import logging
import os
import time

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE_URL = os.getenv("TMDB_BASE_URL")
DISCOVER_URL = f"{TMDB_BASE_URL}/discover/movie"
DETAIL_URL = f"{TMDB_BASE_URL}/movie/{{}}"
HEADERS = {
    "Authorization": f"Bearer {TMDB_API_KEY}",
    "accept": "application/json",
}

csv_directory = os.getenv("CSV_DIRECTORY", "data_collection/csv")
os.makedirs(csv_directory, exist_ok=True)

log_directory = os.getenv("LOG_DIRECTORY", "logs")
os.makedirs(log_directory, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(log_directory, "collect_stratified_movies.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# 分層抽樣設定：4 個評分區間，各抽 500 部
# vote_count.gte=200 確保評分有統計意義
RATING_BANDS = [
    {"name": "low",       "gte": 4.5, "lte": 5.5, "target": 500},
    {"name": "medium",    "gte": 5.5, "lte": 6.5, "target": 500},
    {"name": "good",      "gte": 6.5, "lte": 7.5, "target": 500},
    {"name": "excellent", "gte": 7.5, "lte": 10.0, "target": 500},
]
MIN_VOTE_COUNT = 200
RELEASE_DATE_GTE = "2000-01-01"  # 2000 年後，數位設計普及、風格一致
OUTPUT_FILENAME = os.path.join(csv_directory, "tmdb_stratified_movies.csv")


def fetch_movie_ids_for_band(
    vote_gte: float,
    vote_lte: float,
    target_count: int,
) -> list[int]:
    """Discover endpoint で評分区間内の映画IDを収集する。"""
    movie_ids: list[int] = []
    page = 1

    while len(movie_ids) < target_count:
        params = {
            "vote_average.gte": vote_gte,
            "vote_average.lte": vote_lte,
            "vote_count.gte": MIN_VOTE_COUNT,
            "primary_release_date.gte": RELEASE_DATE_GTE,
            "sort_by": "vote_count.desc",
            "with_original_language": "en",  # 限英語電影，確保 overview 品質
            "page": page,
        }
        try:
            response = requests.get(DISCOVER_URL, headers=HEADERS, params=params)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Discover API error (band {vote_gte}–{vote_lte}, page {page}): {e}")
            time.sleep(5)
            continue
        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error: {e}")
            break

        results = data.get("results", [])
        if not results:
            logging.info(f"Band {vote_gte}–{vote_lte}: no more results at page {page}.")
            break

        ids = [movie["id"] for movie in results]
        movie_ids.extend(ids)
        logging.info(
            f"Band {vote_gte}–{vote_lte}: page {page}, "
            f"got {len(ids)}, total so far {len(movie_ids)}"
        )

        total_pages = data.get("total_pages", 1)
        if page >= total_pages:
            break

        page += 1
        time.sleep(0.25)

    return movie_ids[:target_count]


def fetch_movie_details(movie_id: int) -> dict | None:
    """電影 ID 對應的詳細資料。"""
    url = DETAIL_URL.format(movie_id)
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        return {
            "id": data.get("id"),
            "imdb_id": data.get("imdb_id"),
            "title": data.get("title"),
            "tagline": data.get("tagline"),
            "overview": data.get("overview"),
            "poster_path": data.get("poster_path"),
            "backdrop_path": data.get("backdrop_path"),
            "release_date": data.get("release_date"),
            "vote_average": data.get("vote_average"),
            "vote_count": data.get("vote_count"),
            "genres": [g["name"] for g in data.get("genres", [])],
            "budget": data.get("budget"),
            "revenue": data.get("revenue"),
            "runtime": data.get("runtime"),
            "rating_band": None,  # 填入後續
        }
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch details for movie {movie_id}: {e}")
        return None


def collect_all_bands() -> pd.DataFrame:
    """全 4 個評分帯分層収集し、DataFrame で返す。"""
    all_records: list[dict] = []

    for band in RATING_BANDS:
        logging.info(f"=== Collecting band: {band['name']} ({band['gte']}–{band['lte']}) ===")
        ids = fetch_movie_ids_for_band(band["gte"], band["lte"], band["target"])
        logging.info(f"Band {band['name']}: fetched {len(ids)} IDs, now getting details...")

        for movie_id in ids:
            detail = fetch_movie_details(movie_id)
            if detail and detail.get("overview") and detail.get("poster_path"):
                detail["rating_band"] = band["name"]
                all_records.append(detail)
            time.sleep(0.1)

        logging.info(f"Band {band['name']}: {len([r for r in all_records if r['rating_band'] == band['name']])} valid records.")

    return pd.DataFrame(all_records)


if __name__ == "__main__":
    if os.path.exists(OUTPUT_FILENAME):
        logging.info(f"{OUTPUT_FILENAME} already exists. Skipping collection.")
        df = pd.read_csv(OUTPUT_FILENAME)
    else:
        df = collect_all_bands()
        df.to_csv(OUTPUT_FILENAME, index=False, encoding="utf-8")
        logging.info(f"Saved {len(df)} records to {OUTPUT_FILENAME}.")

    # 印出各評分帯的分佈，確認分層效果
    print("\n=== 分層抽樣結果 ===")
    print(df.groupby("rating_band")["vote_average"].describe()[["count", "mean", "min", "max"]])
    print(f"\n總計：{len(df)} 部電影")
    print(f"整體 vote_average 範圍：{df['vote_average'].min():.1f} – {df['vote_average'].max():.1f}")
