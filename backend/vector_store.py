import os
import time
from datetime import datetime
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec

load_dotenv()

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))


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


image_index = _get_or_create_index("vision-rag-images", 512)
text_index = _get_or_create_index("vision-rag-text", 512)


def save_image_record(
    image_id: str,
    image_path: str,
    filename: str,
    description: str,
    tags: list,
    image_vector: list,
    text_vector: list
):
    metadata = {
        "image_id": image_id,
        "filename": filename,
        "image_url": filename,
        "description": description,
        "tags": ", ".join(tags),
        "created_at": datetime.now().isoformat()
    }

    image_index.upsert(vectors=[{
        "id": f"{image_id}_image",
        "values": image_vector,
        "metadata": {**metadata, "type": "image"}
    }])

    text_index.upsert(vectors=[{
        "id": f"{image_id}_text",
        "values": text_vector,
        "metadata": {**metadata, "type": "text"}
    }])


def get_all_images() -> list:
    """Saare images ki metadata list — /chat aur /images-list ke liye"""
    all_ids = []
    for ids_batch in text_index.list():
        all_ids.extend(ids_batch)

    if not all_ids:
        return []

    fetch_result = text_index.fetch(ids=all_ids)
    seen = set()
    images = []

    for vec in fetch_result.vectors.values():
        meta = vec.metadata
        image_id = meta.get("image_id")
        if image_id and image_id not in seen:
            seen.add(image_id)
            images.append(meta)

    return images


def search_images(query_vector: list, top_k: int = 3, query_text: str = "") -> list:
    results = text_index.query(
        vector=query_vector,
        top_k=top_k * 4,
        include_metadata=True
    )

    seen = set()
    images = []

    for match in results["matches"]:
        meta = match["metadata"]
        image_id = meta.get("image_id")
        if image_id and image_id not in seen:
            seen.add(image_id)
            images.append({
                "image_id": image_id,
                "image_url": meta["image_url"],
                "description": meta["description"],
                "tags": meta["tags"],
                "score": round(float(match["score"]), 3)
            })

    return images[:top_k]
