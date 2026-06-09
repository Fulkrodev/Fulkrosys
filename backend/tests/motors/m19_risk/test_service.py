"""Tests del service core Motor 19 -- Project Risk Management.

Verifica CRUD, catalog instantiation, lifecycle transitions,
and dashboard. Patron consistente con M3 DdA Engine.
"""
import pytest
from uuid import uuid4

from sqlalchemy import text

from backend.app.database import set_tenant_context
from backend.app.models.planning import ProjectRisk
from backend.app.motors.m19_risk.service import ProjectRiskService
from backend.app.motors.m19_risk.exceptions import (
    ProjectRiskNotFoundError,
    ProjectRiskValidationError,
    ProjectRiskStateError,
    CatalogAlreadyInstantiatedError,
)
from backend.tests.conftest import setup_test_project, _admin_setup


# ================================================================
# HELPER
# ================================================================

async def _setup_risk_env(db):
    """Create project + set RLS context. Returns (svc, project_id)."""
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(db, client_id=client_id, project_id=project_id)
    svc = ProjectRiskService(db)
    return svc, project_id


async def _create_test_risk(svc, project_id, code="T-001", **overrides):
    """Create a single test risk with defaults."""
    defaults = dict(
        project_id=project_id,
        risk_code=code,
        titulo=f"Test risk {code}",
        descripcion="Test description",
        categoria="tecnico",
        probabilidad=0.5,
        impacto_dias=10,
        owner="Marcos",
    )
    defaults.update(overrides)
    return await svc.create_risk(**defaults)


# ================================================================
# CRUD TESTS (1-8)
# ================================================================

class TestCrud:

    @pytest.mark.asyncio
    async def test_create_risk_minimal_fields(self, db):
        """C1: Create risk with only required fields."""
        svc, pid = await _setup_risk_env(db)
        risk = await svc.create_risk(
            project_id=pid, risk_code="T-001", titulo="Minimal risk"
        )
        assert risk.risk_code == "T-001"
        assert risk.titulo == "Minimal risk"
        assert risk.status == "identificado"
        assert risk.id is not None

    @pytest.mark.asyncio
    async def test_create_risk_all_fields(self, db):
        """C2: Create risk with all optional fields populated."""
        svc, pid = await _setup_risk_env(db)
        risk = await svc.create_risk(
            project_id=pid,
            risk_code="T-002",
            titulo="Full risk",
            descripcion="Full desc",
            categoria="normativo",
            probabilidad=0.8,
            impacto_dias=20,
            impacto_euros=5000.0,
            owner="Marcos",
            trigger_condicion="Si cambia la ley",
            mitigation_plan={"action": "revisar"},
            contingency_plan={"action": "escalar"},
        )
        assert risk.categoria == "normativo"
        assert risk.probabilidad == 0.8
        assert risk.impacto_euros == 5000.0
        assert risk.mitigation_plan == {"action": "revisar"}
        assert risk.contingency_plan == {"action": "escalar"}

    @pytest.mark.asyncio
    async def test_create_risk_invalid_status_raises(self, db):
        """C3: Invalid status raises ProjectRiskValidationError."""
        svc, pid = await _setup_risk_env(db)
        with pytest.raises(ProjectRiskValidationError, match="Invalid status"):
            await svc.create_risk(
                project_id=pid, risk_code="T-003",
                titulo="Bad status", status="inexistente",
            )

    @pytest.mark.asyncio
    async def test_create_risk_invalid_categoria_raises(self, db):
        """C4: Invalid categoria raises ProjectRiskValidationError."""
        svc, pid = await _setup_risk_env(db)
        with pytest.raises(ProjectRiskValidationError, match="Invalid categoria"):
            await svc.create_risk(
                project_id=pid, risk_code="T-004",
                titulo="Bad cat", categoria="inventada",
            )

    @pytest.mark.asyncio
    async def test_create_risk_invalid_probabilidad_raises(self, db):
        """C5: Probabilidad out of range raises ProjectRiskValidationError."""
        svc, pid = await _setup_risk_env(db)
        with pytest.raises(ProjectRiskValidationError, match="probabilidad"):
            await svc.create_risk(
                project_id=pid, risk_code="T-005",
                titulo="Bad prob", probabilidad=1.5,
            )

    @pytest.mark.asyncio
    async def test_get_risk_not_found_raises(self, db):
        """C6: Get nonexistent risk raises ProjectRiskNotFoundError."""
        svc, _ = await _setup_risk_env(db)
        with pytest.raises(ProjectRiskNotFoundError):
            await svc.get_risk(uuid4())

    @pytest.mark.asyncio
    async def test_list_risks_empty_returns_empty(self, db):
        """C7: List risks on empty project returns empty list."""
        svc, pid = await _setup_risk_env(db)
        risks = await svc.list_risks(pid)
        assert risks == []

    @pytest.mark.asyncio
    async def test_list_risks_with_filters(self, db):
        """C8: List risks with status, categoria, owner filters."""
        svc, pid = await _setup_risk_env(db)
        await _create_test_risk(svc, pid, "F-001", categoria="tecnico", owner="Ana")
        await _create_test_risk(svc, pid, "F-002", categoria="normativo", owner="Marcos")
        await _create_test_risk(svc, pid, "F-003", categoria="tecnico", owner="Marcos")

        by_cat = await svc.list_risks(pid, categoria="tecnico")
        assert len(by_cat) == 2

        by_owner = await svc.list_risks(pid, owner="Marcos")
        assert len(by_owner) == 2

        by_both = await svc.list_risks(pid, categoria="tecnico", owner="Marcos")
        assert len(by_both) == 1


# ================================================================
# UPDATE + DELETE TESTS (9-11)
# ================================================================

class TestUpdateDelete:

    @pytest.mark.asyncio
    async def test_update_risk_partial_fields(self, db):
        """U1: Partial update changes only provided fields."""
        svc, pid = await _setup_risk_env(db)
        risk = await _create_test_risk(svc, pid, "U-001")
        updated = await svc.update_risk(risk.id, titulo="Updated title", probabilidad=0.9)
        assert updated.titulo == "Updated title"
        assert updated.probabilidad == 0.9
        assert updated.descripcion == "Test description"  # unchanged

    @pytest.mark.asyncio
    async def test_update_risk_immutable_fields_ignored(self, db):
        """U2: Attempting to change id, project_id, risk_code, created_at is silently ignored."""
        svc, pid = await _setup_risk_env(db)
        risk = await _create_test_risk(svc, pid, "U-002")
        original_id = risk.id
        original_code = risk.risk_code

        updated = await svc.update_risk(
            risk.id,
            id=uuid4(),
            project_id=uuid4(),
            risk_code="CHANGED",
            titulo="Still updates",
        )
        assert updated.id == original_id
        assert updated.risk_code == original_code
        assert updated.titulo == "Still updates"

    @pytest.mark.asyncio
    async def test_delete_risk_soft_deletes(self, db):
        """U3: Soft delete sets deleted_at, get_risk then raises NotFound."""
        svc, pid = await _setup_risk_env(db)
        risk = await _create_test_risk(svc, pid, "D-001")
        await svc.delete_risk(risk.id)
        with pytest.raises(ProjectRiskNotFoundError):
            await svc.get_risk(risk.id)


# ================================================================
# CATALOG INSTANTIATION TESTS (12-15)
# ================================================================

class TestCatalog:

    @pytest.mark.asyncio
    async def test_is_catalog_instantiated_false_initially(self, db):
        """K1: Fresh project has no catalog instantiated."""
        svc, pid = await _setup_risk_env(db)
        assert await svc.is_catalog_instantiated(pid) is False

    @pytest.mark.asyncio
    async def test_instantiate_catalog_creates_30_risks(self, db):
        """K2: Instantiate creates exactly 30 risks."""
        svc, pid = await _setup_risk_env(db)
        result = await svc.instantiate_catalog_for_project(pid)
        assert result["risks_created"] == 30
        assert result["risks_skipped"] == 0
        assert len(result["categorias_loaded"]) == 6

        risks = await svc.list_risks(pid)
        assert len(risks) == 30
        assert await svc.is_catalog_instantiated(pid) is True

    @pytest.mark.asyncio
    async def test_instantiate_catalog_already_loaded_raises_unless_force(self, db):
        """K3: Double instantiation raises unless force=True."""
        svc, pid = await _setup_risk_env(db)
        await svc.instantiate_catalog_for_project(pid)

        with pytest.raises(CatalogAlreadyInstantiatedError):
            await svc.instantiate_catalog_for_project(pid)

        # With force=True, it skips existing codes
        result = await svc.instantiate_catalog_for_project(pid, force=True)
        assert result["risks_created"] == 0
        assert result["risks_skipped"] == 30

    @pytest.mark.asyncio
    async def test_instantiate_catalog_only_categorias_filters(self, db):
        """K4: only_categorias filters to specific categories."""
        svc, pid = await _setup_risk_env(db)
        result = await svc.instantiate_catalog_for_project(
            pid, only_categorias=["tecnico", "normativo"]
        )
        assert result["risks_created"] == 11  # tecnico=5, normativo=6
        assert set(result["categorias_loaded"]) == {"tecnico", "normativo"}


# ================================================================
# LIFECYCLE TRANSITION TESTS (16-22)
# ================================================================

class TestLifecycle:

    @pytest.mark.asyncio
    async def test_monitor_risk_from_identificado_ok(self, db):
        """L1: Transition identificado -> monitorizado succeeds."""
        svc, pid = await _setup_risk_env(db)
        risk = await _create_test_risk(svc, pid, "L-001")
        result = await svc.monitor_risk(risk.id)
        assert result.status == "monitorizado"

    @pytest.mark.asyncio
    async def test_monitor_risk_from_wrong_status_raises(self, db):
        """L2: Monitor from non-identificado raises StateError."""
        svc, pid = await _setup_risk_env(db)
        risk = await _create_test_risk(svc, pid, "L-002")
        await svc.monitor_risk(risk.id)  # -> monitorizado
        with pytest.raises(ProjectRiskStateError, match="Must be 'identificado'"):
            await svc.monitor_risk(risk.id)  # already monitorizado

    @pytest.mark.asyncio
    async def test_monitor_risk_with_notas_appends_to_descripcion(self, db):
        """L3: Monitor with notas appends timestamped note to descripcion."""
        svc, pid = await _setup_risk_env(db)
        risk = await _create_test_risk(svc, pid, "L-003", descripcion="Original")
        result = await svc.monitor_risk(risk.id, notas="Watch this closely")
        assert "Original" in result.descripcion
        assert "Watch this closely" in result.descripcion
        assert "[Monitorizaci" in result.descripcion  # timestamp marker

    @pytest.mark.asyncio
    async def test_materialize_risk_writes_to_materialization_evidence_not_contingency_plan(self, db):
        """L4 CRITICAL: materialization_evidence gets data, contingency_plan stays intact."""
        svc, pid = await _setup_risk_env(db)
        risk = await _create_test_risk(
            svc, pid, "L-004",
            contingency_plan={"original": "plan"},
        )
        await svc.monitor_risk(risk.id)
        result = await svc.materialize_risk(
            risk.id,
            trigger_evidence="Sprint delay detected",
            materialized_by="Marcos",
        )
        # CRITICAL: contingency_plan NOT mutated
        assert result.contingency_plan == {"original": "plan"}
        # CRITICAL: materialization_evidence has the data
        assert result.materialization_evidence is not None
        assert result.materialization_evidence["trigger_evidence"] == "Sprint delay detected"
        assert result.materialization_evidence["materialized_by"] == "Marcos"
        assert "materialized_at" in result.materialization_evidence
        assert result.materializado_at is not None

    @pytest.mark.asyncio
    async def test_materialize_risk_from_wrong_status_raises(self, db):
        """L5: Materialize from non-monitorizado raises StateError."""
        svc, pid = await _setup_risk_env(db)
        risk = await _create_test_risk(svc, pid, "L-005")
        with pytest.raises(ProjectRiskStateError, match="Must be 'monitorizado'"):
            await svc.materialize_risk(risk.id, trigger_evidence="test")

    @pytest.mark.asyncio
    async def test_close_risk_writes_to_closure_evidence_not_mitigation_plan(self, db):
        """L6 CRITICAL: closure_evidence gets data, mitigation_plan stays intact."""
        svc, pid = await _setup_risk_env(db)
        risk = await _create_test_risk(
            svc, pid, "L-006",
            mitigation_plan={"original": "mitigation"},
        )
        result = await svc.close_risk(
            risk.id,
            resolution_notes="Risk accepted and closed",
            closed_by="RSEG",
        )
        # CRITICAL: mitigation_plan NOT mutated
        assert result.mitigation_plan == {"original": "mitigation"}
        # CRITICAL: closure_evidence has the data
        assert result.closure_evidence is not None
        assert result.closure_evidence["resolution_notes"] == "Risk accepted and closed"
        assert result.closure_evidence["closed_by"] == "RSEG"
        assert "closed_at" in result.closure_evidence
        assert result.cerrado_at is not None

    @pytest.mark.asyncio
    async def test_close_risk_from_identificado_directly_ok(self, db):
        """L7: Close directly from identificado is a valid transition."""
        svc, pid = await _setup_risk_env(db)
        risk = await _create_test_risk(svc, pid, "L-007")
        assert risk.status == "identificado"
        result = await svc.close_risk(risk.id, resolution_notes="Not applicable")
        assert result.status == "cerrado"


# ================================================================
# DASHBOARD TESTS (23-25)
# ================================================================

class TestDashboard:

    @pytest.mark.asyncio
    async def test_get_dashboard_empty_project_returns_zeros_no_404(self, db):
        """D1 CRITICAL: Empty project returns dashboard with zeros, NOT 404."""
        svc, pid = await _setup_risk_env(db)
        dash = await svc.get_dashboard(pid)
        assert dash["total_risks"] == 0
        assert dash["by_status"] == {}
        assert dash["by_semaforo"] == {"verde": 0, "amarillo": 0, "rojo": 0}
        assert dash["top_critical"] == []
        assert dash["recently_materialized"] == []

    @pytest.mark.asyncio
    async def test_get_dashboard_with_30_risks_calculates_semaforo(self, db):
        """D2: Dashboard with catalog risks calculates semaforo correctly."""
        svc, pid = await _setup_risk_env(db)
        await svc.instantiate_catalog_for_project(pid)

        dash = await svc.get_dashboard(pid)
        assert dash["total_risks"] == 30
        total_semaforo = sum(dash["by_semaforo"].values())
        assert total_semaforo == 30
        assert all(k in dash["by_semaforo"] for k in ("verde", "amarillo", "rojo"))

    @pytest.mark.asyncio
    async def test_get_dashboard_top_critical_excludes_cerrado(self, db):
        """D3: Top critical excludes cerrado risks and orders by score desc."""
        svc, pid = await _setup_risk_env(db)
        # High score risk (will be closed)
        r1 = await _create_test_risk(
            svc, pid, "DC-001", probabilidad=0.9, impacto_dias=30
        )
        # Medium score risk (stays active)
        r2 = await _create_test_risk(
            svc, pid, "DC-002", probabilidad=0.5, impacto_dias=20
        )
        # Low score risk
        await _create_test_risk(
            svc, pid, "DC-003", probabilidad=0.1, impacto_dias=2
        )

        # Close the high score risk
        await svc.close_risk(r1.id, resolution_notes="Resolved")

        dash = await svc.get_dashboard(pid)
        top_codes = [t["risk_code"] for t in dash["top_critical"]]
        # DC-001 (cerrado) should NOT be in top_critical
        assert "DC-001" not in top_codes
        # DC-002 should be first (highest active score)
        assert top_codes[0] == "DC-002"
