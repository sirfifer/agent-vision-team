"""Vector embedding generation for semantic search.

Uses sentence-transformers (all-MiniLM-L6-v2, 384-dim) for lightweight
in-process embeddings. The model is lazy-loaded on first use (~80MB).

This module is optional; install with: pip install avt-db[vectors]
"""

from __future__ import annotations

from typing import Optional

_model = None
_MODEL_NAME = "all-MiniLM-L6-v2"
_DIMENSION = 384


def get_embedding(text: str) -> list[float]:
    """Generate a 384-dimensional embedding for the given text.

    Lazy-loads the sentence-transformers model on first call.

    Raises:
        ImportError: If sentence-transformers is not installed.
    """
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
                "sentence-transformers is required for vector search. "
                "Install with: pip install avt-db[vectors]"
            )
        _model = SentenceTransformer(_MODEL_NAME)
    return _model.encode(text).tolist()


def get_embedding_safe(text: str) -> Optional[list[float]]:
    """Generate embedding, returning None if unavailable (no model installed)."""
    try:
        return get_embedding(text)
    except ImportError:
        return None


def get_dimension() -> int:
    """Return the embedding dimension for index configuration."""
    return _DIMENSION


def get_model_name() -> str:
    """Return the model name for documentation/logging."""
    return _MODEL_NAME
