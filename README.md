# Agentic RAG — Single Agent

One orchestrator agent with a Gemini function-calling reasoning loop that queries across SQL, NoSQL, and PDF sources using three tool functions with code-controlled retry.

## Branch Comparison

| Branch | Framework | Style |
|---|---|---|
| [`linear-pipeline`](../../tree/linear-pipeline) | Gemini SDK direct | Fixed 6-stage pipeline, no agents |
| **[`single-agent`](../../tree/single-agent)** | **Gemini function calling** | **1 agent + 3 tools with retry** |
| [`main`](../../tree/main) | Gemini function calling | 4-agent reasoning loops + KG + cross-encoder |
| [`crewai`](../../tree/crewai) | CrewAI | Agent/Crew/Task with tool delegation |
| [`google-adk`](../../tree/google-adk) | Google ADK | Async agent with pre-turn hooks |
| [`langgraph`](../../tree/langgraph) | LangGraph + Gemini | StateGraph with call_model ↔ execute_tools cycle |

## Architecture

```
                        User Query
                            │
                            ▼
┌───────────────────────────────────────────────────┐
│              Orchestrator Agent                   │
│        (Gemini reasoning loop, max 10 turns)      │
│                                                   │
│   Observe ──▶ Reason ──▶ Act ──▶ Observe ...      │
│                    │                              │
│         ┌─────────┼──────────┐                    │
│         ▼         ▼          ▼                    │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│   │ query_sql│ │query_    │ │search_   │         │
│   │          │ │nosql     │ │pdfs      │         │
│   │ generate │ │ generate │ │ hybrid   │         │
│   │ SQL +    │ │ Mongo    │ │ search   │         │
│   │ execute  │ │ query +  │ │ (vector  │         │
│   │ (retry   │ │ execute  │ │ + BM25)  │         │
│   │  ≤3x)    │ │ (retry   │ │ + CLIP   │         │
│   │          │ │  ≤3x)    │ │ images   │         │
│   └──────────┘ └──────────┘ └──────────┘         │
│     code-        code-        no retry,           │
│     controlled   controlled   deterministic       │
│     retry        retry        retrieval            │
└───────────────────────────────────────────────────┘
                            │
                            ▼
                      Final Answer
                   (with source citations
                    and agent trace)
```

The orchestrator is the **only LLM reasoning loop**. It decides which tools to call, inspects results, and either calls more tools or produces the final answer. The tools themselves are plain functions — SQL and NoSQL tools have code-controlled retry (re-generate the query on error, up to 3 attempts), but they do **not** run their own LLM reasoning loops.

**What this branch does NOT have** (compared to `main`):
- No cross-encoder reranking of catalog candidates
- No knowledge graph expansion tool
- No multi-agent delegation — the orchestrator calls tools directly

## Key Components

| Component | File | Description |
|---|---|---|
| Orchestrator Agent | `agents/orchestrator_agent.py` | Gemini function-calling loop (max 10 turns) with 3 tool declarations |
| Orchestrator Entry | `agents/orchestrator.py` | Public API — `run_query()` and `run_query_stream()` |
| SQL Tool | `agents/sql_agent.py` | Generates SQL from table schemas, executes read-only, retries with error feedback |
| NoSQL Tool | `agents/nosql_agent.py` | Generates MongoDB queries from collection schemas, retries with error feedback |
| PDF Tool | `agents/pdf_agent.py` → `tools/pdf_tool.py` | Hybrid search (vector + BM25) with small-to-big context expansion |
| Image Pipeline | `ingestion/image_pipeline.py` | PyMuPDF image extraction from PDFs, CLIP embedding into ChromaDB |
| Image Describer | `tools/image_describer.py` | Gemini Vision on-demand descriptions with disk caching |
| BM25 Search | `tools/bm25_search.py` | BM25Okapi keyword search with bigram tokenization |
| CLIP Embedder | `ingestion/clip_embedder.py` | OpenCLIP ViT-B-32 lazy-loaded singleton for image embeddings |
| Catalog | `catalog/catalog_search.py` | YAML metadata registry for 12 sources, embedded into ChromaDB |
| PDF Pipeline | `ingestion/pdf_pipeline.py` | pdfplumber text + table extraction, LLM summaries, hierarchical chunking |
| FastAPI Backend | `api/app.py` | REST + SSE streaming API with static image serving |
| React UI | `ui/src/App.tsx` | Real-time chat interface with agent trace, source cards, and image gallery |

## Data Sources

**SQL (SQLite) — 6 tables:** `members`, `trainers`, `workout_sessions`, `memberships`, `classes`, `body_metrics`

**NoSQL (MongoDB) — 3 collections:** `nutrition_logs`, `trainer_reviews`, `health_assessments`

**PDF — 3 documents:** `gym_safety_guidelines.pdf`, `q1_2025_fitness_report.pdf`, `nutrition_program_guide.pdf`

## Setup

### Prerequisites

- Python 3.11+
- MongoDB (local or Atlas)
- GCP service account key with Vertex AI access (or `GEMINI_API_KEY`)

### Install

```bash
uv sync

# Start MongoDB (if not running)
brew services start mongodb/brew/mongodb-community
```

### Configure

**Option A: GCP Service Account**

Place your service account JSON key in the project root. Update `GCP_PROJECT` and the key filename in `agentic_rag/config.py`.

**Option B: API Key**

```bash
export GEMINI_API_KEY="your-key"
```

### Initialize Sample Data

```bash
uv run python main.py --setup
```

This creates:
- SQLite database with 6 tables
- MongoDB collections with sample documents
- 3 sample PDFs with charts and tables
- ChromaDB vector indices for catalog and PDF chunks
- CLIP image embeddings for PDF figures

## Usage

### Interactive CLI

```bash
uv run python main.py
```

### Single Query

```bash
uv run python main.py --query "Which trainers have low ratings and why?"
```

### Web UI (API + React)

```bash
# Terminal 1 — API server
uv run uvicorn api.app:app --port 8000

# Terminal 2 — UI dev server
cd ui && npm run dev
```

Open `http://localhost:5173`

## Project Structure

```
agentic_rag/
├── config.py                # Settings, paths, model config
├── models.py                # CatalogEntry, MetaResponse, ImageReference
├── llm.py                   # Shared Gemini client (API key or service account)
├── sample_data/
│   ├── setup_sql.py         # SQLite schema + sample data
│   ├── setup_mongo.py       # MongoDB collections + documents
│   ├── generate_pdfs.py     # PDF generation with reportlab
│   └── pdfs/                # Generated PDFs
├── catalog/
│   ├── catalog.yaml         # Metadata for all 12 sources
│   └── catalog_search.py    # Embed catalog into ChromaDB, vector search
├── knowledge_graph/
│   └── graph.py             # NetworkX graph (present but unused by orchestrator)
├── ingestion/
│   ├── pdf_pipeline.py      # pdfplumber extraction, LLM summaries, hierarchical chunking
│   ├── image_pipeline.py    # PyMuPDF image extraction → CLIP embedding → ChromaDB
│   └── clip_embedder.py     # OpenCLIP ViT-B-32 lazy-loaded singleton
├── tools/
│   ├── sql_tool.py          # Text-to-SQL generation + execution
│   ├── nosql_tool.py        # MongoDB query generation + execution
│   ├── pdf_tool.py          # Hybrid search (vector + BM25) + context expansion
│   ├── bm25_search.py       # BM25Okapi keyword search with bigram tokenization
│   ├── image_tool.py        # CLIP text-to-image search in ChromaDB
│   └── image_describer.py   # Gemini Vision descriptions with disk caching
└── agents/
    ├── orchestrator.py      # Entry point — run_query() and run_query_stream()
    ├── orchestrator_agent.py # Gemini function-calling reasoning loop (1 agent, 3 tools)
    ├── base.py              # BaseAgent abstract class with tracing
    ├── messages.py          # Pydantic message types (SpecialistRequest, SpecialistResult, etc.)
    ├── sql_agent.py         # SQL tool wrapper with retry-on-error loop
    ├── nosql_agent.py       # NoSQL tool wrapper with retry-on-error loop
    └── pdf_agent.py         # PDF tool wrapper (delegates to pdf_tool.search_pdfs)
api/
└── app.py                   # FastAPI backend (REST + SSE streaming)
ui/
└── src/App.tsx              # React chat UI with agent trace and image gallery
```
