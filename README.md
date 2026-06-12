# Agentic RAG

Multi-source RAG system that queries across SQL databases, NoSQL (MongoDB), and PDFs using agentic orchestration powered by Gemini. The project explores four different orchestration approaches — from a deterministic linear pipeline to fully agentic reasoning loops with CrewAI, Google ADK, and LangGraph.

## Architecture

The system has four orchestration implementations, each on its own branch:

### `main` / `linear-pipeline` — Deterministic Pipeline

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

### `crewai` / `google-adk` / `langgraph` — Multi-Agent Architecture

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

The orchestrator LLM decides which specialist to call, inspects results, and either calls another specialist or produces the final answer. Each specialist agent has its own retry-with-error-feedback loop.

| Branch | Framework | Orchestration Style |
|---|---|---|
| `main` / `linear-pipeline` | Gemini SDK direct | Fixed 6-stage pipeline, parallel fan-out |
| `crewai` | CrewAI | Agent/Crew/Task with tool delegation |
| `google-adk` | Google ADK (Antigravity) | Async agent with pre-turn hooks |
| `langgraph` | LangGraph + Gemini | StateGraph with call_model ↔ execute_tools cycle |

## Key Components

| Component | Description |
|---|---|
| **Catalog** | YAML metadata registry for 12 sources, embedded into ChromaDB for semantic search |
| **Knowledge Graph** | NetworkX graph with structural, semantic, governance, and derived edges |
| **PDF Pipeline** | Hierarchical chunking (document → section → chunk) with small-to-big retrieval |
| **SQL Agent/Tool** | Gemini generates SQL from table schemas, executes read-only with LIMIT |
| **NoSQL Agent/Tool** | Gemini generates MongoDB queries from collection schemas |
| **PDF Agent/Tool** | Vector search over chunked PDFs with parent section context expansion |
| **FastAPI Backend** | REST + SSE streaming API for the React frontend |
| **React UI** | Real-time chat interface with pipeline stage visualization and source cards |

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
| "What health risks have been identified?" | MongoDB (health_assessments) + PDF (gym_safety_guidelines) |

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
│   └── pdf_pipeline.py      # Hierarchical chunking → ChromaDB
├── tools/
│   ├── sql_tool.py          # Text-to-SQL → execute → MetaResponse
│   ├── nosql_tool.py        # MongoDB query gen → execute → MetaResponse
│   └── pdf_tool.py          # Vector search + context expansion → MetaResponse
└── agents/
    ├── orchestrator.py      # Entry point (delegates to orchestrator_agent on agentic branches)
    ├── base.py              # BaseAgent abstract class (agentic branches)
    ├── messages.py          # Pydantic message types (agentic branches)
    ├── sql_agent.py         # SQL specialist with retry loop (agentic branches)
    ├── nosql_agent.py       # NoSQL specialist with retry loop (agentic branches)
    ├── pdf_agent.py         # PDF specialist (agentic branches)
    └── orchestrator_agent.py # Framework-specific reasoning loop (agentic branches)
api/
└── app.py                   # FastAPI backend (REST + SSE streaming)
ui/
└── src/App.tsx              # React chat UI with pipeline visualization
```
