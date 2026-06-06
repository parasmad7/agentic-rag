"""Agentic RAG — Interactive CLI."""

import json
import sys

from agentic_rag.agents.orchestrator import run_query


def print_result(result: dict):
    print("\n" + "=" * 80)
    print("ANSWER")
    print("=" * 80)
    print(result["answer"])

    print("\n" + "-" * 80)
    print("SOURCES CONSULTED")
    print("-" * 80)
    for src in result["sources_consulted"]:
        conf_bar = "█" * int(src["confidence"] * 10) + "░" * (10 - int(src["confidence"] * 10))
        print(f"  [{src['type'].upper():5s}] {src['source']}")
        print(f"         Confidence: {conf_bar} {src['confidence']:.1f}")
        print(f"         Results: {src['row_count']} | {src['summary'][:100]}...")

    print("\n" + "-" * 80)
    print("PIPELINE")
    print("-" * 80)
    p = result["pipeline"]
    print(f"  Domains:           {p['domains']}")
    print(f"  Catalog candidates: {p['catalog_candidates']}")
    print(f"  Selected sources:  {p['selected_sources']}")
    print(f"  KG expanded:       {p['kg_expanded']}")
    print(f"  Total queried:     {p['total_queried']}")
    print()


def setup_data():
    print("Setting up sample data...")
    from agentic_rag.catalog.catalog_search import setup as setup_catalog
    from agentic_rag.ingestion.pdf_pipeline import ingest_pdfs
    from agentic_rag.sample_data.generate_pdfs import setup as setup_pdfs
    from agentic_rag.sample_data.setup_mongo import setup as setup_mongo
    from agentic_rag.sample_data.setup_sql import setup as setup_sql

    setup_sql()
    setup_mongo()
    setup_pdfs()
    ingest_pdfs()
    setup_catalog()
    print("\nAll data setup complete!\n")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--setup":
        setup_data()
        return

    if len(sys.argv) > 1 and sys.argv[1] == "--query":
        question = " ".join(sys.argv[2:])
        result = run_query(question, verbose=True)
        print_result(result)
        return

    print("=" * 80)
    print("  AGENTIC RAG — Multi-Source Intelligence")
    print("  SQL (SQLite) | NoSQL (MongoDB) | PDFs")
    print("=" * 80)
    print()
    print("Commands:")
    print("  Type a question to query across all sources")
    print("  'setup'  — Initialize/reset all sample data")
    print("  'quit'   — Exit")
    print()

    while True:
        try:
            question = input("Question: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break
        if question.lower() == "setup":
            setup_data()
            continue

        print(f"\nProcessing: {question}")
        try:
            result = run_query(question, verbose=True)
            print_result(result)
        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
