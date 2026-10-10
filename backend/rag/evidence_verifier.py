"""
Fact-Checking and Evidence Verification Engine with Conformal Calibration.
Inspired by MiniCheck (EMNLP 2024 / arXiv:2404.10774), FActScore (EMNLP 2023),
SAFE (Google DeepMind, 2024), and Conformal Prediction (Quach et al., 2024).

Features:
1. Atomic Claim Decomposition: Splits generated answer into discrete propositional claims.
2. Strict Numerical & Duration Consistency: Verifies monetary figures, waiting period durations,
   percentages, and sub-limits against retrieved policy text.
3. NLI-Style Entailment Scoring: Computes semantic support score for each claim against evidence.
4. Factual Precision Metric: Calculates the percentage of claims directly backed by policy evidence.
5. Calibrated Confidence & Abstention: Integrates Conformal Prediction and Semantic Entropy
   for statistically rigorous confidence scores and principled refusal.
"""
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from models.orm_models import Chunk
from rag.confidence_calibrator import CalibrationSignals, calibrate_confidence

logger = logging.getLogger(__name__)

INSUFFICIENT_EVIDENCE_MSG = "Insufficient evidence available in the uploaded policy documents."

# Number and monetary amount pattern
NUMERIC_FIGURE_RE = re.compile(
    r"(?:rs\.?|inr|₹)?\s*(\d[\d,]*\.?\d*)\s*(?:%|months?|days?|years?|per\s*day|lakhs?|crores?)?",
    re.IGNORECASE,
)

# Sentence splitter for atomic claims
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")


@dataclass
class VerifiedClaim:
    claim_text: str
    status: str  # SUPPORTED | PARTIALLY_SUPPORTED | UNSUPPORTED
    support_score: float
    supporting_chunk_id: str | None = None
    supporting_page: int | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class VerificationResult:
    is_supported: bool
    confidence: float
    factual_precision: float
    verified_claims: list[VerifiedClaim]
    warnings: list[str]
    calibrated_confidence: float = 0.0
    should_abstain: bool = False
    coverage_guarantee: float = 0.95
    entropy_level: str = "low"
    signal_breakdown: dict = field(default_factory=dict)


def decompose_into_claims(answer: str) -> list[str]:
    """
    Decomposes answer text into atomic sentences/claims.
    Filters out boilerplate intro/outro phrases.
    """
    if not answer or INSUFFICIENT_EVIDENCE_MSG.lower() in answer.lower():
        return []

    lines = [line.strip() for line in answer.split("\n") if line.strip()]
    claims: list[str] = []

    for line in lines:
        cleaned_line = re.sub(r"^(?:[-*•]|\d+[\.\)])\s*", "", line)
        sentences = SENTENCE_SPLIT_RE.split(cleaned_line)
        for s in sentences:
            s_clean = s.strip()
            if len(s_clean.split()) >= 3:
                claims.append(s_clean)

    return claims


def extract_quantities(text: str) -> set[str]:
    """Extract normalized numerical and monetary figures from text."""
    matches = NUMERIC_FIGURE_RE.findall(text)
    results = set()
    for m in matches:
        m_clean = m.replace(",", "").strip()
        if m_clean and m_clean != ".":
            results.add(m_clean)
    return results


def verify_numeric_consistency(claim: str, evidence_text: str) -> tuple[bool, list[str]]:
    """Checks if figures in claim exist in evidence text."""
    claim_figures = extract_quantities(claim)
    if not claim_figures:
        return True, []

    evidence_figures = extract_quantities(evidence_text)
    unsupported = claim_figures - evidence_figures

    if unsupported:
        return False, [
            f"Figures not found verbatim in evidence: {', '.join(sorted(unsupported))}"
        ]
    return True, []


def verify_single_claim(
    claim: str,
    evidence_chunks: list[tuple[Chunk, float]],
) -> VerifiedClaim:
    """
    Evaluates grounding of an individual atomic claim against candidate evidence chunks.
    (MiniCheck methodology)
    """
    claim_lower = claim.lower()
    claim_tokens = set(re.findall(r"[a-z0-9]+", claim_lower))
    best_chunk: Chunk | None = None
    best_score = 0.0
    best_warnings: list[str] = []

    for chunk, retrieval_score in evidence_chunks:
        c_text = chunk.content.lower()
        c_tokens = set(re.findall(r"[a-z0-9]+", c_text))

        has_consistent_nums, num_warnings = verify_numeric_consistency(claim, chunk.content)

        if claim_tokens:
            overlap = len(claim_tokens & c_tokens) / len(claim_tokens)
        else:
            overlap = 1.0

        claim_score = (0.65 * overlap) + (0.35 * min(retrieval_score, 1.0))
        if not has_consistent_nums:
            claim_score *= 0.40  # Heavily penalize numerical fabrication

        if claim_score > best_score:
            best_score = claim_score
            best_chunk = chunk
            best_warnings = num_warnings

    if best_score >= 0.50 and not best_warnings:
        status = "SUPPORTED"
    elif best_score >= 0.30:
        status = "PARTIALLY_SUPPORTED"
        if not best_warnings:
            best_warnings.append("Claim has partial semantic support in policy text.")
    else:
        status = "UNSUPPORTED"
        best_warnings.append("Claim lacks sufficient grounding in retrieved policy clauses.")

    return VerifiedClaim(
        claim_text=claim,
        status=status,
        support_score=round(best_score, 3),
        supporting_chunk_id=str(best_chunk.id) if best_chunk else None,
        supporting_page=best_chunk.page if best_chunk else None,
        warnings=best_warnings,
    )


def verify_answer(
    answer: str, evidence_chunks: list[tuple[Chunk, float]]
) -> tuple[bool, float, list[str]]:
    """
    Main verification entrypoint (fully backwards-compatible).
    Returns (is_supported, confidence, warnings).
    """
    detailed = verify_answer_detailed(answer, evidence_chunks)
    return detailed.is_supported, detailed.confidence, detailed.warnings


def verify_answer_detailed(
    answer: str,
    evidence_chunks: list[tuple[Chunk, float]],
    crag_regime: str = "correct",
    facet_coverage: float = 0.0,
    semantic_convergence: float = 1.0,
) -> VerificationResult:
    """
    Full MiniCheck-style fact verification breakdown with Conformal Calibration.
    """
    warnings: list[str] = []

    if not evidence_chunks:
        return VerificationResult(
            is_supported=False,
            confidence=0.0,
            factual_precision=0.0,
            verified_claims=[],
            warnings=["No relevant evidence was retrieved for this question."],
            calibrated_confidence=0.0,
            should_abstain=True,
            coverage_guarantee=0.5,
            entropy_level="high",
        )

    if INSUFFICIENT_EVIDENCE_MSG.lower() in answer.lower():
        return VerificationResult(
            is_supported=False,
            confidence=0.0,
            factual_precision=0.0,
            verified_claims=[],
            warnings=[],
            calibrated_confidence=0.0,
            should_abstain=True,
            coverage_guarantee=1.0,
            entropy_level="low",
        )

    claims = decompose_into_claims(answer)
    if not claims:
        claims = [answer.strip()]

    combined_evidence_text = " ".join(c.content for c, _ in evidence_chunks)
    has_valid_nums, num_warnings = verify_numeric_consistency(answer, combined_evidence_text)
    if num_warnings:
        warnings.extend(num_warnings)

    verified_claims = [verify_single_claim(claim, evidence_chunks) for claim in claims]

    supported_count = sum(1 for c in verified_claims if c.status == "SUPPORTED")
    partially_supported_count = sum(1 for c in verified_claims if c.status == "PARTIALLY_SUPPORTED")
    total_claims = len(verified_claims)

    factual_precision = round((supported_count + 0.5 * partially_supported_count) / max(total_claims, 1), 3)

    avg_retrieval_score = sum(score for _, score in evidence_chunks) / len(evidence_chunks)
    top_retrieval_score = max(score for _, score in evidence_chunks) if evidence_chunks else 0.0

    # Heuristic confidence (legacy)
    confidence = round((0.60 * factual_precision) + (0.40 * min(avg_retrieval_score, 1.0)), 3)

    # Conformal Calibration (Upgrade #6)
    signals = CalibrationSignals(
        retrieval_top_score=top_retrieval_score,
        retrieval_avg_score=avg_retrieval_score,
        facet_coverage=facet_coverage,
        factual_precision=factual_precision,
        numeric_consistency=not bool(num_warnings),
        semantic_convergence=semantic_convergence,
        evidence_count=len(evidence_chunks),
        claim_count=total_claims,
        supported_claim_ratio=factual_precision,
        crag_regime=crag_regime,
    )
    cal = calibrate_confidence(signals)

    is_supported = (factual_precision >= 0.50) and not num_warnings and not cal.should_abstain

    if cal.should_abstain:
        warnings.append(
            f"Calibrated confidence ({cal.calibrated_score:.2f}) triggers abstention guarantee (entropy: {cal.entropy_level})."
        )
    elif not is_supported and not num_warnings:
        warnings.append(
            f"Low factual precision ({factual_precision * 100:.0f}% claims verified); answer may contain speculative statements."
        )

    return VerificationResult(
        is_supported=is_supported,
        confidence=cal.calibrated_score if cal.calibrated_score > 0 else confidence,
        factual_precision=factual_precision,
        verified_claims=verified_claims,
        warnings=warnings,
        calibrated_confidence=cal.calibrated_score,
        should_abstain=cal.should_abstain,
        coverage_guarantee=cal.coverage_guarantee,
        entropy_level=cal.entropy_level,
        signal_breakdown=cal.signal_breakdown,
    )
