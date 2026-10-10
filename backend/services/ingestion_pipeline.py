"""
Orchestrates the full contextual ingestion pipeline for a single policy version:
extract -> clean -> contextual hierarchical chunk -> embed (contextualized) -> persist to Postgres/pgvector.
Runs as a background task so the upload endpoint returns immediately.
"""
import logging
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.db import AsyncSessionLocal
from models.orm_models import Chunk, PolicyVersion
from rag.chunking import chunk_pages
from rag.embeddings import embed_texts
from rag.ingestion import extract_pdf_pages

logger = logging.getLogger(__name__)


async def process_policy_version(policy_version_id: UUID, file_path: str) -> None:
    """Background task entry point. Owns its own DB session since it runs
    outside the request's dependency-injected session lifecycle."""
    async with AsyncSessionLocal() as db:  # type: AsyncSession
        try:
            await _set_status(db, policy_version_id, "processing")

            # Fetch policy name for contextual breadcrumbs
            version_stmt = (
                select(PolicyVersion)
                .options(selectinload(PolicyVersion.policy))
                .where(PolicyVersion.id == policy_version_id)
            )
            pv_row = (await db.execute(version_stmt)).scalar_one_or_none()
            policy_name = pv_row.policy.name if (pv_row and pv_row.policy) else None

            pages = extract_pdf_pages(file_path)
            raw_chunks = chunk_pages(pages, policy_name=policy_name)

            if not raw_chunks:
                await _set_status(db, policy_version_id, "failed")
                logger.error("No text could be extracted from %s", file_path)
                return

            # Embed contextualized content for vastly superior semantic representations (Anthropic 2024)
            texts_to_embed = [c.contextualized_content for c in raw_chunks]
            vectors = embed_texts(texts_to_embed)

            for chunk, vector in zip(raw_chunks, vectors):
                metadata = {
                    "char_len": len(chunk.content),
                    "clause_type": chunk.clause_type,
                    "parent_section": chunk.parent_section,
                    "contextual_header": chunk.contextual_header,
                    "granularity": getattr(chunk, "granularity", "leaf"),
                    "summary": getattr(chunk, "summary", None),
                    "propositions": getattr(chunk, "propositions", []),
                    **(chunk.metadata or {}),
                }
                db.add(
                    Chunk(
                        policy_version_id=policy_version_id,
                        content=chunk.content,
                        page=chunk.page,
                        section=chunk.section,
                        embedding=vector,
                        chunk_metadata=metadata,
                    )
                )

            await db.execute(
                update(PolicyVersion)
                .where(PolicyVersion.id == policy_version_id)
                .values(status="ready", chunk_count=len(raw_chunks))
            )
            await db.commit()
            logger.info("Policy version %s processed: %d contextual chunks", policy_version_id, len(raw_chunks))
        except Exception:
            logger.exception("Processing failed for policy version %s", policy_version_id)
            await _set_status(db, policy_version_id, "failed")


async def _set_status(db: AsyncSession, policy_version_id: UUID, status: str) -> None:
    await db.execute(update(PolicyVersion).where(PolicyVersion.id == policy_version_id).values(status=status))
    await db.commit()
