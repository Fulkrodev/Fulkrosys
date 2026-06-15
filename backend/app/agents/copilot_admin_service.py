"""CopilotAdminLLMService · sub-atom 1.D.B.2 v3.11.

LLM real swap-in admin · sostiene OPS-045 16ª aplicación consecutiva
(pattern reuse 1.D.B.1 CopilotClienteLLMService + AgentBase + CopilotPersonaService).

Endpoint `/api/v1/admin/copilot/chat` cambia code path:
  - Si LLM enabled (anthropic_api_key configurado) → use this service Sonnet 4.6
  - Si LLM disabled → stub service directo
  - Si LLM call fails → graceful stub fallback
  - Si R30 boundary violation → DEFENSIVE ENRICH (NO full stub fallback ·
    admin tolera enrich · NO break UX cuando warning agregado)

Sostiene R1 inviolable: LLM SOLO conversacional · NO decisiones normativas
(A21 determinista cubre detección discrepancias).

Sostiene R30 (admin tutor cronológico asume cero ENS Marcos · explica
conceptos desde primer principios) empíricamente:
  - System prompt persona admin enforces R30 en YAML
  - Post-response check_r30_boundaries verifica NO assume ENS knowledge +
    NO jargon undefined + NO peer-dense
  - Defensive enrich (NO fallback total · admin sostiene latency Sonnet)

Schema response IDÉNTICO CopilotChatStubResponse · zero refactor frontend.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.copilot_cliente_service import llm_enabled
from backend.app.agents.copilot_persona_service import CopilotPersonaService
from backend.app.agents.copilot_stub_service import get_admin_stub_service

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# R30 boundary enforcement (admin tutor cronológico · audit post-response)
# ════════════════════════════════════════════════════════════════════


# Patrones "assume ENS knowledge" prohibidos R30 sostener (Marcos puede ser
# monkey-pilot · NO assume conocimiento previo). Si LLM viola · defensive
# enrich · NO full stub fallback (admin tolera).
_R30_ASSUME_PATTERNS: tuple[str, ...] = (
    "como ya sabes",
    "como conoces",
    "evidentemente",
    "obviamente",
    "claramente sabes",
    "ya conoces el rd",
    "ya conoces el ens",
    "como bien sabes",
    "te suena el art",
    "recordarás que",
)

# Jargon ENS undefined que debería tener glossary inline o explicación
# primer-principios. Acrónimos ENS comunes sin contexto.
_JARGON_UNDEFINED_TRIGGER_TERMS: tuple[str, ...] = (
    "DICAT",
    "DdA",
    "MAGERIT",
    "PCE",
    "CCN-STIC",
    "ENAC",
    "Anexo II",
    "RD 311/2022",
    "BCP-DRP",
)

# Phrases indicating explicit definition/explanation has been provided.
# Si jargon aparece junto a estos triggers · NO se considera undefined.
_DEFINITION_TRIGGERS: tuple[str, ...] = (
    "es decir",
    "que significa",
    "es el",
    "es la",
    "se refiere a",
    "consiste en",
    "(",  # parentheses commonly used for inline definition
    "se trata de",
    "primer principios",
    "primer-principios",
    "explicación:",
    "definición:",
    "viene de",
)


def check_r30_boundaries(response_text: str) -> tuple[bool, list[str]]:
    """Verifica respuesta admin NO viola R30 (assume ENS · jargon undefined).

    Returns (is_clean, list_violations). is_clean=True si 0 violations.
    is_clean=False con list violations triggers defensive enrich.

    Defensive: NO fallback total a stub (admin tolera enrich) · solo agregar
    nota tutor "Si necesitas más detalle sobre [X concepto] · pregúntame".
    """
    violations: list[str] = []
    text_lower = response_text.lower()

    # Check assume ENS knowledge patterns
    for pattern in _R30_ASSUME_PATTERNS:
        if pattern in text_lower:
            violations.append(f"assume_ens: '{pattern}'")
            break  # 1 violation suffices to enrich (NO spam multiple of same type)

    # Check jargon undefined · only flag si jargon usado SIN definition trigger nearby
    for jargon in _JARGON_UNDEFINED_TRIGGER_TERMS:
        if jargon in response_text:
            # Verifica si hay definition trigger en cercanía (~50 chars antes/después)
            jargon_idx = response_text.find(jargon)
            window_start = max(0, jargon_idx - 50)
            window_end = min(len(response_text), jargon_idx + 50)
            window = response_text[window_start:window_end].lower()
            has_definition = any(trig in window for trig in _DEFINITION_TRIGGERS)
            if not has_definition:
                violations.append(f"jargon_undefined: '{jargon}'")
                # Limit list growth · 1 unexplained jargon enough to trigger enrich
                break

    return len(violations) == 0, violations


def enrich_response_defensive(response_text: str, violations: list[str]) -> str:
    """Defensive enrich · agrega nota tutor cuando R30 violation detectada.

    NO modifica el response LLM original · solo agrega footer tutorial al final
    invitando Marcos a pedir detalle adicional (sostener "monkey-pilot friendly").
    """
    if not violations:
        return response_text
    footer = (
        "\n\n---\n"
        "💡 _Tip tutor: Si quieres que profundice en algún concepto ENS · "
        "pregúntame y te lo explico desde primer principios._"
    )
    return response_text + footer


# ════════════════════════════════════════════════════════════════════
# Admin LLM service · swap-in stub when LLM enabled
# ════════════════════════════════════════════════════════════════════


class CopilotAdminLLMService:
    """LLM real admin · wraps AgentBase pattern + CopilotPersonaService.

    Pattern reuse OPS-045 16ª: análogo CopilotClienteLLMService 1.D.B.1.
    Sostiene R30 (tutor cronológico · asume cero ENS Marcos).
    """

    def __init__(self) -> None:
        self.persona_service = CopilotPersonaService("admin")
        self.stub_service = get_admin_stub_service()

    async def build_context(
        self,
        db: AsyncSession,
        active_project_id: uuid.UUID | None = None,
        active_project_name: str | None = None,
        active_step_title: str | None = None,
        active_fase: str | None = None,
        current_screen: str | None = None,
        active_motor: str | None = None,
    ) -> dict[str, Any]:
        """Build admin context dict para system prompt rendering."""
        return await self.persona_service.build_admin_context(
            db,
            active_project_id=active_project_id,
            active_project_name=active_project_name,
            active_step_title=active_step_title,
            active_fase=active_fase,
            current_screen=current_screen,
            active_motor=active_motor,
        )

    async def generate_response(
        self,
        db: AsyncSession,
        action_id: str,
        *,
        project_id: uuid.UUID | None,
        project_nombre: str | None,
        question: str | None,
        step_template_id: str | None,
        step_title: str | None,
        fase_actual: str | None,
        current_screen: str | None = None,
        active_motor: str | None = None,
        history: list[dict] | None = None,
    ) -> tuple[str, str | None, bool]:
        """Genera respuesta LLM real admin · R30-safe defensive enrich.

        Returns (response_text, next_action_hint, is_stub_fallback).

        Flow:
          1. LLM disabled → stub directo
          2. Build context portfolio + active client si project_id
          3. Render system prompt persona admin
          4. Build user_message según action_id + question
          5. Call LLM Sonnet 4.6 via existing router
          6. R30 boundary check post-response
          7. Si violations → defensive enrich (NO full stub fallback ·
             admin tolera enrich)
          8. Si LLM exception → graceful stub fallback
        """
        # Ejecutable 8 OLA 0 (FR-2 · F-13-02 residual): PI guard en el path
        # persona admin. Mirror del path RAG (agent_14_copiloto/service.py:383).
        # Defensa en profundidad pre-LLM (bajo riesgo, admin único, pero cierra
        # la superficie persona que el RAG no cubría).
        if question:
            from backend.app.security.llm_prompt_injection_guard import (
                sanitize_user_input,
            )
            _pi = sanitize_user_input(question)
            if _pi.should_block:
                logger.warning(
                    "Copiloto admin PI guard blocked input · categorias=%s",
                    [v.category for v in _pi.violations],
                )
                return (
                    "No puedo procesar esa solicitud. Reformula la consulta "
                    "sobre el proyecto o la implantación ENS y te ayudo.",
                    None,
                    True,
                )

        if not llm_enabled():
            text, hint = self.stub_service.generate_stub_response(
                action_id,
                project_nombre=project_nombre,
                step_template_id=step_template_id,
                step_title=step_title,
                fase_actual=fase_actual,
            )
            return text, hint, True

        try:
            context = await self.build_context(
                db,
                active_project_id=project_id,
                active_project_name=project_nombre,
                active_step_title=step_title,
                active_fase=fase_actual,
                current_screen=current_screen,
                active_motor=active_motor,
            )
            system_prompt = self.persona_service.render_system_prompt(context)
            # Pasada 18: auto-conocimiento de plataforma (R30 tutor · cita
            # [Fulkro Plataforma]). Persona YAML cubre tono/boundaries.
            from backend.app.agents.system_knowledge import (
                SYSTEM_KNOWLEDGE_ADMIN,
            )
            system_prompt = system_prompt + "\n\n" + SYSTEM_KNOWLEDGE_ADMIN
            user_message = self._build_user_message(
                action_id, question, project_nombre, step_title, fase_actual,
            )
            llm_text = await self._call_llm(
                system_prompt, user_message, db, project_id, history=history,
            )

            # R30 boundary check + defensive enrich (NO full fallback)
            is_clean, violations = check_r30_boundaries(llm_text)
            if not is_clean:
                logger.info(
                    "Copiloto admin R30 violations detected · defensive enrich: %s",
                    violations,
                )
                enriched_text = enrich_response_defensive(llm_text, violations)
                next_hint = self._suggest_next_hint(action_id, step_title)
                return enriched_text, next_hint, False

            next_hint = self._suggest_next_hint(action_id, step_title)
            return llm_text, next_hint, False

        except Exception as exc:
            logger.warning(
                "Copiloto admin LLM call failed · fallback stub: %s", exc,
            )
            text, hint = self.stub_service.generate_stub_response(
                action_id,
                project_nombre=project_nombre,
                step_template_id=step_template_id,
                step_title=step_title,
                fase_actual=fase_actual,
            )
            return text, hint, True

    def _build_user_message(
        self,
        action_id: str,
        question: str | None,
        project_nombre: str | None,
        step_title: str | None,
        fase_actual: str | None,
    ) -> str:
        """User message LLM según action_id · tutor cronológico tone."""
        # Defense-in-depth (FRENTE E hardening): el nombre de proyecto y el
        # título de paso vienen de datos del proyecto · se neutralizan antes de
        # interpolarlos en el prompt (el PI-guard solo cubre `question`).
        from backend.app.security.llm_prompt_injection_guard import (
            neutralize_context_value,
        )
        project_nombre = neutralize_context_value(project_nombre)
        step_title = neutralize_context_value(step_title)
        client_ref = f' del cliente "{project_nombre}"' if project_nombre else ""
        step_ref = f' en el step "{step_title}"' if step_title else ""

        if action_id == "chat_send" and question:
            return question
        if action_id == "que_hago":
            return (
                f"¿Qué tengo que hacer ahora{client_ref}{step_ref}? "
                "Explícamelo paso a paso · asume que no tengo conocimiento "
                "ENS previo · enseña primer principios cuando uses jerga."
            )
        if action_id == "explica_paso":
            return (
                f"Explícame{step_ref}{client_ref} desde primer principios · "
                "qué es · por qué importa ENS · cómo se hace · qué evidencia "
                "documentar. Cita RD 311/2022 + CCN-STIC + Anexo II cuando "
                "aplique."
            )
        if action_id == "draft_email":
            return (
                f"Redacta un draft email{client_ref}{step_ref} para mandar al "
                "cliente · tono profesional + claro · explica paso a paso lo "
                "que necesito de ellos. NO send · solo draft para revisar."
            )
        if action_id == "briefing_reunion":
            return (
                f"Prepárame briefing para la reunión{client_ref}{step_ref} · "
                "status actual · progreso semanal · bloqueos · validaciones "
                "pendientes · sugerencias talking points."
            )
        return question or "Necesito ayuda con un cliente · oriéntame."

    async def _call_llm(
        self,
        system_prompt: str,
        user_message: str,
        db: AsyncSession,
        project_id: uuid.UUID | None,
        history: list[dict] | None = None,
    ) -> str:
        """LLM call admin via router · Sonnet 4.6 (vs Haiku cliente).

        ``history`` (N6 · memoria entre conversaciones por proyecto) = turnos
        previos ``[{role, content}, ...]`` inyectados ANTES del mensaje actual.
        """
        from backend.app.core.ai.llm_router import get_default_llm_router
        import asyncio as _asyncio

        # Model alias resolution
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
        """Log llm_interaction_log best-effort."""
        try:
            import hashlib
            from backend.app.models.knowledge import LLMInteractionLog

            prompt_hash = hashlib.sha256(
                user_message.encode("utf-8", errors="ignore"),
            ).hexdigest()
            from backend.app.core.ai.pricing import compute_cost_usd
            entry = LLMInteractionLog(
                project_id=project_id,
                feature="copilot_admin_1d_b_2",
                model=str(model)[:128],
                prompt_hash=prompt_hash,
                prompt_preview=user_message[:500],
                response_preview=response_text[:500],
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                cost_usd=compute_cost_usd(model, prompt_tokens, completion_tokens),
                latency_ms=0,
                status="success",
            )
            try:
                async with db.begin_nested():
                    db.add(entry)
                    await db.flush()
            except Exception as exc:
                logger.debug("Copiloto admin log flush failed: %s", exc)
        except Exception as exc:
            logger.debug("Copiloto admin log setup failed: %s", exc)

    def _suggest_next_hint(
        self, action_id: str, step_title: str | None,
    ) -> str | None:
        """Friendly admin next hint."""
        if action_id == "que_hago" and step_title:
            return "Marca el sub-paso completo cuando esté hecho"
        return None


# ════════════════════════════════════════════════════════════════════
# Module-level singleton
# ════════════════════════════════════════════════════════════════════


_admin_llm_service: CopilotAdminLLMService | None = None


def get_admin_llm_service() -> CopilotAdminLLMService:
    """Lazy singleton · persona loaded once en primer use."""
    global _admin_llm_service
    if _admin_llm_service is None:
        _admin_llm_service = CopilotAdminLLMService()
    return _admin_llm_service
