"""Tests de retrieval vectorial sobre el RD 311/2022 post-embedding.

Complementa test_rd311_retrieval.py (BM25) con queries vectoriales
usando pgvector cosine similarity (<=>).

Applies 'query: ' prefix (e5 convention) and L2 normalizes before search.
Filters by measure_code IS NOT NULL to focus on Anexo II measures.
"""
import math

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.ai.embeddings import get_default_embedding_provider

_provider = None


def _get_provider():
    global _provider
    if _provider is None:
        _provider = get_default_embedding_provider()
    return _provider


def _embed_and_normalize(query: str) -> list[float]:
    """Embed a query with 'query: ' prefix and L2 normalize."""
    provider = _get_provider()
    raw = provider.embed_query("query: " + query)
    norm = math.sqrt(sum(x * x for x in raw))
    return [x / norm for x in raw] if norm > 0 else raw


async def vector_search(
    db: AsyncSession, query: str, top_k: int = 5
) -> list[tuple[str, float]]:
    """Vector cosine search over knowledge_chunks with measure_code."""
    qemb = _embed_and_normalize(query)
    result = await db.execute(
        text(
            "SELECT measure_code, 1 - (embedding <=> CAST(:qemb AS vector)) AS similarity "
            "FROM knowledge_chunks "
            "WHERE embedding IS NOT NULL AND measure_code IS NOT NULL "
            "ORDER BY embedding <=> CAST(:qemb AS vector) "
            "LIMIT :k"
        ),
        {"qemb": str(qemb), "k": top_k},
    )
    return [(row[0], float(row[1])) for row in result]


@pytest.mark.asyncio
async def test_vector_authentication_returns_op_acc_5_or_6(db):
    """After corpus v2 re-ingest, both op.acc.5 (mecanismo de autenticación)
    and op.acc.6 (acceso local) are the relevant answers — either is OK."""
    results = await vector_search(db, "autenticación multifactor de usuarios")
    top_measures = [m for m, _ in results]
    assert any(m in top_measures for m in ("op.acc.5", "op.acc.6")), (
        f"op.acc.5 u op.acc.6 debe estar en top 5 vectorial, got {top_measures}"
    )


@pytest.mark.asyncio
async def test_vector_incident_management_returns_op_exp_7(db):
    results = await vector_search(db, "respuesta ante incidentes de seguridad")
    top_measures = [m for m, _ in results]
    assert "op.exp.7" in top_measures, (
        f"op.exp.7 debe estar en top 5 vectorial, got {top_measures}"
    )


@pytest.mark.asyncio
async def test_vector_backup_returns_op_cont_or_mp_info(db):
    """Copias de seguridad should match op.cont.x or mp.info.x."""
    results = await vector_search(db, "copias de seguridad y restauración")
    top_measures = [m for m, _ in results]
    cont_or_info = [m for m in top_measures if m.startswith(("op.cont", "mp.info"))]
    assert len(cont_or_info) >= 1, (
        f"Al menos 1 medida de continuidad/info en top 5, got {top_measures}"
    )


@pytest.mark.asyncio
async def test_vector_all_rd_chunks_have_embedding(db):
    r = await db.execute(
        text(
            "SELECT COUNT(*) FROM knowledge_chunks c "
            "JOIN knowledge_documents d ON d.id = c.document_id "
            "WHERE d.source_id IS NOT NULL AND c.embedding IS NULL"
        )
    )
    count = r.scalar()
    assert count == 0, f"{count} chunks del RD nuevo sin embedding"


@pytest.mark.asyncio
async def test_no_orphan_chunks_after_v2_reset(db):
    """After corpus_ingest_v2 --reset-orphans, no chunks belong to
    knowledge_documents without source_id. All corpus is now linked."""
    r = await db.execute(
        text(
            "SELECT COUNT(*) FROM knowledge_chunks c "
            "JOIN knowledge_documents d ON d.id = c.document_id "
            "WHERE d.source_id IS NULL"
        )
    )
    count = r.scalar()
    assert count == 0, f"Expected 0 orphan chunks post-v2, got {count}"
