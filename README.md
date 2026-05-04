# VisionRAG

A visual search and chat system that lets you upload images with descriptions, store them as vector embeddings, and query them using natural language.

---

## What It Does

- Upload images (file or URL) with a custom description
- Images are embedded using CLIP and stored in a vector database
- Chat interface to search and retrieve images using natural language
- GPT-4o-mini answers queries based on your image knowledge base

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python 3.11) |
| Vector DB | Pinecone (Serverless, AWS us-east-1) |
| Embeddings | CLIP ViT-B-32 via Hugging Face Space |
| Chat / QA | GPT-4o-mini (OpenAI) |
| Image Storage | Cloudinary |
| Frontend | React 18 + Vite |
| Deployment | Render (backend) |

---

## Project Structure

```
vision-rag/
├── backend/
│   ├── main.py           # FastAPI app — /ingest, /chat, /images-list
│   ├── clip_model.py     # CLIP embeddings via HF Space (512-dim)
│   ├── vector_store.py   # Pinecone — image + text indexes
│   ├── image_store.py    # Cloudinary upload + local temp storage
│   ├── vlm.py            # GPT-4o-mini vision (reserved for future use)
│   ├── requirements.txt
│   └── runtime.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx       # Full React UI
│   │   ├── index.css     # Dark theme styles
│   │   └── main.jsx      # Entry point
│   ├── index.html
│   └── vite.config.js
├── render.yaml
└── README.md
```

---

## API Endpoints

### `POST /ingest`
Upload an image with a description into the knowledge base.

**Form fields:**
| Field | Type | Required |
|---|---|---|
| `file` | Image file | One of file or image_url |
| `image_url` | string | One of file or image_url |
| `description` | string | Yes |
| `tags` | string (comma-separated) | No |

**Response:**
```json
{
  "success": true,
  "image_id": "uuid",
  "image_url": "https://cloudinary.com/...",
  "description": "your description",
  "tags": ["tag1", "tag2"]
}
```

---

### `POST /chat`
Query your image knowledge base with natural language.

**Request body:**
```json
{
  "message": "show me images of sunsets",
  "history": []
}
```

**Response:**
```json
{
  "answer": "Yes, there is a sunset image...",
  "matched_images": [
    {
      "image_id": "uuid",
      "image_url": "https://cloudinary.com/...",
      "description": "...",
      "tags": "...",
      "score": 0.912
    }
  ]
}
```

---

### `GET /images-list`
Returns all images in the knowledge base.

**Response:**
```json
{
  "images": [...],
  "total": 12
}
```

---

## Error Responses

All endpoints return standard HTTP error codes with a JSON body:

```json
{ "detail": "error message" }
```

| Status Code | Cause |
|---|---|
| `400 Bad Request` | Neither `file` nor `image_url` provided, or `description` is empty |
| `404 Not Found` | Route does not exist |
| `422 Unprocessable Entity` | Required field missing or wrong type in request body |
| `500 Internal Server Error` | Upstream failure — Cloudinary upload, CLIP HF Space, or Pinecone error |

**Frontend behavior:**
- On ingest error → shows error message inside the upload modal
- On chat error → shows `⚠ Could not reach backend` in the chat

---

## Local Setup

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
uvicorn main:app --port 8000
```

Create `backend/.env`:
```
OPENAI_API_KEY=your_key
PINECONE_API_KEY=your_key
CLOUDINARY_CLOUD_NAME=your_name
CLOUDINARY_API_KEY=your_key
CLOUDINARY_API_SECRET=your_secret
HF_TOKEN=your_token
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Update `src/App.jsx` line 3:
```js
const API = 'http://127.0.0.1:8000'
```

Open `http://localhost:3000`

---

## How It Works

### Ingest Flow
1. Image uploaded (file or URL) → saved locally + uploaded to Cloudinary
2. User-provided description used directly (no auto-generation)
3. CLIP HF Space → image vector (512-dim) + text vector from description (512-dim)
4. Both vectors upserted to Pinecone with metadata

### Chat Flow
1. Vague queries ("show this") → resolved using last assistant message
2. Query embedded via CLIP → Pinecone similarity search (score threshold: 0.85)
3. All image descriptions passed to GPT-4o-mini as context
4. Response includes answer + matched images (if display keywords detected)

---

## Deployment

Backend is deployed on **Render** via `render.yaml`.

Auto-deploys on push to `main` branch.

Set the following environment variables in Render dashboard:
- `OPENAI_API_KEY`
- `PINECONE_API_KEY`
- `CLOUDINARY_CLOUD_NAME`
- `CLOUDINARY_API_KEY`
- `CLOUDINARY_API_SECRET`
- `HF_TOKEN`
