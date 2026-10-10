"""
Knowledge graph endpoint: builds (or rebuilds) the NetworkX graph for a
policy on request and returns nodes/edges for visualization.
"""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.db import get_db
from graph.graph_builder import build_policy_graph
from graph.graph_query import graph_to_response
from models.orm_models import Chunk, Contradiction, Policy
from schemas.schemas import GraphResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("/{policy_id}", response_model=GraphResponse)
async def get_policy_graph(policy_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Policy).options(selectinload(Policy.versions)).where(Policy.id == policy_id)
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    chunks_by_version: dict[str, list[Chunk]] = {}
    for version in policy.versions:
        rows = (await db.execute(select(Chunk).where(Chunk.policy_version_id == version.id))).scalars().all()
        chunks_by_version[str(version.id)] = list(rows)

    all_chunk_ids = [c.id for chunks in chunks_by_version.values() for c in chunks]
    contradictions = []
    if all_chunk_ids:
        contradictions = (
            (await db.execute(select(Contradiction).where(Contradiction.clause_a.in_(all_chunk_ids))))
            .scalars()
            .all()
        )

    g = build_policy_graph(policy, list(policy.versions), chunks_by_version, list(contradictions))
    return graph_to_response(g)
