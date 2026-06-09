"""Tests integracion · sub-lote 1.B.5.2 · ingest 14 PDFs batch a knowledge_*.

Asume ingest ya ejecutado (`python -m backend.app.corpus.ccn_pdf_ingest --all`).
Valida que los 14 documents existen + chunk_count > 0 + sector_aplicacion y
version_label poblados + sha256 hash 64-char hex.

Requires: DB live puerto 5433 con corpus ingerido.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.corpus.ccn_pdf_ingest import CORPUS_BATCH_1B5_2
from backend.app.models.knowledge import KnowledgeDocument, KnowledgeSource


BATCH_CODES = [e.code for e in CORPUS_BATCH_1B5_2]


@pytest.mark.asyncio
@pytest.mark.parametrize("code", BATCH_CODES)
async def test_pdf_doc_ingested(code: str, db: AsyncSession):
    """Cada doc del batch tiene KnowledgeSource + KnowledgeDocument + chunks."""
    src_res = await db.execute(
        select(KnowledgeSource).where(KnowledgeSource.code == code)
    )
    src = src_res.scalar_one_or_none()
    assert src is not None, f"KnowledgeSource '{code}' no encontrada · ejecutar ccn_pdf_ingest"

    doc_res = await db.execute(
        select(KnowledgeDocument).where(KnowledgeDocument.source_id == src.id)
    )
    doc = doc_res.scalar_one_or_none()
    assert doc is not None, f"KnowledgeDocument para source '{code}' no encontrado"

    assert doc.chunk_count > 0, f"{code} chunk_count=0"
    assert doc.content_hash and len(doc.content_hash) == 64, (
        f"{code} content_hash invalido: {doc.content_hash!r}"
    )
    assert doc.mime_type == "application/pdf"
    assert doc.sector_aplicacion, f"{code} sector_aplicacion vacio"
    assert doc.version_label, f"{code} version_label vacio"


@pytest.mark.asyncio
async def test_dora_solo_sector_privado(db: AsyncSession):
    """DORA es sector financiero · sector_aplicacion debe ser SOLO ['privado']."""
    src_res = await db.execute(
        select(KnowledgeSource).where(KnowledgeSource.code == "UE-DORA")
    )
    src = src_res.scalar_one()
    doc_res = await db.execute(
        select(KnowledgeDocument).where(KnowledgeDocument.source_id == src.id)
    )
    doc = doc_res.scalar_one()
    assert doc.sector_aplicacion == ["privado"], (
        f"UE-DORA sector_aplicacion={doc.sector_aplicacion} · esperaba ['privado']"
    )


@pytest.mark.asyncio
async def test_ccn_stic_v2025_marked(db: AsyncSession):
    """Las 5 CCN-STIC publicadas 17-jun-2025 (AMEND-011 #3) deben tener
    version_label='2025-06-17' para distinguir de las versiones 2010-2011."""
    v2025_codes = ["CCN-STIC-801", "CCN-STIC-802", "CCN-STIC-803",
                    "CCN-STIC-805", "CCN-STIC-808"]
    for code in v2025_codes:
        src_res = await db.execute(
            select(KnowledgeSource).where(KnowledgeSource.code == code)
        )
        src = src_res.scalar_one()
        doc_res = await db.execute(
            select(KnowledgeDocument).where(KnowledgeDocument.source_id == src.id)
        )
        doc = doc_res.scalar_one()
        assert doc.version_label == "2025-06-17", (
            f"{code} version_label={doc.version_label!r} · esperaba '2025-06-17'"
        )


@pytest.mark.asyncio
async def test_total_chunks_above_threshold(db: AsyncSession):
    """Total chunks del batch 1.B.5.2 >= 500 (briefing 1.B.5.2 PASO 4.4)."""
    res = await db.execute(text(
        "SELECT COALESCE(SUM(kd.chunk_count), 0) "
        "FROM knowledge_documents kd "
        "JOIN knowledge_sources ks ON ks.id = kd.source_id "
        "WHERE ks.metadata->>'batch' = '1.B.5.2'"
    ))
    total = res.scalar_one()
    assert total >= 500, f"Total chunks batch 1.B.5.2 = {total} < 500"
