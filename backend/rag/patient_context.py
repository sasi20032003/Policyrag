"""
Builds a structured personal context block from a patient profile.
This context is injected into the LLM prompt alongside policy evidence,
enabling personalized answers like:
  "Given your age of 45 and Type 2 Diabetes declared at policy inception,
   the 2-year waiting period for your pre-existing condition ends on 2025-04-01."
"""
from datetime import date
from typing import Optional


from services.pii_anonymizer import pii_anonymizer


def _years_since(start: date) -> float:
    """Returns number of years elapsed since start date."""
    today = date.today()
    delta = today - start
    return delta.days / 365.25


def build_patient_context(profile: dict, anonymize: bool = True) -> str:
    """
    Convert a patient profile dict into a structured natural-language
    context block to inject into the LLM system prompt.
    When anonymize=True (default), direct identifiers (real name, exact DOB)
    are replaced with privacy-preserving pseudonyms ([Primary Insured]).

    Args:
        profile: dict representation of PatientProfile ORM or PatientProfileCreate
        anonymize: whether to de-identify PII before prompt generation (HIPAA/GDPR compliant)

    Returns:
        A formatted string describing the patient's situation.
    """
    if not profile:
        return ""

    if anonymize:
        profile, _ = pii_anonymizer.deidentify_profile(profile)

    lines = ["=== PATIENT / POLICYHOLDER DETAILS ==="]
    lines.append("Use these personal details to make your answer specific to this person.")
    lines.append("")

    # ── Identity ──────────────────────────────────────────────────────────────
    name    = profile.get("full_name", "the policyholder")
    age     = profile.get("age")
    gender  = profile.get("gender")
    dob     = profile.get("date_of_birth")

    identity_parts = [f"Name: {name}"]
    if age:
        identity_parts.append(f"Age: {age} years")
    if gender:
        identity_parts.append(f"Gender: {gender}")
    if dob:
        identity_parts.append(f"Date of Birth: {dob}")
    lines.append("IDENTITY: " + " | ".join(identity_parts))

    # ── Policy Enrollment ─────────────────────────────────────────────────────
    policy_start  = profile.get("policy_start_date")
    sum_insured   = profile.get("sum_insured")
    plan_type     = profile.get("plan_type")
    is_primary    = profile.get("is_primary_insured", True)

    enrollment_parts = []
    if policy_start:
        years_insured = _years_since(policy_start) if isinstance(policy_start, date) else None
        if years_insured is not None:
            enrollment_parts.append(
                f"Policy Start: {policy_start} ({years_insured:.1f} years ago — "
                f"{'policy is active' if years_insured > 0 else 'newly enrolled'})"
            )
        else:
            enrollment_parts.append(f"Policy Start: {policy_start}")
    if sum_insured:
        enrollment_parts.append(f"Sum Insured: ₹{sum_insured:,.0f}")
    if plan_type:
        enrollment_parts.append(f"Plan Type: {plan_type}")
    enrollment_parts.append(f"Role: {'Primary Insured' if is_primary else 'Dependent/Add-on member'}")

    if enrollment_parts:
        lines.append("POLICY ENROLLMENT: " + " | ".join(enrollment_parts))

    # ── Family Members ────────────────────────────────────────────────────────
    family = profile.get("family_members")
    if family:
        members_str = ", ".join(
            f"{m.get('name', 'Member')} ({m.get('relation', '?')}, {m.get('age', '?')} yrs, {m.get('gender', '?')})"
            for m in family
        )
        lines.append(f"FAMILY MEMBERS COVERED: {members_str}")

    # ── Pre-Existing Diseases (PED) ───────────────────────────────────────────
    ped = profile.get("pre_existing_diseases")
    if ped:
        lines.append(f"PRE-EXISTING DISEASES (declared at policy inception): {', '.join(ped)}")
        if policy_start:
            years = _years_since(policy_start) if isinstance(policy_start, date) else None
            if years is not None:
                lines.append(
                    f"  → PED Waiting Period Note: Policy has been active for {years:.1f} years. "
                    f"If the standard PED waiting period is 2 years, "
                    f"{'PED coverage has STARTED' if years >= 2 else f'PED coverage starts in approximately {(2 - years) * 12:.0f} months'}."
                )

    # ── Current Conditions ────────────────────────────────────────────────────
    current = profile.get("current_conditions")
    if current:
        lines.append(f"CURRENT HEALTH CONDITIONS: {', '.join(current)}")

    # ── Medical History ───────────────────────────────────────────────────────
    history = profile.get("medical_history")
    if history:
        history_str = "; ".join(
            f"{h.get('procedure', '?')} ({h.get('year', '?')}"
            + (f", {h['hospital']}" if h.get('hospital') else "") + ")"
            for h in history
        )
        lines.append(f"PAST MEDICAL PROCEDURES: {history_str}")

    # ── Current Medications ───────────────────────────────────────────────────
    meds = profile.get("current_medications")
    if meds:
        lines.append(f"CURRENT MEDICATIONS: {', '.join(meds)}")

    # ── Lifestyle Flags ───────────────────────────────────────────────────────
    lifestyle = []
    if profile.get("is_smoker") is True:
        lifestyle.append("Smoker (may affect loading/exclusions)")
    elif profile.get("is_smoker") is False:
        lifestyle.append("Non-smoker")
    if profile.get("is_diabetic") is True:
        lifestyle.append("Diabetic")
    if profile.get("is_hypertensive") is True:
        lifestyle.append("Hypertensive")
    if lifestyle:
        lines.append(f"LIFESTYLE / RISK FLAGS: {', '.join(lifestyle)}")

    # ── Claim History ─────────────────────────────────────────────────────────
    claims = profile.get("claim_history")
    if claims:
        total_claimed = sum(c.get("amount", 0) for c in claims)
        approved_claims = [c for c in claims if c.get("approved")]
        claims_str = "; ".join(
            f"₹{c.get('amount', 0):,.0f} for {c.get('reason', '?')} in {c.get('year', '?')} "
            f"({'Approved' if c.get('approved') else 'Rejected'})"
            for c in claims
        )
        lines.append(
            f"CLAIM HISTORY ({len(claims)} claim(s), total ₹{total_claimed:,.0f}, "
            f"{len(approved_claims)} approved): {claims_str}"
        )

    # ── Notes ─────────────────────────────────────────────────────────────────
    notes = profile.get("notes")
    if notes:
        lines.append(f"ADDITIONAL NOTES FROM PATIENT: {notes}")

    lines.append("")
    lines.append(
        "INSTRUCTION: Use the above personal details to personalize your answer. "
        "Calculate waiting periods based on the policy start date. "
        "Flag if any pre-existing disease might affect the coverage asked about. "
        "Mention if any family members are relevant to the question. "
        "Still base all factual claims on the policy evidence provided below."
    )
    lines.append("=" * 40)

    return "\n".join(lines)
