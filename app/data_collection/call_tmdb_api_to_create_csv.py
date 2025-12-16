import requests
import pandas as pd
import time
import json
import logging
import os
from dotenv import load_dotenv

load_dotenv()
# --- 設定 ---
# 請將這裡替換為您的 TMDB API 讀取權限 Token
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE_URL = os.getenv("TMDB_BASE_URL")
TOP_RATED_URL = f'{TMDB_BASE_URL}/movie/top_rated'
DETAIL_URL = f'{TMDB_BASE_URL}/movie/{{}}'  # 需要填入 movie_id
HEADERS = {
    'Authorization': f'Bearer {TMDB_API_KEY}',
    'accept': 'application/json'
}
csv_directory = os.getenv("CSV_DIRECTORY", "data_collection/csv")
if not os.path.exists(csv_directory):
    os.makedirs(csv_directory)
TOP_RATED_MOVIE_IDS_FILENAME = os.path.join(csv_directory, 'tmdb_top_rated_movies.csv')
MOVIE_DETAILS_FILENAME = os.path.join(csv_directory, 'tmdb_top_rated_movie_details_10000.csv')

# 設定日誌，方便追蹤進度與錯誤
# Define the log file path
log_directory = os.getenv("LOG_DIRECTORY", "logs")
log_filename = "tmdb_api_details_10000.log"
log_filepath = os.path.join(log_directory, log_filename)

# Ensure the log directory exists
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

logging.basicConfig(filename=log_filepath, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def fetch_tmdb_top_rated_data(max_pages=None):
    """
    從 TMDB 的 top_rated API 獲取所有分頁的電影數據。

    Args:
        max_pages (int, optional): 可選的最大頁數限制。若為 None，則獲取所有頁面。
    
    Returns:
        list: 包含所有電影數據字典的列表。
    """
    all_movie_ids = []
    current_page = 1
    total_pages = 1 # 初始值，會在第一次呼叫後更新

    logging.info(f"開始從 TMDB Top Rated API 收集數據...")

    while current_page <= total_pages:
        if max_pages is not None and current_page > max_pages:
            logging.warning(f"已達到設定的最大頁數限制 ({max_pages})，停止收集。")
            break

        params = {'page': current_page}
        
        try:
            # 執行 API 呼叫
            response = requests.get(TOP_RATED_URL, headers=HEADERS, params=params)
            response.raise_for_status() # 檢查是否有 HTTP 錯誤 (4xx 或 5xx)
            data = response.json()

            # 第一次呼叫時獲取總頁數
            if current_page == 1:
                total_pages = data.get('total_pages', 1)
                # 為了避免一次性拉取超過 10000 筆資料 (API 限制)，通常會限制在 500 頁
                if total_pages > 500:
                    logging.warning(f"總頁數為 {total_pages}，但 TMDB 通常只允許訪問前 500 頁。將總頁數限制為 500。")
                    total_pages = 500
                logging.info(f"偵測到 {data.get('total_results', '未知')} 筆結果，共 {total_pages} 頁。")

            # only fetch id
            movie_ids = [movie['id'] for movie in data.get('results', [])]
            all_movie_ids.extend(movie_ids)
            logging.info(f"已成功收集第 {current_page} 頁，共 {len(movie_ids)} 筆電影 ID。")
            
            # 準備下一頁
            current_page += 1
            
            # 延遲以避免觸發速率限制
            time.sleep(0.5)

        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTP 錯誤發生在第 {current_page} 頁: {e}")
            break
        except requests.exceptions.RequestException as e:
            logging.error(f"連線錯誤發生在第 {current_page} 頁: {e}")
            # 遇到連線問題時等待更久再重試
            time.sleep(5)
        except json.JSONDecodeError as e:
            logging.error(f"JSON 解析錯誤發生在第 {current_page} 頁: {e}")
            break
        
    return all_movie_ids

def fetch_movie_details(movie_id):
    """
    根據電影 ID 從 TMDB 獲取詳細電影資訊。
    """
    url = DETAIL_URL.format(movie_id)
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()

        logging.info(f"Fetched details for movie ID {movie_id} successfully.")
        # Only return required fields if needed
        movie_details = {
            'id': response.json().get('id'),
            'imdb_id': response.json().get('imdb_id'),
            'title': response.json().get('title'),
            'tagline': response.json().get('tagline'),
            'overview': response.json().get('overview'),
            'poster_path': response.json().get('poster_path'),
            'backdrop_path': response.json().get('backdrop_path'),
            'release_date': response.json().get('release_date'),
            'vote_average': response.json().get('vote_average'),
            'vote_count': response.json().get('vote_count'),
            'genres': [genre['name'] for genre in response.json().get('genres', [])],
            'budget': response.json().get('budget'),
            'revenue': response.json().get('revenue'),
            'runtime': response.json().get('runtime'),

        }
        return movie_details
    except requests.exceptions.RequestException as e:
        logging.error(f"無法獲取電影 ID {movie_id} 的詳細資訊: {e}")
        return None

def save_ids_to_csv(movie_ids, filename):
    """
    將電影 ID 列表儲存為 CSV 檔案。
    """
    df = pd.DataFrame(movie_ids, columns=['movie_id'])
    df.to_csv(filename, index=False, encoding='utf-8')
    logging.info(f"成功將 {len(movie_ids)} 筆電影 ID 儲存到 {filename} 中。")

def save_details_to_csv(data_list:list, filename:str, filtered: bool = False):
    """
    將電影數據列表儲存為 CSV 檔案。
    """
    if not data_list:
        logging.warning("No data to save.")
        return

    df = pd.DataFrame(data_list, columns=[
        'id', 'imdb_id', 'title', 'tagline', 'overview', 'poster_path', 'backdrop_path',
        'release_date', 'vote_average', 'vote_count', 'genres', 'budget', 'revenue', 'runtime'
    ])
    
    if filtered:
        # 執行研究所需的數據清洗 (例如，過濾掉 vote_count 太少的電影)
        # 我們在步驟一的規劃中提到這個重要步驟，先在這裡加入示範
        MIN_VOTES = 1000 
        df_filtered = df[(df['vote_count'] >= MIN_VOTES) & (df['overview'].notna()) & (df['poster_path'].notna())]
        
        # 儲存到 CSV
        df_filtered.to_csv(filename, index=False, encoding='utf-8')
        
        logging.info(f"成功將 {len(df_filtered)} 筆電影數據儲存到 {filename} 中。")
        logging.info(f"原始數據共 {len(df)} 筆，過濾掉 {len(df) - len(df_filtered)} 筆低投票數或缺失數據的電影。")
    else:
        df.to_csv(filename, index=False, encoding='utf-8')
        logging.info(f"成功將 {len(df)} 筆電影數據儲存到 {filename} 中。")

# --- 主程式執行區塊 ---
if __name__ == "__main__":
    # 您可以調整 max_pages 來限制收集的資料量，例如 max_pages=100
    # 如果要收集所有數據，請保持 max_pages=None
    if not os.path.exists(TOP_RATED_MOVIE_IDS_FILENAME):
        movie_ids = fetch_tmdb_top_rated_data(max_pages=None)
        save_ids_to_csv(movie_ids, TOP_RATED_MOVIE_IDS_FILENAME)
        logging.info("Get movie ids finished.")
    else:
        logging.info(f"{TOP_RATED_MOVIE_IDS_FILENAME} already exists. Reading movie IDs from file...")
        movie_ids = pd.read_csv(TOP_RATED_MOVIE_IDS_FILENAME)['movie_id'].tolist()

    logging.info(f"There are total {len(movie_ids)} movie ids to fetch details.")
    logging.info(f"Now fetching detailed movie information...")
    movie_details = [fetch_movie_details(movie_id) for movie_id in movie_ids]

    # Store all movie details to the csv file
    save_details_to_csv(movie_details, MOVIE_DETAILS_FILENAME, filtered=False)
    # logging.info(f"下一步：請使用這個 {TOP_RATED_MOVIE_IDS_FILENAME} 檔案進行 VLM 特徵提取。")