# main.py

import uuid
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

from clip_model import get_image_vector, get_text_vector
from vlm import get_image_description
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

# ─────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────

@app.post("/ingest")
async def ingest(
    image_url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    if not image_url and not file:
        raise HTTPException(400, "image_url ya file dono mein se ek do")

    if image_url and image_url.strip():
        image_path, cloudinary_url = await save_from_url(image_url)
    else:
        image_path, cloudinary_url = await save_from_upload(file)

    result = get_image_description(image_path)
    description = result["description"]
    tags = result["tags"]

    image_vector = get_image_vector(image_path)
    text_vector = get_text_vector(description)

    image_id = str(uuid.uuid4())
    save_image_record(
        image_id=image_id,
        image_path=image_path,
        filename=cloudinary_url,
        description=description,
        tags=tags,
        image_vector=image_vector,
        text_vector=text_vector
    )

    return {
        "success": True,
        "image_id": image_id,
        "image_url": cloudinary_url,
        "description": description,
        "tags": tags
    }


@app.post("/chat")
async def chat(request: ChatRequest):
    # Step 1: search query banao — "show this" jaise contextual queries ke liye history se topic lo
    search_query = request.message
    msg_lower = request.message.lower()
    vague_words = ["this", "it", "that", "show this", "show it", "can you show", "show me this"]
    is_vague = any(w in msg_lower for w in vague_words) and len(request.message.split()) <= 6
    if is_vague and request.history:
        # last assistant message se topic extract karo
        for msg in reversed(request.history):
            if msg["role"] == "assistant":
                search_query = msg["content"][:200]
                break

    # Step 2: vector search — relevant images dhundo
    query_vector = get_text_vector(search_query)
    matched_images = search_images(query_vector, top_k=3)

    # Step 3: saari images ka context GPT ke liye
    all_images = get_all_images()
    context = ""
    for meta in all_images:
        context += f"- Description: {meta['description']}\n"
        context += f"  Tags: {meta['tags']}\n\n"

    # Step 4: GPT-4o se answer lo
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

    # Step 5: show_images decide karo
    show_keywords = ["show", "give", "display", "dikhao", "pic", "picture", "image", "photo", "dekha", "de do"]
    hide_keywords = ["have you", "do you", "koi hai", "any image", "hai kya", "you seen", "seen anywhere", "anywhere"]
    show_images = any(w in msg_lower for w in show_keywords) and not any(w in msg_lower for w in hide_keywords)

    return {
        "answer": response.choices[0].message.content,
        "matched_images": matched_images if show_images else []
    }


@app.get("/images-list")
async def images_list():
    images = get_all_images()
    return {"images": images, "total": len(images)}
