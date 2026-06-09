"""Tests for backend.app.core.ai.embeddings module."""

import numpy as np
import pytest

from backend.app.core.ai.embeddings import (
    BGE_M3_DIMENSIONS,
    FastEmbedBGEMProvider,
    get_default_embedding_provider,
)


@pytest.fixture(scope="module")
def provider() -> FastEmbedBGEMProvider:
    """Shared embedding provider — avoids reloading the model per test."""
    return FastEmbedBGEMProvider()


# ------------------------------------------------------------------
# Basic properties
# ------------------------------------------------------------------

def test_provider_dimensions(provider: FastEmbedBGEMProvider):
    assert provider.dimensions == 1024
    assert provider.dimensions == BGE_M3_DIMENSIONS


def test_provider_model_name(provider: FastEmbedBGEMProvider):
    assert provider.model_name == "intfloat/multilingual-e5-large"


# ------------------------------------------------------------------
# Embedding operations
# ------------------------------------------------------------------

def test_embed_single_query_returns_1024_dim(provider: FastEmbedBGEMProvider):
    vec = provider.embed_query("categoria alta del ENS")
    assert isinstance(vec, list)
    assert len(vec) == 1024
    assert all(isinstance(v, float) for v in vec)


def test_embed_documents_batch_returns_list_of_vectors(provider: FastEmbedBGEMProvider):
    texts = [
        "Real Decreto 311/2022 del Esquema Nacional de Seguridad",
        "Medidas de seguridad para sistemas de categoria alta",
        "Analisis de riesgos segun la metodologia MAGERIT",
    ]
    vectors = provider.embed_documents(texts)
    assert isinstance(vectors, list)
    assert len(vectors) == 3
    for vec in vectors:
        assert len(vec) == 1024


def test_embed_empty_documents_returns_empty_list(provider: FastEmbedBGEMProvider):
    vectors = provider.embed_documents([])
    assert vectors == []


# ------------------------------------------------------------------
# Semantic similarity
# ------------------------------------------------------------------

def test_semantic_similarity_same_topic_higher_than_different(
    provider: FastEmbedBGEMProvider,
):
    """ENS-related sentences should be closer to each other than to cooking."""
    ens_a = provider.embed_query("medidas de seguridad del Esquema Nacional de Seguridad")
    ens_b = provider.embed_query("controles de ciberseguridad segun el ENS")
    cooking = provider.embed_query("receta de paella valenciana con mariscos")

    a = np.array(ens_a)
    b = np.array(ens_b)
    c = np.array(cooking)

    sim_ens = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
    sim_diff = float(np.dot(a, c) / (np.linalg.norm(a) * np.linalg.norm(c)))

    assert sim_ens > sim_diff, (
        f"ENS-ENS similarity ({sim_ens:.4f}) should be > ENS-cooking ({sim_diff:.4f})"
    )


# ------------------------------------------------------------------
# Singleton
# ------------------------------------------------------------------

def test_get_default_embedding_provider_returns_singleton():
    # Reset singleton for clean test
    import backend.app.core.ai.embeddings as mod
    mod._default_provider = None

    p1 = get_default_embedding_provider()
    p2 = get_default_embedding_provider()
    assert p1 is p2
