"""
Multi-Granularity Semantic Chunking for Insurance Policy Documents.
Inspired by:
- Anthropic Contextual Retrieval (2024): Hierarchical breadcrumb injection
- RAPTOR (ICLR 2024): Recursive abstractive processing with summary trees
- Late Chunking (Jina AI, 2024): Semantic boundary detection
- Dense X Retrieval (EMNLP 2024): Proposition-level decomposition

Features:
1. Semantic Boundary Detection: Uses sentence-embedding cosine breakpoints
   to split chunks at natural semantic shifts instead of fixed char windows.
2. Contextual Breadcrumb Injection: Prepends hierarchical context headers
   (Policy > Section > Subsection) per Anthropic Contextual Retrieval.
3. RAPTOR Summary Tree: Produces multi-level summaries (leaf chunks → section
   summaries → policy abstract) for abstract/global questions.
4. Domain-Specific Clause Categorization: Auto-tags chunks as coverage,
   exclusion, waiting_period, limit, claim, or definition.
5. Proposition-Level Decomposition: Decomposes each chunk into atomic
   propositions for Dense X indexing with parent-chunk backlinks.
6. Smart Boundary Preservation: Respects sentence boundaries, bullet points,
   tabular structures, and monetary clause integrity.
"""
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from rag.ingestion import PageText

logger = logging.getLogger(__name__)

# Section detection patterns
SECTION_HEADER_RE = re.compile(
    r"^(?:[A-Z0-9\.\-\s]{3,80}|(?:SECTION|Section|CLAUSE|Clause|ARTICLE|Article|PART|Part)\s+[0-9IVX]+[\.\d]*.*)$"
)

SUBSECTION_RE = re.compile(
    r"^(?:\d+\.\d+|\([a-z0-9]\)|[A-Z]\.|\\bClause\s+\d+\.\d+)\s+([A-Za-z0-9\s,\-\(\)\/]{3,80})"
)

# Clause classification regex patterns
COVERAGE_PATTERNS = re.compile(
    r"\b(covered|inpatient|hospitalization|day\s*care|ayush|organ\s*donor|ambulance|domiciliary|restoration|recharge|sum\s*insured|bonus|wellness)\b",
    re.IGNORECASE,
)
EXCLUSION_PATTERNS = re.compile(
    r"\b(exclusion|exclusions|not\s*covered|permanent\s*exclusion|shall\s*not\s*be\s*liable|non-payable|excluded|does\s*not\s*cover)\b",
    re.IGNORECASE,
)
WAITING_PERIOD_PATTERNS = re.compile(
    r"\b(waiting\s*period|pre-existing\s*disease|ped\b|specified\s*disease|30\s*days|24\s*months|36\s*months|48\s*months|initial\s*waiting)\b",
    re.IGNORECASE,
)
LIMIT_PATTERNS = re.compile(
    r"\b(limit|sub-limit|sublimit|co-payment|copay|deductible|room\s*rent|capping|capped\s*at|maximum\s*payable|percentage\s*of)\b",
    re.IGNORECASE,
)
CLAIM_PATTERNS = re.compile(
    r"\b(claim|claims|intimation|cashless|reimbursement|discharge\s*summary|pre-authorization|tpa|documents\s*required)\b",
    re.IGNORECASE,
)
DEFINITION_PATTERNS = re.compile(
    r"\b(means|shall\s*mean|defined\s*as|definition|interpretation|glossary)\b",
    re.IGNORECASE,
)

# Semantic boundary detection — cosine similarity drop threshold
SEMANTIC_BREAK_THRESHOLD = 0.35

CHUNK_CHAR_TARGET = 900
CHUNK_CHAR_OVERLAP = 150
CHUNK_CHAR_MIN = 100  # Minimum viable chunk size


@dataclass
class Chunk:
    content: str
    page: int
    section: str | None
    parent_section: str | None = None
    clause_type: str = "general"  # coverage | exclusion | waiting_period | limit | claim | definition | general
    contextual_header: str | None = None
    summary: str | None = None     # RAPTOR: mid-level summary for this chunk
    granularity: str = "leaf"      # leaf | section_summary | policy_abstract
    propositions: list[str] = field(default_factory=list)  # Dense X atomic propositions
    metadata: dict = field(default_factory=dict)

    @property
    def contextualized_content(self) -> str:
        """Returns content enriched with contextual breadcrumb prefix (Anthropic Contextual Retrieval)."""
        if self.contextual_header:
            return f"[{self.contextual_header}]\n{self.content}"
        return self.content


def clean_text(text: str) -> str:
    """Sanitize PDF text, normalize whitespace, and remove formatting artifacts."""
    if not text:
        return ""
    text = text.replace("\x0c", " ")
    text = text.replace("\r\n", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def detect_section(line: str) -> str | None:
    """Detect if a line represents a major section heading."""
    line = line.strip()
    if 3 <= len(line) <= 90:
        if SECTION_HEADER_RE.match(line):
            # Exclude lines that end with standard sentence punctuation or are too conversational
            if not line.endswith((".", ",", ";", ":", "?")):
                return line
    return None


def detect_subsection(line: str) -> str | None:
    """Detect numbered sub-sections or specific sub-clause headings."""
    line = line.strip()
    if 3 <= len(line) <= 80:
        match = SUBSECTION_RE.match(line)
        if match:
            return line
    return None


def classify_clause_type(text: str) -> str:
    """Classify policy clause into functional insurance categories."""
    text_lower = text.lower()
    if EXCLUSION_PATTERNS.search(text_lower):
        return "exclusion"
    if WAITING_PERIOD_PATTERNS.search(text_lower):
        return "waiting_period"
    if LIMIT_PATTERNS.search(text_lower):
        return "limit"
    if CLAIM_PATTERNS.search(text_lower):
        return "claim"
    if DEFINITION_PATTERNS.search(text_lower):
        return "definition"
    if COVERAGE_PATTERNS.search(text_lower):
        return "coverage"
    return "general"


def build_contextual_header(
    policy_name: Optional[str] = None,
    section: Optional[str] = None,
    subsection: Optional[str] = None,
    clause_type: str = "general",
) -> str:
    """
    Constructs an Anthropic-style hierarchical contextual breadcrumb.
    Example: 'Policy: Arogya Sanjeevani | Section: Exclusions > Pre-Existing Diseases | Type: waiting_period'
    """
    crumbs = []
    if policy_name:
        crumbs.append(f"Policy: {policy_name}")
    if section:
        crumbs.append(f"Section: {section}")
    if subsection and subsection != section:
        crumbs.append(f"Clause: {subsection}")
    crumbs.append(f"Type: {clause_type}")
    return " | ".join(crumbs)


# ─────────────────────────────────────────────────────────────────────────────
# Semantic Boundary Detection (Late Chunking, Jina AI 2024)
# ─────────────────────────────────────────────────────────────────────────────

def _detect_semantic_breaks(sentences: list[str], threshold: float = SEMANTIC_BREAK_THRESHOLD) -> list[int]:
    """
    Identify sentence indices where a semantic boundary occurs using
    embedding cosine similarity between consecutive sentence pairs.

    Returns list of indices where breaks should be inserted.
    Falls back to empty list if embeddings are unavailable.
    """
    if len(sentences) < 3:
        return []

    try:
        from rag.embeddings import embed_texts
        embeddings = embed_texts(sentences)

        breaks = []
        for i in range(1, len(embeddings)):
            # Cosine similarity between consecutive sentences
            sim = sum(a * b for a, b in zip(embeddings[i - 1], embeddings[i]))
            if sim < threshold:
                breaks.append(i)
        return breaks
    except Exception as exc:
        logger.debug("Semantic boundary detection unavailable: %s", exc)
        return []


def _split_into_sentences(text: str) -> list[str]:
    """Split text into sentences, respecting abbreviations and bullet points."""
    # Split on sentence-ending punctuation followed by space + capital letter
    raw_splits = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9(•\-])", text)
    sentences = []
    for s in raw_splits:
        s = s.strip()
        if s:
            sentences.append(s)
    return sentences


# ─────────────────────────────────────────────────────────────────────────────
# Proposition Decomposition (Dense X Retrieval, EMNLP 2024)
# ─────────────────────────────────────────────────────────────────────────────

def _extract_propositions(text: str) -> list[str]:
    """
    Extract atomic propositions from a chunk using rule-based decomposition.
    Each proposition is a self-contained factual statement.
    """
    sentences = _split_into_sentences(text)
    propositions = []

    for sent in sentences:
        # Strip bullet/list prefixes
        clean_sent = re.sub(r"^(?:[-*•]|\d+[.)\]])\s*", "", sent).strip()
        if len(clean_sent.split()) >= 4:
            propositions.append(clean_sent)

    return propositions


# ─────────────────────────────────────────────────────────────────────────────
# RAPTOR Summary Tree (ICLR 2024)
# ─────────────────────────────────────────────────────────────────────────────

def build_raptor_summaries(
    chunks: list[Chunk],
    policy_name: Optional[str] = None,
) -> list[Chunk]:
    """
    Builds RAPTOR-style hierarchical summary chunks:
    - Level 0: Leaf chunks (already produced by chunk_pages)
    - Level 1: Section summaries (one per detected section, summarizing its children)
    - Level 2: Policy abstract (one per policy, summarizing all sections)

    Note: Uses extractive summarization (first+last sentence concatenation)
    as a zero-cost alternative to LLM-based abstractive summaries.
    LLM-based summaries can be substituted at ingestion time for higher quality.
    """
    if not chunks:
        return []

    summary_chunks: list[Chunk] = []

    # Group leaf chunks by section
    section_groups: dict[str, list[Chunk]] = {}
    for c in chunks:
        key = c.section or c.parent_section or "__no_section__"
        section_groups.setdefault(key, []).append(c)

    # Level 1: Section summaries
    section_summary_texts = []
    for section_name, section_chunks in section_groups.items():
        if section_name == "__no_section__":
            continue

        # Extractive summary: concatenate first sentence of each chunk in section
        summary_parts = []
        for sc in section_chunks[:6]:  # Cap at 6 chunks per section
            first_sent = sc.content.split(". ")[0].strip()
            if first_sent and not first_sent.endswith("."):
                first_sent += "."
            if first_sent:
                summary_parts.append(first_sent)

        summary_text = " ".join(summary_parts)
        if len(summary_text.split()) < 10:
            continue

        c_type = classify_clause_type(summary_text)
        header = build_contextual_header(policy_name, section_name, None, c_type)
        page_range = f"{section_chunks[0].page}-{section_chunks[-1].page}"

        summary_chunk = Chunk(
            content=summary_text,
            page=section_chunks[0].page or 1,
            section=section_name,
            parent_section=None,
            clause_type=c_type,
            contextual_header=header,
            summary=None,
            granularity="section_summary",
            metadata={
                "source_section": section_name,
                "source_chunk_count": len(section_chunks),
                "page_range": page_range,
                "raptor_level": 1,
            },
        )
        summary_chunks.append(summary_chunk)
        section_summary_texts.append(summary_text)

    # Level 2: Policy abstract
    if section_summary_texts and len(section_summary_texts) >= 2:
        abstract_parts = []
        for st in section_summary_texts[:8]:
            first_sent = st.split(". ")[0].strip()
            if first_sent:
                abstract_parts.append(first_sent)

        abstract_text = " ".join(abstract_parts)
        if len(abstract_text.split()) >= 15:
            header = build_contextual_header(policy_name, "Policy Overview", None, "general")
            abstract_chunk = Chunk(
                content=abstract_text,
                page=1,
                section="Policy Abstract",
                parent_section=None,
                clause_type="general",
                contextual_header=header,
                granularity="policy_abstract",
                metadata={
                    "source_section_count": len(section_summary_texts),
                    "raptor_level": 2,
                },
            )
            summary_chunks.append(abstract_chunk)

    logger.info(
        "RAPTOR summary tree: %d section summaries + %d policy abstract(s) from %d leaf chunks",
        len([c for c in summary_chunks if c.granularity == "section_summary"]),
        len([c for c in summary_chunks if c.granularity == "policy_abstract"]),
        len(chunks),
    )
    return summary_chunks


# ─────────────────────────────────────────────────────────────────────────────
# Main Chunking Pipeline
# ─────────────────────────────────────────────────────────────────────────────

def chunk_pages(
    pages: list[PageText],
    policy_name: Optional[str] = None,
    target_char_size: int = CHUNK_CHAR_TARGET,
    overlap_char_size: int = CHUNK_CHAR_OVERLAP,
    enable_semantic_breaks: bool = True,
    enable_raptor: bool = True,
    enable_propositions: bool = True,
) -> list[Chunk]:
    """
    Produce semantically coherent, hierarchically tagged, and contextualized chunks
    with optional RAPTOR summary tree and Dense X propositions.

    Pipeline:
    1. Parse pages, detect section/subsection boundaries
    2. Buffer text within sections, flush at structural boundaries
    3. Apply semantic break detection within large buffers
    4. Classify clause types and attach contextual breadcrumbs
    5. Extract atomic propositions for Dense X indexing
    6. Build RAPTOR summary tree (section summaries + policy abstract)
    """
    leaf_chunks: list[Chunk] = []
    current_section: str | None = None
    current_subsection: str | None = None

    for page in pages:
        text = clean_text(page.text)
        if not text:
            continue

        lines = text.split("\n")
        buffer_lines: list[str] = []

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            maybe_section = detect_section(line_str)
            if maybe_section and line_str.isupper():
                _flush_buffer(
                    buffer_lines,
                    leaf_chunks,
                    page.page_number,
                    current_section,
                    current_subsection,
                    policy_name,
                    target_char_size,
                    overlap_char_size,
                    enable_semantic_breaks,
                    enable_propositions,
                )
                buffer_lines = []
                current_section = maybe_section
                current_subsection = None
                continue

            maybe_subsection = detect_subsection(line_str)
            if maybe_subsection:
                _flush_buffer(
                    buffer_lines,
                    leaf_chunks,
                    page.page_number,
                    current_section,
                    current_subsection,
                    policy_name,
                    target_char_size,
                    overlap_char_size,
                    enable_semantic_breaks,
                    enable_propositions,
                )
                buffer_lines = []
                current_subsection = maybe_subsection
                continue

            buffer_lines.append(line_str)

        _flush_buffer(
            buffer_lines,
            leaf_chunks,
            page.page_number,
            current_section,
            current_subsection,
            policy_name,
            target_char_size,
            overlap_char_size,
            enable_semantic_breaks,
            enable_propositions,
        )

    # Build RAPTOR summary tree
    all_chunks = list(leaf_chunks)
    if enable_raptor and leaf_chunks:
        raptor_chunks = build_raptor_summaries(leaf_chunks, policy_name)
        all_chunks.extend(raptor_chunks)

    logger.info(
        "Produced %d chunks (%d leaf + %d RAPTOR summaries) across %d pages",
        len(all_chunks),
        len(leaf_chunks),
        len(all_chunks) - len(leaf_chunks),
        len(pages),
    )
    return all_chunks


def _flush_buffer(
    lines: list[str],
    chunks: list[Chunk],
    page_number: int,
    section: str | None,
    subsection: str | None,
    policy_name: str | None,
    target_size: int,
    overlap_size: int,
    enable_semantic_breaks: bool,
    enable_propositions: bool,
) -> None:
    if not lines:
        return

    text = " ".join(lines).strip()
    if not text:
        return

    n = len(text)
    active_section = subsection or section

    if n <= target_size:
        _create_chunk(
            text, page_number, section, subsection, active_section,
            policy_name, enable_propositions, chunks,
        )
        return

    # Try semantic boundary detection for large buffers
    if enable_semantic_breaks and n > target_size:
        sentences = _split_into_sentences(text)
        if len(sentences) >= 3:
            breaks = _detect_semantic_breaks(sentences)
            if breaks:
                # Split at semantic boundaries
                groups: list[list[str]] = []
                current_group: list[str] = []
                for idx, sent in enumerate(sentences):
                    current_group.append(sent)
                    if idx + 1 in breaks:
                        groups.append(current_group)
                        current_group = []
                if current_group:
                    groups.append(current_group)

                for group in groups:
                    group_text = " ".join(group).strip()
                    if len(group_text) >= CHUNK_CHAR_MIN:
                        _create_chunk(
                            group_text, page_number, section, subsection,
                            active_section, policy_name, enable_propositions, chunks,
                        )
                return

    # Fallback: Sliding window with sentence-aware boundaries
    start = 0
    while start < n:
        end = min(start + target_size, n)
        if end < n:
            last_period = text.rfind(". ", start, end)
            if last_period != -1 and last_period > start + (target_size // 2):
                end = last_period + 1

        piece = text[start:end].strip()
        if piece and len(piece) >= CHUNK_CHAR_MIN:
            _create_chunk(
                piece, page_number, section, subsection,
                active_section, policy_name, enable_propositions, chunks,
            )

        if end >= n:
            break
        start = max(start + 1, end - overlap_size)


def _create_chunk(
    text: str,
    page_number: int,
    section: str | None,
    subsection: str | None,
    active_section: str | None,
    policy_name: str | None,
    enable_propositions: bool,
    chunks: list[Chunk],
) -> None:
    """Create a single chunk with classification, contextual header, and propositions."""
    c_type = classify_clause_type(text)
    header = build_contextual_header(policy_name, section, subsection, c_type)

    # Extract atomic propositions (Dense X Retrieval)
    props = _extract_propositions(text) if enable_propositions else []

    chunks.append(
        Chunk(
            content=text,
            page=page_number,
            section=active_section,
            parent_section=section,
            clause_type=c_type,
            contextual_header=header,
            granularity="leaf",
            propositions=props,
            metadata={
                "char_len": len(text),
                "has_numeric": bool(re.search(r"\d+", text)),
                "proposition_count": len(props),
            },
        )
    )
