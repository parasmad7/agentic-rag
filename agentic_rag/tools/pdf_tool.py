"""PDF search tool: hybrid retrieval (vector + BM25) with cross-encoder reranking."""

import chromadb
from sentence_transformers import CrossEncoder

from agentic_rag.config import CHROMA_DIR
from agentic_rag.ingestion.pdf_pipeline import PDF_COLLECTION
from agentic_rag.models import ImageReference, MetaResponse
from agentic_rag.tools.bm25_search import search_bm25
from agentic_rag.tools.image_describer import describe_images_batch
from agentic_rag.tools.image_tool import search_images

VECTOR_WEIGHT = 0.8
BM25_WEIGHT = 0.2
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

_reranker: CrossEncoder | None = None


def _get_reranker() -> CrossEncoder:
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder(RERANKER_MODEL)
    return _reranker


def _rerank(query: str, hits: list[dict], top_k: int = 5) -> list[dict]:
    if not hits:
        return []
    reranker = _get_reranker()
    pairs = [(query, h["document"]) for h in hits]
    scores = reranker.predict(pairs)
    for i, hit in enumerate(hits):
        hit["rerank_score"] = float(scores[i])
    hits.sort(key=lambda h: h["rerank_score"], reverse=True)
    return hits[:top_k]


def _search_vector(
    query: str,
    source_filter: list[str] | None = None,
    top_k: int = 10,
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


def _min_max_normalize(scores: list[float]) -> list[float]:
    if not scores:
        return []
    lo, hi = min(scores), max(scores)
    if hi == lo:
        return [1.0] * len(scores)
    return [(s - lo) / (hi - lo) for s in scores]


def _hybrid_search(
    query: str,
    source_filter: list[str] | None = None,
    top_k: int = 5,
) -> list[dict]:
    vector_hits = _search_vector(query, source_filter, top_k=top_k * 2)
    bm25_hits = search_bm25(query, source_filter, top_k=top_k * 2)

    vec_scores = _min_max_normalize([1 - h["distance"] for h in vector_hits])
    bm25_scores = _min_max_normalize([h["bm25_score"] for h in bm25_hits])

    fused: dict[str, float] = {}
    hit_map: dict[str, dict] = {}

    for i, hit in enumerate(vector_hits):
        doc_id = hit["id"]
        fused[doc_id] = VECTOR_WEIGHT * vec_scores[i]
        hit_map[doc_id] = hit

    for i, hit in enumerate(bm25_hits):
        doc_id = hit["id"]
        fused[doc_id] = fused.get(doc_id, 0) + BM25_WEIGHT * bm25_scores[i]
        if doc_id not in hit_map:
            hit_map[doc_id] = {
                "id": doc_id,
                "document": hit["document"],
                "metadata": hit["metadata"],
                "distance": 1.0,
            }

    ranked = sorted(fused.items(), key=lambda x: x[1], reverse=True)[:top_k * 2]

    candidates = []
    for doc_id, score in ranked:
        hit = hit_map[doc_id]
        hit["hybrid_score"] = score
        candidates.append(hit)

    reranked = _rerank(query, candidates, top_k=top_k)
    return reranked


def _expand_context(hits: list[dict]) -> str:
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_collection(PDF_COLLECTION)

    parent_ids = set()
    doc_summary_ids = set()
    for hit in hits:
        parent_id = hit["metadata"].get("parent_section_id")
        if parent_id:
            parent_ids.add(parent_id)
        source = hit["metadata"]["source"]
        doc_summary_ids.add(f"{source}__doc_summary")

    expanded_text_parts = []

    doc_results = collection.get(
        ids=list(doc_summary_ids),
        include=["documents", "metadatas"],
    )
    for i, doc in enumerate(doc_results["documents"]):
        meta = doc_results["metadatas"][i]
        expanded_text_parts.append(
            f"[Document Context - {meta['source']}]\n{doc}"
        )

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

    sibling_ids = set()
    hit_ids = {h["id"] for h in hits}
    for hit in hits:
        source = hit["metadata"]["source"]
        section = hit["metadata"]["section"]
        chunk_idx = hit["metadata"]["chunk_index"]
        section_id_prefix = hit["id"].rsplit("__c", 1)[0]
        for offset in (-1, 1):
            neighbor_id = f"{section_id_prefix}__c{chunk_idx + offset}"
            if neighbor_id not in hit_ids:
                sibling_ids.add(neighbor_id)

    if sibling_ids:
        sibling_results = collection.get(
            ids=list(sibling_ids),
            include=["documents", "metadatas"],
        )
        sibling_map = {
            sibling_results["ids"][i]: sibling_results["documents"][i]
            for i in range(len(sibling_results["ids"]))
        }
    else:
        sibling_map = {}

    for hit in hits:
        section_id_prefix = hit["id"].rsplit("__c", 1)[0]
        chunk_idx = hit["metadata"]["chunk_index"]

        prev_id = f"{section_id_prefix}__c{chunk_idx - 1}"
        if prev_id in sibling_map:
            expanded_text_parts.append(f"[Preceding chunk]\n{sibling_map[prev_id]}")

        expanded_text_parts.append(hit["document"])

        next_id = f"{section_id_prefix}__c{chunk_idx + 1}"
        if next_id in sibling_map:
            expanded_text_parts.append(f"[Following chunk]\n{sibling_map[next_id]}")

    return "\n\n---\n\n".join(expanded_text_parts)


IMAGE_RELEVANCE_RATIO = 0.75


def _search_and_describe_images(
    question: str, source_filter: list[str] | None = None, top_k: int = 3
) -> tuple[list[ImageReference], str]:
    image_hits = search_images(question, source_filter, top_k)
    if not image_hits:
        return [], ""

    best_score = image_hits[0]["relevance_score"]
    threshold = best_score * IMAGE_RELEVANCE_RATIO
    image_hits = [h for h in image_hits if h["relevance_score"] >= threshold]

    image_paths = [h["image_path"] for h in image_hits]
    descriptions = describe_images_batch(image_paths, query_context=question)

    image_refs = []
    context_parts = []
    for hit in image_hits:
        desc = descriptions.get(hit["image_path"], "")
        image_refs.append(ImageReference(
            image_path=hit["image_path"],
            source=hit["source"],
            page_num=hit["page_num"],
            description=desc,
            relevance_score=hit["relevance_score"],
        ))
        context_parts.append(
            f"[Image from {hit['source']} page {hit['page_num'] + 1}]\n{desc}"
        )

    return image_refs, "\n\n---\n\n".join(context_parts)


def search_pdfs(question: str, source_filter: list[str] | None = None) -> MetaResponse:
    hits = _hybrid_search(question, source_filter)

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

    best_rerank = hits[0].get("rerank_score", 1.0) if hits else 1.0
    chunk_data = [
        {
            "type": "text",
            "source": h["metadata"]["source"],
            "section": h["metadata"]["section"],
            "rerank_score": round(h.get("rerank_score", 0), 4),
            "hybrid_score": round(h.get("hybrid_score", 0), 4),
            "excerpt": h["document"][:200] + "...",
        }
        for h in hits
    ]

    image_refs, image_context = _search_and_describe_images(question, source_filter)
    if image_context:
        expanded_context = image_context + "\n\n---\n\n" + expanded_context

    for img in image_refs:
        sources_found.append(img.source)
        chunk_data.append({
            "type": "image",
            "source": img.source,
            "image_path": img.image_path,
            "description": img.description[:200] + "...",
            "relevance_score": img.relevance_score,
        })

    sources_found = list(dict.fromkeys(sources_found))
    avg_rerank = sum(h.get("rerank_score", 0) for h in hits) / len(hits) if hits else 0
    confidence = round(min(max(avg_rerank, 0.1), 1.0), 2)

    return MetaResponse(
        source=", ".join(sources_found),
        source_type="pdf",
        query_used=question,
        confidence=confidence,
        summary=expanded_context,
        data=chunk_data,
        row_count=len(hits),
        images=image_refs if image_refs else None,
    )
