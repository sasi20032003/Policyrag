"""
BM25 lexical retrieval over a policy version's chunks. Built on-demand from
DB rows since the corpus is scoped per policy/version rather than global.
"""
import logging
import re

from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")


def _tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


class BM25Index:
    """Thin wrapper mapping BM25 scores back to chunk ids."""

    def __init__(self, chunk_ids: list[str], texts: list[str]):
        self.chunk_ids = chunk_ids
        self._corpus_tokens = [_tokenize(t) for t in texts]
        self._bm25 = BM25Okapi(self._corpus_tokens) if self._corpus_tokens else None

    def search(self, query: str, top_k: int = 20) -> list[tuple[str, float]]:
        if not self._bm25:
            return []
        scores = self._bm25.get_scores(_tokenize(query))
        ranked = sorted(zip(self.chunk_ids, scores), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]
