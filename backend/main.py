# main.py

import uuid
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

from clip_model import get_image_vector, get_text_vector
from image_store import save_from_url, save_from_upload
from vector_store import save_image_record, search_images, get_all_images

from openai import OpenAI
from dotenv import load_dotenv
import os

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

class IngestItem(BaseModel):
    image_url: str
    description: str
    tags: Optional[str] = None

class BatchIngestRequest(BaseModel):
    images: List[IngestItem]

# ─────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────

@app.post("/ingest")
async def ingest(
    image_url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    description: str = Form(...),
    tags: Optional[str] = Form(None)
):
    if not image_url and not file:
        raise HTTPException(400, "Provide either image_url or a file")

    if not description.strip():
        raise HTTPException(400, "description is required")

    if image_url and image_url.strip():
        image_path, cloudinary_url = await save_from_url(image_url)
    else:
        image_path, cloudinary_url = await save_from_upload(file)

    tags_list = [t.strip() for t in tags.split(",")] if tags and tags.strip() else []

    image_vector = get_image_vector(image_path)
    text_vector = get_text_vector(description)

    image_id = str(uuid.uuid4())
    save_image_record(
        image_id=image_id,
        image_path=image_path,
        filename=cloudinary_url,
        description=description,
        tags=tags_list,
        image_vector=image_vector,
        text_vector=text_vector
    )

    return {
        "success": True,
        "image_id": image_id,
        "image_url": cloudinary_url,
        "description": description,
        "tags": tags_list
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
            tags_list = [t.strip() for t in item.tags.split(",")] if item.tags and item.tags.strip() else []
            image_vector = get_image_vector(image_path)
            text_vector = get_text_vector(item.description)
            image_id = str(uuid.uuid4())
            save_image_record(
                image_id=image_id,
                image_path=image_path,
                filename=cloudinary_url,
                description=item.description,
                tags=tags_list,
                image_vector=image_vector,
                text_vector=text_vector
            )
            results.append({
                "success": True,
                "image_id": image_id,
                "image_url": cloudinary_url,
                "description": item.description,
                "tags": tags_list
            })
        except Exception as e:
            errors.append({
                "image_url": item.image_url,
                "error": str(e)
            })

    return {
        "total": len(request.images),
        "success_count": len(results),
        "error_count": len(errors),
        "results": results,
        "errors": errors
    }


@app.post("/chat")
async def chat(request: ChatRequest):
    # Step 1: build search query — for vague queries like "show this", use topic from history
    search_query = request.message
    msg_lower = request.message.lower()
    vague_words = ["this", "it", "that", "show this", "show it", "can you show", "show me this"]
    is_vague = any(w in msg_lower for w in vague_words) and len(request.message.split()) <= 6
    if is_vague and request.history:
        # extract topic from last assistant message
        for msg in reversed(request.history):
            if msg["role"] == "assistant":
                search_query = msg["content"][:200]
                break

    # Step 2: vector search — find relevant images
    query_vector = get_text_vector(search_query)
    matched_images = search_images(query_vector, top_k=3)

    # Step 3: build context from all images for GPT
    all_images = get_all_images()
    context = ""
    for meta in all_images:
        context += f"- Description: {meta['description']}\n"
        context += f"  Tags: {meta['tags']}\n\n"

    # Step 4: get answer from GPT-4o-mini
    messages = [
        {
            "role": "system",
            "content": f"""You are an image search assistant. Answer ONLY based on the images listed below.

Available images in the database:
{context}

Rules:
- Read ALL descriptions carefully and answer truthfully
- If any description matches the user query — say YES it exists and describe it
- Do NOT include any URLs in your answer
- Keep answers under 3 lines
- NEVER say you cannot show images — the system handles image display automatically
- NEVER say an image doesn't exist if its description matches the query"""
        }
    ]

    for msg in request.history:
        messages.append(msg)

    messages.append({"role": "user", "content": request.message})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=150
    )

    # Step 5: decide whether to show images based on keywords
    show_keywords = ["show", "give", "display", "pic", "picture", "image", "photo"]
    hide_keywords = ["have you", "do you", "any image", "you seen", "seen anywhere", "anywhere"]
    show_images = any(w in msg_lower for w in show_keywords) and not any(w in msg_lower for w in hide_keywords)

    return {
        "answer": response.choices[0].message.content,
        "matched_images": matched_images if show_images else []
    }


@app.get("/images-list")
async def images_list():
    images = get_all_images()
    return {"images": images, "total": len(images)}
