"""Tests for backend.app.core.ai.llm_router module — SDK oficial anthropic.

Post-refactor Sesion 9: el router usa ``client.messages.stream()`` del SDK
oficial. Los mocks patchean el cliente interno del router.
"""

import logging
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from backend.app.core.ai.llm_router import (
    LLMResponse,
    LLMRouter,
    get_default_llm_router,
    reset_default_llm_router,
)


# ------------------------------------------------------------------
# Environment / configuration
# ------------------------------------------------------------------

def test_default_model_from_env(monkeypatch, patched_settings):
    monkeypatch.setenv("ANTHROPIC_DEFAULT_MODEL", "claude-test-model")
    monkeypatch.setenv("ANTHROPIC_FALLBACK_MODEL", "claude-fallback-test")
    patched_settings(anthropic_api_key="sk-test-key")
    router = LLMRouter()
    assert router.default_model == "claude-test-model"
    assert router.fallback_model == "claude-fallback-test"


def test_router_warns_on_missing_api_key(patched_settings, caplog):
    patched_settings(anthropic_api_key="")
    with caplog.at_level(logging.WARNING):
        router = LLMRouter(api_key="")
    assert "ANTHROPIC_API_KEY not set" in caplog.text


# ------------------------------------------------------------------
# Mocked stream (SDK oficial)
# ------------------------------------------------------------------


def _make_mock_message(content: str = "OK", model: str = "claude-sonnet-4-5"):
    """Build a Message-like object compatible con response.content[0].text."""
    text_block = SimpleNamespace(type="text", text=content)
    usage = SimpleNamespace(
        input_tokens=10,
        output_tokens=5,
    )
    return SimpleNamespace(
        content=[text_block],
        usage=usage,
        model=model,
    )


class _FakeStreamCtx:
    """Context manager que imita client.messages.stream()."""

    def __init__(self, final_message):
        self._final = final_message

    def __enter__(self):
        # ``text_stream`` es iterable (puede estar vacío).
        self.text_stream = iter([self._final.content[0].text])
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get_final_message(self):
        return self._final


def test_router_complete_with_mock(patched_settings):
    patched_settings(anthropic_api_key="sk-test-key")
    router = LLMRouter()

    mock_msg = _make_mock_message(content="Respuesta de prueba")
    mock_stream = MagicMock(return_value=_FakeStreamCtx(mock_msg))

    with patch.object(router._client.messages, "stream", mock_stream):
        response = router.complete(
            messages=[{"role": "user", "content": "Hola"}],
            max_tokens=50,
        )

    assert isinstance(response, LLMResponse)
    assert response.content == "Respuesta de prueba"
    assert response.prompt_tokens == 10
    assert response.completion_tokens == 5
    assert response.total_tokens == 15
    assert response.latency_ms >= 0
    mock_stream.assert_called_once()


def test_router_use_fallback_model(monkeypatch, patched_settings):
    monkeypatch.setenv("ANTHROPIC_FALLBACK_MODEL", "claude-opus-4-6")
    patched_settings(anthropic_api_key="sk-test-key")
    router = LLMRouter()

    mock_msg = _make_mock_message(model="claude-opus-4-6")
    mock_stream = MagicMock(return_value=_FakeStreamCtx(mock_msg))

    with patch.object(router._client.messages, "stream", mock_stream):
        response = router.complete(
            messages=[{"role": "user", "content": "test"}],
            use_fallback=True,
        )

    # Verifica que el modelo usado fue el fallback (sin prefijo "anthropic/")
    call_kwargs = mock_stream.call_args.kwargs
    assert "opus" in call_kwargs.get("model", "")
    # El SDK no acepta el prefijo "anthropic/" por eso _strip_anthropic_prefix
    # lo elimina — el modelo que llega al SDK es "claude-opus-4-6".
    assert not call_kwargs["model"].startswith("anthropic/")
    assert "opus" in response.model


def test_router_strips_anthropic_prefix(patched_settings):
    """Si un caller pasa ``anthropic/claude-opus-4-7`` el router lo limpia."""
    patched_settings(anthropic_api_key="sk-test-key")
    router = LLMRouter()

    mock_msg = _make_mock_message(model="claude-opus-4-7")
    mock_stream = MagicMock(return_value=_FakeStreamCtx(mock_msg))

    with patch.object(router._client.messages, "stream", mock_stream):
        router.complete(
            messages=[{"role": "user", "content": "x"}],
            model="anthropic/claude-opus-4-7",
            max_tokens=10,
        )

    call_model = mock_stream.call_args.kwargs["model"]
    assert call_model == "claude-opus-4-7"


def test_router_omits_temperature_for_opus_47(patched_settings):
    """opus-4.7 rechaza ``temperature`` → el router no lo envía."""
    patched_settings(anthropic_api_key="sk-test-key")
    router = LLMRouter()

    mock_msg = _make_mock_message(model="claude-opus-4-7")
    mock_stream = MagicMock(return_value=_FakeStreamCtx(mock_msg))

    with patch.object(router._client.messages, "stream", mock_stream):
        router.complete(
            messages=[{"role": "user", "content": "x"}],
            model="claude-opus-4-7",
            max_tokens=10,
            temperature=0.15,
        )

    kwargs = mock_stream.call_args.kwargs
    assert "temperature" not in kwargs, (
        f"Opus 4.7 no acepta temperature; no debe enviarse. kwargs={list(kwargs)}"
    )


def test_router_splits_system_and_messages(patched_settings):
    """El role=system se extrae como param ``system`` del SDK."""
    patched_settings(anthropic_api_key="sk-test-key")
    router = LLMRouter()

    mock_msg = _make_mock_message()
    mock_stream = MagicMock(return_value=_FakeStreamCtx(mock_msg))

    with patch.object(router._client.messages, "stream", mock_stream):
        router.complete(
            messages=[
                {"role": "system", "content": "Eres X."},
                {"role": "user", "content": "Hola"},
            ],
            model="claude-sonnet-4-5",
            max_tokens=10,
        )

    kwargs = mock_stream.call_args.kwargs
    assert kwargs["system"] == "Eres X."
    assert len(kwargs["messages"]) == 1
    assert kwargs["messages"][0]["role"] == "user"


# ------------------------------------------------------------------
# Singleton
# ------------------------------------------------------------------

def test_get_default_llm_router_returns_singleton(patched_settings):
    patched_settings(anthropic_api_key="sk-test-key")
    reset_default_llm_router()

    r1 = get_default_llm_router()
    r2 = get_default_llm_router()
    assert r1 is r2
