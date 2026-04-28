# clip_model.py

# from sentence_transformers import SentenceTransformer
# from PIL import Image

# # ek baar load hoga jab app start hogi
# # model = SentenceTransformer("clip-ViT-B-32")
# model = SentenceTransformer("all-MiniLM-L6-v2")

# def get_image_vector(image_path: str) -> list:
#     """Image file path lo, CLIP se vector banao"""
#     image = Image.open(image_path)
#     vector = model.encode(image)
#     return vector.tolist()


from sympy import python


import torch
import open_clip
from PIL import Image

# lightweight OpenCLIP model
model, _, preprocess = open_clip.create_model_and_transforms(
    'ViT-B-32',
    pretrained='laion2b_s34b_b79k',
    device='cpu'
)

def get_image_vector(image_path: str) -> list:
    image = preprocess(Image.open(image_path)).unsqueeze(0)

    with torch.no_grad():
        image_features = model.encode_image(image)

    return image_features[0].cpu().numpy().tolist()



# def get_text_vector(text: str) -> list:
#     """Text lo, CLIP se vector banao — 77 token limit hai CLIP mein"""
#     # CLIP ki limit 77 tokens hai, isliye truncate karo
#     words = text.split()
#     short_text = " ".join(words[:50])  # safe limit
#     vector = model.encode(short_text)
#     return vector.tolist()

from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_text_vector(text: str) -> list:
    """OpenAI se text embedding banao — CLIP se better semantic search"""
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text[:2000]
    )
    return response.data[0].embedding