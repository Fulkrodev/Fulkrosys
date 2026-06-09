"""BM25 retrieval tests for RD 311/2022 knowledge chunks.

These tests require a running database with ingested RD 311/2022 data.
They verify that the tsvector-based full-text search returns the expected
measures for domain-specific queries.

DO NOT run without a live DB (port 5433).
"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

async def bm25_search(
    db: AsyncSession,
    query: str,
    *,
    limit: int = 5,
) -> list[dict]:
    """Run a BM25 (tsvector) search over knowledge_chunks.

    Returns list of dicts with measure_code, heading_path, rank.
    """
    result = await db.execute(
        text("""
            SELECT
                measure_code,
                heading_path,
                ts_rank_cd(content_tsvector,
                           plainto_tsquery('spanish', :q)) AS rank
            FROM knowledge_chunks
            WHERE content_tsvector @@ plainto_tsquery('spanish', :q)
              AND measure_code IS NOT NULL
            ORDER BY rank DESC
            LIMIT :lim
        """),
        {"q": query, "lim": limit},
    )
    return [
        {"measure_code": row.measure_code, "heading_path": row.heading_path, "rank": row.rank}
        for row in result.fetchall()
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_corpus_ingested_has_73_measures(db: AsyncSession):
    """Verify that exactly 73 unique measure codes are ingested."""
    result = await db.execute(
        text("""
            SELECT COUNT(DISTINCT measure_code)
            FROM knowledge_chunks
            WHERE measure_code IS NOT NULL
              AND seccion = 'measure'
        """)
    )
    count = result.scalar_one()
    assert count == 73, f"Expected 73 unique measures, got {count}"


@pytest.mark.asyncio
async def test_corpus_has_41_articles(db: AsyncSession):
    """Verify that at least 40 article chunks exist (target: 41)."""
    result = await db.execute(
        text("""
            SELECT COUNT(*)
            FROM knowledge_chunks
            WHERE seccion = 'article'
        """)
    )
    count = result.scalar_one()
    assert count >= 40, f"Expected >= 40 articles, got {count}"
    assert count <= 45, f"Expected <= 45 articles, got {count}"


@pytest.mark.asyncio
async def test_bm25_authentication_returns_op_acc_6(db: AsyncSession):
    """BM25 search for 'autenticacion usuarios organizacion' should
    return op.acc.6 in top results."""
    results = await bm25_search(db, "autenticación usuarios organización")
    codes = [r["measure_code"] for r in results if r["measure_code"]]
    assert "op.acc.6" in codes, (
        f"Expected op.acc.6 in results for 'autenticación usuarios organización', "
        f"got: {codes}"
    )


@pytest.mark.asyncio
async def test_bm25_incidentes_returns_op_exp_7(db: AsyncSession):
    """BM25 search for 'gestión incidentes seguridad' should
    return op.exp.7 in top results."""
    results = await bm25_search(db, "gestión incidentes seguridad")
    codes = [r["measure_code"] for r in results if r["measure_code"]]
    assert "op.exp.7" in codes, (
        f"Expected op.exp.7 in results for 'gestión incidentes seguridad', "
        f"got: {codes}"
    )


@pytest.mark.asyncio
async def test_bm25_analisis_riesgos_returns_op_pl_1(db: AsyncSession):
    """BM25 search for 'análisis riesgos' should
    return op.pl.1 in top results."""
    results = await bm25_search(db, "análisis riesgos")
    codes = [r["measure_code"] for r in results if r["measure_code"]]
    assert "op.pl.1" in codes, (
        f"Expected op.pl.1 in results for 'análisis riesgos', "
        f"got: {codes}"
    )
