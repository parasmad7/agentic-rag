"""PDF specialist agent: Gemini-controlled search loop with result validation."""

import json

from google.genai.types import (
    Content,
    FunctionDeclaration,
    GenerateContentConfig,
    Part,
    Tool,
)

from agentic_rag.agents.base import BaseAgent
from agentic_rag.agents.messages import SpecialistRequest, SpecialistResult
from agentic_rag.config import GEMINI_MODEL
from agentic_rag.llm import get_client
from agentic_rag.models import MetaResponse
from agentic_rag.tools.pdf_tool import search_pdfs

MAX_TURNS = 3


def _build_tools() -> list[Tool]:
    return [Tool(function_declarations=[
        FunctionDeclaration(
            name="search_pdf",
            description="Search a PDF document using hybrid retrieval (vector + BM25 + cross-encoder reranking). Returns text chunks and relevant images with descriptions.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "A focused search query to find relevant content in the PDF.",
                    },
                },
                "required": ["query"],
            },
        ),
    ])]


def _build_system_prompt(pdf_name: str) -> str:
    return f"""You are a document analyst searching the PDF: {pdf_name}

RULES:
- Search the PDF with focused, specific queries
- After seeing results, evaluate whether they answer the question
- If results are not relevant enough, try rephrasing your search query with different keywords
- When you have enough information, provide a clear summary with specific numbers, percentages, and details from the document
- If images (charts/graphs) are included in results, incorporate their data into your summary"""


class PDFAgent(BaseAgent[SpecialistRequest, SpecialistResult]):
    name = "pdf_agent"

    def run(self, req: SpecialistRequest) -> SpecialistResult:
        pdf_name = req.source_name
        client = get_client()
        tools = _build_tools()
        system_prompt = _build_system_prompt(pdf_name)

        history: list[Content] = [
            Content(role="user", parts=[Part.from_text(text=req.question)]),
        ]
        last_response: MetaResponse | None = None
        attempts = 0

        for turn in range(1, MAX_TURNS + 1):
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
                p for p in candidate.content.parts if p.function_call is not None
            ]

            if not function_calls:
                summary = response.text.strip() if response.text else ""
                if last_response:
                    last_response.summary = summary or last_response.summary
                    return SpecialistResult(
                        source_id=req.source_id,
                        response=last_response,
                        attempts=attempts,
                    )
                return SpecialistResult(
                    source_id=req.source_id,
                    response=MetaResponse(
                        source=pdf_name,
                        source_type="pdf",
                        query_used=req.question,
                        confidence=0.3,
                        summary=summary or "No relevant content found.",
                        data=[],
                        row_count=0,
                    ),
                    attempts=attempts,
                )

            function_response_parts = []
            for fc_part in function_calls:
                fc = fc_part.function_call
                query = fc.args.get("query", req.question)
                attempts += 1

                meta = search_pdfs(query, source_filter=[pdf_name])
                last_response = meta

                result = {
                    "source": meta.source,
                    "confidence": meta.confidence,
                    "row_count": meta.row_count,
                    "summary": meta.summary[:3000],
                    "chunks": meta.data[:5],
                }

                function_response_parts.append(
                    Part.from_function_response(name="search_pdf", response=result)
                )

            history.append(Content(role="user", parts=function_response_parts))

        if last_response:
            return SpecialistResult(
                source_id=req.source_id,
                response=last_response,
                attempts=attempts,
            )
        return SpecialistResult(
            source_id=req.source_id,
            response=MetaResponse(
                source=pdf_name,
                source_type="pdf",
                query_used=req.question,
                confidence=0.1,
                summary="Max search attempts reached.",
                data=[],
                row_count=0,
            ),
            attempts=attempts,
        )
