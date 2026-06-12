"""Pydantic message types for inter-agent communication."""

from __future__ import annotations

from pydantic import BaseModel

from agentic_rag.models import MetaResponse


class QueryInput(BaseModel):
    question: str


class ResolvedSource(BaseModel):
    source_id: str
    source_type: str
    source_name: str
    description: str


class SpecialistRequest(BaseModel):
    question: str
    source_id: str
    source_type: str
    source_name: str
    max_retries: int = 2


class SpecialistResult(BaseModel):
    source_id: str
    response: MetaResponse
    attempts: int = 1
    error: str | None = None


class OrchestratorResult(BaseModel):
    question: str
    answer: str
    sources_consulted: list[dict]
    agent_trace: list[dict]
