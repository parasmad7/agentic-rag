# Agentic RAG

Multi-agent RAG system that autonomously queries across SQL databases, NoSQL (MongoDB), and PDFs. An orchestrator agent reasons about what information it needs, delegates to specialist agents, and adapts its strategy based on intermediate results — powered by Gemini.

## Architecture

```
User Question
      │
┌─────▼──────────────────────────────────────────────────┐
│              Orchestrator Agent                         │
│         (Gemini function-calling loop)                  │
│                                                         │
│   "I need trainer ratings"  ──▶  NoSQL Agent            │
│   "Got ratings, now need      ──▶  SQL Agent             │
│    session counts"                                      │
│   "Results conflict, check    ──▶  PDF Agent             │
│    the report"                                          │
│   "I have enough" ──▶ synthesize final answer            │
└────────┬────────────────┬────────────────┬──────────────┘
    ┌────▼────┐      ┌────▼─────┐     ┌───▼────┐
    │SQL Agent│      │NoSQL Agent│    │PDF Agent│
    │         │      │          │     │        │
    │ gen SQL │      │ gen query│     │ vector │
    │ execute │      │ execute  │     │ search │
    │ retry?  │      │ retry?   │     │ expand │
    └─────────┘      └──────────┘     └────────┘
```

### What Makes It Agentic

The orchestrator uses a **reasoning loop**, not a fixed pipeline. The LLM decides:
- **Which tools to call** — based on the question, not a hardcoded mapping
- **What sub-questions to ask** — each specialist gets a focused query, not the raw user question
- **When to stop** — the LLM decides it has enough information, not a fixed step count
- **How to adapt** — results from one agent inform queries to the next

Example: *"Are trainers with safety certifications getting better reviews?"*
1. SQL Agent → "What certifications do trainers have?" (discovers cert types)
2. PDF Agent → "What safety certifications are required?" (learns CPR/AED is the safety cert)
3. SQL Agent → "Which trainers have CPR/AED?" (uses PDF insight to refine query)
4. Synthesize → honest answer noting data gap

A fixed pipeline would send the same generic question to all sources in parallel.

## Agents

| Agent | Role | Tools |
|---|---|---|
| **Orchestrator** | Reasons about the question, delegates to specialists, adapts strategy, synthesizes | `query_sql`, `query_nosql`, `search_pdfs` (via Gemini function calling) |
| **SQL Agent** | Generates SQL, executes against SQLite, retries with error feedback | `_generate_sql`, `_execute_sql` |
| **NoSQL Agent** | Generates MongoDB queries, executes, retries with error feedback | `_generate_mongo_query`, `_execute_mongo` |
| **PDF Agent** | Vector search over chunked PDFs with small-to-big context expansion | `_search_chunks`, `_expand_context` |

## Data Sources (Gym/Fitness Domain)

| Source | Type | Description |
|---|---|---|
| `members` | SQL | Profiles, membership type, join date, status |
| `trainers` | SQL | Specialization, certification, hourly rate |
| `workout_sessions` | SQL | Session logs with member, trainer, type, calories |
| `memberships` | SQL | Billing records, plan types, monthly fees |
| `classes` | SQL | Group fitness classes, schedules, enrollment |
| `body_metrics` | SQL | Weight, body fat, BMI tracking over time |
| `nutrition_logs` | MongoDB | Daily meal logs with macro breakdowns |
| `trainer_reviews` | MongoDB | Member reviews of trainers with ratings |
| `health_assessments` | MongoDB | Periodic health assessments with vitals |
| `gym_safety_guidelines.pdf` | PDF | Equipment rules, injury protocols, emergency procedures |
| `q1_2025_fitness_report.pdf` | PDF | Quarterly report with membership growth, risks |
| `nutrition_program_guide.pdf` | PDF | Macro targets, hydration, supplements |

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

**Option A: GCP Service Account** — place your service account JSON key in the project root. Update `GCP_PROJECT` and the key filename in `agentic_rag/config.py`.

**Option B: API Key**

```bash
export GEMINI_API_KEY="your-key"
```

### Initialize Sample Data

```bash
uv run python main.py --setup
```

## Usage

### Interactive CLI

```bash
uv run python main.py
```

### Single Query

```bash
uv run python main.py --query "Are trainers with safety certifications getting better reviews?"
```

### API Server

```bash
uv run uvicorn api.app:app --reload
```

- `POST /api/query` — returns full result with agent trace
- `POST /api/query/stream` — SSE stream with `agent_call`, `agent_result`, `reasoning`, and `token` events

### Example Queries

| Query | Agent Behavior |
|---|---|
| "How many active members?" | SQL Agent (1 turn) → synthesize |
| "What is the average trainer hourly rate?" | SQL Agent (1 turn) → synthesize |
| "Which trainers have the best reviews?" | NoSQL Agent → synthesize |
| "Are trainers with safety certifications getting better reviews?" | SQL → SQL (retry) → SQL (adapt) → PDF (cross-source) → SQL (refine) → synthesize |
| "What protein intake is recommended for muscle building?" | PDF Agent → synthesize |

## Project Structure

```
agentic_rag/
├── config.py                    # Settings, paths, credentials
├── models.py                    # CatalogEntry, MetaResponse, GraphEdge
├── llm.py                       # Shared Gemini client (API key or service account)
├── agents/
│   ├── orchestrator.py          # Entry points: run_query(), run_query_stream()
│   ├── orchestrator_agent.py    # Reasoning loop with Gemini function calling
│   ├── sql_agent.py             # SQL specialist with retry
│   ├── nosql_agent.py           # NoSQL specialist with retry
│   ├── pdf_agent.py             # PDF specialist
│   ├── base.py                  # BaseAgent[InputT, OutputT] abstract class
│   └── messages.py              # Inter-agent Pydantic message types
├── catalog/
│   ├── catalog.yaml             # Metadata for all 12 sources
│   └── catalog_search.py        # Embed catalog into ChromaDB, vector search
├── knowledge_graph/
│   └── graph.py                 # NetworkX graph with 4 edge types
├── ingestion/
│   └── pdf_pipeline.py          # Hierarchical chunking → ChromaDB
├── tools/
│   ├── sql_tool.py              # Text-to-SQL → execute → MetaResponse
│   ├── nosql_tool.py            # MongoDB query gen → execute → MetaResponse
│   └── pdf_tool.py              # Vector search + context expansion
└── sample_data/
    ├── setup_sql.py             # SQLite schema + sample data
    ├── setup_mongo.py           # MongoDB collections + documents
    ├── generate_pdfs.py         # PDF generation with reportlab
    └── pdfs/                    # Generated PDFs
api/
└── app.py                       # FastAPI backend
ui/
└── src/App.tsx                  # React + Tailwind frontend
```

## Branches

- `main` — multi-agent architecture with reasoning loops
- `linear-pipeline` — original fixed-step pipeline (classify → search → rerank → expand → parallel execute → synthesize)
