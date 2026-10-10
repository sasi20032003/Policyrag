"""
Pydantic schemas for patient/person profile — request validation and API responses.
"""
from datetime import date, datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, Field


# ── Sub-schemas ──────────────────────────────────────────────────────────────

class FamilyMember(BaseModel):
    name: str
    relation: str   # Spouse | Son | Daughter | Father | Mother
    age: int
    gender: str     # Male | Female | Other


class MedicalHistoryItem(BaseModel):
    procedure: str
    year: int
    hospital: Optional[str] = None


class ClaimHistoryItem(BaseModel):
    year: int
    amount: float
    reason: str
    approved: bool


# ── Create / Update ──────────────────────────────────────────────────────────

class PatientProfileCreate(BaseModel):
    """Used when creating a new patient profile."""

    # Identity
    full_name: str = Field(..., min_length=2, max_length=200, example="Rajesh Kumar")
    age: Optional[int] = Field(None, ge=0, le=120, example=45)
    gender: Optional[str] = Field(None, example="Male")           # Male|Female|Other
    date_of_birth: Optional[date] = Field(None, example="1979-06-15")

    # Policy enrollment
    policy_start_date: Optional[date] = Field(None, example="2023-04-01")
    sum_insured: Optional[float] = Field(None, ge=0, example=500000)
    plan_type: Optional[str] = Field(None, example="Family Floater")
    is_primary_insured: bool = Field(True)

    # Family
    family_members: Optional[list[FamilyMember]] = Field(
        None,
        example=[{"name": "Priya", "relation": "Spouse", "age": 40, "gender": "Female"}]
    )

    # Health
    pre_existing_diseases: Optional[list[str]] = Field(
        None,
        example=["Type 2 Diabetes", "Hypertension"]
    )
    current_conditions: Optional[list[str]] = Field(
        None,
        example=["Knee Osteoarthritis"]
    )
    medical_history: Optional[list[MedicalHistoryItem]] = Field(
        None,
        example=[{"procedure": "Appendectomy", "year": 2021, "hospital": "Apollo Hospital"}]
    )
    current_medications: Optional[list[str]] = Field(
        None,
        example=["Metformin 500mg", "Amlodipine 5mg"]
    )

    # Lifestyle flags
    is_smoker: Optional[bool] = Field(None, example=False)
    is_diabetic: Optional[bool] = Field(None, example=True)
    is_hypertensive: Optional[bool] = Field(None, example=True)

    # Claim history
    claim_history: Optional[list[ClaimHistoryItem]] = Field(
        None,
        example=[{"year": 2023, "amount": 45000, "reason": "Hospitalization - Fever", "approved": True}]
    )

    notes: Optional[str] = Field(None, example="Planning knee replacement surgery next year.")


class PatientProfileUpdate(PatientProfileCreate):
    """All fields optional for partial updates (PATCH)."""
    full_name: Optional[str] = Field(None, min_length=2, max_length=200)


# ── Response ─────────────────────────────────────────────────────────────────

class PatientProfileOut(BaseModel):
    id: UUID
    user_id: Optional[UUID] = None
    full_name: str
    age: Optional[int]
    gender: Optional[str]
    date_of_birth: Optional[date]
    policy_start_date: Optional[date]
    sum_insured: Optional[float]
    plan_type: Optional[str]
    is_primary_insured: bool
    family_members: Optional[list]
    pre_existing_diseases: Optional[list]
    current_conditions: Optional[list]
    medical_history: Optional[list]
    current_medications: Optional[list]
    is_smoker: Optional[bool]
    is_diabetic: Optional[bool]
    is_hypertensive: Optional[bool]
    claim_history: Optional[list]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Personalized Chat ─────────────────────────────────────────────────────────

class PersonalizedChatRequest(BaseModel):
    """
    Extended chat request that includes a patient profile ID.
    The profile is injected as context into the LLM prompt so answers
    are tailored to the specific person's health and policy situation.
    """
    question: str = Field(..., min_length=3, example="Am I eligible for knee replacement surgery?")
    policy_id: Optional[UUID] = None
    as_of_date: Optional[date] = None
    top_k: int = Field(8, ge=1, le=20)

    # Patient context — either reference an existing profile or provide inline
    patient_profile_id: Optional[UUID] = Field(
        None,
        description="ID of a saved patient profile to use as context"
    )
    inline_profile: Optional[PatientProfileCreate] = Field(
        None,
        description="Provide profile inline without saving to DB"
    )
