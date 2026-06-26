# Agentic RAG

Multi-source RAG system that queries across SQL databases, NoSQL (MongoDB), and PDFs using agentic orchestration powered by Gemini. This project explores **six orchestration approaches** — each on its own branch — from a deterministic pipeline to fully agentic reasoning loops.

| Branch | Framework | Style |
|---|---|---|
| [`linear-pipeline`](../../tree/linear-pipeline) | Gemini SDK direct | Fixed 6-stage pipeline, no agents |
| [`single-agent`](../../tree/single-agent) | Gemini function calling | 1 agent + 3 tools with retry |
| **[`main`](../../tree/main)** | **Gemini function calling** | **4-agent reasoning loops + KG + cross-encoder** |
| [`crewai`](../../tree/crewai) | CrewAI | Agent/Crew/Task with tool delegation |
| [`google-adk`](../../tree/google-adk) | Google ADK | Async agent with pre-turn hooks |
| [`langgraph`](../../tree/langgraph) | LangGraph + Gemini | StateGraph with call_model ↔ execute_tools cycle |

> Each branch has its own README documenting its architecture.

---

## This Branch: Multi-Agent Architecture (4 Agents)

The most advanced implementation. Every agent (orchestrator + 3 specialists) has its own **Gemini function-calling reasoning loop**. The orchestrator decides which specialist to call, inspects results, and either calls another or produces the final answer. When independent tools are requested in one turn, specialists run in parallel.

```
User Query
    │
    ▼
┌──────────────────────────────────────────────────────┐
│            ORCHESTRATOR AGENT                        │
│      (Gemini reasoning loop, max 10 turns)           │
│                                                      │
│  Observe → Think → Act → Observe → Think → ...       │
│                                                      │
│  Tools:                                              │
│  ┌──────────┐ ┌───────────┐ ┌─────────┐ ┌────────┐ │
│  │SQL Agent │ │NoSQL Agent│ │PDF Agent│ │  KG    │ │
│  │(Gemini   │ │(Gemini    │ │(Gemini  │ │Expand  │ │
│  │ loop +   │ │ loop +    │ │ loop +  │ │        │ │
│  │ validate)│ │ validate) │ │reranker)│ │        │ │
│  └──────────┘ └───────────┘ └─────────┘ └────────┘ │
│       ↕              ↕             ↕                 │
│   execute_sql    execute_mongo  search_pdf           │
│                                  (hybrid +           │
│                                   cross-encoder)     │
└──────────────────────────────────────────────────────┘
          │
          ▼
     Final Answer (with agent trace + thinking)
```

### Key Components

| Component | Description |
|---|---|
| **Orchestrator Agent** | Gemini function-calling loop (max 10 turns) with thinking capture and parallel execution |
| **SQL Agent** | Generates SQL, executes, validates, reformulates if needed (max 5 turns) |
| **NoSQL Agent** | Generates MongoDB queries, executes, validates, reformulates (max 5 turns) |
| **PDF Agent** | Searches via hybrid retrieval, validates relevance, rephrases if poor (max 3 turns) |
| **Cross-Encoder Reranker** | ms-marco-MiniLM-L-6-v2 rescores hybrid search candidates (~50ms, CPU) |
| **KG Expansion** | Traverses knowledge graph (1-hop) to discover related sources |
| **Hybrid Search** | Vector (ChromaDB) + BM25 with score fusion (0.8/0.2) + cross-encoder reranking |
| **Image Pipeline** | CLIP-based image extraction from PDFs with text-to-image search |
| **Eval Framework** | 15-case suite with 6 scoring dimensions, LLM-as-judge + heuristic scorers |

## Data Sources

**SQL (SQLite)** — `members`, `trainers`, `workout_sessions`, `memberships`, `classes`, `body_metrics`

**NoSQL (MongoDB)** — `nutrition_logs`, `trainer_reviews`, `health_assessments`

**PDF** — `gym_safety_guidelines.pdf`, `q1_2025_fitness_report.pdf`, `nutrition_program_guide.pdf`

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

**Option A: GCP Service Account** — Place your service account JSON key in the project root. Update `GCP_PROJECT` and the key filename in `agentic_rag/config.py`.

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
uv run python main.py --query "Which trainers have low ratings and why?"
```

### Query with Logs

```bash
uv run python main.py --log "Are trainers with safety certifications getting better reviews?"
```

### Run Evals

```bash
uv run python main.py --eval
uv run python main.py --eval --category=multi_source
uv run python main.py --eval --case=sql_active_members,pdf_q1_risks
```

### Web UI

```bash
# Terminal 1 — API server
uv run uvicorn api.app:app --port 8000

# Terminal 2 — UI dev server
cd ui && npm run dev
```

### Example Queries

| Query | Sources Hit |
|---|---|
| "How many active members are there?" | SQL (members, memberships) |
| "Which trainers have low ratings and why?" | SQL (trainers) + MongoDB (trainer_reviews) |
| "What is the recommended protein intake for muscle building?" | PDF (nutrition_program_guide) |
| "Are members following nutrition guidelines?" | MongoDB (nutrition_logs) + PDF (nutrition_program_guide) |

## Project Structure

```
agentic_rag/
├── agents/
│   ├── orchestrator.py          # Entry point
│   ├── orchestrator_agent.py    # Orchestrator reasoning loop + KG expansion + parallel exec
│   ├── base.py                  # BaseAgent with tracing
│   ├── sql_agent.py             # SQL specialist (Gemini loop, max 5 turns)
│   ├── nosql_agent.py           # NoSQL specialist (Gemini loop, max 5 turns)
│   └── pdf_agent.py             # PDF specialist (Gemini loop, max 3 turns)
├── tools/
│   ├── sql_tool.py              # SQLite query execution
│   ├── nosql_tool.py            # MongoDB query execution
│   ├── pdf_tool.py              # Hybrid search + cross-encoder reranking
│   ├── bm25_search.py           # BM25Okapi keyword search
│   ├── image_tool.py            # CLIP text-to-image search
│   └── image_describer.py       # Gemini Vision descriptions with caching
├── ingestion/
│   ├── pdf_pipeline.py          # Text + table extraction, LLM summaries, chunking → ChromaDB
│   ├── image_pipeline.py        # PDF image extraction → CLIP embedding → ChromaDB
│   └── clip_embedder.py         # OpenCLIP ViT-B-32 singleton
├── catalog/                     # YAML metadata registry + ChromaDB vector search
├── knowledge_graph/             # NetworkX graph with 4 edge types
├── sample_data/                 # SQL, MongoDB, and PDF generators
├── config.py
├── models.py
└── llm.py
evals/
├── dataset.yaml                 # 15 eval cases across 4 categories
├── judges.py                    # Heuristic + LLM-as-judge scorers
├── runner.py                    # Eval runner
└── report.py                    # Terminal + JSON reporting
api/app.py                       # FastAPI (REST + SSE streaming)
ui/src/App.tsx                   # React chat UI
```
