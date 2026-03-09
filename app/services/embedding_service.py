"""
Sentence-transformers embedding service.

Lazy-loads the model on first call to avoid slow startup
when embeddings aren't needed.
"""

import logging

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            from app.config import settings
            _model = SentenceTransformer(settings.embedding_model)
            logger.info(f"Loaded embedding model: {settings.embedding_model}")
        except Exception as e:
            logger.warning(f"Could not load embedding model: {e}")
    return _model


def embed_name(name: str) -> list[float] | None:
    """Return embedding vector for a name, or None if model unavailable."""
    model = _get_model()
    if model is None:
        return None
    try:
        return model.encode(name).tolist()
    except Exception as e:
        logger.warning(f"Embedding failed for '{name}': {e}")
        return None
