"""Unit tests for upgraded MiniCheck evidence verification and fact checking guardrails."""
from types import SimpleNamespace
import uuid

from rag.evidence_verifier import (
    INSUFFICIENT_EVIDENCE_MSG,
    decompose_into_claims,
    extract_quantities,
    verify_answer,
    verify_answer_detailed,
    verify_numeric_consistency,
)


def _fake_chunk(content, page=1):
    return SimpleNamespace(id=uuid.uuid4(), content=content, page=page)


def test_no_evidence_returns_unsupported():
    supported, confidence, warnings = verify_answer("Room rent is 5000.", [])
    assert not supported
    assert confidence == 0.0


def test_insufficient_evidence_message_short_circuits():
    supported, confidence, warnings = verify_answer(INSUFFICIENT_EVIDENCE_MSG, [(_fake_chunk("x"), 0.9)])
    assert not supported
    assert confidence == 0.0


def test_supported_answer_with_matching_numbers():
    evidence = [(_fake_chunk("Room rent covered up to 5000 per day."), 0.8)]
    supported, confidence, warnings = verify_answer("Room rent covered up to 5000 per day.", evidence)
    assert supported
    assert confidence > 0.25


def test_detect_hallucinated_figures():
    evidence_text = "Room rent covered up to Rs 5,000 per day. ICU charges up to Rs 10,000."
    is_valid, warnings = verify_numeric_consistency("Room rent is covered up to Rs 50,000 per day.", evidence_text)
    assert not is_valid
    assert any("50000" in w for w in warnings)


def test_decompose_into_claims():
    answer = (
        "1. Cataract surgery is covered under the policy.\n"
        "2. The maximum limit for cataract surgery is Rs 25,000 per eye.\n"
        "3. A waiting period of 24 months applies."
    )
    claims = decompose_into_claims(answer)
    assert len(claims) == 3
    assert any("Cataract surgery is covered" in c for c in claims)


def test_detailed_verification_breakdown():
    evidence = [
        (_fake_chunk("Cataract surgery is covered up to Rs 25,000 per eye after 24 months waiting period."), 0.85)
    ]
    answer = "Cataract surgery is covered up to Rs 25,000 per eye. A waiting period of 24 months applies."
    detailed = verify_answer_detailed(answer, evidence)

    assert detailed.is_supported
    assert detailed.factual_precision >= 0.70
    assert len(detailed.verified_claims) >= 1
    assert all(c.status in ("SUPPORTED", "PARTIALLY_SUPPORTED") for c in detailed.verified_claims)
