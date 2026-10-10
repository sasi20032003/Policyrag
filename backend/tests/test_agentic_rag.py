"""Unit tests for the end-to-end Agentic RAG pipeline."""
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import uuid

import pytest

from rag.agentic_rag import execute_agentic_rag


@pytest.mark.asyncio
async def test_agentic_rag_returns_insufficient_when_no_valid_version():
    mock_db = AsyncMock()
    with patch("rag.agentic_rag.get_valid_versions", new_callable=AsyncMock) as mock_get_versions:
        mock_get_versions.return_value = []
        result = await execute_agentic_rag(mock_db, "Is cataract covered?")

        assert "Insufficient evidence" in result.answer
        assert result.confidence == 0.0
        assert result.crag_regime == "incorrect"


@pytest.mark.asyncio
async def test_agentic_rag_successful_flow():
    mock_db = AsyncMock()
    v_id = uuid.uuid4()
    p_id = uuid.uuid4()

    fake_policy = SimpleNamespace(id=p_id, name="Health Shield", insurer="Star Health")
    fake_version = SimpleNamespace(
        id=v_id,
        policy_id=p_id,
        version="1.0",
        effective_from=date(2023, 1, 1),
        effective_until=None,
        status="ready",
        chunk_count=1,
        policy=fake_policy,
    )

    fake_chunk = SimpleNamespace(
        id=uuid.uuid4(),
        policy_version_id=v_id,
        content="Cataract surgery is covered up to Rs 25,000 per eye after 24 months waiting period.",
        page=3,
        section="Special Conditions",
        chunk_metadata={"clause_type": "limit"},
    )

    with patch("rag.agentic_rag.get_valid_versions", new_callable=AsyncMock) as mock_versions, \
         patch("rag.agentic_rag.hybrid_retrieve", new_callable=AsyncMock) as mock_hybrid, \
         patch("rag.agentic_rag.hippo_graph_retriever.retrieve_associative_chunks", new_callable=AsyncMock) as mock_graph, \
         patch("rag.agentic_rag.generate_answer", new_callable=AsyncMock) as mock_gen:

        mock_versions.return_value = [fake_version]
        mock_hybrid.return_value = [fake_chunk]
        mock_graph.return_value = []
        mock_gen.return_value = "Cataract surgery is covered up to Rs 25,000 per eye with 24 months waiting period."

        result = await execute_agentic_rag(
            db=mock_db,
            question="Is cataract surgery covered and what is the sub-limit?",
        )

        assert "Cataract surgery is covered" in result.answer
        assert result.policy_version == "Health Shield v1.0"
        assert len(result.evidence) == 1
        assert result.evidence[0].page == 3
        assert result.factual_precision > 0.5
        assert result.confidence > 0.2
        assert result.crag_regime in ("correct", "ambiguous")
        assert len(result.sub_queries) >= 1
