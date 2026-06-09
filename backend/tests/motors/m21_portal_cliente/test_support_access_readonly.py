"""Acceso de soporte READ-ONLY · guard bulletproof en authenticate_request.

CHOKEPOINT app-level: el guard vive en authenticate_request (corre en TODAS las
rutas no-exentas, antes del endpoint). Este test demuestra EMPÍRICAMENTE que cubre
las DOS deps de auth cliente:
  - get_current_client_user (m19 incidents review)
  - require_client_user      (m_cloud connectors connect)
Una sesión de soporte (claim support=true) NO puede ejecutar métodos mutating en
ninguna → 403 support_access_read_only, ANTES del endpoint. Una sesión NORMAL
(sin claim) sigue pudiendo (cero regresión).

real_auth: usa el authenticate_request REAL (opt-out del stub autouse de conftest).
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.app.motors.m21_portal_cliente import auth_service
from backend.tests.conftest import _admin_setup, setup_test_project

pytestmark = pytest.mark.real_auth

# Rutas reales (una por cada dep de auth cliente).
INCIDENTS_REVIEW = "/api/v1/portal/incidents/{iid}/review"      # get_current_client_user
CLOUD_CONNECT = "/api/v1/client-portal/cloud-connectors/connect/m365"  # require_client_user


async def _admin_id(db) -> uuid.UUID:
    async with _admin_setup(db):
        admin_id = (await db.execute(text(
            "INSERT INTO auth_users (id, email, password_hash, role, "
            " created_at, updated_at) "
            "VALUES (gen_random_uuid(), :em, 'x', 'owner', now(), now()) "
            "RETURNING id"
        ), {"em": f"support-admin-{uuid.uuid4()}@fulkro.es"})).scalar()
    return admin_id


async def _client_user(db):
    client_id_str, _project_id = await setup_test_project(db)
    user, temp = await auth_service.create_user(
        db, uuid.UUID(client_id_str), "portal-user@example.com", "Cliente Portal",
    )
    return user, temp


def _cookies(token: str, csrf: str) -> dict:
    return {"fulkro_session": token, "fulkro_csrf": csrf}


@pytest.mark.asyncio
async def test_support_session_blocks_mutating_on_BOTH_deps(async_client, db):
    admin_id = await _admin_id(db)
    user, _temp = await _client_user(db)
    token, csrf, _exp = await auth_service.mint_support_session(db, user, admin_id)
    await db.execute(text("RESET ROLE"))  # mint hizo SET LOCAL ROLE fulkro_app_bypassrls
    await db.flush()

    cookies = _cookies(token, csrf)
    headers = {"X-CSRF-Token": csrf}

    # Dep 1 · get_current_client_user (m19) · POST mutating → 403 del GUARD.
    r1 = await async_client.post(
        INCIDENTS_REVIEW.format(iid=uuid.uuid4()),
        json={"decision": "approved"}, cookies=cookies, headers=headers,
    )
    assert r1.status_code == 403, r1.text
    assert r1.json()["detail"] == "support_access_read_only"

    # Dep 2 · require_client_user (m_cloud) · POST mutating → 403 del GUARD.
    r2 = await async_client.post(
        CLOUD_CONNECT, json={}, cookies=cookies, headers=headers,
    )
    assert r2.status_code == 403, r2.text
    assert r2.json()["detail"] == "support_access_read_only"


@pytest.mark.asyncio
async def test_support_session_allows_GET(async_client, db):
    admin_id = await _admin_id(db)
    user, _temp = await _client_user(db)
    token, csrf, _exp = await auth_service.mint_support_session(db, user, admin_id)
    await db.execute(text("RESET ROLE"))
    await db.flush()

    # GET (read-only) NO es bloqueado por el guard de soporte.
    r = await async_client.get(
        "/api/v1/portal/incidents", cookies=_cookies(token, csrf),
    )
    assert r.status_code != 403 or r.json().get("detail") != "support_access_read_only"


@pytest.mark.asyncio
async def test_normal_session_can_mutate_no_regression(async_client, db):
    """Sesión cliente NORMAL (sin claim support) → el guard NO la bloquea."""
    _user, temp = await _client_user(db)
    user2, token, csrf, _exp = await auth_service.login(
        db, "portal-user@example.com", temp,
    )
    await db.execute(text("RESET ROLE"))
    await db.flush()

    r = await async_client.post(
        INCIDENTS_REVIEW.format(iid=uuid.uuid4()),
        json={"decision": "approved"},
        cookies=_cookies(token, csrf), headers={"X-CSRF-Token": csrf},
    )
    # El guard de soporte NO se aplica (no es sesión de soporte).
    assert not (r.status_code == 403 and r.json().get("detail") == "support_access_read_only")
