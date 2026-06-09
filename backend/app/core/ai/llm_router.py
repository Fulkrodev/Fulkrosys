"""LLM Router for FULKRO — wraps the official Anthropic SDK.

Reads configuration from environment variables:
  - ANTHROPIC_API_KEY: required
  - ANTHROPIC_DEFAULT_MODEL: default model (default: claude-sonnet-4-5)
  - ANTHROPIC_FALLBACK_MODEL: fallback model (default: claude-opus-4-6)

Design notes:
- Usa el SDK oficial ``anthropic`` en vez de litellm. litellm rechazaba
  ``claude-opus-4-7`` con ``authentication_error`` aunque la misma key
  via httpx directa funcionaba (bug de routing de litellm con el prefix
  ``anthropic/``). Bypass permanente documentado en
  progress/backlog_formal.md "deuda menor: remover litellm Sesion 10".
- Mantiene el mismo contrato publico (``LLMResponse``, ``LLMRouter``,
  ``get_default_llm_router``) para no romper callers existentes.
- Traduce el formato OpenAI-style (messages con role=system) al formato
  Anthropic (system string + messages sin role=system).
- Reintentos con backoff 2s/8s/32s sobre ``RateLimitError`` hasta 3
  intentos; ``AuthenticationError`` y ``APIError`` suben tal cual.
"""

from __future__ import annotations

import logging
import os
import random
import time
from dataclasses import dataclass
from typing import Any, Iterator

from anthropic import (
    Anthropic,
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    RateLimitError,
)
from dotenv import load_dotenv

from backend.app.config import get_settings

load_dotenv()

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public exception hierarchy (estable para callers)
# ---------------------------------------------------------------------------


class LLMError(Exception):
    """Base class for FULKRO LLM layer errors."""


class LLMAuthError(LLMError):
    """Credencial invalida / ausente."""


class LLMRateLimitError(LLMError):
    """Rate limit agotado tras reintentos con backoff."""


class LLMBackendError(LLMError):
    """Error del backend Anthropic (5xx, timeout, conexion)."""


class LLMBadRequestError(LLMError):
    """Request malformado (4xx distinto de 401/429)."""


# ---------------------------------------------------------------------------
# Response dataclass (contrato publico sin cambios)
# ---------------------------------------------------------------------------


@dataclass
class LLMResponse:
    """Structured response from an LLM call."""

    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    # Prompt caching (Anthropic). 0 si no se usa ``enable_prompt_caching``
    # o si el modelo no soporta cache. cache_creation = tokens escritos al
    # cache; cache_read = tokens leidos de cache (10% del coste input).
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


# ---------------------------------------------------------------------------
# Retry config
# ---------------------------------------------------------------------------


_RATE_LIMIT_BACKOFFS: tuple[float, ...] = (2.0, 8.0, 32.0)


# Modelos que han deprecado el parametro ``temperature`` (Anthropic lo
# rechaza con 400 "temperature is deprecated for this model"). Se omite
# silenciosamente el param en esos casos.
_MODELS_WITHOUT_TEMPERATURE: frozenset[str] = frozenset(
    {
        "claude-opus-4-7",
    }
)


def _sleep_with_jitter(base: float) -> None:
    """Sleep base +/- 20% jitter para evitar thundering herd."""
    factor = 1.0 + random.uniform(-0.2, 0.2)
    time.sleep(max(0.1, base * factor))


# ---------------------------------------------------------------------------
# Helpers de conversion de mensajes
# ---------------------------------------------------------------------------


def _split_system_and_messages(
    messages: list[dict[str, Any]]
) -> tuple[str | None, list[dict[str, Any]]]:
    """El SDK oficial separa ``system`` del resto de mensajes.

    Consolida todos los role=system encontrados en una sola cadena ``system``
    y devuelve la lista de mensajes restantes (role=user/assistant). Acepta
    mensajes con ``content`` string o con ``content`` lista (multimodal).
    """
    system_parts: list[str] = []
    remaining: list[dict[str, Any]] = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            if isinstance(content, str):
                system_parts.append(content)
            elif isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "text":
                        system_parts.append(c.get("text", ""))
            else:
                system_parts.append(str(content))
            continue
        remaining.append(msg)
    system_str = "\n\n".join(p for p in system_parts if p) or None
    return system_str, remaining


def _strip_anthropic_prefix(model: str) -> str:
    """Quita el prefijo ``anthropic/`` si quedase de la era litellm."""
    if model.startswith("anthropic/"):
        return model[len("anthropic/"):]
    return model


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


class LLMRouter:
    """Routes LLM requests to Anthropic via the official SDK.

    Mantiene el contrato publico previo: ``complete`` (sync) y
    ``stream_complete`` (sync iterator). Internamente usa ``anthropic.Anthropic``.
    """

    def __init__(
        self,
        default_model: str | None = None,
        fallback_model: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float = 120.0,
        max_retries: int = 0,  # reintentos se manejan en ``_call_with_retries``
    ) -> None:
        self._api_key = api_key or get_settings().anthropic_api_key.get_secret_value()
        self._default_model = default_model or os.environ.get(
            "ANTHROPIC_DEFAULT_MODEL", "claude-sonnet-4-5"
        )
        self._fallback_model = fallback_model or os.environ.get(
            "ANTHROPIC_FALLBACK_MODEL", "claude-opus-4-6"
        )

        if not self._api_key:
            logger.warning(
                "ANTHROPIC_API_KEY not set — LLM calls will fail. "
                "Set it in .env or environment."
            )

        # El SDK expone su propia capa de reintentos, pero la dejamos en 0
        # para controlar el backoff desde este modulo (log + metricas).
        self._client = Anthropic(
            api_key=self._api_key,
            timeout=timeout_seconds,
            max_retries=max_retries,
        )

    # Compatibilidad: algunos callers crean router + ajustan key despues.
    @property
    def api_key(self) -> str:
        return self._api_key

    @property
    def default_model(self) -> str:
        return self._default_model

    @property
    def fallback_model(self) -> str:
        return self._fallback_model

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def complete(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        use_fallback: bool = False,
        enable_prompt_caching: bool = False,
        **kwargs: Any,
    ) -> LLMResponse:
        """Send a completion request via the Anthropic SDK.

        Args:
            messages: Lista OpenAI-style con roles. Se extrae ``system``
                automaticamente si aparece; el resto (``user``/``assistant``)
                va a ``messages.create``.
            model: Override model name. Se le quita cualquier prefijo
                ``anthropic/`` heredado.
            max_tokens: Tope de tokens de respuesta.
            temperature: Sampling temperature (0..1).
            use_fallback: Si True, usa ``fallback_model`` en vez del default.
            enable_prompt_caching: Si True y hay ``system`` prompt, lo envia
                como bloque estructurado con ``cache_control={"type":
                "ephemeral"}`` (TTL 5 min). La primera llamada paga ``cache
                creation`` (~1.25x base); llamadas subsiguientes dentro
                del TTL pagan ``cache read`` (~0.1x base). Ideal para
                prompts >1k tokens que se reusan (A18 panel live).
            **kwargs: Params adicionales pasados a ``messages.create``
                (p. ej. ``top_p``, ``stop_sequences``, ``metadata``).

        Raises:
            LLMAuthError: 401 Anthropic (api key invalida).
            LLMRateLimitError: 429 tras agotar reintentos.
            LLMBackendError: 5xx / timeout / connection.
            LLMBadRequestError: 400 (modelo invalido, tokens fuera de rango).
        """
        if model is None:
            model = self._fallback_model if use_fallback else self._default_model
        model = _strip_anthropic_prefix(model)

        system_prompt, user_messages = _split_system_and_messages(messages)

        create_kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": user_messages,
            **kwargs,
        }
        if model not in _MODELS_WITHOUT_TEMPERATURE:
            create_kwargs["temperature"] = temperature
        if system_prompt is not None:
            if enable_prompt_caching:
                # Bloque estructurado con cache_control ephemeral (TTL 5 min).
                # Para modelos sin soporte de caching Anthropic devuelve 400;
                # lo dejamos fallar explicitamente para no silenciar bugs.
                create_kwargs["system"] = [
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"},
                    }
                ]
            else:
                create_kwargs["system"] = system_prompt

        t0 = time.perf_counter()
        response = self._call_with_retries(create_kwargs)
        latency_ms = (time.perf_counter() - t0) * 1000

        text = _extract_text(response)
        usage = getattr(response, "usage", None)
        input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        cache_creation = int(getattr(usage, "cache_creation_input_tokens", 0) or 0)
        cache_read = int(getattr(usage, "cache_read_input_tokens", 0) or 0)
        model_returned = getattr(response, "model", model) or model

        return LLMResponse(
            content=text,
            model=model_returned,
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens + cache_creation + cache_read,
            latency_ms=round(latency_ms, 1),
            cache_creation_input_tokens=cache_creation,
            cache_read_input_tokens=cache_read,
        )

    def stream_complete(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> Iterator[str]:
        """Yield content deltas via the SDK stream helper.

        El iterador emite strings no vacios con cada delta de texto. Si el
        stream termina sin deltas, no emite nada (no lanza).
        """
        if model is None:
            model = self._default_model
        model = _strip_anthropic_prefix(model)
        system_prompt, user_messages = _split_system_and_messages(messages)
        create_kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": user_messages,
            **kwargs,
        }
        if model not in _MODELS_WITHOUT_TEMPERATURE:
            create_kwargs["temperature"] = temperature
        if system_prompt is not None:
            create_kwargs["system"] = system_prompt

        try:
            with self._client.messages.stream(**create_kwargs) as stream:
                for text_delta in stream.text_stream:
                    if text_delta:
                        yield text_delta
        except AuthenticationError as e:
            raise LLMAuthError(str(e)) from e
        except RateLimitError as e:
            raise LLMRateLimitError(str(e)) from e
        except (APIConnectionError, APITimeoutError, InternalServerError) as e:
            raise LLMBackendError(str(e)) from e
        except BadRequestError as e:
            raise LLMBadRequestError(str(e)) from e
        except APIStatusError as e:
            # Catch-all para status codes no mapeados arriba (4xx/5xx).
            raise LLMBackendError(str(e)) from e
        except APIError as e:
            raise LLMBackendError(str(e)) from e

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _call_with_retries(self, create_kwargs: dict[str, Any]) -> Any:
        """Ejecuta ``messages.create`` con reintentos exponenciales en 429.

        Usa el helper ``messages.stream()`` en vez de ``create()`` porque
        Anthropic corta las peticiones non-streaming con max_tokens alto
        (>~4096) despues de ~60s con el error "Request timed out or
        interrupted" (ver https://docs.anthropic.com/en/api/errors#long-requests).
        El cliente sync acumula los deltas y devuelve el ``Message`` final
        con el mismo contrato (``.content``, ``.usage``, ``.model``).
        """
        last_rate_limit_exc: Exception | None = None
        for attempt, backoff in enumerate([0.0, *_RATE_LIMIT_BACKOFFS]):
            if backoff > 0:
                logger.info(
                    "LLMRouter: rate-limit retry attempt %d after %.1fs",
                    attempt, backoff,
                )
                _sleep_with_jitter(backoff)
            try:
                # Streaming interno: evita el timeout de non-streaming cuando
                # el output esperado supera ~4k tokens.
                with self._client.messages.stream(**create_kwargs) as stream:
                    # Iteramos los deltas para drenar el stream. La SDK
                    # acumula internamente y expone el Message completo
                    # al salir del ``with``.
                    for _ in stream.text_stream:
                        pass
                    return stream.get_final_message()
            except AuthenticationError as e:
                raise LLMAuthError(str(e)) from e
            except BadRequestError as e:
                raise LLMBadRequestError(str(e)) from e
            except RateLimitError as e:
                last_rate_limit_exc = e
                continue
            except (APIConnectionError, APITimeoutError, InternalServerError) as e:
                # 5xx / timeout / connection — reintentamos con backoff
                last_rate_limit_exc = e
                continue
            except APIStatusError as e:
                if 500 <= getattr(e, "status_code", 0) < 600:
                    last_rate_limit_exc = e
                    continue
                raise LLMBackendError(str(e)) from e
            except APIError as e:
                raise LLMBackendError(str(e)) from e
        # Si salimos del loop sin return, se agotaron los reintentos
        assert last_rate_limit_exc is not None
        if isinstance(last_rate_limit_exc, RateLimitError):
            raise LLMRateLimitError(str(last_rate_limit_exc)) from last_rate_limit_exc
        raise LLMBackendError(str(last_rate_limit_exc)) from last_rate_limit_exc


# ---------------------------------------------------------------------------
# Helpers de extraccion
# ---------------------------------------------------------------------------


def _extract_text(response: Any) -> str:
    """Concatena todos los bloques ``TextBlock`` en la respuesta."""
    parts: list[str] = []
    for block in getattr(response, "content", []) or []:
        if getattr(block, "type", None) == "text":
            txt = getattr(block, "text", "") or ""
            if txt:
                parts.append(txt)
        elif isinstance(block, dict) and block.get("type") == "text":
            txt = block.get("text", "") or ""
            if txt:
                parts.append(txt)
    return "".join(parts)


# ---------------------------------------------------------------------------
# Singleton (contrato publico sin cambios)
# ---------------------------------------------------------------------------


_default_router: LLMRouter | None = None


def get_default_llm_router() -> LLMRouter:
    """Return (and lazily create) the default LLM router singleton."""
    global _default_router
    if _default_router is None:
        _default_router = LLMRouter()
    return _default_router


def reset_default_llm_router() -> None:
    """Test helper: fuerza recreacion en el siguiente ``get_default_llm_router``.

    Util para tests que monkeypatch ``ANTHROPIC_API_KEY`` o similares.
    """
    global _default_router
    _default_router = None
