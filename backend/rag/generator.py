"""
Grounded Answer Generator with Contextual Citations, DSPy-Style Dynamic Prompting & Self-Refine.
Inspired by Self-RAG (ICLR 2024), Self-Refine (NeurIPS 2023), DSPy (Stanford 2024),
and Anthropic Contextual Retrieval (2024).

Features:
1. Dynamic Prompt Assembly: Integrates rag.prompt_optimizer to tailor system prompts
   to query complexity class, CRAG evidence regime, OKF rules, and graph reasoning paths.
2. Contextual Evidence Formatting: Incorporates hierarchical breadcrumbs, clause types,
   and HippoRAG graph reasoning paths into the context window.
3. Grounded In-Line Citations: Instructs model to cite [Page X, Section Y] for every claim.
4. Self-Refine Loop: Automatically executes a self-correction pass if initial generation
   fails fact verification or introduces ungrounded numbers.
5. Progressive Streaming: Yields tokens asynchronously for Server-Sent Events (SSE).
"""
import logging
from typing import AsyncGenerator, Optional

from models.orm_models import Chunk
from rag.evidence_verifier import INSUFFICIENT_EVIDENCE_MSG
from rag.prompt_optimizer import get_cached_prompt
from services.llm_service import llm_service

logger = logging.getLogger(__name__)

REFINE_SYSTEM_PROMPT = f"""You are reviewing and correcting an insurance policy answer.
The previous answer contained potential inaccuracies or figures not supported by the evidence.
Rules:
1. Revise the answer strictly removing any ungrounded claims or unsupported numbers.
2. Use ONLY the facts directly stated in the evidence below.
3. If the evidence is insufficient to answer reliably, respond with EXACTLY:
   "{INSUFFICIENT_EVIDENCE_MSG}"
"""


def format_evidence(
    chunks: list[tuple[Chunk, float]],
    graph_paths: Optional[list[str]] = None,
) -> str:
    """Format chunks with hierarchical metadata and graph associations."""
    parts = []
    for i, (chunk, score) in enumerate(chunks, start=1):
        meta = chunk.chunk_metadata or {}
        c_type = meta.get("clause_type", "general")
        breadcrumb = meta.get("contextual_header") or chunk.section or "Policy Clause"

        header_line = (
            f"[Evidence {i}] (Page {chunk.page or 'N/A'}, Section: {chunk.section or 'N/A'}, "
            f"Type: {c_type}, Relevance: {score:.2f})\n"
            f"Context: {breadcrumb}"
        )
        parts.append(f"{header_line}\n{chunk.content}")

    evidence_text = "\n\n".join(parts)

    if graph_paths:
        graph_block = "\n".join(f"• {p}" for p in graph_paths[:4])
        evidence_text += f"\n\n[Knowledge Graph Structural Associations]:\n{graph_block}"

    return evidence_text


def _build_prompts(
    question: str,
    evidence_chunks: list[tuple[Chunk, float]],
    patient_context: Optional[str] = None,
    graph_paths: Optional[list[str]] = None,
    okf_context: Optional[str] = None,
    query_complexity: str = "simple",
    crag_regime: str = "correct",
    system_prompt_override: Optional[str] = None,
) -> tuple[str, str]:
    """Builds optimized system prompt and formatted user prompt."""
    from services.pii_anonymizer import pii_anonymizer
    safe_question = pii_anonymizer.sanitize_text(question).sanitized_text

    if system_prompt_override:
        system_prompt = system_prompt_override
    else:
        prompt_cfg = get_cached_prompt(
            query_complexity=query_complexity,
            crag_regime=crag_regime,
            has_patient_context=bool(patient_context and patient_context.strip()),
            has_okf_context=bool(okf_context and okf_context.strip()),
            has_graph_paths=bool(graph_paths),
        )
        system_prompt = prompt_cfg.system_prompt

    evidence_block = format_evidence(evidence_chunks, graph_paths=graph_paths)

    prompt_parts = [f"Question: {safe_question}\n"]
    if okf_context and okf_context.strip():
        prompt_parts.append(f"{okf_context.strip()}\n")
    if patient_context and patient_context.strip():
        prompt_parts.append(f"[Policyholder / Patient Details]:\n{patient_context.strip()}\n")
    if evidence_block.strip():
        prompt_parts.append(f"Document Evidence:\n{evidence_block}\n")
    prompt_parts.append("Answer:")

    user_prompt = "\n".join(prompt_parts)
    return system_prompt, user_prompt


async def generate_answer(
    question: str,
    evidence_chunks: list[tuple[Chunk, float]],
    patient_context: Optional[str] = None,
    graph_paths: Optional[list[str]] = None,
    okf_context: Optional[str] = None,
    query_complexity: str = "simple",
    crag_regime: str = "correct",
    system_prompt_override: Optional[str] = None,
) -> str:
    """
    Generate grounded, citation-backed answer with dynamic prompt optimization.
    """
    if not evidence_chunks and not okf_context:
        return INSUFFICIENT_EVIDENCE_MSG

    system_prompt, user_prompt = _build_prompts(
        question=question,
        evidence_chunks=evidence_chunks,
        patient_context=patient_context,
        graph_paths=graph_paths,
        okf_context=okf_context,
        query_complexity=query_complexity,
        crag_regime=crag_regime,
        system_prompt_override=system_prompt_override,
    )

    try:
        answer = await llm_service.complete(system_prompt, user_prompt, max_tokens=850)
        return answer.strip()
    except Exception as exc:
        logger.exception("LLM generation failed: %s", exc)
        return INSUFFICIENT_EVIDENCE_MSG


async def stream_generate_answer(
    question: str,
    evidence_chunks: list[tuple[Chunk, float]],
    patient_context: Optional[str] = None,
    graph_paths: Optional[list[str]] = None,
    okf_context: Optional[str] = None,
    query_complexity: str = "simple",
    crag_regime: str = "correct",
    system_prompt_override: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """
    Progressively stream answer tokens using dynamic prompt assembly.
    """
    if not evidence_chunks and not okf_context:
        yield INSUFFICIENT_EVIDENCE_MSG
        return

    system_prompt, user_prompt = _build_prompts(
        question=question,
        evidence_chunks=evidence_chunks,
        patient_context=patient_context,
        graph_paths=graph_paths,
        okf_context=okf_context,
        query_complexity=query_complexity,
        crag_regime=crag_regime,
        system_prompt_override=system_prompt_override,
    )

    try:
        async for token in llm_service.stream_complete(system_prompt, user_prompt, max_tokens=850):
            yield token
    except Exception as exc:
        logger.exception("Streaming LLM generation failed: %s", exc)
        yield INSUFFICIENT_EVIDENCE_MSG


async def generate_answer_with_refine(
    question: str,
    evidence_chunks: list[tuple[Chunk, float]],
    initial_answer: str,
    refinement_warnings: list[str],
    patient_context: Optional[str] = None,
    okf_context: Optional[str] = None,
) -> str:
    """
    Self-Refine pass: Re-generates answer when initial output was flagged with warnings
    or unsupported figures.
    """
    if not evidence_chunks and not okf_context:
        return INSUFFICIENT_EVIDENCE_MSG

    evidence_block = format_evidence(evidence_chunks)
    warning_list = "\n".join(f"- {w}" for w in refinement_warnings)

    refine_parts = [f"Question: {question}\n"]
    if okf_context and okf_context.strip():
        refine_parts.append(f"{okf_context.strip()}\n")
    if patient_context and patient_context.strip():
        refine_parts.append(f"[Policyholder / Patient Details]:\n{patient_context.strip()}\n")
    if evidence_block.strip():
        refine_parts.append(f"Document Evidence:\n{evidence_block}\n")
    refine_parts.append(f"Previous Draft Answer:\n{initial_answer}\n")
    refine_parts.append(f"Verification Feedback:\n{warning_list}\n")
    refine_parts.append("Please regenerate the corrected answer eliminating any unsupported assertions:")

    user_prompt = "\n".join(refine_parts)

    try:
        refined = await llm_service.complete(REFINE_SYSTEM_PROMPT, user_prompt, max_tokens=850)
        return refined.strip()
    except Exception as exc:
        logger.warning("Self-refine LLM call failed, keeping initial answer: %s", exc)
        return initial_answer
