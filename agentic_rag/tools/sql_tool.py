"""SQL tool: generate and execute SQL queries via Gemini."""

import json

import sqlalchemy as sa

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
        # Serialize date objects to strings
        for row in rows:
            for k, v in row.items():
                if hasattr(v, "isoformat"):
                    row[k] = v.isoformat()
    engine.dispose()
    return rows, len(rows)


def query_sql(question: str, table_names: list[str]) -> MetaResponse:
    schemas = _get_table_schemas(table_names)

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

QUESTION: {question}

SQL QUERY:"""

    sql_query = generate(prompt)
    sql_query = sql_query.removeprefix("```sql").removeprefix("```").removesuffix("```").strip()

    if not sql_query.upper().startswith("SELECT"):
        return MetaResponse(
            source=", ".join(table_names),
            source_type="sql",
            query_used=sql_query,
            confidence=0.0,
            summary="Generated query was not a SELECT statement. Refused for safety.",
            data=[],
            row_count=0,
        )

    try:
        rows, count = _execute_sql(sql_query)
    except Exception as e:
        return MetaResponse(
            source=", ".join(table_names),
            source_type="sql",
            query_used=sql_query,
            confidence=0.1,
            summary=f"Query execution failed: {e}",
            data=[],
            row_count=0,
        )

    summary_prompt = f"""Given this SQL query and its results, provide a concise summary answering the original question.

QUESTION: {question}
SQL QUERY: {sql_query}
RESULTS ({count} rows): {json.dumps(rows[:20], default=str)}

Provide a 2-3 sentence summary of the findings:"""

    summary_text = generate(summary_prompt)

    return MetaResponse(
        source=", ".join(table_names),
        source_type="sql",
        query_used=sql_query,
        confidence=0.9 if count > 0 else 0.3,
        summary=summary_text,
        data=rows[:50],
        row_count=count,
    )
