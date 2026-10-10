"""
Master Agentic RAG Pipeline for PolicyGraph-RAG.
Orchestrates:
1. Temporal Version Validation (Temporal Filter)
2. Canonical Knowledge Resolution & Ontological Traversal (OKF Engine)
3. Query Complexity Classification & Expansion (Adaptive-RAG / HyDE)
4. Contextual Hybrid Retrieval with Multi-Granularity Indexing (Anthropic / Dense X / RAPTOR)
5. Knowledge Graph Associative Traversal & GraphRAG Community Detection (HippoRAG / GraphRAG)
6. Multi-Candidate Fusion & Cross-Encoder Reranking (BGE-Reranker / ColBERTv2)
7. Corrective RAG Evaluation (CRAG)
8. DSPy-Style Query-Aware Dynamic Prompt Assembly (Prompt Optimizer)
9. Speculative RAG Parallel Draft-then-Verify Architecture (Google 2024 / CoVe)
10. Atomic Claim Fact Verification & Conformal Confidence Calibration (MiniCheck / Conformal LM)
11. Self-Refine Correction Loop
12. Progressive SSE Streaming Generation
"""
import asyncio
import json
import logging
from datetime import date
from typing import AsyncGenerator, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.orm_models import Chunk, Evidence, PolicyVersion, QueryLog
from rag.confidence_calibrator import compute_semantic_convergence
from rag.crag_evaluator import CRAGRegime, evaluate_retrieval
from rag.evidence_verifier import (
    INSUFFICIENT_EVIDENCE_MSG,
    verify_answer_detailed,
)
from rag.generator import (
    generate_answer,
    generate_answer_with_refine,
    stream_generate_answer,
)
from rag.graph_retrieval import hippo_graph_retriever
from rag.hybrid_retrieval import hybrid_retrieve
from rag.okf_engine import okf_engine
from rag.prompt_optimizer import get_cached_prompt
from rag.query_engine import QueryComplexity, analyze_query
from rag.reranker import rerank
from rag.speculative_rag import generate_speculative_drafts
from rag.temporal_filter import get_valid_versions
from schemas.schemas import EvidenceItem

logger = logging.getLogger(__name__)


class AgenticRAGResult:
    def __init__(
        self,
        answer: str,
        policy_version: Optional[str],
        evidence: list[EvidenceItem],
        confidence: float,
        warnings: list[str],
        crag_regime: str,
        retrieval_strategy: str,
        sub_queries: list[str],
        factual_precision: float,
        reasoning_paths: list[str],
        okf_concepts: Optional[list[str]] = None,
        okf_rules_applied: Optional[dict] = None,
        calibrated_confidence: Optional[float] = None,
        should_abstain: bool = False,
        coverage_guarantee: Optional[float] = None,
        entropy_level: Optional[str] = None,
        speculative_drafts_count: int = 0,
        community_summaries: Optional[list[str]] = None,
        verified_claims: Optional[list[dict]] = None,
        merkle_root: Optional[str] = None,
        certificate_signature: Optional[str] = None,
        conformal_interval: Optional[list[float]] = None,
        topological_dispersion: Optional[float] = None,
        lattice_arbitration_status: Optional[str] = None,
    ):
        self.answer = answer
        self.policy_version = policy_version
        self.evidence = evidence
        self.confidence = confidence
        self.warnings = warnings
        self.crag_regime = crag_regime
        self.retrieval_strategy = retrieval_strategy
        self.sub_queries = sub_queries
        self.factual_precision = factual_precision
        self.reasoning_paths = reasoning_paths
        self.okf_concepts = okf_concepts or []
        self.okf_rules_applied = okf_rules_applied or {}
        self.calibrated_confidence = calibrated_confidence if calibrated_confidence is not None else confidence
        self.should_abstain = should_abstain
        self.coverage_guarantee = coverage_guarantee or 0.95
        self.entropy_level = entropy_level or "low"
        self.speculative_drafts_count = speculative_drafts_count
        self.community_summaries = community_summaries or []
        self.verified_claims = verified_claims or []
        self.merkle_root = merkle_root
        self.certificate_signature = certificate_signature
        self.conformal_interval = conformal_interval or [0.0, 1.0]
        self.topological_dispersion = topological_dispersion or 0.0
        self.lattice_arbitration_status = lattice_arbitration_status or "SATISFIED"


async def execute_agentic_rag(
    db: AsyncSession,
    question: str,
    policy_id: Optional[UUID] = None,
    as_of_date: Optional[date] = None,
    top_k: int = 8,
    patient_context: Optional[str] = None,
) -> AgenticRAGResult:
    """
    Executes the upgraded state-of-the-art Agentic RAG pipeline.
    """
    logger.info("Executing Agentic RAG for question: '%s'", question)

    # Step 1: Temporal Validation
    versions = await get_valid_versions(db, policy_id, as_of_date)
    if not versions:
        return AgenticRAGResult(
            answer=INSUFFICIENT_EVIDENCE_MSG,
            policy_version=None,
            evidence=[],
            confidence=0.0,
            warnings=["No valid, fully-processed policy version found for the requested date."],
            crag_regime=CRAGRegime.INCORRECT.value,
            retrieval_strategy="temporal_filter_failed",
            sub_queries=[question],
            factual_precision=0.0,
            reasoning_paths=[],
            calibrated_confidence=0.0,
            should_abstain=True,
            coverage_guarantee=1.0,
            entropy_level="low",
        )

    version_ids = [v.id for v in versions]

    # Step 1.5: OKF Canonical Concept Resolution & Ontological Traversal
    matched_okf = okf_engine.resolve_concepts(question, top_k=2)
    all_okf = list(matched_okf)
    for c in matched_okf:
        all_okf.extend(okf_engine.traverse_linked_concepts(c))

    unique_okf_dict = {c.id: c for c in all_okf}
    unique_okf = list(unique_okf_dict.values())
    okf_concept_ids = [c.id for c in unique_okf]
    okf_rules = {c.id: c.rules for c in unique_okf if c.rules}
    okf_context = okf_engine.format_okf_context_for_prompt(unique_okf) if unique_okf else None

    # Step 2: Adaptive Query Understanding (Adaptive-RAG / HyDE)
    q_analysis = analyze_query(question)
    retrieval_strategy = (
        f"hybrid_okf_{q_analysis.complexity.value}"
        if okf_concept_ids
        else f"adaptive_{q_analysis.complexity.value}"
    )

    # Step 3: Contextual Hybrid Retrieval with Multi-Granularity Indexing
    hybrid_candidates = await hybrid_retrieve(
        db,
        query=question,
        policy_version_ids=version_ids,
        sub_queries=q_analysis.sub_queries,
        hyde_query=q_analysis.hyde_prompt,
        top_k=max(top_k * 2, 16),
    )

    # Step 4: HippoRAG Associative Graph Traversal & GraphRAG Community Detection
    graph_candidates = await hippo_graph_retriever.retrieve_associative_chunks(
        db, query=question, version_ids=version_ids, top_k=6
    )

    # Retrieve GraphRAG community summaries for abstract / multi-hop / comparative queries
    community_summaries: list[str] = []
    if q_analysis.complexity in (
        QueryComplexity.COMPARATIVE,
        QueryComplexity.MULTI_HOP,
        QueryComplexity.CONDITIONAL,
    ):
        try:
            comm_contexts = await hippo_graph_retriever.retrieve_community_context(
                db, query=question, version_ids=version_ids, top_k=3
            )
            community_summaries = [
                f"[Community {c.get('theme', 'General')}]: {c.get('summary', '')}"
                for c in comm_contexts
                if c.get("summary")
            ]
        except Exception as exc:
            logger.warning("GraphRAG community retrieval failed: %s", exc)

    # Step 5: Multi-Channel Candidate Fusion
    seen_chunk_ids = {c.id for c in hybrid_candidates}
    combined_candidates = list(hybrid_candidates)
    graph_reasoning_paths = []

    for g_chunk, g_score, path_desc in graph_candidates:
        if path_desc:
            graph_reasoning_paths.append(path_desc)
        if g_chunk.id not in seen_chunk_ids:
            combined_candidates.append(g_chunk)
            seen_chunk_ids.add(g_chunk.id)

    # Step 6: Cross-Encoder & Late-Interaction Reranking
    reranked_evidence = rerank(question, combined_candidates, top_k=top_k)

    # Step 7: CRAG (Corrective RAG) Evaluator
    crag_eval = evaluate_retrieval(question, reranked_evidence)

    if crag_eval.regime == CRAGRegime.INCORRECT:
        return AgenticRAGResult(
            answer=INSUFFICIENT_EVIDENCE_MSG,
            policy_version=_format_version_label(versions),
            evidence=[],
            confidence=crag_eval.confidence_score,
            warnings=[
                "Evidence retrieved did not meet CRAG factuality thresholds for this policy query.",
                crag_eval.recommendation,
            ],
            crag_regime=crag_eval.regime.value,
            retrieval_strategy=retrieval_strategy,
            sub_queries=q_analysis.sub_queries,
            factual_precision=0.0,
            reasoning_paths=graph_reasoning_paths,
            okf_concepts=okf_concept_ids,
            okf_rules_applied=okf_rules,
            calibrated_confidence=0.0,
            should_abstain=True,
            coverage_guarantee=1.0,
            entropy_level="high",
            community_summaries=community_summaries,
        )

    # Step 8: DSPy Dynamic Prompt Assembly
    prompt_cfg = get_cached_prompt(
        query_complexity=q_analysis.complexity.value,
        crag_regime=crag_eval.regime.value,
        has_patient_context=bool(patient_context and patient_context.strip()),
        has_okf_context=bool(okf_context and okf_context.strip()),
        has_graph_paths=bool(graph_reasoning_paths),
    )

    # Step 9: Grounded Generation (Speculative RAG vs Single-Pass DSPy)
    use_speculative = (
        q_analysis.complexity
        in (QueryComplexity.CONDITIONAL, QueryComplexity.COMPARATIVE, QueryComplexity.MULTI_HOP)
        or crag_eval.regime == CRAGRegime.AMBIGUOUS
    ) and len(reranked_evidence) >= 4

    speculative_drafts_count = 0
    semantic_convergence = 1.0

    if use_speculative:
        logger.info("Executing Speculative RAG (draft-then-verify) for query complexity: %s", q_analysis.complexity.value)
        spec_result = await generate_speculative_drafts(
            question=question,
            evidence_chunks=reranked_evidence,
            system_prompt=prompt_cfg.system_prompt,
            patient_context=patient_context,
            okf_context=okf_context,
            graph_paths=graph_reasoning_paths + community_summaries[:2],
            num_drafts=3,
        )
        answer = spec_result.best_answer
        speculative_drafts_count = spec_result.num_drafts_generated
        if spec_result.verification_details:
            draft_texts = [d.get("answer", "") for d in spec_result.verification_details if d.get("answer")]
            if len(draft_texts) >= 2:
                semantic_convergence = compute_semantic_convergence(draft_texts)
    else:
        answer = await generate_answer(
            question=question,
            evidence_chunks=reranked_evidence,
            patient_context=patient_context,
            graph_paths=graph_reasoning_paths + community_summaries[:2],
            okf_context=okf_context,
            query_complexity=q_analysis.complexity.value,
            crag_regime=crag_eval.regime.value,
            system_prompt_override=prompt_cfg.system_prompt,
        )

    # Step 10: MiniCheck Fact Verification & Conformal Calibration (Upgrade #6)
    facet_cov = len(crag_eval.matched_facets) / max(len(crag_eval.matched_facets) + len(crag_eval.missing_facets), 1)
    v_result = verify_answer_detailed(
        answer=answer,
        evidence_chunks=reranked_evidence,
        crag_regime=crag_eval.regime.value,
        facet_coverage=facet_cov,
        semantic_convergence=semantic_convergence,
    )
    final_warnings = list(v_result.warnings)

    # Check OKF deterministic rule adherence
    okf_rule_warnings = okf_engine.validate_answer_against_rules(
        answer=answer,
        policy_tenure_months=None,
        concepts=unique_okf,
    )
    final_warnings.extend(okf_rule_warnings)

    # Step 11: Self-Refine Loop (if initial answer had unsupported claims or numbers)
    if (not v_result.is_supported or okf_rule_warnings) and answer.strip() != INSUFFICIENT_EVIDENCE_MSG:
        logger.info("Answer triggered Self-Refine loop due to verification/OKF warnings: %s", final_warnings)
        refined_answer = await generate_answer_with_refine(
            question=question,
            evidence_chunks=reranked_evidence,
            initial_answer=answer,
            refinement_warnings=final_warnings,
            patient_context=patient_context,
            okf_context=okf_context,
        )
        # Re-verify refined answer with conformal calibration
        v_result_refined = verify_answer_detailed(
            answer=refined_answer,
            evidence_chunks=reranked_evidence,
            crag_regime=crag_eval.regime.value,
            facet_coverage=facet_cov,
            semantic_convergence=semantic_convergence,
        )
        answer = refined_answer
        v_result = v_result_refined
        final_warnings = [w for w in v_result.warnings if "speculative" not in w]
        final_warnings.append("Self-Refine pass applied with OKF rule alignment.")

    # Step 12: Chain-of-Verification (CoVe) & Zero-Hallucination Gate
    from rag.hallucination_guard import sanitize_and_strip_hallucinations, execute_cove_refinement

    if (not v_result.is_supported or final_warnings) and answer.strip() != INSUFFICIENT_EVIDENCE_MSG:
        logger.info("Executing Chain-of-Verification (CoVe) audit on draft answer")
        cove_revised = await execute_cove_refinement(
            question=question,
            draft_answer=answer,
            evidence_chunks=reranked_evidence,
            system_prompt=prompt_cfg.system_prompt,
        )
        answer = cove_revised

    # Strict Zero-Hallucination Gate: Strip ungrounded claims, fix citations & verify numbers
    audit_report = sanitize_and_strip_hallucinations(
        answer=answer,
        evidence_chunks=reranked_evidence,
        strict_mode=True,
    )
    answer = audit_report.sanitized_answer
    if audit_report.has_hallucinations:
        final_warnings.extend(audit_report.audit_notes)
        # Re-verify sanitized output for calibrated confidence
        v_result = verify_answer_detailed(
            answer=answer,
            evidence_chunks=reranked_evidence,
            crag_regime=crag_eval.regime.value,
            facet_coverage=facet_cov,
            semantic_convergence=semantic_convergence,
        )

    version_label = _format_version_label(versions)

    # Assemble structured evidence items
    evidence_items = []
    for chunk, score in reranked_evidence:
        version_name = next(
            (v.version for v in versions if v.id == chunk.policy_version_id), "unknown"
        )
        evidence_items.append(
            EvidenceItem(
                chunk_id=chunk.id,
                content=chunk.content,
                page=chunk.page,
                section=chunk.section,
                policy_version=version_name,
                relevance_score=round(score, 3),
            )
        )

    claims_summary = [
        {
            "claim": c.claim_text,
            "status": c.status,
            "support_score": c.support_score,
            "page": c.supporting_page,
            "warnings": c.warnings,
        }
        for c in v_result.verified_claims
    ]

    # Step 13: Patent Engine - Graph-Conditioned Conformal Prediction & Cryptographic Merkle Provenance
    from rag.patent_inventions import conformal_predictor, merkle_ledger

    retrieval_scores = [score for _, score in reranked_evidence]
    centrality_proxies = [score * 0.9 for _, score in reranked_evidence]
    gccp_res = conformal_predictor.evaluate_graph_conditioned_coverage(
        retrieval_scores=retrieval_scores,
        factual_precision=v_result.factual_precision,
        community_cluster_entropy=0.25 if community_summaries else 0.1,
        graph_centrality_scores=centrality_proxies,
    )

    evidence_dicts = [
        {"chunk_id": str(item.chunk_id), "page": item.page, "section": item.section, "content": item.content}
        for item in evidence_items
    ]
    claims_texts = [c.claim_text for c in v_result.verified_claims]
    merkle_cert = merkle_ledger.generate_audit_certificate(
        query=question,
        answer=answer,
        evidence_chunks=evidence_dicts,
        claims=claims_texts,
    )

    return AgenticRAGResult(
        answer=answer,
        policy_version=version_label,
        evidence=evidence_items,
        confidence=v_result.calibrated_confidence,
        warnings=final_warnings,
        crag_regime=crag_eval.regime.value,
        retrieval_strategy=retrieval_strategy,
        sub_queries=q_analysis.sub_queries,
        factual_precision=v_result.factual_precision,
        reasoning_paths=graph_reasoning_paths,
        okf_concepts=okf_concept_ids,
        okf_rules_applied=okf_rules,
        calibrated_confidence=v_result.calibrated_confidence,
        should_abstain=v_result.should_abstain,
        coverage_guarantee=v_result.coverage_guarantee,
        entropy_level=v_result.entropy_level,
        speculative_drafts_count=speculative_drafts_count,
        community_summaries=community_summaries,
        verified_claims=claims_summary,
        merkle_root=merkle_cert["evidence_merkle_root"],
        certificate_signature=merkle_cert["certificate_signature"],
        conformal_interval=list(gccp_res.confidence_interval),
        topological_dispersion=gccp_res.topological_dispersion,
        lattice_arbitration_status="VERIFIED_CONSISTENT" if not audit_report.has_hallucinations else "RECTIFIED",
    )


async def stream_agentic_rag(
    db: AsyncSession,
    question: str,
    policy_id: Optional[UUID] = None,
    as_of_date: Optional[date] = None,
    top_k: int = 8,
    patient_context: Optional[str] = None,
) -> AsyncGenerator[dict, None]:
    """
    Progressive SSE Generator: Emits step-by-step progress, retrieved evidence cards,
    generating tokens, claim verification results, and conformal calibration metrics.
    """
    yield {
        "event": "status",
        "data": {"step": "temporal_validation", "message": "Validating temporal policy versions..."},
    }

    versions = await get_valid_versions(db, policy_id, as_of_date)
    if not versions:
        yield {
            "event": "error",
            "data": {"message": "No valid policy version found for requested date.", "abstain": True},
        }
        return

    version_ids = [v.id for v in versions]

    # OKF Resolution
    matched_okf = okf_engine.resolve_concepts(question, top_k=2)
    all_okf = list(matched_okf)
    for c in matched_okf:
        all_okf.extend(okf_engine.traverse_linked_concepts(c))
    unique_okf = list({c.id: c for c in all_okf}.values())
    okf_context = okf_engine.format_okf_context_for_prompt(unique_okf) if unique_okf else None

    # Query Analysis
    q_analysis = analyze_query(question)
    yield {
        "event": "query_analysis",
        "data": {
            "complexity": q_analysis.complexity.value,
            "sub_queries": q_analysis.sub_queries,
            "okf_concepts": [c.id for c in unique_okf],
        },
    }

    # Contextual Hybrid Retrieval
    yield {
        "event": "status",
        "data": {"step": "retrieval", "message": "Executing contextual hybrid retrieval & GraphRAG traversal..."},
    }

    hybrid_candidates = await hybrid_retrieve(
        db,
        query=question,
        policy_version_ids=version_ids,
        sub_queries=q_analysis.sub_queries,
        hyde_query=q_analysis.hyde_prompt,
        top_k=max(top_k * 2, 16),
    )

    graph_candidates = await hippo_graph_retriever.retrieve_associative_chunks(
        db, query=question, version_ids=version_ids, top_k=6
    )

    community_summaries: list[str] = []
    try:
        comm_contexts = await hippo_graph_retriever.retrieve_community_context(
            db, query=question, version_ids=version_ids, top_k=2
        )
        community_summaries = [
            f"[Community {c.get('theme', 'General')}]: {c.get('summary', '')}"
            for c in comm_contexts
            if c.get("summary")
        ]
    except Exception:
        pass

    seen_chunk_ids = {c.id for c in hybrid_candidates}
    combined = list(hybrid_candidates)
    graph_paths = []
    for g_chunk, _, path_desc in graph_candidates:
        if path_desc:
            graph_paths.append(path_desc)
        if g_chunk.id not in seen_chunk_ids:
            combined.append(g_chunk)
            seen_chunk_ids.add(g_chunk.id)

    reranked_evidence = rerank(question, combined, top_k=top_k)

    # Progressive disclosure: Emit retrieved evidence cards IMMEDIATELY before generation
    evidence_payload = [
        {
            "chunk_id": str(chunk.id),
            "content": chunk.content,
            "page": chunk.page,
            "section": chunk.section,
            "relevance_score": round(score, 3),
        }
        for chunk, score in reranked_evidence
    ]
    yield {
        "event": "evidence",
        "data": {
            "count": len(evidence_payload),
            "evidence": evidence_payload,
            "reasoning_paths": graph_paths[:4],
            "community_summaries": community_summaries,
        },
    }

    # CRAG Evaluation
    crag_eval = evaluate_retrieval(question, reranked_evidence)
    yield {
        "event": "crag_evaluation",
        "data": {
            "regime": crag_eval.regime.value,
            "confidence_score": crag_eval.confidence_score,
            "matched_facets": crag_eval.matched_facets,
            "missing_facets": crag_eval.missing_facets,
        },
    }

    if crag_eval.regime == CRAGRegime.INCORRECT:
        yield {
            "event": "done",
            "data": {
                "answer": INSUFFICIENT_EVIDENCE_MSG,
                "confidence": crag_eval.confidence_score,
                "should_abstain": True,
                "warnings": ["Evidence failed CRAG factuality check."],
            },
        }
        return

    # Prompt Assembly & Streaming Generation
    prompt_cfg = get_cached_prompt(
        query_complexity=q_analysis.complexity.value,
        crag_regime=crag_eval.regime.value,
        has_patient_context=bool(patient_context and patient_context.strip()),
        has_okf_context=bool(okf_context and okf_context.strip()),
        has_graph_paths=bool(graph_paths),
    )

    yield {
        "event": "status",
        "data": {"step": "generation", "message": "Streaming grounded response with citations..."},
    }

    accumulated_tokens = []
    async for token in stream_generate_answer(
        question=question,
        evidence_chunks=reranked_evidence,
        patient_context=patient_context,
        graph_paths=graph_paths + community_summaries[:2],
        okf_context=okf_context,
        query_complexity=q_analysis.complexity.value,
        crag_regime=crag_eval.regime.value,
        system_prompt_override=prompt_cfg.system_prompt,
    ):
        accumulated_tokens.append(token)
        yield {"event": "token", "data": {"token": token}}

    full_answer = "".join(accumulated_tokens).strip()

    # Fact Verification & Conformal Calibration
    facet_cov = len(crag_eval.matched_facets) / max(len(crag_eval.matched_facets) + len(crag_eval.missing_facets), 1)
    v_result = verify_answer_detailed(
        answer=full_answer,
        evidence_chunks=reranked_evidence,
        crag_regime=crag_eval.regime.value,
        facet_coverage=facet_cov,
    )

    claims_data = [
        {
            "claim": c.claim_text,
            "status": c.status,
            "support_score": c.support_score,
            "page": c.supporting_page,
            "warnings": c.warnings,
        }
        for c in v_result.verified_claims
    ]

    yield {
        "event": "verification",
        "data": {
            "is_supported": v_result.is_supported,
            "factual_precision": v_result.factual_precision,
            "calibrated_confidence": v_result.calibrated_confidence,
            "should_abstain": v_result.should_abstain,
            "coverage_guarantee": v_result.coverage_guarantee,
            "entropy_level": v_result.entropy_level,
            "verified_claims": claims_data,
            "warnings": v_result.warnings,
        },
    }

    # Zero-Hallucination Guardrail: Strip ungrounded claims, fix citations & verify numbers
    from rag.hallucination_guard import sanitize_and_strip_hallucinations
    audit_report = sanitize_and_strip_hallucinations(
        answer=full_answer,
        evidence_chunks=reranked_evidence,
        strict_mode=True,
    )
    if audit_report.has_hallucinations:
        full_answer = audit_report.sanitized_answer
        yield {
            "event": "hallucination_audit",
            "data": {
                "detected": audit_report.hallucinations_detected,
                "unsupported_numbers": audit_report.unsupported_numbers,
                "stripped_claims": audit_report.stripped_claims,
                "notes": audit_report.audit_notes,
            },
        }

    version_label = _format_version_label(versions)
    yield {
        "event": "done",
        "data": {
            "answer": full_answer,
            "policy_version": version_label,
            "confidence": v_result.calibrated_confidence,
            "calibrated_confidence": v_result.calibrated_confidence,
            "should_abstain": v_result.should_abstain,
            "coverage_guarantee": v_result.coverage_guarantee,
            "warnings": v_result.warnings,
            "factual_precision": v_result.factual_precision,
            "crag_regime": crag_eval.regime.value,
        },
    }


def _format_version_label(versions: list[PolicyVersion]) -> Optional[str]:
    if not versions:
        return None
    v0 = versions[0]
    p_name = v0.policy.name if hasattr(v0, "policy") and v0.policy else ""
    return f"{p_name} v{v0.version}".strip() if p_name else f"v{v0.version}"
