"""E-4 · memoria entre conversaciones (CopilotQuery.history).

Verifica que los turnos previos del hilo se inyectan en el prompt del LLM
ENTRE el system prompt y la pregunta actual, y que sin historial el prompt
queda intacto (solo system + user). Patchea hybrid_search (sin fastembed) y
el router (sin LLM real) para capturar los mensajes ensamblados.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.agents.agent_14_copiloto.service import answer_question
from backend.app.agents.agent_14_copiloto.types import CopilotQuery


def _fake_router(captured: dict) -> MagicMock:
    def fake_complete(*, messages, model, max_tokens, temperature):
        captured["messages"] = messages
        return SimpleNamespace(
            content="MAGERIT alimenta el análisis de riesgos del ENS (RD 311/2022).",
            model="claude-haiku-4-5",
            prompt_tokens=10,
            completion_tokens=8,
            total_tokens=18,
            latency_ms=5,
        )

    router = MagicMock()
    router.complete.side_effect = fake_complete
    return router


@pytest.mark.asyncio
async def test_e4_history_injected_between_system_and_user(db):
    captured: dict = {}
    history = [
        {"role": "user", "content": "¿Qué es MAGERIT?"},
        {"role": "assistant", "content": "Es la metodología de análisis de riesgos."},
    ]
    query = CopilotQuery(
        question="¿Y cómo se relaciona con el ENS?",
        history=history,
    )

    with patch(
        "backend.app.agents.agent_14_copiloto.service.hybrid_search",
        new=AsyncMock(return_value=[]),
    ), patch(
        "backend.app.agents.agent_14_copiloto.service.get_default_llm_router",
        return_value=_fake_router(captured),
    ):
        await answer_question(db, query)

    msgs = captured["messages"]
    assert msgs[0]["role"] == "system"
    assert msgs[1] == history[0]
    assert msgs[2] == history[1]
    assert msgs[-1]["role"] == "user"
    assert "cómo se relaciona" in msgs[-1]["content"]


@pytest.mark.asyncio
async def test_e4_empty_history_keeps_prompt_intact(db):
    captured: dict = {}
    query = CopilotQuery(question="¿Qué es el ENS?")  # history default []

    with patch(
        "backend.app.agents.agent_14_copiloto.service.hybrid_search",
        new=AsyncMock(return_value=[]),
    ), patch(
        "backend.app.agents.agent_14_copiloto.service.get_default_llm_router",
        return_value=_fake_router(captured),
    ):
        await answer_question(db, query)

    msgs = captured["messages"]
    assert len(msgs) == 2  # solo system + user · sin historial
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "user"
