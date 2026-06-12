"""Orchestrator agent: reasoning loop using Gemini function calling.

The LLM decides which specialist to call, inspects results, and either
calls another specialist or produces the final synthesized answer.
"""

import json

from google.genai import types

from agentic_rag.agents.messages import (
    OrchestratorResult,
    QueryInput,
    SpecialistRequest,
    SpecialistResult,
)
from agentic_rag.agents.nosql_agent import NoSQLAgent
from agentic_rag.agents.pdf_agent import PDFAgent
from agentic_rag.agents.sql_agent import SQLAgent
from agentic_rag.catalog.catalog_search import load_catalog, load_domains, search_catalog
from agentic_rag.config import GEMINI_MODEL
from agentic_rag.knowledge_graph.graph import build_graph, expand_sources
from agentic_rag.llm import get_client

MAX_TURNS = 10

_TOOL_DECLARATIONS = types.Tool(
    functionDeclarations=[
        types.FunctionDeclaration(
            name="query_sql",
            description="Query a SQL database table. Use for structured data: members, trainers, workout sessions, memberships, classes, body metrics.",
            parametersJsonSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "A focused question to answer from this SQL table.",
                    },
                    "table_name": {
                        "type": "string",
                        "description": "The SQL table to query.",
                        "enum": [
                            "members",
                            "trainers",
                            "workout_sessions",
                            "memberships",
                            "classes",
                            "body_metrics",
                        ],
                    },
                },
                "required": ["question", "table_name"],
            },
        ),
        types.FunctionDeclaration(
            name="query_nosql",
            description="Query a MongoDB collection. Use for semi-structured data: nutrition logs, trainer reviews, health assessments.",
            parametersJsonSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "A focused question to answer from this MongoDB collection.",
                    },
                    "collection_name": {
                        "type": "string",
                        "description": "The MongoDB collection to query.",
                        "enum": [
                            "nutrition_logs",
                            "trainer_reviews",
                            "health_assessments",
                        ],
                    },
                },
                "required": ["question", "collection_name"],
            },
        ),
        types.FunctionDeclaration(
            name="search_pdfs",
            description="Search PDF documents for policy, guidelines, or report information: gym safety guidelines, Q1 2025 fitness report, nutrition program guide.",
            parametersJsonSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "A focused question to answer from PDF documents.",
                    },
                    "pdf_name": {
                        "type": "string",
                        "description": "The PDF document to search.",
                        "enum": [
                            "gym_safety_guidelines.pdf",
                            "q1_2025_fitness_report.pdf",
                            "nutrition_program_guide.pdf",
                        ],
                    },
                },
                "required": ["question", "pdf_name"],
            },
        ),
    ]
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


def _execute_function_call(
    name: str, args: dict
) -> tuple[SpecialistResult, str]:
    """Execute a function call and return (result, source_type)."""
    if name == "query_sql":
        table_name = args["table_name"]
        agent = SQLAgent()
        req = SpecialistRequest(
            question=args["question"],
            source_id=_SOURCE_ID_MAP.get(table_name, table_name),
            source_type="sql",
            source_name=table_name,
        )
        return agent.run(req), "sql"

    elif name == "query_nosql":
        collection_name = args["collection_name"]
        agent = NoSQLAgent()
        req = SpecialistRequest(
            question=args["question"],
            source_id=_SOURCE_ID_MAP.get(collection_name, collection_name),
            source_type="nosql",
            source_name=collection_name,
        )
        return agent.run(req), "nosql"

    elif name == "search_pdfs":
        pdf_name = args["pdf_name"]
        agent = PDFAgent()
        req = SpecialistRequest(
            question=args["question"],
            source_id=_SOURCE_ID_MAP.get(pdf_name, pdf_name),
            source_type="pdf",
            source_name=pdf_name,
        )
        return agent.run(req), "pdf"

    else:
        raise ValueError(f"Unknown function: {name}")


def _result_to_function_response(
    fc: types.FunctionCall, result: SpecialistResult
) -> types.Part:
    r = result.response
    response_data = {
        "source": r.source,
        "source_type": r.source_type,
        "confidence": r.confidence,
        "row_count": r.row_count,
        "summary": r.summary[:2000],
        "attempts": result.attempts,
    }
    if result.error:
        response_data["error"] = result.error

    return types.Part(
        functionResponse=types.FunctionResponse(
            id=fc.id,
            name=fc.name,
            response=response_data,
        )
    )


from typing import TypedDict, List, Dict, Any, Literal
from langgraph.graph import StateGraph, START, END
from langchain_core.runnables import RunnableConfig
import queue
import threading

class AgentState(TypedDict):
    question: str
    messages: List[types.Content]
    answer: str
    sources_consulted: List[Dict[str, Any]]
    agent_trace: List[Dict[str, Any]]
    turn: int
    all_results: List[SpecialistResult]
    next_action: Literal["call_model", "execute_tools", "end"]
    pending_function_calls: List[types.FunctionCall]


def call_model_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    cfg = config.get("configurable", {})
    callback = cfg.get("event_callback")
    verbose = cfg.get("verbose", False)
    
    turn = state.get("turn", 0) + 1
    
    if callback:
        callback("stage", {"name": "reasoning", "turn": turn})
        
    if verbose:
        print(f"  [Orchestrator] Turn {turn}...")
        
    client = get_client()
    system_prompt = _build_system_prompt()
    config_gemini = types.GenerateContentConfig(
        system_instruction=system_prompt,
        tools=[_TOOL_DECLARATIONS],
    )
    
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=state["messages"],
        config=config_gemini,
    )
    
    function_calls = response.function_calls
    new_messages = list(state["messages"])
    
    if not function_calls:
        answer = response.text or ""
        if verbose:
            print(f"  [Orchestrator] Synthesized answer ({len(answer)} chars)")
        if callback:
            callback("stage", {"name": "synthesizing"})
            for i in range(0, len(answer), 20):
                callback("token", {"text": answer[i : i + 20]})
        return {
            "answer": answer,
            "next_action": "end",
            "turn": turn,
        }
        
    new_messages.append(response.candidates[0].content)
    
    return {
        "messages": new_messages,
        "next_action": "execute_tools",
        "turn": turn,
        "pending_function_calls": function_calls,
    }


def execute_tools_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    cfg = config.get("configurable", {})
    callback = cfg.get("event_callback")
    verbose = cfg.get("verbose", False)
    
    function_calls = state.get("pending_function_calls", [])
    turn = state.get("turn", 1)
    
    new_messages = list(state["messages"])
    all_results = list(state.get("all_results", []))
    agent_trace = list(state.get("agent_trace", []))
    
    function_response_parts = []
    
    for fc in function_calls:
        if verbose:
            print(f"  [Orchestrator] Calling {fc.name}({json.dumps(fc.args, default=str)[:100]}...)")
            
        if callback:
            callback("agent_call", {
                "tool": fc.name,
                "args": fc.args,
                "turn": turn,
            })
            
        result, _ = _execute_function_call(fc.name, fc.args)
        all_results.append(result)
        
        agent_trace.append({
            "turn": turn,
            "tool": fc.name,
            "args": fc.args,
            "source_id": result.source_id,
            "confidence": result.response.confidence,
            "row_count": result.response.row_count,
            "attempts": result.attempts,
            "error": result.error,
        })
        
        if verbose:
            r = result.response
            status = "ok" if r.confidence > 0.2 else "low confidence"
            print(f"    -> {r.row_count} results, confidence={r.confidence} ({status})")
            
        if callback:
            callback("agent_result", {
                "source": result.response.source,
                "type": result.response.source_type,
                "confidence": result.response.confidence,
                "row_count": result.response.row_count,
                "summary": result.response.summary[:300],
                "attempts": result.attempts,
            })
            
        function_response_parts.append(_result_to_function_response(fc, result))
        
    new_messages.append(
        types.Content(role="user", parts=function_response_parts)
    )
    
    if turn >= MAX_TURNS:
        next_action = "end"
        answer = "I was unable to produce a final answer within the allowed number of reasoning steps."
        if callback:
            callback("token", {"text": answer})
    else:
        next_action = "call_model"
        answer = state.get("answer", "")
        
    return {
        "messages": new_messages,
        "all_results": all_results,
        "agent_trace": agent_trace,
        "next_action": next_action,
        "answer": answer,
        "pending_function_calls": [],
    }


def router(state: AgentState) -> Literal["call_model", "execute_tools", "end"]:
    return state["next_action"]


workflow = StateGraph(AgentState)
workflow.add_node("call_model", call_model_node)
workflow.add_node("execute_tools", execute_tools_node)
workflow.add_edge(START, "call_model")
workflow.add_conditional_edges(
    "call_model",
    router,
    {
        "execute_tools": "execute_tools",
        "end": END,
    }
)
workflow.add_conditional_edges(
    "execute_tools",
    router,
    {
        "call_model": "call_model",
        "end": END,
    }
)

app = workflow.compile()


def run_agent(question: str, verbose: bool = False) -> OrchestratorResult:
    initial_state = AgentState(
        question=question,
        messages=[
            types.Content(
                role="user",
                parts=[types.Part(text=question)],
            )
        ],
        answer="",
        sources_consulted=[],
        agent_trace=[],
        turn=0,
        all_results=[],
        next_action="call_model",
        pending_function_calls=[],
    )
    
    config = {
        "configurable": {
            "verbose": verbose,
        }
    }
    
    final_state = app.invoke(initial_state, config=config)
    
    sources_consulted = [
        {
            "source": r.response.source,
            "type": r.response.source_type,
            "confidence": r.response.confidence,
            "summary": r.response.summary[:300],
            "row_count": r.response.row_count,
        }
        for r in final_state.get("all_results", [])
    ]
    
    return OrchestratorResult(
        question=final_state["question"],
        answer=final_state["answer"],
        sources_consulted=sources_consulted,
        agent_trace=final_state.get("agent_trace", []),
    )


def run_agent_stream(question: str):
    """Generator that yields SSE-formatted events as the agent reasons."""
    
    def _event(event_type: str, data: dict) -> str:
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
        
    q = queue.Queue()
    
    def callback(event_type: str, data: dict):
        q.put((event_type, data))
        
    initial_state = AgentState(
        question=question,
        messages=[
            types.Content(
                role="user",
                parts=[types.Part(text=question)],
            )
        ],
        answer="",
        sources_consulted=[],
        agent_trace=[],
        turn=0,
        all_results=[],
        next_action="call_model",
        pending_function_calls=[],
    )
    
    config = {
        "configurable": {
            "event_callback": callback,
            "verbose": False,
        }
    }
    
    def run_graph():
        try:
            final_state = app.invoke(initial_state, config=config)
            sources_consulted = [
                {
                    "source": r.response.source,
                    "type": r.response.source_type,
                    "confidence": r.response.confidence,
                    "row_count": r.response.row_count,
                }
                for r in final_state.get("all_results", [])
            ]
            q.put(("done", {
                "sources_consulted": sources_consulted,
                "turns": final_state.get("turn", 0),
            }))
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
