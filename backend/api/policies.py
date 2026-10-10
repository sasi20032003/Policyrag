"""
Policy upload, listing, retrieval, comparison, reprocess and delete endpoints.
"""
import logging
import os
from datetime import date
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.db import get_db
from models.orm_models import Chunk, Contradiction, Policy, PolicyVersion
from rag.contradiction_detector import detect_contradictions
from schemas.schemas import ClauseDiff, CompareRequest, CompareResponse, PolicyOut, PolicyUploadResponse
from services.file_service import save_upload
from services.ingestion_pipeline import process_policy_version

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/policies", tags=["policies"])


@router.post("/upload", response_model=PolicyUploadResponse)
async def upload_policy(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    policy_name: str = Form(...),
    insurer: str = Form(...),
    version: str = Form(...),
    effective_from: date = Form(...),
    effective_until: date | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    # Reuse an existing Policy row if name+insurer already exists, else create.
    existing = (
        await db.execute(select(Policy).where(Policy.name == policy_name, Policy.insurer == insurer))
    ).scalar_one_or_none()

    policy = existing or Policy(name=policy_name, insurer=insurer)
    if not existing:
        db.add(policy)
        await db.flush()

    file_path = await save_upload(file)

    policy_version = PolicyVersion(
        policy_id=policy.id,
        version=version,
        effective_from=effective_from,
        effective_until=effective_until,
        file_path=file_path,
        status="pending",
    )
    db.add(policy_version)
    await db.commit()
    await db.refresh(policy_version)

    background_tasks.add_task(process_policy_version, policy_version.id, file_path)

    return PolicyUploadResponse(
        policy_id=policy.id,
        policy_version_id=policy_version.id,
        status="processing_started",
        message="Upload received. Text extraction and chunking running in the background.",
    )


@router.get("", response_model=list[PolicyOut])
async def list_policies(db: AsyncSession = Depends(get_db)):
    from sqlalchemy.orm import selectinload

    result = await db.execute(select(Policy).options(selectinload(Policy.versions)))
    return result.scalars().unique().all()


@router.get("/{policy_id}", response_model=PolicyOut)
async def get_policy(policy_id: UUID, db: AsyncSession = Depends(get_db)):
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(Policy).options(selectinload(Policy.versions)).where(Policy.id == policy_id)
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy


@router.post("/compare", response_model=CompareResponse)
async def compare_policy_versions(payload: CompareRequest, db: AsyncSession = Depends(get_db)):
    version_a = await db.get(PolicyVersion, payload.policy_version_id_a)
    version_b = await db.get(PolicyVersion, payload.policy_version_id_b)
    if not version_a or not version_b:
        raise HTTPException(status_code=404, detail="One or both policy versions not found")

    chunks_a = (
        (await db.execute(select(Chunk).where(Chunk.policy_version_id == version_a.id))).scalars().all()
    )
    chunks_b = (
        (await db.execute(select(Chunk).where(Chunk.policy_version_id == version_b.id))).scalars().all()
    )

    diff = await detect_contradictions(list(chunks_a), list(chunks_b))

    # Persist contradictions/updates for graph visualization.
    for bucket in ("modified", "contradictions"):
        for item in diff[bucket]:
            ca_id = item.get("clause_a_id")
            cb_id = item.get("clause_b_id")
            if ca_id and cb_id:
                db.add(
                    Contradiction(
                        clause_a=ca_id,
                        clause_b=cb_id,
                        type=item["type"],
                        explanation=item.get("explanation"),
                        confidence=item.get("confidence"),
                    )
                )
    await db.commit()

    def to_clause_diff(items):
        return [ClauseDiff(**item) for item in items]

    return CompareResponse(
        added=to_clause_diff(diff["added"]),
        removed=to_clause_diff(diff["removed"]),
        modified=to_clause_diff(diff["modified"]),
        contradictions=to_clause_diff(diff["contradictions"]),
    )


@router.post("/{policy_id}/reprocess")
async def reprocess_policy(policy_id: UUID, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(Policy).options(selectinload(Policy.versions)).where(Policy.id == policy_id)
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    for version in policy.versions:
        await db.execute(Chunk.__table__.delete().where(Chunk.policy_version_id == version.id))
        version.status = "pending"
        version.chunk_count = 0
        background_tasks.add_task(process_policy_version, version.id, version.file_path)
    await db.commit()
    return {"message": f"Reprocessing started for {len(policy.versions)} version(s)."}


@router.delete("/{policy_id}")
async def delete_policy(policy_id: UUID, db: AsyncSession = Depends(get_db)):
    policy = await db.get(Policy, policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Policy).options(selectinload(Policy.versions)).where(Policy.id == policy_id)
    )
    policy = result.scalar_one()
    for version in policy.versions:
        if os.path.exists(version.file_path):
            try:
                os.remove(version.file_path)
            except OSError:
                logger.warning("Could not remove file %s", version.file_path)

    await db.delete(policy)
    await db.commit()
    return {"message": "Policy deleted."}
