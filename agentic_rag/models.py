from __future__ import annotations

from pydantic import BaseModel


class CatalogEntry(BaseModel):
    id: str
    source_type: str  # sql | nosql | pdf
    domain: str
    name: str
    description: str
    key_fields: list[str]
    sample_questions: list[str]


class MetaResponse(BaseModel):
    source: str
    source_type: str
    query_used: str
    confidence: float
    summary: str
    data: list[dict] | None = None
    row_count: int = 0


class GraphEdge(BaseModel):
    source: str
    target: str
    edge_type: str  # structural | semantic | governance | derived | temporal
    description: str
