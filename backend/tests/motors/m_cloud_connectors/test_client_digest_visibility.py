"""Tests · cliente digest visibility + filtered schema (1.D.X.VERIFY 2b).

Verifica:
- build_client_digest_view filtra correctamente (NO leak admin fields)
- Trend MoM deterministic (mejora · igual · baja_suave · primer_resumen)
- NUNCA color hint 'rojo' (R29 sin alarma)
- Notification trigger crea ClientNotification 'report_available' per ClientUser
- Empty state cuando no snapshot (has_snapshot=False)
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text

from backend.app.models.client_notification import ClientNotification
from backend.app.motors.m_cloud_connectors import (
    build_client_digest_view,
    generate_monthly_digest_for_project,
)
from backend.tests.conftest import setup_test_project


# ============================================================
# build_client_digest_view · pure function tests
# ============================================================


def test_build_view_no_snapshot_returns_empty_state():
    """has_snapshot=False + summary friendly + emoji ✨ neutral."""
    view = build_client_digest_view(latest=None, previous=None)
    assert view["has_snapshot"] is False
    assert view["compliance_score"] == 100
    assert view["trend_label"] == "primer_resumen"
    assert view["trend_emoji"] == "✨"
    assert view["trend_color_hint"] == "neutral"
    assert view["changes_reviewed_count"] == 0
    assert "primer resumen" in view["summary_friendly"].lower()


def test_build_view_first_snapshot_no_previous():
    """1er digest · sin previous · trend=primer_resumen."""

    class _MockSnap:
        compliance_score = 95
        open_gaps_total = 2
        generated_at = None

    view = build_client_digest_view(latest=_MockSnap(), previous=None)
    assert view["has_snapshot"] is True
    assert view["trend_label"] == "primer_resumen"
    assert view["compliance_score"] == 95


def test_build_view_trend_mejora_when_score_rises_above_2():
    """Delta > 2 → mejora · color verde · emoji ↑."""

    class _Latest: compliance_score = 95; open_gaps_total = 0; generated_at = None
    class _Prev: compliance_score = 88; open_gaps_total = 5; generated_at = None

    view = build_client_digest_view(latest=_Latest(), previous=_Prev())
    assert view["trend_label"] == "mejora"
    assert view["trend_emoji"] == "↑"
    assert view["trend_color_hint"] == "verde"


def test_build_view_trend_baja_uses_naranja_suave_NUNCA_rojo():
    """Delta < -2 → baja · color naranja_suave · NUNCA rojo (R29 sostener)."""

    class _Latest: compliance_score = 70; open_gaps_total = 5; generated_at = None
    class _Prev: compliance_score = 90; open_gaps_total = 2; generated_at = None

    view = build_client_digest_view(latest=_Latest(), previous=_Prev())
    assert view["trend_label"] == "baja"
    assert view["trend_emoji"] == "↓"
    assert view["trend_color_hint"] == "naranja_suave"
    # CRITICAL R29: NUNCA color rojo aunque score baje
    assert view["trend_color_hint"] != "rojo"
    assert "preocupante" not in view["summary_friendly"].lower()


def test_build_view_trend_igual_when_delta_within_tolerance():
    """|Delta| <= 2 → igual · color ámbar · emoji ≈."""

    class _Latest: compliance_score = 88; open_gaps_total = 3; generated_at = None
    class _Prev: compliance_score = 90; open_gaps_total = 3; generated_at = None

    view = build_client_digest_view(latest=_Latest(), previous=_Prev())
    assert view["trend_label"] == "igual"
    assert view["trend_emoji"] == "≈"


def test_build_view_summary_no_admin_jargon():
    """Summary NO contiene jerga admin/ENS técnica (R30 inverso cliente)."""

    class _Latest: compliance_score = 80; open_gaps_total = 3; generated_at = None
    class _Prev: compliance_score = 85; open_gaps_total = 2; generated_at = None

    view = build_client_digest_view(latest=_Latest(), previous=_Prev())
    summary = view["summary_friendly"].lower()
    # NO admin lingo
    forbidden = [
        "compliance", "audit", "evidence", "trazabilidad",
        "anexo ii", "rd 311", "ccn-stic", "gap",
    ]
    for term in forbidden:
        assert term not in summary, (
            f"summary contiene jerga prohibida: {term!r} · "
            f"texto: {summary!r}"
        )


# ============================================================
# Filtered schema · NO leak admin sensitive fields
# ============================================================


def test_view_excludes_admin_sensitive_fields():
    """ClientDigestView NO incluye triggered_by_user_id · snapshot_jsonb · etc."""

    class _Latest:
        compliance_score = 90
        open_gaps_total = 1
        generated_at = None

    view = build_client_digest_view(latest=_Latest(), previous=None)
    # CRITICAL: NUNCA estos fields en cliente view
    forbidden_keys = {
        "triggered_by", "triggered_by_user_id", "snapshot_jsonb",
        "id", "project_id", "open_gaps_by_severity",
    }
    for key in forbidden_keys:
        assert key not in view, f"ClientDigestView leak field admin: {key!r}"


# ============================================================
# Notification trigger · ClientNotification per ClientUser
# ============================================================


async def _create_client_user(db, *, client_id: uuid.UUID) -> uuid.UUID:
    """Insert ClientUser dummy bajo client_id existing."""
    user_id = uuid.uuid4()
    await db.execute(text(
        "INSERT INTO client_users "
        "(id, client_id, email, password_hash, must_change_password, "
        "failed_attempts, created_by_marcos, "
        "consent_functional, consent_analytics, consent_marketing) "
        "VALUES (:id, :cid, :email, 'h', true, 0, true, false, false, false)"
    ), {
        "id": str(user_id),
        "cid": str(client_id),
        "email": f"user_{user_id.hex[:8]}@test.local",
    })
    await db.flush()
    return user_id


@pytest.mark.asyncio
async def test_notification_triggered_on_digest_generation(db):
    """generate_monthly_digest_for_project emite ClientNotification per user."""
    client_id_str, project_id_str = await setup_test_project(db)
    cid = uuid.UUID(client_id_str)
    pid = uuid.UUID(project_id_str)

    user_id = await _create_client_user(db, client_id=cid)

    snapshot = await generate_monthly_digest_for_project(
        db, project_id=pid, triggered_by="admin_manual",
    )

    # Verify ClientNotification created
    res = await db.execute(
        select(ClientNotification).where(
            ClientNotification.client_user_id == user_id,
        )
    )
    notifs = list(res.scalars().all())
    assert len(notifs) == 1
    n = notifs[0]
    assert n.type == "report_available"
    assert n.target_url == "/client-portal/retainer-checkin"
    assert n.emitted_by_motor == "m_cloud_connectors"
    assert n.priority == "normal"
    # Payload contiene snapshot reference (NO sensitive raw)
    assert n.payload_json["digest_snapshot_id"] == str(snapshot.id)
    # Body friendly · sin presión
    assert n.body is not None
    assert "sin prisa" in n.body.lower() or "echa un vistazo" in n.body.lower()


@pytest.mark.asyncio
async def test_no_notification_when_no_client_users(db):
    """Project sin ClientUsers · digest se genera pero NO emite notification."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)

    snapshot = await generate_monthly_digest_for_project(
        db, project_id=pid, triggered_by="celery_monthly",
    )

    # Snapshot creado OK
    assert snapshot.id is not None
    # 0 notifications (no users)
    res = await db.execute(
        select(ClientNotification).where(
            ClientNotification.project_id == pid,
        )
    )
    assert list(res.scalars().all()) == []


# ============================================================
# YAML loader smoke (mini-smoke commit 2b req)
# ============================================================


def test_copilot_personas_yaml_screen_retainer_checkin():
    """YAML carga OK · persona cliente tiene entry /client-portal/retainer-checkin."""
    from backend.app.agents.copilot_personas_loader import (
        load_catalog,
    )

    catalog = load_catalog(use_cache=False)
    cliente = catalog.personas["cliente"]

    retainer_entries = [
        e for e in cliente.screen_references_catalog
        if e.screen == "/client-portal/retainer-checkin"
    ]
    assert len(retainer_entries) == 1, (
        f"Persona cliente debe tener entry /client-portal/retainer-checkin · "
        f"encontrados: {[e.screen for e in cliente.screen_references_catalog]}"
    )
    entry = retainer_entries[0]
    assert entry.motor == "m_cloud_connectors"
    assert "compliance score" in " ".join(entry.actions).lower()
    assert "trend" in " ".join(entry.actions).lower()
    # Context hints debe mencionar primer-principios + NO presión
    hints = entry.context_hints.lower()
    assert "no inventar" in hints
    assert "no presión" in hints or "no alarma" in hints
