"""Ola 3 · aislamiento cross-tenant del stream SSE cliente (las DOS caras).

Hueco real detectado en el plan: el ownership del stream cliente NO se testea
hoy a nivel endpoint (solo el filtro de tipo puro). Tras hacer phase_changed
cliente-facing (#14) se refuerza la garantía cross-tenant:

- CARA NEGATIVA: cliente B NO puede abrir el stream del proyecto de cliente A
  (403 · _verify_client_owns_project · gate de CANAL · NO hay fuga cross-tenant
  aunque ahora el cliente vea phase_changed de SU proyecto).
- CARA POSITIVA: cliente A SÍ accede a su propio proyecto + ve phase_changed.

El gate de canal (no el filtro de tipo) es la barrera entre clientes · #14 solo
tocó el filtro de tipo (intra-proyecto), por eso esta barrera sigue intacta.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from backend.app.api.v1.sse_client_api import _verify_client_owns_project
from backend.app.core.sse_dispatcher import event_matches_audience
from backend.app.models.client_portal import ClientUser
from backend.app.motors.m21_portal_cliente.api import get_current_client_user


async def _mk_client_with_user(db, *, nombre: str):
    """Crea cliente + proyecto + ClientUser (bajo fulkro · setup)."""
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    await db.execute(
        text(
            "INSERT INTO clients (id, nombre, cif, created_at) "
            "VALUES (:id, :n, :cif, now())"
        ),
        {"id": str(client_id), "n": nombre, "cif": cif},
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
            "INSERT INTO client_users "
            "(id, client_id, email, password_hash, created_at) "
            "VALUES (:uid, :cid, :email, 'x', now())"
        ),
        {
            "uid": str(user_id),
            "cid": str(client_id),
            "email": f"u{user_id.hex[:6]}@test.es",
        },
    )
    await db.flush()
    user = await db.get(ClientUser, user_id)
    return client_id, project_id, user


@pytest.mark.asyncio
async def test_cross_tenant_sse_ownership_gate_both_faces(db):
    _ca, project_a, user_a = await _mk_client_with_user(db, nombre="Cliente A")
    _cb, _project_b, user_b = await _mk_client_with_user(db, nombre="Cliente B")
    # Bajo fulkro la fila projects es visible → el 403 lo decide el GATE (cid),
    # no la RLS (que sería una 2ª capa). Probamos la barrera explícita.
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))

    # CARA NEGATIVA · cliente B NO puede abrir el stream del proyecto de A.
    with pytest.raises(HTTPException) as exc:
        await _verify_client_owns_project(db, user_b, project_a)
    assert exc.value.status_code == 403

    # CARA POSITIVA · cliente A SÍ accede a su propio proyecto (sin 403).
    await _verify_client_owns_project(db, user_a, project_a)  # no raise

    # Y ve phase_changed de SU proyecto (política #14 lo permite por tipo · el
    # canal ya quedó aislado por el gate de arriba).
    assert event_matches_audience(
        "phase_changed",
        "cliente",
        {"project_id": str(project_a), "old_phase": "x", "new_phase": "y"},
    ) is True


@pytest.mark.asyncio
async def test_cross_tenant_sse_endpoint_403(async_client, db):
    """A NIVEL ENDPOINT (hoy sin test) · cliente B → stream del proyecto de A → 403.

    El 403 se levanta ANTES de abrir el stream (en _verify_client_owns_project),
    así que la respuesta es inmediata · no cuelga."""
    from backend.app.main import app

    _ca, project_a, _ua = await _mk_client_with_user(db, nombre="Cliente A")
    _cb, _pb, user_b = await _mk_client_with_user(db, nombre="Cliente B")
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))

    app.dependency_overrides[get_current_client_user] = lambda: user_b
    try:
        r = await async_client.get(
            f"/api/v1/client-portal/projects/{project_a}/events",
        )
    finally:
        app.dependency_overrides.pop(get_current_client_user, None)

    assert r.status_code == 403, r.text
