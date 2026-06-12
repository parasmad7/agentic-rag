"""Orchestrator agent: reasoning loop using CrewAI."""

import json
import queue
import threading
from typing import Any, Generator

from crewai import Agent, Crew, LLM, Task
from crewai.tools import tool

from agentic_rag.agents.messages import (
    OrchestratorResult,
    SpecialistRequest,
    SpecialistResult,
)
from agentic_rag.agents.nosql_agent import NoSQLAgent
from agentic_rag.agents.pdf_agent import PDFAgent
from agentic_rag.agents.sql_agent import SQLAgent
from agentic_rag.catalog.catalog_search import load_catalog
from agentic_rag.config import (
    GCP_LOCATION,
    GCP_PROJECT,
    GEMINI_MODEL,
    SERVICE_ACCOUNT_KEY,
)

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
- Always cite which source each piece of information comes from
- If sources conflict, note the discrepancy
- If you're uncertain, mention the uncertainty
- Be specific with numbers and details from the data"""


def _run_agent_impl(
    question: str, callback: Any = None, verbose: bool = False
) -> OrchestratorResult:
    all_results = []
    agent_trace = []
    current_turn = 0

    # Define tools with @tool decorator
    @tool("query_sql")
    def query_sql_tool(question: str, table_name: str) -> str:
        """Query a SQL database table. Use for structured data: members, trainers, workout sessions, memberships, classes, body metrics.

        Args:
            question: A focused question to answer from this SQL table.
            table_name: The SQL table to query.
        """
        nonlocal current_turn
        current_turn += 1
        if callback:
            callback("stage", {"name": "reasoning", "turn": current_turn})
            callback(
                "agent_call",
                {
                    "tool": "query_sql",
                    "args": {"table_name": table_name, "question": question},
                    "turn": current_turn,
                },
            )
        if verbose:
            print(f"  [Orchestrator] Calling query_sql({table_name})...")

        agent = SQLAgent()
        req = SpecialistRequest(
            question=question,
            source_id=_SOURCE_ID_MAP.get(table_name, table_name),
            source_type="sql",
            source_name=table_name,
        )
        res = agent.run(req)

        agent_trace.append({
            "turn": current_turn,
            "tool": "query_sql",
            "args": {"table_name": table_name, "question": question},
            "source_id": res.source_id,
            "confidence": res.response.confidence,
            "row_count": res.response.row_count,
            "attempts": res.attempts,
            "error": res.error,
        })
        all_results.append(res)

        if callback:
            callback(
                "agent_result",
                {
                    "source": res.response.source,
                    "type": res.response.source_type,
                    "confidence": res.response.confidence,
                    "row_count": res.response.row_count,
                    "summary": res.response.summary[:300],
                    "attempts": res.attempts,
                },
            )

        if verbose:
            print(
                f"    -> {res.response.row_count} results, confidence={res.response.confidence}"
            )

        return json.dumps({
            "source": res.response.source,
            "source_type": res.response.source_type,
            "confidence": res.response.confidence,
            "row_count": res.response.row_count,
            "summary": res.response.summary[:2000],
            "attempts": res.attempts,
            "error": res.error,
        })

    @tool("query_nosql")
    def query_nosql_tool(question: str, collection_name: str) -> str:
        """Query a MongoDB collection. Use for semi-structured data: nutrition logs, trainer reviews, health assessments.

        Args:
            question: A focused question to answer from this MongoDB collection.
            collection_name: The MongoDB collection to query.
        """
        nonlocal current_turn
        current_turn += 1
        if callback:
            callback("stage", {"name": "reasoning", "turn": current_turn})
            callback(
                "agent_call",
                {
                    "tool": "query_nosql",
                    "args": {
                        "collection_name": collection_name,
                        "question": question,
                    },
                    "turn": current_turn,
                },
            )
        if verbose:
            print(f"  [Orchestrator] Calling query_nosql({collection_name})...")

        agent = NoSQLAgent()
        req = SpecialistRequest(
            question=question,
            source_id=_SOURCE_ID_MAP.get(collection_name, collection_name),
            source_type="nosql",
            source_name=collection_name,
        )
        res = agent.run(req)

        agent_trace.append({
            "turn": current_turn,
            "tool": "query_nosql",
            "args": {
                "collection_name": collection_name,
                "question": question,
            },
            "source_id": res.source_id,
            "confidence": res.response.confidence,
            "row_count": res.response.row_count,
            "attempts": res.attempts,
            "error": res.error,
        })
        all_results.append(res)

        if callback:
            callback(
                "agent_result",
                {
                    "source": res.response.source,
                    "type": res.response.source_type,
                    "confidence": res.response.confidence,
                    "row_count": res.response.row_count,
                    "summary": res.response.summary[:300],
                    "attempts": res.attempts,
                },
            )

        if verbose:
            print(
                f"    -> {res.response.row_count} results, confidence={res.response.confidence}"
            )

        return json.dumps({
            "source": res.response.source,
            "source_type": res.response.source_type,
            "confidence": res.response.confidence,
            "row_count": res.response.row_count,
            "summary": res.response.summary[:2000],
            "attempts": res.attempts,
            "error": res.error,
        })

    @tool("search_pdfs")
    def search_pdfs_tool(question: str, pdf_name: str) -> str:
        """Search PDF documents for policy, guidelines, or report information: gym safety guidelines, Q1 2025 fitness report, nutrition program guide.

        Args:
            question: A focused question to answer from PDF documents.
            pdf_name: The PDF document to search.
        """
        nonlocal current_turn
        current_turn += 1
        if callback:
            callback("stage", {"name": "reasoning", "turn": current_turn})
            callback(
                "agent_call",
                {
                    "tool": "search_pdfs",
                    "args": {"pdf_name": pdf_name, "question": question},
                    "turn": current_turn,
                },
            )
        if verbose:
            print(f"  [Orchestrator] Calling search_pdfs({pdf_name})...")

        agent = PDFAgent()
        req = SpecialistRequest(
            question=question,
            source_id=_SOURCE_ID_MAP.get(pdf_name, pdf_name),
            source_type="pdf",
            source_name=pdf_name,
        )
        res = agent.run(req)

        agent_trace.append({
            "turn": current_turn,
            "tool": "search_pdfs",
            "args": {"pdf_name": pdf_name, "question": question},
            "source_id": res.source_id,
            "confidence": res.response.confidence,
            "row_count": res.response.row_count,
            "attempts": res.attempts,
            "error": res.error,
        })
        all_results.append(res)

        if callback:
            callback(
                "agent_result",
                {
                    "source": res.response.source,
                    "type": res.response.source_type,
                    "confidence": res.response.confidence,
                    "row_count": res.response.row_count,
                    "summary": res.response.summary[:300],
                    "attempts": res.attempts,
                },
            )

        if verbose:
            print(
                f"    -> {res.response.row_count} results, confidence={res.response.confidence}"
            )

        return json.dumps({
            "source": res.response.source,
            "source_type": res.response.source_type,
            "confidence": res.response.confidence,
            "row_count": res.response.row_count,
            "summary": res.response.summary[:2000],
            "attempts": res.attempts,
            "error": res.error,
        })

    # Configure LLM via Vertex AI
    import os

    if SERVICE_ACCOUNT_KEY.exists():
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(SERVICE_ACCOUNT_KEY)

    llm = LLM(
        model=f"vertex_ai/{GEMINI_MODEL}",
        project=GCP_PROJECT,
        location=GCP_LOCATION,
    )

    system_prompt = _build_system_prompt()

    # Define CrewAI Coordinator Agent
    coordinator = Agent(
        role="Principal Data Analyst",
        goal="Gather data using specific specialist tools and synthesize a coherent answer.",
        backstory="You are an expert analyst at a fitness center. You have access to SQL databases, MongoDB logs, and PDF files. "
        + system_prompt,
        tools=[query_sql_tool, query_nosql_tool, search_pdfs_tool],
        llm=llm,
        verbose=verbose,
    )

    # Define Tasks
    task = Task(
        description=f"Answer the user's question: {question}. Choose the correct tools to retrieve all required facts, then compile a final answer citing the sources.",
        expected_output="A comprehensive synthesized answer citing the sources used.",
        agent=coordinator,
    )

    # Run Crew
    crew = Crew(
        agents=[coordinator],
        tasks=[task],
        verbose=verbose,
    )

    raw_result = crew.kickoff()
    answer = str(raw_result)

    if callback:
        callback("stage", {"name": "synthesizing"})
        for i in range(0, len(answer), 20):
            callback("token", {"text": answer[i : i + 20]})

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
    return _run_impl_in_thread(question, verbose=verbose)


def _run_impl_in_thread(question: str, callback: Any = None, verbose: bool = False) -> OrchestratorResult:
    res = []
    err = []

    def run():
        try:
            val = _run_agent_impl(question, callback=callback, verbose=verbose)
            res.append(val)
        except Exception as e:
            err.append(e)

    t = threading.Thread(target=run)
    t.start()
    t.join()

    if err:
        raise err[0]
    return res[0]


def run_agent_stream(question: str) -> Generator[str, None, None]:
    """Generator that yields SSE-formatted events as the agent reasons."""

    def _event(event_type: str, data: dict) -> str:
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

    q = queue.Queue()

    def callback(event_type: str, data: dict):
        q.put((event_type, data))

    def run_graph():
        try:
            final_res = _run_impl_in_thread(
                question, callback=callback, verbose=False
            )
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

    t = threading.Thread(target=run_graph)
    t.start()

    while True:
        event_type, data = q.get()
        if event_type is None:
            break
        if event_type == "error":
            raise RuntimeError(data["message"])
        yield _event(event_type, data)
