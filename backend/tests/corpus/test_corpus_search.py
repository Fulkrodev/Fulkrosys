"""Tests de la recuperacion sobre el corpus (ranking vectorial).

Se llamaba `test_hybrid_search.py` y probaba la fusion RRF. La fusion se quito
el 2026-09-11 porque se midio que perdia (ver el docstring de
backend/app/corpus/retrieval.py y docs/EVAL_RECUPERACION.md), asi que el test
unitario de `_rrf_fuse` se fue con ella: probaba aritmetica de una funcion que
ya no existe, no una propiedad del producto.

Lo que sustituye a aquel test unitario esta un nivel mas arriba y es mejor
prueba: `test_orden_es_por_coseno_descendente` comprueba la propiedad que
importa de verdad, que la lista sale ordenada por similitud.
"""
import pytest

from backend.app.corpus.retrieval import CorpusResult, corpus_search


# ── Integration tests (require live DB with ingested corpus) ──────


@pytest.mark.asyncio
async def test_hybrid_returns_results(db):
    """Smoke: basic query returns top_k results without errors."""
    results = await corpus_search(db, "seguridad de la informacion", top_k=5)
    assert len(results) == 5
    for r in results:
        assert isinstance(r, CorpusResult)
        assert 0.0 <= r.score <= 1.0
        assert r.content


@pytest.mark.asyncio
async def test_hybrid_authentication_finds_op_acc_5_or_6(db):
    """Query about authentication should return op.acc.5 (mecanismo de
    autenticación) or op.acc.6 (acceso local) in top 5 — both are valid."""
    results = await corpus_search(
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
    results = await corpus_search(
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
    results = await corpus_search(
        db, "seguridad", top_k=10, source_codes=["RD_311_2022"]
    )
    assert len(results) > 0
    for r in results:
        assert r.source_code == "RD_311_2022", f"Unexpected source: {r.source_code}"


@pytest.mark.asyncio
async def test_hybrid_filter_measure_code(db):
    """only_with_measure_code=True returns only measure chunks."""
    results = await corpus_search(
        db, "control de acceso", top_k=10, only_with_measure_code=True
    )
    assert len(results) > 0
    for r in results:
        assert r.measure_code is not None


@pytest.mark.asyncio
async def test_hybrid_top_k_respected(db):
    """top_k=3 returns exactly 3 results."""
    results = await corpus_search(db, "seguridad", top_k=3)
    assert len(results) == 3


@pytest.mark.asyncio
async def test_orden_es_por_coseno_descendente(db):
    """La lista sale ordenada por similitud, y `vector_rank` la sigue.

    Es la propiedad que el consumidor da por hecha: A14 lee `results[0]` como
    «el mejor». Si el orden dejara de cumplirse, el repliegue por confianza
    (umbral 0,45 sobre `confidence`) estaria mirando un fragmento cualquiera.
    """
    results = await corpus_search(db, "gestion de incidentes", top_k=10)
    assert len(results) > 1
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)
    assert [r.vector_rank for r in results] == list(range(1, len(results) + 1))


@pytest.mark.asyncio
async def test_confidence_es_el_coseno_del_primero(db):
    """`confidence` es la senal global que consume el repliegue de A14."""
    results = await corpus_search(db, "analisis de riesgos", top_k=5)
    assert results
    assert all(r.confidence == pytest.approx(results[0].score) for r in results)
