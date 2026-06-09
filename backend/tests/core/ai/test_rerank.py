"""Tests for backend.app.core.ai.rerank module."""

import pytest

from backend.app.core.ai.rerank import (
    NoopRerankProvider,
    RerankResult,
    get_default_reranker,
)


@pytest.fixture
def noop() -> NoopRerankProvider:
    return NoopRerankProvider()


SAMPLE_DOCS = [
    "El ENS establece la politica de seguridad",
    "MAGERIT es la metodologia de analisis de riesgos",
    "Las medidas del marco operacional incluyen planificacion",
]


def test_noop_reranker_returns_original_order(noop: NoopRerankProvider):
    results = noop.rerank(query="seguridad", documents=SAMPLE_DOCS)
    assert len(results) == 3
    for i, r in enumerate(results):
        assert isinstance(r, RerankResult)
        assert r.index == i
        assert r.text == SAMPLE_DOCS[i]
        assert r.score == 1.0


def test_noop_reranker_respects_top_k(noop: NoopRerankProvider):
    results = noop.rerank(query="seguridad", documents=SAMPLE_DOCS, top_k=2)
    assert len(results) == 2
    assert results[0].index == 0
    assert results[1].index == 1


def test_noop_reranker_empty_documents(noop: NoopRerankProvider):
    results = noop.rerank(query="anything", documents=[])
    assert results == []


def test_default_reranker_is_instantiable():
    reranker = get_default_reranker()
    assert isinstance(reranker, NoopRerankProvider)
    results = reranker.rerank("test", ["doc1", "doc2"])
    assert len(results) == 2
