"""Unit tests for the domain knowledge graph builder."""
from datetime import date
from types import SimpleNamespace
import uuid

from graph.graph_builder import build_policy_graph


def test_build_policy_graph_extracts_entities():
    policy = SimpleNamespace(id=uuid.uuid4(), name="Optima Secure", insurer="HDFC ERGO")
    v1_id = uuid.uuid4()
    version = SimpleNamespace(
        id=v1_id,
        version="1.0",
        effective_from=date(2023, 1, 1),
        effective_until=date(2023, 12, 31),
        chunk_count=2,
    )

    c1 = SimpleNamespace(
        id=uuid.uuid4(),
        content="Cataract surgery is covered subject to a sub-limit of Rs 25,000 per eye and 24 months waiting period.",
        page=4,
        section="Special Conditions",
        chunk_metadata={"clause_type": "limit"},
    )
    c2 = SimpleNamespace(
        id=uuid.uuid4(),
        content="Room rent is capped at Rs 5,000 per day with 10% co-payment. Cosmetic treatment is strictly not covered.",
        page=6,
        section="Exclusions",
        chunk_metadata={"clause_type": "exclusion"},
    )

    chunks_by_version = {str(v1_id): [c1, c2]}
    graph = build_policy_graph(policy, [version], chunks_by_version, [])

    # Check that graph contains extracted domain entities
    node_types = {data.get("type") for _, data in graph.nodes(data=True)}
    assert "Policy" in node_types
    assert "Version" in node_types
    assert "Clause" in node_types
    assert "MedicalCondition" in node_types
    assert "WaitingPeriod" in node_types
    assert "SubLimit" in node_types
    assert "CoPay" in node_types
    assert "Exclusion" in node_types

    # Check specific edge relationships
    relations = {data.get("relation") for _, _, data in graph.edges(data=True)}
    assert "HAS_VERSION" in relations
    assert "CONTAINS" in relations
    assert "COVERS" in relations
    assert "HAS_WAITING_PERIOD" in relations
    assert "HAS_SUBLIMIT" in relations
    assert "HAS_COPAY" in relations
    assert "EXCLUDES" in relations
