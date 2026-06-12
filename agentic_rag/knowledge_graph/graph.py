"""Knowledge graph connecting all data sources via structural, semantic, governance, and derived edges."""

import networkx as nx

from agentic_rag.catalog.catalog_search import load_catalog
from agentic_rag.models import CatalogEntry, GraphEdge

STRUCTURAL_EDGES = [
    GraphEdge(source="sql_workout_sessions", target="sql_members", edge_type="structural", description="workout sessions reference members via member_id"),
    GraphEdge(source="sql_workout_sessions", target="sql_trainers", edge_type="structural", description="workout sessions reference trainers via trainer_id"),
    GraphEdge(source="sql_memberships", target="sql_members", edge_type="structural", description="memberships belong to members via member_id"),
    GraphEdge(source="sql_body_metrics", target="sql_members", edge_type="structural", description="body metrics recorded for members via member_id"),
    GraphEdge(source="sql_classes", target="sql_trainers", edge_type="structural", description="classes are taught by trainers via trainer_id"),
]

SEMANTIC_EDGES = [
    GraphEdge(source="sql_members", target="nosql_nutrition_logs", edge_type="semantic", description="member profiles connect to their nutrition tracking logs"),
    GraphEdge(source="sql_members", target="nosql_health_assessments", edge_type="semantic", description="member profiles connect to their periodic health assessments"),
    GraphEdge(source="sql_trainers", target="nosql_trainer_reviews", edge_type="semantic", description="trainer records connect to member reviews of their performance"),
    GraphEdge(source="sql_workout_sessions", target="nosql_nutrition_logs", edge_type="semantic", description="workout calorie burn relates to daily nutrition and calorie intake"),
    GraphEdge(source="sql_body_metrics", target="nosql_health_assessments", edge_type="semantic", description="body metric measurements overlap with health assessment measurements"),
    GraphEdge(source="sql_classes", target="pdf_q1_report", edge_type="semantic", description="Q1 report contains class attendance and capacity analysis"),
]

GOVERNANCE_EDGES = [
    GraphEdge(source="pdf_safety_guidelines", target="sql_workout_sessions", edge_type="governance", description="safety guidelines govern how workout sessions should be conducted"),
    GraphEdge(source="pdf_safety_guidelines", target="sql_classes", edge_type="governance", description="safety guidelines define class capacity limits and warm-up requirements"),
    GraphEdge(source="pdf_nutrition_guide", target="nosql_nutrition_logs", edge_type="governance", description="nutrition guide defines recommended macros and calorie targets for meal logging"),
    GraphEdge(source="pdf_safety_guidelines", target="sql_trainers", edge_type="governance", description="safety guidelines define trainer responsibilities and certification requirements"),
    GraphEdge(source="pdf_nutrition_guide", target="nosql_health_assessments", edge_type="governance", description="nutrition guide recommendations inform health assessment dietary advice"),
]

DERIVED_EDGES = [
    GraphEdge(source="pdf_q1_report", target="sql_memberships", edge_type="derived", description="Q1 report membership growth section is derived from membership billing data"),
    GraphEdge(source="pdf_q1_report", target="nosql_trainer_reviews", edge_type="derived", description="Q1 report trainer performance section is derived from member reviews"),
    GraphEdge(source="pdf_q1_report", target="sql_body_metrics", edge_type="derived", description="Q1 report health outcomes section is derived from body metric tracking data"),
]

ALL_EDGES = STRUCTURAL_EDGES + SEMANTIC_EDGES + GOVERNANCE_EDGES + DERIVED_EDGES


def build_graph(
    entries: list[CatalogEntry] | None = None,
    edges: list[GraphEdge] | None = None,
) -> nx.Graph:
    if entries is None:
        entries = load_catalog()
    if edges is None:
        edges = ALL_EDGES

    g = nx.Graph()

    for entry in entries:
        g.add_node(entry.id, **{
            "source_type": entry.source_type,
            "domain": entry.domain,
            "name": entry.name,
            "description": entry.description,
        })

    for edge in edges:
        g.add_edge(edge.source, edge.target, **{
            "edge_type": edge.edge_type,
            "description": edge.description,
        })

    return g


def expand_sources(
    graph: nx.Graph,
    selected_ids: list[str],
    max_hops: int = 2,
) -> list[dict]:
    expanded = set(selected_ids)

    for source_id in selected_ids:
        if source_id not in graph:
            continue
        for neighbor in nx.single_source_shortest_path_length(graph, source_id, cutoff=max_hops):
            expanded.add(neighbor)

    results = []
    for node_id in expanded:
        if node_id not in graph:
            continue
        node_data = dict(graph.nodes[node_id])
        edge_info = []
        for neighbor in graph.neighbors(node_id):
            if neighbor in expanded:
                edge_data = graph.edges[node_id, neighbor]
                edge_info.append({
                    "connected_to": neighbor,
                    "edge_type": edge_data["edge_type"],
                    "description": edge_data["description"],
                })
        results.append({
            "id": node_id,
            "directly_selected": node_id in selected_ids,
            **node_data,
            "edges": edge_info,
        })

    return results


def setup():
    entries = load_catalog()
    graph = build_graph(entries)
    print(f"Knowledge graph built: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
    print(f"  Structural edges: {sum(1 for _, _, d in graph.edges(data=True) if d['edge_type'] == 'structural')}")
    print(f"  Semantic edges: {sum(1 for _, _, d in graph.edges(data=True) if d['edge_type'] == 'semantic')}")
    print(f"  Governance edges: {sum(1 for _, _, d in graph.edges(data=True) if d['edge_type'] == 'governance')}")
    print(f"  Derived edges: {sum(1 for _, _, d in graph.edges(data=True) if d['edge_type'] == 'derived')}")

    print("\nExpansion test — starting from 'sql_members' (1 hop):")
    results = expand_sources(graph, ["sql_members"], max_hops=1)
    for r in results:
        marker = " *" if r["directly_selected"] else ""
        print(f"  {r['id']}{marker} ({r['source_type']}) — {len(r['edges'])} connections")


if __name__ == "__main__":
    setup()
