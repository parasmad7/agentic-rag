"""SQL specialist agent: Gemini-controlled query loop with result validation."""

import json

import sqlalchemy as sa
from google.genai.types import (
    Content,
    FunctionDeclaration,
    GenerateContentConfig,
    Part,
    Tool,
)

from agentic_rag.agents.base import BaseAgent
from agentic_rag.agents.messages import SpecialistRequest, SpecialistResult
from agentic_rag.config import GEMINI_MODEL, SQL_QUERY_LIMIT, SQLITE_DB_PATH
from agentic_rag.llm import get_client
from agentic_rag.models import MetaResponse

MAX_TURNS = 5


def _get_table_schemas(table_names: list[str]) -> str:
    engine = sa.create_engine(f"sqlite:///{SQLITE_DB_PATH}")
    inspector = sa.inspect(engine)
    schemas = []

    for table_name in table_names:
        if table_name not in inspector.get_table_names():
            continue
        columns = inspector.get_columns(table_name)
        fks = inspector.get_foreign_keys(table_name)

        col_defs = []
        for col in columns:
            col_str = f"  {col['name']} {col['type']}"
            if col.get("primary_key"):
                col_str += " PRIMARY KEY"
            if not col.get("nullable", True):
                col_str += " NOT NULL"
            col_defs.append(col_str)

        fk_defs = []
        for fk in fks:
            fk_defs.append(
                f"  FOREIGN KEY ({', '.join(fk['constrained_columns'])}) "
                f"REFERENCES {fk['referred_table']}({', '.join(fk['referred_columns'])})"
            )

        schema = f"CREATE TABLE {table_name} (\n"
        schema += ",\n".join(col_defs + fk_defs)
        schema += "\n);"
        schemas.append(schema)

    engine.dispose()
    return "\n\n".join(schemas)


def _execute_sql(query: str) -> tuple[list[dict], int]:
    engine = sa.create_engine(f"sqlite:///{SQLITE_DB_PATH}")
    with engine.connect() as conn:
        result = conn.execute(sa.text(query))
        rows = [dict(row._mapping) for row in result]
        for row in rows:
            for k, v in row.items():
                if hasattr(v, "isoformat"):
                    row[k] = v.isoformat()
    engine.dispose()
    return rows, len(rows)


def _build_tools() -> list[Tool]:
    return [Tool(function_declarations=[
        FunctionDeclaration(
            name="execute_sql",
            description="Execute a read-only SQL SELECT query against the SQLite database.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "A valid SQLite SELECT query. Must start with SELECT and include LIMIT.",
                    },
                },
                "required": ["query"],
            },
        ),
    ])]


def _build_system_prompt(schemas: str) -> str:
    return f"""You are a SQL expert. Generate and execute queries to answer the user's question.

TABLE SCHEMAS:
{schemas}

RULES:
- Only generate SELECT queries (read-only)
- Always include LIMIT {SQL_QUERY_LIMIT}
- Use proper JOINs when data spans multiple tables
- After seeing query results, evaluate whether they fully answer the question
- If results are empty or incomplete, try a different query approach (rephrase, different columns, different JOINs)
- You may run multiple queries to build a complete answer
- When you have enough data, provide a clear summary that includes all specific names, numbers, and values from the results"""


class SQLAgent(BaseAgent[SpecialistRequest, SpecialistResult]):
    name = "sql_agent"

    def run(self, req: SpecialistRequest) -> SpecialistResult:
        table_names = [req.source_name]
        schemas = _get_table_schemas(table_names)
        source_label = ", ".join(table_names)
        client = get_client()
        tools = _build_tools()
        system_prompt = _build_system_prompt(schemas)

        history: list[Content] = [
            Content(role="user", parts=[Part.from_text(text=req.question)]),
        ]
        all_rows: list[dict] = []
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
                summary = response.text.strip() if response.text else json.dumps(all_rows[:20], default=str)
                return SpecialistResult(
                    source_id=req.source_id,
                    response=MetaResponse(
                        source=source_label,
                        source_type="sql",
                        query_used="; ".join(all_queries),
                        confidence=0.9 if all_rows else 0.3,
                        summary=summary,
                        data=all_rows[:50],
                        row_count=len(all_rows),
                    ),
                    attempts=attempts,
                )

            function_response_parts = []
            for fc_part in function_calls:
                fc = fc_part.function_call
                query = fc.args.get("query", "")
                attempts += 1

                if not query.strip().upper().startswith("SELECT"):
                    result = {"error": "Only SELECT queries are allowed."}
                else:
                    try:
                        rows, count = _execute_sql(query)
                        all_rows.extend(rows)
                        all_queries.append(query)
                        result = {"rows": rows[:20], "total_count": count}
                    except Exception as e:
                        last_error = str(e)
                        result = {"error": f"Query failed: {e}"}

                function_response_parts.append(
                    Part.from_function_response(name="execute_sql", response=result)
                )

            history.append(Content(role="user", parts=function_response_parts))

        summary = json.dumps(all_rows[:20], default=str) if all_rows else f"Max turns reached. Last error: {last_error}"
        return SpecialistResult(
            source_id=req.source_id,
            response=MetaResponse(
                source=source_label,
                source_type="sql",
                query_used="; ".join(all_queries),
                confidence=0.5 if all_rows else 0.1,
                summary=summary,
                data=all_rows[:50],
                row_count=len(all_rows),
            ),
            attempts=attempts,
            error=last_error,
        )
