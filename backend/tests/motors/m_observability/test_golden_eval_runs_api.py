"""Tests golden_eval_runs admin API · sub-atom 1.E.1.B.3.E.

Cubre:
  - GET /datasets · list available
  - POST /run · trigger eval run · sync execute
  - GET /runs · historical list
  - GET /runs/{run_id} · drill-down
  - RBAC require_owner enforced (real_auth marker)
"""
from __future__ import annotations

import pytest



pytestmark = pytest.mark.asyncio


# ════════════════════════════════════════════════════════════════════
# /datasets · list available
# ════════════════════════════════════════════════════════════════════


async def test_admin_list_datasets_returns_deliverable_text_auditor(
    async_client,
):
    r = await async_client.get(
        "/api/v1/admin/observability/golden-eval/datasets",
    )
    assert r.status_code == 200, r.text
    data = r.json()
    items = data["items"]
    agents = [item["agent_name"] for item in items]
    assert "deliverable_text_auditor" in agents


# ════════════════════════════════════════════════════════════════════
# POST /run · trigger eval (sync execute)
# ════════════════════════════════════════════════════════════════════


async def test_admin_trigger_run_sync_completes_skipped(async_client, db):
    """Trigger eval run sync · capability pending → entries skipped ·
    status completes con severity ok (vacuously) · regression_score=1.0."""
    r = await async_client.post(
        "/api/v1/admin/observability/golden-eval/run",
        json={
            "agent_name": "deliverable_text_auditor",
            "version": "v1",
            "sync_execute": True,
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["agent_name"] == "deliverable_text_auditor"
    assert data["status"] == "completed"
    assert data["entries_in_dataset"] == 10
    # All entries skipped (capability pending) · evaluated == 0
    assert data["entries_evaluated"] == 0
    assert data["regression_score"] == 1.0  # vacuously true
    assert data["severity"] == "ok"


async def test_admin_trigger_run_queued_no_sync(async_client, db):
    """sync_execute=False · run permanece queued para Celery worker future."""
    r = await async_client.post(
        "/api/v1/admin/observability/golden-eval/run",
        json={
            "agent_name": "deliverable_text_auditor",
            "version": "v1",
            "sync_execute": False,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "queued"
    assert "id" in data


# ════════════════════════════════════════════════════════════════════
# GET /runs · history
# ════════════════════════════════════════════════════════════════════


async def test_admin_list_runs_returns_recently_triggered(async_client, db):
    # Trigger 1 sync run primero
    await async_client.post(
        "/api/v1/admin/observability/golden-eval/run",
        json={
            "agent_name": "deliverable_text_auditor",
            "version": "v1",
            "sync_execute": True,
        },
    )
    r = await async_client.get(
        "/api/v1/admin/observability/golden-eval/runs?days=7",
    )
    assert r.status_code == 200
    data = r.json()
    assert data["days"] == 7
    assert data["total"] >= 1
    # Verify ordered DESC + agent_name presente
    item = data["items"][0]
    assert item["agent_name"] == "deliverable_text_auditor"


async def test_admin_list_runs_filter_by_agent_name(async_client, db):
    r = await async_client.get(
        "/api/v1/admin/observability/golden-eval/runs?"
        "agent_name=nonexistent_agent&days=7",
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0


# ════════════════════════════════════════════════════════════════════
# GET /runs/{run_id} · drill-down
# ════════════════════════════════════════════════════════════════════


async def test_admin_get_run_detail(async_client, db):
    trigger = await async_client.post(
        "/api/v1/admin/observability/golden-eval/run",
        json={
            "agent_name": "deliverable_text_auditor",
            "version": "v1",
            "sync_execute": True,
        },
    )
    run_id = trigger.json()["id"]
    r = await async_client.get(
        f"/api/v1/admin/observability/golden-eval/runs/{run_id}",
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["id"] == run_id
    assert data["status"] == "completed"


async def test_admin_get_run_unknown_returns_404(async_client):
    r = await async_client.get(
        "/api/v1/admin/observability/golden-eval/runs/"
        "00000000-0000-0000-0000-000000000000",
    )
    assert r.status_code == 404


# ════════════════════════════════════════════════════════════════════
# RBAC · require_owner blocks anonymous
# ════════════════════════════════════════════════════════════════════


@pytest.mark.real_auth
async def test_require_owner_blocks_anonymous_golden_eval_endpoints(
    async_client,
):
    """SIN auth · golden-eval endpoints 401/403."""
    endpoints = (
        "/api/v1/admin/observability/golden-eval/datasets",
        "/api/v1/admin/observability/golden-eval/runs",
        ("POST", "/api/v1/admin/observability/golden-eval/run"),
    )
    for ep in endpoints:
        if isinstance(ep, tuple):
            method, url = ep
            r = await async_client.post(
                url,
                json={"agent_name": "x", "version": "v1"},
            )
        else:
            r = await async_client.get(ep)
        assert r.status_code in (401, 403), (
            f"endpoint {ep} retornó {r.status_code} sin auth · expected 401/403"
        )
