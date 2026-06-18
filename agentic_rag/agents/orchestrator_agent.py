"""Orchestrator agent: reasoning loop using raw Gemini function calling (no framework)."""

import json
import queue
import threading
import time
from pathlib import Path
from typing import Any, Generator

from google.genai.types import (
    Content,
    FunctionDeclaration,
    GenerateContentConfig,
    Part,
    ThinkingConfig,
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
from agentic_rag.knowledge_graph.graph import build_graph, expand_sources
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
        FunctionDeclaration(
            name="get_related_sources",
            description=(
                "Use the knowledge graph to discover data sources related to "
                "ones you have already queried. Returns connected sources with "
                "relationship descriptions (e.g., structural joins, semantic "
                "links, governance rules). Call this when you suspect there may "
                "be useful information in sources you haven't queried yet."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "source_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Names of sources already queried — e.g., "
                            "'trainers', 'nutrition_logs', 'gym_safety_guidelines.pdf'"
                        ),
                    },
                },
                "required": ["source_names"],
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
- ALWAYS query data sources first before drawing any conclusions. Never say "I can't" without trying.
- Break complex questions into focused sub-questions and query each data source separately
- Use focused, specific questions when calling tools — not the raw user question
- If a query returns results that inform your next step, use those results to formulate a better follow-up query
- You can call multiple tools if needed — use results from one to refine queries to another
- Cross-reference data across sources: e.g., get names from SQL, then look up those names in MongoDB
- Use get_related_sources to discover connected data sources via the knowledge graph when you need to find related information across different source types
- When you have enough information, provide a comprehensive answer citing your sources

RULES:
- If the question is unrelated to the available fitness center data sources, politely explain that you can only answer questions about the fitness center's data. Do not call any tools for off-topic questions.
- For all on-topic questions, you MUST call at least one tool before answering. Gather real data first, then analyze.
- Always cite which source each piece of information comes from
- If sources conflict, note the discrepancy
- If you're uncertain, mention the uncertainty
- Be specific with numbers and details from the data"""


_kg_graph = None


def _get_kg_graph():
    global _kg_graph
    if _kg_graph is None:
        _kg_graph = build_graph()
    return _kg_graph


def _execute_kg_expansion(source_names: list[str], verbose: bool) -> dict:
    graph = _get_kg_graph()
    source_ids = [_SOURCE_ID_MAP.get(n, n) for n in source_names]
    expanded = expand_sources(graph, source_ids, max_hops=1)

    related = []
    for node in expanded:
        if node["directly_selected"]:
            continue
        edges_desc = [
            f"{e['edge_type']}: {e['description']}"
            for e in node.get("edges", [])
        ]
        related.append({
            "source": node["name"],
            "type": node["source_type"],
            "domain": node.get("domain", ""),
            "description": node.get("description", ""),
            "relationships": edges_desc,
        })

    if verbose:
        print(f"    -> KG expanded to {len(related)} related sources")
    return {"related_sources": related}


def _execute_function_call(
    name: str, args: dict, agent_trace: list, all_results: list,
    current_turn: int, callback: Any, verbose: bool,
) -> dict:
    if callback:
        callback("agent_call", {"tool": name, "args": args, "turn": current_turn})
    if verbose:
        print(f"  [Orchestrator] Calling {name}({args})...")

    if name == "get_related_sources":
        source_names = args.get("source_names", [])
        result = _execute_kg_expansion(source_names, verbose)
        agent_trace.append({
            "turn": current_turn,
            "tool": name,
            "args": args,
            "source_id": "knowledge_graph",
            "confidence": 1.0,
            "row_count": len(result["related_sources"]),
            "attempts": 1,
            "error": None,
        })
        return result

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
        payload = {
            "source": res.response.source,
            "type": res.response.source_type,
            "confidence": res.response.confidence,
            "row_count": res.response.row_count,
            "summary": res.response.summary[:300],
            "attempts": res.attempts,
        }
        if res.response.images:
            payload["images"] = [
                {
                    "url": f"/api/images/{img.image_path}",
                    "source": img.source,
                    "description": img.description,
                    "relevance_score": img.relevance_score,
                }
                for img in res.response.images
            ]
        callback("agent_result", payload)

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
        "summary": res.response.summary[:5000],
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

        if len(function_calls) > 1:
            from concurrent.futures import ThreadPoolExecutor

            def _run_fc(fc_part):
                fc = fc_part.function_call
                return fc.name, _execute_function_call(
                    fc.name, dict(fc.args), agent_trace, all_results,
                    turn, callback, verbose,
                )

            with ThreadPoolExecutor(max_workers=len(function_calls)) as pool:
                futures = [pool.submit(_run_fc, fc_part) for fc_part in function_calls]
                ordered_results = [f.result() for f in futures]

            function_response_parts = [
                Part.from_function_response(name=name, response=result)
                for name, result in ordered_results
            ]
        else:
            fc = function_calls[0].function_call
            result = _execute_function_call(
                fc.name, dict(fc.args), agent_trace, all_results,
                turn, callback, verbose,
            )
            function_response_parts = [
                Part.from_function_response(name=fc.name, response=result)
            ]

        history.append(Content(role="user", parts=function_response_parts))
    else:
        answer = f"Reached maximum turns ({MAX_TURNS}) without a final answer."

    sources_consulted = []
    for r in all_results:
        entry = {
            "source": r.response.source,
            "type": r.response.source_type,
            "confidence": r.response.confidence,
            "summary": r.response.summary[:300],
            "row_count": r.response.row_count,
        }
        if r.response.images:
            entry["images"] = [
                {
                    "url": f"/api/images/{img.image_path}",
                    "source": img.source,
                    "description": img.description,
                    "relevance_score": img.relevance_score,
                }
                for img in r.response.images
            ]
        sources_consulted.append(entry)

    return OrchestratorResult(
        question=question,
        answer=answer,
        sources_consulted=sources_consulted,
        agent_trace=agent_trace,
    )


def run_agent(question: str, verbose: bool = False) -> OrchestratorResult:
    return _run_agent_impl(question, verbose=verbose)


def run_agent_with_logs(
    question: str, log_dir: str = "logs",
) -> OrchestratorResult:
    """Run the orchestrator with detailed per-turn logging to a JSON file."""
    from agentic_rag.config import BASE_DIR

    log_path = Path(BASE_DIR) / log_dir
    log_path.mkdir(parents=True, exist_ok=True)

    client = get_client()
    all_results: list[SpecialistResult] = []
    agent_trace: list[dict] = []
    turn_logs: list[dict] = []
    total_start = time.time()

    system_prompt = _build_system_prompt()
    tools = _build_tools()

    history: list[Content] = [
        Content(role="user", parts=[Part.from_text(text=question)]),
    ]

    print(f"\n{'='*80}")
    print(f"QUERY: {question}")
    print(f"{'='*80}\n")

    answer = ""
    for turn in range(1, MAX_TURNS + 1):
        turn_start = time.time()
        print(f"--- Turn {turn} ---")

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=history,
            config=GenerateContentConfig(
                tools=tools,
                system_instruction=system_prompt,
                thinking_config=ThinkingConfig(
                    thinking_budget=2048,
                    include_thoughts=True,
                ),
            ),
        )
        llm_elapsed = time.time() - turn_start

        candidate = response.candidates[0]
        history.append(candidate.content)

        thought_parts = [
            p.text for p in candidate.content.parts
            if p.thought and p.text
        ]
        text_parts = [
            p.text for p in candidate.content.parts
            if p.text and not p.thought
        ]
        function_calls = [
            p for p in candidate.content.parts
            if p.function_call is not None
        ]

        turn_log: dict[str, Any] = {
            "turn": turn,
            "llm_latency_s": round(llm_elapsed, 2),
            "thinking": "\n".join(thought_parts) if thought_parts else None,
            "output_text": "\n".join(text_parts) if text_parts else None,
            "function_calls": [],
            "is_final": len(function_calls) == 0,
        }

        if thought_parts:
            print(f"  Thinking ({llm_elapsed:.1f}s):")
            for t in thought_parts:
                for line in t.strip().split("\n")[:10]:
                    print(f"    {line}")
            if len(thought_parts[0].split("\n")) > 10:
                print(f"    ... ({len(thought_parts[0])} chars total)")

        if text_parts:
            print(f"  LLM reasoning ({llm_elapsed:.1f}s):")
            for t in text_parts:
                for line in t.strip().split("\n"):
                    print(f"    {line}")

        if not function_calls:
            answer = response.text.strip() if response.text else ""
            turn_log["final_answer_length"] = len(answer)
            turn_logs.append(turn_log)
            print(f"  -> Final answer ({len(answer)} chars)")
            break

        def _run_and_log(fc_part):
            fc = fc_part.function_call
            fc_args = dict(fc.args)
            print(f"  -> Calling {fc.name}({json.dumps(fc_args)})")

            tool_start = time.time()
            result = _execute_function_call(
                fc.name, fc_args, agent_trace, all_results,
                turn, None, True,
            )
            tool_elapsed = time.time() - tool_start

            fc_log = {
                "tool": fc.name,
                "args": fc_args,
                "tool_latency_s": round(tool_elapsed, 2),
                "result_source": result.get("source"),
                "result_confidence": result.get("confidence"),
                "result_row_count": result.get("row_count"),
                "result_attempts": result.get("attempts"),
                "result_error": result.get("error"),
                "result_summary": result.get("summary", "")[:500],
            }

            print(f"      source={result.get('source')}, "
                  f"confidence={result.get('confidence')}, "
                  f"rows={result.get('row_count')}, "
                  f"time={tool_elapsed:.1f}s")
            if result.get("error"):
                print(f"      ERROR: {result['error']}")

            return fc.name, result, fc_log

        if len(function_calls) > 1:
            from concurrent.futures import ThreadPoolExecutor

            with ThreadPoolExecutor(max_workers=len(function_calls)) as pool:
                futures = [pool.submit(_run_and_log, fc_part) for fc_part in function_calls]
                ordered_results = [f.result() for f in futures]

            function_response_parts = []
            for name, result, fc_log in ordered_results:
                turn_log["function_calls"].append(fc_log)
                function_response_parts.append(
                    Part.from_function_response(name=name, response=result)
                )
        else:
            name, result, fc_log = _run_and_log(function_calls[0])
            turn_log["function_calls"].append(fc_log)
            function_response_parts = [
                Part.from_function_response(name=name, response=result)
            ]

        turn_logs.append(turn_log)
        history.append(Content(role="user", parts=function_response_parts))
    else:
        answer = f"Reached maximum turns ({MAX_TURNS}) without a final answer."

    total_elapsed = time.time() - total_start

    sources_consulted = []
    for r in all_results:
        entry = {
            "source": r.response.source,
            "type": r.response.source_type,
            "confidence": r.response.confidence,
            "summary": r.response.summary[:300],
            "row_count": r.response.row_count,
        }
        if r.response.images:
            entry["images"] = [
                {
                    "url": f"/api/images/{img.image_path}",
                    "source": img.source,
                    "description": img.description,
                    "relevance_score": img.relevance_score,
                }
                for img in r.response.images
            ]
        sources_consulted.append(entry)

    orchestrator_result = OrchestratorResult(
        question=question,
        answer=answer,
        sources_consulted=sources_consulted,
        agent_trace=agent_trace,
    )

    # Write detailed log file
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    slug = question[:50].lower().replace(" ", "_").replace("?", "")
    log_file = log_path / f"{timestamp}_{slug}.json"
    log_data = {
        "question": question,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "total_latency_s": round(total_elapsed, 2),
        "total_turns": len(turn_logs),
        "total_tool_calls": sum(len(t["function_calls"]) for t in turn_logs),
        "answer": answer,
        "turns": turn_logs,
        "agent_trace": agent_trace,
        "sources_consulted": sources_consulted,
    }
    log_file.write_text(json.dumps(log_data, indent=2, default=str))

    print(f"\n{'='*80}")
    print(f"COMPLETE: {len(turn_logs)} turns, "
          f"{sum(len(t['function_calls']) for t in turn_logs)} tool calls, "
          f"{total_elapsed:.1f}s total")
    print(f"Log saved: {log_file}")
    print(f"{'='*80}\n")
    print(f"ANSWER:\n{answer}\n")

    return orchestrator_result


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

            sources_consulted = []
            for r in final_res.sources_consulted:
                entry = {
                    "source": r["source"],
                    "type": r["type"],
                    "confidence": r["confidence"],
                    "row_count": r["row_count"],
                }
                if "images" in r:
                    entry["images"] = r["images"]
                sources_consulted.append(entry)
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
