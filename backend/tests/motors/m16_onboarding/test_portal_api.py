"""Tests para portal API wrappers M16 (SAN-E v3.MB-4.2.bis · Q1-B).

Test pattern:
- Override get_current_client_user con fake ClientUser para evitar JWT roundtrip.
- Override get_db con fixture transaccional.
- Pre-create client + project + ClientUser + OnboardingSession en DB.
"""
from __future__ import annotations

import uuid
from typing import Any

import pytest
from sqlalchemy import text as sa_text

from backend.app.models.client_portal import ClientUser
from backend.app.motors.m21_portal_cliente.api import get_current_client_user
from backend.tests.conftest import _admin_setup, setup_test_project


pytestmark = pytest.mark.asyncio


async def _setup_client_user(db, client_id: str) -> ClientUser:
    """Crea ClientUser en DB y devuelve la instancia ORM construida en memoria."""
    user_id = uuid.uuid4()
    email = f"portal-{user_id.hex[:8]}@example.com"
    async with _admin_setup(db):
        await db.execute(sa_text("""
            INSERT INTO client_users (id, client_id, email, password_hash, must_change_password, created_at)
            VALUES (:id, :cid, :email, 'fake_hash', false, now())
        """), {
            "id": str(user_id),
            "cid": client_id,
            "email": email,
        })
    return ClientUser(
        id=user_id,
        client_id=uuid.UUID(client_id),
        email=email,
        password_hash="fake_hash",
        must_change_password=False,
    )


async def _setup_onboarding_session(db, project_id: str, template_id: str = "tpl-test") -> str:
    """Crea OnboardingSession básica para tests."""
    session_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(sa_text("""
            INSERT INTO onboarding_sessions
                (id, project_id, estado, template_id_str, total_questions, answered_questions, created_at)
            VALUES (:id, :pid, 'sent', :tpl, 5, 2, now())
        """), {
            "id": str(session_id),
            "pid": project_id,
            "tpl": template_id,
        })
    return str(session_id)


async def _override_auth(async_client, user: ClientUser) -> None:
    """Override get_current_client_user para devolver un ClientUser fake."""
    from backend.app.main import app
    app.dependency_overrides[get_current_client_user] = lambda: user


def _clear_overrides() -> None:
    from backend.app.main import app
    if get_current_client_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_client_user]


async def test_portal_status_unauthenticated_401(async_client):
    """Sin auth · debe retornar 401 (vía endpoint sin override)."""
    project_id = uuid.uuid4()
    response = await async_client.get(
        f"/api/v1/portal/onboarding/projects/{project_id}/status",
    )
    assert response.status_code == 401


async def test_portal_status_returns_progress(db, async_client):
    _, project_id = await setup_test_project(db)
    res = await db.execute(sa_text("SELECT get_project_owner(:pid)"), {"pid": project_id})
    client_id = str(res.scalar())
    user = await _setup_client_user(db, client_id)
    await _setup_onboarding_session(db, project_id)

    await _override_auth(async_client, user)
    try:
        response = await async_client.get(
            f"/api/v1/portal/onboarding/projects/{project_id}/status",
        )
        assert response.status_code == 200
        body = response.json()
        assert body["estado"] == "sent"
        assert body["answered_questions"] == 2
        assert body["total_questions"] == 5
        assert body["progress_pct"] == 40
    finally:
        _clear_overrides()


async def test_portal_status_404_no_session(db, async_client):
    _, project_id = await setup_test_project(db)
    res = await db.execute(sa_text("SELECT get_project_owner(:pid)"), {"pid": project_id})
    client_id = str(res.scalar())
    user = await _setup_client_user(db, client_id)

    await _override_auth(async_client, user)
    try:
        response = await async_client.get(
            f"/api/v1/portal/onboarding/projects/{project_id}/status",
        )
        assert response.status_code == 404
    finally:
        _clear_overrides()


async def test_portal_scope_other_client_403(db, async_client):
    """ClientUser de cliente A no puede ver project de cliente B."""
    _, project_id_a = await setup_test_project(db)
    res = await db.execute(sa_text("SELECT get_project_owner(:pid)"), {"pid": project_id_a})
    client_a = str(res.scalar())

    # Crea segundo cliente + project + user
    client_b = uuid.uuid4()
    project_b = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(sa_text(
            "INSERT INTO clients (id, nombre, cif, created_at) "
            "VALUES (:id, 'B', :cif, now())"
        ), {"id": str(client_b), "cif": f"X{uuid.uuid4().hex[:8].upper()}"})
        await db.execute(sa_text(
            "INSERT INTO projects (id, client_id, nombre, created_at) "
            "VALUES (:id, :cid, 'B Project', now())"
        ), {"id": str(project_b), "cid": str(client_b)})

    user_b = await _setup_client_user(db, str(client_b))

    # User de cliente B intenta acceder project de cliente A
    await _override_auth(async_client, user_b)
    try:
        response = await async_client.get(
            f"/api/v1/portal/onboarding/projects/{project_id_a}/status",
        )
        assert response.status_code == 403
    finally:
        _clear_overrides()


async def test_portal_list_connectors_6_providers(db, async_client):
    _, project_id = await setup_test_project(db)
    res = await db.execute(sa_text("SELECT get_project_owner(:pid)"), {"pid": project_id})
    client_id = str(res.scalar())
    user = await _setup_client_user(db, client_id)

    await _override_auth(async_client, user)
    try:
        response = await async_client.get(
            f"/api/v1/portal/onboarding/projects/{project_id}/connectors",
        )
        assert response.status_code == 200
        connectors = response.json()["connectors"]
        types = {c["connector_type"] for c in connectors}
        assert types == {"github", "microsoft", "azure", "google", "base", "aws"}
        # Todos not_connected inicialmente
        for c in connectors:
            assert c["connected"] is False
            if c["connector_type"] == "aws":
                assert c["auth_method"] == "iam_access_key"
            else:
                assert c["auth_method"] == "oauth"
    finally:
        _clear_overrides()


async def test_portal_aws_oauth_init_returns_405(db, async_client):
    """AWS no soporta OAuth init · debe retornar 405."""
    _, project_id = await setup_test_project(db)
    res = await db.execute(sa_text("SELECT get_project_owner(:pid)"), {"pid": project_id})
    client_id = str(res.scalar())
    user = await _setup_client_user(db, client_id)

    await _override_auth(async_client, user)
    try:
        response = await async_client.post(
            f"/api/v1/portal/onboarding/projects/{project_id}/connectors/aws/oauth-init",
            json={"redirect_uri": "http://localhost/cb"},
        )
        assert response.status_code == 405
        assert "AWS no usa OAuth" in response.json()["detail"]
    finally:
        _clear_overrides()


async def test_portal_oauth_init_creates_state(db, async_client):
    from pydantic import SecretStr
    from backend.app.config import get_settings
    settings = get_settings()
    settings.github_client_id = "test_client_id"
    settings.github_client_secret = SecretStr("test_client_secret")

    _, project_id = await setup_test_project(db)
    res = await db.execute(sa_text("SELECT get_project_owner(:pid)"), {"pid": project_id})
    client_id = str(res.scalar())
    user = await _setup_client_user(db, client_id)

    await _override_auth(async_client, user)
    try:
        response = await async_client.post(
            f"/api/v1/portal/onboarding/projects/{project_id}/connectors/github/oauth-init",
            json={"redirect_uri": "http://localhost/cb"},
        )
        assert response.status_code == 200
        body = response.json()
        assert "authorize_url" in body
        assert "github.com" in body["authorize_url"]
        assert "state" in body
        assert "state=" in body["authorize_url"]
    finally:
        _clear_overrides()


async def test_portal_oauth_init_unknown_provider_400(db, async_client):
    _, project_id = await setup_test_project(db)
    res = await db.execute(sa_text("SELECT get_project_owner(:pid)"), {"pid": project_id})
    client_id = str(res.scalar())
    user = await _setup_client_user(db, client_id)

    await _override_auth(async_client, user)
    try:
        response = await async_client.post(
            f"/api/v1/portal/onboarding/projects/{project_id}/connectors/bogus/oauth-init",
            json={"redirect_uri": "http://localhost/cb"},
        )
        assert response.status_code == 400
    finally:
        _clear_overrides()


async def test_portal_lms_lists_assignments(db, async_client):
    _, project_id = await setup_test_project(db)
    res = await db.execute(sa_text("SELECT get_project_owner(:pid)"), {"pid": project_id})
    client_id = str(res.scalar())
    user = await _setup_client_user(db, client_id)

    # Crear LMS assignment
    assignment_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(sa_text("""
            INSERT INTO lms_assignments
                (id, project_id, course_codigo, course_titulo, course_duracion_minutos,
                 asistente_nombre, asistente_email, estado, asignado_at, created_at)
            VALUES (:id, :pid, 'LMS-001', 'Concienciación ENS', 60,
                    'Test User', 'test@ex.es', 'assigned', now(), now())
        """), {"id": str(assignment_id), "pid": project_id})

    await _override_auth(async_client, user)
    try:
        response = await async_client.get(
            f"/api/v1/portal/onboarding/projects/{project_id}/lms",
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body["assignments"]) == 1
        assert body["assignments"][0]["course_codigo"] == "LMS-001"
        assert "courses_available" in body
    finally:
        _clear_overrides()
