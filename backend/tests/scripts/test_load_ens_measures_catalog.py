"""Tests for ENS measures catalog loader (Motor 3 DdA Engine).

Verifies idempotency, cross-check with magerit_ens_mapping,
descriptions loaded, and FK integrity of reinforcements.

Uses the actual DB (loader is sync, tests verify post-load state).
El catalogo (docs/catalogs/ens_measures_catalog_v1.yaml) contiene
73 medidas canonicas del RD 311/2022 Anexo II
(4 organizativas + 33 operacionales + 36 de proteccion).
"""
import pytest
from sqlalchemy import text

from backend.tests.conftest import _admin_setup


class TestEnsMeasuresCatalog:
    """Verify ens_measures loaded correctly from YAML catalog."""

    @pytest.mark.asyncio
    async def test_exactly_73_measures_loaded(self, db):
        """Loader produce 73 medidas canonicas (RD 311/2022 Anexo II)."""
        async with _admin_setup(db):
            result = await db.execute(text("SELECT COUNT(*) FROM ens_measures"))
            count = result.scalar()
        assert count == 73, f"Expected 73 (RD 311/2022 Anexo II), got {count}"

    @pytest.mark.asyncio
    async def test_codes_match_magerit_ens_mapping(self, db):
        """Los 73 codigos de magerit_ens_mapping son subset de ens_measures."""
        async with _admin_setup(db):
            ens_codes = await db.execute(
                text("SELECT codigo FROM ens_measures ORDER BY codigo")
            )
            ens_set = {row[0] for row in ens_codes.fetchall()}

            mapping_codes = await db.execute(
                text("SELECT DISTINCT ens_measure FROM magerit_ens_mapping ORDER BY ens_measure")
            )
            mapping_set = {row[0] for row in mapping_codes.fetchall()}

        missing_in_measures = mapping_set - ens_set
        assert not missing_in_measures, (
            f"magerit_ens_mapping debe ser subset de ens_measures. "
            f"Faltan en ens_measures: {missing_in_measures}"
        )

    @pytest.mark.asyncio
    async def test_measures_have_descriptions(self, db):
        """Al menos 65 de 73 medidas tienen descripciones reales."""
        async with _admin_setup(db):
            result = await db.execute(
                text("SELECT COUNT(*) FROM ens_measures WHERE nombre NOT LIKE 'TODO%'")
            )
            non_todo = result.scalar()
        assert non_todo >= 65, f"Expected >= 65 non-TODO measures, got {non_todo}"

    @pytest.mark.asyncio
    async def test_todo_measures_documented(self, db):
        """TODO measures should have descriptive text explaining the gap."""
        async with _admin_setup(db):
            result = await db.execute(
                text("SELECT codigo, descripcion FROM ens_measures WHERE nombre LIKE 'TODO%'")
            )
            todos = result.mappings().all()
        for todo in todos:
            assert todo["descripcion"], f"TODO measure {todo['codigo']} has empty description"

    @pytest.mark.asyncio
    async def test_marcos_obligatorios_present(self, db):
        """All 3 marcos (org, op, mp) must be represented."""
        async with _admin_setup(db):
            result = await db.execute(
                text("SELECT DISTINCT marco FROM ens_measures ORDER BY marco")
            )
            marcos = {row[0] for row in result.fetchall()}
        assert marcos == {"org", "op", "mp"}, f"Expected 3 marcos, got {marcos}"

    @pytest.mark.asyncio
    async def test_marco_counts(self, db):
        """RD 311/2022 Anexo II oficial: org=4, op=33, mp=36 (total 73)."""
        async with _admin_setup(db):
            result = await db.execute(
                text("SELECT marco, COUNT(*) FROM ens_measures GROUP BY marco ORDER BY marco")
            )
            counts = {row[0]: row[1] for row in result.fetchall()}
        assert counts["org"] == 4, f"org expected 4, got {counts['org']}"
        assert counts["op"] == 33, f"op expected 33, got {counts['op']}"
        assert counts["mp"] == 36, f"mp expected 36, got {counts['mp']}"


@pytest.mark.skip(reason="FASE 9.0 (ADR-029): tabla ens_reinforcements drop · reseed canonico ens_measure_refuerzos diferido a Fase alpha.2.")
class TestEnsReinforcements:
    """Verify ens_reinforcements loaded correctly. SKIPPED post-FASE 9.0 drop legacy."""

    @pytest.mark.asyncio
    async def test_reinforcements_loaded(self, db):
        """At least 20 reinforcements should be loaded."""
        async with _admin_setup(db):
            result = await db.execute(text("SELECT COUNT(*) FROM ens_reinforcements"))
            count = result.scalar()
        assert count >= 20, f"Expected >= 20 reinforcements, got {count}"

    @pytest.mark.asyncio
    async def test_reinforcements_fk_valid(self, db):
        """Every reinforcement must point to a valid ens_measures row."""
        async with _admin_setup(db):
            result = await db.execute(text("""
                SELECT r.id, r.measure_id
                FROM ens_reinforcements r
                LEFT JOIN ens_measures m ON r.measure_id = m.id
                WHERE m.id IS NULL
            """))
            orphans = result.fetchall()
        assert len(orphans) == 0, f"Found {len(orphans)} orphan reinforcements"

    @pytest.mark.asyncio
    async def test_reinforcement_categories_valid(self, db):
        """aplica_categoria_minima must be one of B, M, A."""
        async with _admin_setup(db):
            result = await db.execute(
                text("SELECT DISTINCT aplica_categoria_minima FROM ens_reinforcements")
            )
            cats = {row[0] for row in result.fetchall()}
        assert cats.issubset({"B", "M", "A"}), f"Invalid categories: {cats}"

    @pytest.mark.asyncio
    async def test_idempotency_count_stable(self, db):
        """Running loader twice should produce same counts (80 + 20)."""
        async with _admin_setup(db):
            measures = await db.execute(text("SELECT COUNT(*) FROM ens_measures"))
            reinforcements = await db.execute(text("SELECT COUNT(*) FROM ens_reinforcements"))
            m_count = measures.scalar()
            r_count = reinforcements.scalar()

        assert m_count == 80, f"m_count expected 80 (v2.2), got {m_count}"
        assert r_count >= 20, f"r_count expected >= 20, got {r_count}"
