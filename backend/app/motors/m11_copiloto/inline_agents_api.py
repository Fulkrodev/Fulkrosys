"""Inline agents API · MB-7 atom 7.4-bis plan v6 NEW v5.

Client-facing inline agent invocations · 9 agents (A02/A17 skip admin-only):
  a04_redactor_summary, a06_contratos_analysis, a11_auditor_virtual_check,
  a12_coach_suggestion, a18_reunion_summary, a19_propuestas_justify,
  a20_negociacion_counter, a21_discrepancias_scan, a27_clasificador_upload,
  a31_enriquecedor_dda.

Tier-aware filtering per plan v6 tabla:
- BASICA  · A04, A18, A19, A20, A06, A27
- MEDIA   · + A11, A12, A21, A31
- ALTA    · + grounding citas avanzadas

Cached quick_suggestion (30 min · in-process LRU). Rate limit deferred
to atom 7.5 with Redis (post-MB-7 caching layer).
"""
from __future__ import annotations

import importlib
import logging
import time
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.base import AgentBase
from backend.app.agents.copilot_rate_limit import (
    CopilotRateLimitExceeded,
    enforce_rate_limit_or_raise,
)
from backend.app.database import get_db
from backend.app.models.client_portal import ClientUser
from backend.app.motors.m21_portal_cliente.api import get_current_client_user


logger = logging.getLogger(__name__)

# Tamaño máximo del cache in-process (evita crecimiento ilimitado · §4.5).
_SUGGESTION_CACHE_MAX = 512


async def _enforce_inline_cliente_cap(
    db: AsyncSession, user: ClientUser, project_id: uuid.UUID,
) -> None:
    """§4.5 · aplica el cap cliente (mensajes/día + coste/mes) a los agentes inline
    (antes SIN rate-limit → vía de evasión del tope de coste LLM). 429 si supera."""
    try:
        await enforce_rate_limit_or_raise(
            db=db, user_id=user.id, tier="cliente", project_id=project_id,
        )
    except CopilotRateLimitExceeded as exc:
        raise HTTPException(
            status_code=429,
            detail=(
                getattr(exc.status, "blocked_reason", None)
                or "Has alcanzado el límite de uso del asistente. Vuelve más tarde."
            ),
        )


def _prune_suggestion_cache(now: float) -> None:
    """Elimina entradas caducadas y, si aún excede el máximo, las más antiguas."""
    expired = [
        k for k, (ts, _) in _suggestion_cache.items()
        if now - ts >= _SUGGESTION_TTL_SECONDS
    ]
    for k in expired:
        _suggestion_cache.pop(k, None)
    if len(_suggestion_cache) > _SUGGESTION_CACHE_MAX:
        for k in sorted(_suggestion_cache, key=lambda k: _suggestion_cache[k][0])[
            : len(_suggestion_cache) - _SUGGESTION_CACHE_MAX
        ]:
            _suggestion_cache.pop(k, None)


router = APIRouter(
    prefix="/client-portal/inline-agents",
    tags=["Portal Cliente - Inline Agents"],
)


# inline-agents slug → (agent_id, registry class path, min tier)
_INLINE_AGENT_MAP: dict[str, tuple[int, str, str]] = {
    "a04_redactor_summary": (4, "agent_04_redactor.RedactorPoliticasAgent", "BASICA"),
    "a06_contratos_analysis": (6, "agent_06_contratos.AnalistaContratosAgent", "BASICA"),
    "a11_auditor_virtual_check": (11, "agent_11_auditor_virtual.AuditorInternoVirtualAgent", "MEDIA"),
    "a12_coach_suggestion": (12, "agent_12_coach_cliente.CoachClienteAgent", "MEDIA"),
    "a18_reunion_summary": (18, "agent_18_reunion.AsistenteReunionExploratoriaAgent", "BASICA"),
    "a19_propuestas_justify": (19, "agent_19_propuestas.RedactorPropuestasAgent", "BASICA"),
    "a20_negociacion_counter": (20, "agent_20_negociacion.AsistenteNegociacionAgent", "BASICA"),
    "a21_discrepancias_scan": (21, "agent_21_discrepancias.DetectorDiscrepanciasAgent", "MEDIA"),
    "a27_clasificador_upload": (27, "agent_27_clasificador.ClasificadorIDMSAgent", "BASICA"),
    "a31_enriquecedor_dda": (31, "agent_31_enriquecedor_dda.Agent31EnriquecedorDdA", "MEDIA"),
}

_TIER_ORDER = {"BASICA": 0, "MEDIA": 1, "ALTA": 2}


# In-process suggestion cache: (slug, project_id, page_url) → (timestamp, value)
_SUGGESTION_TTL_SECONDS = 30 * 60
_suggestion_cache: dict[tuple[str, str, str], tuple[float, dict]] = {}


def _get_agent_class(class_path: str) -> type[AgentBase] | None:
    module_name, class_name = class_path.rsplit(".", 1)
    mod = importlib.import_module(f"backend.app.agents.{module_name}")
    return getattr(mod, class_name, None)


async def _resolve_project_and_tier(
    db: AsyncSession, client_id: uuid.UUID,
) -> tuple[Optional[uuid.UUID], Optional[str]]:
    # projects tiene FORCE RLS por current_client_id(): fijar el contexto del
    # cliente ANTES de leer (si no, 0 filas → 404 para TODO cliente legítimo).
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": str(client_id)},
    )
    row = (await db.execute(
        text(
            "SELECT id, categoria_objetivo FROM projects "
            "WHERE client_id = :cid AND deleted_at IS NULL "
            "ORDER BY created_at DESC LIMIT 1"
        ),
        {"cid": str(client_id)},
    )).first()
    if not row:
        return None, None
    # Fijar también project_id para que agent.invoke lea datos project-scoped.
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(row[0])},
    )
    return row[0], row[1]


def _agent_allowed_for_tier(
    min_tier: str, project_tier: Optional[str],
) -> bool:
    """BASICA tier sees BASICA agents only. MEDIA sees BASICA+MEDIA. ALTA all."""
    if project_tier is None:
        return min_tier == "BASICA"
    return _TIER_ORDER.get(project_tier, -1) >= _TIER_ORDER.get(min_tier, 0)


class InlineAgentInvokeBody(BaseModel):
    user_message: str = Field(..., min_length=1, max_length=4000)
    extra_context: Optional[str] = Field(None, max_length=8000)
    page_url: Optional[str] = None
    structured_output: bool = False


class InlineAgentInvokeResponse(BaseModel):
    agent_id: int
    agent_name: str
    response: str
    tokens_input: int
    tokens_output: int
    latency_ms: int
    citations: list[str]


@router.get("")
async def list_inline_agents(
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List inline agents available for the client tier."""
    _, tier = await _resolve_project_and_tier(db, user.client_id)
    items: list[dict] = []
    for slug, (agent_id, _class_path, min_tier) in _INLINE_AGENT_MAP.items():
        items.append({
            "slug": slug,
            "agent_id": agent_id,
            "min_tier": min_tier,
            "available": _agent_allowed_for_tier(min_tier, tier),
        })
    return {"tier": tier, "agents": items}


@router.post("/{slug}/invoke", response_model=InlineAgentInvokeResponse)
async def invoke_inline_agent(
    slug: str,
    body: InlineAgentInvokeBody,
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> InlineAgentInvokeResponse:
    """Run an inline agent · tier-gated by project categoria_objetivo."""
    entry = _INLINE_AGENT_MAP.get(slug)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Inline agent {slug} not found")
    agent_id, class_path, min_tier = entry

    project_id, tier = await _resolve_project_and_tier(db, user.client_id)
    if not project_id:
        raise HTTPException(
            status_code=404, detail="No active project for this client",
        )
    if not _agent_allowed_for_tier(min_tier, tier):
        raise HTTPException(
            status_code=403,
            detail=(
                f"Tu categoría {tier or '?'} no incluye este agente "
                f"(requiere {min_tier})."
            ),
        )

    await _enforce_inline_cliente_cap(db, user, project_id)  # §4.5
    cls = _get_agent_class(class_path)
    if not cls:
        raise HTTPException(
            status_code=404, detail=f"Implementation class not found for {slug}",
        )
    agent = cls()
    result = await agent.invoke(
        db=db,
        project_id=project_id,
        user_message=body.user_message,
        extra_context=body.extra_context or "",
        structured_output=body.structured_output,
        feature_override=f"inline_cliente_{slug}",  # §4.5 · cuenta contra cap cliente
    )
    return InlineAgentInvokeResponse(
        agent_id=agent_id,
        agent_name=result.get("agent_name", ""),
        response=result.get("response", ""),
        tokens_input=int(result.get("tokens_input", 0)),
        tokens_output=int(result.get("tokens_output", 0)),
        latency_ms=int(result.get("latency_ms", 0)),
        citations=list(result.get("citations", []) or []),
    )


@router.get("/{slug}/quick-suggestion")
async def quick_suggestion(
    slug: str,
    page_url: Optional[str] = None,
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return a cached suggestion for the agent · 30 min TTL.

    Light-weight idempotent endpoint for banner-style hints. Cache key
    is (slug, project_id, page_url). On miss invokes the agent with a
    canonical prompt; on hit returns the cached payload.
    """
    entry = _INLINE_AGENT_MAP.get(slug)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Inline agent {slug} not found")
    agent_id, class_path, min_tier = entry

    project_id, tier = await _resolve_project_and_tier(db, user.client_id)
    if not project_id:
        raise HTTPException(status_code=404, detail="No active project")
    if not _agent_allowed_for_tier(min_tier, tier):
        return {"available": False, "reason": f"requires {min_tier}"}

    cache_key = (slug, str(project_id), page_url or "")
    now = time.time()
    hit = _suggestion_cache.get(cache_key)
    if hit and now - hit[0] < _SUGGESTION_TTL_SECONDS:
        return {"available": True, "cached": True, **hit[1]}

    # §4.5 · sólo en miss (un hit no llama al LLM) aplicar cap + poda del cache.
    await _enforce_inline_cliente_cap(db, user, project_id)
    _prune_suggestion_cache(now)
    cls = _get_agent_class(class_path)
    if not cls:
        raise HTTPException(status_code=404, detail="No impl class")
    agent = cls()
    result = await agent.invoke(
        db=db,
        project_id=project_id,
        user_message=(
            "Dame una sugerencia breve (1-2 frases) para el cliente en su "
            f"contexto actual{f' en {page_url}' if page_url else ''}."
        ),
        extra_context="",
        feature_override=f"inline_cliente_{slug}",  # §4.5
    )
    payload = {
        "agent_id": agent_id,
        "agent_name": result.get("agent_name", ""),
        "response": result.get("response", ""),
        "citations": list(result.get("citations", []) or []),
    }
    _suggestion_cache[cache_key] = (now, payload)
    return {"available": True, "cached": False, **payload}
