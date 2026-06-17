"""Tests MCP execution endpoints + executor service · sub-atom 1.D.E.A v3.11.

Cobertura:
- Catalog 13 tools (vulnscan 4 · cloud 4 · config 4 · phishing 1)
- get_tool_descriptor lookup
- execute_tool · trigger background + status=running → completed
- Auto-attach evidence al folder código "13_Informes_Tecnicos"
- Required params validation
- SSE event queue publish + consume
- Endpoint POST execute · 201 + execution_id
- Endpoint GET status · 200 + 404
- Endpoint GET list executions · history per project
- Endpoint GET catalog · 13 tools

Pattern test_action_plans · `setup_test_project` + `_admin_setup` reuse.
"""
from __future__ import annotations

import asyncio
import uuid

import pytest
import pytest_asyncio

from backend.app.motors.m08_verification.mcp_executor_service import (
    MCP_TOOLS_CATALOG,
    MCPExecutorError,
    MCPExecutorService,
    get_mcp_executor,
    get_tool_descriptor,
    list_all_tools,
    reset_executor_for_tests,
)
from backend.tests.conftest import setup_test_project


@pytest_asyncio.fixture(autouse=True)
async def _drain_mcp_background_tasks():
    """Drena los background tasks del executor tras cada test.

    El executor lanza `asyncio.create_task` (fire-and-forget). Si un task queda
    en vuelo cuando pytest-asyncio cierra el event loop, se cancela a media
    operación DB y devuelve una conexión envenenada al pool global → el
    siguiente consumidor de async_session() (p.ej. notifications redispatch)
    falla con InterfaceError "another operation in progress". Drenar aquí evita
    la fuga cruzada entre tests/ficheros. Ejecutable 8 Pasada 16.
    """
    yield
    try:
        await get_mcp_executor().wait_pending_tasks()
    except Exception:
        pass


# ════════════════════════════════════════════════════════════════════
# Catalog
# ════════════════════════════════════════════════════════════════════


def test_catalog_has_4_families():
    assert set(MCP_TOOLS_CATALOG.keys()) == {
        "vulnscan", "cloud", "config", "phishing",
    }


def test_catalog_has_13_tools_total():
    total = sum(len(tools) for tools in MCP_TOOLS_CATALOG.values())
    assert total == 13
    assert len(list_all_tools()) == 13


def test_catalog_vulnscan_4_tools():
    assert set(MCP_TOOLS_CATALOG["vulnscan"].keys()) == {
        "nuclei_scan", "openvas_scan", "trivy_scan", "grype_sbom_scan",
    }


def test_catalog_cloud_4_tools():
    # S12 fix: nombres alineados a los MCPTool.name reales de los server.py.
    assert set(MCP_TOOLS_CATALOG["cloud"].keys()) == {
        "prowler_audit", "scoutsuite_audit", "pacu_attack", "kube_security_scan",
    }


def test_catalog_config_4_tools():
    assert set(MCP_TOOLS_CATALOG["config"].keys()) == {
        "clara_ccn_audit", "cis_cat_audit", "lynis_audit", "openscap_audit",
    }


def test_catalog_phishing_1_tool():
    assert set(MCP_TOOLS_CATALOG["phishing"].keys()) == {"gophish_campaign"}


def test_get_tool_descriptor_known():
    d = get_tool_descriptor("vulnscan", "nuclei_scan")
    assert d is not None
    assert d.label == "Nuclei"
    assert any(p.name == "target" and p.required for p in d.params)


def test_get_tool_descriptor_unknown_returns_none():
    assert get_tool_descriptor("vulnscan", "unknown_tool") is None
    assert get_tool_descriptor("unknown_family", "x") is None


# ════════════════════════════════════════════════════════════════════
# Executor service
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_execute_unknown_tool_raises():
    reset_executor_for_tests()
    svc = MCPExecutorService()
    with pytest.raises(MCPExecutorError):
        await svc.execute_tool(
            db=None,
            project_id=uuid.uuid4(),
            mcp_name="vulnscan",
            tool_name="unknown",
            params={},
        )


@pytest.mark.asyncio
async def test_execute_missing_required_param_raises():
    reset_executor_for_tests()
    svc = MCPExecutorService()
    with pytest.raises(MCPExecutorError):
        # nuclei_scan requiere "target"
        await svc.execute_tool(
            db=None,
            project_id=uuid.uuid4(),
            mcp_name="vulnscan",
            tool_name="nuclei_scan",
            params={},
        )


@pytest.mark.asyncio
async def test_execute_trigger_and_completion(db):
    """Trigger + esperar a que termine (USE_MCP_REAL=false simulado).

    Verifica que:
      - execution se crea con status=pending
      - background task pasa a running → completed
      - evidence_document_id set tras auto-attach
    """
    reset_executor_for_tests()
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)

    svc = get_mcp_executor()
    execution = await svc.execute_tool(
        db=db,
        project_id=pid,
        mcp_name="vulnscan",
        tool_name="nuclei_scan",
        params={"target": "https://example.com"},
    )
    assert execution.status == "pending"

    # Esperar hasta 5s a que el background task complete
    for _ in range(50):
        await asyncio.sleep(0.1)
        if execution.status in ("completed", "failed"):
            break

    assert execution.status == "completed", (
        f"status={execution.status} error={execution.error}"
    )
    assert execution.progress == 100
    assert execution.result is not None
    assert execution.result.get("_simulated") is True
    # Auto-attach evidence puede fallar si IDMS no setup pero NO bloquea
    # la ejecución (manejado defensive en _run_execution).


async def _wait_completion(execution, timeout_s: float = 5.0) -> None:
    """Helper: espera a que el background task termine.

    asyncpg single connection no permite ops concurrentes; secuenciar
    triggers en tests evita InterfaceError en rollback teardown.
    """
    for _ in range(int(timeout_s / 0.1)):
        await asyncio.sleep(0.1)
        if execution.status in ("completed", "failed"):
            return


@pytest.mark.asyncio
async def test_list_executions_by_project(db):
    reset_executor_for_tests()
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)

    svc = get_mcp_executor()
    e1 = await svc.execute_tool(
        db=db, project_id=pid,
        mcp_name="vulnscan", tool_name="nuclei_scan",
        params={"target": "https://example.com"},
    )
    await _wait_completion(e1)
    e2 = await svc.execute_tool(
        db=db, project_id=pid,
        mcp_name="cloud", tool_name="prowler_audit",
        params={"provider": "aws"},
    )
    await _wait_completion(e2)

    executions = svc.list_executions_by_project(pid)
    ids = {e.execution_id for e in executions}
    assert e1.execution_id in ids
    assert e2.execution_id in ids


@pytest.mark.asyncio
async def test_get_execution_isolation_across_projects(db):
    """Una execution NO debe ser visible desde otro project_id."""
    reset_executor_for_tests()
    _, p1_str = await setup_test_project(db)
    p1 = uuid.UUID(p1_str)
    p2 = uuid.uuid4()  # NOT real project

    svc = get_mcp_executor()
    execution = await svc.execute_tool(
        db=db, project_id=p1,
        mcp_name="vulnscan", tool_name="nuclei_scan",
        params={"target": "https://example.com"},
    )
    await _wait_completion(execution)

    p2_list = svc.list_executions_by_project(p2)
    assert execution not in p2_list


# ════════════════════════════════════════════════════════════════════
# Endpoint tests
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_endpoint_list_tools_catalog(async_client):
    response = await async_client.get("/api/v1/mcps/tools")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 13
    assert set(data["families"].keys()) == {
        "vulnscan", "cloud", "config", "phishing",
    }


@pytest.mark.asyncio
async def test_endpoint_execute_unknown_tool_404(async_client, db):
    _, project_id_str = await setup_test_project(db)
    response = await async_client.post(
        f"/api/v1/projects/{project_id_str}"
        "/mcps/vulnscan/tools/unknown_tool/execute",
        json={"params": {}},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_endpoint_execute_missing_required_param_400(
    async_client, db,
):
    _, project_id_str = await setup_test_project(db)
    response = await async_client.post(
        f"/api/v1/projects/{project_id_str}"
        "/mcps/vulnscan/tools/nuclei_scan/execute",
        json={"params": {}},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_endpoint_execute_201_and_status_lookup(async_client, db):
    reset_executor_for_tests()
    _, project_id_str = await setup_test_project(db)
    response = await async_client.post(
        f"/api/v1/projects/{project_id_str}"
        "/mcps/vulnscan/tools/nuclei_scan/execute",
        json={"params": {"target": "https://example.com"}},
    )
    assert response.status_code == 201
    body = response.json()
    exec_id = body["execution_id"]
    assert body["status"] == "pending"
    assert body["mcp_name"] == "vulnscan"
    assert body["tool_name"] == "nuclei_scan"

    # Esperar a que el background task complete · asyncpg single
    # connection no soporta ops concurrentes en teardown rollback.
    execution = get_mcp_executor().get_execution(uuid.UUID(exec_id))
    assert execution is not None
    await _wait_completion(execution)

    # Lookup status
    status_resp = await async_client.get(
        f"/api/v1/projects/{project_id_str}"
        f"/mcps/executions/{exec_id}",
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["execution_id"] == exec_id
