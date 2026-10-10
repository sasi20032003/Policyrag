"""
Sentence-transformers embedding service. Lazily loads the model once and
reuses it (singleton), since loading is expensive.
"""
import logging
import threading

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_model = None
_lock = threading.Lock()


def _get_model():
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer

                logger.info("Loading embedding model: %s", settings.embedding_model)
                _model = SentenceTransformer(settings.embedding_model)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Return one embedding vector per input text."""
    if not texts:
        return []
    model = _get_model()
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return [v.tolist() for v in vectors]


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
