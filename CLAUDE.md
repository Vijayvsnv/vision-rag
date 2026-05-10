# VisionRAG — Codebase Guide

## What This Project Does

VisionRAG is a visual search and chat system. Users upload images with optional metadata (location, time, device); GPT-4o auto-generates the description. Images are embedded with OpenAI `text-embedding-3-large` and stored in Pinecone. A chat interface lets users query the knowledge base in natural language — GPT-4o looks at the actual matched images in real time and answers.

---

## Branches

| Branch | Purpose |
|---|---|
| `main` | Production — deployed on Render, stable |
| `dev` | Active development — 70% refactor, do all work here |

---

## Architecture

```
vision-rag/
├── backend/                        # FastAPI Python 3.11
│   ├── main.py                     # Routes: /ingest, /ingest/batch, /chat, /images-list
│   ├── description_and_embedding.py # GPT-4o vision description + text-embedding-3-large
│   ├── vector_store.py             # Pinecone — single index, 3072-dim
│   ├── image_store.py              # Cloudinary upload + local temp storage
│   ├── requirements.txt
│   └── runtime.txt                 # python-3.11.9 (for Render)
├── frontend/                       # React 18 + Vite
│   ├── src/
│   │   ├── App.jsx                 # Full UI — chat + upload modal
│   │   ├── index.css               # Light theme, indigo accent
│   │   └── main.jsx                # React entry point
│   ├── index.html                  # Outfit + Space Mono fonts
│   └── vite.config.js              # Dev server port 3000
├── render.yaml                     # Render deploy config (backend only)
├── CLAUDE.md                       # This file
└── README.md
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI 0.111, Uvicorn, Python 3.11 |
| Vector DB | Pinecone Serverless (AWS us-east-1, cosine, **3072-dim**) |
| Description | GPT-4o vision (auto-generated, user does not type it) |
| Embeddings | `text-embedding-3-large` (OpenAI, 3072-dim) |
| Chat / QA | GPT-4o with real-time vision (Cloudinary URLs passed directly) |
| Image Storage | Cloudinary (CDN) + `backend/image_store/` (local temp) |
| Frontend | React 18, Vite 5 |
| Deployment | Render (backend), frontend run separately |

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
# conda env activate karo (gmaps-scraper)
conda activate gmaps-scraper

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
const API = 'http://127.0.0.1:8000'                          // local
// const API = 'https://vision-rag-backend-t58m.onrender.com'  // prod
```

---

## API Endpoints

### `POST /ingest`
Accepts `multipart/form-data`. Requires one of `file` or `image_url`. All other fields are optional.

| Field | Type | Notes |
|---|---|---|
| `file` | binary | one of file or image_url |
| `image_url` | string | one of file or image_url |
| `location` | string | e.g. "Mumbai, India" |
| `capture_time` | string | ISO datetime, e.g. "2025-01-15T14:30" |
| `camera_device` | string | e.g. "iPhone 15 Pro" |
| `latitude` | float | |
| `longitude` | float | |

Flow:
1. Image saved locally + uploaded to Cloudinary
2. GPT-4o vision → auto-generates description
3. `day` extracted automatically from `capture_time` (e.g. "Monday")
4. `text-embedding-3-large` → 3072-dim vector from description
5. Upserted to Pinecone with all metadata

### `POST /ingest/batch`
JSON body `{ images: [{ image_url, location, capture_time, day, camera_device, latitude, longitude }] }`.

### `POST /chat`
```json
{ "message": "show me photos from Mumbai", "history": [] }
```

Flow:
1. Embed user message → 3072-dim vector
2. Pinecone search (threshold 0.60, top_k=5) → matched images
3. Cloudinary URLs of matched images sent directly to GPT-4o as vision inputs
4. GPT-4o sees actual images in real time → answers user question
5. Returns `{ answer, matched_images }`

### `GET /images-list`
Returns all images: `{ images: [...], total: N }`.

---

## Key Design Details

### Single Pinecone Index
Index name: `vision-rag-images`, dimension: 3072, metric: cosine.
Only text embeddings stored (from description). No separate image vector index.

### `get_all_images()` Trick
Uses a uniform dummy vector (`[1/√3072] * 3072`) to fetch all records via `query(top_k=1000)` — Pinecone's way of doing a full-table scan.

### GPT-4o Real-Time Vision in Chat
Matched image Cloudinary URLs are passed as `image_url` type in the OpenAI message content array. GPT-4o fetches and sees the actual images — not just descriptions.

### Auto Description
`get_description()` in `description_and_embedding.py` sends the image to GPT-4o with a detailed analysis prompt. User never types a description — it's always AI-generated on ingest.

### Day Auto-Extraction
`_extract_day(capture_time)` in `main.py` parses ISO datetime and extracts weekday name ("Monday", "Tuesday" etc.) automatically.

---

## Frontend Details

Single-file React app (`App.jsx`). All styling is inline CSS.

Design system (CSS variables in `index.css`):
- Background: `#f6f7fb`
- Accent: `#6366f1` (indigo)
- Font body: `Outfit`, Font mono: `Space Mono`

Upload Modal fields:
- File upload or Image URL (tab switch)
- Location, Date & Time, Camera/Device, Latitude, Longitude
- Description is **not** a user field — shown as "auto-generated by AI" info banner

ImageCard shows:
- Image thumbnail
- AI-generated description (2 lines)
- `📍 location` and `🕐 capture_time` if present
- Cosine similarity score

---

## Deployment

Backend on **Render** (`render.yaml`):
- Runtime: Python 3.11.9
- Build: `pip install -r requirements.txt`
- Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Auto-deploys on push to `main` branch only

Set env vars in Render dashboard (not in `render.yaml`).

---

## Common Tasks

**Add new metadata field:** Add to `save_image_record()` in `vector_store.py`, add `Form(None)` param in `/ingest` in `main.py`, add input field in `UploadModal` in `App.jsx`.

**Change similarity threshold:** Edit `threshold` param in `search_images()` call in `main.py` (currently 0.60).

**Switch to local backend in frontend:** Change `const API` on line 3 of `App.jsx`.

**Pinecone index reset:** Delete `vision-rag-images` index in Pinecone dashboard — code auto-recreates it at 3072-dim on next startup.
