"""Unit tests for the upgraded contextual and hierarchical chunking module."""
from rag.chunking import (
    Chunk,
    chunk_pages,
    clean_text,
    detect_section,
    detect_subsection,
    classify_clause_type,
    build_contextual_header,
)
from rag.ingestion import PageText


def test_clean_text_collapses_whitespace():
    assert clean_text("Hello   world\n\n\n\nfoo") == "Hello world\n\nfoo"


def test_detect_section_matches_headers():
    assert detect_section("EXCLUSIONS") == "EXCLUSIONS"
    assert detect_section("Section 4.2 Waiting Periods") is not None
    assert detect_section("this is a normal sentence.") is None


def test_detect_subsection():
    assert detect_subsection("1.1 Inpatient Hospitalization") is not None
    assert detect_subsection("(a) Room Rent and Boarding") is not None
    assert detect_subsection("not a subsection header") is None


def test_classify_clause_type():
    assert classify_clause_type("Pre-existing diseases have a 36 months waiting period.") == "waiting_period"
    assert classify_clause_type("Cosmetic and aesthetic surgeries are not covered.") == "exclusion"
    assert classify_clause_type("Room rent is capped at Rs 5,000 per day with 20% co-payment.") == "limit"
    assert classify_clause_type("Inpatient hospitalization and day care treatments are covered.") == "coverage"


def test_contextual_breadcrumb_construction():
    header = build_contextual_header(
        policy_name="Care Plus",
        section="Exclusions",
        subsection="Clause 4.1 PED",
        clause_type="waiting_period",
    )
    assert "Policy: Care Plus" in header
    assert "Section: Exclusions" in header
    assert "Clause: Clause 4.1 PED" in header
    assert "Type: waiting_period" in header


def test_chunk_pages_produces_chunks_with_contextual_metadata():
    pages = [
        PageText(
            page_number=1,
            text="SECTION 1 BENEFITS\n1.1 Room Rent\nRoom rent covered up to Rs 5000 per day.\n"
                 "SECTION 2 EXCLUSIONS\nCosmetic treatment is strictly excluded.",
        )
    ]
    chunks = chunk_pages(pages, policy_name="Care Plus")
    assert len(chunks) >= 1
    assert all(isinstance(c, Chunk) for c in chunks)
    assert any(c.clause_type in ("limit", "coverage") for c in chunks)
    assert any(c.clause_type == "exclusion" for c in chunks)
    assert all(c.contextual_header is not None for c in chunks)
    assert any("Care Plus" in c.contextualized_content for c in chunks)
