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


FILLER_WORDS = {
    "show", "give", "display", "me", "the", "a", "an", "this", "that",
    "it", "image", "photo", "picture", "pic", "find", "get", "can",
    "you", "please", "if", "exist", "exists", "same", "also", "is",
    "are", "was", "were", "be", "been", "have", "has", "had", "do",
    "does", "did", "will", "would", "could", "should", "yes", "no",
    "there", "here", "all", "any", "some", "i", "my", "your", "and",
    "or", "but", "of", "in", "on", "at", "to", "for", "with", "carefully",
    "okay", "ok", "what", "where", "when", "who", "which", "how",
    "describe", "tell", "explain", "see", "look", "hey", "hi", "hello",
    "name", "related", "about", "regarding", "any", "person",
    "object", "like", "description", "thing", "things", "stuff", "content",
    "many", "peoples", "much", "several", "few", "number", "count",
    # Hindi/Hinglish filler
    "de", "dedo", "dikhao", "dikha", "kya", "hai", "nahi", "haan",
    "iska", "uski", "unka", "yahi", "wahi", "woh", "vo", "toh", "bhi",
    "karo", "kar", "koi", "naam", "ka", "wala", "batao", "bata"
}

# Words that indicate user wants to SEE something from prior context
SHOW_WORDS = {"show", "give", "display", "de", "dedo", "dikhao", "dikha"}
REFERENCE_WORDS = {"this", "same", "it", "iska", "uski", "unka", "yahi", "wahi", "woh", "vo"}

def extract_query_terms(message: str) -> str:
    words = message.lower().split()
    return " ".join(w.strip(".,?!") for w in words if w.strip(".,?!") not in FILLER_WORDS)

def is_show_from_context(message: str) -> bool:
    words = {w.strip(".,?!'\"") for w in message.lower().split()}
    has_show = bool(words & SHOW_WORDS)
    has_reference = bool(words & REFERENCE_WORDS)
    extracted = extract_query_terms(message)
    # treat as context-based if: (show + reference) OR (show intent + no new meaningful terms)
    return has_show and (has_reference or not extracted)

def get_topic_from_history(history: list) -> str:
    recent = history[-6:] if len(history) > 6 else history
    # prefer user messages with 2+ meaningful words (single generic words like "object" are skipped)
    for msg in reversed(recent):
        if msg["role"] == "user":
            terms = extract_query_terms(msg["content"])
            if terms and len(terms.split()) >= 2:
                return terms
    # fallback: accept even 1-word terms
    for msg in reversed(recent):
        if msg["role"] == "user":
            terms = extract_query_terms(msg["content"])
            if terms:
                return terms
    # last resort: assistant first sentence
    for msg in reversed(recent):
        if msg["role"] == "assistant":
            terms = extract_query_terms(msg["content"].split(".")[0])
            if terms:
                return terms
    return ""


@app.post("/chat")
async def chat(request: ChatRequest):
    msg_lower = request.message.lower()

    # Step 1: vector search on user's message — CLIP handles semantic matching
    query_vector = get_text_vector(request.message)
    relevant_images = search_images(query_vector, top_k=5, threshold=0.60)

    # Step 2: get all images + build GPT context
    all_images = get_all_images()

    # highlight top relevant images so GPT doesn't have to scan all descriptions
    relevant_context = ""
    if relevant_images:
        relevant_context = "Most relevant images found by search:\n"
        for img in relevant_images:
            relevant_context += f"- {img['description']} | Tags: {img['tags']}\n"
        relevant_context += "\n"

    full_context = "All images in database:\n"
    for meta in all_images:
        full_context += f"- {meta['description']} | Tags: {meta['tags']}\n"

    # Step 3: GPT answers using both relevant + full context
    is_show_request = bool({w.strip(".,?!'\"") for w in msg_lower.split()} & SHOW_WORDS)

    messages = [
        {
            "role": "system",
            "content": f"""You are an image search assistant. Always respond in English only.

{relevant_context}
{full_context}

Rules:
- Existence question → answer YES or NO + one brief phrase only
- Describe request → describe the image in detail
- Show/display request → reply with 1 short confirmation line, then on a NEW LINE write exactly: [SEARCH: <2-3 word description of the image to find>]
- Use semantic understanding — "country flag" matches "American flag", "person" matches "man/woman" etc.
- ALWAYS respond in English
- Do NOT include any URLs
- NEVER say an image doesn't exist if the relevant images above match the query
- NEVER say you cannot show images"""
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

    raw_answer = response.choices[0].message.content

    # Step 4: parse GPT's search term for show requests
    search_query = None
    answer = raw_answer
    if "[SEARCH:" in raw_answer:
        parts = raw_answer.split("[SEARCH:")
        answer = parts[0].strip()
        search_query = parts[1].split("]")[0].strip()

    # Step 5: vector search using GPT's extracted term + keyword fallback
    matched_images = []
    if search_query:
        sq_vector = get_text_vector(search_query)
        matched_images = search_images(sq_vector, top_k=3, threshold=0.75)

        if not matched_images:
            sq_words = {w for w in search_query.lower().split() if len(w) > 3}
            for meta in all_images:
                combined = (meta.get("description", "") + " " + meta.get("tags", "")).lower()
                if sum(1 for w in sq_words if w in combined) >= 2:
                    matched_images.append({
                        "image_id": meta.get("image_id", ""),
                        "image_url": meta.get("image_url", ""),
                        "description": meta.get("description", ""),
                        "tags": meta.get("tags", ""),
                        "score": 0.0
                    })
                if len(matched_images) >= 3:
                    break

    return {
        "answer": answer,
        "matched_images": matched_images
    }


@app.get("/images-list")
async def images_list():
    images = get_all_images()
    return {"images": images, "total": len(images)}
