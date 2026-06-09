"""CLUSTER 2 Phase 2D · ClientNotification central SSE wire-completeness tests.

Sesión 3B-2B.8 CLUSTER 2 Phase 2D · DRY centralizado: emit_client_notification
ahora dispatch SSE event `client_notification.created` + audit_log
`cliente.notif.dispatched` (Sub-atom 5.A 3-way OR project_id + client_id)
post-persist · best-effort try/except · primary persist nunca bloqueado.

Coverage:
- Test SSE dispatch fired post-persist (subscriber receives event)
- Test audit_log entry cliente.notif.dispatched (Sub-atom 5.A propagated)
- Test graceful degradation: SSE dispatcher failure → primary persist NOT blocked
- Test event payload schema (notification_id + type + target_url + client_user_id)
- Test forward-compat ALL VALID_TYPES (single emit_client_notification serves
  report_available + acta_review + evidence_request + etc · NO per-type wiring)

Pattern reference: pattern 15 cumulative (central function fn + SSE dispatch DRY
· emit_client_notification wraps persist + SSE + audit_log in 1 fn).
"""
from __future__ import annotations

import asyncio
import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.sse_dispatcher import (
    CLIENTE_EVENT_TYPES,
    SseEvent,
    event_matches_audience,
    sse_dispatcher,
)
from backend.app.models.client_notification import ClientNotification
from backend.app.motors.m21_portal_cliente.notification_service import (
    emit_client_notification,
)
from backend.tests.conftest import _admin_setup, setup_test_project


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════


async def _create_active_client_user(
    db: AsyncSession, *, client_id: uuid.UUID,
) -> uuid.UUID:
    """Insert active ClientUser row · returns user_id."""
    user_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO client_users (id, client_id, email, "
                "password_hash, full_name, must_change_password, created_at) "
                "VALUES (:uid, :cid, :email, 'x', 'Test', false, now())"
            ),
            {
                "uid": str(user_id),
                "cid": str(client_id),
                "email": f"cliente-{user_id.hex[:8]}@test.invalid",
            },
        )
    return user_id


async def _collect_sse_events(
    channel: str, count: int, timeout_s: float = 2.0,
) -> list[SseEvent]:
    """Subscribe channel · collect up to N events with timeout."""
    collected: list[SseEvent] = []
    sub_iter = sse_dispatcher.subscribe(channel)

    async def _consume():
        try:
            async for event in sub_iter:
                collected.append(event)
                if len(collected) >= count:
                    break
        except asyncio.CancelledError:
            pass

    try:
        await asyncio.wait_for(_consume(), timeout=timeout_s)
    except asyncio.TimeoutError:
        pass
    finally:
        await sub_iter.aclose()

    return collected


# ════════════════════════════════════════════════════════════════════
# Phase 2D · SSE whitelist + audience filter coverage
# ════════════════════════════════════════════════════════════════════


def test_client_notification_event_in_whitelist():
    """`client_notification.created` debe estar en CLIENTE_EVENT_TYPES whitelist."""
    assert "client_notification.created" in CLIENTE_EVENT_TYPES


def test_client_notification_audience_filter_cliente_permits():
    """Cliente recibe `client_notification.created` (audience filter true)."""
    assert event_matches_audience(
        "client_notification.created",
        "cliente",
        {"notification_id": "abc", "type": "report_available"},
    ) is True


def test_client_notification_audience_filter_admin_denies():
    """Admin NO recibe `client_notification.created` (cliente-only namespace)."""
    assert event_matches_audience(
        "client_notification.created",
        "admin",
        {},
    ) is False


# ════════════════════════════════════════════════════════════════════
# Phase 2D · SSE dispatch fired on emit_client_notification
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_emit_client_notification_dispatches_sse(
    db: AsyncSession,
) -> None:
    """emit_client_notification debe dispatch SSE `client_notification.created`."""
    client_id_str, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    client_id = uuid.UUID(client_id_str)
    user_id = await _create_active_client_user(db, client_id=client_id)

    # Subscribe ANTES emit · collect 1 event
    channel = f"project:{project_uuid}"
    collector_task = asyncio.create_task(
        _collect_sse_events(channel, count=1, timeout_s=2.0),
    )
    # Yield para que subscribe registre antes del dispatch
    await asyncio.sleep(0.05)

    await emit_client_notification(
        db,
        project_id=project_uuid,
        client_user_id=user_id,
        type="report_available",
        title="Reporte mensual disponible",
        body="Tu informe de compliance mensual está listo.",
        target_url="/client-portal/inbox",
        priority="normal",
        emitted_by_motor="m_cloud_connectors",
        payload={"snapshot_id": str(uuid.uuid4())},
    )
    await db.flush()

    events = await collector_task
    assert len(events) >= 1, "SSE dispatch debió ocurrir post emit_client_notification"

    evt = events[0]
    assert evt.type == "client_notification.created"
    assert evt.data["type"] == "report_available"
    assert evt.data["title"] == "Reporte mensual disponible"
    assert evt.data["target_url"] == "/client-portal/inbox"
    assert evt.data["priority"] == "normal"
    assert evt.data["client_user_id"] == str(user_id)
    assert evt.data["emitted_by_motor"] == "m_cloud_connectors"
    assert "notification_id" in evt.data


# ════════════════════════════════════════════════════════════════════
# Phase 2D · audit_log emit Sub-atom 5.A 3-way OR
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_emit_client_notification_writes_audit_log(
    db: AsyncSession,
) -> None:
    """audit_log entry `cliente.notif.dispatched` debe persistir Sub-atom 5.A."""
    client_id_str, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    client_id = uuid.UUID(client_id_str)
    user_id = await _create_active_client_user(db, client_id=client_id)

    notif = await emit_client_notification(
        db,
        project_id=project_uuid,
        client_user_id=user_id,
        type="acta_review",
        title="Acta lista para tu revisión",
        body="Marcos firmó · ahora revisas.",
        target_url="/client-portal/actas",
        priority="high",
        emitted_by_motor="m05",
    )
    await db.flush()

    async with _admin_setup(db):
        row = (await db.execute(
            text(
                "SELECT accion, project_id, client_id, tabla, payload_new, "
                "usuario "
                "FROM audit_log "
                "WHERE registro_id = :rid AND accion = :acc"
            ),
            {"rid": str(notif.id), "acc": "cliente.notif.dispatched"},
        )).first()

    assert row is not None, (
        "audit_log row cliente.notif.dispatched debe estar persistida"
    )
    assert str(row[1]) == project_id_str, (
        "audit_log.project_id propagated Sub-atom 5.A"
    )
    assert str(row[2]) == client_id_str, (
        "audit_log.client_id propagated Sub-atom 5.A"
    )
    assert row[3] == "client_notification", "tabla canonical = client_notification"
    assert row[5] == "m05", "usuario = emitted_by_motor (audit trail)"

    payload = row[4]
    assert payload["type"] == "acta_review"
    assert payload["priority"] == "high"
    assert payload["target_url"] == "/client-portal/actas"


# ════════════════════════════════════════════════════════════════════
# Phase 2D · Graceful degradation · SSE failure NO bloquea primary persist
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_emit_client_notification_sse_failure_does_not_block_persist(
    db: AsyncSession,
    monkeypatch,
) -> None:
    """SSE dispatch raise → ClientNotification PERSISTED (best-effort try/except)."""
    client_id_str, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    client_id = uuid.UUID(client_id_str)
    user_id = await _create_active_client_user(db, client_id=client_id)

    async def _boom(*args, **kwargs):
        raise RuntimeError("Simulated SSE dispatcher crash")

    monkeypatch.setattr(sse_dispatcher, "dispatch", _boom)

    # emit NO debe propagar la excepción · primary persist completa
    notif = await emit_client_notification(
        db,
        project_id=project_uuid,
        client_user_id=user_id,
        type="evidence_request",
        title="Test evidence request",
        body=None,
        target_url="/client-portal/evidencias",
        priority="normal",
        emitted_by_motor="m05",
    )
    await db.flush()

    # ClientNotification row persisted empirical
    async with _admin_setup(db):
        rows = (await db.execute(
            select(ClientNotification).where(
                ClientNotification.id == notif.id,
            )
        )).scalars().all()
    assert len(rows) == 1, (
        "Primary persist must succeed despite SSE failure (best-effort)"
    )
    assert rows[0].type == "evidence_request"


# ════════════════════════════════════════════════════════════════════
# Phase 2D · Forward-compat · ALL VALID_TYPES single emit path
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_emit_client_notification_dispatch_forward_compat_all_types(
    db: AsyncSession,
) -> None:
    """DRY centralizado · emit_client_notification dispatch SSE for any VALID_TYPE.

    Test 4 types representativos (incluyendo report_available · acta_review ·
    evidence_request · compliance_confirmation) · single emit fn cubre todos.
    """
    client_id_str, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    client_id = uuid.UUID(client_id_str)
    user_id = await _create_active_client_user(db, client_id=client_id)

    channel = f"project:{project_uuid}"
    types_to_test = [
        ("report_available", "Reporte disponible", "/client-portal/inbox"),
        ("acta_review", "Acta revisar", "/client-portal/actas"),
        ("evidence_request", "Evidencia", "/client-portal/evidencias"),
        ("compliance_confirmation", "Conformidad", "/client-portal/conformidad"),
    ]

    collector_task = asyncio.create_task(
        _collect_sse_events(channel, count=len(types_to_test), timeout_s=3.0),
    )
    await asyncio.sleep(0.05)

    for notif_type, title, target_url in types_to_test:
        await emit_client_notification(
            db,
            project_id=project_uuid,
            client_user_id=user_id,
            type=notif_type,
            title=title,
            body=None,
            target_url=target_url,
            priority="normal",
            emitted_by_motor="test",
        )
    await db.flush()

    events = await collector_task
    received_types = {evt.data.get("type") for evt in events}
    expected_types = {t[0] for t in types_to_test}
    assert expected_types.issubset(received_types), (
        f"Forward-compat falla · esperados {expected_types} · "
        f"recibidos {received_types}"
    )
