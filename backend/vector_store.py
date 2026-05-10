import os
import math
import time
from datetime import datetime
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec

load_dotenv()

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

INDEX_NAME = "vision-rag-text-index"
DIMENSION = 3072


def _get_or_create_index(name: str, dimension: int):
    existing = [idx.name for idx in pc.list_indexes()]
    if name not in existing:
        pc.create_index(
            name=name,
            dimension=dimension,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
        while not pc.describe_index(name).status["ready"]:
            time.sleep(1)
    return pc.Index(name)


index = _get_or_create_index(INDEX_NAME, DIMENSION)


def save_image_record(
    image_id: str,
    image_url: str,
    description: str,
    vector: list,
    notes: str = None,
):
    metadata = {
        "image_id": image_id,
        "image_url": image_url,
        "description": description,
        "notes": notes or "",
        "created_at": datetime.now().isoformat()
    }

    index.upsert(vectors=[{
        "id": image_id,
        "values": vector,
        "metadata": metadata
    }])


def get_all_images() -> list:
    dummy_vector = [1.0 / math.sqrt(DIMENSION)] * DIMENSION

    results = index.query(
        vector=dummy_vector,
        top_k=1000,
        include_metadata=True
    )

    return [match["metadata"] for match in results["matches"]]


def search_images(query_vector: list, top_k: int = 5, threshold: float = 0.60) -> list:
    results = index.query(
        vector=query_vector,
        top_k=top_k * 3,
        include_metadata=True
    )

    images = []
    for match in results["matches"]:
        score = round(float(match["score"]), 3)
        if score < threshold:
            continue
        meta = match["metadata"]
        images.append({
            "image_id": meta.get("image_id", ""),
            "image_url": meta.get("image_url", ""),
            "description": meta.get("description", ""),
            "notes": meta.get("notes", ""),
            "score": score
        })

    return images[:top_k]
