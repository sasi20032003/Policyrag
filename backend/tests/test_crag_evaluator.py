"""Unit tests for CRAG (Corrective RAG) retrieval evaluator."""
from types import SimpleNamespace
import uuid

from rag.crag_evaluator import CRAGRegime, evaluate_retrieval


def _fake_chunk(content):
    return SimpleNamespace(id=uuid.uuid4(), content=content, page=1)


def test_crag_evaluates_empty_evidence_as_incorrect():
    eval_res = evaluate_retrieval("Is maternity covered?", [])
    assert eval_res.regime == CRAGRegime.INCORRECT
    assert eval_res.confidence_score == 0.0


def test_crag_evaluates_strong_evidence_as_correct():
    evidence = [
        (
            _fake_chunk("Maternity expenses are covered up to Rs 50,000 for normal delivery and Rs 75,000 for caesarean section after a 24-month waiting period."),
            0.88,
        ),
        (
            _fake_chunk("Waiting period of 24 months applies for all maternity benefits."),
            0.80,
        ),
    ]
    eval_res = evaluate_retrieval("Is maternity covered and what is the waiting period and limit?", evidence)
    assert eval_res.regime == CRAGRegime.CORRECT
    assert eval_res.confidence_score >= 0.60
    assert "waiting_period" in eval_res.matched_facets
    assert "limit_amount" in eval_res.matched_facets


def test_crag_evaluates_partial_evidence_as_ambiguous():
    evidence = [
        (
            _fake_chunk("General inpatient hospitalization is covered under Section 1."),
            0.50,
        )
    ]
    eval_res = evaluate_retrieval("What is the waiting period for pre-existing diseases?", evidence)
    # The evidence lacks waiting_period facet
    assert eval_res.regime in (CRAGRegime.AMBIGUOUS, CRAGRegime.INCORRECT)
    assert "waiting_period" in eval_res.missing_facets
