"""
Query-Aware Dynamic Prompt Assembly with DSPy-Style Optimization.
Based on DSPy (Stanford NLP, 2024) and AdalFlow (2024).

Dynamically selects and composes prompt modules based on:
- Query complexity class (Adaptive-RAG)
- CRAG retrieval regime (evidence quality)
- Patient context availability
- OKF canonical knowledge presence
- Graph reasoning paths availability

Features:
1. Modular Prompt Signatures: Each prompt component (citation style,
   reasoning depth, personalization, OKF injection) is a composable module.
2. Complexity-Adaptive Depth: Simple queries get concise direct-answer prompts;
   multi-hop queries get chain-of-thought decomposition instructions.
3. Evidence-Quality-Adaptive Hedging: When CRAG regime is AMBIGUOUS, the prompt
   instructs the LLM to explicitly state uncertainty and cite gaps.
4. Cached Prompt Configurations: Stores winning prompt assemblies per query-type
   for fast re-use.
"""
import logging
from dataclasses import dataclass, field
from typing import Optional

from rag.evidence_verifier import INSUFFICIENT_EVIDENCE_MSG

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Prompt Module Definitions (DSPy-style composable signatures)
# ─────────────────────────────────────────────────────────────────────────────

CORE_IDENTITY = """You are a healthcare insurance policy expert assistant with deep knowledge of Indian and International health insurance regulations, IRDAI guidelines, and policy interpretation."""

CITATION_MODULE_STRICT = """CITATION RULES (Mandatory):
- Every factual claim MUST cite its source as [Page X, Section Y].
- Quote monetary amounts (Rs/INR/₹), timeframes, and percentages EXACTLY as stated in evidence.
- If multiple evidence sources support a claim, cite all of them.
- NEVER fabricate or interpolate figures not present in the evidence."""

CITATION_MODULE_RELAXED = """CITATION RULES:
- Cite key factual claims with [Page X, Section Y] where possible.
- Prefer quoting exact amounts and timeframes from evidence."""

REASONING_MODULE_SIMPLE = """ANSWER FORMAT:
- Provide a direct, concise answer to the question.
- State the key fact, then cite the supporting evidence.
- Keep the response focused and under 200 words."""

REASONING_MODULE_CONDITIONAL = """ANSWER FORMAT:
- Structure your answer around the specific condition or scenario asked about.
- State: (1) Whether covered, (2) Any waiting periods, (3) Sub-limits or co-payments, (4) Relevant exclusions.
- For each point, cite the exact evidence source."""

REASONING_MODULE_COMPARATIVE = """ANSWER FORMAT:
- Present a structured comparison using clear categories.
- For each difference: state the OLD value → NEW value with exact citations.
- Highlight which version is more favorable and why.
- Organize by: Coverage Changes, Limit Changes, Waiting Period Changes, New Additions, Removals."""

REASONING_MODULE_MULTIHOP = """ANSWER FORMAT (Multi-Part Question):
- Decompose the question into its constituent parts.
- Answer each sub-question separately with dedicated evidence citations.
- Synthesize a final combined answer connecting all parts.
- Use a numbered list for clarity.
- Explicitly state if any sub-question lacks sufficient evidence."""

HEDGING_MODULE_CONFIDENT = """CONFIDENCE INSTRUCTIONS:
- Provide definitive answers based on the evidence.
- Use clear, authoritative language."""

HEDGING_MODULE_UNCERTAIN = """CONFIDENCE INSTRUCTIONS:
- Evidence quality is partial or ambiguous for this query.
- Explicitly state what IS supported by evidence and what is UNCLEAR.
- Use hedging language: "Based on available evidence...", "The policy appears to..."
- Flag any gaps: "Note: The retrieved evidence does not explicitly address [X]."
- Do NOT fill gaps with assumptions or general insurance knowledge."""

HEDGING_MODULE_ABSTAIN = f"""CONFIDENCE INSTRUCTIONS:
- Evidence is insufficient to answer this question reliably.
- Respond with EXACTLY: "{INSUFFICIENT_EVIDENCE_MSG}"
- Do NOT attempt to answer from general knowledge."""

PERSONALIZATION_MODULE = """PERSONALIZATION INSTRUCTIONS:
- Use the patient/policyholder details provided below to personalize your answer.
- Calculate waiting period eligibility based on their policy start date.
- Flag if any pre-existing diseases affect the coverage being asked about.
- Mention relevant family members if applicable to the question.
- Reference their claim history if relevant."""

OKF_MODULE = """OKF CANONICAL KNOWLEDGE INSTRUCTIONS:
- The OKF (Open Knowledge Format) entries below contain verified, canonical rules.
- These rules take PRECEDENCE over ambiguous evidence interpretations.
- If OKF rules specify a waiting period, sub-limit, or eligibility criterion,
  state it explicitly and verify that your answer complies with it.
- If the evidence contradicts an OKF canonical rule, note the discrepancy."""

GRAPH_REASONING_MODULE = """GRAPH STRUCTURAL CONTEXT:
- Knowledge graph traversal has identified structurally related clauses.
- The reasoning paths below show how entities (conditions, waiting periods, sub-limits)
  connect across different policy clauses.
- Use these structural relationships to provide a more complete picture.
- Cite graph-discovered clauses alongside direct evidence."""

ZERO_HALLUCINATION_GUARD_MODULE = """NEGATIVE CONSTRAINTS & ZERO-HALLUCINATION RULES (Mandatory):
1. STRICT NEGATIVE CONSTRAINT: Never assume, extrapolate, or generalize coverage. If a policy clause states X is covered, do NOT assume related procedure Y is covered unless explicitly written in evidence.
2. NUMERICAL & DURATION FIDELITY: Only quote monetary figures (Rs., INR, ₹), percentages (%), or durations (days/months/years) that appear VERBATIM in Document Evidence. If a limit is not stated in evidence, explicitly say: "No specific limit is stated in the retrieved policy text."
3. CITATION VERIFIABILITY: Every single claim must have a valid [Page X, Section Y] citation pointing to the exact evidence chunk supporting it. Do NOT fabricate page numbers or sections.
4. HONEST UNCERTAINTY: If the retrieved excerpts do not explicitly confirm an answer, explicitly declare what is unknown rather than guessing.
"""


@dataclass
class PromptConfig:
    """Assembled prompt configuration with all selected modules."""
    query_type: str
    crag_regime: str
    system_prompt: str
    has_personalization: bool = False
    has_okf: bool = False
    has_graph_paths: bool = False
    modules_used: list[str] = field(default_factory=list)


def assemble_system_prompt(
    query_complexity: str,
    crag_regime: str = "correct",
    has_patient_context: bool = False,
    has_okf_context: bool = False,
    has_graph_paths: bool = False,
) -> PromptConfig:
    """
    Dynamically assembles an optimized system prompt by selecting and
    composing the appropriate modules based on query characteristics.

    Args:
        query_complexity: One of 'simple', 'conditional', 'comparative', 'multi_hop'
        crag_regime: One of 'correct', 'ambiguous', 'incorrect'
        has_patient_context: Whether patient profile is available
        has_okf_context: Whether OKF canonical knowledge is available
        has_graph_paths: Whether graph reasoning paths are available

    Returns:
        PromptConfig with the assembled system prompt and metadata.
    """
    modules_used = ["core_identity"]
    parts = [CORE_IDENTITY]

    # ── Citation Module ──────────────────────────────────────────────
    if query_complexity in ("conditional", "comparative", "multi_hop"):
        parts.append(CITATION_MODULE_STRICT)
        modules_used.append("citation_strict")
    else:
        parts.append(CITATION_MODULE_RELAXED)
        modules_used.append("citation_relaxed")

    # ── Reasoning Depth Module ───────────────────────────────────────
    reasoning_map = {
        "simple": (REASONING_MODULE_SIMPLE, "reasoning_simple"),
        "conditional": (REASONING_MODULE_CONDITIONAL, "reasoning_conditional"),
        "comparative": (REASONING_MODULE_COMPARATIVE, "reasoning_comparative"),
        "multi_hop": (REASONING_MODULE_MULTIHOP, "reasoning_multihop"),
    }
    reasoning_module, reasoning_name = reasoning_map.get(
        query_complexity, (REASONING_MODULE_SIMPLE, "reasoning_simple")
    )
    parts.append(reasoning_module)
    modules_used.append(reasoning_name)

    # ── Hedging / Confidence Module ──────────────────────────────────
    if crag_regime == "incorrect":
        parts.append(HEDGING_MODULE_ABSTAIN)
        modules_used.append("hedging_abstain")
    elif crag_regime == "ambiguous":
        parts.append(HEDGING_MODULE_UNCERTAIN)
        modules_used.append("hedging_uncertain")
    else:
        parts.append(HEDGING_MODULE_CONFIDENT)
        modules_used.append("hedging_confident")

    # ── Personalization Module ───────────────────────────────────────
    if has_patient_context:
        parts.append(PERSONALIZATION_MODULE)
        modules_used.append("personalization")

    # ── OKF Canonical Knowledge Module ───────────────────────────────
    if has_okf_context:
        parts.append(OKF_MODULE)
        modules_used.append("okf_canonical")

    # ── Graph Reasoning Module ───────────────────────────────────────
    if has_graph_paths:
        parts.append(GRAPH_REASONING_MODULE)
        modules_used.append("graph_reasoning")

    # ── Zero-Hallucination Negative Constraints ─────────────────────
    parts.append(ZERO_HALLUCINATION_GUARD_MODULE)
    modules_used.append("zero_hallucination_guard")

    # ── Insufficient Evidence Fallback (always present) ──────────────
    parts.append(
        f'\nIf the evidence does not contain sufficient information, reply with EXACTLY:\n"{INSUFFICIENT_EVIDENCE_MSG}"'
    )
    modules_used.append("fallback_instruction")

    system_prompt = "\n\n".join(parts)

    config = PromptConfig(
        query_type=query_complexity,
        crag_regime=crag_regime,
        system_prompt=system_prompt,
        has_personalization=has_patient_context,
        has_okf=has_okf_context,
        has_graph_paths=has_graph_paths,
        modules_used=modules_used,
    )

    logger.info(
        "Assembled dynamic prompt: complexity=%s, crag=%s, modules=%s",
        query_complexity,
        crag_regime,
        modules_used,
    )
    return config


# ─────────────────────────────────────────────────────────────────────────────
# Prompt Configuration Cache (lightweight in-memory memoization)
# ─────────────────────────────────────────────────────────────────────────────

_prompt_cache: dict[str, PromptConfig] = {}


def get_cached_prompt(
    query_complexity: str,
    crag_regime: str = "correct",
    has_patient_context: bool = False,
    has_okf_context: bool = False,
    has_graph_paths: bool = False,
) -> PromptConfig:
    """
    Returns a cached prompt config if one exists for the given parameter
    combination, otherwise assembles a new one and caches it.
    """
    cache_key = f"{query_complexity}|{crag_regime}|{has_patient_context}|{has_okf_context}|{has_graph_paths}"

    if cache_key not in _prompt_cache:
        _prompt_cache[cache_key] = assemble_system_prompt(
            query_complexity=query_complexity,
            crag_regime=crag_regime,
            has_patient_context=has_patient_context,
            has_okf_context=has_okf_context,
            has_graph_paths=has_graph_paths,
        )

    return _prompt_cache[cache_key]
