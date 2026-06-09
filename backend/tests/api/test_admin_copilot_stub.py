"""Tests · admin_copilot_stub endpoint sub-atom 1.C.D.B.3 v3.8 → 1.D.B.2 v3.11.

Verifica STUB path (LLM disabled · llm_enabled patched a False) sostiene
schema response IDÉNTICO post 1.D.B.2 swap-in. Tests LLM real path en
`test_copilot_admin_llm_service.py`.

  - POST /api/v1/admin/copilot/chat retorna 200 con CopilotChatStubResponse
  - 5 action_ids generan stub responses CALIDAD contextualizados
  - is_stub=True · next_action_hint per action
  - Schema response idéntico a LLM real (swap-in zero refactor)
"""
from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def force_llm_disabled():
    """Force llm_enabled=False para todos los tests · predictable stub path.

    Post 1.D.B.2 v3.11 · endpoint usa LLM real cuando api_key configurado.
    Estos tests verifican el STUB path (graceful fallback) · LLM real path
    tested en `test_copilot_admin_llm_service.py`.
    """
    with patch(
        "backend.app.agents.copilot_cliente_service.llm_enabled",
        return_value=False,
    ), patch(
        "backend.app.api.v1.admin_copilot_stub.llm_enabled",
        return_value=False,
    ):
        yield


@pytest.mark.asyncio
async def test_copilot_chat_stub_que_hago(async_client):
    """action_id=que_hago retorna stub response contextualizado."""
    resp = await async_client.post(
        "/api/v1/admin/copilot/chat",
        json={
            "action_id": "que_hago",
            "project_nombre": "Fintech Plus",
            "step_title": "Formación G1",
            "step_template_id": "ENR_IM_03_FORMACION_EMPLEADOS",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["action_id"] == "que_hago"
    assert data["is_stub"] is True
    assert "Fintech Plus" in data["response_text"]
    assert "Formación G1" in data["response_text"]
    assert "LLM completo" in data["response_text"]
    assert data["next_action_hint"] is not None


@pytest.mark.asyncio
async def test_copilot_chat_stub_explica_paso(async_client):
    resp = await async_client.post(
        "/api/v1/admin/copilot/chat",
        json={
            "action_id": "explica_paso",
            "step_title": "DICAT categorización",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["action_id"] == "explica_paso"
    assert data["is_stub"] is True
    assert "DICAT categorización" in data["response_text"]
    assert "ENS Anexo II" in data["response_text"]


@pytest.mark.asyncio
async def test_copilot_chat_stub_draft_email(async_client):
    resp = await async_client.post(
        "/api/v1/admin/copilot/chat",
        json={"action_id": "draft_email"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["action_id"] == "draft_email"
    assert "plantillas E-XXX" in data["response_text"]


@pytest.mark.asyncio
async def test_copilot_chat_stub_briefing_reunion(async_client):
    resp = await async_client.post(
        "/api/v1/admin/copilot/chat",
        json={
            "action_id": "briefing_reunion",
            "project_nombre": "Industrial Talavera",
            "fase_actual": "verificacion",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "Industrial Talavera" in data["response_text"]
    assert "verificacion" in data["response_text"]


@pytest.mark.asyncio
async def test_copilot_chat_stub_chat_send(async_client):
    resp = await async_client.post(
        "/api/v1/admin/copilot/chat",
        json={
            "action_id": "chat_send",
            "question": "Pregunta libre",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["action_id"] == "chat_send"
    assert "próximo sprint" in data["response_text"]


@pytest.mark.asyncio
async def test_copilot_chat_stub_invalid_action_rejected(async_client):
    """Pydantic Literal rechaza action_id no válido."""
    resp = await async_client.post(
        "/api/v1/admin/copilot/chat",
        json={"action_id": "not_a_real_action"},
    )
    assert resp.status_code == 422  # Pydantic validation error
