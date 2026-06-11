"""Client Copiloto stub endpoint · sub-atom 1.C.D.C.3 v3.8 → refactor 1.D.B.0.2 v3.10.

Endpoint placeholder /api/v1/client-portal/copilot/chat · dummy responses
ready para swap-in LLM real 1.D.B.1 (zero refactor cliente UI).

Schema response IDÉNTICO al admin stub 1.C.D.B.3 + LLM real 1.D.B.1 final · cliente
puede empezar a usar QuickActions inmediatamente con stub responses CALIDAD
tono friendly tutor paciente.

Refactor 1.D.B.0.2 v3.10: lógica template generation movida a
`backend/app/agents/copilot_stub_service.py` (cleaner separation · OPS-045
14ª). Stub service instantiates CopilotPersonaService("cliente") al init ·
persona YAML loaded + boundaries R29 ready · cuando 1.D.B.1 promote LLM real ·
solo cambiar code path use persona.render_system_prompt + AgentBase.invoke.

NO LLM call · NO costs · returns stub responses según action_id + context.

R29 sostenido (CRÍTICO · audit pre-commit · templates moved to
copilot_stub_service.py preservados verbatim · 0 strings coercitivos):
  ✅ Tono amable · paciente · sin jerga
  ✅ "Estoy aquí cuando me necesites" approach
  ✅ "Sin prisa · cuando puedas" en respuestas
  ❌ NUNCA "llevas X días sin..." · NUNCA "deadline urgente"
  ❌ NUNCA generar urgencia · ansiedad · culpa
  ❌ NUNCA imperativos coercitivos ("tienes que ahora")
"""
from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.copilot_cliente_service import (
    get_cliente_llm_service,
    llm_enabled,
)
from backend.app.agents.copilot_rate_limit import (
    CopilotRateLimitExceeded,
    enforce_rate_limit_or_raise,
)
from backend.app.agents.copilot_stub_service import get_client_stub_service
from backend.app.auth.dependencies import require_client_user
from backend.app.database import get_db, set_tenant_context
from backend.app.models.client_portal import ClientUser
from fastapi import HTTPException, status as http_status


router = APIRouter(
    prefix="/client-portal/copilot",
    tags=["Client Copiloto · LLM real (1.D.B.1) + stub fallback"],
    dependencies=[Depends(require_client_user)],
)


# ============================================================
# Schemas (idénticos a 1.D.B.1 LLM real · NO refactor UI swap-in)
# ============================================================


class ClientCopilotChatStubRequest(BaseModel):
    """Request schema · zero refactor con LLM real 1.D.B.1."""

    action_id: Literal[
        "que_hago",
        "porque_importa",
        "explica_concepto",
        "necesito_ayuda",
        "chat_send",
    ] = Field(..., description="ID de acción rápida o chat genérico")

    question: str | None = Field(
        None,
        description="Texto libre cliente (sólo aplica si action_id=chat_send)",
    )
    project_id: str | None = Field(
        None, description="UUID proyecto current context",
    )
    step_template_id: str | None = Field(
        None, description="Template ID sub-paso current",
    )
    step_title: str | None = Field(
        None, description="Título sub-paso current friendly",
    )
    fase_actual: str | None = Field(None, description="Fase lifecycle actual")
    concepto: str | None = Field(
        None,
        description="Término ENS a explicar (sólo aplica si action_id=explica_concepto)",
    )


class ClientCopilotChatStubResponse(BaseModel):
    """Response schema · zero refactor con LLM real 1.D.B.1."""

    action_id: str
    response_text: str
    is_stub: bool = Field(True, description="True · marca stub · UI muestra disclaimer")
    next_action_hint: str | None = Field(
        None, description="Hint próxima acción si aplica",
    )
    citations: list[dict[str, Any]] = Field(default_factory=list)
    # 1.D.G.I · rate limit soft-warn surface
    rate_limit_warning: str | None = Field(
        None, description="Mensaje soft-warn cuando ≥80% cap (NO bloquea)",
    )
    remaining_quota_today: int | None = Field(
        None, description="Mensajes restantes hoy",
    )


# ============================================================
# Endpoint · delegates to ClientCopilotStubService (1.D.B.0.2 refactor)
# ============================================================


@router.post(
    "/chat",
    response_model=ClientCopilotChatStubResponse,
)
async def client_copilot_chat(
    payload: ClientCopilotChatStubRequest,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(require_client_user),
) -> ClientCopilotChatStubResponse:
    """Endpoint copiloto cliente · LLM real (1.D.B.1) con stub graceful fallback.

    Code path:
      1. Si LLM enabled (anthropic_api_key configurado) → CopilotClienteLLMService
         render persona system_prompt + AgentBase-style call · R29 boundary check
         post-response · si violation → graceful stub fallback
      2. Si LLM disabled (CI/tests/no API key) → use stub service directo
      3. Si LLM call fail (exception · network · rate limit) → graceful stub
         fallback (NO break UX cliente)

    Schema IDÉNTICO ClientCopilotStubResponse (zero refactor frontend).

    R29 sostenido empíricamente:
      - System prompt persona cliente enforces R29 en YAML
      - check_r29_boundaries post-response defensive
      - Stub fallback templates verbatim preserved (0 coercitive)

    R1 sostenido: LLM SOLO conversacional · NO decisiones normativas
    (A21 determinista cubre detección discrepancias).
    """
    # 1.D.G.I · Rate limit cliente · enforce antes LLM call.
    # R09 fail-closed: el cap del cliente es POR PROYECTO · ``get_rate_limit_status``
    # EXIGE ``project_id`` para el tier cliente. Resolvemos el proyecto del cliente
    # server-side (RLS-gated · _resolve_project_meta_scoped fija el contexto). Si el
    # cliente no tiene proyecto activo, no hay agregado por-tenant que aplicar → se
    # omite el cap (evita 500 · no degrada cross-tenant).
    from backend.app.motors.m11_copiloto.portal_api import (
        _resolve_project_meta_scoped,
    )
    rate_status = None
    _pid_str, _ = await _resolve_project_meta_scoped(db, user.client_id)
    if _pid_str:
        try:
            rate_status = await enforce_rate_limit_or_raise(
                db=db, user_id=user.id, tier="cliente",
                project_id=uuid.UUID(_pid_str),
            )
        except CopilotRateLimitExceeded as exc:
            raise HTTPException(
                status_code=http_status.HTTP_429_TOO_MANY_REQUESTS,
                detail=exc.status.blocked_reason or "Rate limit exceeded",
            )

    rate_warning = rate_status.warning_message if rate_status else None
    remaining_quota = (
        rate_status.remaining_messages_today if rate_status else None
    )

    if not llm_enabled():
        # Direct stub fallback (CI · tests · no API key)
        stub_service = get_client_stub_service()
        response_text, next_hint = stub_service.generate_stub_response(
            payload.action_id,
            step_title=payload.step_title,
            concepto=payload.concepto,
        )
        return ClientCopilotChatStubResponse(
            action_id=payload.action_id,
            response_text=response_text,
            is_stub=True,
            next_action_hint=next_hint,
            citations=[],
            rate_limit_warning=rate_warning,
            remaining_quota_today=remaining_quota,
        )

    # LLM enabled · attempt real call with graceful fallback
    llm_service = get_cliente_llm_service()
    project_uuid: uuid.UUID | None = None
    if payload.project_id:
        try:
            project_uuid = uuid.UUID(payload.project_id)
        except ValueError:
            project_uuid = None

    # F-18-01 · setea contexto RLS (client_id) antes de generate_response →
    # build_client_context. El runtime es fulkro_app (RLS activa) y no hay
    # middleware que ponga app.current_client_id; sin esto la query de contexto
    # (`projects` client_isolation) sería ciega → contexto genérico para el
    # dueño legítimo. SOLO client_id desde el user autenticado: NO seteamos
    # app.current_project_id desde payload.project_id (input cliente) porque
    # eso expondría child tables project-scoped de un proyecto AJENO vía RLS
    # (fuga cross-tenant). Con client_id ctx, un project_id ajeno → 0 filas
    # (fail-closed). generate_response llama build_client_context antes del LLM
    # y solo hace db.flush() (no commit) → el GUC is_local se sostiene.
    #
    # NOTA TEST (F-18-01): esta rama NO tiene test de endpoint porque solo se
    # ejecuta con llm_enabled() (API key real); en CI/tests va por el stub
    # directo (arriba) que nunca llama build_client_context. El scoping se
    # cubre con test de helper inequívoco sobre build_client_context
    # (test_portal_copilot_tenant_context.py::test_build_client_context_*).
    await set_tenant_context(db, client_id=user.client_id)

    # N6 · memoria del copiloto cliente ENTRE conversaciones (aislada por
    # client_id+project_id) · sesión separada best-effort (no toca el GUC RLS
    # de esta request · degrada a stateless si falla).
    from backend.app.agents.copilot_memory import (
        load_conversation_history,
        persist_exchange,
    )

    _conv_id, _history = await load_conversation_history(
        project_id=project_uuid,
        client_user_id=getattr(user, "id", None),
        client_id=user.client_id,
    )

    response_text, next_hint, is_stub_fallback = await llm_service.generate_response(
        db,
        payload.action_id,
        project_id=project_uuid,
        question=payload.question,
        step_template_id=payload.step_template_id,
        step_title=payload.step_title,
        fase_actual=payload.fase_actual,
        concepto=payload.concepto,
        history=_history,
    )

    if not is_stub_fallback:
        await persist_exchange(
            conversation_id=_conv_id,
            project_id=project_uuid,
            client_id=user.client_id,
            user_text=payload.question or f"(acción: {payload.action_id})",
            assistant_text=response_text,
        )

    return ClientCopilotChatStubResponse(
        action_id=payload.action_id,
        response_text=response_text,
        is_stub=is_stub_fallback,
        next_action_hint=next_hint,
        citations=[],
        rate_limit_warning=rate_warning,
        remaining_quota_today=remaining_quota,
    )
