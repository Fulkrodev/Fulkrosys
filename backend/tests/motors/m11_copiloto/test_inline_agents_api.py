"""Tests for /api/v1/client-portal/inline-agents/* · MB-7 atom 7.4-bis.

Auth is overridden via real_auth marker (these tests bypass via the
generic Marcos stub, NOT client portal cookie · plain HTTP tests). The
client portal user dependency would normally require a session, but
since we want to test the route logic without writing a full client
portal session fixture, we override get_current_client_user directly.
"""
import uuid

import pytest
from sqlalchemy import text

from backend.tests.conftest import _admin_setup


pytestmark = pytest.mark.asyncio


async def _setup_client_with_project(
    db, *, categoria: str = "MEDIA",
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO clients (id, nombre, cif, created_at) "
            "VALUES (:id, 'Test Client', :cif, now())"
        ), {"id": str(client_id), "cif": cif})
        await db.execute(text(
            "INSERT INTO projects (id, client_id, nombre, "
            "categoria_objetivo, created_at) "
            "VALUES (:id, :cid, 'Test', :cat, now())"
        ), {
            "id": str(project_id),
            "cid": str(client_id),
            "cat": categoria,
        })
        await db.execute(text(
            "INSERT INTO client_users (id, client_id, email, full_name, "
            "password_hash, created_at) "
            "VALUES (:id, :cid, :em, 'Test User', 'x', now())"
        ), {
            "id": str(user_id),
            "cid": str(client_id),
            "em": f"test+{uuid.uuid4().hex[:6]}@example.com",
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


def _override_client_user(app, user, db):
    """Override get_current_client_user dependency for client portal tests."""
    from backend.app.motors.m21_portal_cliente.api import get_current_client_user

    async def _override():
        return user

    app.dependency_overrides[get_current_client_user] = _override


async def test_list_inline_agents_returns_tier_map(db, async_client):
    from backend.app.main import app
    from backend.app.models.client_portal import ClientUser

    _, _, user_id = await _setup_client_with_project(db, categoria="MEDIA")
    user = (await db.execute(
        text("SELECT * FROM client_users WHERE id = :i"),
        {"i": str(user_id)},
    )).mappings().first()
    fake = ClientUser(
        id=user_id, client_id=user["client_id"],
        email=user["email"], full_name=user["full_name"],
    )
    _override_client_user(app, fake, db)

    r = await async_client.get("/api/v1/client-portal/inline-agents")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["tier"] == "MEDIA"
    by_slug = {a["slug"]: a for a in data["agents"]}
    # BASICA + MEDIA agents available; ALTA-only would be unavailable but
    # the registry today has only BASICA/MEDIA tiers.
    assert by_slug["a04_redactor_summary"]["available"] is True
    assert by_slug["a11_auditor_virtual_check"]["available"] is True
    app.dependency_overrides.pop(
        __import__(
            "backend.app.motors.m21_portal_cliente.api",
            fromlist=["get_current_client_user"],
        ).get_current_client_user,
        None,
    )


async def test_invoke_inline_agent_tier_forbidden_returns_403(db, async_client):
    from backend.app.main import app
    from backend.app.models.client_portal import ClientUser
    from backend.app.motors.m21_portal_cliente.api import get_current_client_user

    _, _, user_id = await _setup_client_with_project(db, categoria="BASICA")
    user = (await db.execute(
        text("SELECT * FROM client_users WHERE id = :i"),
        {"i": str(user_id)},
    )).mappings().first()
    fake = ClientUser(
        id=user_id, client_id=user["client_id"],
        email=user["email"], full_name=user["full_name"],
    )
    app.dependency_overrides[get_current_client_user] = lambda: fake

    # a11 requires MEDIA · BASICA tier should be forbidden
    r = await async_client.post(
        "/api/v1/client-portal/inline-agents/a11_auditor_virtual_check/invoke",
        json={"user_message": "Test"},
    )
    assert r.status_code == 403, r.text
    assert "BASICA" in r.json()["detail"] or "requires" in r.json()["detail"].lower() or "tier" in r.json()["detail"].lower() or "categoría" in r.json()["detail"]
    app.dependency_overrides.pop(get_current_client_user, None)


async def test_invoke_inline_agent_invalid_slug_404(db, async_client):
    from backend.app.main import app
    from backend.app.models.client_portal import ClientUser
    from backend.app.motors.m21_portal_cliente.api import get_current_client_user

    _, _, user_id = await _setup_client_with_project(db, categoria="ALTA")
    user = (await db.execute(
        text("SELECT * FROM client_users WHERE id = :i"),
        {"i": str(user_id)},
    )).mappings().first()
    fake = ClientUser(
        id=user_id, client_id=user["client_id"],
        email=user["email"], full_name=user["full_name"],
    )
    app.dependency_overrides[get_current_client_user] = lambda: fake

    r = await async_client.post(
        "/api/v1/client-portal/inline-agents/nonexistent_agent/invoke",
        json={"user_message": "Test"},
    )
    assert r.status_code == 404
    app.dependency_overrides.pop(get_current_client_user, None)


async def test_invoke_inline_agent_basica_tier_allows_basica_agent(db, async_client):
    from backend.app.main import app
    from backend.app.models.client_portal import ClientUser
    from backend.app.motors.m21_portal_cliente.api import get_current_client_user

    _, _, user_id = await _setup_client_with_project(db, categoria="BASICA")
    user = (await db.execute(
        text("SELECT * FROM client_users WHERE id = :i"),
        {"i": str(user_id)},
    )).mappings().first()
    fake = ClientUser(
        id=user_id, client_id=user["client_id"],
        email=user["email"], full_name=user["full_name"],
    )
    app.dependency_overrides[get_current_client_user] = lambda: fake

    # a04 has min_tier=BASICA · should work for BASICA project
    r = await async_client.post(
        "/api/v1/client-portal/inline-agents/a04_redactor_summary/invoke",
        json={"user_message": "Resume mi DPC."},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["agent_id"] == 4
    assert "response" in data
    app.dependency_overrides.pop(get_current_client_user, None)
