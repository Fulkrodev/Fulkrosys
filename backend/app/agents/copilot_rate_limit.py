"""Copilot rate limit service · cliente Haiku + admin Sonnet caps (1.D.G.I v3.11).

Audit-first OPS-045: LLMInteractionLog ORM existing (knowledge.py:236) tracks
per-interaction · usuario · tokens · cost. Derivamos aggregates daily/monthly
on-query desde existing log · ADR-025 sostener (NO new tables).

Caps definidos:
  CLIENTE Haiku 4.5: 100 msgs/día · 30k output tokens/día · €6/mes hard cap
  ADMIN Sonnet 4.6: 500 msgs/día · 100k output tokens/día · €40/mes hard cap

Soft-warn: cuando 80% cap → response includes warning_message + remaining_quota.
Hard-fail: cuando 100% cap → FriendlyR29Limit exception (cliente) o admin
plain error (admin).

Daily reset 00:00 Europe/Madrid (timezone-aware).
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, time, timezone
from typing import Literal, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.knowledge import LLMInteractionLog


logger = logging.getLogger(__name__)


CopilotTier = Literal["cliente", "admin"]


@dataclass(frozen=True)
class RateLimitConfig:
    daily_messages_cap: int
    daily_output_tokens_cap: int
    monthly_cost_eur_cap: float
    # Etiquetas reales de LLMInteractionLog.feature por tier (filtro IN). Antes era
    # un único string "copiloto_cliente"/"copiloto_admin" que NO casaba con ninguna
    # etiqueta real → el cap nunca saltaba (0 filas · auditoría 2026-06-07).
    feature_filters: tuple[str, ...]
    # §4.5 · prefijos LIKE adicionales (p.ej. "inline_cliente_" para los agentes
    # inline del portal cliente · feature_override en base.py). Vacío = sólo exact.
    feature_prefixes: tuple[str, ...] = ()


# Default caps · architect approve · puede env override
CLIENTE_CAPS = RateLimitConfig(
    daily_messages_cap=100,
    daily_output_tokens_cap=30_000,
    monthly_cost_eur_cap=6.0,
    # §4.5 audit-2026-06-15 · el cliente SÍ usa answer_question/stream vía
    # portal_api (/client-portal/copiloto/chat[/stream]) · agent_14 ahora etiqueta
    # esa vía como copilot_cliente_chat[_stream] (role-aware) → DEBE contar en el
    # cap cliente (antes se logueaba 'copilot_chat' = etiqueta admin → la vía
    # dominante del cliente escapaba su tope y contaminaba el cap de Marcos).
    feature_filters=(
        "copilot_cliente_1d_b_1",
        "copilot_cliente_chat",
        "copilot_cliente_chat_stream",
    ),
    # Los agentes inline del portal cliente (feature "inline_cliente_<slug>")
    # también cuentan contra el cap cliente del proyecto.
    feature_prefixes=("inline_cliente_",),
)

ADMIN_CAPS = RateLimitConfig(
    daily_messages_cap=500,
    daily_output_tokens_cap=100_000,
    monthly_cost_eur_cap=40.0,
    # Copiloto admin: answer_question (copilot_chat[_stream] · router m11 require_owner)
    # + copilot_admin_service (copilot_admin_1d_b_2).
    feature_filters=("copilot_chat", "copilot_chat_stream", "copilot_admin_1d_b_2"),
)


@dataclass(frozen=True)
class RateLimitStatus:
    """Snapshot rate limit cliente/admin · returnable como part of response."""

    tier: CopilotTier
    messages_today: int
    tokens_output_today: int
    cost_eur_month: float
    daily_cap_pct: float  # 0-100+
    monthly_cap_pct: float
    soft_warn: bool  # ≥80% threshold any cap
    hard_blocked: bool  # ≥100% any cap
    blocked_reason: Optional[str]
    warning_message: Optional[str]
    remaining_messages_today: int


class CopilotRateLimitExceeded(Exception):
    """Hard-fail · cap reached."""

    def __init__(self, status: RateLimitStatus):
        self.status = status
        super().__init__(status.blocked_reason or "Rate limit exceeded")


def _config_for_tier(tier: CopilotTier) -> RateLimitConfig:
    return CLIENTE_CAPS if tier == "cliente" else ADMIN_CAPS


def _start_of_day_utc(now: Optional[datetime] = None) -> datetime:
    """00:00 today UTC · usado para daily aggregate window."""
    if now is None:
        now = datetime.now(timezone.utc)
    return datetime.combine(now.date(), time.min, tzinfo=timezone.utc)


def _start_of_month_utc(now: Optional[datetime] = None) -> datetime:
    if now is None:
        now = datetime.now(timezone.utc)
    return datetime(now.year, now.month, 1, tzinfo=timezone.utc)


async def get_rate_limit_status(
    db: AsyncSession,
    user_id: uuid.UUID,
    tier: CopilotTier,
    now: Optional[datetime] = None,
    project_id: Optional[uuid.UUID] = None,
) -> RateLimitStatus:
    """Calcula rate limit status reading LLMInteractionLog aggregates.

    FIX P1-1: cuando ``project_id`` se pasa (tier cliente), el agregado se filtra
    por ``LLMInteractionLog.project_id`` → el cap es POR TENANT. Sin él, el cap
    del cliente sumaba el uso LLM de TODOS los proyectos (quota poisoning
    cross-tenant + fuga de coste). El tier admin (Marcos, único) sigue global.

    R09 HARDENING (fail-closed): para ``tier == 'cliente'`` el ``project_id`` es
    OBLIGATORIO. Antes era opcional también para el cliente, así que un futuro
    call-site que olvidara pasarlo degradaba silenciosamente a agregado GLOBAL
    (cap envenenable cross-tenant). Ahora se rechaza explícitamente. El tier
    admin (single-user Marcos) conserva el agregado global y admite ``None``.
    """
    if tier == "cliente" and project_id is None:
        raise ValueError(
            "project_id es obligatorio para el cap del tier 'cliente' "
            "(R09 fail-closed · evita agregado LLM cross-tenant)"
        )
    config = _config_for_tier(tier)
    now = now or datetime.now(timezone.utc)
    start_today = _start_of_day_utc(now)
    start_month = _start_of_month_utc(now)

    # FIX P1-1: filtro tenant opcional. Daily + monthly comparten el mismo filtro
    # de proyecto para que el cap del cliente sea estrictamente de su proyecto.
    # §4.5 · feature exacto IN(...) OR prefijo LIKE 'inline_cliente_%' (inline agents).
    feature_pred = or_(
        LLMInteractionLog.feature.in_(config.feature_filters),
        *[LLMInteractionLog.feature.like(f"{p}%") for p in config.feature_prefixes],
    )
    daily_filters = [
        feature_pred,
        LLMInteractionLog.created_at >= start_today,
    ]
    monthly_filters = [
        feature_pred,
        LLMInteractionLog.created_at >= start_month,
    ]
    if project_id is not None:
        daily_filters.append(LLMInteractionLog.project_id == project_id)
        monthly_filters.append(LLMInteractionLog.project_id == project_id)

    daily_q = await db.execute(
        select(
            func.count(LLMInteractionLog.id),
            func.coalesce(func.sum(LLMInteractionLog.completion_tokens), 0),
            func.coalesce(func.sum(LLMInteractionLog.cost_usd), 0.0),
        ).where(*daily_filters)
    )
    daily_row = daily_q.one()
    messages_today = int(daily_row[0] or 0)
    tokens_output_today = int(daily_row[1] or 0)
    cost_today_usd = float(daily_row[2] or 0.0)

    monthly_q = await db.execute(
        select(
            func.coalesce(func.sum(LLMInteractionLog.cost_usd), 0.0),
        ).where(*monthly_filters)
    )
    monthly_cost_usd = float(monthly_q.scalar_one() or 0.0)

    # USD → EUR rough conversion 1:1 simplification (architect approve)
    cost_eur_month = monthly_cost_usd

    daily_cap_pct = max(
        (messages_today / config.daily_messages_cap) * 100,
        (tokens_output_today / config.daily_output_tokens_cap) * 100,
    )
    monthly_cap_pct = (cost_eur_month / config.monthly_cost_eur_cap) * 100

    soft_warn = daily_cap_pct >= 80 or monthly_cap_pct >= 80
    hard_blocked = daily_cap_pct >= 100 or monthly_cap_pct >= 100

    blocked_reason: Optional[str] = None
    warning_message: Optional[str] = None
    if hard_blocked:
        if monthly_cap_pct >= 100:
            blocked_reason = (
                "Has alcanzado el límite mensual de uso · vuelve el próximo mes"
            )
        else:
            blocked_reason = (
                "Has alcanzado el límite diario · vuelve mañana"
            )
    elif soft_warn:
        remaining = max(0, config.daily_messages_cap - messages_today)
        warning_message = f"Te quedan ~{remaining} consultas hoy"

    return RateLimitStatus(
        tier=tier,
        messages_today=messages_today,
        tokens_output_today=tokens_output_today,
        cost_eur_month=cost_eur_month,
        daily_cap_pct=daily_cap_pct,
        monthly_cap_pct=monthly_cap_pct,
        soft_warn=soft_warn,
        hard_blocked=hard_blocked,
        blocked_reason=blocked_reason,
        warning_message=warning_message,
        remaining_messages_today=max(
            0, config.daily_messages_cap - messages_today,
        ),
    )


async def enforce_rate_limit_or_raise(
    db: AsyncSession,
    user_id: uuid.UUID,
    tier: CopilotTier,
    project_id: Optional[uuid.UUID] = None,
) -> RateLimitStatus:
    """Check + raise CopilotRateLimitExceeded si hard_blocked.

    Returns status si OK (caller puede attach warning_message a response).
    ``project_id`` (tier cliente) hace el cap por-tenant · FIX P1-1.
    """
    status = await get_rate_limit_status(db, user_id, tier, project_id=project_id)
    if status.hard_blocked:
        logger.warning(
            "rate limit exceeded · tier=%s user=%s daily_pct=%.1f monthly_pct=%.1f",
            tier, user_id, status.daily_cap_pct, status.monthly_cap_pct,
        )
        raise CopilotRateLimitExceeded(status)
    return status
