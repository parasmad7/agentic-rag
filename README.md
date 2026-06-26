# Agentic RAG -- Google ADK

Async multi-source RAG orchestrated by the Google Agent Development Kit (ADK), using pre-turn hooks for turn tracking and three specialist agents across SQL, NoSQL, and PDF data sources.

## Branch Comparison

| Branch | Framework | Style |
|---|---|---|
| [`linear-pipeline`](../../tree/linear-pipeline) | Gemini SDK direct | Fixed 6-stage pipeline, no agents |
| [`single-agent`](../../tree/single-agent) | Gemini function calling | 1 agent + 3 tools with retry |
| [`main`](../../tree/main) | Gemini function calling | 4-agent reasoning loops + KG + cross-encoder |
| [`crewai`](../../tree/crewai) | CrewAI | Agent/Crew/Task with tool delegation |
| **[`google-adk`](../../tree/google-adk)** | **Google ADK** | **Async agent with pre-turn hooks** |
| [`langgraph`](../../tree/langgraph) | LangGraph + Gemini | StateGraph with call_model / execute_tools cycle |

## Architecture

```
User Query
    |
    v
+---------------------------------------------+
|         Google ADK  Agent                    |
|  (LocalAgentConfig + GeminiConfig)           |
|                                              |
|  system prompt = catalog context + strategy  |
|                                              |
|  @hooks.pre_turn  -----> turn counter,       |
|                          SSE "reasoning"     |
|                          event               |
|                                              |
|  +--- Turn N --------------------------------|--+
|  |  LLM decides which tool(s) to call        |  |
|  |                                            |  |
|  |  query_sql() --------> SQLAgent.run()      |  |
|  |  query_nosql() -------> NoSQLAgent.run()   |  |
|  |  search_pdfs() -------> PDFAgent.run()     |  |
|  |                                            |  |
|  |  Results fed back to LLM for next turn     |  |
|  +--------------------------------------------+--+
|                  ...repeats...               |
|                                              |
|  async for token in response:                |
|      --> streamed final answer               |
+---------------------------------------------+
    |
    v
OrchestratorResult
  { answer, sources_consulted, agent_trace }
```

The ADK `Agent` manages the reasoning loop automatically. On each turn the `@hooks.pre_turn` hook fires, incrementing the turn counter and emitting an SSE event. The LLM chooses which tools to call; tool results are fed back into the next turn until the LLM produces a final answer, which is streamed token-by-token.

## Key Components

| Component | File | Description |
|---|---|---|
| **ADK Orchestrator** | `agents/orchestrator_agent.py` | Configures `Agent` with `LocalAgentConfig`, `GeminiConfig`, pre-turn hook, and three tools |
| **SQL Agent** | `agents/sql_agent.py` | Gemini generates SQL from table schemas, executes read-only with retry |
| **NoSQL Agent** | `agents/nosql_agent.py` | Gemini generates MongoDB queries from collection schemas with retry |
| **PDF Agent** | `agents/pdf_agent.py` | ChromaDB vector search with small-to-big parent-section expansion |
| **Catalog** | `catalog/catalog.yaml` | YAML metadata registry for all 12 sources across 4 domains |
| **Knowledge Graph** | `knowledge_graph/graph.py` | NetworkX graph with structural, semantic, governance, and derived edges |
| **PDF Pipeline** | `ingestion/pdf_pipeline.py` | Hierarchical chunking (document -> section -> chunk) into ChromaDB |
| **LLM Client** | `llm.py` | Shared Gemini client used by specialist agents (Vertex AI or API key) |
| **FastAPI** | `api/app.py` | REST + SSE streaming endpoints for the React UI |

## Data Sources

**SQL (SQLite, 6 tables)** -- members, trainers, workout_sessions, memberships, classes, body_metrics

**NoSQL (MongoDB, 3 collections)** -- nutrition_logs, trainer_reviews, health_assessments

**PDF (3 documents)** -- gym_safety_guidelines.pdf, q1_2025_fitness_report.pdf, nutrition_program_guide.pdf

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
- SQLite database with 6 tables (members, trainers, workout sessions, memberships, classes, body metrics)
- MongoDB collections (nutrition_logs, trainer_reviews, health_assessments)
- 3 sample PDFs (gym safety guidelines, Q1 fitness report, nutrition program guide)
- ChromaDB vector indices for catalog and PDF chunks

## Usage

### Interactive CLI

```bash
uv run python main.py
```

### Single Query

```bash
uv run python main.py --query "Which trainers have the best reviews and what classes do they teach?"
```

### Web UI

```bash
# Terminal 1: API server
uv run uvicorn api.app:app --reload

# Terminal 2: React frontend
cd ui && npm install && npm run dev
```

Open `http://localhost:5173` to use the streaming chat interface.

## Project Structure

```
agentic_rag/
  config.py                  # Paths, credentials, model settings
  models.py                  # CatalogEntry, MetaResponse, GraphEdge
  llm.py                     # Shared Gemini client (Vertex AI or API key)
  agents/
    orchestrator_agent.py    # ADK Agent + LocalAgentConfig + pre-turn hook
    orchestrator.py          # Entry points: run_query, run_query_stream
    base.py                  # BaseAgent with typed I/O and tracing
    messages.py              # Pydantic message types for inter-agent comms
    sql_agent.py             # Text-to-SQL specialist with retry
    nosql_agent.py           # MongoDB query specialist with retry
    pdf_agent.py             # Vector search + context expansion specialist
  catalog/
    catalog.yaml             # Metadata for all 12 sources
    catalog_search.py        # Embed catalog into ChromaDB, vector search
  knowledge_graph/
    graph.py                 # NetworkX graph with 4 edge types
  ingestion/
    pdf_pipeline.py          # Hierarchical chunking into ChromaDB
  tools/
    sql_tool.py              # SQL execution helpers
    nosql_tool.py            # MongoDB execution helpers
    pdf_tool.py              # PDF search helpers
  sample_data/
    setup_sql.py             # SQLite schema + sample data
    setup_mongo.py           # MongoDB collections + documents
    generate_pdfs.py         # PDF generation with reportlab
api/
  app.py                     # FastAPI backend (REST + SSE)
ui/                          # React + Tailwind chat frontend
main.py                      # CLI entry point
```
