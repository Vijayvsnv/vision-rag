# image_store.py

import uuid
import httpx
import cloudinary
import cloudinary.uploader
from pathlib import Path
from fastapi import UploadFile
from dotenv import load_dotenv
import os

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

TEMP_DIR = Path("./image_store")
TEMP_DIR.mkdir(exist_ok=True)


async def save_from_url(url: str) -> tuple[str, str]:
    """Download image from URL, upload to Cloudinary, return (local_path, cloudinary_url)."""
    async with httpx.AsyncClient(timeout=30) as http:
        response = await http.get(url)
        if response.status_code != 200:
            raise Exception(f"Image download failed: {response.status_code}")

        content_type = response.headers.get("content-type", "image/jpeg")
        ext = content_type.split("/")[-1].split(";")[0].strip()
        if ext not in ("jpeg", "jpg", "png", "webp"):
            ext = "jpg"

        temp_filename = f"{uuid.uuid4()}.{ext}"
        temp_path = TEMP_DIR / temp_filename
        temp_path.write_bytes(response.content)

    result = cloudinary.uploader.upload(str(temp_path), folder="vision-rag")
    cloudinary_url = result["secure_url"]

    return str(temp_path), cloudinary_url


async def save_from_upload(file: UploadFile) -> tuple[str, str]:
    """Save uploaded file locally, upload to Cloudinary, return (local_path, cloudinary_url)."""
    ext = file.filename.split(".")[-1].lower()
    if ext not in ("jpeg", "jpg", "png", "webp"):
        ext = "jpg"

    temp_filename = f"{uuid.uuid4()}.{ext}"
    temp_path = TEMP_DIR / temp_filename
    temp_path.write_bytes(await file.read())

    result = cloudinary.uploader.upload(str(temp_path), folder="vision-rag")
    cloudinary_url = result["secure_url"]

    return str(temp_path), cloudinary_url
