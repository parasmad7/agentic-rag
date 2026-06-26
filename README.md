# Agentic RAG -- Linear Pipeline

Deterministic 6-stage retrieval pipeline over SQL, NoSQL, and PDF sources -- no agents, no reasoning loops, just hardcoded control flow powered by Gemini.

## Branch Comparison

| Branch | Framework | Style |
|---|---|---|
| **[`linear-pipeline`](../../tree/linear-pipeline)** | **Gemini SDK direct** | **Fixed 6-stage pipeline, no agents** |
| [`single-agent`](../../tree/single-agent) | Gemini function calling | 1 agent + 3 tools with retry |
| [`main`](../../tree/main) | Gemini function calling | 4-agent reasoning loops + KG + cross-encoder |
| [`crewai`](../../tree/crewai) | CrewAI | Agent/Crew/Task with tool delegation |
| [`google-adk`](../../tree/google-adk) | Google ADK | Async agent with pre-turn hooks |
| [`langgraph`](../../tree/langgraph) | LangGraph + Gemini | StateGraph with call_model / execute_tools cycle |

## Architecture

```
User Query
    |
    v
+---------------------+
|  Domain Classifier   |  > narrows to relevant domains
|     (Gemini)         |
+---------+-----------+
          |
          v
+---------------------+
| Catalog Vector Search|  > top-K candidates from ChromaDB
+---------+-----------+
          |
          v
+---------------------+
|   LLM Reranking     |  > selects top-N most relevant
|   + KG Expansion    |  > knowledge graph adds related sources
+---------+-----------+
          |
          v  parallel fan-out
    +-----+-------------+
    v     v             v
  SQL   NoSQL         PDF
  Tool  Tool         Search
    |     |             |
    v     v             v
  MetaResponse x N
          |
          v
+---------------------+
|    Synthesizer       |  > combines all MetaResponses
|     (Gemini)         |
+---------------------+
          |
          v
     Final Answer
```

Every stage runs exactly once in sequence (fan-out is the only parallelism). Gemini is used for classification, reranking, and synthesis, but it never decides _which_ stage to run next -- the orchestrator does.

## Key Components

| Component | Description |
|---|---|
| **Orchestrator** | `agentic_rag/agents/orchestrator.py` -- fixed 6-stage pipeline with `run_query` (batch) and `run_query_stream` (SSE) |
| **Catalog** | YAML metadata for all 12 sources, embedded into ChromaDB for vector search |
| **Knowledge Graph** | NetworkX graph with structural/semantic/governance/derived edges connecting sources |
| **SQL Tool** | Gemini generates SQL from table schema, executes read-only with LIMIT, returns `MetaResponse` |
| **NoSQL Tool** | Gemini generates MongoDB aggregation pipelines from collection schema, returns `MetaResponse` |
| **PDF Tool** | Vector search over chunked PDFs with parent-section context expansion, returns `MetaResponse` |
| **PDF Pipeline** | Hierarchical chunking (document > section > chunk) with pdfplumber extraction |

## Data Sources

**SQL (SQLite, 6 tables):** members, trainers, workout_sessions, memberships, classes, body_metrics

**NoSQL (MongoDB, 3 collections):** nutrition_logs, trainer_reviews, health_assessments

**PDF (ChromaDB, 3 documents):** gym_safety_guidelines.pdf, q1_2025_fitness_report.pdf, nutrition_program_guide.pdf

All sources share a fitness-center domain with four sub-domains: member_management, training, nutrition, wellness.

## Setup

### Prerequisites

- Python 3.11+
- MongoDB (local or Atlas)
- Gemini API key _or_ GCP service account with Vertex AI access

### Install

```bash
uv sync
```

Start MongoDB if it is not already running:

```bash
brew services start mongodb/brew/mongodb-community
```

### Configure

**Option A -- API Key:**

```bash
export GEMINI_API_KEY="your-key"
```

**Option B -- GCP Service Account:**

Place the service-account JSON in the project root and update `GCP_PROJECT` / key filename in `agentic_rag/config.py`.

### Initialize Data

```bash
uv run python main.py --setup
```

This creates the SQLite database (6 tables), MongoDB collections (3), sample PDFs (3), ChromaDB vector indices for catalog + PDF chunks, and the knowledge graph.

## Usage

### Interactive CLI

```bash
uv run python main.py
```

### Single Query

```bash
uv run python main.py --query "Which members are losing weight and what are they eating?"
```

### Web UI

Start the FastAPI backend and React dev server:

```bash
# Terminal 1 -- API
uv run uvicorn api.app:app --reload

# Terminal 2 -- UI
cd ui && npm install && npm run dev
```

Open `http://localhost:5173`. The UI streams pipeline stages and tokens via SSE.

## Project Structure

```
agentic_rag/
  config.py                  # Paths, credentials, model settings
  models.py                  # CatalogEntry, MetaResponse, GraphEdge
  llm.py                     # Gemini client (API key or service account)
  agents/
    orchestrator.py           # 6-stage pipeline (run_query + run_query_stream)
  catalog/
    catalog.yaml              # Metadata for all 12 sources
    catalog_search.py         # Embed catalog into ChromaDB, vector search
  knowledge_graph/
    graph.py                  # NetworkX graph with edge-type expansion
  ingestion/
    pdf_pipeline.py           # pdfplumber extraction + hierarchical chunking
  tools/
    sql_tool.py               # Text-to-SQL -> execute -> MetaResponse
    nosql_tool.py             # MongoDB query gen -> execute -> MetaResponse
    pdf_tool.py               # Vector search + context expansion -> MetaResponse
  sample_data/
    setup_sql.py              # SQLite schema + seed data
    setup_mongo.py            # MongoDB collections + seed documents
    generate_pdfs.py          # reportlab PDF generation
    pdfs/                     # Generated sample PDFs
api/
  app.py                      # FastAPI backend (POST /api/query, /api/query/stream)
ui/                           # React + Vite + Tailwind frontend
main.py                       # CLI entry point (--setup, --query, interactive)
pyproject.toml                # Dependencies (google-genai, chromadb, pymongo, etc.)
```
