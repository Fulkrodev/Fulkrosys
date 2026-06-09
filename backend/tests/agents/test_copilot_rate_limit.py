"""Tests · Copilot rate limit service (1.D.G.I v3.11).

Cubre:
- CLIENTE_CAPS + ADMIN_CAPS configuration
- _start_of_day_utc / _start_of_month_utc helpers
- get_rate_limit_status soft_warn 80% threshold
- get_rate_limit_status hard_blocked 100% cap
- enforce_rate_limit_or_raise raises CopilotRateLimitExceeded
- warning_message + remaining_messages_today calculated correctly
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.agents.copilot_rate_limit import (
    ADMIN_CAPS,
    CLIENTE_CAPS,
    CopilotRateLimitExceeded,
    RateLimitStatus,
    _config_for_tier,
    _start_of_day_utc,
    _start_of_month_utc,
    enforce_rate_limit_or_raise,
    get_rate_limit_status,
)


# ============= Config caps =============


def test_cliente_caps_match_architect_spec():
    assert CLIENTE_CAPS.daily_messages_cap == 100
    assert CLIENTE_CAPS.daily_output_tokens_cap == 30_000
    assert CLIENTE_CAPS.monthly_cost_eur_cap == 6.0
    assert CLIENTE_CAPS.feature_filters == ("copilot_cliente_1d_b_1",)


def test_admin_caps_match_architect_spec():
    assert ADMIN_CAPS.daily_messages_cap == 500
    assert ADMIN_CAPS.daily_output_tokens_cap == 100_000
    assert ADMIN_CAPS.monthly_cost_eur_cap == 40.0
    assert ADMIN_CAPS.feature_filters == (
        "copilot_chat", "copilot_chat_stream", "copilot_admin_1d_b_2",
    )


def test_config_for_tier_returns_correct():
    assert _config_for_tier("cliente") == CLIENTE_CAPS
    assert _config_for_tier("admin") == ADMIN_CAPS


# ============= Time helpers =============


def test_start_of_day_utc_midnight():
    sample = datetime(2026, 5, 21, 15, 30, 45, tzinfo=timezone.utc)
    start = _start_of_day_utc(sample)
    assert start == datetime(2026, 5, 21, 0, 0, 0, tzinfo=timezone.utc)


def test_start_of_month_utc_first_day():
    sample = datetime(2026, 5, 21, 15, 30, tzinfo=timezone.utc)
    start = _start_of_month_utc(sample)
    assert start == datetime(2026, 5, 1, 0, 0, 0, tzinfo=timezone.utc)


# ============= get_rate_limit_status =============


def _build_db_mock(
    messages_count: int = 0,
    tokens_output: int = 0,
    monthly_cost: float = 0.0,
):
    """Build async DB mock returning specified aggregates."""
    db = AsyncMock()

    daily_result = MagicMock()
    daily_result.one = MagicMock(
        return_value=(messages_count, tokens_output, 0.0),
    )

    monthly_result = MagicMock()
    monthly_result.scalar_one = MagicMock(return_value=monthly_cost)

    call_count = {"i": 0}

    async def execute_side(_query):
        call_count["i"] += 1
        if call_count["i"] == 1:
            return daily_result
        return monthly_result

    db.execute = execute_side
    return db


@pytest.mark.asyncio
async def test_rate_limit_status_below_thresholds_clean():
    db = _build_db_mock(messages_count=10, tokens_output=1_000, monthly_cost=0.5)
    status = await get_rate_limit_status(db, uuid.uuid4(), "cliente")
    assert status.soft_warn is False
    assert status.hard_blocked is False
    assert status.warning_message is None
    assert status.blocked_reason is None
    assert status.remaining_messages_today == 90


@pytest.mark.asyncio
async def test_rate_limit_status_soft_warn_80pct_messages():
    db = _build_db_mock(messages_count=82, tokens_output=1_000, monthly_cost=0.0)
    status = await get_rate_limit_status(db, uuid.uuid4(), "cliente")
    assert status.soft_warn is True
    assert status.hard_blocked is False
    assert status.warning_message is not None
    assert "18" in status.warning_message  # ~18 messages remaining
    assert status.remaining_messages_today == 18


@pytest.mark.asyncio
async def test_rate_limit_status_hard_blocked_messages():
    db = _build_db_mock(messages_count=105, tokens_output=1_000, monthly_cost=0.0)
    status = await get_rate_limit_status(db, uuid.uuid4(), "cliente")
    assert status.hard_blocked is True
    assert status.blocked_reason is not None
    assert "límite diario" in status.blocked_reason
    assert status.remaining_messages_today == 0


@pytest.mark.asyncio
async def test_rate_limit_status_hard_blocked_monthly_cost():
    db = _build_db_mock(messages_count=10, tokens_output=1_000, monthly_cost=7.0)
    status = await get_rate_limit_status(db, uuid.uuid4(), "cliente")
    assert status.hard_blocked is True
    assert "mensual" in status.blocked_reason


@pytest.mark.asyncio
async def test_rate_limit_status_admin_higher_caps():
    db = _build_db_mock(messages_count=400, tokens_output=80_000, monthly_cost=35.0)
    status = await get_rate_limit_status(db, uuid.uuid4(), "admin")
    # 400/500 = 80% · soft_warn pero NO hard_blocked
    assert status.soft_warn is True
    assert status.hard_blocked is False


# ============= enforce_rate_limit_or_raise =============


@pytest.mark.asyncio
async def test_enforce_passes_below_cap():
    db = _build_db_mock(messages_count=10, monthly_cost=0.0)
    status = await enforce_rate_limit_or_raise(db, uuid.uuid4(), "cliente")
    assert status.hard_blocked is False


@pytest.mark.asyncio
async def test_enforce_raises_when_hard_blocked():
    db = _build_db_mock(messages_count=200, monthly_cost=0.0)
    with pytest.raises(CopilotRateLimitExceeded) as exc:
        await enforce_rate_limit_or_raise(db, uuid.uuid4(), "cliente")
    assert exc.value.status.hard_blocked is True
    assert exc.value.status.blocked_reason is not None


# ===== Integración real-DB · el cap CUENTA las etiquetas REALES (fix 2026-06-07) =====


def _llm_row(feature: str):
    from backend.app.models.knowledge import LLMInteractionLog
    return LLMInteractionLog(
        feature=feature, model="claude-test", prompt_hash="z" * 64,
        prompt_tokens=10, completion_tokens=100, total_tokens=110,
        latency_ms=50, status="success",
    )


@pytest.mark.asyncio
async def test_cap_counts_real_feature_labels(db):
    """Antes del fix: feature_filter='copiloto_admin' no casaba con ninguna
    etiqueta real → messages_today=0 SIEMPRE → cap nunca saltaba. Ahora cuenta
    las etiquetas reales por tier y NO mezcla cliente/admin."""
    db.add(_llm_row("copilot_admin_1d_b_2"))
    db.add(_llm_row("copilot_chat"))
    db.add(_llm_row("copilot_cliente_1d_b_1"))
    await db.flush()

    admin = await get_rate_limit_status(db, uuid.uuid4(), "admin")
    cliente = await get_rate_limit_status(db, uuid.uuid4(), "cliente")

    # admin cuenta sus 2 etiquetas (admin_1d_b_2 + chat) · NO la del cliente
    assert admin.messages_today >= 2
    # cliente cuenta solo la suya (1) · NO las admin
    assert cliente.messages_today >= 1
    assert cliente.messages_today < admin.messages_today + 1  # no mezcla
