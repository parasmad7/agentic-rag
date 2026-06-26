# Agentic RAG — LangGraph

Multi-agent RAG system using LangGraph's StateGraph to orchestrate specialist agents across SQL, NoSQL, and PDF sources with Gemini as the reasoning backbone.

## Branches

| Branch | Framework | Style |
|---|---|---|
| [`linear-pipeline`](../../tree/linear-pipeline) | Gemini SDK direct | Fixed 6-stage pipeline, no agents |
| [`single-agent`](../../tree/single-agent) | Gemini function calling | 1 agent + 3 tools with retry |
| [`main`](../../tree/main) | Gemini function calling | 4-agent reasoning loops + KG + cross-encoder |
| [`crewai`](../../tree/crewai) | CrewAI | Agent/Crew/Task with tool delegation |
| [`google-adk`](../../tree/google-adk) | Google ADK | Async agent with pre-turn hooks |
| **[`langgraph`](../../tree/langgraph)** | **LangGraph + Gemini** | **StateGraph with call_model / execute_tools cycle** |

## Architecture

```
                          User Question
                               │
                               ▼
                       ┌──────────────┐
                       │    START     │
                       └──────┬───────┘
                              │
                              ▼
                  ┌───────────────────────┐
                  │      call_model       │
                  │  (Gemini reasoning)   │
                  │                       │
                  │  - Build system prompt │
                  │    with catalog context│
                  │  - Send messages to    │
                  │    Gemini with tools   │
                  │  - Parse response      │
                  └───────┬───────────────┘
                          │
                    ┌─────┴──────┐
                    │   router   │
                    └─────┬──────┘
               ┌──────────┼──────────┐
               │ function  │  no      │
               │ calls     │  function│
               │ present   │  calls   │
               ▼           │          ▼
  ┌────────────────────┐   │    ┌──────────┐
  │   execute_tools    │   │    │   END    │
  │                    │   │    │  (answer) │
  │ For each function  │   │    └──────────┘
  │ call, dispatch to: │   │
  │ ┌────────────────┐ │   │
  │ │   SQL Agent    │ │   │
  │ │  gen + execute │ │   │
  │ │  + retry       │ │   │
  │ ├────────────────┤ │   │
  │ │  NoSQL Agent   │ │   │
  │ │  gen + execute │ │   │
  │ │  + retry       │ │   │
  │ ├────────────────┤ │   │
  │ │   PDF Agent    │ │   │
  │ │  vector search │ │   │
  │ │  + expansion   │ │   │
  │ └────────────────┘ │   │
  └────────┬───────────┘   │
           │               │
           │  turn < 10    │
           └───────────────┘
            (back to call_model)
```

The graph has two nodes connected by conditional edges:

- **`call_model`** sends the conversation history to Gemini with tool declarations. If Gemini returns function calls, the router sends state to `execute_tools`. If it returns text, the router sends state to `END`.
- **`execute_tools`** dispatches each function call to the appropriate specialist agent, appends the results as function responses, and routes back to `call_model` (or to `END` if the turn limit is reached).

This creates a `call_model` / `execute_tools` cycle that repeats until the LLM decides it has enough information to answer.

## Key Components

| Component | File | Role |
|---|---|---|
| **AgentState** | `orchestrator_agent.py` | TypedDict holding messages, answer, trace, turn count, and pending function calls |
| **StateGraph** | `orchestrator_agent.py` | LangGraph graph with `call_model` and `execute_tools` nodes + conditional edges |
| **call_model node** | `orchestrator_agent.py` | Sends messages to Gemini, parses function calls or final text |
| **execute_tools node** | `orchestrator_agent.py` | Dispatches function calls to specialist agents, collects results |
| **router** | `orchestrator_agent.py` | Conditional edge function reading `next_action` from state |
| **SQL Agent** | `sql_agent.py` | Text-to-SQL generation, execution against SQLite, retry with error feedback |
| **NoSQL Agent** | `nosql_agent.py` | MongoDB query generation, execution, retry with error feedback |
| **PDF Agent** | `pdf_agent.py` | Vector search over chunked PDFs with small-to-big context expansion |
| **Catalog** | `catalog_search.py` | YAML metadata for all 12 sources, embedded into ChromaDB for search |
| **Knowledge Graph** | `graph.py` | NetworkX graph with structural, semantic, governance, and derived edges |

## Data Sources

All sources are in the gym/fitness domain.

**SQL (SQLite, 6 tables):** `members`, `trainers`, `workout_sessions`, `memberships`, `classes`, `body_metrics`

**NoSQL (MongoDB, 3 collections):** `nutrition_logs`, `trainer_reviews`, `health_assessments`

**PDF (3 documents):** `gym_safety_guidelines.pdf`, `q1_2025_fitness_report.pdf`, `nutrition_program_guide.pdf`

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

**Option A: GCP Service Account** -- place your service account JSON key in the project root. Update `GCP_PROJECT` and the key filename in `agentic_rag/config.py`.

**Option B: API Key**

```bash
export GEMINI_API_KEY="your-key"
```

### Initialize Sample Data

```bash
uv run python main.py --setup
```

This creates the SQLite database, populates MongoDB collections, generates PDFs, chunks and indexes PDFs into ChromaDB, and builds the source catalog.

## Usage

### Interactive CLI

```bash
uv run python main.py
```

### Single Query

```bash
uv run python main.py --query "Are trainers with safety certifications getting better reviews?"
```

### Web UI

Start the FastAPI backend and React frontend:

```bash
# API server
uv run uvicorn api.app:app --reload

# Frontend (separate terminal)
cd ui && npm install && npm run dev
```

- `POST /api/query` -- returns full result with agent trace
- `POST /api/query/stream` -- SSE stream with `stage`, `agent_call`, `agent_result`, `token`, and `done` events

## Project Structure

```
agentic_rag/
├── config.py                    # Settings, paths, credentials
├── models.py                    # CatalogEntry, MetaResponse, GraphEdge
├── llm.py                       # Shared Gemini client (API key or service account)
├── agents/
│   ├── orchestrator.py          # Entry points: run_query(), run_query_stream()
│   ├── orchestrator_agent.py    # LangGraph StateGraph + call_model / execute_tools nodes
│   ├── sql_agent.py             # SQL specialist with retry
│   ├── nosql_agent.py           # NoSQL specialist with retry
│   ├── pdf_agent.py             # PDF specialist (vector search + expansion)
│   ├── base.py                  # BaseAgent[InputT, OutputT] abstract class
│   └── messages.py              # Inter-agent Pydantic message types
├── catalog/
│   ├── catalog.yaml             # Metadata for all 12 sources
│   └── catalog_search.py        # Embed catalog into ChromaDB, vector search
├── knowledge_graph/
│   └── graph.py                 # NetworkX graph with 4 edge types
├── ingestion/
│   └── pdf_pipeline.py          # Hierarchical chunking into ChromaDB
├── tools/
│   ├── sql_tool.py              # Text-to-SQL generation + execution
│   ├── nosql_tool.py            # MongoDB query generation + execution
│   └── pdf_tool.py              # Vector search + context expansion
└── sample_data/
    ├── setup_sql.py             # SQLite schema + sample data
    ├── setup_mongo.py           # MongoDB collections + documents
    ├── generate_pdfs.py         # PDF generation with reportlab
    └── pdfs/                    # Generated PDFs
api/
└── app.py                       # FastAPI backend (query + SSE streaming)
ui/
└── src/App.tsx                  # React + Tailwind frontend
main.py                          # CLI entry point
pyproject.toml                   # Dependencies (langgraph, google-genai, etc.)
```
