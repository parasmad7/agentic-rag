"""Eval judges: heuristic scorers + LLM-as-judge for RAG quality dimensions."""

from __future__ import annotations

import json
import re

from pydantic import BaseModel

from agentic_rag.llm import get_client
from agentic_rag.config import EVAL_JUDGE_MODEL

from google.genai.types import GenerateContentConfig, ThinkingConfig


class Scores(BaseModel):
    tool_routing: float = 0.0
    source_coverage: float = 0.0
    faithfulness: float = 0.0
    relevance: float = 0.0
    correctness: float = 0.0
    efficiency: float = 0.0


def _extract_json(text: str) -> dict:
    match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {}


# ── Heuristic judges ─────────────────────────────────────────────


def score_tool_routing(
    agent_trace: list[dict],
    expected_tools: list[str],
) -> float:
    if not expected_tools:
        return 1.0 if not agent_trace else 0.0

    tools_called = {step["tool"] for step in agent_trace}
    expected = set(expected_tools)

    if not expected:
        return 1.0

    hits = expected & tools_called
    return len(hits) / len(expected)


def score_source_coverage(
    sources_consulted: list[dict],
    expected_sources: list[str],
) -> float:
    if not expected_sources:
        return 1.0 if not sources_consulted else 0.0

    sources_hit = {s["source"] for s in sources_consulted}
    expected = set(expected_sources)
    hits = expected & sources_hit
    return len(hits) / len(expected)


def score_efficiency(
    agent_trace: list[dict],
    expected_tools: list[str],
) -> float:
    n_calls = len(agent_trace)
    n_expected = max(len(expected_tools), 1)

    if n_calls == 0 and n_expected == 0:
        return 1.0

    turns = max(step.get("turn", 1) for step in agent_trace) if agent_trace else 0

    if n_calls == 0:
        return 0.0

    ratio = n_expected / n_calls
    call_score = min(ratio, 1.0)

    turn_score = 1.0 if turns <= n_expected + 1 else max(0.0, 1.0 - (turns - n_expected - 1) * 0.2)

    return round(0.6 * call_score + 0.4 * turn_score, 3)


# ── LLM-as-judge ─────────────────────────────────────────────────

_JUDGE_PROMPT = """You are an evaluation judge for a RAG (Retrieval-Augmented Generation) system.
You will score an answer on three dimensions. Be strict but fair.

QUESTION: {question}

ANSWER: {answer}

SOURCES CONSULTED: {sources}

EXPECTED FACTS (ground truth): {expected_facts}

Score each dimension from 0.0 to 1.0:

1. **faithfulness**: Is the answer grounded in the retrieved sources? Does it avoid hallucinating facts not present in the sources? (1.0 = fully grounded, 0.0 = fabricated)

2. **relevance**: Does the answer directly address the user's question? Is it on-topic and complete? (1.0 = perfectly addresses the question, 0.0 = completely off-topic)

3. **correctness**: Does the answer contain the expected facts listed above? (1.0 = all expected facts present, 0.0 = none present)

Respond with ONLY a JSON object (no markdown, no explanation):
{{"faithfulness": 0.X, "relevance": 0.X, "correctness": 0.X}}"""


def score_with_llm(
    question: str,
    answer: str,
    sources_consulted: list[dict],
    expected_facts: list[str],
) -> dict[str, float]:
    sources_text = json.dumps(
        [
            {"source": s["source"], "type": s["type"], "summary": s.get("summary", "")[:300]}
            for s in sources_consulted
        ],
        indent=2,
    )

    prompt = _JUDGE_PROMPT.format(
        question=question,
        answer=answer[:3000],
        sources=sources_text,
        expected_facts="\n".join(f"- {f}" for f in expected_facts),
    )

    client = get_client()
    response = client.models.generate_content(
        model=EVAL_JUDGE_MODEL,
        contents=prompt,
        config=GenerateContentConfig(
            thinking_config=ThinkingConfig(thinking_budget=0),
            temperature=0.0,
        ),
    )

    parsed = _extract_json(response.text)
    return {
        "faithfulness": float(parsed.get("faithfulness", 0.0)),
        "relevance": float(parsed.get("relevance", 0.0)),
        "correctness": float(parsed.get("correctness", 0.0)),
    }


def judge(
    question: str,
    answer: str,
    sources_consulted: list[dict],
    agent_trace: list[dict],
    expected_tools: list[str],
    expected_sources: list[str],
    expected_facts: list[str],
) -> Scores:
    tool_rt = score_tool_routing(agent_trace, expected_tools)
    src_cov = score_source_coverage(sources_consulted, expected_sources)
    eff = score_efficiency(agent_trace, expected_tools)

    llm_scores = score_with_llm(question, answer, sources_consulted, expected_facts)

    return Scores(
        tool_routing=round(tool_rt, 3),
        source_coverage=round(src_cov, 3),
        faithfulness=round(llm_scores["faithfulness"], 3),
        relevance=round(llm_scores["relevance"], 3),
        correctness=round(llm_scores["correctness"], 3),
        efficiency=round(eff, 3),
    )
