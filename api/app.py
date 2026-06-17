"""FastAPI backend for the Agentic RAG UI."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agentic_rag.agents.orchestrator import run_query, run_query_stream
from agentic_rag.config import IMAGE_DIR

app = FastAPI(title="Agentic RAG API")

app.mount("/api/images", StaticFiles(directory=str(IMAGE_DIR)), name="images")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    question: str


@app.post("/api/query")
def query(req: QueryRequest):
    result = run_query(req.question, verbose=False)
    return result


@app.post("/api/query/stream")
def query_stream(req: QueryRequest):
    return StreamingResponse(
        run_query_stream(req.question),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/health")
def health():
    return {"status": "ok"}
