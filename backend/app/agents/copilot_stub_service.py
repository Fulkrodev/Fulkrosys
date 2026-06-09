"""Copilot stub service · sub-atom 1.D.B.0.2 v3.10.

Extrae lógica stub response generation desde endpoint files (cleaner
separation · pattern OPS-045 14ª). Stubs current preserved behavior idéntico
(zero schema change · zero refactor frontend).

Wiring CopilotPersonaService:
- Stubs instantiate persona service per role (cliente · admin)
- Persona loaded at service init · verify YAML correct + boundaries ready
- Persona metadata NOT used yet en response generation (stubs return canned
  templates per action_id)
- Cuando 1.D.B.1+.2 promote LLM real · solo cambia code path en stub endpoint
  (use persona.render_system_prompt + invoke LLM via AgentBase pattern existing)

Sostiene:
- R29 (cliente templates sin coercitive · audit pre-commit empírico)
- R30 (admin templates asume cero ENS Marcos)
- R1 (NO decisiones normativas LLM · stub solo conversational helper)
"""
from __future__ import annotations

from typing import Any, Literal

from backend.app.agents.copilot_persona_service import CopilotPersonaService


# ════════════════════════════════════════════════════════════════════
# Admin stub templates (1.C.D.B.3 v3.8 preserved + cleaner separation)
# ════════════════════════════════════════════════════════════════════


ADMIN_ACTION_LITERAL = Literal[
    "que_hago",
    "explica_paso",
    "draft_email",
    "briefing_reunion",
    "chat_send",
]


_ADMIN_STUB_TEMPLATES: dict[str, str] = {
    "que_hago": (
        "Próximo step {project_or_generic}: {step_or_generic}. "
        "{action_hint} (LLM completo disponible en breve · próximo sprint)"
    ),
    "explica_paso": (
        "{step_or_generic} es obligatorio según ENS Anexo II "
        "(referencias contextualizadas según los tooltips_ens del template). "
        "Sin completarlo · auditor ENAC marca no conformidad. "
        "(LLM completo en breve · próximo sprint)"
    ),
    "draft_email": (
        "Para redactar emails contextualizados con datos cliente · activaremos "
        "el copiloto LLM completo próximamente. Por ahora puedes usar las "
        "plantillas E-XXX disponibles en el módulo Documentos del cliente."
    ),
    "briefing_reunion": (
        "Briefing para reunión {project_or_generic}: status fase {fase_or_generic} · "
        "próximo step {step_or_generic} · revisar progreso semanal + bloqueos + "
        "validaciones pendientes. (LLM completo en breve)"
    ),
    "chat_send": (
        "El chat conversacional estará disponible cuando se active el copiloto LLM "
        "completo (próximo sprint 1.D.B.2). Por ahora · usa las Acciones rápidas del "
        "panel para obtener respuestas contextualizadas."
    ),
}


# ════════════════════════════════════════════════════════════════════
# Client stub templates (1.C.D.C.3 v3.8 preserved · R29 sostener empírico)
# ════════════════════════════════════════════════════════════════════


CLIENT_ACTION_LITERAL = Literal[
    "que_hago",
    "porque_importa",
    "explica_concepto",
    "necesito_ayuda",
    "chat_send",
]


_CLIENT_STUB_TEMPLATES: dict[str, str] = {
    "que_hago": (
        "Tu siguiente paso es {step_or_generic}. Si tienes dudas sobre cómo "
        "abordarlo · estoy aquí para explicarte. Sin prisa · avanzamos a tu ritmo."
    ),
    "porque_importa": (
        "{step_or_generic} es importante porque es parte del Esquema Nacional "
        "de Seguridad (ENS) · las reglas oficiales para trabajar con la "
        "Administración Pública. Cada paso encaja como una pieza del puzle · "
        "todos juntos certifican que tu empresa cuida la información correctamente."
    ),
    "explica_concepto": (
        "Buena pregunta · {concepto_or_generic} es un término que aparece a "
        "menudo en ENS. Cuando se active el asistente completo · te lo "
        "explicaré con palabras normales · sin jerga consultora. Por ahora · "
        "Marcos puede aclarártelo directamente desde el chat."
    ),
    "necesito_ayuda": (
        "Claro · estoy aquí para ayudarte. Cuando se active el asistente "
        "completo · podré responder cualquier duda ENS con tus datos. Mientras "
        "tanto · puedes usar las preguntas frecuentes de esta página o contactar "
        "a Marcos directamente desde el chat. No hay prisa."
    ),
    "chat_send": (
        "Esta conversación estará disponible muy pronto · cuando se active el "
        "asistente completo. Por ahora · usa los botones de Acciones rápidas "
        "para preguntas habituales · o escribe a Marcos desde el chat para "
        "dudas concretas. Aquí seguimos cuando me necesites."
    ),
}


# ════════════════════════════════════════════════════════════════════
# Stub services (instantiate CopilotPersonaService · ready swap-in)
# ════════════════════════════════════════════════════════════════════


class AdminCopilotStubService:
    """Stub service admin · persona loaded ready swap-in 1.D.B.2 LLM real."""

    def __init__(self) -> None:
        # Persona loaded at init · verifica YAML correct + raises early si
        # catalog inválido. Service ready cuando 1.D.B.2 promote LLM real.
        self.persona_service = CopilotPersonaService("admin")

    def generate_stub_response(
        self,
        action_id: str,
        *,
        project_nombre: str | None = None,
        step_template_id: str | None = None,
        step_title: str | None = None,
        fase_actual: str | None = None,
    ) -> tuple[str, str | None]:
        """Genera stub response text + next_action_hint per action_id.

        Returns (response_text, next_action_hint).
        """
        template = _ADMIN_STUB_TEMPLATES.get(
            action_id, _ADMIN_STUB_TEMPLATES["chat_send"],
        )

        project_or_generic = (
            f'"{project_nombre}"' if project_nombre else "del cliente actual"
        )
        step_or_generic = (
            f'"{step_title}"' if step_title else "el sub-paso actual"
        )
        fase_or_generic = fase_actual or "actual"

        # action_hint específico por acción
        if action_id == "que_hago" and step_template_id:
            action_hint = (
                "Te ayudo a redactar email convocatoria o briefing detallado si "
                "lo necesitas."
            )
        elif action_id == "que_hago":
            action_hint = "Te ayudo a redactar contexto si lo necesitas."
        else:
            action_hint = ""

        response_text = template.format(
            project_or_generic=project_or_generic,
            step_or_generic=step_or_generic,
            fase_or_generic=fase_or_generic,
            action_hint=action_hint,
        )

        next_hint: str | None = None
        if action_id == "que_hago" and step_title:
            next_hint = "Marca el sub-paso completo cuando esté hecho"

        return response_text, next_hint

    @property
    def persona_metadata(self) -> dict[str, Any]:
        """Persona metadata · útil para debugging/logging · NO exposed in API."""
        return {
            "role": self.persona_service.role,
            "model_recommended": self.persona_service.model,
            "temperature": self.persona_service.temperature,
            "max_tokens": self.persona_service.max_tokens,
            "citations_required": self.persona_service.citations_required,
        }


class ClientCopilotStubService:
    """Stub service cliente · persona loaded ready swap-in 1.D.B.1 LLM real.

    R29 sostener empírico · templates audit-checked NO coercitive strings.
    """

    def __init__(self) -> None:
        self.persona_service = CopilotPersonaService("cliente")

    def generate_stub_response(
        self,
        action_id: str,
        *,
        step_title: str | None = None,
        concepto: str | None = None,
    ) -> tuple[str, str | None]:
        """Genera stub response text + next_action_hint per action_id."""
        template = _CLIENT_STUB_TEMPLATES.get(
            action_id, _CLIENT_STUB_TEMPLATES["chat_send"],
        )

        step_or_generic = (
            f'"{step_title}"' if step_title else "el paso actual"
        )
        concepto_or_generic = (
            f'"{concepto}"' if concepto else "ese término"
        )

        response_text = template.format(
            step_or_generic=step_or_generic,
            concepto_or_generic=concepto_or_generic,
        )

        next_hint: str | None = None
        if action_id == "que_hago" and step_title:
            next_hint = "Cuando termines · márcalo como hecho"

        return response_text, next_hint

    @property
    def persona_metadata(self) -> dict[str, Any]:
        return {
            "role": self.persona_service.role,
            "model_recommended": self.persona_service.model,
            "temperature": self.persona_service.temperature,
            "max_tokens": self.persona_service.max_tokens,
            "citations_required": self.persona_service.citations_required,
        }


# ════════════════════════════════════════════════════════════════════
# Module-level singletons (lightweight · persona loaded once at import)
# ════════════════════════════════════════════════════════════════════


_admin_stub_service: AdminCopilotStubService | None = None
_client_stub_service: ClientCopilotStubService | None = None


def get_admin_stub_service() -> AdminCopilotStubService:
    """Lazy singleton · evita load YAML en imports recursivos pytest."""
    global _admin_stub_service
    if _admin_stub_service is None:
        _admin_stub_service = AdminCopilotStubService()
    return _admin_stub_service


def get_client_stub_service() -> ClientCopilotStubService:
    """Lazy singleton."""
    global _client_stub_service
    if _client_stub_service is None:
        _client_stub_service = ClientCopilotStubService()
    return _client_stub_service
