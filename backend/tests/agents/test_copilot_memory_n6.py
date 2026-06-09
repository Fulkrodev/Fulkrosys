"""FRENTE E · N6 · memoria del copiloto entre conversaciones.

Verifica el MECANISMO determinista (sin BD/LLM real):
- ``_call_llm`` inyecta el historial ENTRE el system y el mensaje actual, en
  orden cronológico (admin + cliente).
- ``copilot_memory`` degrada a stateless (project_id None → (None, [])).
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from backend.app.agents.copilot_admin_service import CopilotAdminLLMService
from backend.app.agents.copilot_cliente_service import CopilotClienteLLMService


class _FakeResp:
    content = "RESP"
    prompt_tokens = 1
    completion_tokens = 1
    model = "fake-model"


class _FakeRouter:
    def __init__(self, sink: dict):
        self._sink = sink

    def complete(self, messages, **kw):  # noqa: ANN001
        self._sink["messages"] = messages
        return _FakeResp()


_HISTORY = [
    {"role": "user", "content": "H1-pregunta-previa"},
    {"role": "assistant", "content": "H2-respuesta-previa"},
]


@pytest.mark.asyncio
@pytest.mark.parametrize("svc_cls", [CopilotAdminLLMService, CopilotClienteLLMService])
async def test_call_llm_injects_history_in_order(svc_cls):
    svc = svc_cls()
    sink: dict = {}
    with patch(
        "backend.app.core.ai.llm_router.get_default_llm_router",
        return_value=_FakeRouter(sink),
    ), patch.object(svc, "_log_interaction", new=AsyncMock()):
        out = await svc._call_llm(
            "SYSTEM", "USER-ACTUAL", db=None, project_id=None, history=_HISTORY,
        )

    assert out == "RESP"
    msgs = sink["messages"]
    roles = [m["role"] for m in msgs]
    # system → historial (user, assistant) → mensaje actual
    assert roles == ["system", "user", "assistant", "user"]
    assert msgs[0]["content"] == "SYSTEM"
    assert msgs[1]["content"] == "H1-pregunta-previa"
    assert msgs[2]["content"] == "H2-respuesta-previa"
    assert msgs[-1]["content"] == "USER-ACTUAL"


@pytest.mark.asyncio
async def test_call_llm_no_history_is_backward_compatible():
    svc = CopilotAdminLLMService()
    sink: dict = {}
    with patch(
        "backend.app.core.ai.llm_router.get_default_llm_router",
        return_value=_FakeRouter(sink),
    ), patch.object(svc, "_log_interaction", new=AsyncMock()):
        await svc._call_llm("SYS", "USER", db=None, project_id=None)
    assert [m["role"] for m in sink["messages"]] == ["system", "user"]


@pytest.mark.asyncio
async def test_memory_helper_graceful_without_project():
    from backend.app.agents.copilot_memory import (
        load_conversation_history,
        persist_exchange,
    )

    conv_id, history = await load_conversation_history(project_id=None)
    assert conv_id is None and history == []
    # no project → no-op (no raise)
    await persist_exchange(
        conversation_id=None, project_id=None,
        user_text="x", assistant_text="y",
    )
