"""NoSQL tool: generate and execute MongoDB queries via Gemini."""

import json
from datetime import datetime

from pymongo import MongoClient

from agentic_rag.config import MONGO_DB_NAME, MONGO_URI
from agentic_rag.llm import generate
from agentic_rag.models import MetaResponse


def _get_collection_schema(collection_name: str) -> str:
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB_NAME]
    sample = db[collection_name].find_one()
    client.close()

    if not sample:
        return f"Collection '{collection_name}': empty"

    def _describe_fields(doc: dict, prefix: str = "") -> list[str]:
        fields = []
        for key, value in doc.items():
            if key == "_id":
                continue
            full_key = f"{prefix}{key}" if not prefix else f"{prefix}.{key}"
            type_name = type(value).__name__
            if isinstance(value, dict):
                fields.append(f"  {full_key}: object")
                fields.extend(_describe_fields(value, full_key))
            elif isinstance(value, list) and value:
                elem_type = type(value[0]).__name__
                fields.append(f"  {full_key}: array[{elem_type}]")
            else:
                fields.append(f"  {full_key}: {type_name}")
        return fields

    field_list = _describe_fields(sample)
    return f"Collection '{collection_name}':\n" + "\n".join(field_list)


def _serialize(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "__str__"):
        return str(obj)
    return obj


def query_nosql(question: str, collection_names: list[str]) -> MetaResponse:
    schemas = []
    for name in collection_names:
        schemas.append(_get_collection_schema(name))

    prompt = f"""You are a MongoDB expert. Given the following collection schemas and a user question,
generate a MongoDB query as a JSON object.

RULES:
- Return ONLY a JSON object with these fields:
  - "collection": the collection name to query
  - "filter": the MongoDB filter document (use {{"$regex": "pattern", "$options": "i"}} for text search)
  - "projection": fields to include (optional)
  - "sort": sort specification (optional)
  - "limit": max documents to return (default 20)
- For date comparisons, use {{"$gte": "YYYY-MM-DD"}} format
- Do NOT use $text or $search operators

SCHEMAS:
{chr(10).join(schemas)}

QUESTION: {question}

JSON QUERY:"""

    query_text = generate(prompt)
    query_text = query_text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        query_spec = json.loads(query_text)
    except json.JSONDecodeError:
        return MetaResponse(
            source=", ".join(collection_names),
            source_type="nosql",
            query_used=query_text,
            confidence=0.1,
            summary="Failed to parse generated MongoDB query.",
            data=[],
            row_count=0,
        )

    collection_name = query_spec.get("collection", collection_names[0])
    filter_doc = query_spec.get("filter", {})
    projection = query_spec.get("projection")
    sort = query_spec.get("sort")
    limit = query_spec.get("limit", 20)

    try:
        mongo_client = MongoClient(MONGO_URI)
        db = mongo_client[MONGO_DB_NAME]
        cursor = db[collection_name].find(filter_doc, projection)
        if sort:
            sort_list = [(k, v) for k, v in sort.items()]
            cursor = cursor.sort(sort_list)
        cursor = cursor.limit(limit)
        docs = []
        for doc in cursor:
            serialized = {}
            for k, v in doc.items():
                serialized[k] = _serialize(v)
            docs.append(serialized)
        mongo_client.close()
    except Exception as e:
        return MetaResponse(
            source=collection_name,
            source_type="nosql",
            query_used=query_text,
            confidence=0.1,
            summary=f"Query execution failed: {e}",
            data=[],
            row_count=0,
        )

    summary_prompt = f"""Given this MongoDB query and its results, provide a concise summary answering the original question.

QUESTION: {question}
QUERY: {query_text}
RESULTS ({len(docs)} documents): {json.dumps(docs[:10], default=str)}

Provide a 2-3 sentence summary of the findings:"""

    summary_text = generate(summary_prompt)

    return MetaResponse(
        source=collection_name,
        source_type="nosql",
        query_used=query_text,
        confidence=0.9 if docs else 0.3,
        summary=summary_text,
        data=docs[:20],
        row_count=len(docs),
    )
