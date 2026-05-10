import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
import os

from description_and_embedding import get_description, get_embedding
from image_store import save_from_url, save_from_upload
from vector_store import save_image_record, search_images, get_all_images

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI(title="Vision RAG")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────
# SCHEMAS
# ─────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    history: List[dict] = []
    excluded_ids: List[str] = []
    active_image: Optional[dict] = None

class IngestItem(BaseModel):
    image_url: str
    location: Optional[str] = None
    capture_time: Optional[str] = None
    day: Optional[str] = None
    camera_device: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class BatchIngestRequest(BaseModel):
    images: List[IngestItem]

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

def _extract_day(capture_time: Optional[str]) -> Optional[str]:
    if not capture_time:
        return None
    try:
        dt = datetime.fromisoformat(capture_time)
        return dt.strftime("%A")
    except Exception:
        return None

# ─────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────

@app.post("/ingest")
async def ingest(
    image_url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    notes: Optional[str] = Form(None),
):
    if not image_url and not file:
        raise HTTPException(400, "Provide either image_url or a file")

    if image_url and image_url.strip():
        image_path, cloudinary_url = await save_from_url(image_url)
    else:
        image_path, cloudinary_url = await save_from_upload(file)

    description = get_description(image_path)
    vector = get_embedding(description)

    image_id = str(uuid.uuid4())
    save_image_record(
        image_id=image_id,
        image_url=cloudinary_url,
        description=description,
        vector=vector,
        notes=notes,
    )

    return {
        "success": True,
        "image_id": image_id,
        "image_url": cloudinary_url,
        "description": description,
        "notes": notes,
    }


@app.post("/ingest/batch")
async def ingest_batch(request: BatchIngestRequest):
    if not request.images:
        raise HTTPException(400, "images list is empty")

    results = []
    errors = []

    for item in request.images:
        try:
            image_path, cloudinary_url = await save_from_url(item.image_url)
            description = get_description(image_path)
            day = item.day or _extract_day(item.capture_time)
            vector = get_embedding(description)
            image_id = str(uuid.uuid4())
            save_image_record(
                image_id=image_id,
                image_url=cloudinary_url,
                description=description,
                vector=vector,
                location=item.location,
                capture_time=item.capture_time,
                day=day,
                camera_device=item.camera_device,
                latitude=item.latitude,
                longitude=item.longitude,
            )
            results.append({
                "success": True,
                "image_id": image_id,
                "image_url": cloudinary_url,
                "description": description,
            })
        except Exception as e:
            errors.append({"image_url": item.image_url, "error": str(e)})

    return {
        "total": len(request.images),
        "success_count": len(results),
        "error_count": len(errors),
        "results": results,
        "errors": errors,
    }


@app.post("/chat")
async def chat(request: ChatRequest):
    # 1. Embed the query
    query_vector = get_embedding(request.message)

    # 2. Search Pinecone for semantically relevant images
    # If active_image is locked, use it directly — skip Pinecone search
    if request.active_image:
        matched_images = [request.active_image]
        print(f"[CHAT] Using active_image: {request.active_image.get('image_id', '')[:20]}")
    else:
        matched_images = search_images(query_vector, top_k=3, threshold=0.35)
        if request.excluded_ids:
            matched_images = [img for img in matched_images if img["image_id"] not in request.excluded_ids]
        print(f"[CHAT] query='{request.message[:60]}' | matched={len(matched_images)} | excluded={len(request.excluded_ids)}")
        for img in matched_images:
            print(f"  score={img['score']} | desc={img['description'][:80]}")

    # 3. Build GPT-4o messages
    messages = [
        {
            "role": "system",
            "content": (
                "You are an intelligent image analysis assistant. "
                "You will be given real images from a database. "
                "Analyze every detail of the image carefully — objects, people, actions, colors, text, expressions, body language, background, foreground, shadows, reflections — everything. "
                "Answer any question the user asks about the image, no matter how small or specific. "
                "If the user asks about suspicious activity, weapons, unusual behavior, or anything concerning — analyze carefully and give a direct honest answer about what you see. "
                "If text is visible in the image, try to read it. "
                "Keep answers short, direct, and to the point. "
                "STRICT RULE: Never use general knowledge. Only answer based on what you actually see in the provided image. "
                "STRICT RULE: If you cannot count or see something clearly in the image, say exactly that — do NOT guess or use knowledge (e.g. do not say '50 stars' from memory, say 'I can see X stars clearly but cannot count all'). "
                "If no image is provided, say: 'No matching image found in database.'"
            )
        }
    ]

    for msg in request.history:
        messages.append(msg)

    # Send only the top 1 match to GPT-4o to avoid confusion
    top_image = matched_images[:1]

    # Current user turn: attach matched image as vision input
    content = []
    for img in top_image:
        if img["image_url"].startswith("http"):
            content.append({
                "type": "image_url",
                "image_url": {"url": img["image_url"]}
            })

    content.append({"type": "text", "text": request.message})
    messages.append({"role": "user", "content": content})

    # 4. Call GPT-4o with real-time vision
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=500
    )

    answer = response.choices[0].message.content

    return {
        "answer": answer,
        "matched_images": matched_images
    }


@app.get("/images-list")
async def images_list():
    images = get_all_images()
    return {"images": images, "total": len(images)}
