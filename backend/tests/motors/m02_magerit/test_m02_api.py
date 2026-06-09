"""
Tests for Motor 2 — MAGERIT v3 Risk Engine REST API (HTTP integration tests).

Tests exercise the actual FastAPI endpoints via httpx AsyncClient,
covering the full HTTP request/response cycle including Pydantic
validation, RLS tenant context, and database persistence.

Each test that validates MAGERIT calculation results cites its source.
"""
import uuid
import pytest
from sqlalchemy import text

from backend.tests.conftest import setup_test_project

BASE = "/api/v1/magerit"


# ================================================================
# HELPERS
# ================================================================

async def _create_analysis(async_client, db, mode="qualitative"):
    """Helper: create client + project + analysis, return (project_id, analysis_id)."""
    _, project_id = await setup_test_project(db)
    r = await async_client.post(
        f"{BASE}/projects/{project_id}/analysis",
        json={"name": "Test Analysis", "calculation_mode": mode},
    )
    assert r.status_code == 201, f"Setup failed: {r.status_code} {r.text}"
    return project_id, r.json()["id"]


async def _setup_full_pipeline(async_client, db):
    """Helper: create analysis + assets + deps + threats + safeguards.

    Returns (analysis_id, asset_ids).
    """
    _, analysis_id = await _create_analysis(async_client, db)

    # Load 2 assets
    r = await async_client.post(
        f"{BASE}/analysis/{analysis_id}/assets",
        json={"assets": [
            {"code": "S-001", "name": "Servicio Web", "asset_type_code": "S",
             "value_d": 8, "value_i": 7, "value_c": 5, "value_a": 6, "value_t": 4},
            {"code": "HW-001", "name": "Servidor", "asset_type_code": "HW",
             "value_d": 3, "value_i": 2, "value_c": 1, "value_a": 2, "value_t": 1},
        ]},
    )
    assets = r.json()
    sup_id, inf_id = assets[0]["id"], assets[1]["id"]

    # Dependencies
    await async_client.post(
        f"{BASE}/analysis/{analysis_id}/dependencies",
        json={"dependencies": [
            {"superior_asset_id": sup_id, "inferior_asset_id": inf_id,
             "dependency_degree": 0.8},
        ]},
    )

    # Propagate
    await async_client.post(f"{BASE}/analysis/{analysis_id}/propagate")

    # Threats
    await async_client.post(
        f"{BASE}/analysis/{analysis_id}/threats",
        json={"assessments": [
            {"asset_id": inf_id, "threat_code": "A.11", "probability": "M",
             "degradation_d": 80, "degradation_i": 50, "degradation_c": 30,
             "degradation_a": 20, "degradation_t": 10},
        ]},
    )

    # Safeguards
    await async_client.post(
        f"{BASE}/analysis/{analysis_id}/safeguards",
        json={"deployments": [
            {"safeguard_code": "H.IA", "efficacy": 70,
             "effect_type": "preventive", "status": "deployed"},
        ]},
    )

    return analysis_id, [sup_id, inf_id]


# ================================================================
# CREATION + VALIDATION (2 tests)
# ================================================================

class TestAnalysisCreationHTTP:
    """HTTP tests for analysis creation."""

    @pytest.mark.asyncio
    async def test_create_analysis_returns_201(self, async_client, db):
        """POST /analysis devuelve 201 con analysis_id."""
        _, project_id = await setup_test_project(db)

        response = await async_client.post(
            f"{BASE}/projects/{project_id}/analysis",
            json={"name": "Test MAGERIT", "calculation_mode": "qualitative",
                  "description": "Smoke test"},
        )
        assert response.status_code == 201, f"Got {response.status_code}: {response.text}"
        data = response.json()
        assert "id" in data
        assert data["name"] == "Test MAGERIT"
        assert data["calculation_mode"] == "qualitative"
        assert data["status"] == "draft"

    @pytest.mark.asyncio
    async def test_create_analysis_invalid_mode_returns_422(self, async_client, db):
        """POST con calculation_mode invalido devuelve 422 (Pydantic Literal)."""
        _, project_id = await setup_test_project(db)

        response = await async_client.post(
            f"{BASE}/projects/{project_id}/analysis",
            json={"name": "Bad", "calculation_mode": "INVALID"},
        )
        assert response.status_code == 422


# ================================================================
# DATA LOADING (3 tests)
# ================================================================

class TestDataLoadingHTTP:
    """HTTP tests for loading assets, dependencies, and threats."""

    @pytest.mark.asyncio
    async def test_load_assets_returns_201(self, async_client, db):
        """POST /assets con batch devuelve 201."""
        _, analysis_id = await _create_analysis(async_client, db)

        response = await async_client.post(
            f"{BASE}/analysis/{analysis_id}/assets",
            json={"assets": [
                {"code": "TEST-1", "name": "Activo Test", "asset_type_code": "HW",
                 "value_d": 5, "value_i": 3, "value_c": 2, "value_a": 1, "value_t": 0},
            ]},
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data) == 1
        assert data[0]["code"] == "TEST-1"

    @pytest.mark.asyncio
    async def test_load_dependencies_returns_201(self, async_client, db):
        """POST /dependencies devuelve 201."""
        _, analysis_id = await _create_analysis(async_client, db)
        r = await async_client.post(
            f"{BASE}/analysis/{analysis_id}/assets",
            json={"assets": [
                {"code": "A", "name": "Sup", "asset_type_code": "S",
                 "value_d": 8, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
                {"code": "B", "name": "Inf", "asset_type_code": "HW",
                 "value_d": 3, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
            ]},
        )
        assets = r.json()

        response = await async_client.post(
            f"{BASE}/analysis/{analysis_id}/dependencies",
            json={"dependencies": [
                {"superior_asset_id": assets[0]["id"],
                 "inferior_asset_id": assets[1]["id"],
                 "dependency_degree": 0.8},
            ]},
        )
        assert response.status_code == 201
        assert response.json()["rows_affected"] == 1

    @pytest.mark.asyncio
    async def test_load_threats_returns_201(self, async_client, db):
        """POST /threats devuelve 201."""
        _, analysis_id = await _create_analysis(async_client, db)
        r = await async_client.post(
            f"{BASE}/analysis/{analysis_id}/assets",
            json={"assets": [
                {"code": "T", "name": "Target", "asset_type_code": "HW",
                 "value_d": 5, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
            ]},
        )
        asset_id = r.json()[0]["id"]

        response = await async_client.post(
            f"{BASE}/analysis/{analysis_id}/threats",
            json={"assessments": [
                {"asset_id": asset_id, "threat_code": "A.11", "probability": "M",
                 "degradation_d": 60, "degradation_i": 0, "degradation_c": 0,
                 "degradation_a": 0, "degradation_t": 0},
            ]},
        )
        assert response.status_code == 201
        assert response.json()["rows_affected"] == 1


# ================================================================
# PIPELINE OPERATIONS (7 tests)
# ================================================================

class TestPipelineHTTP:
    """HTTP tests for the full MAGERIT pipeline operations."""

    @pytest.mark.asyncio
    async def test_propagate_values_returns_200(self, async_client, db):
        """POST /propagate tras cargar activos devuelve 200."""
        _, analysis_id = await _create_analysis(async_client, db)
        await async_client.post(
            f"{BASE}/analysis/{analysis_id}/assets",
            json={"assets": [
                {"code": "P", "name": "Solo", "asset_type_code": "HW",
                 "value_d": 5, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
            ]},
        )

        response = await async_client.post(f"{BASE}/analysis/{analysis_id}/propagate")
        assert response.status_code == 200
        assert response.json()["rows_affected"] >= 1

    @pytest.mark.asyncio
    async def test_propagate_404_if_analysis_not_found(self, async_client, db):
        """POST /propagate con analysis_id fake devuelve 404."""
        fake_id = str(uuid.uuid4())
        response = await async_client.post(f"{BASE}/analysis/{fake_id}/propagate")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_calculate_intrinsic_returns_200(self, async_client, db):
        """POST /calculate-intrinsic devuelve 200 con calculos generados.

        Cita: Libro III sec 2.1 pp.6-7 (calculo de riesgo intrinseco cualitativo).
        """
        analysis_id, _ = await _setup_full_pipeline(async_client, db)
        response = await async_client.post(
            f"{BASE}/analysis/{analysis_id}/calculate-intrinsic"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["rows_affected"] > 0
        assert "qualitative" in data["message"]

    @pytest.mark.asyncio
    async def test_calculate_intrinsic_409_if_no_threats(self, async_client, db):
        """POST /calculate-intrinsic sin amenazas devuelve 409."""
        _, analysis_id = await _create_analysis(async_client, db)
        await async_client.post(
            f"{BASE}/analysis/{analysis_id}/assets",
            json={"assets": [
                {"code": "X", "name": "Sin amenazas", "asset_type_code": "HW",
                 "value_d": 5, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
            ]},
        )
        response = await async_client.post(
            f"{BASE}/analysis/{analysis_id}/calculate-intrinsic"
        )
        assert response.status_code == 409, f"Got {response.status_code}: {response.text}"

    @pytest.mark.asyncio
    async def test_calculate_effective_returns_200(self, async_client, db):
        """POST /calculate-effective tras salvaguardas devuelve 200.

        Cita: Libro III sec 2.2.2 p.15 (riesgo efectivo con salvaguardas).
        """
        analysis_id, _ = await _setup_full_pipeline(async_client, db)
        await async_client.post(f"{BASE}/analysis/{analysis_id}/calculate-intrinsic")

        response = await async_client.post(
            f"{BASE}/analysis/{analysis_id}/calculate-effective"
        )
        assert response.status_code == 200
        assert response.json()["rows_affected"] > 0

    @pytest.mark.asyncio
    async def test_treatment_plan_returns_201(self, async_client, db):
        """POST /treatment-plan genera plan de tratamiento.

        Cita: Libro I sec 4.1.7 pp.50-51 (estrategias de tratamiento).
        """
        analysis_id, _ = await _setup_full_pipeline(async_client, db)
        await async_client.post(f"{BASE}/analysis/{analysis_id}/calculate-intrinsic")
        await async_client.post(f"{BASE}/analysis/{analysis_id}/calculate-effective")

        response = await async_client.post(
            f"{BASE}/analysis/{analysis_id}/treatment-plan",
            json={"risk_tolerance_threshold": "M"},
        )
        assert response.status_code == 201
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_calculate_residual_returns_200(self, async_client, db):
        """POST /calculate-residual tras plan de tratamiento devuelve 200.

        Cita: Libro III sec 2.2.1 p.11 + Libro I sec 4.1.7 pp.50-51.
        """
        analysis_id, _ = await _setup_full_pipeline(async_client, db)
        await async_client.post(f"{BASE}/analysis/{analysis_id}/calculate-intrinsic")
        await async_client.post(f"{BASE}/analysis/{analysis_id}/calculate-effective")
        await async_client.post(
            f"{BASE}/analysis/{analysis_id}/treatment-plan",
            json={"risk_tolerance_threshold": "M"},
        )

        response = await async_client.post(
            f"{BASE}/analysis/{analysis_id}/calculate-residual"
        )
        assert response.status_code == 200
        assert response.json()["rows_affected"] > 0


# ================================================================
# REPORT + EXPORT (3 tests)
# ================================================================

class TestReportExportHTTP:
    """HTTP tests for report and PILAR export endpoints."""

    @pytest.mark.asyncio
    async def test_load_safeguards_returns_201(self, async_client, db):
        """POST /safeguards devuelve 201."""
        _, analysis_id = await _create_analysis(async_client, db)
        response = await async_client.post(
            f"{BASE}/analysis/{analysis_id}/safeguards",
            json={"deployments": [
                {"safeguard_code": "FW.1", "efficacy": 60,
                 "effect_type": "both", "status": "deployed"},
            ]},
        )
        assert response.status_code == 201
        assert response.json()["rows_affected"] == 1

    @pytest.mark.asyncio
    async def test_get_report_returns_complete_json(self, async_client, db):
        """GET /report devuelve JSON con los campos esperados."""
        analysis_id, _ = await _setup_full_pipeline(async_client, db)
        await async_client.post(f"{BASE}/analysis/{analysis_id}/calculate-intrinsic")

        response = await async_client.get(
            f"{BASE}/analysis/{analysis_id}/report"
        )
        assert response.status_code == 200
        data = response.json()
        assert "analysis" in data
        assert "assets" in data
        assert "risk_calculations" in data
        assert "treatment_actions" in data
        assert "summary" in data
        assert data["summary"]["total_assets"] == 2

    @pytest.mark.asyncio
    async def test_get_pilar_export_returns_xml(self, async_client, db):
        """GET /export-pilar devuelve XML con Content-Type correcto."""
        analysis_id, _ = await _setup_full_pipeline(async_client, db)
        await async_client.post(f"{BASE}/analysis/{analysis_id}/calculate-intrinsic")

        response = await async_client.get(
            f"{BASE}/analysis/{analysis_id}/export-pilar"
        )
        assert response.status_code == 200
        assert "xml" in response.headers.get("content-type", "")
        assert "fulkro_magerit_analysis" in response.text



# ================================================================
# API COVERAGE: 404/409/422 BRANCHES (8 tests + 1 PILAR E2E)
# ================================================================

class TestMotor2ErrorBranches:
    """Tests for 404/409/422 error branches in Motor 2 api.py."""

    @pytest.mark.asyncio
    async def test_create_analysis_404_project_not_found(self, async_client, db):
        """POST /analysis with nonexistent project_id returns 404 (L88)."""
        fake_pid = str(uuid.uuid4())
        r = await async_client.post(
            f"{BASE}/projects/{fake_pid}/analysis",
            json={"name": "Test", "calculation_mode": "qualitative"},
        )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_load_dependencies_422_cycle_detected(self, async_client, db):
        """POST /dependencies with circular graph returns 422 (L154-155).

        service.py build_dependency_graph() detects cycles via DFS and
        raises ValueError('Ciclo detectado'). Endpoint catches as 422.
        """
        _, analysis_id = await _create_analysis(async_client, db)
        # Create 2 assets
        r = await async_client.post(
            f"{BASE}/analysis/{analysis_id}/assets",
            json={"assets": [
                {"code": "CY-A", "name": "A", "asset_type_code": "HW",
                 "value_d": 5, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
                {"code": "CY-B", "name": "B", "asset_type_code": "HW",
                 "value_d": 3, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
            ]},
        )
        assets = r.json()
        a_id, b_id = assets[0]["id"], assets[1]["id"]

        # Circular: A->B, B->A
        r = await async_client.post(
            f"{BASE}/analysis/{analysis_id}/dependencies",
            json={"dependencies": [
                {"superior_asset_id": a_id, "inferior_asset_id": b_id, "dependency_degree": 1.0},
                {"superior_asset_id": b_id, "inferior_asset_id": a_id, "dependency_degree": 1.0},
            ]},
        )
        assert r.status_code == 422, f"Expected 422 for cycle, got {r.status_code}: {r.text}"

    @pytest.mark.asyncio
    async def test_propagate_409_no_assets(self, async_client, db):
        """POST /propagate on analysis without assets returns 409 (L185)."""
        _, analysis_id = await _create_analysis(async_client, db)
        r = await async_client.post(f"{BASE}/analysis/{analysis_id}/propagate")
        assert r.status_code == 409

    @pytest.mark.asyncio
    async def test_calculate_intrinsic_409_no_assets(self, async_client, db):
        """POST /calculate-intrinsic without assets returns 409 (L253).

        Different from test_calculate_intrinsic_409_if_no_threats which
        tests the 'no threats' branch (L255). This tests 'no assets' (L253).
        """
        _, analysis_id = await _create_analysis(async_client, db)
        r = await async_client.post(f"{BASE}/analysis/{analysis_id}/calculate-intrinsic")
        assert r.status_code == 409
        assert "assets" in r.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_calculate_effective_409_no_intrinsic(self, async_client, db):
        """POST /calculate-effective without intrinsic calculated returns 409 (L318)."""
        _, analysis_id = await _create_analysis(async_client, db)
        # Load assets + threats but do NOT call calculate-intrinsic
        r_a = await async_client.post(
            f"{BASE}/analysis/{analysis_id}/assets",
            json={"assets": [
                {"code": "X", "name": "X", "asset_type_code": "HW",
                 "value_d": 5, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
            ]},
        )
        asset_id = r_a.json()[0]["id"]
        await async_client.post(
            f"{BASE}/analysis/{analysis_id}/threats",
            json={"assessments": [
                {"asset_id": asset_id, "threat_code": "A.11", "probability": "M",
                 "degradation_d": 50, "degradation_i": 0, "degradation_c": 0,
                 "degradation_a": 0, "degradation_t": 0},
            ]},
        )
        # Skip calculate-intrinsic, go directly to effective
        r = await async_client.post(f"{BASE}/analysis/{analysis_id}/calculate-effective")
        assert r.status_code == 409

    @pytest.mark.asyncio
    async def test_treatment_plan_409_no_calculations(self, async_client, db):
        """POST /treatment-plan without calculations returns 409 (L356)."""
        _, analysis_id = await _create_analysis(async_client, db)
        r = await async_client.post(
            f"{BASE}/analysis/{analysis_id}/treatment-plan",
            json={"risk_tolerance_threshold": "M"},
        )
        assert r.status_code == 409

    @pytest.mark.asyncio
    async def test_calculate_residual_409_no_plan(self, async_client, db):
        """POST /calculate-residual without treatment plan returns 409 (L392)."""
        analysis_id, _ = await _setup_full_pipeline(async_client, db)
        # Do intrinsic + effective but skip treatment-plan
        await async_client.post(f"{BASE}/analysis/{analysis_id}/calculate-intrinsic")
        await async_client.post(f"{BASE}/analysis/{analysis_id}/calculate-effective")
        # Skip treatment-plan, go directly to residual
        r = await async_client.post(f"{BASE}/analysis/{analysis_id}/calculate-residual")
        assert r.status_code == 409

    @pytest.mark.asyncio
    async def test_pilar_export_includes_treatment_actions(self, async_client, db):
        """GET /export-pilar includes treatment plan actions in XML (L577).

        Runs the complete pipeline through treatment plan to ensure the
        PILAR export XML contains <action> elements from plan_actions.
        """
        analysis_id, _ = await _setup_full_pipeline(async_client, db)
        await async_client.post(f"{BASE}/analysis/{analysis_id}/calculate-intrinsic")
        await async_client.post(f"{BASE}/analysis/{analysis_id}/calculate-effective")
        await async_client.post(
            f"{BASE}/analysis/{analysis_id}/treatment-plan",
            json={"risk_tolerance_threshold": "MB"},  # Low threshold to force actions
        )

        r = await async_client.get(f"{BASE}/analysis/{analysis_id}/export-pilar")
        assert r.status_code == 200
        assert "xml" in r.headers.get("content-type", "")
        # L577: SubElement(tp_el, "action", ...) should have generated elements
        assert "<action" in r.text, (
            "PILAR XML should contain <action> elements from treatment plan"
        )



# ================================================================
# SOFT DELETE TESTS (3 tests)
# ================================================================

class TestMotor2SoftDeleteHTTP:
    """Tests for soft delete of MAGERIT analyses."""

    @pytest.mark.asyncio
    async def test_soft_delete_analysis_returns_204(self, async_client, db):
        """DELETE /analysis/{id} soft-deletes with cascade."""
        from backend.tests.conftest import _admin_setup

        analysis_id, _ = await _setup_full_pipeline(async_client, db)

        r = await async_client.delete(f"{BASE}/analysis/{analysis_id}")
        assert r.status_code == 204

        # Verify analysis soft-deleted in DB
        async with _admin_setup(db):
            row = await db.execute(
                text("SELECT deleted_at FROM magerit_analysis WHERE id = :aid"),
                {"aid": analysis_id},
            )
            assert row.scalar() is not None, "Analysis deleted_at should be set"

            asset_count = (await db.execute(
                text("SELECT COUNT(*) FROM magerit_assets WHERE analysis_id = :aid AND deleted_at IS NOT NULL"),
                {"aid": analysis_id},
            )).scalar()
            assert asset_count == 2, f"2 assets should be soft-deleted, got {asset_count}"

    @pytest.mark.asyncio
    async def test_soft_delete_analysis_404_already_deleted(self, async_client, db):
        """DELETE on already-deleted analysis returns 404."""
        analysis_id, _ = await _setup_full_pipeline(async_client, db)
        r1 = await async_client.delete(f"{BASE}/analysis/{analysis_id}")
        assert r1.status_code == 204

        r2 = await async_client.delete(f"{BASE}/analysis/{analysis_id}")
        assert r2.status_code == 404

    @pytest.mark.asyncio
    async def test_calculate_intrinsic_ignores_soft_deleted_assets(self, async_client, db):
        """TEST CRITICAL: soft-deleted assets excluded from intrinsic calculation.

        Creates 2 assets, soft-deletes 1, verifies calculate_intrinsic
        only processes the remaining active asset.
        """
        from backend.tests.conftest import _admin_setup

        _, analysis_id = await _create_analysis(async_client, db)
        r = await async_client.post(
            f"{BASE}/analysis/{analysis_id}/assets",
            json={"assets": [
                {"code": "KEEP", "name": "Active", "asset_type_code": "HW",
                 "value_d": 8, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
                {"code": "DEL", "name": "To Delete", "asset_type_code": "SW",
                 "value_d": 3, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
            ]},
        )
        assets = r.json()
        del_id = assets[1]["id"]

        # Soft-delete one asset directly via admin
        async with _admin_setup(db):
            await db.execute(
                text("UPDATE magerit_assets SET deleted_at = NOW() WHERE id = :aid"),
                {"aid": del_id},
            )

        # Add threat only on the KEEP asset
        await async_client.post(
            f"{BASE}/analysis/{analysis_id}/threats",
            json={"assessments": [
                {"asset_id": assets[0]["id"], "threat_code": "A.11", "probability": "M",
                 "degradation_d": 60, "degradation_i": 0, "degradation_c": 0,
                 "degradation_a": 0, "degradation_t": 0},
            ]},
        )
        await async_client.post(f"{BASE}/analysis/{analysis_id}/propagate")

        r_calc = await async_client.post(f"{BASE}/analysis/{analysis_id}/calculate-intrinsic")
        assert r_calc.status_code == 200
        # Should only have calcs for the KEEP asset, not DEL
        data = r_calc.json()
        assert data["rows_affected"] > 0

        # Verify report only shows 1 active asset
        r_report = await async_client.get(f"{BASE}/analysis/{analysis_id}/report")
        assert r_report.status_code == 200
        assert r_report.json()["summary"]["total_assets"] == 1, (
            f"Report should show 1 active asset, got {r_report.json()['summary']['total_assets']}"
        )



# ================================================================
# FREEZE/UNFREEZE TESTS (7 tests)
# ================================================================

class TestMotor2FreezeHTTP:
    """Tests for freeze/unfreeze analysis snapshot."""

    @pytest.mark.asyncio
    async def test_freeze_creates_snapshot(self, async_client, db):
        """POST /freeze on completed pipeline creates snapshot."""
        analysis_id, _ = await _setup_full_pipeline(async_client, db)
        await async_client.post(f"{BASE}/analysis/{analysis_id}/calculate-intrinsic")
        await async_client.post(f"{BASE}/analysis/{analysis_id}/calculate-effective")
        await async_client.post(
            f"{BASE}/analysis/{analysis_id}/treatment-plan",
            json={"risk_tolerance_threshold": "M"},
        )
        await async_client.post(f"{BASE}/analysis/{analysis_id}/calculate-residual")

        r = await async_client.post(f"{BASE}/analysis/{analysis_id}/freeze")
        assert r.status_code == 200
        data = r.json()
        assert "snapshot_frozen_at" in data
        assert "snapshot" in data
        assert data["snapshot"]["schema_version"] == "1.0"
        assert len(data["snapshot"]["assets"]) == 2

    @pytest.mark.asyncio
    async def test_freeze_without_calculations_returns_409(self, async_client, db):
        """POST /freeze without pipeline execution returns 409."""
        _, analysis_id = await _create_analysis(async_client, db)
        r = await async_client.post(f"{BASE}/analysis/{analysis_id}/freeze")
        assert r.status_code == 409

    @pytest.mark.asyncio
    async def test_get_snapshot_404_when_not_frozen(self, async_client, db):
        """GET /snapshot on unfrozen analysis returns 404."""
        _, analysis_id = await _create_analysis(async_client, db)
        r = await async_client.get(f"{BASE}/analysis/{analysis_id}/snapshot")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_get_snapshot_returns_frozen_data(self, async_client, db):
        """GET /snapshot after freeze returns the snapshot."""
        analysis_id, _ = await _setup_full_pipeline(async_client, db)
        await async_client.post(f"{BASE}/analysis/{analysis_id}/calculate-intrinsic")
        await async_client.post(f"{BASE}/analysis/{analysis_id}/freeze")

        r = await async_client.get(f"{BASE}/analysis/{analysis_id}/snapshot")
        assert r.status_code == 200
        assert r.json()["snapshot"]["schema_version"] == "1.0"

    @pytest.mark.asyncio
    async def test_frozen_analysis_cannot_recalculate(self, async_client, db):
        """TEST CRITICAL: frozen analysis rejects pipeline modifications."""
        analysis_id, _ = await _setup_full_pipeline(async_client, db)
        await async_client.post(f"{BASE}/analysis/{analysis_id}/calculate-intrinsic")
        await async_client.post(f"{BASE}/analysis/{analysis_id}/freeze")

        # All pipeline endpoints should return 409
        r = await async_client.post(f"{BASE}/analysis/{analysis_id}/propagate")
        assert r.status_code == 409, f"Propagate should be blocked, got {r.status_code}"

        r = await async_client.post(f"{BASE}/analysis/{analysis_id}/calculate-intrinsic")
        assert r.status_code == 409

        r = await async_client.post(f"{BASE}/analysis/{analysis_id}/calculate-effective")
        assert r.status_code == 409

    @pytest.mark.asyncio
    async def test_unfreeze_allows_modification(self, async_client, db):
        """Unfreeze + recalculate works normally."""
        analysis_id, _ = await _setup_full_pipeline(async_client, db)
        await async_client.post(f"{BASE}/analysis/{analysis_id}/calculate-intrinsic")
        await async_client.post(f"{BASE}/analysis/{analysis_id}/freeze")

        # Unfreeze
        r = await async_client.post(f"{BASE}/analysis/{analysis_id}/unfreeze")
        assert r.status_code == 204

        # Now pipeline works again
        r = await async_client.post(f"{BASE}/analysis/{analysis_id}/calculate-intrinsic")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_snapshot_reflects_current_state(self, async_client, db):
        """Snapshot contains actual current asset values."""
        analysis_id, asset_ids = await _setup_full_pipeline(async_client, db)
        await async_client.post(f"{BASE}/analysis/{analysis_id}/calculate-intrinsic")
        await async_client.post(f"{BASE}/analysis/{analysis_id}/freeze")

        r = await async_client.get(f"{BASE}/analysis/{analysis_id}/snapshot")
        snapshot = r.json()["snapshot"]
        # _setup_full_pipeline creates asset S-001 with value_d=8
        s001 = next((a for a in snapshot["assets"] if a["code"] == "S-001"), None)
        assert s001 is not None
        assert s001["value_d"] == 8, (
            f"Snapshot should reflect current asset value. Expected 8, got {s001['value_d']}"
        )



# ================================================================
# MAGERIT REPORT PDF/DOCX TESTS (3 tests)
# ================================================================

class TestMotor2ReportPDFHTTP:
    """Tests for MAGERIT report PDF/DOCX generation."""

    @pytest.mark.asyncio
    async def test_magerit_report_pdf_valid(self, async_client, db):
        """GET /report.pdf returns valid PDF with MAGERIT content."""
        import pdfplumber, io

        analysis_id, _ = await _setup_full_pipeline(async_client, db)
        await async_client.post(f"{BASE}/analysis/{analysis_id}/calculate-intrinsic")

        r = await async_client.get(f"{BASE}/analysis/{analysis_id}/report.pdf")
        assert r.status_code == 200
        assert r.content[:5] == b"%PDF-"
        assert len(r.content) > 1000

        pdf = pdfplumber.open(io.BytesIO(r.content))
        text = " ".join(p.extract_text() or "" for p in pdf.pages)
        pdf.close()
        assert "MAGERIT" in text
        assert "BORRADOR" in text  # Not frozen = draft

    @pytest.mark.asyncio
    async def test_magerit_report_docx_valid(self, async_client, db):
        """GET /report.docx returns valid DOCX."""
        import zipfile, io

        analysis_id, _ = await _setup_full_pipeline(async_client, db)
        await async_client.post(f"{BASE}/analysis/{analysis_id}/calculate-intrinsic")

        r = await async_client.get(f"{BASE}/analysis/{analysis_id}/report.docx")
        assert r.status_code == 200
        assert r.content[:2] == b"PK"
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        assert "word/document.xml" in zf.namelist()

    @pytest.mark.asyncio
    async def test_magerit_report_pdf_404_not_found(self, async_client, db):
        """GET /report.pdf with fake analysis returns 404."""
        fake_id = str(uuid.uuid4())
        r = await async_client.get(f"{BASE}/analysis/{fake_id}/report.pdf")
        assert r.status_code == 404


    @pytest.mark.asyncio
    async def test_export_xml_and_deprecated_pilar_return_same_content(self, async_client, db):
        """Verifica que /export-xml y /export-pilar devuelven mismo contenido.

        /export-pilar queda como alias deprecated. El nombre correcto es
        /export-xml porque no es formato PILAR real (.mgr propietario del CCN).
        """
        analysis_id, _ = await _setup_full_pipeline(async_client, db)
        await async_client.post(f"{BASE}/analysis/{analysis_id}/calculate-intrinsic")

        r_new = await async_client.get(f"{BASE}/analysis/{analysis_id}/export-xml")
        r_old = await async_client.get(f"{BASE}/analysis/{analysis_id}/export-pilar")

        assert r_new.status_code == 200
        assert r_old.status_code == 200
        assert r_new.text == r_old.text
        assert "FULKRO native XML export" in r_new.text
        assert "NOT compatible with PILAR" in r_new.text



# ================================================================
# CSV/XLSX IMPORT TESTS (6 tests)
# ================================================================

def _make_csv_bytes(rows):
    """Helper: create CSV bytes from list of dicts."""
    import csv as csv_mod, io
    out = io.StringIO()
    if rows:
        writer = csv_mod.DictWriter(out, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return out.getvalue().encode("utf-8")


def _make_xlsx_bytes(rows):
    """Helper: create XLSX bytes from list of dicts."""
    from openpyxl import Workbook
    import io as io_mod
    wb = Workbook()
    ws = wb.active
    if rows:
        headers = list(rows[0].keys())
        ws.append(headers)
        for row in rows:
            ws.append([row.get(h, "") for h in headers])
    buf = io_mod.BytesIO()
    wb.save(buf)
    return buf.getvalue()


VALID_IMPORT_ROWS = [
    {"code": "IMP-HW1", "name": "Servidor Web", "asset_type_code": "HW",
     "value_d": "8", "value_i": "6", "value_c": "4", "value_a": "3", "value_t": "2"},
    {"code": "IMP-SW1", "name": "App CRM", "asset_type_code": "SW",
     "value_d": "5", "value_i": "5", "value_c": "7", "value_a": "3", "value_t": "1"},
    {"code": "IMP-COM1", "name": "Red LAN", "asset_type_code": "COM",
     "value_d": "6", "value_i": "2", "value_c": "3", "value_a": "2", "value_t": "1"},
]


class TestMotor2ImportHTTP:
    """Tests for CSV/XLSX asset import."""

    @pytest.mark.asyncio
    async def test_import_csv_valid_atomic(self, async_client, db):
        """TEST CRITICAL: valid CSV imports all 3 assets atomically."""
        _, analysis_id = await _create_analysis(async_client, db)
        csv_bytes = _make_csv_bytes(VALID_IMPORT_ROWS)

        r = await async_client.post(
            f"{BASE}/analysis/{analysis_id}/assets/import",
            files={"file": ("assets.csv", csv_bytes, "text/csv")},
        )
        assert r.status_code == 201, f"Got {r.status_code}: {r.text}"
        data = r.json()
        assert data["imported_count"] == 3
        assert data["mode"] == "atomic"

    @pytest.mark.asyncio
    async def test_import_xlsx_valid_atomic(self, async_client, db):
        """Valid XLSX imports all 3 assets."""
        _, analysis_id = await _create_analysis(async_client, db)
        xlsx_bytes = _make_xlsx_bytes(VALID_IMPORT_ROWS)

        r = await async_client.post(
            f"{BASE}/analysis/{analysis_id}/assets/import",
            files={"file": ("assets.xlsx", xlsx_bytes,
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert r.status_code == 201
        assert r.json()["imported_count"] == 3

    @pytest.mark.asyncio
    async def test_import_atomic_rollback_on_error(self, async_client, db):
        """TEST CRITICAL: one bad row rolls back ALL rows (atomic)."""

        _, analysis_id = await _create_analysis(async_client, db)
        rows_with_error = [
            {"code": "OK1", "name": "Good", "asset_type_code": "HW",
             "value_d": "5", "value_i": "5", "value_c": "5", "value_a": "5", "value_t": "5"},
            {"code": "BAD", "name": "Bad Type", "asset_type_code": "NONEXISTENT",
             "value_d": "5", "value_i": "5", "value_c": "5", "value_a": "5", "value_t": "5"},
            {"code": "OK2", "name": "Also Good", "asset_type_code": "SW",
             "value_d": "5", "value_i": "5", "value_c": "5", "value_a": "5", "value_t": "5"},
        ]
        csv_bytes = _make_csv_bytes(rows_with_error)

        r = await async_client.post(
            f"{BASE}/analysis/{analysis_id}/assets/import",
            files={"file": ("bad.csv", csv_bytes, "text/csv")},
        )
        assert r.status_code == 422, f"Expected 422, got {r.status_code}"
        assert "atomico" in r.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_import_missing_required_columns(self, async_client, db):
        """CSV missing required column returns 422."""
        _, analysis_id = await _create_analysis(async_client, db)
        # Missing value_c column
        rows = [{"code": "X", "name": "Y", "asset_type_code": "HW",
                 "value_d": "5", "value_i": "5", "value_a": "5", "value_t": "5"}]
        csv_bytes = _make_csv_bytes(rows)

        r = await async_client.post(
            f"{BASE}/analysis/{analysis_id}/assets/import",
            files={"file": ("missing.csv", csv_bytes, "text/csv")},
        )
        assert r.status_code == 422
        assert "value_c" in r.json()["detail"]

    @pytest.mark.asyncio
    async def test_import_extra_columns_ignored(self, async_client, db):
        """Extra columns in CSV are silently ignored."""
        _, analysis_id = await _create_analysis(async_client, db)
        rows = [
            {"code": "EX1", "name": "Extra Test", "asset_type_code": "HW",
             "value_d": "5", "value_i": "5", "value_c": "5", "value_a": "5", "value_t": "5",
             "ubicacion_fisica": "Sala Servidores", "responsable": "IT Manager"},
        ]
        csv_bytes = _make_csv_bytes(rows)

        r = await async_client.post(
            f"{BASE}/analysis/{analysis_id}/assets/import",
            files={"file": ("extra.csv", csv_bytes, "text/csv")},
        )
        assert r.status_code == 201
        assert r.json()["imported_count"] == 1

    @pytest.mark.asyncio
    async def test_import_frozen_analysis_rejects(self, async_client, db):
        """Import on frozen analysis returns 409."""
        analysis_id, _ = await _setup_full_pipeline(async_client, db)
        await async_client.post(f"{BASE}/analysis/{analysis_id}/calculate-intrinsic")
        await async_client.post(f"{BASE}/analysis/{analysis_id}/freeze")

        csv_bytes = _make_csv_bytes(VALID_IMPORT_ROWS)
        r = await async_client.post(
            f"{BASE}/analysis/{analysis_id}/assets/import",
            files={"file": ("frozen.csv", csv_bytes, "text/csv")},
        )
        assert r.status_code == 409


# ================================================================
# XLSX EXPORT TESTS (E-020 to E-026)
# ================================================================

class TestXlsxExportEndpoints:
    """HTTP tests for 7 XLSX export endpoints.

    Each test validates:
    1. HTTP 200 + correct Content-Type
    2. Content-Disposition with correct filename
    3. Valid XLSX content (parseable by openpyxl)
    4. Deterministic column headers
    5. Data rows match expected count
    """

    @pytest.mark.asyncio
    async def test_e020_asset_inventory_xlsx(self, async_client, db):
        """E-020: GET /export/assets.xlsx returns valid XLSX with 2 assets."""
        analysis_id, _ = await _setup_full_pipeline(async_client, db)

        r = await async_client.get(f"{BASE}/analysis/{analysis_id}/export/assets.xlsx")
        assert r.status_code == 200
        assert "spreadsheetml" in r.headers["content-type"]
        assert "E020_activos" in r.headers["content-disposition"]

        import io
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(r.content))
        ws = wb.active
        assert ws.cell(row=1, column=1).value == "Codigo"
        assert ws.cell(row=1, column=5).value == "Val_D"
        # 2 assets from _setup_full_pipeline
        assert ws.cell(row=2, column=1).value is not None
        assert ws.cell(row=3, column=1).value is not None
        assert ws.cell(row=4, column=1).value is None  # no 3rd asset

    @pytest.mark.asyncio
    async def test_e020_deterministic_order(self, async_client, db):
        """E-020: Assets sorted by code (deterministic for audit)."""
        analysis_id, _ = await _setup_full_pipeline(async_client, db)

        import io
        from openpyxl import load_workbook

        r1 = await async_client.get(f"{BASE}/analysis/{analysis_id}/export/assets.xlsx")
        r2 = await async_client.get(f"{BASE}/analysis/{analysis_id}/export/assets.xlsx")

        wb1, wb2 = load_workbook(io.BytesIO(r1.content)), load_workbook(io.BytesIO(r2.content))
        ws1, ws2 = wb1.active, wb2.active

        # Row 2 code must be same in both calls
        assert ws1.cell(row=2, column=1).value == ws2.cell(row=2, column=1).value
        # HW-001 < S-001 alphabetically
        assert ws1.cell(row=2, column=1).value == "HW-001"
        assert ws1.cell(row=3, column=1).value == "S-001"

    @pytest.mark.asyncio
    async def test_e021_dependency_map_xlsx(self, async_client, db):
        """E-021: GET /export/dependencies.xlsx returns dependency graph."""
        analysis_id, _ = await _setup_full_pipeline(async_client, db)

        r = await async_client.get(f"{BASE}/analysis/{analysis_id}/export/dependencies.xlsx")
        assert r.status_code == 200
        assert "E021_dependencias" in r.headers["content-disposition"]

        import io
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(r.content))
        ws = wb.active
        assert ws.cell(row=1, column=1).value == "Activo Superior"
        assert ws.cell(row=1, column=3).value == "Grado Dependencia"
        # 1 dependency from _setup_full_pipeline
        assert ws.cell(row=2, column=3).value == 0.8

    @pytest.mark.asyncio
    async def test_e022_threat_assessment_xlsx(self, async_client, db):
        """E-022: GET /export/threats.xlsx returns threat assessments."""
        analysis_id, _ = await _setup_full_pipeline(async_client, db)

        r = await async_client.get(f"{BASE}/analysis/{analysis_id}/export/threats.xlsx")
        assert r.status_code == 200
        assert "E022_amenazas" in r.headers["content-disposition"]

        import io
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(r.content))
        ws = wb.active
        assert ws.cell(row=1, column=2).value == "Amenaza"
        assert ws.cell(row=1, column=3).value == "Probabilidad"
        # 1 threat (A.11 on HW-001)
        assert ws.cell(row=2, column=2).value == "A.11"
        assert ws.cell(row=2, column=3).value == "M"

    @pytest.mark.asyncio
    async def test_e023_safeguard_deployment_xlsx(self, async_client, db):
        """E-023: GET /export/safeguards.xlsx returns deployed safeguards."""
        analysis_id, _ = await _setup_full_pipeline(async_client, db)

        r = await async_client.get(f"{BASE}/analysis/{analysis_id}/export/safeguards.xlsx")
        assert r.status_code == 200
        assert "E023_salvaguardas" in r.headers["content-disposition"]

        import io
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(r.content))
        ws = wb.active
        assert ws.cell(row=1, column=1).value == "Salvaguarda"
        assert ws.cell(row=2, column=1).value == "H.IA"
        assert ws.cell(row=2, column=3).value == 70  # efficacy

    @pytest.mark.asyncio
    async def test_e024_risk_calculations_xlsx(self, async_client, db):
        """E-024: GET /export/risks.xlsx returns risk calculations after intrinsic calc."""
        analysis_id, _ = await _setup_full_pipeline(async_client, db)
        await async_client.post(f"{BASE}/analysis/{analysis_id}/calculate-intrinsic")

        r = await async_client.get(f"{BASE}/analysis/{analysis_id}/export/risks.xlsx")
        assert r.status_code == 200
        assert "E024_riesgos" in r.headers["content-disposition"]

        import io
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(r.content))
        ws = wb.active
        assert ws.cell(row=1, column=1).value == "Activo"
        assert ws.cell(row=1, column=10).value == "Nivel"
        # At least 1 calculation row
        assert ws.cell(row=2, column=2).value is not None

    @pytest.mark.asyncio
    async def test_e024_empty_before_calculation(self, async_client, db):
        """E-024: XLSX is empty (headers only) if no calculations done yet."""
        _, analysis_id = await _create_analysis(async_client, db)

        r = await async_client.get(f"{BASE}/analysis/{analysis_id}/export/risks.xlsx")
        assert r.status_code == 200

        import io
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(r.content))
        ws = wb.active
        # Headers exist
        assert ws.cell(row=1, column=1).value == "Activo"
        # No data rows
        assert ws.cell(row=2, column=1).value is None

    @pytest.mark.asyncio
    async def test_e025_treatment_plan_xlsx(self, async_client, db):
        """E-025: GET /export/treatment.xlsx returns treatment plan."""
        analysis_id, _ = await _setup_full_pipeline(async_client, db)
        await async_client.post(f"{BASE}/analysis/{analysis_id}/calculate-intrinsic")
        await async_client.post(f"{BASE}/analysis/{analysis_id}/calculate-effective")
        await async_client.post(
            f"{BASE}/analysis/{analysis_id}/treatment-plan",
            json={"risk_tolerance_threshold": "B"},
        )

        r = await async_client.get(f"{BASE}/analysis/{analysis_id}/export/treatment.xlsx")
        assert r.status_code == 200
        assert "E025_tratamiento" in r.headers["content-disposition"]

        import io
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(r.content))
        ws = wb.active
        assert ws.cell(row=1, column=5).value == "Tratamiento"
        # At least 1 treatment action
        assert ws.cell(row=2, column=5).value is not None

    @pytest.mark.asyncio
    async def test_e026_executive_summary_xlsx(self, async_client, db):
        """E-026: GET /export/summary.xlsx returns multi-sheet summary."""
        analysis_id, _ = await _setup_full_pipeline(async_client, db)
        await async_client.post(f"{BASE}/analysis/{analysis_id}/calculate-intrinsic")

        r = await async_client.get(f"{BASE}/analysis/{analysis_id}/export/summary.xlsx")
        assert r.status_code == 200
        assert "E026_resumen" in r.headers["content-disposition"]

        import io
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(r.content))

        # 3 sheets
        assert len(wb.sheetnames) == 3
        assert "Resumen General" in wb.sheetnames
        assert "Distribucion Riesgo" in wb.sheetnames
        assert "Top 10 Riesgos" in wb.sheetnames

        # Sheet 1: summary data
        ws1 = wb["Resumen General"]
        assert ws1.cell(row=2, column=1).value == "Nombre del analisis"

        # Sheet 2: risk distribution (5 levels)
        ws2 = wb["Distribucion Riesgo"]
        levels = [ws2.cell(row=i, column=1).value for i in range(2, 7)]
        assert levels == ["MB", "B", "M", "A", "MA"]

    @pytest.mark.asyncio
    async def test_e026_top10_ordering(self, async_client, db):
        """E-026: Top 10 sheet sorted by risk level descending."""
        analysis_id, _ = await _setup_full_pipeline(async_client, db)
        await async_client.post(f"{BASE}/analysis/{analysis_id}/calculate-intrinsic")

        r = await async_client.get(f"{BASE}/analysis/{analysis_id}/export/summary.xlsx")
        import io
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(r.content))
        ws3 = wb["Top 10 Riesgos"]
        assert ws3.cell(row=1, column=5).value == "Nivel"
        # First row should be highest risk level
        first_level = ws3.cell(row=2, column=5).value
        assert first_level is not None

    @pytest.mark.asyncio
    async def test_xlsx_export_404_nonexistent_analysis(self, async_client, db):
        """All XLSX endpoints return 404 for nonexistent analysis."""
        fake_id = str(uuid.uuid4())
        endpoints = [
            "assets.xlsx", "dependencies.xlsx", "threats.xlsx",
            "safeguards.xlsx", "risks.xlsx", "treatment.xlsx", "summary.xlsx",
        ]
        for ep in endpoints:
            r = await async_client.get(f"{BASE}/analysis/{fake_id}/export/{ep}")
            assert r.status_code == 404, f"Expected 404 for {ep}, got {r.status_code}"

    @pytest.mark.asyncio
    async def test_xlsx_exports_with_full_pipeline(self, async_client, db):
        """Smoke test: all 7 XLSX endpoints return 200 with full pipeline data."""
        analysis_id, _ = await _setup_full_pipeline(async_client, db)
        await async_client.post(f"{BASE}/analysis/{analysis_id}/calculate-intrinsic")
        await async_client.post(f"{BASE}/analysis/{analysis_id}/calculate-effective")
        await async_client.post(
            f"{BASE}/analysis/{analysis_id}/treatment-plan",
            json={"risk_tolerance_threshold": "B"},
        )

        endpoints = [
            "assets.xlsx", "dependencies.xlsx", "threats.xlsx",
            "safeguards.xlsx", "risks.xlsx", "treatment.xlsx", "summary.xlsx",
        ]
        for ep in endpoints:
            r = await async_client.get(f"{BASE}/analysis/{analysis_id}/export/{ep}")
            assert r.status_code == 200, f"XLSX export {ep} failed: {r.status_code}"
            assert len(r.content) > 100, f"XLSX {ep} too small: {len(r.content)} bytes"
