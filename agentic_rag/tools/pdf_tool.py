"""PDF search tool: vector search with small-to-big retrieval from ChromaDB."""

import chromadb

from agentic_rag.config import CHROMA_DIR
from agentic_rag.ingestion.pdf_pipeline import PDF_COLLECTION
from agentic_rag.llm import generate
from agentic_rag.models import MetaResponse


def _search_chunks(
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

    results = collection.query(
        query_texts=[query],
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    hits = []
    for i in range(len(results["ids"][0])):
        hits.append({
            "id": results["ids"][0][i],
            "document": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
        })
    return hits


def _expand_context(hits: list[dict]) -> str:
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_collection(PDF_COLLECTION)

    parent_ids = set()
    for hit in hits:
        parent_id = hit["metadata"].get("parent_section_id")
        if parent_id:
            parent_ids.add(parent_id)

    expanded_text_parts = []

    if parent_ids:
        parent_results = collection.get(
            ids=list(parent_ids),
            include=["documents", "metadatas"],
        )
        for i, doc in enumerate(parent_results["documents"]):
            meta = parent_results["metadatas"][i]
            expanded_text_parts.append(
                f"[Section Context - {meta['source']}: {meta['section']}]\n{doc}"
            )

    for hit in hits:
        expanded_text_parts.append(hit["document"])

    return "\n\n---\n\n".join(expanded_text_parts)


def search_pdfs(question: str, source_filter: list[str] | None = None) -> MetaResponse:
    hits = _search_chunks(question, source_filter)

    if not hits:
        sources = ", ".join(source_filter) if source_filter else "all PDFs"
        return MetaResponse(
            source=sources,
            source_type="pdf",
            query_used=question,
            confidence=0.0,
            summary="No relevant PDF content found.",
            data=[],
            row_count=0,
        )

    expanded_context = _expand_context(hits)
    sources_found = list({h["metadata"]["source"] for h in hits})

    prompt = f"""Based on the following document excerpts, answer the user's question.
Cite the specific document and section when possible.

QUESTION: {question}

DOCUMENT EXCERPTS:
{expanded_context}

Provide a concise, accurate answer based only on the provided excerpts:"""

    response_text = generate(prompt)

    chunk_data = [
        {
            "source": h["metadata"]["source"],
            "section": h["metadata"]["section"],
            "relevance_score": round(1 - h["distance"], 3),
            "excerpt": h["document"][:200] + "...",
        }
        for h in hits
    ]

    avg_relevance = sum(1 - h["distance"] for h in hits) / len(hits)

    return MetaResponse(
        source=", ".join(sources_found),
        source_type="pdf",
        query_used=question,
        confidence=round(min(avg_relevance + 0.2, 1.0), 2),
        summary=response_text,
        data=chunk_data,
        row_count=len(hits),
    )
