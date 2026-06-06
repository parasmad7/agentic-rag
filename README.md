# Agentic RAG

Scalable multi-source RAG system that queries across SQL databases, NoSQL (MongoDB), and PDFs using an agentic orchestration pipeline powered by Gemini.

## Architecture

```
User Query
    │
    ▼
┌─────────────────────┐
│   Semantic Cache     │──hit──▶ cached answer
└─────────┬───────────┘
          │ miss
          ▼
┌─────────────────────┐
│  Domain Classifier  │ ▶ narrows to relevant domains
│     (Gemini)        │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Catalog Vector Search│ ▶ searches within selected domains
│  (ChromaDB)         │ ▶ top-K candidates
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│   Schema Selector   │ ▶ LLM reranks to top-N
│   + KG Expansion    │ ▶ knowledge graph adds related sources
│     (Gemini)        │
└─────────┬───────────┘
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
│    Synthesizer      │ ▶ combines all MetaResponses
│     (Gemini)        │
└─────────────────────┘
          │
          ▼
     Final Answer
```

## Key Components

| Component | Description |
|---|---|
| **Catalog** | YAML metadata registry for all sources, embedded into ChromaDB for semantic search |
| **Knowledge Graph** | NetworkX graph with structural, semantic, governance, and derived edges connecting all sources |
| **PDF Pipeline** | Hierarchical chunking (document → section → chunk) with small-to-big retrieval |
| **SQL Tool** | Gemini generates SQL from table schemas, executes read-only with LIMIT, returns MetaResponse |
| **NoSQL Tool** | Gemini generates MongoDB queries from collection schemas, returns MetaResponse |
| **PDF Tool** | Vector search over chunked PDFs with parent section context expansion |
| **Orchestrator** | Domain classify → catalog search → KG expand → parallel fan-out → synthesize |

## Setup

### Prerequisites

- Python 3.11+
- MongoDB (local or Atlas)
- GCP service account key with Vertex AI access (or `GEMINI_API_KEY`)

### Install

```bash
# Install dependencies
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
- SQLite database with 6 tables (departments, employees, vendors, invoices, purchase_orders, line_items)
- MongoDB collections (customer_feedback, vendor_reviews, support_tickets)
- 3 sample PDFs (expense policy, Q1 financial report, vendor onboarding guide)
- ChromaDB vector indices for catalog and PDF chunks
- Knowledge graph with 19 edges across all sources

## Usage

### Interactive CLI

```bash
uv run python main.py
```

### Single Query

```bash
uv run python main.py --query "Are we paying vendors on time per policy?"
```

### Example Queries

| Query | Sources Hit |
|---|---|
| "What's our total outstanding invoice amount?" | SQL (invoices) |
| "What are customers saying about our support?" | MongoDB (customer_feedback, support_tickets) |
| "What is the approval threshold for purchases over $50K?" | PDF (expense_policy) |
| "Are we paying vendors on time per policy?" | SQL + PDF + MongoDB (cross-source) |

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
    └── orchestrator.py      # Full pipeline orchestration
```

## Scaling

The architecture is designed to scale to 10,000+ sources:

- **Catalog vector search** replaces putting all schemas in the prompt
- **Domain classification** narrows search to relevant partitions
- **Knowledge graph** auto-expands to related sources across types (SQL ↔ MongoDB ↔ PDF)
- **Parallel tool execution** via ThreadPoolExecutor
- **Hierarchical PDF chunking** with small-to-big retrieval for context preservation
