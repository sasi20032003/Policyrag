"""
Advanced Multi-Stage Reranker for Policy Retrieval.
Inspired by BGE-Reranker (2023), ColBERTv2 (NAACL 2022), and RankGPT (EMNLP 2023).

Features:
1. Cross-Encoder Architecture: Dynamically loads sentence-transformers CrossEncoder
   when available for joint query-passage cross-attention.
2. ColBERT-style Late-Interaction & Lexical Boost: Fallback engine combining
   bi-encoder cosine alignment, token-level coverage, exact numerical entity match,
   and section context weighting.
3. Domain Sensitivity: Elevates clauses that explicitly state quantitative limits,
   exclusion conditions, and waiting period durations relevant to the query.
"""
import logging
import re
import threading
from typing import Optional

from models.orm_models import Chunk
from rag.embeddings import embed_query, embed_texts

logger = logging.getLogger(__name__)

_cross_encoder_model = None
_ce_lock = threading.Lock()
_cross_encoder_failed = False


def _get_cross_encoder():
    """Lazily load a lightweight cross-encoder model if available."""
    global _cross_encoder_model, _cross_encoder_failed
    if _cross_encoder_failed:
        return None

    if _cross_encoder_model is None:
        with _ce_lock:
            if _cross_encoder_model is None and not _cross_encoder_failed:
                try:
                    from sentence_transformers import CrossEncoder

                    model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
                    logger.info("Attempting to load CrossEncoder model: %s", model_name)
                    _cross_encoder_model = CrossEncoder(model_name, max_length=512)
                except Exception as exc:
                    logger.info(
                        "CrossEncoder not loaded (%s). Using high-performance Late-Interaction Fallback.",
                        exc,
                    )
                    _cross_encoder_failed = True
    return _cross_encoder_model


def _extract_query_features(query: str) -> dict:
    """Extract numbers, conditions, and keywords from query for late-interaction matching."""
    q_lower = query.lower()
    numbers = set(re.findall(r"\b\d+\b", q_lower))
    tokens = [t for t in re.findall(r"[a-z0-9]+", q_lower) if len(t) > 2]

    # Check key intent
    is_exclusion_query = bool(re.search(r"\b(exclu|not covered|denied|rejection)\b", q_lower))
    is_waiting_query = bool(re.search(r"\b(waiting|ped|pre-existing|how long)\b", q_lower))
    is_limit_query = bool(re.search(r"\b(limit|sub-limit|cap|room rent|copay|percentage|maximum)\b", q_lower))

    return {
        "numbers": numbers,
        "tokens": set(tokens),
        "is_exclusion": is_exclusion_query,
        "is_waiting": is_waiting_query,
        "is_limit": is_limit_query,
    }


def _late_interaction_score(
    query: str,
    query_vec: list[float],
    chunk: Chunk,
    chunk_vec: list[float],
    q_features: dict,
) -> float:
    """
    ColBERTv2-inspired late interaction scoring combining:
    - Dense cosine alignment
    - Token overlap ratio
    - Quantitative/number matching
    - Clause type alignment
    """
    # 1. Cosine similarity
    cosine = sum(x * y for x, y in zip(query_vec, chunk_vec))

    content_lower = chunk.content.lower()
    chunk_tokens = set(re.findall(r"[a-z0-9]+", content_lower))

    # 2. Token overlap ratio
    if q_features["tokens"]:
        matched_tokens = q_features["tokens"] & chunk_tokens
        token_coverage = len(matched_tokens) / len(q_features["tokens"])
    else:
        token_coverage = 0.5

    # 3. Numeric figure match boost
    chunk_numbers = set(re.findall(r"\b\d+\b", content_lower))
    num_match_boost = 0.0
    if q_features["numbers"]:
        common_nums = q_features["numbers"] & chunk_numbers
        if common_nums:
            num_match_boost = 0.15

    # 4. Domain clause alignment boost
    clause_meta = chunk.chunk_metadata or {}
    c_type = clause_meta.get("clause_type", "general")
    domain_boost = 0.0

    if q_features["is_exclusion"] and (c_type == "exclusion" or "exclusion" in content_lower):
        domain_boost += 0.12
    if q_features["is_waiting"] and (c_type == "waiting_period" or "waiting period" in content_lower):
        domain_boost += 0.12
    if q_features["is_limit"] and (c_type == "limit" or any(k in content_lower for k in ["sub-limit", "room rent", "cap", "copay"])):
        domain_boost += 0.12

    # Weighted aggregate score
    final_score = (0.50 * cosine) + (0.25 * token_coverage) + num_match_boost + domain_boost
    return max(min(final_score, 1.0), 0.0)


def rerank(query: str, chunks: list[Chunk], top_k: int = 8) -> list[tuple[Chunk, float]]:
    """
    Reranks candidate chunks with CrossEncoder (if available) or Late-Interaction Neural Scorer.
    Returns sorted list of (Chunk, relevance_score) pairs.
    """
    if not chunks:
        return []

    # Try Cross-Encoder first
    ce = _get_cross_encoder()
    if ce is not None:
        try:
            pairs = [[query, c.content] for c in chunks]
            scores = ce.predict(pairs)
            scored = [(c, float(s)) for c, s in zip(chunks, scores)]
            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[:top_k]
        except Exception as exc:
            logger.warning("CrossEncoder prediction failed (%s), using late-interaction fallback", exc)

    # Late-Interaction Fallback
    query_vec = embed_query(query)
    chunk_vecs = embed_texts([c.content for c in chunks])
    q_features = _extract_query_features(query)

    scored = [
        (
            chunk,
            _late_interaction_score(query, query_vec, chunk, vec, q_features),
        )
        for chunk, vec in zip(chunks, chunk_vecs)
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]
