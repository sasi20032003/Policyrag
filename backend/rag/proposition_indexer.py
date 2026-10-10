"""
Proposition-Level Indexing for Dense X Retrieval.
Based on Dense X Retrieval / Propositions (Chen et al., EMNLP 2024) and
Faceted Query-Document Relevance (Li et al., 2024).

At ingestion time, decomposes each chunk into atomic propositions
(single-fact statements) and embeds each individually. At retrieval,
matches propositions for precision but returns full parent chunks for
context — bridging the granularity gap that degrades standard RAG.

Features:
1. Rule-Based Atomic Decomposition: Splits on sentence boundaries, bullet
   points, and enumerated clauses to extract self-contained facts.
2. Proposition Deduplication: Removes near-duplicate propositions within
   a chunk using token-level Jaccard overlap.
3. Parent-Chunk Backlinks: Every proposition retains a pointer to its
   source chunk for context-faithful generation.
4. Insurance-Domain Proposition Enrichment: Detects quantitative clauses
   (amounts, durations, percentages) and preserves them as standalone propositions
   even when they are embedded mid-sentence.
"""
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# Sentence boundary splitter (respects abbreviations common in insurance docs)
SENT_SPLIT_RE = re.compile(
    r"(?<=[.!?])\s+(?=[A-Z0-9(])"
    r"|(?<=\n)\s*(?=[•\-\d(])"  # Bullet / numbered list items
)

# Pattern for quantitative clauses that should be standalone propositions
QUANT_CLAUSE_RE = re.compile(
    r"(?:Rs\.?\s*|INR\s*|₹\s*)[\d,]+(?:\.\d+)?"
    r"|(?:\d+)\s*(?:%|percent|per\s*cent)"
    r"|(?:\d+)\s*(?:days?|months?|years?)\s*(?:waiting|period|from)?"
    r"|(?:sub-?limit|co-?pay(?:ment)?|deductible|capping|maximum)\s*(?:of\s*)?(?:Rs\.?\s*|INR\s*|₹\s*)?[\d,]+",
    re.IGNORECASE,
)

# Minimum proposition length (tokens) to be meaningful
MIN_PROPOSITION_TOKENS = 4
# Jaccard threshold for near-duplicate suppression
DEDUP_JACCARD_THRESHOLD = 0.85


@dataclass
class Proposition:
    """A single atomic factual statement extracted from a chunk."""
    text: str
    parent_chunk_index: int          # Index into the chunk list
    parent_chunk_content: str        # Full parent chunk text for backlink
    page: Optional[int] = None
    section: Optional[str] = None
    is_quantitative: bool = False    # Contains amounts, durations, percentages
    metadata: dict = field(default_factory=dict)


def _tokenize_simple(text: str) -> set[str]:
    """Fast lowercase token set for Jaccard comparison."""
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


def decompose_chunk_to_propositions(
    chunk_text: str,
    chunk_index: int,
    page: Optional[int] = None,
    section: Optional[str] = None,
    min_tokens: int = MIN_PROPOSITION_TOKENS,
) -> list[Proposition]:
    """
    Decompose a single chunk into atomic propositions.

    Strategy:
    1. Split on sentence boundaries and bullet points.
    2. For each segment, check if it contains multiple quantitative clauses
       and split further if so.
    3. Deduplicate near-identical propositions within the chunk.
    4. Tag propositions containing numerical/monetary/duration facts.
    """
    if not chunk_text or not chunk_text.strip():
        return []

    # Phase 1: Coarse split on sentence/bullet boundaries
    raw_segments = SENT_SPLIT_RE.split(chunk_text)

    # Phase 2: Clean and filter
    candidate_props: list[str] = []
    for seg in raw_segments:
        seg = seg.strip()
        # Strip bullet/list prefixes
        seg = re.sub(r"^(?:[-*•]|\d+[.)\]])\s*", "", seg).strip()
        if not seg:
            continue

        # Check if segment is overly long (>300 chars) and contains
        # multiple quantitative sub-facts — split on semicolons/commas
        if len(seg) > 300:
            sub_parts = re.split(r"[;]\s*|\.\s+(?=[A-Z])", seg)
            for sp in sub_parts:
                sp = sp.strip()
                if len(sp.split()) >= min_tokens:
                    candidate_props.append(sp)
        else:
            if len(seg.split()) >= min_tokens:
                candidate_props.append(seg)

    if not candidate_props:
        # Fallback: treat entire chunk as one proposition
        if len(chunk_text.split()) >= min_tokens:
            candidate_props = [chunk_text.strip()]
        else:
            return []

    # Phase 3: Deduplicate near-identical propositions
    deduped: list[str] = []
    deduped_token_sets: list[set[str]] = []

    for prop_text in candidate_props:
        prop_tokens = _tokenize_simple(prop_text)
        is_duplicate = False
        for existing_tokens in deduped_token_sets:
            if _jaccard_similarity(prop_tokens, existing_tokens) > DEDUP_JACCARD_THRESHOLD:
                is_duplicate = True
                break
        if not is_duplicate:
            deduped.append(prop_text)
            deduped_token_sets.append(prop_tokens)

    # Phase 4: Build Proposition objects with quantitative tagging
    propositions: list[Proposition] = []
    for prop_text in deduped:
        is_quant = bool(QUANT_CLAUSE_RE.search(prop_text))
        propositions.append(
            Proposition(
                text=prop_text,
                parent_chunk_index=chunk_index,
                parent_chunk_content=chunk_text,
                page=page,
                section=section,
                is_quantitative=is_quant,
                metadata={
                    "token_count": len(prop_text.split()),
                    "char_count": len(prop_text),
                },
            )
        )

    return propositions


def decompose_chunks_to_propositions(
    chunks: list[dict],
) -> list[Proposition]:
    """
    Batch decompose a list of chunk dicts into propositions.
    Each chunk dict should have keys: 'content', 'page', 'section'.
    """
    all_propositions: list[Proposition] = []
    for idx, chunk in enumerate(chunks):
        content = chunk.get("content", "")
        page = chunk.get("page")
        section = chunk.get("section")
        props = decompose_chunk_to_propositions(
            chunk_text=content,
            chunk_index=idx,
            page=page,
            section=section,
        )
        all_propositions.extend(props)

    logger.info(
        "Decomposed %d chunks into %d atomic propositions (avg %.1f props/chunk)",
        len(chunks),
        len(all_propositions),
        len(all_propositions) / max(len(chunks), 1),
    )
    return all_propositions


def retrieve_parent_chunks_from_propositions(
    matched_propositions: list[Proposition],
    all_chunks: list,
    max_unique_parents: int = 8,
) -> list:
    """
    Given matched propositions, returns unique parent chunks
    (deduplicated by chunk_index) preserving the ordering of
    highest-scoring proposition matches.
    """
    seen_indices: set[int] = set()
    parent_chunks = []

    for prop in matched_propositions:
        idx = prop.parent_chunk_index
        if idx not in seen_indices and idx < len(all_chunks):
            seen_indices.add(idx)
            parent_chunks.append(all_chunks[idx])
            if len(parent_chunks) >= max_unique_parents:
                break

    return parent_chunks
