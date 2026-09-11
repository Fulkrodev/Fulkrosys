"""Tests del service core Motor 4 -- Gap Analysis Engine.

Uses M3 DdA Engine to generate a real DdA, then runs gap analysis.
Pattern consistent with M19 and M3 test_service.py.
"""
import pytest
from uuid import uuid4

from sqlalchemy import text

from backend.app.database import set_tenant_context
from backend.app.models.findings import Finding
from backend.app.motors.m04_gap.service import GapAnalysisService, FUENTE_GAP
from backend.app.motors.m04_gap.exceptions import (
    GapNotFoundError,
    GapStateError,
    DdANotReadyError,
    GapAlreadyAnalyzedError,
    GapValidationError,
)
from backend.app.motors.m03_dda.service import DdaService
from backend.app.motors.m03_dda.enums import CategoriaSistema
from backend.tests.conftest import setup_test_project, _admin_setup


# ================================================================
# HELPERS
# ================================================================

async def _setup_gap_env(db):
    """Create project + set RLS. Returns (svc, project_id, client_id)."""
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(db, client_id=client_id, project_id=project_id)
    svc = GapAnalysisService(db)
    return svc, project_id, client_id


async def _setup_with_dda(db, categoria="BASICA"):
    """Create project + system + categorization + DdA. Returns (gap_svc, project_id)."""
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(db, client_id=client_id, project_id=project_id)

    # Create system + categorization using admin role
    system_id = uuid4()
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO systems (id, project_id, nombre, created_at) "
            "VALUES (:sid, :pid, 'Test System', now())"
        ), {"sid": str(system_id), "pid": str(project_id)})
        await db.execute(text(
            "INSERT INTO categorizations (id, system_id, categoria_resultante, created_at) "
            "VALUES (:id, :sid, :cat, now())"
        ), {"id": str(uuid4()), "sid": str(system_id), "cat": categoria})
        # N1 · el sistema tiene que VALORAR sus dimensiones. Antes este fixture
        # creaba la categorizacion y nada mas, y el escenario funcionaba solo
        # porque la generacion de la DdA ignoraba el eje de dimension: contaba
        # las medidas de eje categoria y ya. Con el Anexo II punto 5 aplicado de
        # verdad -- una medida aplica por la CATEGORIA del sistema O por el
        # NIVEL de una dimension -- un sistema sin ninguna dimension valorada da
        # 36 medidas aplicables, no 47. El escenario, no el arreglo, era lo que
        # estaba mal: un sistema BASICA real tiene dimensiones valoradas.
        _NIVEL = {"BASICA": "BAJO", "MEDIA": "MEDIO", "ALTA": "ALTO"}
        await db.execute(text(
            "INSERT INTO information_types (id, system_id, nombre, "
            "  valoracion_c, valoracion_i, valoracion_d, valoracion_a, "
            "  valoracion_t, created_at) "
            "VALUES (:id, :sid, 'Datos del servicio', :n, :n, :n, :n, :n, now())"
        ), {
            "id": str(uuid4()), "sid": str(system_id),
            "n": _NIVEL.get(categoria, "BAJO"),
        })
    await db.flush()

    # Generate DdA via Motor 3 (requires CategoriaSistema enum)
    cat_enum = CategoriaSistema(categoria)
    dda_svc = DdaService(db)
    await dda_svc.generate_dda(
        project_id=project_id,
        system_category=cat_enum,
        responsable="RSEG Test",
    )
    await db.flush()

    gap_svc = GapAnalysisService(db)
    return gap_svc, project_id


async def _create_test_gap(svc, project_id, codigo="org.1", **overrides):
    """Create a gap finding manually for CRUD tests."""
    defaults = dict(
        project_id=project_id,
        fuente=FUENTE_GAP,
        severidad="alta",
        medida_afectada=codigo,
        descripcion=f"Gap en {codigo}",
        estado="abierto",
        metadata_jsonb={
            "motor": "m04_gap",
            "codigo_medida": codigo,
            "familia": "org",
            "quick_win": False,
            "nuclear": False,
        },
    )
    defaults.update(overrides)
    f = Finding(**defaults)
    svc.db.add(f)
    await svc.db.flush()
    return f


# ================================================================
# CRUD TESTS
# ================================================================

class TestCrud:

    @pytest.mark.asyncio
    async def test_get_gap_not_found_raises(self, db):
        svc, pid, _ = await _setup_gap_env(db)
        with pytest.raises(GapNotFoundError):
            await svc.get_gap(uuid4())

    @pytest.mark.asyncio
    async def test_list_gaps_empty_returns_empty(self, db):
        svc, pid, _ = await _setup_gap_env(db)
        gaps = await svc.list_gaps(pid)
        assert gaps == []

    @pytest.mark.asyncio
    async def test_update_gap_partial(self, db):
        svc, pid, _ = await _setup_gap_env(db)
        gap = await _create_test_gap(svc, pid)
        updated = await svc.update_gap(gap.id, severidad="critica", asignado_a="Ana")
        assert updated.severidad == "critica"
        assert updated.asignado_a == "Ana"

    @pytest.mark.asyncio
    async def test_close_gap_writes_metadata(self, db):
        svc, pid, _ = await _setup_gap_env(db)
        gap = await _create_test_gap(svc, pid)
        closed = await svc.close_gap(gap.id, resolution_notes="Fixed", closed_by="Marcos")
        assert closed.estado == "cerrado"
        assert closed.metadata_jsonb["closure"]["resolution_notes"] == "Fixed"
        assert closed.metadata_jsonb["closure"]["closed_by"] == "Marcos"

    @pytest.mark.asyncio
    async def test_delete_gap_soft_delete(self, db):
        svc, pid, _ = await _setup_gap_env(db)
        gap = await _create_test_gap(svc, pid)
        await svc.delete_gap(gap.id)
        with pytest.raises(GapNotFoundError):
            await svc.get_gap(gap.id)


# ================================================================
# ANALYSIS TESTS
# ================================================================

class TestAnalysis:

    @pytest.mark.asyncio
    async def test_analyze_without_dda_raises(self, db):
        svc, pid, _ = await _setup_gap_env(db)
        with pytest.raises(DdANotReadyError):
            await svc.analyze_project(pid, categoria_objetivo="BASICA")

    @pytest.mark.asyncio
    async def test_analyze_with_dda_creates_gaps(self, db):
        svc, pid = await _setup_with_dda(db, "BASICA")
        result = await svc.analyze_project(pid, categoria_objetivo="BASICA")
        assert result["gaps_created"] > 0
        assert result["categoria_usada"] == "BASICA"
        assert result["dda_entries_evaluated"] == 73

    @pytest.mark.asyncio
    async def test_analyze_skips_non_applicable(self, db):
        svc, pid = await _setup_with_dda(db, "BASICA")
        result = await svc.analyze_project(pid, categoria_objetivo="BASICA")
        # BASICA has ~47 applicable. All start at L0, target L2, so all applicable = gap
        assert result["gaps_created"] >= 40
        assert result["gaps_created"] <= 73

    @pytest.mark.asyncio
    async def test_analyze_assigns_correct_severity(self, db):
        svc, pid = await _setup_with_dda(db, "MEDIA")
        result = await svc.analyze_project(pid, categoria_objetivo="MEDIA")
        # op.acc.6 should be critica for MEDIA
        gaps = await svc.list_gaps(pid, severidad="critica")
        codigos = [g.medida_afectada for g in gaps]
        assert "op.acc.6" in codigos

    @pytest.mark.asyncio
    async def test_analyze_marks_nuclear_gaps(self, db):
        svc, pid = await _setup_with_dda(db, "MEDIA")
        await svc.analyze_project(pid, categoria_objetivo="MEDIA")
        gaps = await svc.list_gaps(pid, only_nuclear=True)
        nuclear_codigos = {g.medida_afectada for g in gaps}
        # These must be nuclear
        for code in ["op.acc.6", "mp.info.3", "op.exp.7"]:
            assert code in nuclear_codigos, f"{code} should be nuclear"

    @pytest.mark.asyncio
    async def test_analyze_marks_quick_wins(self, db):
        svc, pid = await _setup_with_dda(db, "BASICA")
        await svc.analyze_project(pid, categoria_objetivo="BASICA")
        qw_gaps = await svc.list_gaps(pid, only_quick_wins=True)
        assert len(qw_gaps) > 0
        for g in qw_gaps:
            md = g.metadata_jsonb or {}
            assert md.get("quick_win") is True

    @pytest.mark.asyncio
    async def test_analyze_force_deletes_previous(self, db):
        svc, pid = await _setup_with_dda(db, "BASICA")
        r1 = await svc.analyze_project(pid, categoria_objetivo="BASICA")
        count1 = r1["gaps_created"]

        r2 = await svc.analyze_project(pid, force=True, categoria_objetivo="BASICA")
        count2 = r2["gaps_created"]
        # Should be the same count (re-analysis of same data)
        assert count2 == count1

    @pytest.mark.asyncio
    async def test_analyze_force_false_raises_if_already(self, db):
        svc, pid = await _setup_with_dda(db, "BASICA")
        await svc.analyze_project(pid, categoria_objetivo="BASICA")
        with pytest.raises(GapAlreadyAnalyzedError):
            await svc.analyze_project(pid, categoria_objetivo="BASICA")

    @pytest.mark.asyncio
    async def test_analyze_fills_metadata_jsonb(self, db):
        svc, pid = await _setup_with_dda(db, "BASICA")
        await svc.analyze_project(pid, categoria_objetivo="BASICA")
        gaps = await svc.list_gaps(pid)
        assert len(gaps) > 0
        md = gaps[0].metadata_jsonb
        assert md is not None
        required_keys = {
            "motor", "catalog_version", "codigo_medida", "familia",
            "estado_actual", "estado_objetivo", "esfuerzo_horas",
            "quick_win", "nuclear", "guia_remediacion", "evidencia_tipica",
            "notas_auditor", "dda_entry_id", "generated_at",
        }
        assert required_keys.issubset(set(md.keys())), f"Missing keys: {required_keys - set(md.keys())}"

    @pytest.mark.asyncio
    async def test_analyze_uses_categoria_objetivo_override(self, db):
        svc, pid = await _setup_with_dda(db, "BASICA")
        # Override to ALTA which has stricter requirements
        result = await svc.analyze_project(pid, categoria_objetivo="ALTA")
        assert result["categoria_usada"] == "ALTA"
        # ALTA should create more gaps than BASICA (target L4 vs L2)
        assert result["gaps_created"] >= 40


# ================================================================
# DASHBOARD TESTS
# ================================================================

class TestDashboard:

    @pytest.mark.asyncio
    async def test_dashboard_empty_returns_zeros_no_404(self, db):
        """CRITICAL: Empty project returns dashboard with zeros, NOT 404."""
        svc, pid, _ = await _setup_gap_env(db)
        dash = await svc.get_dashboard(pid)
        assert dash["total_gaps"] == 0
        assert dash["by_semaforo"] == {"verde": 0, "amarillo": 0, "rojo": 0}
        assert dash["top_10_critical"] == []
        assert dash["quick_wins"] == []
        assert dash["nuclear_gaps"] == []

    @pytest.mark.asyncio
    async def test_dashboard_with_gaps_calculates_counts(self, db):
        svc, pid = await _setup_with_dda(db, "BASICA")
        await svc.analyze_project(pid, categoria_objetivo="BASICA")
        dash = await svc.get_dashboard(pid)
        assert dash["total_gaps"] > 0
        total_sev = sum(dash["by_severidad"].values())
        assert total_sev == dash["total_gaps"]

    @pytest.mark.asyncio
    async def test_dashboard_top_10_orders_by_severity(self, db):
        svc, pid = await _setup_with_dda(db, "MEDIA")
        await svc.analyze_project(pid, categoria_objetivo="MEDIA")
        dash = await svc.get_dashboard(pid)
        top = dash["top_10_critical"]
        assert len(top) <= 10
        if len(top) >= 2:
            assert top[0]["severidad_numeric"] >= top[1]["severidad_numeric"]

    @pytest.mark.asyncio
    async def test_dashboard_quick_wins_filters(self, db):
        svc, pid = await _setup_with_dda(db, "BASICA")
        await svc.analyze_project(pid, categoria_objetivo="BASICA")
        dash = await svc.get_dashboard(pid)
        for qw in dash["quick_wins"]:
            assert qw["quick_win"] is True

    @pytest.mark.asyncio
    async def test_dashboard_nuclear_gaps_filters(self, db):
        svc, pid = await _setup_with_dda(db, "MEDIA")
        await svc.analyze_project(pid, categoria_objetivo="MEDIA")
        dash = await svc.get_dashboard(pid)
        for ng in dash["nuclear_gaps"]:
            assert ng["nuclear"] is True


# ================================================================
# FILTER TESTS
# ================================================================

class TestFilters:

    @pytest.mark.asyncio
    async def test_list_filter_by_severidad(self, db):
        svc, pid = await _setup_with_dda(db, "BASICA")
        await svc.analyze_project(pid, categoria_objetivo="BASICA")
        criticas = await svc.list_gaps(pid, severidad="critica")
        for g in criticas:
            assert g.severidad == "critica"

    @pytest.mark.asyncio
    async def test_list_filter_by_familia(self, db):
        svc, pid = await _setup_with_dda(db, "BASICA")
        await svc.analyze_project(pid, categoria_objetivo="BASICA")
        org_gaps = await svc.list_gaps(pid, familia="org")
        for g in org_gaps:
            assert (g.metadata_jsonb or {}).get("familia") == "org"

    @pytest.mark.asyncio
    async def test_list_filter_only_quick_wins(self, db):
        svc, pid = await _setup_with_dda(db, "BASICA")
        await svc.analyze_project(pid, categoria_objetivo="BASICA")
        qw = await svc.list_gaps(pid, only_quick_wins=True)
        for g in qw:
            assert (g.metadata_jsonb or {}).get("quick_win") is True

    @pytest.mark.asyncio
    async def test_list_filter_only_nuclear(self, db):
        svc, pid = await _setup_with_dda(db, "MEDIA")
        await svc.analyze_project(pid, categoria_objetivo="MEDIA")
        nuc = await svc.list_gaps(pid, only_nuclear=True)
        for g in nuc:
            assert (g.metadata_jsonb or {}).get("nuclear") is True

    @pytest.mark.asyncio
    async def test_list_combined_filters(self, db):
        svc, pid = await _setup_with_dda(db, "MEDIA")
        await svc.analyze_project(pid, categoria_objetivo="MEDIA")
        results = await svc.list_gaps(pid, severidad="critica", only_nuclear=True)
        for g in results:
            assert g.severidad == "critica"
            assert (g.metadata_jsonb or {}).get("nuclear") is True

    @pytest.mark.asyncio
    async def test_list_filter_by_estado(self, db):
        """Filter by estado=abierto returns only open gaps."""
        svc, pid, _ = await _setup_gap_env(db)
        await _create_test_gap(svc, pid, "E-001", estado="abierto")
        await _create_test_gap(svc, pid, "E-002", estado="cerrado")
        open_gaps = await svc.list_gaps(pid, estado="abierto")
        assert len(open_gaps) == 1
        assert open_gaps[0].medida_afectada == "E-001"


# ================================================================
# EDGE CASE / COVERAGE TESTS
# ================================================================

class TestEdgeCases:

    @pytest.mark.asyncio
    async def test_get_gap_wrong_fuente_raises(self, db):
        """Finding exists but fuente != gap_analysis raises GapNotFoundError."""
        svc, pid, _ = await _setup_gap_env(db)
        # Create a finding with different fuente
        f = Finding(
            project_id=pid,
            fuente="manual",
            severidad="alta",
            medida_afectada="org.1",
            estado="abierto",
        )
        svc.db.add(f)
        await svc.db.flush()
        with pytest.raises(GapNotFoundError, match="not a gap analysis finding"):
            await svc.get_gap(f.id)

    @pytest.mark.asyncio
    async def test_update_gap_invalid_estado_raises(self, db):
        """Update with invalid estado raises GapValidationError."""
        svc, pid, _ = await _setup_gap_env(db)
        gap = await _create_test_gap(svc, pid)
        with pytest.raises(GapValidationError, match="Invalid estado"):
            await svc.update_gap(gap.id, estado="inventado")

    @pytest.mark.asyncio
    async def test_update_gap_invalid_severidad_raises(self, db):
        """Update with invalid severidad raises GapValidationError."""
        svc, pid, _ = await _setup_gap_env(db)
        gap = await _create_test_gap(svc, pid)
        with pytest.raises(GapValidationError, match="Invalid severidad"):
            await svc.update_gap(gap.id, severidad="inventada")

    @pytest.mark.asyncio
    async def test_close_gap_already_closed_raises(self, db):
        """Close already-closed gap raises GapStateError."""
        svc, pid, _ = await _setup_gap_env(db)
        gap = await _create_test_gap(svc, pid)
        await svc.close_gap(gap.id, resolution_notes="Done")
        with pytest.raises(GapStateError, match="already closed"):
            await svc.close_gap(gap.id, resolution_notes="Again")

    @pytest.mark.asyncio
    async def test_analyze_invalid_categoria_objetivo_raises(self, db):
        """Invalid categoria_objetivo raises GapValidationError."""
        svc, pid, _ = await _setup_gap_env(db)
        with pytest.raises(GapValidationError, match="Invalid categoria_objetivo"):
            await svc.analyze_project(pid, categoria_objetivo="INVENTADA")

    @pytest.mark.asyncio
    async def test_analyze_auto_detect_categoria(self, db):
        """Analyze without categoria_objetivo auto-detects from categorization table."""
        svc, pid = await _setup_with_dda(db, "MEDIA")
        # Don't pass categoria_objetivo — should auto-detect MEDIA
        result = await svc.analyze_project(pid)
        assert result["categoria_usada"] == "MEDIA"
        assert result["gaps_created"] > 0

    @pytest.mark.asyncio
    async def test_analyze_skips_at_target_level(self, db):
        """#21 Ola 4 · medida con estado >= target produce no gap (continue).

        Migrado de controls.estado (tabla vacía · bug) → estado_implementacion
        de la SoA: 'implantada' deriva CMM L3, que supera el target BASICA (L2),
        así que la medida se salta."""
        svc, pid = await _setup_with_dda(db, "BASICA")

        # Get first applicable DdA entry
        dda_result = await db.execute(
            text(
                "SELECT de.id FROM dda_entries de "
                "JOIN ens_measures em ON em.id = de.measure_id "
                "WHERE de.project_id = :pid AND de.aplicabilidad != 'no_aplica' "
                "AND de.deleted_at IS NULL "
                "ORDER BY em.codigo LIMIT 1"
            ),
            {"pid": str(pid)},
        )
        dda_entry_id = str(dda_result.scalar())

        # #21 · marca la medida 'implantada' (→ CMM L3, derivado de la SoA).
        # L3 >= target BASICA (L2) → se salta. (Antes: INSERT controls L2.)
        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        await db.execute(text(
            "UPDATE dda_entries SET estado_implementacion = 'implantada' "
            "WHERE id = :did"
        ), {"did": dda_entry_id})
        await db.execute(text("RESET ROLE"))
        await db.flush()

        # Run analysis — la entry 'implantada' (L3) se salta (L3 >= L2 target)
        result = await svc.analyze_project(pid, categoria_objetivo="BASICA")
        # All other entries are at L0 → gap. This one at L2 → no gap.
        # So we should have at least 1 fewer gap than total applicable
        all_applicable = await db.execute(text(
            "SELECT COUNT(*) FROM dda_entries "
            "WHERE project_id = :pid AND aplicabilidad != 'no_aplica' AND deleted_at IS NULL"
        ), {"pid": str(pid)})
        total_applicable = all_applicable.scalar()
        assert result["gaps_created"] == total_applicable - 1

    # ════════════════════════════════════════════════════════════════
    # #21 Ola 4 · CMM derivado de la SoA (estado_implementacion), NO de
    # controls (vacía → siempre L0 = EL BUG). derive_control_state + acople L4.
    # ════════════════════════════════════════════════════════════════

    def test_derive_control_state_mapping(self):
        """Mapping unit: cada estado_implementacion → su nivel CMM (CCN-STIC 804)."""
        from backend.app.motors.m04_gap.service import derive_control_state

        assert derive_control_state("no_aplica") is None      # excluida
        assert derive_control_state("no_valorado") == "L0"    # sin valorar
        assert derive_control_state("no_implantada") == "L0"  # inexistente
        assert derive_control_state("parcial") == "L1"        # inicial
        assert derive_control_state("implantada") == "L3"     # definido
        assert derive_control_state(None) == "L0"             # default conservador
        assert derive_control_state("grafia_desconocida") == "L0"  # nunca silencia

    @pytest.mark.asyncio
    async def test_implantada_derives_L3_not_L0_bug_fixed(self, db):
        """EL BUG ARREGLADO: una medida 'implantada' deriva CMM L3, NO L0.

        Antes el gap engine leía controls.estado (tabla VACÍA) → siempre L0 →
        gap máximo falso para TODA medida (aunque estuviera implantada). Ahora
        deriva de estado_implementacion (la SoA): implantada (L3) >= MEDIA (L3)
        → NO gap. Si el bug persistiera (L0 < L3) → SÍ habría gap."""
        svc, pid = await _setup_with_dda(db, "MEDIA")

        row = (await db.execute(text(
            "SELECT de.id, em.codigo FROM dda_entries de "
            "JOIN ens_measures em ON em.id = de.measure_id "
            "WHERE de.project_id = :pid AND de.aplicabilidad != 'no_aplica' "
            "AND de.deleted_at IS NULL ORDER BY em.codigo LIMIT 1"
        ), {"pid": str(pid)})).first()
        dda_entry_id, codigo = str(row[0]), row[1]

        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        await db.execute(text(
            "UPDATE dda_entries SET estado_implementacion = 'implantada' "
            "WHERE id = :did"
        ), {"did": dda_entry_id})
        await db.execute(text("RESET ROLE"))
        await db.flush()

        await svc.analyze_project(pid, categoria_objetivo="MEDIA")

        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        gap_for_measure = await db.scalar(text(
            "SELECT count(*) FROM findings WHERE project_id = :pid "
            "AND medida_afectada = :cod AND fuente = 'gap_analysis' "
            "AND deleted_at IS NULL"
        ), {"pid": str(pid), "cod": codigo})
        assert gap_for_measure == 0, (
            "medida 'implantada' NO debe tener gap (L3 >= MEDIA L3); "
            "si lo tiene, el bug controls-siempre-L0 sigue vivo"
        )

    @pytest.mark.asyncio
    async def test_ALTA_L4_requires_implantada_plus_evidencia_verde(self, db):
        """Acople #20→#21 · ALTA (target L4): 'implantada' SOLA deriva L3 → gap;
        'implantada' + evidencia VERDE (semáforo #20) → L4 → no gap. La madurez
        se demuestra con evidencia, no solo se declara."""
        svc, pid = await _setup_with_dda(db, "ALTA")

        row = (await db.execute(text(
            "SELECT de.id, em.codigo FROM dda_entries de "
            "JOIN ens_measures em ON em.id = de.measure_id "
            "WHERE de.project_id = :pid AND de.aplicabilidad != 'no_aplica' "
            "AND de.deleted_at IS NULL ORDER BY em.codigo LIMIT 1"
        ), {"pid": str(pid)})).first()
        dda_entry_id, codigo = str(row[0]), row[1]

        # implantada + evidencia en regla (vigente, clean, no caducada) → verde → L4
        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        await db.execute(text(
            "UPDATE dda_entries SET estado_implementacion = 'implantada' "
            "WHERE id = :did"
        ), {"did": dda_entry_id})
        await db.execute(text(
            "INSERT INTO evidence "
            "(id, project_id, measure_code, vigente, scan_status, "
            "fecha_caducidad, created_at) "
            "VALUES (:id, :pid, :cod, TRUE, 'clean', "
            "(now() + interval '365 days')::date, now())"
        ), {"id": str(uuid4()), "pid": str(pid), "cod": codigo})
        await db.execute(text("RESET ROLE"))
        await db.flush()

        await svc.analyze_project(pid, categoria_objetivo="ALTA")

        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        gap_for_measure = await db.scalar(text(
            "SELECT count(*) FROM findings WHERE project_id = :pid "
            "AND medida_afectada = :cod AND fuente = 'gap_analysis' "
            "AND deleted_at IS NULL"
        ), {"pid": str(pid), "cod": codigo})
        assert gap_for_measure == 0, (
            "implantada + evidencia verde → L4 → ALTA (L4) sin gap"
        )
