"""Image search tool: CLIP-based vector search in ChromaDB."""

import chromadb

from agentic_rag.config import CHROMA_DIR, IMAGE_COLLECTION
from agentic_rag.ingestion.clip_embedder import embed_text


def search_images(
    query: str,
    source_filter: list[str] | None = None,
    top_k: int = 3,
) -> list[dict]:
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        collection = client.get_collection(IMAGE_COLLECTION)
    except Exception:
        return []

    query_embedding = embed_text(query)

    where = None
    if source_filter:
        where = {"source": {"$in": source_filter}}

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where,
        include=["metadatas", "distances"],
    )

    hits = []
    for i in range(len(results["ids"][0])):
        meta = results["metadatas"][0][i]
        hits.append({
            "id": results["ids"][0][i],
            "image_path": meta["image_path"],
            "source": meta["source"],
            "page_num": meta["page_num"],
            "distance": results["distances"][0][i],
            "relevance_score": round(1 - results["distances"][0][i], 3),
        })
    return hits
