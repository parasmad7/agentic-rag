# Agentic RAG

Multi-source RAG system that queries across SQL databases, NoSQL (MongoDB), and PDFs using agentic orchestration powered by Gemini. The project explores five different orchestration approaches — from a deterministic linear pipeline to fully agentic reasoning loops with vanilla Gemini function calling, CrewAI, Google ADK, and LangGraph.

## Architecture

The system has five orchestration implementations, each on its own branch:

### `linear-pipeline` — Deterministic Pipeline (No Agents)

```
User Query
    │
    ▼
┌─────────────────────┐
│  Domain Classifier   │ ▶ narrows to relevant domains
│     (Gemini)         │
└─────────┬────────────┘
          │
          ▼
┌─────────────────────┐
│ Catalog Vector Search│ ▶ top-K candidates from ChromaDB
└─────────┬────────────┘
          │
          ▼
┌─────────────────────┐
│   LLM Reranking     │ ▶ selects top-N most relevant
│   + KG Expansion    │ ▶ knowledge graph adds related sources
└─────────┬────────────┘
          │
          ▼  parallel fan-out
    ┌─────┼─────────────┐
    ▼     ▼             ▼
  SQL   NoSQL         PDF
  Tool  Tool         Search
    │     │             │
    ▼     ▼             ▼
  MetaResponse × N
          │
          ▼
┌─────────────────────┐
│    Synthesizer       │ ▶ combines all MetaResponses
│     (Gemini)         │
└─────────────────────┘
          │
          ▼
     Final Answer
```

The pipeline uses Gemini for classification, reranking, and synthesis, but the **control flow is hardcoded** — the programmer decides every step. No agents, no reasoning loop.

### `main` / `crewai` / `google-adk` / `langgraph` — Multi-Agent Architecture (4 Agents)

```
User Query
    │
    ▼
┌───────────────────────────────────────┐
│       Orchestrator Agent              │
│  (Gemini reasoning loop, max 10 turns)│
│                                       │
│  Observe → Reason → Act → Observe ... │
│                                       │
│  Tools:                               │
│  ┌───────────┐ ┌──────────┐ ┌──────┐ │
│  │ SQL Agent │ │NoSQL Agent│ │PDF   │ │
│  │ (retry +  │ │(retry +  │ │Agent │ │
│  │  refine)  │ │ refine)  │ │      │ │
│  └───────────┘ └──────────┘ └──────┘ │
└───────────────────────────────────────┘
          │
          ▼
     Final Answer (with agent trace)
```

The orchestrator LLM decides which specialist to call, inspects results, and either calls another specialist or produces the final answer. Each specialist agent has its own retry-with-error-feedback loop. The **LLM controls the flow** — it decides what to query, in what order, and when to stop.

| Branch | Framework | Orchestration Style |
|---|---|---|
| `linear-pipeline` | Gemini SDK direct | Fixed 6-stage pipeline, parallel fan-out, no agents |
| `main` | Gemini SDK function calling | 4-agent reasoning loop, no framework |
| `crewai` | CrewAI | Agent/Crew/Task with tool delegation |
| `google-adk` | Google ADK (Antigravity) | Async agent with pre-turn hooks |
| `langgraph` | LangGraph + Gemini | StateGraph with call_model ↔ execute_tools cycle |

## Key Components

| Component | Description |
|---|---|
| **Orchestrator Agent** | Gemini function-calling reasoning loop (max 10 turns) — decides which specialists to call and when to stop |
| **SQL Agent** | Generates SQL from table schemas, executes read-only, retries with error feedback |
| **NoSQL Agent** | Generates MongoDB queries from collection schemas, retries with error feedback |
| **PDF Agent** | Hybrid search (vector + BM25) over chunked PDFs with parent section context expansion |
| **Image Pipeline** | CLIP-based image extraction from PDFs, embedding, and text-to-image search |
| **Image Describer** | Gemini Vision on-demand image descriptions with disk caching |
| **Catalog** | YAML metadata registry for 12 sources with temporal context, embedded into ChromaDB |
| **Knowledge Graph** | NetworkX graph with structural, semantic, governance, and derived edges |
| **PDF Pipeline** | pdfplumber text + table extraction, LLM summaries, hierarchical chunking, cross-page table merging |
| **FastAPI Backend** | REST + SSE streaming API with static image serving |
| **React UI** | Real-time chat interface with agent trace, source cards, and image gallery with lightbox |

## Data Sources

### SQL (SQLite) — 6 tables
`members`, `trainers`, `workout_sessions`, `memberships`, `classes`, `body_metrics`

### NoSQL (MongoDB) — 3 collections
`nutrition_logs`, `trainer_reviews`, `health_assessments`

### PDF — 3 documents
`gym_safety_guidelines.pdf`, `q1_2025_fitness_report.pdf`, `nutrition_program_guide.pdf`

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
- SQLite database with 6 tables (members, trainers, classes, etc.)
- MongoDB collections (nutrition_logs, trainer_reviews, health_assessments)
- 3 sample PDFs (gym safety guidelines, Q1 fitness report, nutrition program guide)
- ChromaDB vector indices for catalog and PDF chunks
- Knowledge graph with cross-source edges

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

### Example Queries

| Query | Sources Hit |
|---|---|
| "How many active members are there?" | SQL (members, memberships) |
| "Which trainers have low ratings and why?" | SQL (trainers) + MongoDB (trainer_reviews) |
| "What is the recommended protein intake for muscle building?" | PDF (nutrition_program_guide) |
| "Are members following nutrition guidelines?" | MongoDB (nutrition_logs) + PDF (nutrition_program_guide) |
| "What percentage of classes are HIIT in Q1 2025?" | PDF (q1_2025_fitness_report) + pie chart image |
| "Show me the membership growth chart" | PDF (q1_2025_fitness_report) + bar chart image |

## Project Structure

```
agentic_rag/
├── config.py                # Settings, paths, credentials
├── models.py                # CatalogEntry, MetaResponse, GraphEdge
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
│   └── graph.py             # NetworkX graph with 4 edge types
├── ingestion/
│   ├── pdf_pipeline.py      # pdfplumber extraction, LLM summaries, hierarchical chunking → ChromaDB
│   ├── image_pipeline.py    # PyMuPDF image extraction → CLIP embedding → ChromaDB
│   └── clip_embedder.py     # OpenCLIP ViT-B-32 lazy-loaded singleton
├── tools/
│   ├── sql_tool.py          # Text-to-SQL → execute → MetaResponse
│   ├── nosql_tool.py        # MongoDB query gen → execute → MetaResponse
│   ├── pdf_tool.py          # Hybrid search (vector + BM25) + context expansion → MetaResponse
│   ├── bm25_search.py       # BM25Okapi keyword search with bigram tokenization
│   ├── image_tool.py        # CLIP text-to-image search in ChromaDB
│   └── image_describer.py   # Gemini Vision descriptions with disk caching
└── agents/
    ├── orchestrator.py      # Entry point (delegates to orchestrator_agent)
    ├── orchestrator_agent.py # Gemini function-calling reasoning loop (vanilla, no framework)
    ├── base.py              # BaseAgent abstract class with tracing
    ├── messages.py          # Pydantic message types for inter-agent communication
    ├── sql_agent.py         # SQL specialist with retry-on-error loop
    ├── nosql_agent.py       # NoSQL specialist with retry-on-error loop
    └── pdf_agent.py         # PDF specialist with vector search + context expansion
api/
└── app.py                   # FastAPI backend (REST + SSE streaming)
ui/
└── src/App.tsx              # React chat UI with pipeline visualization
```
