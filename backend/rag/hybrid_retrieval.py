"""
Contextual Hybrid Retrieval Engine combining Contextual BM25 and Dense Vector Search.
Inspired by Anthropic Contextual Retrieval (2024), BGE-M3 (2024), and RRF Fusion.

Features:
1. Contextual BM25: Indexes chunks enriched with their hierarchical breadcrumbs,
   enabling keyword hits on section titles and categories even when omitted in chunk text.
2. Multi-Query Fusion: Executes parallel retrieval across sub-queries and expanded synonyms.
3. Weighted Reciprocal Rank Fusion (RRF): Blends dense semantic vector scores and sparse lexical rankings.
"""
import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.orm_models import Chunk
from rag.bm25 import BM25Index
from rag.vector_search import vector_search

logger = logging.getLogger(__name__)

RRF_K = 60  # Reciprocal rank fusion constant


async def hybrid_retrieve(
    db: AsyncSession,
    query: str,
    policy_version_ids: list[UUID],
    sub_queries: Optional[list[str]] = None,
    hyde_query: Optional[str] = None,
    top_k: int = 15,
    dense_weight: float = 1.0,
    sparse_weight: float = 1.0,
) -> list[Chunk]:
    """
    Fuse Contextual BM25 lexical retrieval with pgvector semantic search.
    Supports sub-queries and HyDE vector query augmentation.
    """
    if not policy_version_ids:
        return []

    # Fetch candidate chunks scoped to the active policy versions
    stmt = select(Chunk).where(Chunk.policy_version_id.in_(policy_version_ids))
    rows = (await db.execute(stmt)).scalars().all()

    if not rows:
        return []

    chunk_by_id = {str(c.id): c for c in rows}

    # Contextual BM25: Index breadcrumb-enriched text, RAPTOR summaries, and Dense X propositions
    indexed_texts = []
    for c in rows:
        meta = c.chunk_metadata or {}
        header = meta.get("contextual_header") or c.section or ""
        enriched = f"[{header}] {c.content}" if header else c.content
        summary = meta.get("summary")
        if summary:
            enriched += f" [Summary: {summary}]"
        props = meta.get("propositions", [])
        if props:
            prop_str = " | ".join(props[:8])
            enriched += f" [Propositions: {prop_str}]"
        indexed_texts.append(enriched)

    bm25_index = BM25Index([str(c.id) for c in rows], indexed_texts)

    all_queries = [query]
    if sub_queries:
        for sq in sub_queries:
            if sq not in all_queries:
                all_queries.append(sq)

    rrf_scores: dict[str, float] = {}

    # Run Contextual BM25 for all sub-queries
    for q_item in all_queries:
        bm25_hits = bm25_index.search(q_item, top_k=max(top_k * 2, 20))
        for rank, (cid, score) in enumerate(bm25_hits):
            if score > 0:
                rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (sparse_weight / (RRF_K + rank + 1))

    # Run Vector Search for main query and optional HyDE query
    vector_target = hyde_query if hyde_query else query
    vector_results = await vector_search(db, vector_target, policy_version_ids, top_k=max(top_k * 2, 20))

    for rank, (chunk, score) in enumerate(vector_results):
        cid = str(chunk.id)
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (dense_weight / (RRF_K + rank + 1))

    # Also run vector search for original query if hyde was different
    if hyde_query and hyde_query != query:
        orig_vec_results = await vector_search(db, query, policy_version_ids, top_k=top_k)
        for rank, (chunk, score) in enumerate(orig_vec_results):
            cid = str(chunk.id)
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (dense_weight * 0.5 / (RRF_K + rank + 1))

    ranked_ids = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

    logger.info(
        "Hybrid retrieval fused BM25 + pgvector for %d sub-queries -> %d candidate chunks",
        len(all_queries),
        len(ranked_ids),
    )
    return [chunk_by_id[cid] for cid, _ in ranked_ids if cid in chunk_by_id]
