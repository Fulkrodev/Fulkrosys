"""Tests sub-bloque 11.A — Copilot streaming SSE expansion.

- ``test_quick_actions_per_context_returns_catalog``: hardcoded look-up
  endpoint, no DB / LLM.
- ``test_stream_emits_citation_frames_with_mock_llm``: stream pipeline with
  the LLM router mocked so the test runs deterministically without an
  Anthropic API key. Validates ``start`` -> ``delta`` -> ``citation`` ->
  ``done`` frame sequence and the new ``chunks_used`` / ``corpus_gap`` /
  ``confidence`` fields in the ``done`` frame.
"""
from __future__ import annotations

import json
from typing import Iterator

import pytest


@pytest.mark.asyncio
async def test_quick_actions_per_context_returns_catalog(async_client):
    r_magerit = await async_client.get(
        "/api/v1/copilot/quick-actions", params={"context": "magerit"},
    )
    assert r_magerit.status_code == 200, r_magerit.text
    actions = r_magerit.json()
    assert len(actions) >= 3
    assert all("prefill_query" in a for a in actions)
    assert all("id" in a and "label" in a and "icon" in a for a in actions)
    assert any("riesgo" in a["prefill_query"].lower() for a in actions)

    r_default = await async_client.get("/api/v1/copilot/quick-actions")
    assert r_default.status_code == 200
    default_actions = r_default.json()
    assert len(default_actions) >= 1

    r_unknown = await async_client.get(
        "/api/v1/copilot/quick-actions", params={"context": "no_existe_motor"},
    )
    assert r_unknown.status_code == 200
    assert r_unknown.json() == default_actions


class _FakeLLMResponse:
    def __init__(self, content: str):
        self.content = content
        self.model = "fake-model"
        self.prompt_tokens = 1
        self.completion_tokens = 1
        self.total_tokens = 2
        self.latency_ms = 1.0


class _FakeRouter:
    """Minimal stand-in for ``LLMRouter`` covering ``stream_complete``."""

    def __init__(self, tokens: list[str]):
        self._tokens = tokens

    def stream_complete(self, **_: object) -> Iterator[str]:
        for tok in self._tokens:
            yield tok

    def complete(self, **_: object) -> _FakeLLMResponse:
        return _FakeLLMResponse("".join(self._tokens))


@pytest.mark.asyncio
async def test_stream_emits_citation_frames_with_mock_llm(
    async_client, db, monkeypatch,
):
    fake_tokens = [
        "La medida ",
        "[RD 311/2022 medida op.acc.6] ",
        "exige autenticación robusta. ",
        "Más información en ",
        "[CCN-STIC 804 seccion 5.2].",
    ]
    fake_router = _FakeRouter(fake_tokens)
    monkeypatch.setattr(
        "backend.app.agents.agent_14_copiloto.service.get_default_llm_router",
        lambda: fake_router,
    )

    payload = {
        "question": "qué exige el RD 311/2022 sobre op.acc.6",
        "project_id": None,
    }
    frames: list[dict] = []
    async with async_client.stream(
        "POST",
        "/api/v1/copilot/chat/stream",
        json=payload,
    ) as resp:
        assert resp.status_code == 200, await resp.aread()
        async for raw_line in resp.aiter_lines():
            line = raw_line.strip()
            if not line.startswith("data:"):
                continue
            frames.append(json.loads(line[len("data:"):].strip()))

    types = [f["type"] for f in frames]
    assert types[0] == "start"
    assert "delta" in types
    assert "citation" in types
    assert types[-1] == "done"

    citation_frames = [f for f in frames if f["type"] == "citation"]
    raw_citations = [f["data"]["raw"] for f in citation_frames]
    assert any("op.acc.6" in r for r in raw_citations)
    assert all("norm" in f["data"] for f in citation_frames)

    done = next(f for f in frames if f["type"] == "done")["data"]
    assert "answer" in done
    assert "chunks_used" in done
    assert "confidence" in done
    assert "corpus_gap" in done
    assert isinstance(done["confidence"], (int, float))
    assert isinstance(done["corpus_gap"], bool)
    assert "[RD 311/2022 medida op.acc.6]" in done["answer"]
    assert "op.acc.6" in done["citations_found"][0]

    start = frames[0]
    assert "confidence" in start
    assert "corpus_gap" in start
