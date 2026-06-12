"""Orchestrator: entry points that delegate to the multi-agent system."""

from agentic_rag.agents.orchestrator_agent import run_agent, run_agent_stream


def run_query(question: str, verbose: bool = False) -> dict:
    result = run_agent(question, verbose=verbose)
    return {
        "question": result.question,
        "answer": result.answer,
        "sources_consulted": result.sources_consulted,
        "agent_trace": result.agent_trace,
    }


def run_query_stream(question: str):
    yield from run_agent_stream(question)

