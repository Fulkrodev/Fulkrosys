"""Batch B diagnóstico previo · trigger admin POST /onboarding/precliente/sessions.

Emite la sesión precliente + magic-link sobre un proyecto ligero existente y
devuelve magic_link_url + plantilla de email branded (NO auto-send). require_owner.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from backend.app.motors.m16_onboarding.api import router as m16_router
from backend.app.auth.dependencies import require_owner
from backend.app.fulkro_identity import FULKRO_EMAIL, FULKRO_PHONE
from backend.tests.conftest import setup_test_project

ENDPOINT = "/api/v1/onboarding/precliente/sessions"


def test_trigger_endpoint_is_require_owner():
    """El trigger lleva require_owner per-endpoint (introspección · gating admin)."""
    from fastapi.routing import APIRoute
    target = None
    for route in m16_router.routes:
        if isinstance(route, APIRoute) and route.path.endswith("/precliente/sessions") \
                and "POST" in route.methods:
            target = route
            break
    assert target is not None, "endpoint /precliente/sessions no encontrado"
    dep_funcs = [d.dependency for d in target.dependencies]
    assert require_owner in dep_funcs, "el trigger debe exigir require_owner"


@pytest.mark.asyncio
async def test_trigger_rejects_non_admin(async_client, db):
    """Un no-admin (require_owner falla) → rechazado (no 200)."""
    from fastapi import HTTPException, status
    from backend.app.main import app

    _, project_id_str = await setup_test_project(db)

    async def _deny():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

    app.dependency_overrides[require_owner] = _deny
    try:
        r = await async_client.post(ENDPOINT, json={
            "project_id": project_id_str,
            "interlocutor_email": "lead@example.com",
            "interlocutor_name": "Lead Frío",
        })
    finally:
        app.dependency_overrides.pop(require_owner, None)
    assert r.status_code == 403, r.text


@pytest.mark.asyncio
async def test_trigger_returns_usable_magic_link_and_branded_email(async_client, db):
    """Happy path (owner stub): devuelve magic_link_url USABLE + email branded.

    'Usable' = el token consume correctamente (flujo del lead real · fix F-18).
    """
    _, project_id_str = await setup_test_project(db)

    r = await async_client.post(ENDPOINT, json={
        "project_id": project_id_str,
        "interlocutor_email": "lead@example.com",
        "interlocutor_name": "Lead Frío",
    })
    assert r.status_code == 200, r.text
    body = r.json()

    # magic-link emitido.
    assert body["magic_link_id"] is not None
    url = body["magic_link_url"]
    assert url and "token=" in url

    # email branded: violeta + firma canónica (fulkro_identity) + el enlace.
    email = body["email"]
    assert email["subject"]
    assert "#6C63FF" in email["html"]
    assert FULKRO_PHONE in email["html"] and FULKRO_EMAIL in email["html"]
    assert url in email["html"]
    assert url in email["text"]
    # NUNCA precio (coherente con outreach en frío).
    assert "€" not in email["html"] and "precio" not in email["text"].lower()

    # USABLE: el token consume (réplica del lead · contexto limpio, fix F-18).
    await db.execute(text(
        "SELECT set_config('app.current_project_id', '', true), "
        "       set_config('app.current_client_id', '', true)"
    ))
    token = url.split("token=")[1]
    c = await async_client.post("/api/v1/onboarding/consume", json={"token": token})
    assert c.status_code == 200, c.text
    assert c.json()["session_secret"]
    assert c.json()["total_questions"] == 17
