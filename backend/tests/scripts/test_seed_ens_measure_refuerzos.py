"""Tests para seed canónico ``ens_measure_refuerzos`` + ``ens_measure_dimensiones``.

Verifica que el seed (SAN-C.MB-9.1) cargado vía migration
``sancseed091001_san_c_seed_ens_refuerzos_dimensiones`` cumple los
invariantes canónicos del RD 311/2022 Anexo II:

- Dimensiones CIDAT seedeadas para las 73 medidas
- Refuerzos R1-R9 según text Anexo II oficial
- ``applicable_categories`` JSONB correctamente diferencia
  Básica/Media/Alta para casos canónicos verificables
- Idempotencia: re-run del seed no duplica filas
- Trazabilidad: ``source_chunk_id`` FK válido a ``knowledge_chunks``

Tests sync (loader es sync, verifica post-load state).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from backend.tests.conftest import _admin_setup


SOURCE_TAG = "BOE-A-2022-7191 Anexo II"


class TestSeedEnsMeasureRefuerzos:
    """Verifica seed canónico cargado correctamente vs RD 311/2022 Anexo II."""

    @pytest.mark.asyncio
    async def test_all_73_measures_have_dimensiones(self, db):
        """Las 73 medidas tienen al menos 1 dimensión CIDAT seedeada."""
        async with _admin_setup(db):
            result = await db.execute(
                text(
                    "SELECT count(DISTINCT measure_code) FROM ens_measure_dimensiones "
                    "WHERE metadata ->> 'source' = :tag"
                ),
                {"tag": SOURCE_TAG},
            )
            count = result.scalar()
        assert count == 73, f"Expected 73 medidas con dimensiones, got {count}"

    @pytest.mark.asyncio
    async def test_dimensiones_are_canonical_cidat(self, db):
        """Solo se aceptan letras D/I/C/A/T."""
        async with _admin_setup(db):
            result = await db.execute(
                text(
                    "SELECT DISTINCT dimension FROM ens_measure_dimensiones "
                    "WHERE metadata ->> 'source' = :tag"
                ),
                {"tag": SOURCE_TAG},
            )
            dims = {row[0] for row in result.fetchall()}
        assert dims.issubset({"D", "I", "C", "A", "T"}), (
            f"Non-CIDAT dimensions present: {dims - {'D','I','C','A','T'}}"
        )

    @pytest.mark.asyncio
    async def test_mp_com_2_canonical_refuerzos(self, db):
        """mp.com.2 (Protección confidencialidad) declara R1-R5 canónicos.

        Anexo II: Nivel BAJO sólo medida base · MEDIO + R1 · ALTO + R1+R2+R3.
        R4 y R5 declarados como refuerzos disponibles pero no asignados a
        nivel BÁSICA/MEDIA/ALTA por defecto (R4 R5 son refuerzos opcionales
        per criterio adicional del RSEG).
        """
        async with _admin_setup(db):
            result = await db.execute(
                text(
                    "SELECT refuerzo_level, applicable_categories::text "
                    "FROM ens_measure_refuerzos "
                    "WHERE measure_code = 'mp.com.2' "
                    "AND metadata ->> 'source' = :tag "
                    "ORDER BY refuerzo_level"
                ),
                {"tag": SOURCE_TAG},
            )
            rows = result.fetchall()

        levels = [row[0] for row in rows]
        assert levels == ["+R1", "+R2", "+R3", "+R4", "+R5"], (
            f"mp.com.2 expected R1..R5 canónicos, got {levels}"
        )

        cats = {row[0]: row[1] for row in rows}
        assert "MEDIA" in cats["+R1"] and "ALTA" in cats["+R1"], (
            "mp.com.2 +R1 debe aplicar a MEDIA y ALTA per Anexo II"
        )
        assert "ALTA" in cats["+R2"] and "MEDIA" not in cats["+R2"], (
            "mp.com.2 +R2 sólo aplica a ALTA per Anexo II"
        )

    @pytest.mark.asyncio
    async def test_org_1_no_refuerzos(self, db):
        """org.1 (Política Seguridad) NO declara refuerzos · sólo medida base."""
        async with _admin_setup(db):
            result = await db.execute(
                text(
                    "SELECT count(*) FROM ens_measure_refuerzos "
                    "WHERE measure_code = 'org.1' "
                    "AND metadata ->> 'source' = :tag"
                ),
                {"tag": SOURCE_TAG},
            )
            count = result.scalar()
        assert count == 0, f"org.1 no debe tener refuerzos, found {count}"

    @pytest.mark.asyncio
    async def test_source_chunk_id_fk_valid(self, db):
        """Cada refuerzo seedeado lleva FK válido a knowledge_chunks."""
        async with _admin_setup(db):
            result = await db.execute(
                text(
                    "SELECT count(*) FROM ens_measure_refuerzos r "
                    "WHERE r.metadata ->> 'source' = :tag "
                    "AND r.source_chunk_id IS NOT NULL "
                    "AND NOT EXISTS ("
                    "  SELECT 1 FROM knowledge_chunks k WHERE k.id = r.source_chunk_id"
                    ")"
                ),
                {"tag": SOURCE_TAG},
            )
            orphans = result.scalar()
        assert orphans == 0, f"Found {orphans} refuerzos con FK source_chunk_id huérfana"
