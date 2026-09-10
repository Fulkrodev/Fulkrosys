"""AgentBase — abstract base class for all 27 FULKRO agents.

Each agent:
1. Has an immutable system prompt (COMMON_HEADER + SPECIFIC_PROMPT).
2. Builds project context if project_id is provided.
3. Calls the LLM via the existing router (sync, wrapped in executor).
4. Post-processes the response (JSON parse if structured_output).
5. Logs the interaction best-effort.
6. Returns a normalized dict.

BLOQUE D · D1 (2026-09-10) · lo que ya NO hace
----------------------------------------------
Hasta este cambio, cuando la llamada al modelo fallaba, `_call_llm` devolvia
una respuesta fabricada y `_log_interaction` la grababa con `status="success"`,
`completion_tokens=50` (constante inventada) y un `cost_usd` calculado sobre
esos tokens inventados. Es decir: un fallo de red se contabilizaba como una
llamada correcta y sumaba dinero al coste agregado.

Ahora:

* Fallo del proveedor  -> `LLMCallFailed` se PROPAGA. Antes de propagar se graba
  una fila con `status="error"`, tokens NULL y `cost_usd` NULL.
* Sin `ANTHROPIC_API_KEY` -> se conserva el modo degradado (la suite entera
  depende de el; ver `tests/conftest.py`), pero la fila se graba con
  `status="mock"`, `cost_usd=0` y tokens NULL.
* Ninguna agregacion de coste ni de tokens suma filas `mock` ni `error`
  (`copilot_rate_limit.py` y `m_observability/llm_observability_service.py`
  filtran por `status`).

La asimetria entre la FILA (tokens NULL) y el DICCIONARIO que devuelve
`invoke()` (tokens 0) esta justificada y medida en
`docs/adr/ADR-004-llamada-llm-fallida-no-es-exito.md`.
"""
import asyncio
import hashlib
import json
import logging
import re
import time
import uuid
from abc import ABC
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.prompts.common_header import COMMON_HEADER
from backend.app.config import get_settings

logger = logging.getLogger(__name__)


class LLMCallFailed(RuntimeError):
    """La llamada al modelo fallo.

    Se propaga a quien invoco al agente. NO se sustituye por una respuesta
    fabricada: un agente que no ha hablado con el modelo no tiene nada que
    devolver, y devolver texto inventado con `status="success"` era el defecto
    que este bloque cierra (D1).
    """


_MODEL_ALIAS_MAP = {
    "sonnet-4.5": "claude-sonnet-4-5",
    "sonnet-4.6": "claude-sonnet-4-6",
    "opus-4": "claude-opus-4-6",
    "opus-4.6": "claude-opus-4-6",
    "opus-4.7": "claude-opus-4-7",
    "haiku-4.5": "claude-haiku-4-5",
}


def _resolve_model(alias: str) -> str:
    """Map agent registry alias to the real LiteLLM model name."""
    return _MODEL_ALIAS_MAP.get(alias, alias)


class AgentBase(ABC):
    """Abstract base class for all FULKRO agents."""

    AGENT_ID: int = 0
    AGENT_NAME: str = "Base"
    MODEL: str = "sonnet-4.5"
    TEMPERATURE: float = 0.15
    MAX_TOKENS: int = 4096
    SPECIFIC_PROMPT: str = ""
    # Activa cache_control ephemeral sobre el system_prompt.
    # Util cuando (a) system es largo (>1k tokens) y (b) el agente recibe
    # varias llamadas consecutivas dentro del TTL 5 min (p.ej. A18 panel
    # live K.4 con updates cada 30-60s). Primer call paga ~1.25x base;
    # subsiguientes pagan ~0.1x base + caen ~70-80% de latencia.
    ENABLE_PROMPT_CACHING: bool = False

    def __init__(self):
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        return f"{COMMON_HEADER}\n\n---\n\n{self.SPECIFIC_PROMPT}"

    async def invoke(
        self,
        db: AsyncSession,
        project_id: Optional[uuid.UUID] = None,
        user_message: str = "",
        context: Optional[dict] = None,
        structured_output: bool = False,
        extra_context: str = "",
        feature_override: Optional[str] = None,
    ) -> dict:
        start = time.monotonic()

        project_context = ""
        if project_id is not None:
            try:
                project_context = await self._build_project_context(db, project_id)
            except Exception as exc:
                logger.debug("Project context build failed for agent %s: %s", self.AGENT_ID, exc)
                project_context = ""

        full_user_message = ""
        if project_context:
            full_user_message += f"CONTEXTO DEL PROYECTO:\n{project_context}\n\n"
        if extra_context:
            full_user_message += f"CONTEXTO ADICIONAL:\n{extra_context}\n\n"
        if context:
            full_user_message += (
                "DATOS ESTRUCTURADOS:\n"
                + json.dumps(context, ensure_ascii=False, indent=2, default=str)
                + "\n\n"
            )
        if structured_output:
            full_user_message += (
                "INSTRUCCION: Responde EXCLUSIVAMENTE en JSON valido sin markdown ni explicaciones.\n\n"
            )
        full_user_message += user_message or ""

        try:
            llm_response = await self._call_llm(
                system_prompt=self.system_prompt,
                user_message=full_user_message,
                model=self.MODEL,
                temperature=self.TEMPERATURE,
                max_tokens=self.MAX_TOKENS,
            )
        except Exception as exc:
            # D1: el fallo se registra COMO FALLO y se propaga. La fila queda con
            # tokens NULL y cost_usd NULL: no hubo llamada, no hay nada que medir.
            latency_ms = int((time.monotonic() - start) * 1000)
            await self._log_interaction(
                db, project_id, full_user_message,
                {"model": self.MODEL, "text": ""}, latency_ms,
                feature_override=feature_override,
                status="error",
                error_message=f"{type(exc).__name__}: {exc}",
            )
            raise

        text_out = llm_response.get("text", "")
        parsed = self._parse_json_response(text_out) if structured_output else None
        citations = self._extract_citations(text_out)

        latency_ms = int((time.monotonic() - start) * 1000)
        await self._log_interaction(
            db, project_id, full_user_message, llm_response, latency_ms,
            feature_override=feature_override,
            status="mock" if llm_response.get("mock") else "success",
        )

        return {
            "agent_id": self.AGENT_ID,
            "agent_name": self.AGENT_NAME,
            "response": text_out,
            "parsed": parsed,
            "model": llm_response.get("model", self.MODEL),
            "tokens_input": llm_response.get("tokens_input", 0),
            "tokens_output": llm_response.get("tokens_output", 0),
            "cache_creation_input_tokens": llm_response.get(
                "cache_creation_input_tokens", 0
            ),
            "cache_read_input_tokens": llm_response.get(
                "cache_read_input_tokens", 0
            ),
            "latency_ms": latency_ms,
            "citations": citations,
            "project_id": str(project_id) if project_id else None,
            # D1: False cuando la respuesta NO viene del modelo (modo degradado
            # sin clave). Quien publique estas cifras tiene que poder distinguir
            # "cero tokens porque no hubo llamada" de "cero tokens medidos".
            "tokens_medidos": not llm_response.get("mock", False),
            "mock": bool(llm_response.get("mock", False)),
        }

    async def _build_project_context(self, db: AsyncSession, project_id: uuid.UUID) -> str:
        """Default context: minimal project row. Subclasses may override."""
        from sqlalchemy import text as sql_text

        result = await db.execute(
            sql_text(
                "SELECT nombre, fase, categoria_objetivo, estado "
                "FROM projects WHERE id = :pid"
            ),
            {"pid": str(project_id)},
        )
        row = result.fetchone()
        if row:
            return (
                f"Proyecto: {row[0]}\n"
                f"Fase actual: {row[1]}\n"
                f"Categoria objetivo: {row[2]}\n"
                f"Estado: {row[3]}"
            )
        return ""

    async def _call_llm(
        self,
        system_prompt: str,
        user_message: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> dict:
        """Llama al modelo. Sin clave, modo degradado explicito. Si falla, revienta.

        Dos caminos y solo dos:

        * Sin `ANTHROPIC_API_KEY` -> respuesta de modo degradado, marcada con
          `mock=True` y con tokens a 0 (no hubo llamada: cero es la cifra
          correcta, no una estimacion). La fila del log queda `status="mock"`.
        * Con clave y la llamada falla -> `LLMCallFailed`. NO se fabrica
          respuesta. Antes, este camino devolvia texto inventado con 50 tokens
          de salida constantes y `status="success"` (D1).
        """
        api_key = get_settings().anthropic_api_key.get_secret_value().strip()
        if not api_key:
            return self._mock_response(model, system_prompt, user_message)

        try:
            from backend.app.core.ai.llm_router import get_default_llm_router

            real_model = _resolve_model(model)
            router = get_default_llm_router()
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ]
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(
                None,
                lambda: router.complete(
                    messages=messages,
                    model=real_model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    enable_prompt_caching=self.ENABLE_PROMPT_CACHING,
                ),
            )
            return {
                "text": resp.content,
                "tokens_input": resp.prompt_tokens,
                "tokens_output": resp.completion_tokens,
                "cache_creation_input_tokens": resp.cache_creation_input_tokens,
                "cache_read_input_tokens": resp.cache_read_input_tokens,
                "model": resp.model,
            }
        except Exception as exc:
            logger.warning(
                "LLM call failed for agent %s (%s): %s",
                self.AGENT_ID, self.AGENT_NAME, exc,
            )
            raise LLMCallFailed(
                f"Agente {self.AGENT_ID} ({self.AGENT_NAME}): la llamada a "
                f"{_resolve_model(model)} fallo ({type(exc).__name__}: {exc})."
            ) from exc

    def _mock_response(
        self, model: str, system_prompt: str, user_message: str
    ) -> dict:
        """Modo degradado SIN clave de API. Cero llamadas, cero cifras inventadas.

        Los tokens valen 0 porque no hubo llamada al proveedor: 0 es el dato
        correcto, no una estimacion. Lo que se elimino aqui (D1) fue el
        `tokens_output: 50` constante y el `tokens_input` contado por palabras,
        que se colaban en `cost_usd` como si fueran medidas reales.

        El diccionario lleva `mock=True` para que `_log_interaction` grabe la
        fila con `status="mock"`, `cost_usd=0` y tokens NULL.
        """
        return {
            "text": (
                f"[MOCK] Agent {self.AGENT_ID} ({self.AGENT_NAME}). "
                f"Model: {model}. Message length: {len(user_message)}. "
                "Sin ANTHROPIC_API_KEY: no se ha llamado al modelo."
            ),
            "tokens_input": 0,
            "tokens_output": 0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
            "model": model,
            "mock": True,
        }

    def _parse_json_response(self, text: str) -> Optional[dict]:
        if not text:
            return None
        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        try:
            return json.loads(cleaned)
        except (json.JSONDecodeError, ValueError):
            return None

    def _extract_citations(self, text: str) -> list:
        if not text:
            return []
        matches = re.findall(r"\[([^\]]+)\]", text)
        keywords = (
            "RD ", "CCN", "STIC", "Anexo", "Art.", "medida",
            "op.", "org.", "mp.", "MAGERIT",
        )
        return [m for m in matches if any(kw in m for kw in keywords)]

    async def _log_interaction(
        self,
        db: AsyncSession,
        project_id: Optional[uuid.UUID],
        user_message: str,
        response: dict,
        latency_ms: int,
        feature_override: Optional[str] = None,
        status: str = "success",
        error_message: Optional[str] = None,
    ) -> None:
        """Persist interaction to llm_interaction_log (best-effort).

        The write is wrapped in a SAVEPOINT so a logging failure does not
        poison the caller's transaction.

        D1 · `status` manda sobre lo que se graba:

        ==========  =====================  ==========  ==========================
        status      cuando                 cost_usd    prompt/completion/total
        ==========  =====================  ==========  ==========================
        success     respuesta del modelo   calculado   medidos por el proveedor
        mock        sin clave de API       0           NULL (no hubo llamada)
        error       la llamada fallo       NULL        NULL (no hubo respuesta)
        ==========  =====================  ==========  ==========================

        Las filas `mock` y `error` quedan fuera de toda suma de coste y de
        tokens; el filtro vive en las propias consultas
        (`copilot_rate_limit.py`, `llm_observability_service.py`) y ademas la
        migracion `llm_log_status_no_finge_exito_001` impone por CHECK que una
        fila `mock`/`error` no pueda llevar coste distinto de 0/NULL.
        """
        try:
            from backend.app.models.knowledge import LLMInteractionLog

            medido = status == "success"
            tokens_in = int(response.get("tokens_input", 0) or 0) if medido else None
            tokens_out = int(response.get("tokens_output", 0) or 0) if medido else None
            cached_in = int(response.get("cache_read_input_tokens", 0) or 0)
            prompt_hash = hashlib.sha256(
                user_message.encode("utf-8", errors="ignore")
            ).hexdigest()
            slug = re.sub(r"[^a-z0-9]+", "_", self.AGENT_NAME.lower()).strip("_")
            feature_slug = f"agent_{self.AGENT_ID:02d}_{slug}"
            # §4.5 · feature_override permite distinguir la vía cliente inline
            # ("inline_cliente_*") de las ejecuciones backend del mismo agente
            # ("agent_XX_*") → el cap cliente cuenta SÓLO lo iniciado por el cliente.
            feature_used = (feature_override or feature_slug)[:64]
            # §4.5 · poblar cost_usd (antes None → el cap mensual de coste sumaba 0).
            from backend.app.core.ai.pricing import compute_cost_usd
            model_id = str(response.get("model", self.MODEL))[:128]
            if status == "success":
                coste = compute_cost_usd(model_id, tokens_in, tokens_out, cached_in)
            elif status == "mock":
                coste = 0  # no hubo llamada: cero medido, no cero estimado
            else:
                coste = None  # error: no se sabe, y no se inventa
            entry = LLMInteractionLog(
                project_id=project_id,
                feature=feature_used,
                model=model_id,
                prompt_hash=prompt_hash,
                prompt_preview=user_message[:500],
                response_preview=str(response.get("text", ""))[:500],
                prompt_tokens=tokens_in,
                completion_tokens=tokens_out,
                total_tokens=(
                    (tokens_in + tokens_out) if medido else None
                ),
                cached_input_tokens=cached_in,
                cost_usd=coste,
                latency_ms=latency_ms,
                status=status,
                error_message=error_message,
            )
            try:
                async with db.begin_nested():
                    db.add(entry)
                    await db.flush()
            except Exception as exc:
                logger.debug("LLM log flush failed for agent %s: %s", self.AGENT_ID, exc)
        except Exception as exc:
            logger.debug("LLM log setup failed for agent %s: %s", self.AGENT_ID, exc)
