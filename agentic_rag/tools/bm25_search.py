"""BM25 keyword search over PDF chunks in ChromaDB."""

import re

import chromadb
from rank_bm25 import BM25Okapi

from agentic_rag.config import CHROMA_DIR
from agentic_rag.ingestion.pdf_pipeline import PDF_COLLECTION


def _strip_metadata_prefix(text: str) -> str:
    text = re.sub(r"\[Document:[^\]]*\]\s*", "", text)
    text = re.sub(r"\[Section:[^\]]*\]\s*", "", text)
    return text


def _tokenize(text: str) -> list[str]:
    text = _strip_metadata_prefix(text)
    unigrams = re.findall(r"\w+", text.lower())
    bigrams = [f"{unigrams[i]}_{unigrams[i+1]}" for i in range(len(unigrams) - 1)]
    return unigrams + bigrams


def search_bm25(
    query: str,
    source_filter: list[str] | None = None,
    top_k: int = 5,
) -> list[dict]:
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_collection(PDF_COLLECTION)

    where = {"level": "chunk"}
    if source_filter:
        where = {
            "$and": [
                {"level": "chunk"},
                {"source": {"$in": source_filter}},
            ]
        }

    all_chunks = collection.get(where=where, include=["documents", "metadatas"])

    if not all_chunks["ids"]:
        return []

    corpus = [_tokenize(doc) for doc in all_chunks["documents"]]
    bm25 = BM25Okapi(corpus)

    query_tokens = _tokenize(query)
    scores = bm25.get_scores(query_tokens)

    scored = sorted(
        zip(range(len(scores)), scores),
        key=lambda x: x[1],
        reverse=True,
    )[:top_k]

    hits = []
    for idx, score in scored:
        if score <= 0:
            continue
        hits.append({
            "id": all_chunks["ids"][idx],
            "document": all_chunks["documents"][idx],
            "metadata": all_chunks["metadatas"][idx],
            "bm25_score": float(score),
        })
    return hits
