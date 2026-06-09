"""Tests integración auth_service con hash chain audit (ADR-038 SAN-D MB-14.2).

Verifica que login_success y session_revoked persisten:
1. Row legacy via _log_audit (sin chain_index · backward compat)
2. Row hash chain via _log_audit_chain (chain_index NOT NULL · ADR-038)

Project resolution backward compat: si client no tiene proyectos · solo
legacy row · NO chain row · login flow continúa OK.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text

from backend.app.models.client_portal import ClientUserAudit
from backend.app.motors.m21_portal_cliente.auth_service import (
    _log_audit_chain,
    _resolve_active_project_id,
)
from backend.tests.conftest import _admin_setup


async def _setup_client_with_project(db):
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    client_user_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, 'Test', :cif, now())"
            ),
            {"id": str(client_id), "cif": cif},
        )
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, created_at) "
                "VALUES (:id, :cid, 'P', now())"
            ),
            {"id": str(project_id), "cid": str(client_id)},
        )
        await db.execute(
            text(
                "INSERT INTO client_users (id, client_id, email, "
                "password_hash, created_at) "
                "VALUES (:id, :cid, :email, 'h', now())"
            ),
            {
                "id": str(client_user_id),
                "cid": str(client_id),
                "email": f"{client_user_id.hex[:6]}@t.es",
            },
        )
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(project_id)},
    )
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": str(client_id)},
    )
    await db.flush()
    # Wrap in a class-like with .id and .client_id for _log_audit_chain
    class _U:
        def __init__(self, id_, client_id_):
            self.id = id_
            self.client_id = client_id_
    return _U(client_user_id, client_id), project_id


@pytest.mark.asyncio
async def test_resolve_active_project_returns_latest(db):
    user, project_id = await _setup_client_with_project(db)
    resolved = await _resolve_active_project_id(db, user.client_id)
    assert resolved == project_id


@pytest.mark.asyncio
async def test_resolve_active_project_none_when_no_projects(db):
    client_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, 'X', :cif, now())"
            ),
            {"id": str(client_id), "cif": cif},
        )
    await db.flush()
    resolved = await _resolve_active_project_id(db, client_id)
    assert resolved is None


@pytest.mark.asyncio
async def test_log_audit_chain_creates_hash_chain_entry(db):
    user, project_id = await _setup_client_with_project(db)

    await _log_audit_chain(
        db, user, "LOGIN",
        action_data={"method": "password"},
        ip="10.0.0.1",
        user_agent="UA",
        session_id="sess1234",
    )
    await db.flush()

    rows = (
        await db.execute(
            select(ClientUserAudit)
            .where(ClientUserAudit.project_id == project_id)
            .where(ClientUserAudit.chain_index.is_not(None))
        )
    ).scalars().all()
    rows = list(rows)
    assert len(rows) == 1
    assert rows[0].chain_index == 0
    assert rows[0].action_type == "LOGIN"
    assert rows[0].current_hash is not None


@pytest.mark.asyncio
async def test_log_audit_chain_silent_when_no_project(db):
    """Backward compat: client sin proyecto · skip silent · NO raise."""
    client_id = uuid.uuid4()
    client_user_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, 'X', :cif, now())"
            ),
            {"id": str(client_id), "cif": cif},
        )
        await db.execute(
            text(
                "INSERT INTO client_users (id, client_id, email, "
                "password_hash, created_at) "
                "VALUES (:id, :cid, :email, 'h', now())"
            ),
            {
                "id": str(client_user_id),
                "cid": str(client_id),
                "email": f"{client_user_id.hex[:6]}@t.es",
            },
        )
    await db.flush()

    class _U:
        def __init__(self, id_, client_id_):
            self.id = id_
            self.client_id = client_id_

    user = _U(client_user_id, client_id)

    # Should NOT raise
    await _log_audit_chain(db, user, "LOGIN", action_data={})
    await db.flush()

    # NO chain rows created
    rows = (
        await db.execute(
            select(ClientUserAudit)
            .where(ClientUserAudit.client_user_id == client_user_id)
            .where(ClientUserAudit.chain_index.is_not(None))
        )
    ).scalars().all()
    assert len(list(rows)) == 0
