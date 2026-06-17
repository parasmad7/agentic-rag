"""Orchestrator agent: reasoning loop using raw Gemini function calling (no framework)."""

import json
import queue
import threading
from typing import Any, Generator

from google.genai.types import (
    Content,
    FunctionDeclaration,
    GenerateContentConfig,
    Part,
    Tool,
)

from agentic_rag.agents.messages import (
    OrchestratorResult,
    SpecialistRequest,
    SpecialistResult,
)
from agentic_rag.agents.nosql_agent import NoSQLAgent
from agentic_rag.agents.pdf_agent import PDFAgent
from agentic_rag.agents.sql_agent import SQLAgent
from agentic_rag.catalog.catalog_search import load_catalog
from agentic_rag.llm import get_client
from agentic_rag.config import GEMINI_MODEL

MAX_TURNS = 10

_SOURCE_ID_MAP = {
    "members": "sql_members",
    "trainers": "sql_trainers",
    "workout_sessions": "sql_workout_sessions",
    "memberships": "sql_memberships",
    "classes": "sql_classes",
    "body_metrics": "sql_body_metrics",
    "nutrition_logs": "nosql_nutrition_logs",
    "trainer_reviews": "nosql_trainer_reviews",
    "health_assessments": "nosql_health_assessments",
    "gym_safety_guidelines.pdf": "pdf_safety_guidelines",
    "q1_2025_fitness_report.pdf": "pdf_q1_report",
    "nutrition_program_guide.pdf": "pdf_nutrition_guide",
}

_SQL_TABLES = [
    "members", "trainers", "workout_sessions",
    "memberships", "classes", "body_metrics",
]
_NOSQL_COLLECTIONS = [
    "nutrition_logs", "trainer_reviews", "health_assessments",
]
_PDF_NAMES = [
    "gym_safety_guidelines.pdf", "q1_2025_fitness_report.pdf",
    "nutrition_program_guide.pdf",
]


def _build_tools() -> list[Tool]:
    return [Tool(function_declarations=[
        FunctionDeclaration(
            name="query_sql",
            description=(
                "Query a SQL database table. Use for structured data: "
                "members, trainers, workout sessions, memberships, classes, body metrics."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "A focused question to answer from this SQL table.",
                    },
                    "table_name": {
                        "type": "string",
                        "description": "The SQL table to query.",
                        "enum": _SQL_TABLES,
                    },
                },
                "required": ["question", "table_name"],
            },
        ),
        FunctionDeclaration(
            name="query_nosql",
            description=(
                "Query a MongoDB collection. Use for semi-structured data: "
                "nutrition logs, trainer reviews, health assessments."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "A focused question to answer from this MongoDB collection.",
                    },
                    "collection_name": {
                        "type": "string",
                        "description": "The MongoDB collection to query.",
                        "enum": _NOSQL_COLLECTIONS,
                    },
                },
                "required": ["question", "collection_name"],
            },
        ),
        FunctionDeclaration(
            name="search_pdfs",
            description=(
                "Search PDF documents for policy, guidelines, or report information: "
                "gym safety guidelines, Q1 2025 fitness report, nutrition program guide."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "A focused question to answer from PDF documents.",
                    },
                    "pdf_name": {
                        "type": "string",
                        "description": "The PDF document to search.",
                        "enum": _PDF_NAMES,
                    },
                },
                "required": ["question", "pdf_name"],
            },
        ),
    ])]


def _build_catalog_context() -> str:
    catalog = load_catalog()
    lines = []
    for entry in catalog:
        lines.append(
            f"- {entry.name} ({entry.source_type}, domain: {entry.domain}): "
            f"{entry.description}"
        )
    return "\n".join(lines)


def _build_system_prompt() -> str:
    catalog_context = _build_catalog_context()

    return f"""You are an intelligent data analyst with access to multiple data sources in a fitness center.
Your job is to answer user questions by querying the right sources and synthesizing results.

AVAILABLE DATA SOURCES:
{catalog_context}

STRATEGY:
- Think about what information you need before making any queries
- Use focused, specific questions when calling tools — not the raw user question
- If a query returns results that inform your next step, use those results to formulate a better follow-up query
- You can call multiple tools if needed — use results from one to refine queries to another
- When you have enough information, provide a comprehensive answer citing your sources

RULES:
- If the question is unrelated to the available fitness center data sources, politely explain that you can only answer questions about the fitness center's data. Do not call any tools for off-topic questions.
- Always cite which source each piece of information comes from
- If sources conflict, note the discrepancy
- If you're uncertain, mention the uncertainty
- Be specific with numbers and details from the data"""


def _execute_function_call(
    name: str, args: dict, agent_trace: list, all_results: list,
    current_turn: int, callback: Any, verbose: bool,
) -> dict:
    if callback:
        callback("agent_call", {"tool": name, "args": args, "turn": current_turn})
    if verbose:
        print(f"  [Orchestrator] Calling {name}({args})...")

    if name == "query_sql":
        agent = SQLAgent()
        req = SpecialistRequest(
            question=args["question"],
            source_id=_SOURCE_ID_MAP.get(args["table_name"], args["table_name"]),
            source_type="sql",
            source_name=args["table_name"],
        )
    elif name == "query_nosql":
        agent = NoSQLAgent()
        req = SpecialistRequest(
            question=args["question"],
            source_id=_SOURCE_ID_MAP.get(args["collection_name"], args["collection_name"]),
            source_type="nosql",
            source_name=args["collection_name"],
        )
    elif name == "search_pdfs":
        agent = PDFAgent()
        req = SpecialistRequest(
            question=args["question"],
            source_id=_SOURCE_ID_MAP.get(args["pdf_name"], args["pdf_name"]),
            source_type="pdf",
            source_name=args["pdf_name"],
        )
    else:
        return {"error": f"Unknown tool: {name}"}

    res: SpecialistResult = agent.run(req)

    agent_trace.append({
        "turn": current_turn,
        "tool": name,
        "args": args,
        "source_id": res.source_id,
        "confidence": res.response.confidence,
        "row_count": res.response.row_count,
        "attempts": res.attempts,
        "error": res.error,
    })
    all_results.append(res)

    if callback:
        callback("agent_result", {
            "source": res.response.source,
            "type": res.response.source_type,
            "confidence": res.response.confidence,
            "row_count": res.response.row_count,
            "summary": res.response.summary[:300],
            "attempts": res.attempts,
        })

    if verbose:
        print(
            f"    -> {res.response.row_count} results, "
            f"confidence={res.response.confidence}"
        )

    return {
        "source": res.response.source,
        "source_type": res.response.source_type,
        "confidence": res.response.confidence,
        "row_count": res.response.row_count,
        "summary": res.response.summary[:2000],
        "attempts": res.attempts,
        "error": res.error,
    }


def _run_agent_impl(
    question: str, callback: Any = None, verbose: bool = False,
) -> OrchestratorResult:
    client = get_client()
    all_results: list[SpecialistResult] = []
    agent_trace: list[dict] = []

    system_prompt = _build_system_prompt()
    tools = _build_tools()

    history: list[Content] = [
        Content(role="user", parts=[Part.from_text(text=question)]),
    ]

    for turn in range(1, MAX_TURNS + 1):
        if callback:
            callback("stage", {"name": "reasoning", "turn": turn})
        if verbose:
            print(f"  [Orchestrator] Turn {turn}...")

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
            p for p in candidate.content.parts
            if p.function_call is not None
        ]

        if not function_calls:
            answer = response.text.strip() if response.text else ""
            break

        function_response_parts = []
        for fc_part in function_calls:
            fc = fc_part.function_call
            result = _execute_function_call(
                fc.name, dict(fc.args), agent_trace, all_results,
                turn, callback, verbose,
            )
            function_response_parts.append(
                Part.from_function_response(
                    name=fc.name,
                    response=result,
                )
            )

        history.append(Content(role="user", parts=function_response_parts))
    else:
        answer = f"Reached maximum turns ({MAX_TURNS}) without a final answer."

    sources_consulted = [
        {
            "source": r.response.source,
            "type": r.response.source_type,
            "confidence": r.response.confidence,
            "summary": r.response.summary[:300],
            "row_count": r.response.row_count,
        }
        for r in all_results
    ]

    return OrchestratorResult(
        question=question,
        answer=answer,
        sources_consulted=sources_consulted,
        agent_trace=agent_trace,
    )


def run_agent(question: str, verbose: bool = False) -> OrchestratorResult:
    return _run_agent_impl(question, verbose=verbose)


def run_agent_stream(question: str) -> Generator[str, None, None]:
    """Generator that yields SSE-formatted events as the agent reasons."""

    def _event(event_type: str, data: dict) -> str:
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

    q: queue.Queue = queue.Queue()

    def callback(event_type: str, data: dict):
        q.put((event_type, data))

    def run_agent_thread():
        try:
            final_res = _run_agent_impl(
                question, callback=callback, verbose=False,
            )

            # Stream the answer token-by-token
            callback("stage", {"name": "synthesizing"})
            chunk_size = 20
            for i in range(0, len(final_res.answer), chunk_size):
                callback("token", {"text": final_res.answer[i:i + chunk_size]})

            sources_consulted = [
                {
                    "source": r["source"],
                    "type": r["type"],
                    "confidence": r["confidence"],
                    "row_count": r["row_count"],
                }
                for r in final_res.sources_consulted
            ]
            q.put((
                "done",
                {
                    "sources_consulted": sources_consulted,
                    "turns": len(final_res.agent_trace),
                },
            ))
        except Exception as e:
            q.put(("error", {"message": str(e)}))
        finally:
            q.put((None, None))

    t = threading.Thread(target=run_agent_thread)
    t.start()

    while True:
        event_type, data = q.get()
        if event_type is None:
            break
        if event_type == "error":
            raise RuntimeError(data["message"])
        yield _event(event_type, data)
