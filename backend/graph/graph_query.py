"""
Query interface over the NetworkX graph, kept separate from graph_builder so
this file is the sole integration point to swap in Neo4j later (replace the
in-memory nx.MultiDiGraph lookups with Cypher queries against a Neo4j driver,
keeping the same function signatures/return shapes).
"""
import logging

import networkx as nx

from schemas.schemas import GraphEdge, GraphNode, GraphResponse

logger = logging.getLogger(__name__)


def graph_to_response(g: nx.MultiDiGraph) -> GraphResponse:
    nodes = [
        GraphNode(id=node_id, label=data.get("label", node_id), type=data.get("type", "Unknown"),
                  data={k: v for k, v in data.items() if k not in {"label", "type"}})
        for node_id, data in g.nodes(data=True)
    ]
    edges = [
        GraphEdge(source=u, target=v, relation=data.get("relation", "RELATED_TO"))
        for u, v, data in g.edges(data=True)
    ]
    communities = g.graph.get("communities", [])
    return GraphResponse(nodes=nodes, edges=edges, communities=communities)


def get_node_evidence(g: nx.MultiDiGraph, node_id: str) -> dict:
    """Return the evidence/source payload for a clicked node."""
    if node_id not in g:
        return {}
    data = dict(g.nodes[node_id])
    neighbors = [
        {"node": n, "relation": g.edges[node_id, n, k].get("relation")}
        for n, k in [(n, k) for n in g.successors(node_id) for k in g[node_id][n]]
    ]
    data["related"] = neighbors
    return data
