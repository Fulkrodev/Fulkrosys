"""CopilotClienteLLMService · sub-atom 1.D.B.1 v3.11.

LLM real swap-in cliente · sostiene OPS-045 14ª-15ª aplicación consecutiva
(reuse AgentBase 295 LOC + CopilotPersonaService 1.D.B.0.1 + persona YAML
Anexo M materializado + AgentBase MOCK fallback automatic).

Endpoint `/api/v1/client-portal/copilot/chat` cambia code path:
  - Si LLM enabled (anthropic_api_key configurado) → use this service
  - Si LLM disabled o LLM call fails → graceful fallback to stub service
    (NO break UX cliente)

Sostiene R1 inviolable: LLM SOLO conversacional · NO decisiones normativas
(A21 determinista cubre detección discrepancias).

Sostiene R29 (cliente sin presión coercitiva) empíricamente:
  - System prompt persona cliente enforces R29 in YAML
  - Post-response boundary check verify NO coercitive patterns
  - Si LLM viola boundary · fallback to stub (defensive)

Schema response IDÉNTICO ClientCopilotStubResponse · zero refactor frontend.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.copilot_persona_service import CopilotPersonaService
from backend.app.agents.copilot_stub_service import get_client_stub_service
from backend.app.config import get_settings

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# R29 boundary enforcement (post-response audit)
# ════════════════════════════════════════════════════════════════════


# Patrones coercitivos prohibidos R29 sostener empíricamente.
# Si LLM response contiene cualquiera · fallback stub (defensive).
_R29_COERCITIVE_PATTERNS: tuple[str, ...] = (
    "llevas",  # "llevas X días sin..."
    "deadline urgente",
    "se acaba el tiempo",
    "se te acaba",
    "tienes que ahora",
    "ya deberías",
    "estás retrasado",
    "es urgente que",
    "fecha límite",  # generic "deadline" en español
    "plazo se cumple",
)

# Patrones admin lingo prohibidos cliente-facing (R30 inverso).
_ADMIN_LINGO_PATTERNS: tuple[str, ...] = (
    "audit trail",
    "evidence_type_id",
    "classifier_score",
    "rbac",
    "tenant context",
    "RLS",
)


def check_r29_boundaries(response_text: str) -> tuple[bool, str | None]:
    """Verifica respuesta NO contiene patrones coercitivos R29.

    Returns (is_valid, violation_reason).
    """
    text_lower = response_text.lower()
    for pattern in _R29_COERCITIVE_PATTERNS:
        if pattern in text_lower:
            return False, f"R29 violation: coercitive pattern '{pattern}'"
    for pattern in _ADMIN_LINGO_PATTERNS:
        if pattern.lower() in text_lower:
            return False, f"R30-inverso violation: admin lingo '{pattern}'"
    return True, None


# ════════════════════════════════════════════════════════════════════
# Cliente LLM service · swap-in stub when LLM enabled
# ════════════════════════════════════════════════════════════════════


def llm_enabled() -> bool:
    """LLM enabled cuando anthropic_api_key configurado (production).

    Tests + CI sin api_key → AgentBase MOCK fallback (transparent).
    Pero para 1.D.B.1 endpoint queremos siempre intentar LLM call si
    api_key existe · si NO existe · fallback DIRECTO a stub (skip LLM).
    """
    try:
        key = get_settings().anthropic_api_key.get_secret_value().strip()
        return bool(key)
    except Exception:
        return False


class CopilotClienteLLMService:
    """LLM real cliente · wraps AgentBase pattern + CopilotPersonaService.

    Pattern reuse OPS-045: NO duplicar LLM infra (router/cache/log existing
    en AgentBase). Solo añadir persona-aware system prompt + R29 boundary
    enforcement + graceful fallback.
    """

    def __init__(self) -> None:
        self.persona_service = CopilotPersonaService("cliente")
        self.stub_service = get_client_stub_service()

    async def build_context(
        self,
        db: AsyncSession,
        project_id: uuid.UUID | None,
        step_template_id: str | None = None,
        step_title: str | None = None,
        fase_actual: str | None = None,
    ) -> dict[str, Any]:
        """Build cliente context dict para system prompt rendering."""
        return await self.persona_service.build_client_context(
            db,
            project_id,
            step_template_id=step_template_id,
            step_title=step_title,
            fase_actual=fase_actual,
        )

    async def generate_response(
        self,
        db: AsyncSession,
        action_id: str,
        *,
        project_id: uuid.UUID | None,
        question: str | None,
        step_template_id: str | None,
        step_title: str | None,
        fase_actual: str | None,
        concepto: str | None,
        history: list[dict] | None = None,
    ) -> tuple[str, str | None, bool]:
        """Genera respuesta LLM real cliente · R29-safe.

        Returns (response_text, next_action_hint, is_stub_fallback).

        Flow:
          1. Build context (project + step + 19 dims)
          2. Render system prompt persona cliente
          3. Build user_message según action_id + question
          4. Call LLM via AgentBase pattern (router + log)
          5. Boundary check R29 post-response
          6. Si LLM fail o boundary violation → fallback stub graceful
        """
        # Ejecutable 8 OLA 0 (FR-2 · F-13-02 residual): PI guard en el path
        # persona cliente (chat libre del usuario EXTERNO). Mirror del path RAG
        # (agent_14_copiloto/service.py:383). Bloquea jailbreak / extracción de
        # system prompt ANTES de llegar al LLM. Solo aplica a texto libre real.
        if question:
            from backend.app.security.llm_prompt_injection_guard import (
                sanitize_user_input,
            )
            _pi = sanitize_user_input(question)
            if _pi.should_block:
                logger.warning(
                    "Copiloto cliente PI guard blocked input · categorias=%s",
                    [v.category for v in _pi.violations],
                )
                return (
                    "Lo siento, no puedo procesar esa solicitud. Si tienes una "
                    "duda sobre tu proceso ENS, reformúlala con normalidad y te "
                    "ayudo encantado.",
                    None,
                    True,
                )

        # Defensive: si LLM disabled completamente → use stub directo
        if not llm_enabled():
            text, hint = self.stub_service.generate_stub_response(
                action_id,
                step_title=step_title,
                concepto=concepto,
            )
            return text, hint, True

        try:
            context = await self.build_context(
                db, project_id, step_template_id, step_title, fase_actual,
            )
            system_prompt = self.persona_service.render_system_prompt(context)
            # Pasada 18: auto-conocimiento de plataforma (uso del portal · cita
            # [Fulkro Plataforma]). Persona YAML cubre tono/boundaries (R29).
            from backend.app.agents.system_knowledge import (
                SYSTEM_KNOWLEDGE_CLIENTE,
            )
            system_prompt = system_prompt + "\n\n" + SYSTEM_KNOWLEDGE_CLIENTE
            user_message = self._build_user_message(
                action_id, question, step_title, concepto,
            )
            llm_text = await self._call_llm(
                system_prompt, user_message, db, project_id, history=history,
            )

            # R29 boundary enforcement
            ok, violation = check_r29_boundaries(llm_text)
            if not ok:
                logger.warning(
                    "Copiloto cliente R29 violation detected · fallback stub: %s",
                    violation,
                )
                text, hint = self.stub_service.generate_stub_response(
                    action_id,
                    step_title=step_title,
                    concepto=concepto,
                )
                return text, hint, True

            next_hint = self._suggest_next_hint(action_id, step_title)
            return llm_text, next_hint, False

        except Exception as exc:
            logger.warning(
                "Copiloto cliente LLM call failed · fallback stub: %s", exc,
            )
            text, hint = self.stub_service.generate_stub_response(
                action_id,
                step_title=step_title,
                concepto=concepto,
            )
            return text, hint, True

    def _build_user_message(
        self,
        action_id: str,
        question: str | None,
        step_title: str | None,
        concepto: str | None,
    ) -> str:
        """User message LLM según action_id · friendly cliente tone."""
        # Defense-in-depth (FRENTE E hardening): step_title/concepto se
        # neutralizan antes de interpolarlos en el prompt (el PI-guard solo
        # cubre `question`).
        from backend.app.security.llm_prompt_injection_guard import (
            neutralize_context_value,
        )
        step_title = neutralize_context_value(step_title)
        concepto = neutralize_context_value(concepto)
        if action_id == "chat_send" and question:
            return question
        if action_id == "que_hago":
            step_ref = f' "{step_title}"' if step_title else ""
            return (
                f"¿Qué tengo que hacer ahora en mi proceso ENS{step_ref}? "
                "Explícamelo paso a paso con tono amable y sin jerga técnica."
            )
        if action_id == "porque_importa":
            step_ref = f' "{step_title}"' if step_title else " mi paso actual"
            return (
                f"¿Por qué es importante{step_ref}? Explícamelo en términos "
                "sencillos con primer principios · sin jerga."
            )
        if action_id == "explica_concepto":
            concepto_ref = f' "{concepto}"' if concepto else " el término que no entiendo"
            return (
                f"Explícame{concepto_ref} con palabras normales · sin jerga "
                "consultora. Una analogía cotidiana ayuda."
            )
        if action_id == "necesito_ayuda":
            return (
                "Necesito ayuda con mi proceso ENS · ¿puedes orientarme con "
                "tono amable · sin presión?"
            )
        return question or "Hola · ¿puedes ayudarme?"

    async def _call_llm(
        self,
        system_prompt: str,
        user_message: str,
        db: AsyncSession,
        project_id: uuid.UUID | None,
        history: list[dict] | None = None,
    ) -> str:
        """LLM call via existing pattern AgentBase-style · returns text.

        ``history`` (N6 · memoria entre conversaciones por cliente+proyecto) =
        turnos previos ``[{role, content}, ...]`` inyectados antes del actual.
        """
        from backend.app.core.ai.llm_router import get_default_llm_router
        import asyncio as _asyncio

        # Model alias resolution per AgentBase pattern existing
        model_alias = self.persona_service.model
        model_map = {
            "sonnet-4.5": "claude-sonnet-4-5",
            "sonnet-4.6": "claude-sonnet-4-6",
            "opus-4.7": "claude-opus-4-7",
            "haiku-4.5": "claude-haiku-4-5",
        }
        real_model = model_map.get(model_alias, model_alias)

        router = get_default_llm_router()
        messages = [
            {"role": "system", "content": system_prompt},
            *(history or []),
            {"role": "user", "content": user_message},
        ]
        loop = _asyncio.get_event_loop()
        resp = await loop.run_in_executor(
            None,
            lambda: router.complete(
                messages=messages,
                model=real_model,
                max_tokens=self.persona_service.max_tokens,
                temperature=self.persona_service.temperature,
                enable_prompt_caching=self.persona_service.enable_prompt_caching,
            ),
        )
        text = resp.content or ""

        # Best-effort log llm_interaction (m_observability integration)
        await self._log_interaction(
            db, project_id, user_message, text,
            resp.prompt_tokens, resp.completion_tokens, resp.model,
        )
        return text

    async def _log_interaction(
        self,
        db: AsyncSession,
        project_id: uuid.UUID | None,
        user_message: str,
        response_text: str,
        prompt_tokens: int,
        completion_tokens: int,
        model: str,
    ) -> None:
        """Log llm_interaction_log best-effort · NO break si falla."""
        try:
            import hashlib
            from backend.app.models.knowledge import LLMInteractionLog

            prompt_hash = hashlib.sha256(
                user_message.encode("utf-8", errors="ignore"),
            ).hexdigest()
            entry = LLMInteractionLog(
                project_id=project_id,
                feature="copilot_cliente_1d_b_1",
                model=str(model)[:128],
                prompt_hash=prompt_hash,
                prompt_preview=user_message[:500],
                response_preview=response_text[:500],
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                latency_ms=0,
                status="success",
            )
            try:
                async with db.begin_nested():
                    db.add(entry)
                    await db.flush()
            except Exception as exc:
                logger.debug("Copiloto cliente log flush failed: %s", exc)
        except Exception as exc:
            logger.debug("Copiloto cliente log setup failed: %s", exc)

    def _suggest_next_hint(
        self, action_id: str, step_title: str | None,
    ) -> str | None:
        """Friendly next hint · NO coercitivo · R29 sostener."""
        if action_id == "que_hago" and step_title:
            return "Cuando termines · márcalo como hecho"
        return None


# ════════════════════════════════════════════════════════════════════
# Module-level singleton (lazy load · evita catalog en imports recursivos)
# ════════════════════════════════════════════════════════════════════


_cliente_llm_service: CopilotClienteLLMService | None = None


def get_cliente_llm_service() -> CopilotClienteLLMService:
    """Lazy singleton · persona loaded once en primer use."""
    global _cliente_llm_service
    if _cliente_llm_service is None:
        _cliente_llm_service = CopilotClienteLLMService()
    return _cliente_llm_service
