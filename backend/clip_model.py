# clip_model.py

import requests
import base64
import os
from dotenv import load_dotenv

load_dotenv()

SPACE_URL = "https://vijayvsnv-clip-embedding-api.hf.space"


def get_image_vector(image_path: str) -> list:
    """Send image to CLIP HF Space, return 512-dim embedding."""
    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("utf-8")

    response = requests.post(
        f"{SPACE_URL}/image-embedding",
        json={"image_b64": image_b64},
        timeout=60
    )
    return response.json()["embedding"]


def get_text_vector(text: str) -> list:
    """Send text to CLIP HF Space, return 512-dim embedding. Truncated to 300 chars (CLIP ~77 token limit)."""
    response = requests.post(
        f"{SPACE_URL}/text-embedding",
        json={"text": text[:300]},
        timeout=60
    )
    return response.json()["embedding"]
