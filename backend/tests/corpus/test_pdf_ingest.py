"""Tests integración · sub-lote 1.B.5.2 · ingest de PDFs a ``knowledge_*``.

Valida que cada documento del lote existe + chunk_count > 0 + sector_aplicacion
y version_label poblados + hash sha256 de 64 hex.

Q3 · LA DEPENDENCIA, DECLARADA
    11 de estos tests venían fallando y se contaban como «dependencia de
    entorno». La dependencia real no es un puerto: son los **PDF de las nueve
    guías CCN-STIC de la serie 800 y la guía de gestión del riesgo de la AEPD**,
    que NO están en este repositorio y no pueden estarlo — son obra de terceros
    con condiciones de reproducción propias, incompatibles con redistribuirlas
    bajo la licencia de este árbol.

    El fixture ``backend/tests/fixtures/corpus_seed.sql.gz`` sí trae el corpus
    que sí se puede publicar: RD 311/2022, RGPD, NIS2, DORA y eIDAS — 5 fuentes,
    1.031 fragmentos.

    Así que estos tests no fallan: se SALTAN, con el motivo y la orden exacta
    para tenerlos, y bajo el marcador declarado ``requires_corpus_ccn``. Un test
    que sólo pasa en la máquina de quien lo escribió no es un test; uno que dice
    qué le falta y cómo conseguirlo, sí.

        pytest -m requires_corpus_ccn      # sólo estos
        pytest -m "not requires_corpus_ccn"  # el resto
"""
from __future__ import annotations

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.corpus.ccn_pdf_ingest import CORPUS_BATCH_1B5_2
from backend.app.models.knowledge import KnowledgeDocument, KnowledgeSource


BATCH_CODES = [e.code for e in CORPUS_BATCH_1B5_2]

pytestmark = pytest.mark.requires_corpus_ccn

_ORDEN_INGESTA = (
    "coloca los PDF bajo var/corpus/ y ejecuta: "
    "python -m backend.app.corpus.ccn_pdf_ingest --all"
)


async def _fuente_o_salto(db: AsyncSession, code: str) -> KnowledgeSource:
    """La fuente del corpus, o un salto que dice exactamente qué falta."""
    src = (await db.execute(
        select(KnowledgeSource).where(KnowledgeSource.code == code)
    )).scalar_one_or_none()
    if src is None:
        pytest.skip(
            f"El corpus '{code}' no está ingerido en esta base. Es un PDF de "
            f"tercero que este repositorio no distribuye (ver el docstring del "
            f"módulo). Para ejecutarlo, {_ORDEN_INGESTA}."
        )
    return src


@pytest.mark.asyncio
@pytest.mark.parametrize("code", BATCH_CODES)
async def test_pdf_doc_ingested(code: str, db: AsyncSession):
    """Cada doc del batch tiene KnowledgeSource + KnowledgeDocument + chunks."""
    src = await _fuente_o_salto(db, code)

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
    src = await _fuente_o_salto(db, "UE-DORA")
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
        src = await _fuente_o_salto(db, code)
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
    if total == 0:
        pytest.skip(
            "El lote 1.B.5.2 no está ingerido en esta base (PDF de terceros no "
            f"distribuidos con el repositorio). Para ejecutarlo, {_ORDEN_INGESTA}."
        )
    assert total >= 500, f"Total chunks batch 1.B.5.2 = {total} < 500"
