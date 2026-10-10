"""Unit tests for the advanced multi-stage reranker."""
from types import SimpleNamespace
import uuid

from rag.reranker import rerank, _extract_query_features


def _fake_chunk(content, c_type="general"):
    return SimpleNamespace(
        id=uuid.uuid4(),
        content=content,
        page=1,
        section="Benefit Schedule",
        chunk_metadata={"clause_type": c_type},
    )


def test_extract_query_features():
    features = _extract_query_features("What is the room rent limit of 5000?")
    assert "5000" in features["numbers"]
    assert features["is_limit"] is True


def test_reranker_handles_empty():
    assert rerank("query", []) == []


def test_reranker_prioritizes_relevant_clause():
    chunks = [
        _fake_chunk("General definitions and terminology of policy terms.", "general"),
        _fake_chunk("Cataract surgery is subject to a sub-limit of Rs 25,000 per eye.", "limit"),
        _fake_chunk("Premium payment guidelines and cancellation procedures.", "general"),
    ]
    query = "What is the sub-limit for cataract surgery?"
    results = rerank(query, chunks, top_k=3)

    assert len(results) == 3
    top_chunk, top_score = results[0]
    assert "cataract" in top_chunk.content.lower()
    assert top_score > results[1][1]
