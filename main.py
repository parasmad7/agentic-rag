"""Agentic RAG — Interactive CLI."""

import sys

from agentic_rag.agents.orchestrator import run_query, run_query_logged


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

    if "agent_trace" in result and result["agent_trace"]:
        print("\n" + "-" * 80)
        print("AGENT TRACE")
        print("-" * 80)
        for step in result["agent_trace"]:
            status = "ok" if step.get("confidence", 0) > 0.2 else "low"
            print(
                f"  Turn {step['turn']}: {step['tool']}({step['source_id']}) "
                f"-> {step['row_count']} results, confidence={step['confidence']} [{status}]"
                + (f" (retried {step['attempts']}x)" if step["attempts"] > 1 else "")
            )
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

    if len(sys.argv) > 1 and sys.argv[1] == "--log":
        question = " ".join(sys.argv[2:])
        run_query_logged(question)
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
