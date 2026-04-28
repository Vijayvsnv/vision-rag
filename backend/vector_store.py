# # vector_store.py

# import chromadb
# from datetime import datetime

# # local persistent ChromaDB
# chroma_client = chromadb.PersistentClient(path="./chroma_db")
# # collection = chroma_client.get_or_create_collection(name="vision_rag")
# collection = chroma_client.get_or_create_collection(
#     name="vision_rag",
#     metadata={"hnsw:space": "cosine"}
# )

# def save_image_record(
#     image_id: str,
#     image_path: str,
#     filename: str,
#     description: str,
#     tags: list,
#     image_vector: list,
#     text_vector: list
# ):
#     """ image  record save in chroma db"""
    
#     # image vector save karo
#     collection.add(
#         ids=[f"{image_id}_image"],
#         embeddings=[image_vector],
#         metadatas=[{
#             "type": "image",
#             "image_id": image_id,
#             "filename": filename,
#             "image_url": f"/images/{filename}",
#             "description": description,
#             "tags": ", ".join(tags),
#             "created_at": datetime.now().isoformat()
#         }],
#         documents=[description]
#     )
    
#     # text/description vector save karo
#     collection.add(
#         ids=[f"{image_id}_text"],
#         embeddings=[text_vector],
#         metadatas=[{
#             "type": "text",
#             "image_id": image_id,
#             "filename": filename,
#             "image_url": f"/images/{filename}",
#             "description": description,
#             "tags": ", ".join(tags),
#             "created_at": datetime.now().isoformat()
#         }],
#         documents=[description]
#     )

# # def search_images(query_vector: list, top_k: int = 3) -> list:
# #     """Query vector se similar images dhundo"""
# #     results = collection.query(
# #         query_embeddings=[query_vector],
# #         n_results=top_k * 4

# #     )
    
# #     seen = set()
# #     images = []
    
# #     for i, metadata in enumerate(results["metadatas"][0]):
# #         image_id = metadata["image_id"]
# #         if image_id not in seen:
# #             seen.add(image_id)
# #             raw = float(results["distances"][0][i])
# #             images.append({
# #                 "image_id": image_id,
# #                 "image_url": metadata["image_url"],
# #                 "description": metadata["description"],
# #                 "tags": metadata["tags"],
# #                 "score": round(1 / (1 + raw), 3)
# #             })
    
# #     return images

# def search_images(query_vector: list, top_k: int = 3, query_text: str = "") -> list:
#     """Vector search + keyword search hybrid"""
    
#     # Step 1: vector similarity search
#     results = collection.query(
#         query_embeddings=[query_vector],
#         n_results=top_k * 4
#     )
    
#     seen = set()
#     images = []
    
#     for i, metadata in enumerate(results["metadatas"][0]):
#         image_id = metadata["image_id"]
#         if image_id not in seen:
#             seen.add(image_id)
#             raw = float(results["distances"][0][i])
#             images.append({
#                 "image_id": image_id,
#                 "image_url": metadata["image_url"],
#                 "description": metadata["description"],
#                 "tags": metadata["tags"],
#                 "score": round(1 / (1 + raw), 3)
#             })
    
#     # Step 2: keyword search — query ke words description mein dhundo
#     if query_text:
#         all_records = collection.get()
#         keywords = query_text.lower().split()
#         keyword_seen = set(x["image_id"] for x in images)
        
#         for metadata in all_records["metadatas"]:
#             image_id = metadata["image_id"]
#             if image_id in keyword_seen:
#                 continue
#             desc_lower = metadata["description"].lower()
#             tags_lower = metadata["tags"].lower()
#             if any(kw in desc_lower or kw in tags_lower for kw in keywords):
#                 keyword_seen.add(image_id)
#                 images.append({
#                     "image_id": image_id,
#                     "image_url": metadata["image_url"],
#                     "description": metadata["description"],
#                     "tags": metadata["tags"],
#                     "score": 0.5
#                 })
#     filtered = [img for img in images if img["score"] >= 0.007]
#     return filtered[:top_k] if filtered else images[:1]
















import chromadb
from datetime import datetime

chroma_client = chromadb.PersistentClient(path="./chroma_db")

# image vectors ke liye — CLIP 512-dim
image_collection = chroma_client.get_or_create_collection(
    name="vision_rag_images",
    metadata={"hnsw:space": "cosine"}
)

# text vectors ke liye — OpenAI 1536-dim
text_collection = chroma_client.get_or_create_collection(
    name="vision_rag_text",
    metadata={"hnsw:space": "cosine"}
)

# backward compatibility ke liye
collection = text_collection

def save_image_record(
    image_id: str,
    image_path: str,
    filename: str,
    description: str,
    tags: list,
    image_vector: list,
    text_vector: list
):
    # image vector — CLIP collection mein
    image_collection.add(
        ids=[f"{image_id}_image"],
        embeddings=[image_vector],
        metadatas=[{
            "type": "image",
            "image_id": image_id,
            "filename": filename,
            "image_url": f"/images/{filename}",
            "description": description,
            "tags": ", ".join(tags),
            "created_at": datetime.now().isoformat()
        }],
        documents=[description]
    )

    # text vector — OpenAI collection mein
    text_collection.add(
        ids=[f"{image_id}_text"],
        embeddings=[text_vector],
        metadatas=[{
            "type": "text",
            "image_id": image_id,
            "filename": filename,
            "image_url": f"/images/{filename}",
            "description": description,
            "tags": ", ".join(tags),
            "created_at": datetime.now().isoformat()
        }],
        documents=[description]
    )

def search_images(query_vector: list, top_k: int = 3, query_text: str = "") -> list:
    # text_collection mein search karo — OpenAI vectors
    results = text_collection.query(
        query_embeddings=[query_vector],
        n_results=top_k * 4
    )

    seen = set()
    images = []

    for i, metadata in enumerate(results["metadatas"][0]):
        image_id = metadata["image_id"]
        if image_id not in seen:
            seen.add(image_id)
            raw = float(results["distances"][0][i])
            images.append({
                "image_id": image_id,
                "image_url": metadata["image_url"],
                "description": metadata["description"],
                "tags": metadata["tags"],
                "score": round(1 / (1 + raw), 3)
            })

    return images[:top_k]