# VisionRAG — Codebase Guide

## What This Project Does

VisionRAG is a visual search and chat system. Users upload images with optional free-text notes; GPT-4o auto-generates a rich description. Images are embedded with OpenAI `text-embedding-3-large` (3072-dim) and stored in Pinecone. A chat interface lets users query the knowledge base in natural language — GPT-4o looks at the actual matched images in real time and answers with vision.

---

## Branches & Deployment

| Branch | Purpose | Render |
|---|---|---|
| `main` | Stable reference — not actively deployed | — |
| `dev` | Active development — **both Render services deploy from this** | Live |

- Backend URL: `https://vision-rag-backend-t58m.onrender.com`
- GitHub repo: `codenscious-tech/vision-rag`
- Auto-deploys on push to `dev` branch

---

## Architecture

```
vision-rag/
├── backend/                          # FastAPI, Python 3.11 (conda: gmaps-scraper)
│   ├── main.py                       # Routes: /ingest, /ingest/batch, /chat, /images-list
│   ├── description_and_embedding.py  # GPT-4o vision description + text-embedding-3-large
│   ├── vector_store.py               # Pinecone — index: vision-rag-text-index, 3072-dim
│   ├── image_store.py                # Cloudinary upload + local temp (backend/image_store/)
│   ├── requirements.txt
│   └── runtime.txt                   # python-3.11.9 (for Render)
├── frontend/                         # React 18 + Vite 5
│   ├── src/
│   │   ├── App.jsx                   # Full UI — chat + upload modal (all inline CSS)
│   │   ├── index.css                 # CSS variables, animations, scrollbar
│   │   └── main.jsx                  # React entry point
│   ├── index.html                    # Outfit + Space Mono fonts (Google Fonts)
│   └── vite.config.js                # Dev server port 3000
├── render.yaml                       # Render deploy config
├── CLAUDE.md                         # This file
└── README.md
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI 0.111, Uvicorn, Python 3.11.15 |
| Vector DB | Pinecone Serverless (AWS us-east-1, cosine, **3072-dim**) |
| Description | GPT-4o vision — auto-generated on ingest, user never types it |
| Embeddings | `text-embedding-3-large` (OpenAI, 3072-dim) |
| Chat / QA | GPT-4o with real-time vision (Cloudinary URLs passed directly) |
| Image Storage | Cloudinary (`folder="vision-rag"`, `quality="auto:best"`) + local temp |
| Frontend | React 18, Vite 5, all styling inline CSS |
| Deployment | Render — backend + frontend, both from `dev` branch |

---

## Environment Variables

`backend/.env` (never commit — git-ignored):

```
OPENAI_API_KEY=...
PINECONE_API_KEY=...
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
```

---

## Local Development

### Backend

```bash
conda activate gmaps-scraper        # Python 3.11.15

cd backend
pip install -r requirements.txt
uvicorn main:app --port 8000 --reload
```

Backend runs at: `http://127.0.0.1:8000`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at: `http://localhost:3000`

### Switch API URL (local vs production)

`frontend/src/App.jsx` line 3:
```js
// const API = 'http://127.0.0.1:8000'                          // local
const API = 'https://vision-rag-backend-t58m.onrender.com'      // prod (currently active)
```

---

## API Endpoints

### `POST /ingest`

Accepts `multipart/form-data`. Requires one of `file` or `image_url`.

| Field | Type | Notes |
|---|---|---|
| `file` | binary | one of file or image_url |
| `image_url` | string | one of file or image_url |
| `notes` | string | free-text metadata — anything (location, time, event, people, etc.) |

**Flow:**
1. Image saved locally → uploaded to Cloudinary (`quality="auto:best"`, `fetch_format="auto"`)
2. GPT-4o vision → auto-generates rich description (max 1000 tokens)
3. `text-embedding-3-large` → 3072-dim vector from description
4. Upserted to Pinecone with metadata: `image_id, image_url, description, notes, created_at`

**Returns:** `{ success, image_id, image_url, description, notes }`

---

### `POST /ingest/batch`

JSON body. For bulk ingest via API (not used from UI).

```json
{ "images": [{ "image_url": "...", "location": "...", "capture_time": "...", "day": "...", "camera_device": "...", "latitude": 0.0, "longitude": 0.0 }] }
```

> **Known bug:** `save_image_record()` only accepts `notes=` but batch route passes `location=, capture_time=, day=, camera_device=, latitude=, longitude=` — will crash at runtime. Needs fix before batch ingest is used.

---

### `POST /chat`

```json
{
  "message": "show me photos from the office",
  "history": [{ "role": "user", "content": "..." }, { "role": "assistant", "content": "..." }],
  "excluded_ids": ["uuid1", "uuid2"],
  "active_image": { "image_id": "...", "image_url": "...", "description": "...", "notes": "...", "score": 0.82 }
}
```

**Flow:**
1. Embed user message → 3072-dim vector
2. If `active_image` provided → use it directly, skip Pinecone search
3. Else → Pinecone search (threshold=0.35, top_k=3), filter `excluded_ids`
4. Send top 1 matched image URL + conversation history to GPT-4o (real-time vision)
5. Returns `{ answer, matched_images }`

---

### `GET /images-list`

Returns all images via dummy-vector query. `{ images: [...], total: N }`

---

## Key Design Details

### Pinecone Index
- Name: `vision-rag-text-index`
- Dimension: 3072, metric: cosine, cloud: AWS us-east-1
- Only text embeddings stored (from GPT-4o description). No raw image vectors.

### `get_all_images()` Trick
Uses a uniform dummy vector `[1/√3072] * 3072` to fetch all records via `query(top_k=1000)` — Pinecone's way of doing a full-table scan.

### GPT-4o Real-Time Vision in Chat
Matched Cloudinary URLs are passed as `image_url` type in the OpenAI messages content array. GPT-4o fetches and sees the actual images — not just descriptions. Only top 1 image is sent to avoid confusion.

### Auto Description (Ingest)
`get_description()` sends the image to GPT-4o with a comprehensive system prompt covering: scene, people (count/gender/age/clothing/actions), objects, visible text, colors, background/foreground, lighting, camera type. Returns a single flowing paragraph. max_tokens=1000.

### Multi-Turn RAG (Frontend)
Three keyword sets control conversation state:

| Set | Keywords | Action |
|---|---|---|
| `REJECTION_KEYWORDS` | "not this", "wrong", "different", "another", "next", ... | Exclude current image, search again |
| `NEW_SEARCH_KEYWORDS` | "find another", "exit", "new image", "search for", "look for", ... | Reset everything — clear activeImage + excludedIds |
| `SHOW_KEYWORDS` | "show", "display", "show me", "let me see", ... | Re-display the locked image card |

- `activeImage` — locked after first result; follow-up questions use it directly (no re-search)
- `excludedIds` — accumulates already-shown image IDs to avoid repeats
- Rejection detected → `activeImage` cleared; new topic → both cleared

---

## Frontend Details

Single-file React app (`App.jsx`). All styling is inline CSS.

**Design system** (CSS variables in `index.css`):
- Background: `#f6f7fb` (`--bg`)
- Accent: `#6366f1` (indigo, `--accent`)
- Font body: `Outfit`, Font mono: `Space Mono`

**Upload Modal fields:**
- Tab: File upload or Image URL
- Notes textarea — free text, anything the user wants to add
- Description banner — "auto-generated by AI" (user never types description)

**ImageCard shows:**
- Image thumbnail (120px height, object-fit cover)
- `notes` if present
- Cosine similarity score (3 decimal places, monospace)

**Chat UI:**
- Typing dots animation while waiting
- Image cards appear only on fresh search or when SHOW_KEYWORDS detected
- Suggestions shown on empty state: "Show me all images", "Find a portrait photo", "What images do you have?"

---

## Deployment (Render)

Both services on Render, auto-deploy from `dev` branch:

**Backend:**
- Runtime: Python 3.11.9
- Build: `pip install -r requirements.txt`
- Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`

**Frontend:**
- Build: `npm install && npm run build`
- Publish: `dist/`

Set all env vars in Render dashboard (not in `render.yaml`).

---

## Requirements (`backend/requirements.txt`)

```
fastapi==0.111.0
uvicorn>=0.29.0
python-multipart==0.0.9
httpx==0.27.0
openai>=1.32.0,<2.0.0
pinecone
Pillow==10.3.0
pydantic==2.7.1
python-dotenv==1.0.1
cloudinary
```

---

## Common Tasks

**Add new metadata field:**
1. Add to `save_image_record()` signature in `vector_store.py` (and to `metadata` dict)
2. Add `Form(None)` param in `/ingest` in `main.py`, pass to `save_image_record()`
3. Add input field in `UploadModal` in `App.jsx`, include in `fd.append()`

**Change similarity threshold:**
Edit `threshold` param in `search_images()` call in `main.py` (currently `0.35`).

**Switch to local backend:**
Comment/uncomment `const API` on line 3 of `App.jsx`.

**Pinecone index reset:**
Delete `vision-rag-text-index` in Pinecone dashboard — code auto-recreates it at 3072-dim on next startup.

**Fix batch ingest bug:**
Update `save_image_record()` in `vector_store.py` to accept and store `location, capture_time, day, camera_device, latitude, longitude`, then add those fields to the Pinecone metadata dict.
