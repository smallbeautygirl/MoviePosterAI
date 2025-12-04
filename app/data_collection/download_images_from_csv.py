from dotenv import load_dotenv
import os
import pandas as pd
import logging

load_dotenv()

# Settings
csv_directory = os.getenv("CSV_DIRECTORY", "data_collection/csv")
if not os.path.exists(csv_directory):
    os.makedirs(csv_directory)

MOVIE_DETAILS_FILENAME = os.path.join(csv_directory, 'tmdb_top_rated_movie_details_100.csv')
BACKDROP_DIRECTORY = os.getenv("BACKDROP_DIRECTORY", "data_collection/images/backdrops")
POSTER_DIRECTORY = os.getenv("POSTER_DIRECTORY", "data_collection/images/posters")
if not os.path.exists(BACKDROP_DIRECTORY):
    os.makedirs(BACKDROP_DIRECTORY)
if not os.path.exists(POSTER_DIRECTORY):
    os.makedirs(POSTER_DIRECTORY)

log_directory = os.getenv("LOG_DIRECTORY", "logs")
log_filename = "download_images_from_csv.log"
log_filepath = os.path.join(log_directory, log_filename)

logging.basicConfig(filename=log_filepath, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def download_image(image_path:str, save_path:str):
    """ Download image from TMDB and save to local path. """
    import requests
    TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/original"
    if pd.isna(image_path):
        logging.warning(f"No image path provided for {save_path}. Skipping download.")
        return
    url = f"{TMDB_IMAGE_BASE_URL}{image_path}"
    logging.info(f"Downloading image from {url} to {save_path}")
    response = requests.get(url)
    if response.status_code == 200:
        with open(save_path, 'wb') as f:
            f.write(response.content)
        logging.info(f"Downloaded image to {save_path}")
    else:
        logging.error(f"Failed to download image from {url}. Status code: {response.status_code}")

def read_movie_details_csv():
    """ Read movie details from CSV file. And download backdrop and poster images. """
    df = pd.read_csv(MOVIE_DETAILS_FILENAME)
    for index, row in df.iterrows():
        backdrop_path = row['backdrop_path']
        poster_path = row['poster_path']
        download_image(backdrop_path, os.path.join(BACKDROP_DIRECTORY, f"{row['id']}.jpg"))
        download_image(poster_path, os.path.join(POSTER_DIRECTORY, f"{row['id']}.jpg"))

if __name__ == "__main__":
    logging.info("Starting image download process from CSV...")
    read_movie_details_csv()
    logging.info("Image download process completed.")