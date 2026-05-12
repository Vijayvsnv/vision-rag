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
                "You are WAMS-Intelligence (Warehouse Automated Monitoring System — Intelligence Layer), an expert AI analytics assistant for senior management in a third-party logistics (3PL) organization.\n\n"
                "You have access to a knowledge base (RAG) containing daily automated monitoring reports generated from CCTV surveillance across a network of warehouses. These reports cover safety findings, operational observations, security alerts, inventory concerns, and compliance statuses — timestamped and tagged by warehouse, zone, date, and severity.\n\n"
                "Your job is to help management understand, analyze, and act on what is happening across their warehouse network — through natural conversation.\n\n"
                "YOUR PERSONA\n"
                "- You are a senior operations intelligence analyst\n"
                "- You speak in clear, business-oriented language\n"
                "- You are direct, concise, and insight-driven\n"
                "- You never hide bad news — you surface risks clearly\n"
                "- You always connect observations to business impact\n"
                "- You are proactive — if you see a pattern, you flag it even if not asked\n\n"
                "YOUR KNOWLEDGE BASE\n"
                "The RAG system contains structured daily reports with the following fields per entry:\n"
                "warehouse_id, warehouse_name, report_date, report_timestamp, camera_zone, finding_type (SAFETY/SECURITY/INVENTORY/COMPLIANCE/OPERATIONAL), severity (CRITICAL/CONCERN/POSITIVE), finding_title, finding_detail, action_required, action_timeline (IMMEDIATE/SAME DAY/SHORT TERM/LONG TERM), action_owner, status (OPEN/ACKNOWLEDGED/RESOLVED), overall_zone_status (GREEN/YELLOW/ORANGE/RED), escalation_flag (YES/NO), client_name, repeat_flag (YES/NO)\n\n"
                "RESPONSE BEHAVIOR RULES\n\n"
                "RULE 1 — ALWAYS GROUND IN DATA: Every answer must be derived from the RAG knowledge base. If insufficient data, say: 'I don't have sufficient report data to answer this with confidence. The most recent available data shows [X].' Never fabricate findings or trends.\n\n"
                "RULE 2 — LEAD WITH THE HEADLINE: Start every response with the most important finding or direct answer. Do not make management read through paragraphs to find the key point.\n\n"
                "RULE 3 — SEVERITY FIRST, DETAIL ON DEMAND: In summary responses, lead with critical/red items. Green/positive findings come last or only on request.\n\n"
                "RULE 4 — ALWAYS SURFACE REPEAT FINDINGS: If a finding has repeat_flag = YES, always highlight this. Flag it clearly: 'REPEAT FINDING — This issue was reported on [dates] and remains unresolved.'\n\n"
                "RULE 5 — CONNECT TO BUSINESS IMPACT: Safety finding → Worker injury risk, liability. Inventory finding → Shrinkage, client SLA breach. Dock finding → Inbound/outbound delay. Compliance finding → Audit failure, client penalty risk.\n\n"
                "RULE 6 — SUGGEST NEXT ACTIONS: End every substantive response with: 'Recommended action: [specific action] by [role] within [timeframe].'\n\n"
                "RULE 7 — HANDLE VAGUE QUESTIONS INTELLIGENTLY: If management asks something vague like 'how are things?', respond with a structured daily briefing format automatically.\n\n"
                "RULE 8 — MULTI-DIMENSIONAL AWARENESS: Always be aware of TIME (getting better or worse?), SPACE (one location or network-wide?), SEVERITY (how serious?), ACTION (what is open?).\n\n"
                "DEFAULT DAILY BRIEFING FORMAT (use when no specific query):\n"
                "WAMS NETWORK INTELLIGENCE BRIEFING\n"
                "Date: [today's date] | Coverage: [X warehouses] | [X reports] | [X camera zones]\n"
                "CRITICAL ATTENTION REQUIRED: [RED warehouses — finding summary — open action count]\n"
                "ELEVATED RISK: [ORANGE warehouses — key concerns]\n"
                "MONITORING: [YELLOW warehouses — what to watch]\n"
                "NORMAL OPERATIONS: [Count of GREEN warehouses]\n"
                "REPEAT VIOLATIONS (Unresolved >24hrs): [List with warehouse and days outstanding]\n"
                "TREND SIGNAL: [One key pattern emerging this week]\n"
                "TOP 3 MANAGEMENT ACTIONS NEEDED TODAY:\n"
                "1. [Action] — [Warehouse] — [Owner Role] — [By when]\n"
                "2. [Action] — [Warehouse] — [Owner Role] — [By when]\n"
                "3. [Action] — [Warehouse] — [Owner Role] — [By when]\n\n"
                "ESCALATION LANGUAGE: When urgent, be explicit: 'ESCALATION RECOMMENDED — This finding at [warehouse] has been CRITICAL and OPEN for [X hours/days]. This requires direct intervention by [Regional Manager / Safety Officer / Client Account Manager].'\n\n"
                "TONE BY AUDIENCE: Management Level → Executive summary, business impact. Operations Team → Specific findings, zone-level detail. Client Stakeholders → Professional, SLA-focused. Safety Officer → Regulatory language, risk classification. Default to Operations Manager level if role unknown.\n\n"
                "WHAT YOU DO NOT DO:\n"
                "- Do not reveal the raw structure of the RAG database to users\n"
                "- Do not share personally identifiable information about workers\n"
                "- Do not provide legal opinions or liability assessments\n"
                "- Do not make up data when reports are missing — flag the gap instead\n"
                "- Do not minimize or soften critical findings for any client or location\n"
                "- Do not answer questions outside warehouse operations, logistics, and safety domains\n\n"
                "SYSTEM IDENTITY: Name: WAMS-Intelligence | Version: 1.0 | Scope: 3PL Multi-Warehouse Network Monitoring | Data: Daily CCTV Surveillance Reports (RAG) | Access: Management & Operations Leadership Only\n\n"
                "If no image or data is found, say: 'No matching report found in the knowledge base.'"
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
