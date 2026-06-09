"""Atom 10.1 (MB-10) specific checks · 2 new compliance checks tests.

Tests for the 2 checks added in atom 10.1 honoring docs Block 1 commitments:
- ``check_admin_actions_audit_logged`` (ENS art.24.1 + ISO 27001 A.8.20)
- ``check_marketing_analytics_opt_in_only`` (RGPD Art.7 + AEPD 2020)

Atom 10.1 progression: 17 → 18 → 19 checks (atomic commits per check).
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import text

from backend.app.models.compliance_monitor import (
    STATUS_GREEN,
    STATUS_YELLOW,
)
from backend.app.motors.m_compliance_monitor.checks import (
    CHECK_REGISTRY,
    check_admin_actions_audit_logged,
    check_marketing_analytics_opt_in_only,
)
from backend.tests.conftest import _admin_setup


pytestmark = pytest.mark.asyncio


# ── Registry · spec validates correctly ─────────────────────────────────


def test_admin_actions_audit_logged_registered() -> None:
    """Spec present in registry with correct metadata."""
    spec = CHECK_REGISTRY["admin_actions_audit_logged"]
    assert spec.category == "audit"
    assert spec.frequency == "daily"
    assert spec.severity == "high"
    assert spec.runner is check_admin_actions_audit_logged
    assert "ENS" in spec.regulatory_basis
    assert "ISO" in spec.regulatory_basis


# ── Behavioural cases ──────────────────────────────────────────────────


async def _insert_audit_row(
    db, usuario: str, ts: datetime | None = None
) -> None:
    """Helper · insert a row into audit_log under _admin_setup."""
    when = ts or datetime.now(timezone.utc)
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO audit_log "
                "(id, tabla, registro_id, accion, usuario, timestamp, seq) "
                "VALUES (:id, 'fake_table', :rid, 'TEST', :usr, :ts, "
                "  COALESCE((SELECT MAX(seq) FROM audit_log), 0) + 1)"
            ),
            {
                "id": str(uuid.uuid4()),
                "rid": str(uuid.uuid4()),
                "usr": usuario,
                "ts": when,
            },
        )
    await db.flush()


async def test_admin_audit_green_when_24h_activity(db) -> None:
    """GREEN · Marcos activity in last 24h."""
    await _insert_audit_row(db, "marcos@fulkro.es")
    result = await check_admin_actions_audit_logged(db)
    assert result.status == STATUS_GREEN
    assert "active" in result.message.lower()
    assert result.details.get("count_24h", 0) >= 1


async def test_admin_audit_yellow_when_no_7d_activity(db) -> None:
    """YELLOW (informational) · no admin actions in 7 days · dev/vacation OK.

    Baseline limpio: audit_log es append-only (R6 · triggers + privilegio · auditoría
    2026-06-07) y la tx del test está aislada · el seed NO crea filas recientes de
    marcos@fulkro.es (verificado: 0 en 7d), así que NO hace falta borrar (que además
    R6 prohíbe). El check ve 0 actividad reciente → YELLOW informativo.
    """
    result = await check_admin_actions_audit_logged(db)
    assert result.status == STATUS_YELLOW
    assert "7 days" in result.message
    assert result.details.get("count_24h", 0) == 0
    assert result.details.get("count_7d", 0) == 0


async def test_admin_audit_yellow_when_gap_24h_with_7d_activity(db) -> None:
    """YELLOW (suspicious) · 0 rows last 24h but rows in 7d window."""
    # Baseline limpio sin borrar (audit_log append-only R6 · seed sin filas recientes
    # de marcos · tx aislada). Insertamos una fila a 3 días → 0 en 24h, ≥1 en 7d.
    # Insert row 3 days ago (within 7d window, outside 24h)
    three_days_ago = datetime.now(timezone.utc) - timedelta(days=3)
    await _insert_audit_row(db, "marcos@fulkro.es", three_days_ago)

    result = await check_admin_actions_audit_logged(db)
    assert result.status == STATUS_YELLOW
    assert "gap" in result.message.lower() or "0 rows last 24h" in result.message
    assert result.details.get("count_24h", 0) == 0
    assert result.details.get("count_7d", 0) >= 1


# ── Marketing analytics opt-in only (atom 10.1.2) ──────────────────────


def test_marketing_analytics_opt_in_only_registered() -> None:
    """Spec present in registry with correct metadata."""
    spec = CHECK_REGISTRY["marketing_analytics_opt_in_only"]
    assert spec.category == "cookies"
    assert spec.frequency == "weekly"
    assert spec.severity == "high"
    assert spec.runner is check_marketing_analytics_opt_in_only
    assert "GDPR" in spec.regulatory_basis or "RGPD" in spec.regulatory_basis
    assert "AEPD" in spec.regulatory_basis


async def test_marketing_analytics_green_when_no_integration(db) -> None:
    """GREEN · no marketing analytics env vars set (FULKRO privacy-by-design)."""
    # Strip any analytics env vars que pudieran estar set en el entorno test
    analytics_keys = (
        "POSTHOG_API_KEY", "POSTHOG_HOST", "GA_MEASUREMENT_ID",
        "GA4_MEASUREMENT_ID", "MATOMO_URL", "MIXPANEL_TOKEN",
        "SEGMENT_WRITE_KEY", "AMPLITUDE_API_KEY",
    )
    clean_env = {k: v for k, v in os.environ.items() if k not in analytics_keys}
    with patch.dict(os.environ, clean_env, clear=True):
        result = await check_marketing_analytics_opt_in_only(db)
    assert result.status == STATUS_GREEN
    assert "No marketing analytics integration" in result.message
    assert result.details.get("integrations") == []


async def test_marketing_analytics_yellow_when_posthog_detected(db) -> None:
    """YELLOW · PostHog integration detected · manual audit required."""
    with patch.dict(os.environ, {"POSTHOG_API_KEY": "phc_test_token_fake"}):
        result = await check_marketing_analytics_opt_in_only(db)
    assert result.status == STATUS_YELLOW
    assert "MANUAL audit" in result.message
    assert "POSTHOG_API_KEY" in result.details.get("integrations", [])


async def test_marketing_analytics_yellow_when_ga_detected(db) -> None:
    """YELLOW · Google Analytics integration detected · manual audit required."""
    with patch.dict(os.environ, {"GA4_MEASUREMENT_ID": "G-XXXXXXXXXX"}):
        result = await check_marketing_analytics_opt_in_only(db)
    assert result.status == STATUS_YELLOW
    assert "MANUAL audit" in result.message
    assert "GA4_MEASUREMENT_ID" in result.details.get("integrations", [])
