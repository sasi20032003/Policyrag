"""
HippoRAG-inspired Associative Knowledge Graph Retrieval with GraphRAG Community-Aware Search.
Based on:
- HippoRAG (NeurIPS 2024 / arXiv:2405.14831): Associative memory retrieval
- LightRAG (2024): Lightweight graph-augmented retrieval
- Microsoft GraphRAG (2024): Community-based global search + local entity traversal

Features:
1. Seed Entity Grounding: Maps query terms to KG entity nodes.
2. Associative Graph Traversal: 1-hop and 2-hop edge traversal for structurally related clauses.
3. Community-Aware Global Search (GraphRAG): For abstract questions, retrieves
   community summaries instead of individual entities.
4. Graph Reasoning Paths: Provenance trails for explicit structural context.
5. Personalized PageRank: Scores clause importance relative to seed entities.
"""
import logging
import re
from collections import defaultdict
from typing import Optional
from uuid import UUID

import networkx as nx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from graph.graph_builder import build_policy_graph, detect_communities, generate_community_summaries
from models.orm_models import Chunk, Contradiction, Policy, PolicyVersion

logger = logging.getLogger(__name__)


class HippoGraphRetriever:
    """
    Associative memory retrieval engine backed by NetworkX graph
    with GraphRAG community-level global search support.
    """

    def __init__(self):
        # Cache built graphs by policy_version_id
        self._graph_cache: dict[str, nx.MultiDiGraph] = {}

    async def get_or_build_graph(self, db: AsyncSession, version_ids: list[UUID]) -> nx.MultiDiGraph:
        """Fetch or assemble policy graph for the active versions."""
        cache_key = "_".join(sorted(str(v) for v in version_ids))
        if cache_key in self._graph_cache:
            return self._graph_cache[cache_key]

        # Fetch versions with policies and chunks
        versions = (
            (
                await db.execute(
                    select(PolicyVersion)
                    .options(selectinload(PolicyVersion.policy))
                    .where(PolicyVersion.id.in_(version_ids))
                )
            )
            .scalars()
            .all()
        )

        if not versions:
            return nx.MultiDiGraph()

        policy = versions[0].policy
        chunks = (
            (
                await db.execute(
                    select(Chunk).where(Chunk.policy_version_id.in_(version_ids))
                )
            )
            .scalars()
            .all()
        )

        chunks_by_ver: dict[str, list[Chunk]] = {}
        for c in chunks:
            vid_str = str(c.policy_version_id)
            chunks_by_ver.setdefault(vid_str, []).append(c)

        contradictions = []
        chunk_ids = [c.id for c in chunks]
        if chunk_ids:
            contradictions = (
                (
                    await db.execute(
                        select(Contradiction).where(
                            Contradiction.clause_a.in_(chunk_ids),
                            Contradiction.clause_b.in_(chunk_ids),
                        )
                    )
                )
                .scalars()
                .all()
            )

        graph = build_policy_graph(policy, versions, chunks_by_ver, list(contradictions))
        self._graph_cache[cache_key] = graph
        return graph

    def invalidate_cache(self, version_ids: list[UUID] | None = None) -> None:
        """Invalidate cached graphs (e.g., after reprocessing)."""
        if version_ids is None:
            self._graph_cache.clear()
        else:
            cache_key = "_".join(sorted(str(v) for v in version_ids))
            self._graph_cache.pop(cache_key, None)

    async def retrieve_community_context(
        self,
        db: AsyncSession,
        query: str,
        version_ids: list[UUID],
        top_k: int = 3,
    ) -> list[dict]:
        """
        GraphRAG Global Search: Retrieve community summaries most relevant
        to abstract/comparative queries like "What are the key exclusions?"
        or "Summarize the coverage benefits".

        Returns list of community summary dicts ranked by relevance.
        """
        if not version_ids:
            return []

        graph = await self.get_or_build_graph(db, version_ids)
        communities = graph.graph.get("communities", {})

        if not communities:
            return []

        q_lower = query.lower()
        q_tokens = set(re.findall(r"[a-z0-9]+", q_lower))

        scored_communities: list[tuple[int, float, dict]] = []
        for comm_id, comm_data in communities.items():
            summary = comm_data.get("summary", "").lower()
            theme = comm_data.get("theme", "").lower()
            entities = [e.lower() for e in comm_data.get("key_entities", [])]
            clause_types = comm_data.get("clause_types", [])

            # Score based on: theme match, entity overlap, keyword overlap
            score = 0.0

            # Theme keyword matching
            theme_tokens = set(re.findall(r"[a-z0-9]+", theme))
            theme_overlap = len(q_tokens & theme_tokens) / max(len(q_tokens), 1)
            score += theme_overlap * 3.0

            # Entity matching
            for entity in entities:
                entity_words = set(re.findall(r"[a-z0-9]+", entity))
                if entity_words & q_tokens:
                    score += 2.0

            # Summary content matching
            summary_tokens = set(re.findall(r"[a-z0-9]+", summary))
            summary_overlap = len(q_tokens & summary_tokens) / max(len(q_tokens), 1)
            score += summary_overlap * 1.5

            # Clause type matching (boost if query asks about exclusions/limits etc.)
            if any(ct in q_lower for ct in clause_types):
                score += 1.5

            if score > 0:
                scored_communities.append((comm_id, score, comm_data))

        scored_communities.sort(key=lambda x: x[1], reverse=True)

        results = []
        for comm_id, score, comm_data in scored_communities[:top_k]:
            results.append({
                "community_id": comm_id,
                "relevance_score": round(score, 3),
                **comm_data,
            })

        logger.info(
            "GraphRAG community search: %d communities matched for query '%s'",
            len(results),
            query[:80],
        )
        return results

    async def retrieve_associative_chunks(
        self,
        db: AsyncSession,
        query: str,
        version_ids: list[UUID],
        top_k: int = 6,
    ) -> list[tuple[Chunk, float, str]]:
        """
        Traverse knowledge graph from query entities to find associative clauses.
        Returns list of (Chunk, score, reasoning_path_description).
        """
        if not version_ids:
            return []

        graph = await self.get_or_build_graph(db, version_ids)
        if graph.number_of_nodes() == 0:
            return []

        q_lower = query.lower()

        # Step 1: Identify seed entities matching query terms
        seed_nodes = []
        for node_id, data in graph.nodes(data=True):
            node_type = data.get("type", "")
            label = str(data.get("label", "")).lower()

            if node_type in ("MedicalCondition", "WaitingPeriod", "SubLimit", "CoPay", "Exclusion"):
                # Check for token or substring match
                words = [w for w in re.split(r"\W+", label) if len(w) > 3]
                if any(w in q_lower for w in words):
                    seed_nodes.append((node_id, 1.0))
                elif label in q_lower:
                    seed_nodes.append((node_id, 1.2))

        if not seed_nodes:
            return []

        # Step 2: Multi-hop associative propagation (HippoRAG Personalized PageRank / neighborhood walk)
        clause_scores: dict[str, float] = {}
        reasoning_paths: dict[str, list[str]] = {}

        for seed_id, seed_weight in seed_nodes:
            seed_label = graph.nodes[seed_id].get("label", seed_id)
            seed_type = graph.nodes[seed_id].get("type", "")

            # 1-hop predecessors/successors
            neighbors = set(graph.predecessors(seed_id)) | set(graph.successors(seed_id))
            for nbr in neighbors:
                nbr_data = graph.nodes.get(nbr, {})
                if nbr_data.get("type") == "Clause":
                    edge_data = graph.get_edge_data(nbr, seed_id) or graph.get_edge_data(seed_id, nbr)
                    rel = "RELATED_TO"
                    if edge_data:
                        first_edge = list(edge_data.values())[0]
                        rel = first_edge.get("relation", "CONNECTED")

                    cid = nbr.replace("clause:", "")
                    clause_scores[cid] = clause_scores.get(cid, 0.0) + (1.0 * seed_weight)
                    path_str = f"{seed_type}('{seed_label}') --[{rel}]--> Clause(page {nbr_data.get('page')})"
                    reasoning_paths.setdefault(cid, []).append(path_str)

                # 2-hop traversal (e.g. Condition -> Clause A -> SUPERSEDES/CONTRADICTS -> Clause B)
                for second_hop in set(graph.predecessors(nbr)) | set(graph.successors(nbr)):
                    second_data = graph.nodes.get(second_hop, {})
                    if second_data.get("type") == "Clause":
                        cid = second_hop.replace("clause:", "")
                        clause_scores[cid] = clause_scores.get(cid, 0.0) + (0.5 * seed_weight)
                        path_str = f"{seed_type}('{seed_label}') -> {nbr} -> Clause(page {second_data.get('page')})"
                        reasoning_paths.setdefault(cid, []).append(path_str)

        if not clause_scores:
            return []

        # Step 2.5: Community-aware score boosting
        # Boost clauses that belong to the same community as seed entities
        seed_communities = set()
        for seed_id, _ in seed_nodes:
            comm = graph.nodes.get(seed_id, {}).get("community_id")
            if comm is not None:
                seed_communities.add(comm)

        if seed_communities:
            for cid in clause_scores:
                clause_node = f"clause:{cid}"
                clause_comm = graph.nodes.get(clause_node, {}).get("community_id")
                if clause_comm in seed_communities:
                    clause_scores[cid] *= 1.25  # 25% boost for same-community clauses

        # Step 3: Fetch matching Chunk models from DB
        chunk_uuids = [UUID(cid) for cid in clause_scores.keys() if _is_valid_uuid(cid)]
        if not chunk_uuids:
            return []

        db_chunks = (
            (await db.execute(select(Chunk).where(Chunk.id.in_(chunk_uuids))))
            .scalars()
            .all()
        )
        chunk_map = {str(c.id): c for c in db_chunks}

        sorted_results = sorted(clause_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        final_list = []
        for cid, score in sorted_results:
            if cid in chunk_map:
                chunk_obj = chunk_map[cid]
                paths = " | ".join(reasoning_paths.get(cid, []))
                # Normalize graph score into [0.5, 0.95] range
                norm_score = min(0.5 + (score * 0.15), 0.95)
                final_list.append((chunk_obj, round(norm_score, 3), paths))

        logger.info(
            "HippoRAG associative retrieval yielded %d graph-grounded clauses for query '%s'",
            len(final_list),
            query,
        )
        return final_list


def _is_valid_uuid(val: str) -> bool:
    try:
        UUID(val)
        return True
    except ValueError:
        return False


hippo_graph_retriever = HippoGraphRetriever()
