"""Tests de PKG tools para M11 Copiloto."""
import uuid

import pytest

from backend.app.motors.m16_onboarding import pkg_service as pkg
from backend.app.motors.m16_onboarding.pkg_tools_registry import call_tool, get_tool, list_tools
from backend.tests.conftest import setup_test_project


async def _seed_project_with_pkg(db):
    _, project_id = await setup_test_project(db)
    pid = uuid.UUID(project_id)

    await pkg.add_node(db, pid, "person", "Sponsor", properties={"role": "sponsor"})
    await pkg.add_node(db, pid, "system", "ERP", properties={"ens_category": "MEDIA"})
    server = await pkg.add_node(db, pid, "asset", "Production Server", properties={"asset_subtype": "server"})
    await pkg.add_node(db, pid, "asset", "Main Repo", properties={"asset_subtype": "repository"})
    await pkg.add_node(db, pid, "identity", "User 1", properties={"identity_type": "user", "mfa_enabled": True})
    await pkg.add_node(db, pid, "identity", "User 2", properties={"identity_type": "user", "mfa_enabled": False})
    await pkg.add_node(db, pid, "provider", "AWS")
    await pkg.add_node(db, pid, "process", "Facturacion")

    # Get node IDs for edges
    erp_nodes = await pkg.get_nodes_by_type(db, pid, "system")
    person_nodes = await pkg.get_nodes_by_type(db, pid, "person")
    asset_nodes = await pkg.get_nodes_by_type(db, pid, "asset")
    erp_id = erp_nodes[0]["id"]
    sponsor_id = person_nodes[0]["id"]
    server_id = next(a["id"] for a in asset_nodes if a["label"] == "Production Server")

    await pkg.add_edge(db, pid, sponsor_id, erp_id, "owns")
    await pkg.add_edge(db, pid, erp_id, server_id, "depends_on")
    await db.flush()

    return pid, project_id


class TestToolsRegistry:
    def test_list_tools_returns_10(self):
        tools = list_tools()
        assert len(tools) >= 10
        for t in tools:
            assert "name" in t
            assert "description" in t
            assert "input_schema" in t

    def test_get_tool_known(self):
        t = get_tool("pkg_project_summary")
        assert t is not None
        assert "function" in t

    def test_get_tool_unknown(self):
        assert get_tool("fake_tool") is None


class TestToolFunctions:

    @pytest.mark.asyncio
    async def test_project_summary(self, db):
        pid, _ = await _seed_project_with_pkg(db)
        result = await call_tool("pkg_project_summary", {"project_id": str(pid)}, db)
        assert result["total_nodes"] == 8
        assert result["total_edges"] == 2

    @pytest.mark.asyncio
    async def test_count_assets_by_type(self, db):
        pid, _ = await _seed_project_with_pkg(db)
        result = await call_tool("pkg_count_assets_by_type", {"project_id": str(pid)}, db)
        assert result["total_assets"] == 2
        assert "server" in result["by_subtype"]
        assert "repository" in result["by_subtype"]

    @pytest.mark.asyncio
    async def test_mfa_coverage(self, db):
        pid, _ = await _seed_project_with_pkg(db)
        result = await call_tool("pkg_get_mfa_coverage", {"project_id": str(pid)}, db)
        assert result["total_users"] == 2
        assert result["mfa_enabled"] == 1
        assert result["mfa_disabled"] == 1
        assert result["coverage_percentage"] == 50.0
        assert result["ens_compliant"] is False

    @pytest.mark.asyncio
    async def test_list_systems(self, db):
        pid, _ = await _seed_project_with_pkg(db)
        result = await call_tool("pkg_list_systems", {"project_id": str(pid)}, db)
        assert result["total_systems"] == 1
        assert result["systems"][0]["label"] == "ERP"

    @pytest.mark.asyncio
    async def test_stakeholder_roles(self, db):
        pid, _ = await _seed_project_with_pkg(db)
        result = await call_tool("pkg_get_stakeholder_roles", {"project_id": str(pid)}, db)
        assert result["ens_roles"]["sponsor"] is True
        assert result["ens_roles"]["rseg"] is False
        assert "rseg" in result["roles_missing"]

    @pytest.mark.asyncio
    async def test_critical_dependencies(self, db):
        pid, _ = await _seed_project_with_pkg(db)
        result = await call_tool("pkg_get_critical_dependencies", {"project_id": str(pid)}, db)
        assert result["total_dependencies"] == 1
        assert result["dependencies"][0]["source"] == "ERP"

    @pytest.mark.asyncio
    async def test_count_processes(self, db):
        pid, _ = await _seed_project_with_pkg(db)
        result = await call_tool("pkg_count_processes", {"project_id": str(pid)}, db)
        assert result["total_processes"] == 1
        assert "Facturacion" in result["processes"]

    @pytest.mark.asyncio
    async def test_unknown_tool_raises(self, db):
        with pytest.raises(ValueError, match="no existe"):
            await call_tool("fake_tool", {"project_id": str(uuid.uuid4())}, db)


class TestToolsAPI:

    @pytest.mark.asyncio
    async def test_list_tools_endpoint(self, async_client):
        r = await async_client.get("/api/v1/onboarding/tools")
        assert r.status_code == 200
        assert r.json()["total"] >= 10

    @pytest.mark.asyncio
    async def test_call_tool_endpoint(self, async_client, db):
        _, project_id = await _seed_project_with_pkg(db)
        r = await async_client.post(f"/api/v1/onboarding/projects/{project_id}/tools/pkg_project_summary")
        assert r.status_code == 200
        assert "total_nodes" in r.json()

    @pytest.mark.asyncio
    async def test_call_unknown_tool_404(self, async_client, db):
        _, project_id = await setup_test_project(db)
        r = await async_client.post(f"/api/v1/onboarding/projects/{project_id}/tools/fake_tool")
        assert r.status_code == 404
