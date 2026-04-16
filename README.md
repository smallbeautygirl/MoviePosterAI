# MoviePosterAI

自動電影海報生成與品質評估系統。使用 TMDB 資料、CLIP + NIMA 評估框架，以及 LLM 驅動的自適應提示詞優化。

---

## 專案結構

```
MoviePosterAI/
├── app/
│   ├── data_collection/
│   │   ├── call_tmdb_api_to_create_csv.py      # 從 TMDB top_rated 收集 10,000 部電影 metadata
│   │   ├── collect_stratified_movies.py         # 分層抽樣：4 個評分區間各 500 部（用於評估框架驗證）
│   │   ├── download_images_from_csv.py          # 批次下載電影海報與 backdrop 圖片
│   │   └── csv/
│   │       ├── tmdb_top_rated_movies.csv                  # top_rated 電影 ID 清單
│   │       ├── tmdb_top_rated_movie_details_10000.csv     # 10,000 部電影完整 metadata
│   │       ├── tmdb_stratified_movies.csv                 # 分層抽樣電影 metadata（執行後產生）
│   │       └── movie_image_text_features.csv              # CLIP embeddings + consistency_score
│   ├── embedding/
│   │   └── get_image_and_text_feature.py        # 計算海報圖像與文字的 CLIP embedding 及 consistency_score
│   ├── pyproject.toml
│   └── uv.lock
└── docs/
    └── superpowers/specs/
        └── 2026-04-15-movie-poster-ai-design.md  # 研究計畫草稿
```

---

## 資料收集流程

### Step 1：收集電影 metadata

**用於生成實驗（reference posters）：**
```bash
cd app
uv run python data_collection/call_tmdb_api_to_create_csv.py
# 輸出：data_collection/csv/tmdb_top_rated_movie_details_10000.csv
```

**用於評估框架驗證（分層抽樣，評分分佈均勻）：**
```bash
uv run python data_collection/collect_stratified_movies.py
# 輸出：data_collection/csv/tmdb_stratified_movies.csv
# 評分區間：4.0–5.5 / 5.5–7.0 / 7.0–8.0 / 8.0–10.0，各 500 部
```

### Step 2：下載海報圖片

```bash
uv run python data_collection/download_images_from_csv.py
# 輸出：data_collection/images/posters/<movie_id>.jpg
#       data_collection/images/backdrops/<movie_id>.jpg
```

### Step 3：計算 CLIP embeddings

```bash
uv run python embedding/get_image_and_text_feature.py
# 輸出：data_collection/csv/movie_image_text_features.csv
# 欄位：id, consistency_score, img_embed_0..767, txt_embed_0..767
```

---

## 環境設定

複製 `.env.example` 並填入：

```
TMDB_API_KEY=your_bearer_token
TMDB_BASE_URL=https://api.themoviedb.org/3
CSV_DIRECTORY=data_collection/csv
POSTER_DIRECTORY=data_collection/images/posters
BACKDROP_DIRECTORY=data_collection/images/backdrops
LOG_DIRECTORY=logs
```

安裝依賴（使用 [uv](https://github.com/astral-sh/uv)）：

```bash
cd app
uv sync
```

---

## 資料收集進度

| 項目 | 狀態 |
|---|---|
| 10,000 部電影 metadata（top_rated） | ✅ 完成 |
| 海報批次下載腳本 | ✅ 完成 |
| CLIP embedding（768 維）+ consistency_score | ✅ 完成 |
| 分層抽樣資料收集（4 評分區間） | 🔲 待執行 |
