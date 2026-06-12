"""Tests continuidad admin API · feat/fulkro-100 Ola A.

Valida el remate del lado admin del loop de continuidad:
- el buzón (require_owner) lee el cuestionario + decisiones del cliente
- notify-draft-ready responde ok y no 404 sobre proyecto real
- auth gate (sin owner → 401/403)
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import text

from backend.app.motors.m19_risk.cliente_continuidad_service import (
    record_approval,
    upsert_input,
)

pytestmark = pytest.mark.real_auth

_BASE = "/api/v1/admin/projects"


async def _login_owner(async_client) -> str:
    res = await async_client.post("/api/v1/_dev/login-as-marcos")
    assert res.status_code == 200, res.text
    return async_client.cookies.get("fulkro_csrf") or ""


async def _set_rls(db, project_id: str, client_id: str) -> None:
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": project_id},
    )
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": client_id},
    )


@pytest.mark.asyncio
async def test_buzon_requires_owner(async_client):
    """Sin login owner → 401/403 (router require_owner)."""
    res = await async_client.get(f"{_BASE}/{uuid.uuid4()}/continuidad/buzon")
    assert res.status_code in (401, 403), res.text


@pytest.mark.asyncio
async def test_buzon_unknown_project_404(async_client):
    await _login_owner(async_client)
    res = await async_client.get(f"{_BASE}/{uuid.uuid4()}/continuidad/buzon")
    assert res.status_code == 404, res.text


@pytest.mark.asyncio
async def test_buzon_empty_returns_defaults(async_client, db):
    from backend.tests.conftest import setup_test_project

    _, project_id = await setup_test_project(db)
    await _login_owner(async_client)
    res = await async_client.get(f"{_BASE}/{project_id}/continuidad/buzon")
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["has_questionnaire"] is False
    assert data["approvals"] == []
    assert data["pending_comments"] == 0


@pytest.mark.asyncio
async def test_buzon_reflects_cliente_submission(async_client, db):
    from backend.tests.conftest import setup_test_project

    client_obj, project_id = await setup_test_project(db)
    client_id = str(getattr(client_obj, "id", client_obj))
    await _set_rls(db, project_id, client_id)

    # El cliente envía su cuestionario + pide un cambio en el borrador BIA.
    await upsert_input(
        db,
        project_id=uuid.UUID(project_id),
        client_user_id=uuid.uuid4(),
        rto_horas_tolerancia=8,
        rpo_horas_tolerancia=2,
        impacto_diario_eur=Decimal("4200.00"),
        procesos_criticos=[{"nombre": "Facturación"}],
        completed=True,
    )
    await record_approval(
        db,
        project_id=uuid.UUID(project_id),
        client_user_id=uuid.uuid4(),
        artifact_type="bia",
        draft_id=uuid.uuid4(),
        action="comment",
        comment_text="¿Podemos bajar el RTO a 4h?",
    )
    await db.commit()

    await _login_owner(async_client)
    res = await async_client.get(f"{_BASE}/{project_id}/continuidad/buzon")
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["has_questionnaire"] is True
    assert data["questionnaire"]["rto_horas_tolerancia"] == 8
    assert data["questionnaire"]["completed"] is True
    assert data["pending_comments"] == 1
    assert len(data["approvals"]) == 1
    assert data["approvals"][0]["action"] == "comment"


@pytest.mark.asyncio
async def test_notify_draft_ready_ok(async_client, db):
    from backend.tests.conftest import setup_test_project

    _, project_id = await setup_test_project(db)
    csrf = await _login_owner(async_client)
    res = await async_client.post(
        f"{_BASE}/{project_id}/continuidad/notify-draft-ready",
        json={"artifact_type": "drp", "message": "Tu plan ya está listo"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["ok"] is True
    assert data["event_type"] == "continuidad.draft_ready"


@pytest.mark.asyncio
async def test_notify_draft_ready_unknown_project_404(async_client):
    csrf = await _login_owner(async_client)
    res = await async_client.post(
        f"{_BASE}/{uuid.uuid4()}/continuidad/notify-draft-ready",
        json={"artifact_type": "bia"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 404, res.text
