"""Breach notification service tests (atom 9.bis.2).

4 tests covering:
- register_breach assigns BREACH_YYYY_NNN code + pending status
- notify_aepd transitions status to aepd_notified + sets timestamp
- notify_affected_clients emails each affected ClientUser
- 72h SLA helper (hours_remaining_for_aepd) computes correctly
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from backend.app.models.compliance_breach_erasure import (
    BREACH_AEPD_NOTIFIED,
    BREACH_CLIENTS_NOTIFIED,
    BREACH_PENDING,
)
from backend.app.motors.m_compliance.breach_service import (
    BreachNotificationService,
    _next_breach_code,
    hours_remaining_for_aepd,
)


@pytest.mark.asyncio
async def test_register_breach_assigns_code_and_pending(db) -> None:
    svc = BreachNotificationService(db)
    row = await svc.register_breach(
        detected_at=datetime.now(timezone.utc),
        severity="high",
        description="Acceso no autorizado a una copia de seguridad antigua.",
        data_categories_affected=["Datos identificativos", "Email"],
        data_subjects_count=42,
        root_cause="Configuración incorrecta de permisos en bucket.",
        containment_actions="Revocadas las credenciales · rotada clave.",
    )
    assert row.breach_code.startswith("BREACH_")
    assert row.notification_status == BREACH_PENDING
    assert row.data_subjects_count == 42
    assert row.reported_at is not None


@pytest.mark.asyncio
async def test_notify_aepd_updates_status(db) -> None:
    svc = BreachNotificationService(db)
    row = await svc.register_breach(
        detected_at=datetime.now(timezone.utc) - timedelta(hours=2),
        severity="medium",
        description="Pérdida transitoria de logs durante una rotación.",
        data_categories_affected=["Metadatos de uso"],
    )
    notified = await svc.notify_aepd(row.id)
    assert notified.notification_status == BREACH_AEPD_NOTIFIED
    assert notified.notified_aepd_at is not None


@pytest.mark.asyncio
async def test_notify_affected_clients_skips_anonymised(db) -> None:
    """Affected emails endpoint must NOT email tombstoned cliente accounts."""
    # Seed: one normal cliente + one anonymised cliente.
    cid = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    cu_normal = uuid.uuid4()
    cu_anonym = uuid.uuid4()
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    await db.execute(
        text(
            "INSERT INTO clients (id, nombre, cif, created_at) "
            "VALUES (:id, 'Test', :cif, now())"
        ),
        {"id": str(cid), "cif": cif},
    )
    for cu_id, email in (
        (cu_normal, f"normal-{cu_normal}@example.com"),
        (cu_anonym, f"anonymised_{cu_anonym}@removed.fulkro.local"),
    ):
        await db.execute(
            text(
                "INSERT INTO client_users (id, client_id, email, password_hash, "
                "full_name, created_at, must_change_password, failed_attempts) "
                "VALUES (:id, :cid, :email, 'x', 't', now(), false, 0)"
            ),
            {"id": str(cu_id), "cid": str(cid), "email": email},
        )
    await db.execute(text("RESET ROLE"))
    # Set tenant context · the admin notify-clients endpoint resolves the
    # affected tenant from the breach payload before invoking the service.
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": str(cid)},
    )
    await db.flush()

    svc = BreachNotificationService(db)
    row = await svc.register_breach(
        detected_at=datetime.now(timezone.utc),
        severity="critical",
        description="Filtración de emails confirmada.",
        data_categories_affected=["Email"],
        data_subjects_count=2,
        affected_client_user_ids=[cu_normal, cu_anonym],
    )
    notified, sent = await svc.notify_affected_clients(row.id)
    assert notified.notification_status == BREACH_CLIENTS_NOTIFIED
    # Only the non-anonymised cliente receives the email.
    assert sent == 1


def test_hours_remaining_for_aepd_within_window() -> None:
    detected = datetime.now(timezone.utc) - timedelta(hours=10)
    remaining = hours_remaining_for_aepd(detected)
    assert 60 < remaining < 63  # 72 - 10 = 62 ± clock drift

    # Past deadline returns negative number.
    past = datetime.now(timezone.utc) - timedelta(hours=80)
    overdue = hours_remaining_for_aepd(past)
    assert overdue < 0


def test_next_breach_code_increments_within_year() -> None:
    assert _next_breach_code(None, year=2026) == "BREACH_2026_001"
    assert _next_breach_code("BREACH_2026_001", year=2026) == "BREACH_2026_002"
    assert _next_breach_code("BREACH_2025_099", year=2026) == "BREACH_2026_001"
