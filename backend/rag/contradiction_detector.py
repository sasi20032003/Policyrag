"""
Detects relationships (SAME / UPDATED / CONTRADICTORY / REMOVED / ADDED)
between semantically related clauses across two policy versions.

Approach: embed all chunks of both versions, match each chunk in version A
to its nearest neighbor in version B (and vice versa) above a similarity
threshold, then ask the LLM to classify the relationship + explain it in a
structured way. Falls back to a rule-based classification if the LLM call
fails, so the endpoint always returns a usable result.
"""
import json
import logging
import re

import numpy as np

from models.orm_models import Chunk
from rag.embeddings import embed_texts
from services.llm_service import llm_service

logger = logging.getLogger(__name__)

MATCH_THRESHOLD = 0.55

CLASSIFY_SYSTEM_PROMPT = """You compare two insurance policy clauses (A and B) and classify their
relationship. Respond ONLY with compact JSON: {"type": "SAME|UPDATED|CONTRADICTORY", "explanation": "..."}.
- SAME: no meaningful difference.
- UPDATED: a value/limit/condition changed but the coverage intent is consistent (e.g. amount increased).
- CONTRADICTORY: the two clauses conflict in a way that cannot both be true/valid simultaneously.
Keep the explanation to one sentence and state old value -> new value when numeric."""


def _cosine_matrix(vecs_a: list[list[float]], vecs_b: list[list[float]]) -> np.ndarray:
    a = np.array(vecs_a)
    b = np.array(vecs_b)
    return a @ b.T  # vectors are pre-normalized


async def detect_contradictions(
    chunks_a: list[Chunk], chunks_b: list[Chunk]
) -> dict:
    """Returns dict with keys: added, removed, modified, contradictions -
    each a list of {type, clause_a, clause_b, explanation, confidence}."""
    result = {"added": [], "removed": [], "modified": [], "contradictions": []}

    if not chunks_a and not chunks_b:
        return result
    if not chunks_a:
        result["added"] = [
            {"type": "ADDED", "clause_a": None, "clause_b": c.content, "explanation": "New clause in this version.", "confidence": 1.0}
            for c in chunks_b
        ]
        return result
    if not chunks_b:
        result["removed"] = [
            {"type": "REMOVED", "clause_a": c.content, "clause_b": None, "explanation": "Clause removed in this version.", "confidence": 1.0}
            for c in chunks_a
        ]
        return result

    vecs_a = embed_texts([c.content for c in chunks_a])
    vecs_b = embed_texts([c.content for c in chunks_b])
    sim = _cosine_matrix(vecs_a, vecs_b)

    matched_b = set()
    for i, chunk_a in enumerate(chunks_a):
        j = int(np.argmax(sim[i]))
        score = float(sim[i][j])
        if score < MATCH_THRESHOLD:
            result["removed"].append(
                {"type": "REMOVED", "clause_a": chunk_a.content, "clause_b": None,
                 "explanation": "No corresponding clause found in the newer version.", "confidence": round(1 - score, 3)}
            )
            continue

        chunk_b = chunks_b[j]
        matched_b.add(j)

        if chunk_a.content.strip() == chunk_b.content.strip():
            continue  # identical -> SAME, not surfaced in the diff view

        classification = await _classify_pair(chunk_a.content, chunk_b.content)
        bucket = "contradictions" if classification["type"] == "CONTRADICTORY" else "modified"
        result[bucket].append(
            {
                "type": classification["type"],
                "clause_a": chunk_a.content,
                "clause_b": chunk_b.content,
                "clause_a_id": chunk_a.id,
                "clause_b_id": chunk_b.id,
                "explanation": classification["explanation"],
                "confidence": round(score, 3),
            }
        )

    for j, chunk_b in enumerate(chunks_b):
        if j not in matched_b:
            result["added"].append(
                {"type": "ADDED", "clause_a": None, "clause_b": chunk_b.content,
                 "explanation": "New clause introduced in this version.", "confidence": 1.0}
            )

    return result


async def _classify_pair(text_a: str, text_b: str) -> dict:
    prompt = f"Clause A:\n{text_a}\n\nClause B:\n{text_b}"
    try:
        raw = await llm_service.complete(CLASSIFY_SYSTEM_PROMPT, prompt, max_tokens=200)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        parsed = json.loads(match.group(0)) if match else {}
        rel_type = parsed.get("type", "UPDATED")
        if rel_type not in {"SAME", "UPDATED", "CONTRADICTORY"}:
            rel_type = "UPDATED"
        return {"type": rel_type, "explanation": parsed.get("explanation", "Clause content changed.")}
    except Exception as exc:
        logger.warning("Contradiction classification LLM call failed, using fallback: %s", exc)
        return {"type": "UPDATED", "explanation": "Clause content differs between versions (auto-detected)."}
