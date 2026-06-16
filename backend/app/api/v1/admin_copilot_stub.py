"""Admin Copiloto stub endpoint · sub-atom 1.C.D.B.3 v3.8 → refactor 1.D.B.0.2 v3.10.

Endpoint placeholder /api/v1/admin/copilot/chat · dummy responses ready
para swap-in LLM real 1.D.B.2 (zero refactor cliente UI).

Schema response idéntico a 1.D.B.2 final · Marcos puede empezar a usar
QuickActions inmediatamente con stub responses CALIDAD contextualizados.

Refactor 1.D.B.0.2 v3.10: lógica template generation movida a
`backend/app/agents/copilot_stub_service.py` (cleaner separation · OPS-045
14ª). Stub service instantiates CopilotPersonaService("admin") al init ·
persona YAML loaded + boundaries ready · cuando 1.D.B.2 promote LLM real ·
solo cambiar code path use persona.render_system_prompt + AgentBase.invoke.

NO LLM call · NO costs · returns stub responses según action_id + context.
"""
from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.copilot_admin_service import get_admin_llm_service
from backend.app.agents.copilot_cliente_service import llm_enabled
from backend.app.agents.copilot_rate_limit import (
    CopilotRateLimitExceeded,
    enforce_rate_limit_or_raise,
)
from backend.app.agents.copilot_stub_service import get_admin_stub_service
from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db
from backend.app.models.auth import User
from fastapi import HTTPException, status as http_status


router = APIRouter(
    prefix="/admin/copilot",
    tags=["Admin Copiloto · LLM real (1.D.B.2) + stub fallback"],
    dependencies=[Depends(require_owner)],
)


# ============================================================
# Schemas (idénticos a 1.D.B.2 LLM real · NO refactor UI swap-in)
# ============================================================


class CopilotChatStubRequest(BaseModel):
    """Request schema · zero refactor con LLM real 1.D.B.2."""

    action_id: Literal[
        "que_hago",
        "explica_paso",
        "draft_email",
        "briefing_reunion",
        "chat_send",
    ] = Field(..., description="ID de acción rápida o chat genérico")

    question: str | None = Field(
        None, description="Texto libre cliente (sólo aplica si action_id=chat_send)",
    )
    project_id: str | None = Field(
        None, description="UUID proyecto current context (si Marcos en cliente focus)"
    )
    project_nombre: str | None = Field(None, description="Nombre cliente current")
    step_template_id: str | None = Field(
        None, description="Template ID sub-paso current (si Marcos viendo step específico)"
    )
    step_title: str | None = Field(None, description="Título sub-paso current")
    fase_actual: str | None = Field(None, description="Fase lifecycle actual")
    # 1.D.F.0.D · screen-aware context (Next.js usePathname propagado desde frontend)
    current_screen: str | None = Field(
        None,
        description=(
            "Pathname Next.js activa · permite copiloto referenciar botones "
            "específicos UI (e.g. '/admin/projects/abc/dda')"
        ),
        max_length=512,
    )
    active_motor: str | None = Field(
        None,
        description="Motor activo opcional (override screen.motor catalog)",
        max_length=64,
    )


class CopilotChatStubResponse(BaseModel):
    """Response schema · zero refactor con LLM real 1.D.B.2."""

    action_id: str
    response_text: str
    # NOTA (audit §3.1): `is_stub` NO indica un endpoint stub permanente. El
    # path vivo (admin sidebar → /admin/copilot/chat) ejecuta la persona LLM
    # real cuando hay API key. `is_stub=True` es un *runtime fallback flag*:
    # vale True sólo cuando no hay API key (CI/tests) o el LLM falla en runtime,
    # y entonces se sirve la respuesta-plantilla determinista. El nombre
    # "stub" es histórico; semánticamente es "respuesta de fallback".
    is_stub: bool = Field(
        True,
        description=(
            "Runtime fallback flag: True cuando la respuesta proviene del "
            "fallback determinista (sin API key o error LLM), NO de un endpoint "
            "stub permanente. La UI muestra disclaimer en ese caso."
        ),
    )
    next_action_hint: str | None = Field(None, description="Hint próxima acción si aplica")
    citations: list[dict[str, Any]] = Field(default_factory=list)
    # 1.D.G.I · rate limit soft-warn surface
    rate_limit_warning: str | None = Field(
        None, description="Mensaje soft-warn cuando ≥80% cap (NO bloquea)",
    )
    remaining_quota_today: int | None = Field(
        None, description="Mensajes restantes hoy",
    )


# ============================================================
# Endpoint · delegates to AdminCopilotStubService (1.D.B.0.2 refactor)
# ============================================================


@router.post(
    "/chat",
    response_model=CopilotChatStubResponse,
)
async def admin_copilot_chat(
    payload: CopilotChatStubRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_owner),
) -> CopilotChatStubResponse:
    """Endpoint copiloto admin · LLM real (1.D.B.2 Sonnet 4.6) con stub fallback.

    Code path análogo cliente 1.D.B.1:
      1. Si LLM enabled (anthropic_api_key) → CopilotAdminLLMService render
         persona system_prompt admin + AgentBase-style call Sonnet 4.6 · R30
         boundary check post-response · si violations → defensive enrich (NO
         full stub fallback · admin tolera enrich tip tutor)
      2. Si LLM disabled (CI/tests/no API key) → use stub service directo
      3. Si LLM call fail (exception · network) → graceful stub fallback

    Schema IDÉNTICO CopilotChatStubResponse (zero refactor frontend).

    R30 sostenido empíricamente:
      - System prompt persona admin enforces R30 en YAML (asume cero ENS)
      - check_r30_boundaries post-response (assume ENS patterns + jargon
        undefined detection)
      - Defensive enrich agrega tip tutor footer (NO break UX)

    R1 sostenido: LLM SOLO conversacional · NO decisiones normativas
    (A21 determinista cubre detección discrepancias).
    """
    # 1.D.G.I · Rate limit admin · enforce antes LLM call
    rate_status = None
    try:
        rate_status = await enforce_rate_limit_or_raise(
            db=db, user_id=user.id, tier="admin",
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
        stub_service = get_admin_stub_service()
        response_text, next_hint = stub_service.generate_stub_response(
            payload.action_id,
            project_nombre=payload.project_nombre,
            step_template_id=payload.step_template_id,
            step_title=payload.step_title,
            fase_actual=payload.fase_actual,
        )
        return CopilotChatStubResponse(
            action_id=payload.action_id,
            response_text=response_text,
            is_stub=True,
            next_action_hint=next_hint,
            citations=[],
            rate_limit_warning=rate_warning,
            remaining_quota_today=remaining_quota,
        )

    llm_service = get_admin_llm_service()
    project_uuid: uuid.UUID | None = None
    if payload.project_id:
        try:
            project_uuid = uuid.UUID(payload.project_id)
        except ValueError:
            project_uuid = None

    # N6 · memoria del copiloto admin ENTRE conversaciones (aislada por
    # project_id · FULKRO opera con un único admin) · sesión separada best-effort.
    from backend.app.agents.copilot_memory import (
        load_conversation_history,
        persist_exchange,
    )

    _conv_id, _history = await load_conversation_history(project_id=project_uuid)

    response_text, next_hint, is_stub_fallback = await llm_service.generate_response(
        db,
        payload.action_id,
        project_id=project_uuid,
        project_nombre=payload.project_nombre,
        question=payload.question,
        step_template_id=payload.step_template_id,
        step_title=payload.step_title,
        fase_actual=payload.fase_actual,
        current_screen=payload.current_screen,
        active_motor=payload.active_motor,
        history=_history,
    )

    if not is_stub_fallback:
        await persist_exchange(
            conversation_id=_conv_id,
            project_id=project_uuid,
            user_text=payload.question or f"(acción: {payload.action_id})",
            assistant_text=response_text,
        )

    return CopilotChatStubResponse(
        action_id=payload.action_id,
        response_text=response_text,
        is_stub=is_stub_fallback,
        next_action_hint=next_hint,
        citations=[],
        rate_limit_warning=rate_warning,
        remaining_quota_today=remaining_quota,
    )
