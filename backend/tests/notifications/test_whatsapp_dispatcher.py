"""Tests for whatsapp_dispatcher · MB-8 atom 8.2."""
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text

from backend.app.motors.m31_whatsapp.dialog_360_client import Dialog360Client
from backend.app.motors.m31_whatsapp.service import WhatsAppService
from backend.app.notifications.whatsapp_dispatcher import (
    dispatch_critical_event,
    send_basica_digest_for_project,
)
from backend.tests.conftest import _admin_setup


pytestmark = pytest.mark.asyncio


async def _seed(db, *, tier: str = "MEDIA", opted_in: bool = True):
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    now = datetime.now(timezone.utc) if opted_in else None
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO clients (id, nombre, cif, created_at) "
            "VALUES (:id, 'TC', :cif, now())"
        ), {"id": str(client_id), "cif": cif})
        await db.execute(text(
            "INSERT INTO projects (id, client_id, nombre, fase, "
            " categoria_objetivo, whatsapp_enabled, created_at) "
            "VALUES (:id, :cid, 'P', 'retainer_cierre', :cat, true, now())"
        ), {"id": str(project_id), "cid": str(client_id), "cat": tier})
        await db.execute(text(
            "INSERT INTO client_users (id, client_id, email, full_name, "
            " password_hash, whatsapp_number, whatsapp_verified_at, "
            " whatsapp_opt_in_at, created_at) "
            "VALUES (:id, :cid, :em, 'TU', 'x', '+34666555444', "
            " :ts, :ts, now())"
        ), {
            "id": str(user_id),
            "cid": str(client_id),
            "em": f"t+{uuid.uuid4().hex[:6]}@e.com",
            "ts": now,
        })
    await db.execute(
        text("SELECT set_config('app.current_client_id', :v, true)"),
        {"v": str(client_id)},
    )
    await db.execute(
        text("SELECT set_config('app.current_project_id', :v, true)"),
        {"v": str(project_id)},
    )
    await db.flush()
    return client_id, project_id, user_id


async def test_dispatch_critical_unknown_event_skipped(db):
    _, project_id, user_id = await _seed(db, tier="MEDIA")
    svc = WhatsAppService(client=Dialog360Client(mock_mode=True))
    r = await dispatch_critical_event(
        db, event_type="never_seen_event",
        project_id=project_id, client_user_id=user_id,
        payload={}, wa_service=svc,
    )
    assert r.dispatched is False
    assert r.skipped_reason and "no_routing" in r.skipped_reason


async def test_dispatch_critical_alta_tier_sends_whatsapp(db):
    _, project_id, user_id = await _seed(db, tier="ALTA")
    svc = WhatsAppService(client=Dialog360Client(mock_mode=True))
    r = await dispatch_critical_event(
        db, event_type="dpc_anual_due_30d",
        project_id=project_id, client_user_id=user_id,
        payload={"link": "https://fulkro.es/x"},
        wa_service=svc,
    )
    assert r.dispatched is True
    assert r.route == "whatsapp"
    assert r.message_id is not None


async def test_dispatch_critical_basica_drift_is_digest(db):
    """drift_critical_detected on BASICA tier · route='digest' · skip immediate."""
    _, project_id, user_id = await _seed(db, tier="BASICA")
    svc = WhatsAppService(client=Dialog360Client(mock_mode=True))
    r = await dispatch_critical_event(
        db, event_type="drift_critical_detected",
        project_id=project_id, client_user_id=user_id,
        payload={"dim": "evidencias", "link": "https://fulkro.es/d"},
        wa_service=svc,
    )
    assert r.dispatched is False
    assert r.route == "digest"


async def test_dispatch_critical_no_opt_in_skipped(db):
    _, project_id, user_id = await _seed(db, tier="MEDIA", opted_in=False)
    svc = WhatsAppService(client=Dialog360Client(mock_mode=True))
    r = await dispatch_critical_event(
        db, event_type="conformidad_signature_pending",
        project_id=project_id, client_user_id=user_id,
        payload={"link": "https://fulkro.es/f"},
        wa_service=svc,
    )
    assert r.dispatched is False
    assert r.skipped_reason == "no_opt_in"


async def test_basica_digest_no_events_skips(db):
    _, project_id, user_id = await _seed(db, tier="BASICA")
    svc = WhatsAppService(client=Dialog360Client(mock_mode=True))
    summary = await send_basica_digest_for_project(
        db, project_id=project_id, client_user_id=user_id,
        wa_service=svc,
    )
    assert summary.events_in_window == 0
    assert summary.sent is False


async def test_basica_digest_sends_when_events_exist(db):
    _, project_id, user_id = await _seed(db, tier="BASICA")

    # Insert 1 HIGH drift event within window
    async with _admin_setup(db):
        # First need a retainer_contract row referenced by drift event FK
        retainer_id = uuid.uuid4()
        client_id = (await db.execute(text(
            "SELECT client_id FROM projects WHERE id = :p"
        ), {"p": str(project_id)})).scalar()
        await db.execute(text(
            "INSERT INTO retainer_contracts "
            "(id, client_id, project_id, modalidad, precio_mensual, perfil, "
            " estado, inicio, created_at) "
            "VALUES (:id, :cid, :pid, 'mensual', 700, 'R_STD', 'activo', "
            " CURRENT_DATE, now())"
        ), {
            "id": str(retainer_id),
            "cid": str(client_id),
            "pid": str(project_id),
        })
        await db.execute(text(
            "INSERT INTO retainer_drift_events "
            "(retainer_contract_id, project_id, dimension, descripcion, "
            " severidad, impacto, estado, created_at) "
            "VALUES (:rid, :pid, 'evidencias', 'test', 'HIGH', 'EVIDENCE', "
            " 'open', now())"
        ), {"rid": str(retainer_id), "pid": str(project_id)})
    await db.flush()

    svc = WhatsAppService(client=Dialog360Client(mock_mode=True))
    summary = await send_basica_digest_for_project(
        db, project_id=project_id, client_user_id=user_id,
        wa_service=svc,
    )
    assert summary.events_in_window >= 1
    assert summary.sent is True
