"""Unit tests for the Adaptive Query Engine (Adaptive-RAG / HyDE / Multi-Query)."""
from rag.query_engine import (
    QueryComplexity,
    analyze_query,
    classify_query_complexity,
    decompose_query,
    generate_domain_expansions,
    generate_hyde_document,
)


def test_classify_query_complexity():
    assert classify_query_complexity("What is the name of the insurer?") == QueryComplexity.SIMPLE
    assert classify_query_complexity("Is cataract surgery covered and what is the waiting period?") in (
        QueryComplexity.CONDITIONAL,
        QueryComplexity.MULTI_HOP,
    )
    assert classify_query_complexity("Compare room rent limit in v1 vs v2") == QueryComplexity.COMPARATIVE
    assert classify_query_complexity("What is the maternity cover and is newborn baby covered from day 1?") == QueryComplexity.MULTI_HOP


def test_decompose_query():
    query = "Is cataract surgery covered and what is the waiting period?"
    sub_queries = decompose_query(query)
    assert len(sub_queries) >= 2
    assert query in sub_queries


def test_domain_taxomony_expansion():
    expansions = generate_domain_expansions("What is the room rent limit?")
    assert len(expansions) > 0
    assert any("ICU" in exp or "room" in exp for exp in expansions)

    cataract_expansions = generate_domain_expansions("Is cataract operation included?")
    assert any("eye" in exp or "sub-limit" in exp for exp in cataract_expansions)


def test_hyde_document_generation():
    doc = generate_hyde_document("cataract surgery", ["eye treatment", "intraocular lens"])
    assert "Health Insurance Policy" in doc
    assert "cataract surgery" in doc
    assert "eye treatment" in doc


def test_analyze_query_complete():
    analysis = analyze_query("Are pre-existing diseases covered after 2 years?")
    assert analysis.complexity in (QueryComplexity.CONDITIONAL, QueryComplexity.MULTI_HOP)
    assert "waiting_period" in analysis.target_clause_types
    assert len(analysis.expanded_terms) > 0
    assert analysis.hyde_prompt is not None
