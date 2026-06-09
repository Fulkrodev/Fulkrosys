"""Tests Sprint C3 — M11 Copilot expansion."""
from __future__ import annotations

import uuid
import pytest

from backend.app.models.copilot import CopilotConversation, CopilotMessage
from backend.tests.conftest import setup_test_project


BASE = "/api/v1/projects"


def test_c3_copilot_models_defined():
    assert CopilotConversation.__tablename__ == "copilot_conversations"
    assert CopilotMessage.__tablename__ == "copilot_messages"


@pytest.mark.asyncio
async def test_c3_api_create_conversation(async_client, db):
    _, project_id = await setup_test_project(db)
    r = await async_client.post(
        f"{BASE}/{project_id}/copilot/conversations",
        json={"titulo": "Test conversation", "modelo_default": "claude-sonnet-4-5"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["titulo"] == "Test conversation"


@pytest.mark.asyncio
async def test_c3_api_list_conversations_empty(async_client, db):
    _, project_id = await setup_test_project(db)
    r = await async_client.get(f"{BASE}/{project_id}/copilot/conversations")
    assert r.status_code == 200
    assert r.json()["conversations"] == []


@pytest.mark.asyncio
async def test_c3_api_get_conversation_404(async_client, db):
    _, project_id = await setup_test_project(db)
    fake = uuid.uuid4()
    r = await async_client.get(f"{BASE}/{project_id}/copilot/conversations/{fake}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_c3_api_delete_conversation(async_client, db):
    _, project_id = await setup_test_project(db)
    r = await async_client.post(
        f"{BASE}/{project_id}/copilot/conversations",
        json={"titulo": "To delete"},
    )
    conv_id = r.json()["id"]
    r2 = await async_client.delete(f"{BASE}/{project_id}/copilot/conversations/{conv_id}")
    assert r2.status_code == 200


@pytest.mark.asyncio
async def test_c3_api_summary_returns_structure(async_client, db):
    _, project_id = await setup_test_project(db)
    r = await async_client.get(f"{BASE}/{project_id}/copilot/summary")
    assert r.status_code == 200
    data = r.json()
    assert "summary" in data
    assert "context" in data
    assert "dda" in data["context"]


@pytest.mark.asyncio
async def test_c3_api_project_context(async_client, db):
    _, project_id = await setup_test_project(db)
    r = await async_client.post(f"{BASE}/{project_id}/copilot/context")
    assert r.status_code == 200
    ctx = r.json()
    assert "dda" in ctx
    assert "evidence" in ctx
    assert "findings" in ctx
    assert "pentest" in ctx
