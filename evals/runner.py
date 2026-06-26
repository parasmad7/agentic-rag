"""Eval runner: loads dataset, runs each case through the pipeline, judges, reports."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import yaml

from agentic_rag.agents.orchestrator import run_query
from evals.judges import Scores, judge
from evals.report import print_case_result, print_summary, save_json_report


def load_dataset(path: str | None = None) -> list[dict]:
    if path is None:
        path = str(Path(__file__).parent / "dataset.yaml")
    with open(path) as f:
        data = yaml.safe_load(f)
    return data["cases"]


def run_single(case: dict) -> dict:
    question = case["question"]
    start = time.time()
    error = None
    answer = ""
    sources_consulted: list[dict] = []
    agent_trace: list[dict] = []

    try:
        result = run_query(question, verbose=False)
        answer = result["answer"]
        sources_consulted = result["sources_consulted"]
        agent_trace = result["agent_trace"]
    except Exception as e:
        error = str(e)

    latency = time.time() - start

    scores = None
    if not error:
        try:
            scores = judge(
                question=question,
                answer=answer,
                sources_consulted=sources_consulted,
                agent_trace=agent_trace,
                expected_tools=case.get("expected_tools", []),
                expected_sources=case.get("expected_sources", []),
                expected_facts=case.get("expected_facts", []),
            )
        except Exception as e:
            error = f"Judge error: {e}"

    return {
        "case_id": case["id"],
        "question": question,
        "category": case.get("category"),
        "difficulty": case.get("difficulty"),
        "answer": answer,
        "sources_consulted": sources_consulted,
        "agent_trace": agent_trace,
        "scores": scores,
        "latency": latency,
        "error": error,
    }


def run_eval(
    dataset_path: str | None = None,
    case_ids: list[str] | None = None,
    category: str | None = None,
) -> list[dict]:
    cases = load_dataset(dataset_path)

    if case_ids:
        cases = [c for c in cases if c["id"] in case_ids]
    if category:
        cases = [c for c in cases if c.get("category") == category]

    if not cases:
        print("No eval cases matched the filter.")
        return []

    print(f"\n{'=' * 74}")
    print(f"  AGENTIC RAG EVALS — {len(cases)} cases")
    print(f"{'=' * 74}")

    results = []
    for i, case in enumerate(cases, 1):
        print(f"\n  [{i}/{len(cases)}] Running: {case['id']}")
        sys.stdout.flush()

        result = run_single(case)
        results.append(result)

        print_case_result(
            case_id=result["case_id"],
            question=result["question"],
            scores=result["scores"],
            latency=result["latency"],
            error=result.get("error"),
        )

    print_summary(results)
    report_path = save_json_report(results)
    return results
