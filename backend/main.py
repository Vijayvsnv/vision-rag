# main.py

import uuid
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List

from clip_model import get_image_vector, get_text_vector



from vlm import get_image_description
from image_store import save_from_url, save_from_upload
from vector_store import save_image_record, search_images

from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI(title="Vision RAG")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://vision-rag-frontend.onrender.com"],#["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# image_store folder ko static files ki tarah serve karo
app.mount("/images", StaticFiles(directory="image_store"), name="images")

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
    """Image ingest karo — URL ya direct file dono se"""
    
    if not image_url and not file:
        raise HTTPException(400, "image_url ya file dono mein se ek do")
    
    # Step 1: image save karo
    if image_url and image_url.strip():

        image_path, filename = await save_from_url(image_url)
    else:
        image_path, filename = await save_from_upload(file)
    
    # Step 2: GPT-4o Vision se description lo
    result = get_image_description(image_path)
    description = result["description"]
    tags = result["tags"]
    
    # Step 3: CLIP se vectors banao
    image_vector = get_image_vector(image_path)
    text_vector = get_text_vector(description)
    
    # Step 4: ChromaDB mein save karo
    image_id = str(uuid.uuid4())
    save_image_record(
        image_id=image_id,
        image_path=image_path,
        filename=filename,
        description=description,
        tags=tags,
        image_vector=image_vector,
        text_vector=text_vector
    )
    
    return {
        "success": True,
        "image_id": image_id,
        "image_url": f"/images/{filename}",
        "description": description,
        "tags": tags
    }


# @app.post("/chat")
# async def chat(request: ChatRequest):
#     """User ka sawaal lo, similar images dhundo, GPT-4o se answer do"""
    
#     # Step 1: query ka vector banao
#     query_vector = get_text_vector(request.message)
    
#     # Step 2: ChromaDB mein search karo
#     matched_images = search_images(query_vector, top_k=3,query_text=request.message)
    
#     # Step 3: context banao GPT ke liye
#     context = ""
#     for img in matched_images:
#         context += f"- Image URL: {img['image_url']}\n"
#         context += f"  Description: {img['description']}\n"
#         context += f"  Tags: {img['tags']}\n\n"
    
#     # Step 4: GPT-4o se answer lo
#     messages = [
#         {
#             "role": "system",
#             "content": f"""You are an image search assistant. Answer ONLY based on the images listed below.

# Available images in the database:
# {context}

# Rules:
# - Read the descriptions carefully and answer truthfully based on what is IN the descriptions
# - If a description mentions "American flag", "flag", "people", "group" etc — say YES it exists
# - Only show images if user uses words like "show", "image dikhao", "pic", "display", "give image"
# - Otherwise answer in text only
# - Keep answers under 3 lines
# - NEVER say an image doesn't exist if its description matches the query"""
#         }
#     ]
    
#     # history add karo
#     for msg in request.history:
#         messages.append(msg)
    
#     messages.append({"role": "user", "content": request.message})
    
#     response = client.chat.completions.create(
#         model="gpt-4o-mini",
#         messages=messages,
#         max_tokens=100
#     )
#     image_keywords = ["image", "photo", "show", "which", "give", "display", "pic"]
#     show_images = any(word in request.message.lower() for word in image_keywords)
    
#     return {
#         "answer": response.choices[0].message.content,
#         "matched_images": matched_images if show_images else []
#     }


# @app.get("/images-list")
# async def images_list():
#     """Saari ingested images ki list"""
#     from vector_store import collection
#     results = collection.get()
    
#     seen = set()
#     images = []
#     for metadata in results["metadatas"]:
#         if metadata["image_id"] not in seen:
#             seen.add(metadata["image_id"])
#             images.append(metadata)
    
#     return {"images": images, "total": len(images)}
@app.post("/chat")
async def chat(request: ChatRequest):
    """User ka sawaal lo, similar images dhundo, GPT-4o se answer do"""
    
    # Step 1: saari images lo DB se — GPT khud decide karega kaunsi relevant hai
    from vector_store import collection as db_collection
    all_data = db_collection.get()
    seen = set()
    all_images = []
    for metadata in all_data["metadatas"]:
        if metadata["image_id"] not in seen:
            seen.add(metadata["image_id"])
            all_images.append({
                "image_id": metadata["image_id"],
                "image_url": metadata["image_url"],
                "description": metadata["description"],
                "tags": metadata["tags"],
                "score": 1.0
            })

    # Step 2: context banao GPT ke liye — saari images
    context = ""
    for img in all_images:
        context += f"- Image URL: {img['image_url']}\n"
        context += f"  Description: {img['description']}\n"
        context += f"  Tags: {img['tags']}\n\n"

    # Step 3: GPT-4o se answer lo
    messages = [
        {
            "role": "system",
            "content": f"""You are an image search assistant. Answer ONLY based on the images listed below.

Available images in the database:
{context}

Rules:
- Read ALL descriptions carefully and answer truthfully
- If any description matches the user query — say YES it exists and describe it
- Only return image_urls if user uses words like "show", "give", "display", "dikhao", "pic"
- Otherwise answer in text only
- Keep answers under 3 lines
- NEVER say an image doesn't exist if its description matches the query
- When showing images, return ONLY the relevant image URLs in your answer, not all images"""
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

    # Step 4: show_images decide karo
    show_keywords = ["show", "give", "display", "dikhao", "pic", "show me", "de do", "picture do", "image do"]
    hide_keywords = ["have you", "do you", "koi hai", "any image", "hai kya", "you see", "anywhere"]
    msg_lower = request.message.lower()
    show_images = any(w in msg_lower for w in show_keywords) and not any(w in msg_lower for w in hide_keywords)

    # Step 5: agar show karna hai toh GPT ke answer se relevant images filter karo
    matched_images = []
    if show_images:
        for img in all_images:
            if img["image_url"] in response.choices[0].message.content or \
               any(tag.strip().lower() in request.message.lower() for tag in img["tags"].split(",")):
                matched_images.append(img)
        if not matched_images:
            matched_images = all_images[:2]   
            



    return {
        "answer": response.choices[0].message.content,
        "matched_images": matched_images
    }


@app.get("/images-list")
async def images_list():
    """Saari ingested images ki list"""
    from vector_store import collection
    results = collection.get()

    seen = set()
    images = []
    for metadata in results["metadatas"]:
        if metadata["image_id"] not in seen:
            seen.add(metadata["image_id"])
            images.append(metadata)

    return {"images": images, "total": len(images)}
