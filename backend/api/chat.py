"""
Chat/query endpoint implementing the upgraded Agentic RAG answer flow:
temporal filter -> adaptive query engine (HyDE / sub-queries) -> contextual hybrid retrieval
-> HippoRAG & GraphRAG community traversal -> cross-encoder rerank -> CRAG evaluation
-> DSPy dynamic prompt assembly -> Speculative RAG / Grounded Generation
-> MiniCheck atomic fact verification -> Conformal calibration -> Self-Refine loop.

Supports both standard REST JSON query and real-time Server-Sent Events (SSE) streaming
with progressive evidence disclosure.
"""
import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database.db import get_db
from models.orm_models import Evidence, QueryLog
from rag.agentic_rag import execute_agentic_rag, stream_agentic_rag
from schemas.schemas import ChatQueryRequest, ChatQueryResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/query", response_model=ChatQueryResponse)
async def query(payload: ChatQueryRequest, db: AsyncSession = Depends(get_db)):
    """
    Standard synchronous query endpoint returning full structured answer,
    conformal calibration metrics, and factual verification breakdown.
    """
    result = await execute_agentic_rag(
        db=db,
        question=payload.question,
        policy_id=payload.policy_id,
        as_of_date=payload.as_of_date,
        top_k=payload.top_k,
    )

    # Persist query log and evidence citations
    try:
        query_log = QueryLog(
            question=payload.question,
            answer=result.answer,
            confidence=result.confidence,
        )
        db.add(query_log)
        await db.flush()

        for item in result.evidence:
            db.add(Evidence(query_id=query_log.id, chunk_id=item.chunk_id, relevance_score=item.relevance_score))
        await db.commit()
    except Exception as exc:
        logger.warning("Failed to persist query log to DB: %s", exc)

    return ChatQueryResponse(
        answer=result.answer,
        policy_version=result.policy_version,
        evidence=result.evidence,
        confidence=result.confidence,
        warnings=result.warnings,
        crag_regime=result.crag_regime,
        retrieval_strategy=result.retrieval_strategy,
        sub_queries=result.sub_queries,
        factual_precision=result.factual_precision,
        reasoning_paths=result.reasoning_paths,
        okf_concepts=getattr(result, "okf_concepts", []),
        okf_rules_applied=getattr(result, "okf_rules_applied", {}),
        calibrated_confidence=getattr(result, "calibrated_confidence", result.confidence),
        should_abstain=getattr(result, "should_abstain", False),
        coverage_guarantee=getattr(result, "coverage_guarantee", 0.95),
        entropy_level=getattr(result, "entropy_level", "low"),
        speculative_drafts_count=getattr(result, "speculative_drafts_count", 0),
        community_summaries=getattr(result, "community_summaries", []),
        verified_claims=getattr(result, "verified_claims", []),
        merkle_root=getattr(result, "merkle_root", None),
        certificate_signature=getattr(result, "certificate_signature", None),
        conformal_interval=getattr(result, "conformal_interval", None),
        topological_dispersion=getattr(result, "topological_dispersion", None),
        lattice_arbitration_status=getattr(result, "lattice_arbitration_status", None),
    )


@router.post("/query/stream")
async def query_stream(payload: ChatQueryRequest, db: AsyncSession = Depends(get_db)):
    """
    Server-Sent Events (SSE) streaming endpoint implementing Progressive Evidence Disclosure.
    Progressively emits:
    1. status: pipeline stage transitions
    2. query_analysis: complexity and decomposed sub-queries
    3. evidence: retrieved evidence cards BEFORE generation begins
    4. crag_evaluation: regime and facet coverage
    5. token: token-by-token generation stream
    6. verification: claim grounding and MiniCheck verification
    7. done: final calibrated payload
    """
    async def sse_generator() -> AsyncGenerator[str, None]:
        try:
            async for event_obj in stream_agentic_rag(
                db=db,
                question=payload.question,
                policy_id=payload.policy_id,
                as_of_date=payload.as_of_date,
                top_k=payload.top_k,
            ):
                event_type = event_obj.get("event", "message")
                data_payload = json.dumps(event_obj.get("data", {}))
                yield f"event: {event_type}\ndata: {data_payload}\n\n"
        except Exception as exc:
            logger.exception("Error in SSE stream: %s", exc)
            err_data = json.dumps({"error": str(exc)})
            yield f"event: error\ndata: {err_data}\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
