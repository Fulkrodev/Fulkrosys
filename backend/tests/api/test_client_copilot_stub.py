"""Tests · client_copilot_stub endpoint sub-atom 1.C.D.C.3 v3.8 → 1.D.B.1 v3.11.

Verifica STUB path (LLM disabled · llm_enabled patched a False) sostiene
schema response IDÉNTICO post 1.D.B.1 swap-in. Tests LLM real path en
`test_copilot_cliente_llm_service.py`.

  - POST /api/v1/client-portal/copilot/chat retorna 200 con ClientCopilotChatStubResponse
  - 5 action_ids cliente (que_hago · porque_importa · explica_concepto ·
    necesito_ayuda · chat_send) generan stub responses friendly
  - is_stub=True · next_action_hint si aplica
  - Schema response idéntico a 1.D.B.1 LLM real (swap-in zero refactor)
  - R29 audit empírico · 0 strings coercitivos en respuestas
  - 422 con action_id inválido (Pydantic Literal validation)
"""
from __future__ import annotations

from unittest.mock import patch

import pytest


COERCITIVE_PATTERNS = (
    "llevas",
    "deadline",
    "urgente",
    "atrasado",
    "se te acaba",
    "debes ahora",
    "fecha límite",
    "tienes que dejar",
)


def _assert_no_coercitive_strings(text: str) -> None:
    """Audit empírico R29 · 0 strings coercitivos en response_text."""
    lower = text.lower()
    for pattern in COERCITIVE_PATTERNS:
        assert pattern not in lower, (
            f"R29 violation · coercitive pattern '{pattern}' in response: {text}"
        )


@pytest.fixture
async def authed_client_user(async_client, db):
    """Override require_client_user + force llm_enabled=False (stub path).

    Post 1.D.B.1 v3.11 · endpoint usa LLM real cuando api_key configurado.
    Estos tests verifican el STUB path (graceful fallback) · LLM real path
    tests en `test_copilot_cliente_llm_service.py`.
    """
    from backend.app.main import app
    from backend.app.auth.dependencies import require_client_user

    import uuid
    from types import SimpleNamespace

    async def override():
        # 1.D.G.I · rate limit usa user.id + user.client_id (resolución de proyecto
        # R09 · sin proyecto en BD → cap omitido · proceede al stub).
        return SimpleNamespace(id=uuid.uuid4(), client_id=uuid.uuid4())

    app.dependency_overrides[require_client_user] = override
    # Force stub fallback path para predictable assertions
    with patch(
        "backend.app.agents.copilot_cliente_service.llm_enabled",
        return_value=False,
    ), patch(
        "backend.app.api.v1.client_copilot_stub.llm_enabled",
        return_value=False,
    ):
        yield async_client
    app.dependency_overrides.pop(require_client_user, None)


@pytest.mark.asyncio
async def test_client_copilot_chat_stub_que_hago(authed_client_user):
    resp = await authed_client_user.post(
        "/api/v1/client-portal/copilot/chat",
        json={
            "action_id": "que_hago",
            "step_title": "Formación G1",
            "step_template_id": "ENR_IM_03_FORMACION_EMPLEADOS",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["action_id"] == "que_hago"
    assert data["is_stub"] is True
    assert "Formación G1" in data["response_text"]
    assert data["next_action_hint"] is not None
    _assert_no_coercitive_strings(data["response_text"])


@pytest.mark.asyncio
async def test_client_copilot_chat_stub_porque_importa(authed_client_user):
    resp = await authed_client_user.post(
        "/api/v1/client-portal/copilot/chat",
        json={
            "action_id": "porque_importa",
            "step_title": "DICAT categorización",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["action_id"] == "porque_importa"
    assert "DICAT categorización" in data["response_text"]
    assert "ENS" in data["response_text"] or "Esquema Nacional" in data["response_text"]
    _assert_no_coercitive_strings(data["response_text"])


@pytest.mark.asyncio
async def test_client_copilot_chat_stub_explica_concepto(authed_client_user):
    resp = await authed_client_user.post(
        "/api/v1/client-portal/copilot/chat",
        json={
            "action_id": "explica_concepto",
            "concepto": "DORA",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["action_id"] == "explica_concepto"
    assert "DORA" in data["response_text"]
    _assert_no_coercitive_strings(data["response_text"])


@pytest.mark.asyncio
async def test_client_copilot_chat_stub_necesito_ayuda(authed_client_user):
    resp = await authed_client_user.post(
        "/api/v1/client-portal/copilot/chat",
        json={"action_id": "necesito_ayuda"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["action_id"] == "necesito_ayuda"
    # R29 · tono "estoy aquí" / "no hay prisa"
    text_lower = data["response_text"].lower()
    assert (
        "aquí" in text_lower
        or "ayudarte" in text_lower
        or "no hay prisa" in text_lower
    )
    _assert_no_coercitive_strings(data["response_text"])


@pytest.mark.asyncio
async def test_client_copilot_chat_stub_chat_send(authed_client_user):
    resp = await authed_client_user.post(
        "/api/v1/client-portal/copilot/chat",
        json={
            "action_id": "chat_send",
            "question": "¿Cuándo termino?",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["action_id"] == "chat_send"
    _assert_no_coercitive_strings(data["response_text"])


@pytest.mark.asyncio
async def test_client_copilot_chat_stub_invalid_action_rejected(authed_client_user):
    """Pydantic Literal rechaza action_id no válido (admin action_ids)."""
    resp = await authed_client_user.post(
        "/api/v1/client-portal/copilot/chat",
        json={"action_id": "draft_email"},  # admin action · NO existe cliente
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_client_copilot_chat_stub_requires_auth(async_client):
    """SIN auth · endpoint rechaza con 401/403."""
    resp = await async_client.post(
        "/api/v1/client-portal/copilot/chat",
        json={"action_id": "que_hago"},
    )
    assert resp.status_code in (401, 403, 422)
