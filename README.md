# Agentic RAG — CrewAI

Multi-source RAG system using CrewAI's Agent/Crew/Task framework to orchestrate specialist agents across SQL, NoSQL, and PDF data sources.

## Branch Comparison

| Branch | Framework | Style |
|---|---|---|
| [`linear-pipeline`](../../tree/linear-pipeline) | Gemini SDK direct | Fixed 6-stage pipeline, no agents |
| [`single-agent`](../../tree/single-agent) | Gemini function calling | 1 agent + 3 tools with retry |
| [`main`](../../tree/main) | Gemini function calling | 4-agent reasoning loops + KG + cross-encoder |
| **[`crewai`](../../tree/crewai)** | **CrewAI** | **Agent/Crew/Task with tool delegation** |
| [`google-adk`](../../tree/google-adk) | Google ADK | Async agent with pre-turn hooks |
| [`langgraph`](../../tree/langgraph) | LangGraph + Gemini | StateGraph with call_model / execute_tools cycle |

## Architecture

```
User Question
     │
     ▼
┌──────────────────────────────────────────────────────────┐
│                     CrewAI Crew                          │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │            Coordinator Agent                       │  │
│  │   role: "Principal Data Analyst"                   │  │
│  │   LLM:  Gemini 2.5 Flash (via Vertex AI)          │  │
│  │                                                    │  │
│  │   Task: answer the user question by choosing       │  │
│  │         tools, retrieving facts, and synthesizing  │  │
│  └──────────┬──────────────┬──────────────┬───────────┘  │
│             │              │              │               │
│        @tool(query_sql) @tool(query_nosql) @tool(search_pdfs)
│             │              │              │               │
└─────────────┼──────────────┼──────────────┼──────────────┘
              ▼              ▼              ▼
        ┌──────────┐  ┌───────────┐  ┌──────────┐
        │ SQLAgent │  │NoSQLAgent │  │ PDFAgent │
        │ (retry)  │  │  (retry)  │  │ (vector) │
        └────┬─────┘  └─────┬─────┘  └────┬─────┘
             │              │              │
             ▼              ▼              ▼
          SQLite        MongoDB       ChromaDB
        (6 tables)   (3 collections)  (3 PDFs)
```

CrewAI's `Crew.kickoff()` drives the reasoning loop. The coordinator agent decides which `@tool`-decorated functions to call, each of which delegates to a specialist agent class. The specialist agents handle query generation, execution, and retry logic independently, then return results for the coordinator to synthesize.

## Key Components

| Component | File | Description |
|---|---|---|
| **Coordinator Agent** | `agents/orchestrator_agent.py` | CrewAI `Agent` with role/goal/backstory; owns three `@tool` functions and a `Task` |
| **Crew** | `agents/orchestrator_agent.py` | Single-agent `Crew` that calls `kickoff()` to run the reasoning loop |
| **SQL Agent** | `agents/sql_agent.py` | Generates SQL via Gemini, executes against SQLite, retries on error (up to 2 retries) |
| **NoSQL Agent** | `agents/nosql_agent.py` | Generates MongoDB queries via Gemini, executes against MongoDB, retries on error |
| **PDF Agent** | `agents/pdf_agent.py` | Vector search over ChromaDB chunks with small-to-big parent section expansion |
| **Knowledge Graph** | `knowledge_graph/graph.py` | NetworkX graph with structural, semantic, governance, and derived edges |
| **Catalog** | `catalog/catalog.yaml` | YAML registry of all 12 sources with domain tags and sample questions |
| **LLM wrapper** | `llm.py` | Shared Gemini client (Vertex AI service account or API key) |

## Data Sources

| Type | Store | Contents |
|---|---|---|
| SQL | SQLite | `members`, `trainers`, `workout_sessions`, `memberships`, `classes`, `body_metrics` |
| NoSQL | MongoDB | `nutrition_logs`, `trainer_reviews`, `health_assessments` |
| PDF | ChromaDB | `gym_safety_guidelines.pdf`, `q1_2025_fitness_report.pdf`, `nutrition_program_guide.pdf` |

## Setup

### Prerequisites

- Python 3.11+
- MongoDB (local or Atlas)
- GCP service account key with Vertex AI access (or `GEMINI_API_KEY`)

### Install

```bash
uv sync
```

Start MongoDB if not already running:

```bash
brew services start mongodb/brew/mongodb-community
```

### Configure

**Option A -- GCP Service Account (used by CrewAI's LLM wrapper)**

Place your service account JSON key in the project root. Update `GCP_PROJECT` and the key filename in `agentic_rag/config.py`.

CrewAI connects to Gemini via `LLM(model="vertex_ai/gemini-2.5-flash", ...)`, which reads `GOOGLE_APPLICATION_CREDENTIALS` from the environment.

**Option B -- API Key**

```bash
export GEMINI_API_KEY="your-key"
```

### Initialize Sample Data

```bash
uv run python main.py --setup
```

This creates:
- SQLite database with 6 tables (members, trainers, workout_sessions, memberships, classes, body_metrics)
- MongoDB collections (nutrition_logs, trainer_reviews, health_assessments)
- 3 sample PDFs (gym safety guidelines, Q1 2025 fitness report, nutrition program guide)
- ChromaDB vector indices for catalog and PDF chunks

## Usage

### Interactive CLI

```bash
uv run python main.py
```

### Single Query

```bash
uv run python main.py --query "Which trainers have the best reviews and the most sessions?"
```

### Web UI

Start the FastAPI backend and React frontend:

```bash
# Terminal 1 — API server
uv run uvicorn api.app:app --reload

# Terminal 2 — React dev server
cd ui && npm install && npm run dev
```

Open `http://localhost:5173`. The UI streams SSE events as the coordinator agent reasons through its tool calls.

## Project Structure

```
agentic_rag/
├── config.py                  # Paths, credentials, model settings
├── models.py                  # CatalogEntry, MetaResponse, GraphEdge
├── llm.py                     # Shared Gemini client (Vertex AI / API key)
├── agents/
│   ├── orchestrator.py        # Entry points: run_query, run_query_stream
│   ├── orchestrator_agent.py  # CrewAI Agent + Crew + Task + @tool definitions
│   ├── sql_agent.py           # SQL specialist (text-to-SQL with retry)
│   ├── nosql_agent.py         # NoSQL specialist (text-to-MongoDB with retry)
│   ├── pdf_agent.py           # PDF specialist (vector search + context expansion)
│   ├── base.py                # BaseAgent ABC with tracing
│   └── messages.py            # Pydantic message types (SpecialistRequest/Result)
├── tools/
│   ├── sql_tool.py            # Standalone SQL query function
│   ├── nosql_tool.py          # Standalone MongoDB query function
│   └── pdf_tool.py            # Standalone PDF search function
├── catalog/
│   ├── catalog.yaml           # Metadata registry for all 12 sources
│   └── catalog_search.py      # Embed catalog into ChromaDB, vector search
├── knowledge_graph/
│   └── graph.py               # NetworkX graph with 4 edge types (19 edges)
├── ingestion/
│   └── pdf_pipeline.py        # Hierarchical chunking → ChromaDB
└── sample_data/
    ├── setup_sql.py           # SQLite schema + seed data
    ├── setup_mongo.py         # MongoDB collections + documents
    └── generate_pdfs.py       # PDF generation with ReportLab
api/
└── app.py                     # FastAPI backend (POST /api/query, SSE streaming)
ui/
└── src/App.tsx                # React frontend with SSE event display
main.py                        # CLI entry point (--setup, --query, interactive)
pyproject.toml                 # Dependencies (crewai, litellm, google-genai, ...)
```
