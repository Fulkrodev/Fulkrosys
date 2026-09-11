"""Tests del service core Motor 3 — DdA Engine.

Verifica generacion atomica de las 73 entries, applicabilidad por categoria,
update, freeze/unfreeze, stats y enrichment MAGERIT.
"""
import pytest
from uuid import uuid4

from sqlalchemy import text

from backend.app.database import set_tenant_context
from backend.app.motors.m03_dda.service import (
    DdaService,
    DdaFrozenError,
    DdaEntryNotFoundError,
    DdaIncompleteForFreezeError,
)
from backend.app.motors.m03_dda.enums import (
    CategoriaSistema,
)
from backend.tests.conftest import setup_test_project, _admin_setup


# ================================================================
# HELPER
# ================================================================

# O1 · nivel por dimension que corresponde a cada categoria. Antes este helper
# creaba un proyecto SIN valorar una sola dimension y aun asi esperaba ~52
# medidas aplicables en BASICA. Pasaba porque la generacion ignoraba el eje
# "dimension" del Anexo II y solo miraba la categoria. Ahora que lo respeta, un
# proyecto sin dimensiones valoradas da SOLO las 36 de eje categoria -- que es
# lo correcto -- y el escenario del test era imposible en la realidad: no se
# llega a categoria BASICA sin haber valorado nada.
_NIVEL_POR_CATEGORIA = {
    CategoriaSistema.BASICA: "BAJO",
    CategoriaSistema.MEDIA: "MEDIO",
    CategoriaSistema.ALTA: "ALTO",
}


async def _setup_dda(db, category=CategoriaSistema.BASICA):
    """Create project + valued system + generate DdA. Returns (svc, result, pid)."""
    import uuid as _uuid

    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(db, client_id=client_id, project_id=project_id)

    # Sistema con las cinco dimensiones valoradas al nivel de la categoria, que
    # es lo que tiene un proyecto real al llegar aqui.
    nivel = _NIVEL_POR_CATEGORIA[category]
    sid = _uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO systems (id, project_id, nombre, created_at) "
            "VALUES (:id, :pid, 'Sistema test', now())"
        ), {"id": str(sid), "pid": project_id})
        await db.execute(text(
            "INSERT INTO information_types (id, system_id, nombre, valoracion_d, "
            " valoracion_i, valoracion_c, valoracion_a, valoracion_t, created_at) "
            "VALUES (:id, :sid, 'Datos', :n, :n, :n, :n, :n, now())"
        ), {"id": str(_uuid.uuid4()), "sid": str(sid), "n": nivel})
    await db.flush()
    await set_tenant_context(db, client_id=client_id, project_id=project_id)

    svc = DdaService(db)
    result = await svc.generate_dda(
        project_id=project_id,
        system_category=category,
        responsable="RSEG Test",
    )
    await db.flush()
    return svc, result, project_id


async def _implement_entries(db, project_id, count, estado="implantada"):
    """Mark N applicable entries as implemented."""
    result = await db.execute(
        text(
            "SELECT id FROM dda_entries "
            "WHERE project_id = :pid AND aplicabilidad != 'no_aplica' "
            "AND deleted_at IS NULL ORDER BY id LIMIT :n"
        ),
        {"pid": str(project_id), "n": count},
    )
    ids = [row[0] for row in result.fetchall()]
    for eid in ids:
        await db.execute(
            text("UPDATE dda_entries SET estado_implementacion = :e WHERE id = :id"),
            {"e": estado, "id": str(eid)},
        )
    await db.flush()
    return len(ids)


# ================================================================
# GENERATION TESTS (1-6)
# ================================================================

class TestDdaGeneration:

    @pytest.mark.asyncio
    async def test_generate_73_entries_for_basica(self, db):
        """Test 1: BASICA genera 73 entries, ~47 aplicables, ~26 no aplica."""
        svc, result, _ = await _setup_dda(db, CategoriaSistema.BASICA)
        assert result["total_entries"] == 73
        assert result["aplicables"] >= 40
        assert result["no_aplica"] >= 20
        assert result["aplicables"] + result["no_aplica"] == 73

    @pytest.mark.asyncio
    async def test_generate_alta_all_apply(self, db):
        """Test 2: ALTA — las 73 medidas aplican."""
        svc, result, _ = await _setup_dda(db, CategoriaSistema.ALTA)
        assert result["total_entries"] == 73
        assert result["aplicables"] == 73
        assert result["no_aplica"] == 0

    @pytest.mark.asyncio
    async def test_generate_media_intermediate(self, db):
        """Test 3: MEDIA — aplican mas que BASICA pero quizas no todas."""
        svc, result, _ = await _setup_dda(db, CategoriaSistema.MEDIA)
        assert result["total_entries"] == 73
        assert result["aplicables"] > 47  # more than BASICA
        assert result["aplicables"] <= 73

    @pytest.mark.asyncio
    async def test_generate_overwrites_existing(self, db):
        """Test 4: Second generate replaces first (DELETE+INSERT)."""
        svc, _, project_id = await _setup_dda(db, CategoriaSistema.BASICA)
        # O1 · re-categorizar a ALTA implica re-valorar las dimensiones: un
        # sistema con las cinco en BAJO no es ALTA. Sin esto el escenario se
        # contradice y las medidas de eje dimension no aplican, que es lo
        # correcto pero no lo que este test quiere comprobar (el reemplazo).
        await db.execute(text(
            "UPDATE information_types SET valoracion_d='ALTO', valoracion_i='ALTO', "
            " valoracion_c='ALTO', valoracion_a='ALTO', valoracion_t='ALTO' "
            "WHERE system_id IN (SELECT id FROM systems WHERE project_id = :pid)"
        ), {"pid": str(project_id)})
        await db.flush()
        result2 = await svc.generate_dda(project_id, CategoriaSistema.ALTA)
        await db.flush()

        count = await db.execute(
            text("SELECT COUNT(*) FROM dda_entries WHERE project_id = :pid AND deleted_at IS NULL"),
            {"pid": str(project_id)},
        )
        assert count.scalar() == 73  # not 146
        assert result2["aplicables"] == 73  # ALTA

    @pytest.mark.asyncio
    async def test_no_aplica_has_justification(self, db):
        """Test 5: NO_APLICA entries have template justification."""
        svc, _, project_id = await _setup_dda(db, CategoriaSistema.BASICA)

        result = await db.execute(
            text(
                "SELECT justificacion_no_aplica FROM dda_entries "
                "WHERE project_id = :pid AND aplicabilidad = 'no_aplica' "
                "AND deleted_at IS NULL LIMIT 1"
            ),
            {"pid": str(project_id)},
        )
        justif = result.scalar()
        assert justif is not None
        assert "BASICA" in justif
        assert "Anexo" in justif
        # The justification must not leak internal implementation names.
        forbidden = ["Motor ", "Agente ", "M3-G1", "Document Factory", "Copiloto"]
        for token in forbidden:
            assert token not in justif, (
                f"Justification leaked internal reference '{token}': {justif}"
            )

    @pytest.mark.asyncio
    async def test_aplica_has_no_justification(self, db):
        """Test 6: APLICA entries have NULL justification."""
        svc, _, project_id = await _setup_dda(db, CategoriaSistema.BASICA)

        result = await db.execute(
            text(
                "SELECT justificacion_no_aplica FROM dda_entries "
                "WHERE project_id = :pid AND aplicabilidad != 'no_aplica' "
                "AND deleted_at IS NULL LIMIT 1"
            ),
            {"pid": str(project_id)},
        )
        assert result.scalar() is None


# ================================================================
# UPDATE TESTS (7-9)
# ================================================================

class TestDdaUpdate:

    @pytest.mark.asyncio
    async def test_update_changes_estado(self, db):
        """Test 7: Update changes estado_implementacion."""
        svc, _, project_id = await _setup_dda(db)

        result = await db.execute(
            text(
                "SELECT id FROM dda_entries "
                "WHERE project_id = :pid AND aplicabilidad != 'no_aplica' "
                "AND deleted_at IS NULL LIMIT 1"
            ),
            {"pid": str(project_id)},
        )
        entry_id = result.scalar()

        entry = await svc.update_entry(entry_id, {"estado_implementacion": "implantada"})
        assert entry.estado_implementacion == "implantada"
        assert entry.version == 2

    @pytest.mark.asyncio
    async def test_update_increments_version(self, db):
        """Test 8: Multiple updates increment version."""
        svc, _, project_id = await _setup_dda(db)

        result = await db.execute(
            text(
                "SELECT id FROM dda_entries "
                "WHERE project_id = :pid AND aplicabilidad != 'no_aplica' "
                "AND deleted_at IS NULL LIMIT 1"
            ),
            {"pid": str(project_id)},
        )
        entry_id = result.scalar()

        await svc.update_entry(entry_id, {"estado_implementacion": "parcial"})
        entry = await svc.update_entry(entry_id, {"estado_implementacion": "implantada"})
        assert entry.version == 3

    @pytest.mark.asyncio
    async def test_update_nonexistent_raises(self, db):
        """Test 9: Update nonexistent entry raises DdaEntryNotFoundError."""
        svc, _, _ = await _setup_dda(db)
        with pytest.raises(DdaEntryNotFoundError):
            await svc.update_entry(uuid4(), {"estado_implementacion": "implantada"})


# ================================================================
# STATS TESTS (10-11)
# ================================================================

class TestDdaStats:

    @pytest.mark.asyncio
    async def test_initial_stats(self, db):
        """Test 10: Initial stats all NO_VALORADO, 0% completion."""
        svc, result, project_id = await _setup_dda(db, CategoriaSistema.BASICA)
        stats = await svc.get_completion_stats(project_id)

        assert stats["total_medidas"] == 73
        assert stats["no_valoradas"] == result["aplicables"]
        assert stats["completion_pct"] == 0.0

    @pytest.mark.asyncio
    async def test_stats_after_implementations(self, db):
        """Test 11: Stats reflect implemented measures."""
        svc, result, project_id = await _setup_dda(db, CategoriaSistema.BASICA)

        implemented = await _implement_entries(db, project_id, 10)
        stats = await svc.get_completion_stats(project_id)

        assert stats["implantadas"] == 10
        assert stats["completion_pct"] > 0


# ================================================================
# FREEZE TESTS (12-15)
# ================================================================

class TestDdaFreeze:

    @pytest.mark.asyncio
    async def test_freeze_blocks_incomplete(self, db):
        """Test 12: Freeze fails when >20% NO_VALORADO."""
        svc, _, project_id = await _setup_dda(db, CategoriaSistema.BASICA)
        with pytest.raises(DdaIncompleteForFreezeError):
            await svc.freeze_dda(project_id, "RSEG Test")

    @pytest.mark.asyncio
    async def test_freeze_succeeds_when_80pct(self, db):
        """Test 13: Freeze OK when 85% of aplicables are valoradas."""
        svc, result, project_id = await _setup_dda(db, CategoriaSistema.BASICA)
        aplicables = result["aplicables"]
        need = int(aplicables * 0.85)
        await _implement_entries(db, project_id, need)

        freeze_result = await svc.freeze_dda(project_id, "RSEG Test")
        assert freeze_result["frozen_entries"] == 73
        assert freeze_result["aprobado_por"] == "RSEG Test"

    @pytest.mark.asyncio
    async def test_update_blocked_after_freeze(self, db):
        """Test 14: Update raises DdaFrozenError after freeze."""
        svc, result, project_id = await _setup_dda(db, CategoriaSistema.BASICA)
        aplicables = result["aplicables"]
        await _implement_entries(db, project_id, int(aplicables * 0.85))
        await svc.freeze_dda(project_id, "RSEG Test")
        await db.flush()

        entry_result = await db.execute(
            text(
                "SELECT id FROM dda_entries "
                "WHERE project_id = :pid AND deleted_at IS NULL LIMIT 1"
            ),
            {"pid": str(project_id)},
        )
        entry_id = entry_result.scalar()

        with pytest.raises(DdaFrozenError):
            await svc.update_entry(entry_id, {"estado_implementacion": "parcial"})

    @pytest.mark.asyncio
    async def test_unfreeze_allows_update(self, db):
        """Test 15: After unfreeze, update works again."""
        svc, result, project_id = await _setup_dda(db, CategoriaSistema.BASICA)
        aplicables = result["aplicables"]
        await _implement_entries(db, project_id, int(aplicables * 0.85))
        await svc.freeze_dda(project_id, "RSEG Test")
        await db.flush()

        await svc.unfreeze_dda(project_id)
        await db.flush()

        entry_result = await db.execute(
            text(
                "SELECT id FROM dda_entries "
                "WHERE project_id = :pid AND aplicabilidad != 'no_aplica' "
                "AND deleted_at IS NULL LIMIT 1"
            ),
            {"pid": str(project_id)},
        )
        entry_id = entry_result.scalar()

        entry = await svc.update_entry(entry_id, {"estado_implementacion": "parcial"})
        assert entry.estado_implementacion == "parcial"


# ================================================================
# ENRICHMENT TEST (16)
# ================================================================

class TestDdaEnrichment:

    @pytest.mark.asyncio
    async def test_list_entries_enriched_magerit(self, db):
        """Test 16: list_entries includes magerit_safeguards."""
        svc, _, project_id = await _setup_dda(db, CategoriaSistema.BASICA)
        entries = await svc.list_entries(project_id)

        assert len(entries) == 73
        # At least some entries should have magerit safeguards
        with_safeguards = [e for e in entries if e["magerit_safeguards"]]
        assert len(with_safeguards) > 50, (
            f"Expected >50 entries with MAGERIT safeguards, got {len(with_safeguards)}"
        )
