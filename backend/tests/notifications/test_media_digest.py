"""Tests for MEDIA daily digest · MB-8 closure tier coverage."""
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text

from backend.app.motors.m31_whatsapp.dialog_360_client import Dialog360Client
from backend.app.motors.m31_whatsapp.service import WhatsAppService
from backend.app.notifications.whatsapp_dispatcher import (
    send_media_daily_digest_for_project,
)
from backend.tests.conftest import _admin_setup


pytestmark = pytest.mark.asyncio


async def _seed_media(db, *, opted_in: bool = True):
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
            "VALUES (:id, :cid, 'P', 'retainer_cierre', 'MEDIA', true, now())"
        ), {"id": str(project_id), "cid": str(client_id)})
        await db.execute(text(
            "INSERT INTO client_users (id, client_id, email, full_name, "
            " password_hash, whatsapp_number, whatsapp_verified_at, "
            " whatsapp_opt_in_at, created_at) "
            "VALUES (:id, :cid, :em, 'TU', 'x', '+34666555444', :ts, "
            " :ts, now())"
        ), {
            "id": str(user_id),
            "cid": str(client_id),
            "em": f"m+{uuid.uuid4().hex[:6]}@e.com",
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


async def test_media_daily_digest_zero_events_skips(db):
    _, project_id, user_id = await _seed_media(db)
    svc = WhatsAppService(client=Dialog360Client(mock_mode=True))
    summary = await send_media_daily_digest_for_project(
        db, project_id=project_id, client_user_id=user_id,
        wa_service=svc,
    )
    assert summary.events_in_window == 0
    assert summary.sent is False


async def test_media_daily_digest_sends_when_event_in_24h(db):
    _, project_id, user_id = await _seed_media(db)

    async with _admin_setup(db):
        client_id = (await db.execute(text(
            "SELECT client_id FROM projects WHERE id = :p"
        ), {"p": str(project_id)})).scalar()
        retainer_id = uuid.uuid4()
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
            "VALUES (:rid, :pid, 'normativa', 'media_event', 'HIGH', "
            " 'DOCUMENT', 'open', now())"
        ), {"rid": str(retainer_id), "pid": str(project_id)})
    await db.flush()

    svc = WhatsAppService(client=Dialog360Client(mock_mode=True))
    summary = await send_media_daily_digest_for_project(
        db, project_id=project_id, client_user_id=user_id,
        wa_service=svc,
    )
    assert summary.events_in_window >= 1
    assert summary.sent is True


async def test_media_daily_digest_no_opt_in_no_send(db):
    _, project_id, user_id = await _seed_media(db, opted_in=False)
    svc = WhatsAppService(client=Dialog360Client(mock_mode=True))
    summary = await send_media_daily_digest_for_project(
        db, project_id=project_id, client_user_id=user_id,
        wa_service=svc,
    )
    assert summary.sent is False
