"""
Tests for RLS multi-tenant isolation.

These tests verify that PostgreSQL Row Level Security policies correctly
isolate data between tenants when the app uses fulkro_app (NOSUPERUSER).

Each test creates 2 clients (A and B) with their own data, then verifies
that setting tenant context to client A hides client B data, and vice versa.

CRITICAL: These tests are REAL isolation tests, not false positives.
They run as fulkro_app (NOSUPERUSER) where RLS is enforced. The setup
uses _admin_setup() (SET LOCAL ROLE fulkro_app_bypassrls superuser) to insert baseline
data, then RESET ROLE to fulkro_app before making assertions.
"""
import uuid
import pytest
from sqlalchemy import text

from backend.app.database import set_tenant_context
from backend.tests.conftest import _admin_setup


# ================================================================
# HELPERS
# ================================================================

async def _create_two_tenants(db):
    """Create 2 complete tenant structures (client + project + system).

    Returns dict with all IDs for both tenants.
    """
    data = {}
    async with _admin_setup(db):
        for label in ("a", "b"):
            cid = uuid.uuid4()
            pid = uuid.uuid4()
            sid = uuid.uuid4()
            cif = f"RLS{uuid.uuid4().hex[:6].upper()}"

            await db.execute(text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, :name, :cif, now())"
            ), {"id": str(cid), "name": f"Client {label.upper()}", "cif": cif})

            await db.execute(text(
                "INSERT INTO projects (id, client_id, nombre, created_at) "
                "VALUES (:id, :cid, :name, now())"
            ), {"id": str(pid), "cid": str(cid), "name": f"Project {label.upper()}"})

            await db.execute(text(
                "INSERT INTO systems (id, project_id, nombre, created_at) "
                "VALUES (:id, :pid, :name, now())"
            ), {"id": str(sid), "pid": str(pid), "name": f"System {label.upper()}"})

            data[f"client_{label}"] = str(cid)
            data[f"project_{label}"] = str(pid)
            data[f"system_{label}"] = str(sid)

    await db.flush()
    return data


# ================================================================
# 5 RLS ISOLATION TESTS
# ================================================================

class TestRLSIsolation:
    """Real RLS isolation tests with fulkro_app NOSUPERUSER."""

    @pytest.mark.asyncio
    async def test_client_a_cannot_see_systems_of_client_b(self, db):
        """Client A with tenant context sees only their own systems.

        Table systems has policy project_isolation:
        USING (project_id = current_project_id()).
        """
        data = await _create_two_tenants(db)

        # Set tenant context to Client A
        await set_tenant_context(
            db,
            client_id=uuid.UUID(data["client_a"]),
            project_id=uuid.UUID(data["project_a"]),
        )

        rows = (await db.execute(text("SELECT id, nombre FROM systems"))).fetchall()
        visible_ids = {str(r[0]) for r in rows}

        assert data["system_a"] in visible_ids, (
            "Client A must see their own system"
        )
        assert data["system_b"] not in visible_ids, (
            f"RLS FAILURE: Client A sees Client B system. Visible: {visible_ids}"
        )

    @pytest.mark.asyncio
    async def test_client_b_cannot_see_systems_of_client_a(self, db):
        """Symmetric test: Client B sees only their own systems."""
        data = await _create_two_tenants(db)

        await set_tenant_context(
            db,
            client_id=uuid.UUID(data["client_b"]),
            project_id=uuid.UUID(data["project_b"]),
        )

        rows = (await db.execute(text("SELECT id FROM systems"))).fetchall()
        visible_ids = {str(r[0]) for r in rows}

        assert data["system_b"] in visible_ids
        assert data["system_a"] not in visible_ids, (
            f"RLS FAILURE: Client B sees Client A system. Visible: {visible_ids}"
        )

    @pytest.mark.asyncio
    async def test_client_a_cannot_see_projects_of_client_b(self, db):
        """Projects table has policy client_isolation:
        USING (client_id = current_client_id()).
        """
        data = await _create_two_tenants(db)

        await set_tenant_context(
            db, client_id=uuid.UUID(data["client_a"])
        )

        rows = (await db.execute(text("SELECT id FROM projects"))).fetchall()
        visible_ids = {str(r[0]) for r in rows}

        assert data["project_a"] in visible_ids
        assert data["project_b"] not in visible_ids, (
            f"RLS FAILURE: Client A sees Client B project. Visible: {visible_ids}"
        )

    @pytest.mark.asyncio
    async def test_client_a_cannot_modify_system_of_client_b(self, db):
        """UPDATE on Client B system from Client A context affects 0 rows."""
        data = await _create_two_tenants(db)

        await set_tenant_context(
            db,
            client_id=uuid.UUID(data["client_a"]),
            project_id=uuid.UUID(data["project_a"]),
        )

        result = await db.execute(text(
            "UPDATE systems SET nombre = 'HACKED' WHERE id = :sid"
        ), {"sid": data["system_b"]})

        assert result.rowcount == 0, (
            f"RLS FAILURE: Client A modified Client B system. "
            f"Rows affected: {result.rowcount}"
        )

    @pytest.mark.asyncio
    async def test_no_tenant_context_returns_empty(self, db):
        """Without set_tenant_context, SELECT returns 0 rows (RLS deny all).

        This verifies the default-deny behavior: if the app forgets to set
        tenant context, no data is leaked.
        """
        data = await _create_two_tenants(db)

        # Do NOT call set_tenant_context — default should be deny-all
        rows = (await db.execute(text("SELECT id FROM systems"))).fetchall()
        assert len(rows) == 0, (
            f"RLS FAILURE: Without tenant context, {len(rows)} systems visible. "
            f"Expected 0 (default deny)."
        )

        rows_proj = (await db.execute(text("SELECT id FROM projects"))).fetchall()
        assert len(rows_proj) == 0, (
            f"RLS FAILURE: Without tenant context, {len(rows_proj)} projects visible."
        )


# ================================================================
# SUB-ATOM 5.B · MAGERIT CHILD TABLES RLS ISOLATION TESTS
# ================================================================
# 6 child tables magerit + EXISTS pattern 1-level via parent
# magerit_analysis.project_id = current_project_id().
# Migration: sub_atom_5b_magerit_child_rls_001
# ================================================================


async def _create_two_tenants_with_magerit(db):
    """Extends _create_two_tenants with magerit analysis + asset +
    treatment_plan per tenant (Sub-atom 5.B test scaffold).

    Returns dict with all base IDs + magerit_analysis_{a,b} +
    magerit_asset_{a,b} + magerit_treatment_plan_{a,b}.
    """
    data = await _create_two_tenants(db)

    async with _admin_setup(db):
        for label in ("a", "b"):
            analysis_id = uuid.uuid4()
            asset_id = uuid.uuid4()
            plan_id = uuid.uuid4()

            await db.execute(text(
                "INSERT INTO magerit_analysis "
                "(id, project_id, name, version, status, calculation_mode, "
                " methodology_version, created_at, updated_at) "
                "VALUES (:id, :pid, :name, 1, 'draft', 'qualitative', "
                "        'MAGERIT v3', now(), now())"
            ), {
                "id": str(analysis_id),
                "pid": data[f"project_{label}"],
                "name": f"Analysis {label.upper()}",
            })

            await db.execute(text(
                "INSERT INTO magerit_assets "
                "(id, analysis_id, code, name, asset_type_code, "
                " created_at, updated_at) "
                "VALUES (:id, :aid, :code, :name, 'S', now(), now())"
            ), {
                "id": str(asset_id),
                "aid": str(analysis_id),
                "code": f"AST-{label.upper()}-001",
                "name": f"Asset {label.upper()}",
            })

            await db.execute(text(
                "INSERT INTO magerit_treatment_plan "
                "(id, analysis_id, asset_id, threat_code, dimension, "
                " current_risk_level, treatment, status, created_at, updated_at) "
                "VALUES (:id, :aid, :asset_id, 'E.1', 'C', "
                "        'A', 'mitigar', 'pending', now(), now())"
            ), {
                "id": str(plan_id),
                "aid": str(analysis_id),
                "asset_id": str(asset_id),
            })

            data[f"magerit_analysis_{label}"] = str(analysis_id)
            data[f"magerit_asset_{label}"] = str(asset_id)
            data[f"magerit_treatment_plan_{label}"] = str(plan_id)

    await db.flush()
    return data


class TestSubAtom5BMageritChildRLSIsolation:
    """Sub-atom 5.B · 6 child tables magerit RLS isolation via EXISTS 1-level
    subquery contra magerit_analysis.project_id = current_project_id().

    Verifies: setting tenant context = client A hides ALL magerit child rows
    belonging to client B's magerit_analysis (via FK analysis_id chain).
    """

    @pytest.mark.asyncio
    async def test_client_a_cannot_see_magerit_assets_of_client_b(self, db):
        """RLS policy project_isolation on magerit_assets blocks cross-client
        visibility via EXISTS subquery (analysis_id → magerit_analysis.project_id).
        """
        data = await _create_two_tenants_with_magerit(db)

        await set_tenant_context(
            db,
            client_id=uuid.UUID(data["client_a"]),
            project_id=uuid.UUID(data["project_a"]),
        )

        rows = (await db.execute(text("SELECT id FROM magerit_assets"))).fetchall()
        visible_ids = {str(r[0]) for r in rows}

        assert data["magerit_asset_a"] in visible_ids, (
            "Client A must see their own magerit_assets"
        )
        assert data["magerit_asset_b"] not in visible_ids, (
            f"RLS FAILURE Sub-atom 5.B: Client A sees Client B magerit_assets. "
            f"Visible: {visible_ids}"
        )

    @pytest.mark.asyncio
    async def test_magerit_treatment_plan_isolation_via_analysis_id(self, db):
        """RLS isolation on magerit_treatment_plan via EXISTS subquery
        through analysis_id → magerit_analysis.project_id."""
        data = await _create_two_tenants_with_magerit(db)

        await set_tenant_context(
            db,
            client_id=uuid.UUID(data["client_a"]),
            project_id=uuid.UUID(data["project_a"]),
        )

        rows = (await db.execute(
            text("SELECT id FROM magerit_treatment_plan")
        )).fetchall()
        visible_ids = {str(r[0]) for r in rows}

        assert data["magerit_treatment_plan_a"] in visible_ids, (
            "Client A must see their own magerit_treatment_plan"
        )
        assert data["magerit_treatment_plan_b"] not in visible_ids, (
            f"RLS FAILURE Sub-atom 5.B: Client A sees Client B "
            f"magerit_treatment_plan. Visible: {visible_ids}"
        )

    @pytest.mark.asyncio
    async def test_no_tenant_context_returns_empty_magerit_assets(self, db):
        """Default-deny on magerit_assets without tenant context (RLS guard)."""
        await _create_two_tenants_with_magerit(db)

        # Do NOT call set_tenant_context
        rows = (await db.execute(text("SELECT id FROM magerit_assets"))).fetchall()
        assert len(rows) == 0, (
            f"RLS FAILURE Sub-atom 5.B: Without tenant context, "
            f"{len(rows)} magerit_assets visible. Expected 0."
        )

        rows_plan = (await db.execute(
            text("SELECT id FROM magerit_treatment_plan")
        )).fetchall()
        assert len(rows_plan) == 0, (
            f"RLS FAILURE Sub-atom 5.B: Without tenant context, "
            f"{len(rows_plan)} magerit_treatment_plan visible. Expected 0."
        )
