"""Tests for hybrid BM25 + vector + RRF retrieval.

Verifies that hybrid_search returns correct results with proper
RRF scoring, filtering, and ranking.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.corpus.retrieval import (
    HybridResult,
    hybrid_search,
    _rrf_fuse,
    RRF_K,
)


# ── Integration tests (require live DB with ingested corpus) ──────


@pytest.mark.asyncio
async def test_hybrid_returns_results(db):
    """Smoke: basic query returns top_k results without errors."""
    results = await hybrid_search(db, "seguridad de la informacion", top_k=5)
    assert len(results) == 5
    for r in results:
        assert isinstance(r, HybridResult)
        assert r.rrf_score > 0
        assert r.content


@pytest.mark.asyncio
async def test_hybrid_authentication_finds_op_acc_5_or_6(db):
    """Query about authentication should return op.acc.5 (mecanismo de
    autenticación) or op.acc.6 (acceso local) in top 5 — both are valid."""
    results = await hybrid_search(
        db,
        "autenticacion multifactor de usuarios de la organizacion",
        top_k=5,
        only_with_measure_code=True,
    )
    measures = [r.measure_code for r in results]
    assert any(m in measures for m in ("op.acc.5", "op.acc.6")), (
        f"op.acc.5 or op.acc.6 expected in top 5 hybrid, got {measures}"
    )


@pytest.mark.asyncio
async def test_hybrid_incidents_finds_op_exp_7(db):
    """Query about incidents should return op.exp.7 in top 5."""
    results = await hybrid_search(
        db,
        "gestion de incidentes de seguridad",
        top_k=5,
        only_with_measure_code=True,
        source_codes=["RD_311_2022"],
    )
    measures = [r.measure_code for r in results]
    assert "op.exp.7" in measures, f"op.exp.7 expected in top 5 hybrid, got {measures}"


@pytest.mark.asyncio
async def test_hybrid_filter_source_codes(db):
    """source_codes filter restricts to the specified source."""
    results = await hybrid_search(
        db, "seguridad", top_k=10, source_codes=["RD_311_2022"]
    )
    assert len(results) > 0
    for r in results:
        assert r.source_code == "RD_311_2022", f"Unexpected source: {r.source_code}"


@pytest.mark.asyncio
async def test_hybrid_filter_measure_code(db):
    """only_with_measure_code=True returns only measure chunks."""
    results = await hybrid_search(
        db, "control de acceso", top_k=10, only_with_measure_code=True
    )
    assert len(results) > 0
    for r in results:
        assert r.measure_code is not None


@pytest.mark.asyncio
async def test_hybrid_top_k_respected(db):
    """top_k=3 returns exactly 3 results."""
    results = await hybrid_search(db, "seguridad", top_k=3)
    assert len(results) == 3


# ── Unit tests (no DB required) ──────────────────────────────────


def test_rrf_fuse_basic():
    """RRF fusion calculates correct scores."""
    bm25 = {"a": 1, "b": 2, "c": 3}
    vector = {"b": 1, "c": 2, "d": 3}
    scores = _rrf_fuse(bm25, vector, k=RRF_K)

    # 'b' in BM25 rank 2 + vector rank 1
    expected_b = 1 / (RRF_K + 2) + 1 / (RRF_K + 1)
    assert abs(scores["b"] - expected_b) < 1e-9

    # 'a' only in BM25 rank 1
    expected_a = 1 / (RRF_K + 1)
    assert abs(scores["a"] - expected_a) < 1e-9

    # 'b' should have highest score (appears in both lists with good ranks)
    best = max(scores, key=lambda k: scores[k])
    assert best == "b"


def test_rrf_fuse_empty():
    """RRF with empty inputs returns empty dict."""
    assert _rrf_fuse({}, {}) == {}
    result = _rrf_fuse({"a": 1}, {})
    assert abs(result["a"] - 1 / (RRF_K + 1)) < 1e-9
