"""
Corrective RAG (CRAG) Evaluator.
Based on Corrective Retrieval Augmented Generation (Yan et al., 2024 / arXiv:2401.15884)
and Self-RAG (ICLR 2024).

Evaluates retrieved evidence quality into three regimes:
- CORRECT: High-confidence evidence covering the key query facets.
- AMBIGUOUS: Borderline or partial evidence; triggers knowledge graph fallback or query rewrite.
- INCORRECT: Low relevance evidence; triggers conservative refusal to prevent hallucination.
"""
import enum
import logging
import re
from dataclasses import dataclass, field

from models.orm_models import Chunk

logger = logging.getLogger(__name__)


class CRAGRegime(str, enum.Enum):
    CORRECT = "correct"        # Strong evidence; proceed to generation
    AMBIGUOUS = "ambiguous"    # Partial evidence; trigger associative graph retrieval or rewrite
    INCORRECT = "incorrect"    # Inadequate evidence; refuse or trigger fallback


@dataclass
class CRAGEvaluation:
    regime: CRAGRegime
    confidence_score: float
    matched_facets: list[str] = field(default_factory=list)
    missing_facets: list[str] = field(default_factory=list)
    recommendation: str = ""
    refined_query: str | None = None


# Key healthcare insurance facets to check for coverage
FACET_PATTERNS = {
    "waiting_period": re.compile(r"\b(waiting\s*period|months?|days?|ped\b|pre-existing)\b", re.IGNORECASE),
    "limit_amount": re.compile(r"\b(rs\.?|inr|₹|\d[\d,]*|percentage|limit|sub-limit|capping)\b", re.IGNORECASE),
    "coverage_scope": re.compile(r"\b(covered|inpatient|day\s*care|ayush|ambulance|surgery|expenses)\b", re.IGNORECASE),
    "exclusions": re.compile(r"\b(not\s*covered|exclusion|excluded|shall\s*not\s*be\s*liable)\b", re.IGNORECASE),
    "copay": re.compile(r"\b(co-?pay|deductible|proportionate)\b", re.IGNORECASE),
}


def evaluate_retrieval(
    query: str,
    evidence_chunks: list[tuple[Chunk, float]],
    correct_threshold: float = 0.60,
    ambiguous_threshold: float = 0.38,
) -> CRAGEvaluation:
    """
    CRAG Retrieval Evaluator: Assesses evidence quality, computes facet coverage,
    and returns a recommendation.
    """
    if not evidence_chunks:
        return CRAGEvaluation(
            regime=CRAGRegime.INCORRECT,
            confidence_score=0.0,
            missing_facets=["all"],
            recommendation="No evidence retrieved. Return insufficient evidence.",
        )

    q_lower = query.lower()
    combined_evidence = " ".join(c.content.lower() for c, _ in evidence_chunks)
    scores = [s for _, s in evidence_chunks]
    top_score = scores[0] if scores else 0.0
    avg_score = sum(scores) / len(scores) if scores else 0.0

    # 1. Identify which facets the user query asks about
    query_facets: list[str] = []
    for facet_name, pattern in FACET_PATTERNS.items():
        if pattern.search(q_lower):
            query_facets.append(facet_name)

    if not query_facets:
        query_facets = ["coverage_scope"]

    # 2. Check if the retrieved evidence actually addresses those facets
    matched_facets: list[str] = []
    missing_facets: list[str] = []

    for facet in query_facets:
        pattern = FACET_PATTERNS[facet]
        if pattern.search(combined_evidence):
            matched_facets.append(facet)
        else:
            missing_facets.append(facet)

    facet_coverage = len(matched_facets) / max(len(query_facets), 1)

    # 3. Keyword / Concept grounding check
    query_tokens = [w for w in re.findall(r"[a-z0-9]+", q_lower) if len(w) > 3]
    evidence_tokens = set(re.findall(r"[a-z0-9]+", combined_evidence))
    token_overlap = sum(1 for t in query_tokens if t in evidence_tokens) / max(len(query_tokens), 1)

    # Overall CRAG confidence score
    crag_score = round(0.40 * top_score + 0.30 * avg_score + 0.20 * facet_coverage + 0.10 * token_overlap, 3)

    # 4. Classify into CRAG regimes
    if crag_score >= correct_threshold and facet_coverage >= 0.70:
        regime = CRAGRegime.CORRECT
        rec = "Evidence is robust and comprehensive. Proceed directly with grounded generation."
    elif crag_score >= ambiguous_threshold:
        regime = CRAGRegime.AMBIGUOUS
        rec = (
            f"Evidence is partial or ambiguous (missing facets: {', '.join(missing_facets)}). "
            f"Triggering HippoRAG associative graph traversal."
        )
    else:
        regime = CRAGRegime.INCORRECT
        rec = "Evidence relevance is low or fails to support query concepts. Refusal recommended."

    logger.info(
        "CRAG Evaluation for query '%s': regime=%s, confidence=%.3f, matched_facets=%s, missing_facets=%s",
        query,
        regime.value,
        crag_score,
        matched_facets,
        missing_facets,
    )

    return CRAGEvaluation(
        regime=regime,
        confidence_score=crag_score,
        matched_facets=matched_facets,
        missing_facets=missing_facets,
        recommendation=rec,
        refined_query=None if regime == CRAGRegime.CORRECT else f"{query} terms conditions sub-limit",
    )
