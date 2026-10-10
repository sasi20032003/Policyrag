"""
Patient/Person profile model for personalized policy Q&A.
Stores health details used to contextualize LLM answers.
"""
import uuid
from datetime import date, datetime

from sqlalchemy import String, Text, Integer, Float, Date, DateTime, JSON, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from database.db import Base


def _uuid():
    return uuid.uuid4()


class PatientProfile(Base):
    """
    Stores a patient/policyholder's personal and health details.
    These are injected into the LLM prompt to make answers personalized.
    No sensitive data is stored beyond what the user explicitly provides.
    """
    __tablename__ = "patient_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )

    # ── Basic Identity ────────────────────────────────────────────────────────
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)   # Male|Female|Other
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)

    # ── Policy Enrollment Details ─────────────────────────────────────────────
    policy_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    sum_insured: Mapped[float | None] = mapped_column(Float, nullable=True)  # in INR
    plan_type: Mapped[str | None] = mapped_column(String(100), nullable=True)  # Individual|Family Floater|Group
    is_primary_insured: Mapped[bool] = mapped_column(Boolean, default=True)

    # ── Family Members (JSON array) ───────────────────────────────────────────
    # Format: [{"name": "Wife", "age": 35, "relation": "Spouse", "gender": "Female"}, ...]
    family_members: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # ── Health Details ────────────────────────────────────────────────────────
    # Pre-existing diseases (PED) — declared at policy inception
    # Format: ["Type 2 Diabetes", "Hypertension", "Asthma"]
    pre_existing_diseases: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Current health conditions / recent diagnoses
    current_conditions: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Surgeries / hospitalizations in the last 4 years
    # Format: [{"procedure": "Appendectomy", "year": 2022, "hospital": "Apollo"}]
    medical_history: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Regular medications
    # Format: ["Metformin 500mg", "Amlodipine 5mg"]
    current_medications: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Lifestyle factors that affect coverage
    is_smoker: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_diabetic: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_hypertensive: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # ── Claim History ─────────────────────────────────────────────────────────
    # Previous claims filed
    # Format: [{"year": 2023, "amount": 45000, "reason": "Hospitalization", "approved": true}]
    claim_history: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # ── Additional Notes ──────────────────────────────────────────────────────
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
