"""NoSQL specialist agent: generates and executes MongoDB queries with retry on failure."""

import json
from datetime import datetime

from pymongo import MongoClient

from agentic_rag.agents.base import BaseAgent
from agentic_rag.agents.messages import SpecialistRequest, SpecialistResult
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


def _generate_mongo_query(question: str, schemas: str, error_context: str = "") -> str:
    error_section = ""
    if error_context:
        error_section = f"""
PREVIOUS ATTEMPT FAILED:
{error_context}
Generate a corrected query that avoids this error.

"""

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
{schemas}
{error_section}QUESTION: {question}

JSON QUERY:"""

    text = generate(prompt)
    return text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()


def _execute_mongo(collection_name: str, query_spec: dict) -> list[dict]:
    filter_doc = query_spec.get("filter", {})
    projection = query_spec.get("projection")
    sort = query_spec.get("sort")
    limit = query_spec.get("limit", 20)

    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client[MONGO_DB_NAME]
    cursor = db[collection_name].find(filter_doc, projection)
    if sort:
        sort_list = [(k, v) for k, v in sort.items()]
        cursor = cursor.sort(sort_list)
    cursor = cursor.limit(limit)

    docs = []
    for doc in cursor:
        serialized = {k: _serialize(v) for k, v in doc.items()}
        docs.append(serialized)

    mongo_client.close()
    return docs


class NoSQLAgent(BaseAgent[SpecialistRequest, SpecialistResult]):
    name = "nosql_agent"

    def run(self, req: SpecialistRequest) -> SpecialistResult:
        collection_names = [req.source_name]
        schema = _get_collection_schema(req.source_name)

        last_error = None
        for attempt in range(1, req.max_retries + 2):
            error_ctx = ""
            if last_error:
                error_ctx = last_error[:500]

            query_text = _generate_mongo_query(req.question, schema, error_ctx)

            try:
                query_spec = json.loads(query_text)
            except json.JSONDecodeError:
                last_error = f"Query: {query_text}\nError: Invalid JSON"
                if attempt >= req.max_retries + 1:
                    return SpecialistResult(
                        source_id=req.source_id,
                        response=MetaResponse(
                            source=", ".join(collection_names),
                            source_type="nosql",
                            query_used=query_text,
                            confidence=0.1,
                            summary=f"Failed to parse MongoDB query after {attempt} attempts.",
                            data=[],
                            row_count=0,
                        ),
                        attempts=attempt,
                        error="Invalid JSON",
                    )
                continue

            collection_name = query_spec.get("collection", req.source_name)

            try:
                docs = _execute_mongo(collection_name, query_spec)
                return SpecialistResult(
                    source_id=req.source_id,
                    response=MetaResponse(
                        source=collection_name,
                        source_type="nosql",
                        query_used=query_text,
                        confidence=0.9 if docs else 0.3,
                        summary=json.dumps(docs[:10], default=str),
                        data=docs[:20],
                        row_count=len(docs),
                    ),
                    attempts=attempt,
                )
            except Exception as e:
                last_error = f"Query: {query_text}\nError: {e}"
                if attempt >= req.max_retries + 1:
                    return SpecialistResult(
                        source_id=req.source_id,
                        response=MetaResponse(
                            source=collection_name,
                            source_type="nosql",
                            query_used=query_text,
                            confidence=0.1,
                            summary=f"All {attempt} attempts failed: {e}",
                            data=[],
                            row_count=0,
                        ),
                        attempts=attempt,
                        error=str(e),
                    )
