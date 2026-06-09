"""Frente 2 · Pieza 2 · modificar usuario cliente (cockpit · require_owner).

PATCH /clients/{client_id}/users/{user_id} edita email/full_name. Email duplicado
en el mismo cliente → 409 controlado (pre-check · NO IntegrityError/500).
Auth admin vía stub default de conftest (cockpit require_owner).
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text

from backend.app.models.client_portal import ClientUser
from backend.app.motors.m21_portal_cliente import auth_service
from backend.tests.conftest import _admin_setup, setup_test_project

USERS = "/api/v1/clients/{cid}/users/{uid}"


@pytest.mark.asyncio
async def test_update_user_changes_email_and_full_name(async_client, db):
    client_id_str, _p = await setup_test_project(db)
    user, _t = await auth_service.create_user(
        db, uuid.UUID(client_id_str), "orig@example.com", "Nombre Orig",
    )
    await db.flush()

    r = await async_client.patch(
        USERS.format(cid=client_id_str, uid=str(user.id)),
        json={"email": "nuevo@example.com", "full_name": "Nombre Nuevo"},
    )
    assert r.status_code == 200, r.text

    async with _admin_setup(db):
        refreshed = (await db.execute(
            select(ClientUser).where(ClientUser.id == user.id)
        )).scalar_one()
    assert refreshed.email == "nuevo@example.com"      # normalizado lower
    assert refreshed.full_name == "Nombre Nuevo"


@pytest.mark.asyncio
async def test_update_user_duplicate_email_returns_409_not_500(async_client, db):
    client_id_str, _p = await setup_test_project(db)
    user, _t = await auth_service.create_user(
        db, uuid.UUID(client_id_str), "orig@example.com", "Orig",
    )
    # 2º usuario del MISMO cliente con el email 'taken' (seed directo · la
    # constraint UNIQUE(client_id,email) aplica a todos, activos o no).
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO client_users (id, client_id, email, password_hash, "
            " must_change_password, failed_attempts, created_at, updated_at) "
            "VALUES (gen_random_uuid(), :cid, 'taken@example.com', 'x', "
            " true, 0, now(), now())"
        ), {"cid": client_id_str})
    await db.flush()

    r = await async_client.patch(
        USERS.format(cid=client_id_str, uid=str(user.id)),
        json={"email": "taken@example.com"},
    )
    assert r.status_code == 409, r.text      # controlado · NO 500
    assert "Ya existe" in r.json()["detail"]

    # El email original NO cambió (rollback lógico del pre-check).
    async with _admin_setup(db):
        refreshed = (await db.execute(
            select(ClientUser).where(ClientUser.id == user.id)
        )).scalar_one()
    assert refreshed.email == "orig@example.com"


@pytest.mark.asyncio
async def test_update_user_empty_body_400(async_client, db):
    client_id_str, _p = await setup_test_project(db)
    user, _t = await auth_service.create_user(
        db, uuid.UUID(client_id_str), "orig@example.com", "Orig",
    )
    await db.flush()
    r = await async_client.patch(
        USERS.format(cid=client_id_str, uid=str(user.id)), json={},
    )
    assert r.status_code == 400, r.text
