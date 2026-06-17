"""Data types for Agent 14 — ENS Copilot."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PageContext:
    """Active page context to enrich the system prompt.

    Optional fields supplied by the frontend so the copilot knows where the
    user is operating (URL, motor, fase, client). When ``client_id`` is
    present it overrides the ``client_id`` derived from ``project_id`` for
    the M30 contacts injection.

    Sesión 3B-2B.8 CLUSTER 2 Phase 2E · ``ens_category`` permite al system
    prompt tailorear respuestas per categoría del proyecto cliente (BÁSICA
    simpler · MEDIA audit-ready · ALTA detailed SOC/DR). Resolved backend
    desde ``projects.categoria_objetivo`` en portal_copiloto_chat.
    """

    url: Optional[str] = None
    client_id: Optional[str] = None
    project_phase: Optional[str] = None
    active_motor: Optional[str] = None
    ens_category: Optional[str] = None
    # Sesión 3B-2B.8 CLUSTER 4 Phase 4A · coach mode context injection
    # Cuando coach_mode=True · system prompt inject coach guidance R29
    # reuse compute_workflow_state next_cliente_actions.
    coach_mode: bool = False
    coach_current_phase: Optional[str] = None
    coach_pending_action: Optional[str] = None
    # 2026-06-09 · pantalla activa (pathname Next.js) para el lookup del
    # screen_references_catalog por rol → el copiloto referencia los BOTONES
    # concretos de la página actual. Si None, el builder cae a ``url``.
    current_screen: Optional[str] = None
    # 2026-06-09 · bloque pre-formateado "Estado actual del proyecto" compuesto
    # por copilot_project_state.build_project_state_block (compute_workflow_state
    # serializado · role-filtered R29/R30). Se inyecta tal cual en el system
    # prompt. Vacío/None = sin estado (degradación grácil).
    project_state: Optional[str] = None


@dataclass
class CopilotQuery:
    """Input query for the ENS copilot."""

    question: str
    project_id: Optional[str] = None
    requested_model: Optional[str] = None
    max_tokens: Optional[int] = None
    page_context: Optional[PageContext] = None
    # 2026-06-09 · rol del portal que invoca (``cliente`` | ``admin``).
    # Selecciona el bloque de conocimiento de plataforma + el screen catalog
    # correcto en _build_system_prompt. Default ``cliente`` (variante segura).
    role: str = "cliente"
    # E-4 · memoria entre conversaciones: turnos previos del MISMO hilo,
    # formato [{"role": "user"|"assistant", "content": str}, ...] cronológico.
    # Se insertan entre el system prompt y la pregunta actual. Vacío = sin
    # historial (paths persona sin conversation_id → amnesia graceful).
    history: list[dict] = field(default_factory=list)


@dataclass
class CopilotResponse:
    """Structured response from the ENS copilot."""

    answer: str
    citations_found: list[str] = field(default_factory=list)
    chunk_ids_used: list[str] = field(default_factory=list)
    not_in_corpus: bool = False
    low_grounding_confidence: bool = False
    model_used: str = ""
    tokens_input: int = 0
    tokens_output: int = 0
    latency_ms: int = 0
    interaction_log_id: Optional[int] = None
    # S14 · acciones sugeridas deterministas (R1 · sin LLM). Cada entry:
    # {"id": str, "label": str, "kind": "navigate"|"invoke_agent"|
    #  "generate_doc"|"open_magic_link", "payload": {...}}. El frontend
    # (ActionChip) las ejecuta de verdad. Vacío = sin sugerencias.
    actions: list[dict] = field(default_factory=list)
