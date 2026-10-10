"""
pgvector-backed semantic search over the chunks table using cosine distance.
"""
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.orm_models import Chunk
from rag.embeddings import embed_query

logger = logging.getLogger(__name__)


async def vector_search(
    db: AsyncSession, query: str, policy_version_ids: list[UUID], top_k: int = 20
) -> list[tuple[Chunk, float]]:
    """Return (chunk, similarity_score) pairs ordered by cosine similarity desc."""
    if not policy_version_ids:
        return []
    query_vec = embed_query(query)

    stmt = (
        select(Chunk, Chunk.embedding.cosine_distance(query_vec).label("distance"))
        .where(Chunk.policy_version_id.in_(policy_version_ids))
        .order_by("distance")
        .limit(top_k)
    )
    rows = (await db.execute(stmt)).all()
    # convert cosine distance -> similarity for consistent scoring with BM25
    return [(chunk, 1.0 - float(distance)) for chunk, distance in rows]
