"""Embedding provider — local BGE-M3 with caching and graceful degradation.

Uses sentence-transformers for local model inference. Model is loaded once as a
global singleton. Falls back to returning zero-vectors with a warning if the
model is unavailable (RAG degrades to BM25-only in that case).
"""

from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)

_embedding_model: object | None = None
_embedding_lock = threading.Lock()
_embedding_dim = 1024  # BGE-M3 output dimension
_embedding_available = False

try:
    import numpy as np
except ImportError:
    np = None


class EmbeddingProvider:
    """Local BGE-M3 embedding with lazy loading and thread safety."""

    _model = None
    _ready = False

    @classmethod
    def ready(cls) -> bool:
        """Check if the embedding model is loaded and available."""
        return cls._ready

    @classmethod
    def dim(cls) -> int:
        """Return embedding dimension."""
        return _embedding_dim

    @classmethod
    def load(cls) -> bool:
        """Load BGE-M3 model. Returns True on success, False on failure."""
        with _embedding_lock:
            if cls._model is not None:
                return cls._ready
            try:
                from sentence_transformers import SentenceTransformer
                cls._model = SentenceTransformer("BAAI/bge-m3")
                cls._ready = True
                logger.info("BGE-M3 embedding model loaded (dim=%d)", _embedding_dim)
            except Exception as e:
                logger.warning("BGE-M3 not available, RAG will use BM25-only: %s", e)
                cls._ready = False
            return cls._ready

    @classmethod
    def encode(cls, texts: list[str]) -> list[list[float]]:
        """Encode a list of texts to embeddings. Returns zero-vectors on failure."""
        if not cls._ready or cls._model is None:
            return cls._zero_vectors(len(texts))
        try:
            result = cls._model.encode(
                texts, normalize_embeddings=True, show_progress_bar=False
            )
            if hasattr(result, "tolist"):
                result = result.tolist()
            return [[float(v) for v in vec] for vec in result]
        except Exception as e:
            logger.error("Embedding encode failed: %s", e)
            return cls._zero_vectors(len(texts))

    @classmethod
    def encode_single(cls, text: str) -> list[float]:
        """Encode a single text. Returns zero-vector on failure."""
        results = cls.encode([text])
        return results[0] if results else cls._zero_vectors(1)[0]

    @classmethod
    def _zero_vectors(cls, count: int) -> list[list[float]]:
        return [[0.0] * _embedding_dim for _ in range(count)]


def get_embedding_provider() -> EmbeddingProvider:
    """Get the global embedding provider singleton, loading if needed."""
    if not EmbeddingProvider._model:
        EmbeddingProvider.load()
    return EmbeddingProvider
