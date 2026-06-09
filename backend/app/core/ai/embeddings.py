"""Embedding providers for FULKRO vector search.

Default provider: FastEmbed with intfloat/multilingual-e5-large (1024 dims).
"""

from abc import ABC, abstractmethod

import numpy as np
from fastembed import TextEmbedding

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BGE_M3_DIMENSIONS = 1024  # kept name for backward compat; actual model is multilingual-e5-large
DEFAULT_MODEL_NAME = "intfloat/multilingual-e5-large"

# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class EmbeddingProvider(ABC):
    """Base class for all embedding providers."""

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Return the dimensionality of the embedding vectors."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier."""

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of documents. Returns list of float vectors."""

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embed a single query string. Returns one float vector."""


# ---------------------------------------------------------------------------
# FastEmbed implementation
# ---------------------------------------------------------------------------

class FastEmbedBGEMProvider(EmbeddingProvider):
    """FastEmbed provider using intfloat/multilingual-e5-large (1024 dims).

    Multilingual model supporting Spanish content (ENS / RD 311/2022).
    Uses ONNX Runtime for CPU inference — no GPU required.
    """

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME) -> None:
        self._model_name = model_name
        self._model = TextEmbedding(model_name=model_name)

    @property
    def dimensions(self) -> int:
        return BGE_M3_DIMENSIONS

    @property
    def model_name(self) -> str:
        return self._model_name

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of documents."""
        if not texts:
            return []
        embeddings = self._model.embed(texts)
        return [vec.tolist() if isinstance(vec, np.ndarray) else list(vec) for vec in embeddings]

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query string."""
        results = list(self._model.embed([text]))
        vec = results[0]
        return vec.tolist() if isinstance(vec, np.ndarray) else list(vec)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_default_provider: EmbeddingProvider | None = None


def get_default_embedding_provider() -> EmbeddingProvider:
    """Return (and lazily create) the default embedding provider singleton."""
    global _default_provider
    if _default_provider is None:
        _default_provider = FastEmbedBGEMProvider()
    return _default_provider
