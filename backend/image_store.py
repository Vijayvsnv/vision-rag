# image_store.py

import uuid
import httpx
from pathlib import Path
from fastapi import UploadFile

IMAGE_DIR = Path("./image_store")
IMAGE_DIR.mkdir(exist_ok=True)

async def save_from_url(url: str) -> tuple[str, str]:
    """URL se image download karke save karo"""
    async with httpx.AsyncClient(timeout=30) as http:
        response = await http.get(url)
        if response.status_code != 200:
            raise Exception(f"Image download failed: {response.status_code}")
        
        # extension nikalo content-type se
        content_type = response.headers.get("content-type", "image/jpeg")
        ext = content_type.split("/")[-1].split(";")[0].strip()
        if ext not in ("jpeg", "jpg", "png", "webp"):
            ext = "jpg"
        
        filename = f"{uuid.uuid4()}.{ext}"
        path = IMAGE_DIR / filename
        path.write_bytes(response.content)
    
    return str(path), filename

async def save_from_upload(file: UploadFile) -> tuple[str, str]:
    """Direct uploaded file save karo"""
    ext = file.filename.split(".")[-1].lower()
    if ext not in ("jpeg", "jpg", "png", "webp"):
        ext = "jpg"
    
    filename = f"{uuid.uuid4()}.{ext}"
    path = IMAGE_DIR / filename
    path.write_bytes(await file.read())
    
    return str(path), filename