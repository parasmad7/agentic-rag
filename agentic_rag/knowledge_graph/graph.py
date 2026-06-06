"""Knowledge graph connecting all data sources via structural, semantic, and governance edges."""

import networkx as nx

from agentic_rag.catalog.catalog_search import load_catalog
from agentic_rag.models import CatalogEntry, GraphEdge

STRUCTURAL_EDGES = [
    GraphEdge(source="sql_invoices", target="sql_vendors", edge_type="structural", description="invoices reference vendors via vendor_id"),
    GraphEdge(source="sql_purchase_orders", target="sql_vendors", edge_type="structural", description="purchase orders reference vendors via vendor_id"),
    GraphEdge(source="sql_purchase_orders", target="sql_employees", edge_type="structural", description="purchase orders reference employees via requester_id"),
    GraphEdge(source="sql_line_items", target="sql_purchase_orders", edge_type="structural", description="line items belong to purchase orders"),
    GraphEdge(source="sql_employees", target="sql_departments", edge_type="structural", description="employees belong to departments"),
]

SEMANTIC_EDGES = [
    GraphEdge(source="sql_vendors", target="nosql_vendor_reviews", edge_type="semantic", description="vendor master data connects to vendor performance reviews"),
    GraphEdge(source="sql_invoices", target="nosql_vendor_reviews", edge_type="semantic", description="invoice payment history relates to vendor performance feedback"),
    GraphEdge(source="nosql_customer_feedback", target="nosql_support_tickets", edge_type="semantic", description="customer feedback often references issues tracked in support tickets"),
    GraphEdge(source="sql_invoices", target="nosql_support_tickets", edge_type="semantic", description="billing-related support tickets reference invoice data"),
    GraphEdge(source="sql_employees", target="nosql_support_tickets", edge_type="semantic", description="support tickets are assigned to employees"),
    GraphEdge(source="sql_departments", target="pdf_q1_report", edge_type="semantic", description="Q1 report contains department budget vs actual analysis"),
]

GOVERNANCE_EDGES = [
    GraphEdge(source="pdf_expense_policy", target="sql_purchase_orders", edge_type="governance", description="expense policy defines approval thresholds for purchase orders"),
    GraphEdge(source="pdf_expense_policy", target="sql_invoices", edge_type="governance", description="expense policy defines vendor payment terms governing invoices"),
    GraphEdge(source="pdf_expense_policy", target="sql_vendors", edge_type="governance", description="expense policy defines inactive vendor rules"),
    GraphEdge(source="pdf_vendor_guide", target="sql_vendors", edge_type="governance", description="vendor onboarding guide defines the process for adding new vendors"),
    GraphEdge(source="pdf_vendor_guide", target="nosql_vendor_reviews", edge_type="governance", description="vendor guide defines performance monitoring criteria used in reviews"),
]

DERIVED_EDGES = [
    GraphEdge(source="pdf_q1_report", target="sql_invoices", edge_type="derived", description="Q1 report vendor performance section is derived from invoice payment data"),
    GraphEdge(source="pdf_q1_report", target="nosql_customer_feedback", edge_type="derived", description="Q1 report customer health section is derived from customer feedback"),
    GraphEdge(source="pdf_q1_report", target="nosql_support_tickets", edge_type="derived", description="Q1 report references critical support tickets"),
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

    print("\nExpansion test — starting from 'sql_invoices' (1 hop):")
    results = expand_sources(graph, ["sql_invoices"], max_hops=1)
    for r in results:
        marker = " *" if r["directly_selected"] else ""
        print(f"  {r['id']}{marker} ({r['source_type']}) — {len(r['edges'])} connections")


if __name__ == "__main__":
    setup()
