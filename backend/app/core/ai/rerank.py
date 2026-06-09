"""Reranking providers for FULKRO search pipeline.

Default: NoopRerankProvider (returns original order, safe fallback).
Future: SentenceTransformersRerankProvider with CrossEncoder.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class RerankResult:
    """A single reranked document with its score."""

    index: int
    text: str
    score: float


class RerankProvider(ABC):
    """Base class for reranking providers."""

    @abstractmethod
    def rerank(
        self,
        query: str,
        documents: list[str],
        top_k: int | None = None,
    ) -> list[RerankResult]:
        """Rerank documents by relevance to query.

        Args:
            query: The search query.
            documents: List of document texts to rerank.
            top_k: Maximum number of results to return (None = all).

        Returns:
            List of RerankResult sorted by descending relevance.
        """


# ---------------------------------------------------------------------------
# Noop implementation (safe fallback)
# ---------------------------------------------------------------------------

class NoopRerankProvider(RerankProvider):
    """Returns documents in original order with score 1.0.

    Use as a safe default when no reranker model is loaded.
    """

    def rerank(
        self,
        query: str,
        documents: list[str],
        top_k: int | None = None,
    ) -> list[RerankResult]:
        results = [
            RerankResult(index=i, text=doc, score=1.0)
            for i, doc in enumerate(documents)
        ]
        if top_k is not None:
            results = results[:top_k]
        return results


# ---------------------------------------------------------------------------
# SentenceTransformers stub (future)
# ---------------------------------------------------------------------------

class SentenceTransformersRerankProvider(RerankProvider):
    """Reranker using sentence-transformers CrossEncoder.

    Requires: pip install sentence-transformers
    Model: cross-encoder/ms-marco-MiniLM-L-6-v2 (or similar)
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> None:
        try:
            from sentence_transformers import CrossEncoder  # noqa: F401
            self._model = CrossEncoder(model_name)
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers is required for SentenceTransformersRerankProvider. "
                "Install with: pip install sentence-transformers"
            ) from exc

    def rerank(
        self,
        query: str,
        documents: list[str],
        top_k: int | None = None,
    ) -> list[RerankResult]:
        if not documents:
            return []
        pairs = [(query, doc) for doc in documents]
        scores = self._model.predict(pairs)
        indexed = [(i, doc, float(score)) for i, (doc, score) in enumerate(zip(documents, scores))]
        indexed.sort(key=lambda x: x[2], reverse=True)
        results = [RerankResult(index=i, text=doc, score=score) for i, doc, score in indexed]
        if top_k is not None:
            results = results[:top_k]
        return results


# ---------------------------------------------------------------------------
# Default factory
# ---------------------------------------------------------------------------

_default_reranker: RerankProvider | None = None


def get_default_reranker() -> RerankProvider:
    """Return the default reranker (Noop for now)."""
    global _default_reranker
    if _default_reranker is None:
        _default_reranker = NoopRerankProvider()
    return _default_reranker
