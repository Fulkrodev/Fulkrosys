"""Tests knowledge_measure_mappings seed · sub-lote 1.B.5.2 PASO 6.

Asume seed ya ejecutado (`python backend/scripts/seed_measure_mappings.py`).
Valida que las 73 medidas Anexo II tienen al menos un mapping auto-rag
y que los mappings respetan el schema (FK CASCADE, UNIQUE, CHECK range).

Requires: DB live con corpus ingerido + mappings seeded.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_total_mappings_above_threshold(db: AsyncSession):
    """Briefing exige >= 73 mappings tras seed (1 por medida minimo)."""
    res = await db.execute(text(
        "SELECT COUNT(*) FROM knowledge_measure_mappings"
    ))
    total = res.scalar_one()
    assert total >= 73, f"Total mappings = {total} < 73 (briefing minimo)"


@pytest.mark.asyncio
async def test_distinct_medidas_covered(db: AsyncSession):
    """Briefing exige >= 60 medidas distintas con al menos 1 mapping."""
    res = await db.execute(text(
        "SELECT COUNT(DISTINCT ens_medida_id) FROM knowledge_measure_mappings"
    ))
    distinct = res.scalar_one()
    assert distinct >= 60, (
        f"Medidas distintas mapeadas = {distinct} < 60 (briefing minimo · "
        "puede bajarse threshold en seed_measure_mappings.py si necesario)"
    )


@pytest.mark.asyncio
async def test_auto_rag_provenance(db: AsyncSession):
    """Seed automatico debe marcar curated_by='auto-rag' para distinguir
    de curados manuales (curated_by='marcos' en sesion separada)."""
    res = await db.execute(text(
        "SELECT COUNT(*) FROM knowledge_measure_mappings "
        "WHERE curated_by = 'auto-rag'"
    ))
    count = res.scalar_one()
    assert count > 0, "Ningun mapping con curated_by='auto-rag'"


@pytest.mark.asyncio
async def test_relevance_score_in_range(db: AsyncSession):
    """CHECK constraint relevance_score BETWEEN 0 AND 1 (migration)."""
    res = await db.execute(text(
        "SELECT MIN(relevance_score), MAX(relevance_score) "
        "FROM knowledge_measure_mappings "
        "WHERE relevance_score IS NOT NULL"
    ))
    row = res.one()
    min_score, max_score = row
    assert min_score >= 0, f"min relevance_score={min_score} < 0"
    assert max_score <= 1, f"max relevance_score={max_score} > 1"


@pytest.mark.asyncio
async def test_chunk_ids_not_empty(db: AsyncSession):
    """chunk_ids es NOT NULL array · no debe haber arrays vacios."""
    res = await db.execute(text(
        "SELECT COUNT(*) FROM knowledge_measure_mappings "
        "WHERE chunk_ids IS NULL OR array_length(chunk_ids, 1) = 0"
    ))
    invalid = res.scalar_one()
    total = (await db.execute(
        text("SELECT COUNT(*) FROM knowledge_measure_mappings")
    )).scalar_one()
    # Sin esta guarda el test es vacuamente verdadero: sin mappings, el COUNT de
    # invalidos vale 0 y la asercion pasa sin examinar ninguna fila.
    assert total > 0, (
        "0 mappings en knowledge_measure_mappings: el corpus no esta sembrado y "
        "este test no puede verificar nada. Ejecuta scripts/build_test_db.sh."
    )
    assert invalid == 0, f"{invalid} mappings con chunk_ids vacio/null"


@pytest.mark.asyncio
async def test_unique_constraint_enforced(db: AsyncSession):
    """UNIQUE (ens_medida_id, document_id) debe garantizar 0 duplicados."""
    res = await db.execute(text(
        "SELECT COUNT(*) FROM ( "
        "  SELECT ens_medida_id, document_id, COUNT(*) AS n "
        "  FROM knowledge_measure_mappings "
        "  GROUP BY ens_medida_id, document_id "
        "  HAVING COUNT(*) > 1 "
        ") AS dups"
    ))
    dups = res.scalar_one()
    assert dups == 0, f"{dups} pares (medida, doc) duplicados"
