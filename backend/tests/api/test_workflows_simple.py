"""Tests for /api/v1/workflows/{name}/run · MB-7 Q7.C."""
import pytest

pytestmark = pytest.mark.asyncio


async def test_workflows_list_returns_predefined_chains(async_client):
    r = await async_client.get("/api/v1/workflows")
    assert r.status_code == 200
    data = r.json()
    assert "audit_prep" in data
    assert "incident_analysis" in data
    assert "dda_review_inconsistencies" in data
    assert data["audit_prep"]["steps"] == [11, 4, 14]


async def test_workflow_chain_audit_prep_returns_step_results(async_client):
    """Happy path · chain of 3 agents (uses MOCK fallback without LLM key)."""
    r = await async_client.post(
        "/api/v1/workflows/audit_prep/run",
        json={"user_message": "Prepara una auditoria simulada del proyecto"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["workflow"] == "audit_prep"
    assert data["steps_executed"] == 3
    assert len(data["step_results"]) == 3
    assert data["step_results"][0]["agent_id"] == 11
    assert data["step_results"][1]["agent_id"] == 4
    assert data["step_results"][2]["agent_id"] == 14
    assert isinstance(data["total_tokens_input"], int)
    assert isinstance(data["total_tokens_output"], int)
    assert data["final_response"]


async def test_workflow_chain_invalid_name_404(async_client):
    r = await async_client.post(
        "/api/v1/workflows/nonexistent_workflow/run",
        json={"user_message": "test"},
    )
    assert r.status_code == 404
    assert "not registered" in r.json()["detail"].lower()
