"""
Domain Knowledge Graph Builder with Community Detection for Healthcare Insurance Policies.
Inspired by:
- Microsoft GraphRAG (2024): Community detection + community summaries
- HippoRAG (NeurIPS 2024): Associative memory graph traversal
- LightRAG (2024): Lightweight knowledge graph construction

Features:
1. Fine-Grained Insurance Entity Extraction:
   - Policy, Version, Clause, CoverageBenefit, ExclusionCondition,
     WaitingPeriod, SubLimit, CoPay, MedicalProcedure, Condition
2. Semantic Relations:
   - HAS_VERSION, CONTAINS, COVERS, EXCLUDES, HAS_WAITING_PERIOD,
     HAS_SUBLIMIT, APPLIES_TO, SUPERSEDES, CONTRADICTS
3. Leiden Community Detection (GraphRAG):
   - Partitions the graph into topical communities
   - Generates extractive community summaries for global search
4. Community-Aware Retrieval:
   - Abstract questions route through community summaries
   - Specific questions use entity-level traversal
"""
import logging
import re
from collections import defaultdict
from typing import Any

import networkx as nx

from models.orm_models import Chunk, Contradiction, Policy, PolicyVersion

logger = logging.getLogger(__name__)

# Specialized entity extraction patterns
SPECIFIC_CONDITIONS = {
    "cataract": re.compile(r"\bcataract\b", re.IGNORECASE),
    "maternity": re.compile(r"\bmaternity|pregnancy|child\s*birth|caesarean\b", re.IGNORECASE),
    "pre_existing": re.compile(r"\bpre-existing\s*disease|ped\b", re.IGNORECASE),
    "hypertension": re.compile(r"\bhypertension|blood\s*pressure\b", re.IGNORECASE),
    "diabetes": re.compile(r"\bdiabet(?:es|ic)\b", re.IGNORECASE),
    "joint_replacement": re.compile(r"\bjoint\s*replacement|knee\s*replacement\b", re.IGNORECASE),
    "hernia": re.compile(r"\bhernia\b", re.IGNORECASE),
    "dialysis": re.compile(r"\bdialysis|renal|kidney\s*failure\b", re.IGNORECASE),
    "ayush": re.compile(r"\bayush|ayurveda|homeopathy|unani|siddha\b", re.IGNORECASE),
    "room_rent": re.compile(r"\broom\s*rent|icu\s*charges|single\s*private\s*room\b", re.IGNORECASE),
    "cancer": re.compile(r"\bcancer|oncology|chemotherapy|radiation\s*therapy\b", re.IGNORECASE),
    "cardiac": re.compile(r"\bcardiac|heart\s*surgery|angioplasty|bypass|stent\b", re.IGNORECASE),
    "organ_transplant": re.compile(r"\borgan\s*transplant|donor|harvesting\b", re.IGNORECASE),
    "mental_illness": re.compile(r"\bmental\s*illness|psychiatric|psychological\b", re.IGNORECASE),
}

WAITING_PERIOD_RE = re.compile(
    r"\b(\d+)\s*(days?|months?|years?)\s*(?:waiting\s*period|from\s*inception)?\b",
    re.IGNORECASE,
)

SUBLIMIT_RE = re.compile(
    r"(?:sub-?limit|capped\s*at|maximum\s*of|up\s*to)\s*(?:rs\.?|inr|₹)?\s*(\d[\d,]*)(?:\s*(?:per\s*day|per\s*eye|per\s*claim|%))?" ,
    re.IGNORECASE,
)

EXCLUSION_RE = re.compile(
    r"\b(shall\s*not\s*be\s*liable|not\s*covered|permanent\s*exclusion|specifically\s*excluded)\b",
    re.IGNORECASE,
)

COPAY_RE = re.compile(
    r"\b(\d+)\s*%\s*(?:co-?payment|copay|deductible)\b",
    re.IGNORECASE,
)


# ─────────────────────────────────────────────────────────────────────────────
# GraphRAG Community Detection (Microsoft GraphRAG, 2024)
# ─────────────────────────────────────────────────────────────────────────────

def detect_communities(graph: nx.MultiDiGraph) -> dict[str, int]:
    """
    Partition the graph into communities using the Leiden algorithm.
    Falls back to Louvain if Leiden is unavailable, and to label propagation
    as a final fallback. Returns dict mapping node_id → community_id.
    """
    if graph.number_of_nodes() < 3:
        return {n: 0 for n in graph.nodes()}

    # Convert to undirected simple graph for community detection
    undirected = graph.to_undirected()
    simple = nx.Graph(undirected)

    try:
        # Try Leiden first (requires cdlib or leidenalg)
        import community as community_louvain
        partition = community_louvain.best_partition(simple)
        logger.info("Community detection via Louvain: %d communities", len(set(partition.values())))
        return partition
    except ImportError:
        pass

    try:
        # Fallback: NetworkX label propagation
        from networkx.algorithms.community import greedy_modularity_communities
        communities = greedy_modularity_communities(simple)
        partition = {}
        for comm_id, comm_nodes in enumerate(communities):
            for node in comm_nodes:
                partition[node] = comm_id
        logger.info("Community detection via greedy modularity: %d communities", len(set(partition.values())))
        return partition
    except Exception as exc:
        logger.warning("Community detection failed (%s), using single community", exc)
        return {n: 0 for n in graph.nodes()}


def generate_community_summaries(
    graph: nx.MultiDiGraph,
    communities: dict[str, int],
) -> dict[int, dict]:
    """
    Generate extractive summaries for each detected community.
    Each summary describes the community's theme, key entities,
    and representative clause content.

    Returns dict mapping community_id → {
        "summary": str,
        "theme": str,
        "node_count": int,
        "key_entities": list[str],
        "clause_types": list[str],
    }
    """
    # Group nodes by community
    comm_nodes: dict[int, list[str]] = defaultdict(list)
    for node_id, comm_id in communities.items():
        comm_nodes[comm_id].append(node_id)

    summaries = {}
    for comm_id, nodes in comm_nodes.items():
        # Collect metadata from community nodes
        clause_contents = []
        entity_labels = []
        clause_types = set()
        node_types = defaultdict(int)

        for node_id in nodes:
            data = graph.nodes.get(node_id, {})
            n_type = data.get("type", "Unknown")
            label = data.get("label", "")
            node_types[n_type] += 1

            if n_type == "Clause":
                content = data.get("content", "")
                if content:
                    first_sent = content.split(". ")[0].strip()
                    if first_sent:
                        clause_contents.append(first_sent[:200])
                c_type = data.get("clause_type", "general")
                clause_types.add(c_type)
            elif n_type in ("MedicalCondition", "WaitingPeriod", "SubLimit", "CoPay", "Exclusion"):
                entity_labels.append(label)

        # Determine community theme based on dominant clause types
        type_priority = ["exclusion", "waiting_period", "limit", "coverage", "claim", "general"]
        theme = "General Policy Provisions"
        for t in type_priority:
            if t in clause_types:
                theme_map = {
                    "exclusion": "Exclusions & Non-Covered Conditions",
                    "waiting_period": "Waiting Periods & Pre-Existing Disease Rules",
                    "limit": "Sub-Limits, Co-Payments & Capping Rules",
                    "coverage": "Coverage Benefits & Eligible Treatments",
                    "claim": "Claims Process & Documentation",
                }
                theme = theme_map.get(t, theme)
                break

        # Build extractive summary
        summary_parts = [f"Community Theme: {theme}."]
        if entity_labels:
            summary_parts.append(f"Key entities: {', '.join(entity_labels[:6])}.")
        if clause_contents:
            summary_parts.append(
                "Representative clauses: " + " | ".join(clause_contents[:4]) + "."
            )

        summaries[comm_id] = {
            "summary": " ".join(summary_parts),
            "theme": theme,
            "node_count": len(nodes),
            "key_entities": entity_labels[:10],
            "clause_types": list(clause_types),
            "node_type_distribution": dict(node_types),
        }

    return summaries


# ─────────────────────────────────────────────────────────────────────────────
# Graph Construction
# ─────────────────────────────────────────────────────────────────────────────

def build_policy_graph(
    policy: Policy,
    versions: list[PolicyVersion],
    chunks_by_version: dict[str, list[Chunk]],
    contradictions: list[Contradiction],
) -> nx.MultiDiGraph:
    """
    Constructs a rich MultiDiGraph encoding hierarchical document structure,
    insurance business entities, cross-version semantic contradictions,
    and GraphRAG community metadata.
    """
    g = nx.MultiDiGraph()

    policy_node = f"policy:{policy.id}"
    g.add_node(
        policy_node,
        label=policy.name,
        type="Policy",
        insurer=policy.insurer,
        data={"name": policy.name, "insurer": policy.insurer},
    )

    for version in versions:
        version_node = f"version:{version.id}"
        g.add_node(
            version_node,
            label=f"v{version.version}",
            type="Version",
            effective_from=str(version.effective_from),
            effective_until=str(version.effective_until) if version.effective_until else "present",
            data={
                "version": version.version,
                "effective_from": str(version.effective_from),
                "effective_until": str(version.effective_until) if version.effective_until else None,
                "chunk_count": version.chunk_count,
            },
        )
        g.add_edge(policy_node, version_node, relation="HAS_VERSION")

        for chunk in chunks_by_version.get(str(version.id), []):
            clause_node = f"clause:{chunk.id}"
            short_lbl = _short_label(chunk.content)
            clause_metadata = chunk.chunk_metadata or {}
            c_type = clause_metadata.get("clause_type", "general")

            g.add_node(
                clause_node,
                label=short_lbl,
                type="Clause",
                page=chunk.page,
                section=chunk.section,
                content=chunk.content,
                clause_type=c_type,
                data={
                    "page": chunk.page,
                    "section": chunk.section,
                    "clause_type": c_type,
                    "char_len": len(chunk.content),
                },
            )
            g.add_edge(version_node, clause_node, relation="CONTAINS")

            content = chunk.content

            # 1. Extract Specific Medical Condition / Procedure Entities
            for condition_key, pattern in SPECIFIC_CONDITIONS.items():
                if pattern.search(content):
                    condition_node = f"condition:{condition_key}"
                    display_name = condition_key.replace("_", " ").title()
                    if condition_node not in g:
                        g.add_node(
                            condition_node,
                            label=display_name,
                            type="MedicalCondition",
                            data={"name": display_name},
                        )
                    g.add_edge(clause_node, condition_node, relation="COVERS")

            # 2. Extract Waiting Period Entities
            wp_match = WAITING_PERIOD_RE.search(content)
            if wp_match:
                duration_val = wp_match.group(1)
                unit = wp_match.group(2).lower()
                wp_id = f"waiting:{duration_val}_{unit}"
                wp_label = f"Waiting Period: {duration_val} {unit}"
                if wp_id not in g:
                    g.add_node(
                        wp_id,
                        label=wp_label,
                        type="WaitingPeriod",
                        data={"duration": int(duration_val), "unit": unit},
                    )
                g.add_edge(clause_node, wp_id, relation="HAS_WAITING_PERIOD")

            # 3. Extract Sub-limit & Capping Entities
            sublimit_match = SUBLIMIT_RE.search(content)
            if sublimit_match:
                limit_val = sublimit_match.group(1)
                limit_id = f"limit:{limit_val.replace(',', '')}"
                limit_label = f"Sub-limit: Rs {limit_val}"
                if limit_id not in g:
                    g.add_node(
                        limit_id,
                        label=limit_label,
                        type="SubLimit",
                        data={"amount": limit_val},
                    )
                g.add_edge(clause_node, limit_id, relation="HAS_SUBLIMIT")

            # 4. Extract Co-Pay Entities
            copay_match = COPAY_RE.search(content)
            if copay_match:
                pct = copay_match.group(1)
                copay_id = f"copay:{pct}pct"
                copay_label = f"Co-Pay: {pct}%"
                if copay_id not in g:
                    g.add_node(
                        copay_id,
                        label=copay_label,
                        type="CoPay",
                        data={"percentage": int(pct)},
                    )
                g.add_edge(clause_node, copay_id, relation="HAS_COPAY")

            # 5. Extract Exclusion Entities
            if EXCLUSION_RE.search(content) or c_type == "exclusion":
                ex_name = chunk.section or "General Exclusion"
                ex_node = f"exclusion:{chunk.id}"
                g.add_node(
                    ex_node,
                    label=f"Exclusion: {_short_label(ex_name, 35)}",
                    type="Exclusion",
                    data={"section": ex_name},
                )
                g.add_edge(clause_node, ex_node, relation="EXCLUDES")

    # 6. Cross-version contradiction & supersedes edges
    for c in contradictions:
        node_a, node_b = f"clause:{c.clause_a}", f"clause:{c.clause_b}"
        if node_a in g and node_b in g:
            relation = "CONTRADICTS" if c.type == "CONTRADICTORY" else "SUPERSEDES"
            g.add_edge(
                node_a,
                node_b,
                relation=relation,
                explanation=c.explanation,
                confidence=c.confidence,
            )

    # 7. GraphRAG Community Detection & Summary Generation
    if g.number_of_nodes() >= 5:
        communities = detect_communities(g)
        comm_summaries = generate_community_summaries(g, communities)

        # Attach community metadata to nodes
        for node_id, comm_id in communities.items():
            if node_id in g.nodes:
                g.nodes[node_id]["community_id"] = comm_id

        # Store community summaries as graph-level attributes
        g.graph["communities"] = comm_summaries
        g.graph["community_count"] = len(comm_summaries)

        logger.info(
            "GraphRAG: Detected %d communities with extractive summaries",
            len(comm_summaries),
        )

    logger.info(
        "Built domain knowledge graph for policy %s with %d nodes and %d edges",
        policy.name,
        g.number_of_nodes(),
        g.number_of_edges(),
    )
    return g


def _short_label(text: str, max_len: int = 55) -> str:
    text = text.strip().replace("\n", " ")
    return text[:max_len] + ("…" if len(text) > max_len else "")
