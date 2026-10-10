"""
Patient profile CRUD endpoints + personalized chat endpoint.

Routes:
  POST   /api/patients/              Create a new patient profile
  GET    /api/patients/              List all profiles
  GET    /api/patients/{id}          Get one profile
  PUT    /api/patients/{id}          Full update
  PATCH  /api/patients/{id}          Partial update
  DELETE /api/patients/{id}          Delete profile
  POST   /api/patients/chat          Personalized RAG Q&A with patient context
"""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.db import get_db
from models.orm_models import Evidence, QueryLog
from models.patient_profile import PatientProfile
from rag.evidence_verifier import INSUFFICIENT_EVIDENCE_MSG, verify_answer
from rag.generator import generate_answer
from rag.hybrid_retrieval import hybrid_retrieve
from rag.patient_context import build_patient_context
from rag.reranker import rerank
from rag.temporal_filter import get_valid_versions
from schemas.patient_schemas import (
    PatientProfileCreate,
    PatientProfileOut,
    PatientProfileUpdate,
    PersonalizedChatRequest,
)
from schemas.schemas import ChatQueryResponse, EvidenceItem

from models.user import User
from services.auth_service import get_current_user_optional

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/patients", tags=["patients"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _profile_to_dict(profile: PatientProfile) -> dict:
    """Convert ORM model to plain dict for context builder."""
    return {
        "full_name":            profile.full_name,
        "age":                  profile.age,
        "gender":               profile.gender,
        "date_of_birth":        profile.date_of_birth,
        "policy_start_date":    profile.policy_start_date,
        "sum_insured":          profile.sum_insured,
        "plan_type":            profile.plan_type,
        "is_primary_insured":   profile.is_primary_insured,
        "family_members":       profile.family_members,
        "pre_existing_diseases":profile.pre_existing_diseases,
        "current_conditions":   profile.current_conditions,
        "medical_history":      profile.medical_history,
        "current_medications":  profile.current_medications,
        "is_smoker":            profile.is_smoker,
        "is_diabetic":          profile.is_diabetic,
        "is_hypertensive":      profile.is_hypertensive,
        "claim_history":        profile.claim_history,
        "notes":                profile.notes,
    }


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.post("/", response_model=PatientProfileOut, status_code=status.HTTP_201_CREATED)
async def create_profile(
    payload: PatientProfileCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """Create a new patient/policyholder profile bound to the authenticated user."""
    profile_data = payload.model_dump()
    profile = PatientProfile(
        **profile_data,
        user_id=current_user.id if current_user else None,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    logger.info("Created patient profile: %s (%s) for user %s", profile.full_name, profile.id, current_user.id if current_user else "anonymous")
    return profile


@router.get("/", response_model=list[PatientProfileOut])
async def list_profiles(
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """List patient profiles scoped to the current user (tenancy isolation)."""
    stmt = select(PatientProfile).order_by(PatientProfile.created_at.desc())
    if current_user:
        stmt = stmt.where((PatientProfile.user_id == current_user.id) | (PatientProfile.user_id.is_(None)))
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{profile_id}", response_model=PatientProfileOut)
async def get_profile(
    profile_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """Get a single patient profile by ID with ownership verification."""
    profile = await db.get(PatientProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    if current_user and profile.user_id and profile.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have permission to view this patient profile.")

    return profile


@router.put("/{profile_id}", response_model=PatientProfileOut)
async def update_profile(
    profile_id: UUID,
    payload: PatientProfileCreate,
    db: AsyncSession = Depends(get_db),
):
    """Full replacement update of a patient profile."""
    profile = await db.get(PatientProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    for field, value in payload.model_dump().items():
        setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)
    return profile


@router.patch("/{profile_id}", response_model=PatientProfileOut)
async def patch_profile(
    profile_id: UUID,
    payload: PatientProfileUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Partial update — only update fields that are provided."""
    profile = await db.get(PatientProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)
    return profile


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(profile_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete a patient profile."""
    profile = await db.get(PatientProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Patient profile not found")
    await db.delete(profile)
    await db.commit()


# ── Personalized Chat ─────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatQueryResponse)
async def personalized_chat(
    payload: PersonalizedChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Personalized RAG Q&A — answers are tailored to the specific patient's
    health profile, policy start date, pre-existing diseases, and claim history.

    Provide EITHER:
      - patient_profile_id: UUID of an existing saved profile
      - inline_profile: a PatientProfileCreate object sent inline (not saved)

    The patient context is injected into the LLM system prompt alongside
    the retrieved evidence, enabling answers like:
      "Since you have Type 2 Diabetes declared as a pre-existing condition
       and your policy started 1.5 years ago, the 2-year PED waiting period
       has NOT yet elapsed — diabetes-related hospitalization will not be
       covered until April 2025."
    """
    # ── 1. Resolve patient context ─────────────────────────────────────────
    patient_context: str = ""

    if payload.patient_profile_id:
        profile = await db.get(PatientProfile, payload.patient_profile_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Patient profile not found")
        patient_context = build_patient_context(_profile_to_dict(profile))

    elif payload.inline_profile:
        profile_dict = payload.inline_profile.model_dump()
        patient_context = build_patient_context(profile_dict)

    # ── 2. Temporal filter: find valid policy versions ─────────────────────
    versions = await get_valid_versions(db, payload.policy_id, payload.as_of_date)

    if not versions:
        return ChatQueryResponse(
            answer=INSUFFICIENT_EVIDENCE_MSG,
            policy_version=None,
            evidence=[],
            confidence=0.0,
            warnings=["No valid, fully-processed policy version found for the requested date."],
        )

    # ── 3. Hybrid retrieval (BM25 + vector + RRF) ─────────────────────────
    version_ids = [v.id for v in versions]
    candidates  = await hybrid_retrieve(db, payload.question, version_ids, top_k=15)
    top_evidence = rerank(payload.question, candidates, top_k=payload.top_k)

    # ── 4. Generate personalized answer ───────────────────────────────────
    answer = await generate_answer(payload.question, top_evidence, patient_context=patient_context)
    is_supported, confidence, warnings = verify_answer(answer, top_evidence)

    if not is_supported and answer.strip() != INSUFFICIENT_EVIDENCE_MSG:
        warnings.append("Answer flagged as weakly supported by evidence verification.")

    if patient_context:
        # Let user know personalization was applied
        warnings_info = [w for w in warnings]  # copy
    else:
        warnings_info = warnings + ["No patient profile provided — answer is generic, not personalized."]

    version_label = (
        ", ".join(
            f"{v.policy.name if hasattr(v, 'policy') else ''} v{v.version}".strip()
            for v in versions[:1]
        ) or versions[0].version
    )

    # ── 5. Log query + evidence ────────────────────────────────────────────
    query_log = QueryLog(question=payload.question, answer=answer, confidence=confidence)
    db.add(query_log)
    await db.flush()

    evidence_items = []
    for chunk, score in top_evidence:
        db.add(Evidence(query_id=query_log.id, chunk_id=chunk.id, relevance_score=score))
        evidence_items.append(
            EvidenceItem(
                chunk_id=chunk.id,
                content=chunk.content,
                page=chunk.page,
                section=chunk.section,
                policy_version=next(
                    (v.version for v in versions if v.id == chunk.policy_version_id), "unknown"
                ),
                relevance_score=round(score, 3),
            )
        )
    await db.commit()

    return ChatQueryResponse(
        answer=answer,
        policy_version=version_label,
        evidence=evidence_items,
        confidence=confidence,
        warnings=warnings_info,
    )
