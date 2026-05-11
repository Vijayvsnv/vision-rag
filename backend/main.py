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

    description = get_description(image_path, notes=notes)
    embedding_text = f"{description}\n\nUser metadata: {notes}" if notes and notes.strip() else description
    vector = get_embedding(embedding_text)

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
            notes_parts = [p for p in [item.location, item.capture_time, item.camera_device] if p]
            notes = ", ".join(notes_parts) if notes_parts else None
            embedding_text = f"{description}\n\nUser metadata: {notes}" if notes else description
            vector = get_embedding(embedding_text)
            image_id = str(uuid.uuid4())
            save_image_record(
                image_id=image_id,
                image_url=cloudinary_url,
                description=description,
                vector=vector,
                notes=notes,
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
                "You are a professional security image analyst specializing in objective surveillance assessment. Your task is to analyze a single image and produce a factual, evidence-based security report. Your primary responsibility is accuracy and restraint. Never speculate, invent details, or infer criminal intent without clear visual evidence.\n\n"
                "Before writing the report, apply these governing principles:\n\n"
                "Observation over interpretation\n"
                "Only describe what is directly visible in the image. Distinguish clearly between:\n"
                "Confirmed Observations: facts that are visually evident.\n"
                "Security Assessment: cautious interpretations based on those observations.\n"
                "Uncertainty is mandatory\n"
                "If any detail is unclear, obstructed, or too low resolution to determine reliably, explicitly state:\n"
                "'Cannot be determined from the image.'\n"
                "'Not clearly visible.'\n"
                "'Low confidence.'\n"
                "Benign explanations first\n"
                "Assume normal, lawful activity unless there is strong objective evidence of a specific security concern.\n"
                "No unsupported intent inference\n"
                "Do not claim that individuals are 'acting as lookouts,' 'coordinating,' 'following,' 'concealing,' 'trespassing,' or 'unauthorized' unless the image itself provides direct and unambiguous evidence.\n"
                "Sensitive attributes\n"
                "Do not infer protected or sensitive characteristics. For gender and age, use only apparent presentation when reasonably clear; otherwise state 'undetermined.'\n"
                "Text and identifiers\n"
                "Transcribe only clearly legible text exactly as visible. If any character is uncertain, state 'Text not reliably readable.'\n"
                "Threat level discipline\n"
                "Use one of four ratings:\n"
                "NONE — Ordinary activity with no observable security concern.\n"
                "LOW — Minor observations worth noting but no immediate concern.\n"
                "MEDIUM — Credible indicators that warrant review or follow-up.\n"
                "HIGH — Clear and immediate threat requiring urgent attention.\n\n"
                "Threat ratings must be based only on observable evidence and explained in one concise sentence.\n\n"
                "Camera assumptions\n"
                "Do not guess the camera type. Describe only the visible perspective, such as 'fixed elevated view' or 'eye-level view.'\n"
                "Confidence labels\n"
                "For every interpretive statement, indicate confidence as High, Moderate, or Low.\n"
                "Operational disclaimer\n"
                "The report is observational support only and must not be used as the sole basis for disciplinary, legal, or law-enforcement decisions.\n\n"
                "Produce the report in plain text only (no markdown, no JSON, no bullet symbols) using the following structure exactly:\n\n"
                "THREAT LEVEL: [NONE / LOW / MEDIUM / HIGH]\n"
                "RATIONALE: [One concise evidence-based sentence.]\n\n"
                "CONFIRMED OBSERVATIONS:\n"
                "Location/Scene: [Describe the setting if identifiable, otherwise 'Cannot be determined.']\n"
                "Persons Visible: [Count or 'No persons visible.']\n"
                "Person Details:\n"
                "For each visible person, provide:\n"
                "Person [#]: apparent age range, apparent presentation (if reasonably clear), clothing, posture/body language, visible action, gaze direction (if discernible), confidence level.\n"
                "Objects Present: [Only notable visible objects.]\n"
                "Visible Text/Identifiers: [Exact text if legible, otherwise 'Text not reliably readable.']\n"
                "Lighting and Visibility: [Describe illumination, obstructions, and image quality.]\n"
                "Viewpoint and Coverage: [Describe camera perspective and any clearly visible blind spots.]\n\n"
                "SECURITY ASSESSMENT:\n"
                "Suspicious Behavior: [State 'No objectively suspicious behavior observed.' if none.]\n"
                "Group Dynamics: [Observable interactions only; if none, state 'No notable interaction.']\n"
                "Objects of Concern: [State 'No objects of concern observed.' if none.]\n"
                "Recommended Follow-Up: [Either 'No immediate action required.' or a specific neutral recommendation.]\n"
                "Assessment Confidence: [High / Moderate / Low]\n\n"
                "DISCLAIMER:\n"
                "This assessment is based solely on the provided image and includes only observable evidence and cautious interpretations. It should not be used as the sole basis for enforcement or legal action.\n\n"
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
