"""SQL specialist agent: generates and executes SQL with retry on failure."""

import json

import sqlalchemy as sa

from agentic_rag.agents.base import BaseAgent
from agentic_rag.agents.messages import SpecialistRequest, SpecialistResult
from agentic_rag.config import SQL_QUERY_LIMIT, SQLITE_DB_PATH
from agentic_rag.llm import generate
from agentic_rag.models import MetaResponse


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


def _generate_sql(question: str, schemas: str, error_context: str = "") -> str:
    error_section = ""
    if error_context:
        error_section = f"""
PREVIOUS ATTEMPT FAILED:
{error_context}
Generate a corrected query that avoids this error.

"""

    prompt = f"""You are a SQL expert. Given the following SQLite table schemas and a user question,
generate a SQL query to answer the question.

RULES:
- Return ONLY the SQL query, no explanation
- Always include LIMIT {SQL_QUERY_LIMIT}
- Use only SELECT statements (read-only)
- Use proper JOINs when data spans multiple tables
- Handle NULL values appropriately

SCHEMAS:
{schemas}
{error_section}QUESTION: {question}

SQL QUERY:"""

    sql = generate(prompt)
    return sql.removeprefix("```sql").removeprefix("```").removesuffix("```").strip()


class SQLAgent(BaseAgent[SpecialistRequest, SpecialistResult]):
    name = "sql_agent"

    def run(self, req: SpecialistRequest) -> SpecialistResult:
        table_names = [req.source_name]
        schemas = _get_table_schemas(table_names)
        source_label = ", ".join(table_names)

        last_error = None
        for attempt in range(1, req.max_retries + 2):
            error_ctx = ""
            if last_error:
                error_ctx = last_error[:500]

            sql_query = _generate_sql(req.question, schemas, error_ctx)

            if not sql_query.upper().startswith("SELECT"):
                return SpecialistResult(
                    source_id=req.source_id,
                    response=MetaResponse(
                        source=source_label,
                        source_type="sql",
                        query_used=sql_query,
                        confidence=0.0,
                        summary="Generated query was not a SELECT statement. Refused for safety.",
                        data=[],
                        row_count=0,
                    ),
                    attempts=attempt,
                    error="Not a SELECT statement",
                )

            try:
                rows, count = _execute_sql(sql_query)
                return SpecialistResult(
                    source_id=req.source_id,
                    response=MetaResponse(
                        source=source_label,
                        source_type="sql",
                        query_used=sql_query,
                        confidence=0.9 if count > 0 else 0.3,
                        summary=json.dumps(rows[:20], default=str),
                        data=rows[:50],
                        row_count=count,
                    ),
                    attempts=attempt,
                )
            except Exception as e:
                last_error = f"Query: {sql_query}\nError: {e}"
                if attempt >= req.max_retries + 1:
                    return SpecialistResult(
                        source_id=req.source_id,
                        response=MetaResponse(
                            source=source_label,
                            source_type="sql",
                            query_used=sql_query,
                            confidence=0.1,
                            summary=f"All {attempt} attempts failed: {e}",
                            data=[],
                            row_count=0,
                        ),
                        attempts=attempt,
                        error=str(e),
                    )
