"""Tests portal API cliente pentest authorization (SAN-E v3.MB-5.5.B).

Cubre los 3 endpoints del portal cliente m08_verification:
- GET  /portal/pentest/projects/{id}/authorization
- POST /portal/pentest/projects/{id}/authorization/mark-reviewed
- GET  /portal/pentest/projects/{id}/authorization/document-hash

Pattern: override get_current_client_user, pre-create
client + project + ClientUser + VerificationRun en DB (admin role).
"""
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text as sa_text

from backend.app.models.client_portal import ClientUser
from backend.app.motors.m21_portal_cliente.api import get_current_client_user
from backend.tests.conftest import _admin_setup, setup_test_project


pytestmark = pytest.mark.asyncio


# ====================================================================
# Helpers
# ====================================================================


async def _setup_client_user(db, client_id: str) -> ClientUser:
    user_id = uuid.uuid4()
    email = f"portal-pentest-{user_id.hex[:8]}@example.com"
    async with _admin_setup(db):
        await db.execute(sa_text("""
            INSERT INTO client_users
                (id, client_id, email, password_hash, must_change_password, created_at)
            VALUES (:id, :cid, :email, 'fake_hash', false, now())
        """), {"id": str(user_id), "cid": client_id, "email": email})
    return ClientUser(
        id=user_id,
        client_id=uuid.UUID(client_id),
        email=email,
        password_hash="fake_hash",
        must_change_password=False,
    )


async def _setup_verification_run(
    db,
    project_id: str,
    *,
    admin_signed: bool = True,
    with_rich_data: bool = True,
) -> str:
    """Pre-create VerificationRun · escenarios diversos."""
    run_id = uuid.uuid4()
    scope = {
        "summary": "Pentest aplicacion SaaS · scope completo + API",
        "targets": [
            {"target_url": "https://staging.cliente.com", "target_type": "web_app"},
            {"target_url": "https://api.staging.cliente.com", "target_type": "api"},
        ],
        "exclusions": ["DDoS attacks", "Social engineering", "Physical access"],
        "credentials_provided": True,
        "data_classification": "staging",
    }
    tools_cfg = {"tools": ["Nuclei", "Burp Suite", "Nmap", "sqlmap", "ZAP"]}

    inicio = datetime(2026, 6, 1, 9, 0, tzinfo=UTC)
    fin = datetime(2026, 6, 7, 18, 0, tzinfo=UTC)
    admin_signed_at = (
        datetime.now(UTC) - timedelta(hours=2) if admin_signed else None
    )

    rich_cols = ""
    rich_vals = ""
    params: dict = {
        "id": str(run_id),
        "pid": project_id,
        "scope": json.dumps(scope),
        "tools_cfg": json.dumps(tools_cfg),
        "scheduled_start": inicio,
        "admin_signed_at": admin_signed_at,
    }
    if with_rich_data:
        rich_cols = (
            ", ventana_fin, ventana_timezone, ventana_business_hours_only, "
            "plan_test_categorias, plan_test_intensity, plan_test_estimated_hours, "
            "contacto_ir_nombre, contacto_ir_email, contacto_ir_telefono, contacto_ir_horario, "
            "rules_of_engagement, responsibility_disclosure, data_handling_policy"
        )
        rich_vals = (
            ", :ventana_fin, 'Europe/Madrid', true, "
            ":plan_cats, 'medium', 40, "
            "'Marcos Mata', 'marcos@fulkro.com', '+34 6XX XXX XXX', "
            "'09:00-18:00 CEST · 24/7 emergencias', "
            "'Solo testing dentro ventana · pausar si encuentra PII real', "
            "'Vulnerabilidades CRITICAS reportadas inmediato', "
            "'Logs cifrados Hetzner EU · destruccion 30 dias post-cert'"
        )
        params["ventana_fin"] = fin
        params["plan_cats"] = json.dumps(["osint", "scan", "web_app", "api"])

    async with _admin_setup(db):
        await db.execute(sa_text(f"""
            INSERT INTO verification_runs
                (id, project_id, category, mode, status, scope_jsonb, tools_config,
                 scheduled_start, authorized_by, authorization_signed_at, created_at, updated_at
                 {rich_cols})
            VALUES
                (:id, :pid, 'MEDIO', 'internal', 'pending',
                 CAST(:scope AS JSONB), CAST(:tools_cfg AS JSONB),
                 :scheduled_start, 'marcos', :admin_signed_at, now(), now()
                 {rich_vals})
        """), params)

    return str(run_id)


async def _override_auth(async_client, user: ClientUser) -> None:
    from backend.app.main import app
    app.dependency_overrides[get_current_client_user] = lambda: user


def _clear_overrides() -> None:
    from backend.app.main import app
    if get_current_client_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_client_user]


async def _get_client_id(db, project_id: str) -> str:
    res = await db.execute(
        sa_text("SELECT get_project_owner(:pid)"), {"pid": project_id},
    )
    return str(res.scalar())


# ====================================================================
# Tests · GET /authorization
# ====================================================================


async def test_get_authorization_returns_full_detail(db, async_client):
    _, project_id = await setup_test_project(db)
    client_id = await _get_client_id(db, project_id)
    user = await _setup_client_user(db, client_id)
    await _setup_verification_run(db, project_id, admin_signed=True)

    await _override_auth(async_client, user)
    try:
        response = await async_client.get(
            f"/api/v1/portal/pentest/projects/{project_id}/authorization",
        )
        assert response.status_code == 200, response.text
        body = response.json()

        # Scope richer
        assert "SaaS" in body["scope_summary"]
        assert len(body["scope_targets"]) == 2
        assert body["scope_targets"][0]["target_type"] == "web_app"
        assert "DDoS attacks" in body["scope_exclusions"]
        assert body["scope_credentials_provided"] is True
        assert body["scope_data_classification"] == "staging"

        # Ventana
        assert body["ventana_inicio"] is not None
        assert body["ventana_fin"] is not None
        assert body["ventana_timezone"] == "Europe/Madrid"
        assert body["ventana_business_hours_only"] is True

        # Plan
        assert "osint" in body["plan_test_categorias"]
        assert body["plan_test_intensity"] == "medium"
        assert body["plan_test_estimated_hours"] == 40
        assert "Nuclei" in body["plan_tools"]

        # IR
        assert body["contacto_ir_email"] == "marcos@fulkro.com"

        # Compromiso
        assert "PII real" in body["rules_of_engagement"]

        # Admin firma (existing)
        assert body["admin_authorized_at"] is not None
        assert body["admin_authorized_by"] == "marcos"

        # Cliente review · vacio inicial
        assert body["client_reviewed_at"] is None
        assert body["client_signing_intent_id"] is None
    finally:
        _clear_overrides()


async def test_get_authorization_404_si_no_existe(db, async_client):
    _, project_id = await setup_test_project(db)
    client_id = await _get_client_id(db, project_id)
    user = await _setup_client_user(db, client_id)

    await _override_auth(async_client, user)
    try:
        response = await async_client.get(
            f"/api/v1/portal/pentest/projects/{project_id}/authorization",
        )
        assert response.status_code == 404
        assert "pendiente" in response.json()["detail"].lower()
    finally:
        _clear_overrides()


async def test_get_authorization_409_si_admin_no_firmo(db, async_client):
    _, project_id = await setup_test_project(db)
    client_id = await _get_client_id(db, project_id)
    user = await _setup_client_user(db, client_id)
    await _setup_verification_run(db, project_id, admin_signed=False)

    await _override_auth(async_client, user)
    try:
        response = await async_client.get(
            f"/api/v1/portal/pentest/projects/{project_id}/authorization",
        )
        assert response.status_code == 409
        assert "admin" in response.json()["detail"].lower()
    finally:
        _clear_overrides()


# ====================================================================
# Tests · POST /mark-reviewed
# ====================================================================


async def test_mark_reviewed_persists_state(db, async_client):
    _, project_id = await setup_test_project(db)
    client_id = await _get_client_id(db, project_id)
    user = await _setup_client_user(db, client_id)
    await _setup_verification_run(db, project_id, admin_signed=True)

    await _override_auth(async_client, user)
    try:
        response = await async_client.post(
            f"/api/v1/portal/pentest/projects/{project_id}/authorization/mark-reviewed",
            json={"concerns_note": "Necesito ventana extendida hasta 8 junio"},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["client_reviewed_at"] is not None
        assert body["client_reviewed_by_user_id"] == str(user.id)
        assert body["client_concerns_note"] == (
            "Necesito ventana extendida hasta 8 junio"
        )
    finally:
        _clear_overrides()


async def test_mark_reviewed_sin_concerns_ok(db, async_client):
    _, project_id = await setup_test_project(db)
    client_id = await _get_client_id(db, project_id)
    user = await _setup_client_user(db, client_id)
    await _setup_verification_run(db, project_id, admin_signed=True)

    await _override_auth(async_client, user)
    try:
        response = await async_client.post(
            f"/api/v1/portal/pentest/projects/{project_id}/authorization/mark-reviewed",
            json={},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["client_reviewed_at"] is not None
        assert body["client_concerns_note"] is None
    finally:
        _clear_overrides()


# ====================================================================
# Tests · GET /document-hash
# ====================================================================


async def test_document_hash_deterministic(db, async_client):
    _, project_id = await setup_test_project(db)
    client_id = await _get_client_id(db, project_id)
    user = await _setup_client_user(db, client_id)
    await _setup_verification_run(db, project_id, admin_signed=True)

    await _override_auth(async_client, user)
    try:
        r1 = await async_client.get(
            f"/api/v1/portal/pentest/projects/{project_id}/authorization/document-hash",
        )
        r2 = await async_client.get(
            f"/api/v1/portal/pentest/projects/{project_id}/authorization/document-hash",
        )
        assert r1.status_code == 200, r1.text
        assert r2.status_code == 200
        b1, b2 = r1.json(), r2.json()
        assert b1["document_hash_sha256"] == b2["document_hash_sha256"]
        assert len(b1["document_hash_sha256"]) == 64  # SHA256 hex
        assert b1["canonical_length"] > 0
    finally:
        _clear_overrides()


async def test_document_hash_ready_only_after_review(db, async_client):
    _, project_id = await setup_test_project(db)
    client_id = await _get_client_id(db, project_id)
    user = await _setup_client_user(db, client_id)
    await _setup_verification_run(db, project_id, admin_signed=True)

    await _override_auth(async_client, user)
    try:
        # Pre-review · ready_for_authorization=false
        r1 = await async_client.get(
            f"/api/v1/portal/pentest/projects/{project_id}/authorization/document-hash",
        )
        assert r1.status_code == 200
        assert r1.json()["ready_for_authorization"] is False

        # Mark reviewed
        await async_client.post(
            f"/api/v1/portal/pentest/projects/{project_id}/authorization/mark-reviewed",
            json={},
        )

        # Post-review · ready_for_authorization=true
        r2 = await async_client.get(
            f"/api/v1/portal/pentest/projects/{project_id}/authorization/document-hash",
        )
        assert r2.status_code == 200
        assert r2.json()["ready_for_authorization"] is True

        # Hash DEBE cambiar tras review (client_reviewed_at en canonical)
        assert (
            r1.json()["document_hash_sha256"]
            != r2.json()["document_hash_sha256"]
        )
    finally:
        _clear_overrides()
