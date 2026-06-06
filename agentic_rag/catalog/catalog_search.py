"""Catalog management: load YAML, embed into ChromaDB, and search."""

import chromadb
import yaml

from agentic_rag.config import CATALOG_PATH, CHROMA_DIR
from agentic_rag.models import CatalogEntry

CATALOG_COLLECTION = "source_catalog"


def load_catalog() -> list[CatalogEntry]:
    with open(CATALOG_PATH) as f:
        data = yaml.safe_load(f)
    return [CatalogEntry(**s) for s in data["sources"]]


def load_domains() -> dict[str, str]:
    with open(CATALOG_PATH) as f:
        data = yaml.safe_load(f)
    return {d["name"]: d["description"] for d in data.get("domains", [])}


def _build_embedding_text(entry: CatalogEntry) -> str:
    parts = [
        entry.description,
        f"Key fields: {', '.join(entry.key_fields)}",
        "Example questions: " + " | ".join(entry.sample_questions),
    ]
    return " ".join(parts)


def index_catalog(entries: list[CatalogEntry]) -> chromadb.Collection:
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        client.delete_collection(CATALOG_COLLECTION)
    except Exception:
        pass

    collection = client.get_or_create_collection(
        name=CATALOG_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )

    ids = [e.id for e in entries]
    documents = [_build_embedding_text(e) for e in entries]
    metadatas = [
        {
            "source_type": e.source_type,
            "domain": e.domain,
            "name": e.name,
            "description": e.description,
        }
        for e in entries
    ]

    collection.add(ids=ids, documents=documents, metadatas=metadatas)
    return collection


def search_catalog(
    query: str,
    top_k: int = 10,
    domain_filter: list[str] | None = None,
) -> list[dict]:
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_collection(CATALOG_COLLECTION)

    where = None
    if domain_filter:
        where = {"domain": {"$in": domain_filter}}

    results = collection.query(
        query_texts=[query],
        n_results=top_k,
        where=where,
        include=["metadatas", "distances", "documents"],
    )

    hits = []
    for i in range(len(results["ids"][0])):
        hits.append({
            "id": results["ids"][0][i],
            "distance": results["distances"][0][i],
            "metadata": results["metadatas"][0][i],
        })
    return hits


def setup():
    entries = load_catalog()
    collection = index_catalog(entries)
    print(f"Indexed {collection.count()} catalog entries into ChromaDB")


if __name__ == "__main__":
    setup()
