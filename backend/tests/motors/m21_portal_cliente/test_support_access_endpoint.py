"""Acceso de soporte · endpoint POST /clients/{id}/support-access + audit + revoke.

Verifica lo que importa (decisiones Marcos):
  1. audit_log support.access.started: quién (admin) + a quién (client_id) + cuándo.
     (prueba legal art.15 RGPD)
  2. require_owner: la puerta de soporte SOLO la abre el admin (cliente → rechazado).
  3. La sesión acuñada lleva claim support=true (enlace puerta↔muro read-only).
  + revoke: logout de una sesión de soporte → support.access.ended.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.app.auth import crypto
from backend.app.motors.m21_portal_cliente import auth_service
from backend.tests.conftest import _admin_setup, setup_test_project

# id del _StubMarcosUser (conftest · default admin auth en tests motor).
STUB_MARCOS_ID = "00000000-0000-0000-0000-000000000099"
SUPPORT = "/api/v1/clients/{cid}/support-access"


async def _ensure_admin_row(db):
    """auth_users row con el id del stub (FK de support_admin_user_id).

    Email único propio (NO 'marcos@fulkro.es', que ya existe en fulkro_test con
    otro id → violaría UNIQUE(email)). El `usuario` del audit sale de admin.email
    del stub, no de esta fila → la fila solo cubre el FK por id.
    """
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO auth_users (id, email, password_hash, role, "
            " created_at, updated_at) "
            "VALUES (:id, 'support-stub-099@fulkro.es', 'x', 'owner', "
            " now(), now()) "
            "ON CONFLICT (id) DO NOTHING"
        ), {"id": STUB_MARCOS_ID})


async def _client_with_active_user(db) -> str:
    client_id_str, _p = await setup_test_project(db)
    await auth_service.create_user(
        db, uuid.UUID(client_id_str), "portal@example.com", "Cliente Portal",
    )
    await db.flush()
    return client_id_str


@pytest.mark.asyncio
async def test_support_access_starts_audits_and_carries_support_claim(
    async_client, db,
):
    """Admin abre soporte → 200 + audit started (quién/a quién/cuándo) + claim."""
    await _ensure_admin_row(db)
    client_id = await _client_with_active_user(db)

    r = await async_client.post(SUPPORT.format(cid=client_id))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["started"] is True
    assert body["client_user_email"] == "portal@example.com"

    # (3) la cookie acuñada lleva claim support=true.
    token = r.cookies.get("fulkro_session")
    assert token, "no se setó fulkro_session"
    payload = crypto.decode_token(token)
    assert payload.get("support") is True
    assert payload.get("sub", "").startswith("client:")

    # (1) audit_log support.access.started · quién + a quién + cuándo.
    async with _admin_setup(db):
        row = (await db.execute(text(
            "SELECT usuario, client_id, timestamp, payload_new FROM audit_log "
            "WHERE accion = 'support.access.started' AND client_id = :cid"
        ), {"cid": client_id})).first()
    assert row is not None, "no quedó fila support.access.started"
    assert row[0] == "marcos@fulkro.es"      # quién (admin)
    assert str(row[1]) == client_id          # a quién (cliente)
    assert row[2] is not None                # cuándo (timestamp)
    assert row[3]["admin_user_id"] == STUB_MARCOS_ID


@pytest.mark.real_auth
@pytest.mark.asyncio
async def test_support_access_requires_owner_cliente_rejected(async_client, db):
    """(2) Un usuario CLIENTE (no admin) NO puede abrir soporte → require_owner."""
    client_id_str, _p = await setup_test_project(db)
    _u, temp = await auth_service.create_user(
        db, uuid.UUID(client_id_str), "portal@example.com", "Cliente",
    )
    _user, token, csrf, _e = await auth_service.login(
        db, "portal@example.com", temp,
    )
    await db.execute(text("RESET ROLE"))
    await db.flush()

    r = await async_client.post(
        SUPPORT.format(cid=client_id_str),
        cookies={"fulkro_session": token, "fulkro_csrf": csrf},
        headers={"X-CSRF-Token": csrf},
    )
    assert r.status_code in (401, 403), r.text  # solo admin abre la puerta


@pytest.mark.real_auth
@pytest.mark.asyncio
async def test_support_logout_emits_ended(async_client, db):
    """Revoke explícito: logout de una sesión de soporte → support.access.ended."""
    await _ensure_admin_row(db)
    client_id_str, _p = await setup_test_project(db)
    user, _t = await auth_service.create_user(
        db, uuid.UUID(client_id_str), "portal@example.com", "Cliente",
    )
    token, csrf, _e = await auth_service.mint_support_session(
        db, user, uuid.UUID(STUB_MARCOS_ID),
    )
    await db.execute(text("RESET ROLE"))
    await db.flush()

    # logout (permitido a la sesión de soporte · excepción self-logout del guard).
    r = await async_client.post(
        "/api/v1/client-auth/logout",
        cookies={"fulkro_session": token, "fulkro_csrf": csrf},
        headers={"X-CSRF-Token": csrf},
    )
    assert r.status_code == 200, r.text

    async with _admin_setup(db):
        row = (await db.execute(text(
            "SELECT usuario, client_id, payload_new FROM audit_log "
            "WHERE accion = 'support.access.ended' AND client_id = :cid"
        ), {"cid": client_id_str})).first()
    assert row is not None, "no quedó fila support.access.ended"
    assert str(row[1]) == client_id_str                  # a quién
    # Atribución durable del admin: admin_user_id en el payload (ended resuelve
    # el email desde auth_users por id · en prod = mismo row que started).
    assert row[2]["admin_user_id"] == STUB_MARCOS_ID
    assert row[2]["reason"] == "logout"


@pytest.mark.real_auth
@pytest.mark.asyncio
async def test_me_exposes_is_support_access_for_banner(async_client, db):
    """GET /client-portal/me expone is_support_access (+ expiry) → banner frontend."""
    await _ensure_admin_row(db)
    client_id_str, _p = await setup_test_project(db)
    user, temp = await auth_service.create_user(
        db, uuid.UUID(client_id_str), "portal@example.com", "Cliente",
    )

    # Sesión de SOPORTE → /me marca is_support_access=True + expiry.
    s_token, s_csrf, _e = await auth_service.mint_support_session(
        db, user, uuid.UUID(STUB_MARCOS_ID),
    )
    await db.execute(text("RESET ROLE"))
    await db.flush()
    rs = await async_client.get(
        "/api/v1/client-portal/me",
        cookies={"fulkro_session": s_token, "fulkro_csrf": s_csrf},
    )
    assert rs.status_code == 200, rs.text
    assert rs.json()["is_support_access"] is True
    assert rs.json()["support_expires_at"] is not None

    # Sesión NORMAL → is_support_access False (sin banner).
    _u, n_token, n_csrf, _e2 = await auth_service.login(
        db, "portal@example.com", temp,
    )
    await db.execute(text("RESET ROLE"))
    await db.flush()
    rn = await async_client.get(
        "/api/v1/client-portal/me",
        cookies={"fulkro_session": n_token, "fulkro_csrf": n_csrf},
    )
    assert rn.status_code == 200, rn.text
    assert rn.json()["is_support_access"] is False
