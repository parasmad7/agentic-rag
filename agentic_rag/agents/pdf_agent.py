"""PDF specialist agent: delegates to pdf_tool for text + image search."""

from agentic_rag.agents.base import BaseAgent
from agentic_rag.agents.messages import SpecialistRequest, SpecialistResult
from agentic_rag.tools.pdf_tool import search_pdfs


class PDFAgent(BaseAgent[SpecialistRequest, SpecialistResult]):
    name = "pdf_agent"

    def run(self, req: SpecialistRequest) -> SpecialistResult:
        response = search_pdfs(req.question, source_filter=[req.source_name])
        return SpecialistResult(
            source_id=req.source_id,
            response=response,
        )
