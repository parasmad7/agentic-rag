"""NoSQL specialist agent: Gemini-controlled MongoDB query loop with result validation."""

import json
from datetime import datetime

from google.genai.types import (
    Content,
    FunctionDeclaration,
    GenerateContentConfig,
    Part,
    Tool,
)
from pymongo import MongoClient

from agentic_rag.agents.base import BaseAgent
from agentic_rag.agents.messages import SpecialistRequest, SpecialistResult
from agentic_rag.config import GEMINI_MODEL, MONGO_DB_NAME, MONGO_URI
from agentic_rag.llm import get_client
from agentic_rag.models import MetaResponse

MAX_TURNS = 5


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
            if isinstance(value, dict):
                fields.append(f"  {full_key}: object")
                fields.extend(_describe_fields(value, full_key))
            elif isinstance(value, list) and value:
                elem_type = type(value[0]).__name__
                fields.append(f"  {full_key}: array[{elem_type}]")
            else:
                fields.append(f"  {full_key}: {type(value).__name__}")
        return fields

    field_list = _describe_fields(sample)
    return f"Collection '{collection_name}':\n" + "\n".join(field_list)


def _serialize(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "__str__"):
        return str(obj)
    return obj


def _execute_mongo(collection_name: str, filter_doc: dict, projection: dict | None = None,
                   sort: dict | None = None, limit: int = 20) -> list[dict]:
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


def _build_tools() -> list[Tool]:
    return [Tool(function_declarations=[
        FunctionDeclaration(
            name="execute_mongo",
            description="Execute a MongoDB find query against a collection.",
            parameters={
                "type": "object",
                "properties": {
                    "filter": {
                        "type": "object",
                        "description": 'MongoDB filter document. Use {"$regex": "pattern", "$options": "i"} for text search. Use {"$gte": "YYYY-MM-DD"} for date comparisons. Do NOT use $text or $search.',
                    },
                    "projection": {
                        "type": "object",
                        "description": "Fields to include/exclude (optional). Example: {\"name\": 1, \"rating\": 1}",
                    },
                    "sort": {
                        "type": "object",
                        "description": "Sort specification (optional). Example: {\"rating\": -1} for descending.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max documents to return. Default 20.",
                    },
                },
                "required": ["filter"],
            },
        ),
    ])]


def _build_system_prompt(schema: str, collection_name: str) -> str:
    return f"""You are a MongoDB expert. Generate and execute queries to answer the user's question.

COLLECTION: {collection_name}
SCHEMA:
{schema}

RULES:
- Use {{"$regex": "pattern", "$options": "i"}} for text search — do NOT use $text or $search
- Use {{"$gte": "YYYY-MM-DD"}} for date comparisons
- After seeing query results, evaluate whether they fully answer the question
- If results are empty, try a broader filter (e.g., remove restrictive conditions, use regex instead of exact match)
- You may run multiple queries to build a complete answer
- When you have enough data, provide a clear summary that includes all specific names, numbers, and values from the results"""


class NoSQLAgent(BaseAgent[SpecialistRequest, SpecialistResult]):
    name = "nosql_agent"

    def run(self, req: SpecialistRequest) -> SpecialistResult:
        collection_name = req.source_name
        schema = _get_collection_schema(collection_name)
        client = get_client()
        tools = _build_tools()
        system_prompt = _build_system_prompt(schema, collection_name)

        history: list[Content] = [
            Content(role="user", parts=[Part.from_text(text=req.question)]),
        ]
        all_docs: list[dict] = []
        all_queries: list[str] = []
        attempts = 0
        last_error = None

        for turn in range(1, MAX_TURNS + 1):
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=history,
                config=GenerateContentConfig(
                    tools=tools,
                    system_instruction=system_prompt,
                ),
            )

            candidate = response.candidates[0]
            history.append(candidate.content)

            function_calls = [
                p for p in candidate.content.parts if p.function_call is not None
            ]

            if not function_calls:
                summary = response.text.strip() if response.text else json.dumps(all_docs[:10], default=str)
                return SpecialistResult(
                    source_id=req.source_id,
                    response=MetaResponse(
                        source=collection_name,
                        source_type="nosql",
                        query_used="; ".join(all_queries),
                        confidence=0.9 if all_docs else 0.3,
                        summary=summary,
                        data=all_docs[:20],
                        row_count=len(all_docs),
                    ),
                    attempts=attempts,
                )

            function_response_parts = []
            for fc_part in function_calls:
                fc = fc_part.function_call
                args = dict(fc.args)
                filter_doc = args.get("filter", {})
                attempts += 1
                query_desc = json.dumps({"filter": filter_doc}, default=str)

                try:
                    docs = _execute_mongo(
                        collection_name,
                        filter_doc,
                        projection=args.get("projection"),
                        sort=args.get("sort"),
                        limit=int(args.get("limit", 20)),
                    )
                    all_docs.extend(docs)
                    all_queries.append(query_desc)
                    result = {"documents": docs[:10], "total_count": len(docs)}
                except Exception as e:
                    last_error = str(e)
                    result = {"error": f"Query failed: {e}"}

                function_response_parts.append(
                    Part.from_function_response(name="execute_mongo", response=result)
                )

            history.append(Content(role="user", parts=function_response_parts))

        summary = json.dumps(all_docs[:10], default=str) if all_docs else f"Max turns reached. Last error: {last_error}"
        return SpecialistResult(
            source_id=req.source_id,
            response=MetaResponse(
                source=collection_name,
                source_type="nosql",
                query_used="; ".join(all_queries),
                confidence=0.5 if all_docs else 0.1,
                summary=summary,
                data=all_docs[:20],
                row_count=len(all_docs),
            ),
            attempts=attempts,
            error=last_error,
        )
