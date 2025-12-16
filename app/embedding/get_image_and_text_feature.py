from dotenv import load_dotenv
import os
import logging
import torch
import pandas as pd
import open_clip
import numpy as np
from PIL import Image


load_dotenv()

# Settings
csv_directory = os.getenv("CSV_DIRECTORY")
print(csv_directory)
MOVIE_DETAILS_FILENAME = os.path.join(csv_directory, 'tmdb_top_rated_movie_details_100.csv')

POSTER_DIRECTORY = os.getenv("POSTER_DIRECTORY")

log_directory = os.getenv("LOG_DIRECTORY")
log_filename = "get_image_and_text_feature.log"
log_filepath = os.path.join(log_directory, log_filename)

logging.basicConfig(filename=log_filepath, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

MODEL_NAME = "ViT-H-14" # ViT-H-14 的 Embedding 維度是 768
PRETRAINED_DATASET = 'laion2b_s32b_b79k'
EMBEDDING_DIM = 768
device = "cuda" if torch.cuda.is_available() else "cpu"
model, _, preprocess = open_clip.create_model_and_transforms(MODEL_NAME, pretrained=PRETRAINED_DATASET,
device=device)

model.eval()  # model in train mode by default, impacts some models with BatchNorm or stochastic depth active
tokenizer = open_clip.get_tokenizer(MODEL_NAME)

def get_text_embedding(text: str) -> np.ndarray:
    with torch.no_grad(): # no gradient computation
        text_tokens = tokenizer([text]).to(device)
        text_embedding = model.encode_text(text_tokens)

        # normalize text embedding
        text_embedding /= text_embedding.norm(dim=-1, keepdim=True)

    return text_embedding.cpu().numpy()[0]

def get_image_embedding(image_path:str) -> np.ndarray:
    image = Image.open(image_path).convert("RGB")
    image = preprocess(image).unsqueeze(0).to(device)

    with torch.no_grad():
        image_embedding = model.encode_image(image)
        image_embedding = image_embedding / image_embedding.norm(dim=1,keepdim=True)

    return image_embedding.cpu().numpy()[0]

def extract_features(df: pd.DataFrame ) -> pd.DataFrame:
    """
    Extract poster image and overview text features for each movie in the dataframe. And compute similarity score.
    """
    all_features = []

    # *** 這裡就是 embed_cols 的用途：定義 512 個圖片和 512 個文本欄位名稱 ***
    embed_cols = [f'img_embed_{i}' for i in range(EMBEDDING_DIM)] + [f'txt_embed_{i}' for i in range(EMBEDDING_DIM)]
    
    for index,row in df.iterrows():
        movie_id = row['id']
        overview = row['overview']
        tagline = row['tagline']
        poster_path = os.path.join(POSTER_DIRECTORY, f"{movie_id}.jpg")
        try:
            

            # Get embeddings
            img_embedding = get_image_embedding(poster_path)
            # txt_embedding = get_text_embedding(overview)
            txt_embedding = get_text_embedding(tagline)
            # Combine embeddings
            combined_embedding = np.concatenate((img_embedding, txt_embedding))

            # all_features.append(combined_embedding)

            logging.info(f"Extracted features for movie_id: {movie_id}")

            consistency_score = np.dot(img_embedding, txt_embedding)
            logging.info(f"Consistency score for movie_id {movie_id}: {consistency_score}")

            feature_row = {
                'id': movie_id,
                'consistency_score': consistency_score,
                **{col: val for col, val in zip(embed_cols, combined_embedding)}
            }

            all_features.append(feature_row)

            if index % 10 ==0:
                logging.info(f"Processed {index} / {len(df)} movies. ")
        except Exception as e:
            logging.error(f"Error processing movie_id {movie_id}: {e}")
            feature_row = {
                'id': movie_id,
                'consistency_score': np.nan,
                **{col: np.nan for col in embed_cols}
            }
    return pd.DataFrame(all_features)

if __name__ == "__main__":
    # Load movie details
    movie_df = pd.read_csv(MOVIE_DETAILS_FILENAME)

    # Extract features
    features_df = extract_features(movie_df)

    # Save features to CSV
    output_filepath = os.path.join(csv_directory, 'movie_image_text_features.csv')
    features_df.to_csv(output_filepath, index=False)
    logging.info(f"Saved extracted features to {output_filepath}")