"""Orchestrator: domain classify → catalog search → KG expand → parallel fan-out → synthesize."""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from agentic_rag.catalog.catalog_search import load_catalog, load_domains, search_catalog
from agentic_rag.knowledge_graph.graph import build_graph, expand_sources
from agentic_rag.llm import generate, generate_stream
from agentic_rag.models import MetaResponse
from agentic_rag.tools.nosql_tool import query_nosql
from agentic_rag.tools.pdf_tool import search_pdfs
from agentic_rag.tools.sql_tool import query_sql


def _classify_domains(question: str, domains: dict[str, str]) -> list[str]:
    domain_list = "\n".join(f"- {name}: {desc}" for name, desc in domains.items())

    prompt = f"""Given the following domains and a user question, identify which domains are relevant.
Return ONLY a JSON array of domain names. Select 1-3 most relevant domains.

DOMAINS:
{domain_list}

QUESTION: {question}

RELEVANT DOMAINS (JSON array):"""

    text = generate(prompt)
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return list(domains.keys())


def _rerank_sources(question: str, candidates: list[dict]) -> list[str]:
    if len(candidates) <= 5:
        return [c["id"] for c in candidates]

    source_list = "\n".join(
        f"- {c['id']}: {c['metadata']['description']}" for c in candidates
    )

    prompt = f"""Given these data sources and a user question, select the 1-5 most relevant sources
needed to answer the question. Return ONLY a JSON array of source IDs.

SOURCES:
{source_list}

QUESTION: {question}

SELECTED SOURCE IDS (JSON array):"""

    text = generate(prompt)
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return [c["id"] for c in candidates[:5]]


def _synthesize(question: str, responses: list[MetaResponse]) -> str:
    source_summaries = []
    for r in responses:
        source_summaries.append(
            f"[Source: {r.source} ({r.source_type}) | Confidence: {r.confidence}]\n"
            f"Query: {r.query_used}\n"
            f"Summary: {r.summary}\n"
            f"Data points: {r.row_count}"
        )

    prompt = f"""You are a helpful analyst. Synthesize the following information from multiple data sources
to answer the user's question comprehensively.

RULES:
- Cite which source each piece of information comes from
- If sources conflict, note the discrepancy
- If confidence is low on any source, mention the uncertainty
- Be specific with numbers and details from the data

QUESTION: {question}

SOURCE RESULTS:
{chr(10).join(source_summaries)}

SYNTHESIZED ANSWER:"""

    return generate(prompt)


def _execute_tool(source_id: str, source_type: str, source_name: str, question: str) -> MetaResponse:
    if source_type == "sql":
        return query_sql(question, [source_name])
    elif source_type == "nosql":
        return query_nosql(question, [source_name])
    elif source_type == "pdf":
        return search_pdfs(question, [source_name])
    else:
        return MetaResponse(
            source=source_name,
            source_type=source_type,
            query_used="",
            confidence=0.0,
            summary=f"Unknown source type: {source_type}",
        )


def run_query(question: str, verbose: bool = False) -> dict:
    log = []

    # Step 1: Domain classification
    domains = load_domains()
    relevant_domains = _classify_domains(question, domains)
    log.append(f"Domains identified: {relevant_domains}")
    if verbose:
        print(f"  [1] Domains: {relevant_domains}")

    # Step 2: Catalog vector search (filtered by domain)
    candidates = search_catalog(question, top_k=10, domain_filter=relevant_domains)
    log.append(f"Catalog search returned {len(candidates)} candidates")
    if verbose:
        print(f"  [2] Catalog candidates: {[c['id'] for c in candidates]}")

    # Step 3: LLM reranking
    selected_ids = _rerank_sources(question, candidates)
    log.append(f"Reranked to: {selected_ids}")
    if verbose:
        print(f"  [3] Selected sources: {selected_ids}")

    # Step 4: Knowledge graph expansion
    catalog = load_catalog()
    graph = build_graph(catalog)
    expanded = expand_sources(graph, selected_ids, max_hops=1)
    expanded_ids = [e["id"] for e in expanded]
    kg_added = [eid for eid in expanded_ids if eid not in selected_ids]
    log.append(f"KG expansion added: {kg_added}")
    if verbose:
        print(f"  [4] KG expanded: +{kg_added}")

    # Build source lookup
    catalog_map = {e.id: e for e in catalog}

    # Step 5: Parallel tool execution
    sources_to_query = []
    for eid in expanded_ids:
        if eid in catalog_map:
            entry = catalog_map[eid]
            sources_to_query.append((eid, entry.source_type, entry.name))

    if verbose:
        print(f"  [5] Querying {len(sources_to_query)} sources in parallel...")

    responses: list[MetaResponse] = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {
            pool.submit(_execute_tool, sid, stype, sname, question): sid
            for sid, stype, sname in sources_to_query
        }
        for future in futures:
            try:
                resp = future.result(timeout=30)
                responses.append(resp)
                if verbose:
                    print(f"    ✓ {futures[future]}: {resp.row_count} results, confidence={resp.confidence}")
            except Exception as e:
                sid = futures[future]
                log.append(f"Tool execution failed for {sid}: {e}")
                if verbose:
                    print(f"    ✗ {sid}: {e}")

    # Filter out low-confidence responses
    useful_responses = [r for r in responses if r.confidence > 0.2]
    if not useful_responses:
        useful_responses = responses

    # Step 6: Synthesize
    if verbose:
        print(f"  [6] Synthesizing from {len(useful_responses)} responses...")
    answer = _synthesize(question, useful_responses)

    return {
        "question": question,
        "answer": answer,
        "sources_consulted": [
            {
                "source": r.source,
                "type": r.source_type,
                "confidence": r.confidence,
                "summary": r.summary,
                "row_count": r.row_count,
            }
            for r in useful_responses
        ],
        "pipeline": {
            "domains": relevant_domains,
            "catalog_candidates": len(candidates),
            "selected_sources": selected_ids,
            "kg_expanded": kg_added,
            "total_queried": len(sources_to_query),
        },
        "log": log,
    }


def _build_synthesis_prompt(question: str, responses: list[MetaResponse]) -> str:
    source_summaries = []
    for r in responses:
        source_summaries.append(
            f"[Source: {r.source} ({r.source_type}) | Confidence: {r.confidence}]\n"
            f"Query: {r.query_used}\n"
            f"Summary: {r.summary}\n"
            f"Data points: {r.row_count}"
        )

    return f"""You are a helpful analyst. Synthesize the following information from multiple data sources
to answer the user's question comprehensively.

RULES:
- Cite which source each piece of information comes from
- If sources conflict, note the discrepancy
- If confidence is low on any source, mention the uncertainty
- Be specific with numbers and details from the data

QUESTION: {question}

SOURCE RESULTS:
{chr(10).join(source_summaries)}

SYNTHESIZED ANSWER:"""


def run_query_stream(question: str):
    """Generator that yields SSE-formatted events as the pipeline progresses."""

    def _event(event_type: str, data: dict) -> str:
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

    # Step 1: Domain classification
    domains = load_domains()
    relevant_domains = _classify_domains(question, domains)
    yield _event("stage", {"name": "domain_classification", "domains": relevant_domains})

    # Step 2: Catalog vector search
    candidates = search_catalog(question, top_k=10, domain_filter=relevant_domains)
    yield _event("stage", {"name": "catalog_search", "candidates": len(candidates)})

    # Step 3: LLM reranking
    selected_ids = _rerank_sources(question, candidates)
    yield _event("stage", {"name": "reranking", "selected": selected_ids})

    # Step 4: Knowledge graph expansion
    catalog = load_catalog()
    graph = build_graph(catalog)
    expanded = expand_sources(graph, selected_ids, max_hops=1)
    expanded_ids = [e["id"] for e in expanded]
    kg_added = [eid for eid in expanded_ids if eid not in selected_ids]
    yield _event("stage", {"name": "kg_expansion", "added": kg_added})

    # Build source lookup
    catalog_map = {e.id: e for e in catalog}
    sources_to_query = []
    for eid in expanded_ids:
        if eid in catalog_map:
            entry = catalog_map[eid]
            sources_to_query.append((eid, entry.source_type, entry.name))

    yield _event("stage", {"name": "tool_execution", "total": len(sources_to_query)})

    # Step 5: Parallel tool execution — yield each result as it completes
    responses: list[MetaResponse] = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {
            pool.submit(_execute_tool, sid, stype, sname, question): (sid, stype, sname)
            for sid, stype, sname in sources_to_query
        }
        for future in as_completed(futures):
            sid, stype, sname = futures[future]
            try:
                resp = future.result(timeout=30)
                responses.append(resp)
                yield _event("source", {
                    "source": resp.source,
                    "type": resp.source_type,
                    "confidence": resp.confidence,
                    "summary": resp.summary[:300],
                    "row_count": resp.row_count,
                })
            except Exception:
                yield _event("source", {
                    "source": sname,
                    "type": stype,
                    "confidence": 0.0,
                    "summary": "Tool execution failed",
                    "row_count": 0,
                })

    # Filter low-confidence
    useful_responses = [r for r in responses if r.confidence > 0.2]
    if not useful_responses:
        useful_responses = responses

    # Step 6: Stream the synthesis token by token
    yield _event("stage", {"name": "synthesizing", "sources_count": len(useful_responses)})

    prompt = _build_synthesis_prompt(question, useful_responses)
    for token in generate_stream(prompt):
        yield _event("token", {"text": token})

    # Final metadata
    yield _event("done", {
        "pipeline": {
            "domains": relevant_domains,
            "catalog_candidates": len(candidates),
            "selected_sources": selected_ids,
            "kg_expanded": kg_added,
            "total_queried": len(sources_to_query),
        },
    })
