"""Tests HTTP Motor 12 — Magic Link Engine REST API.

Tests exercise FastAPI endpoints via httpx AsyncClient, covering the
full HTTP request/response cycle including RLS, tenant context, and
the critical security pattern of uniform 403 on /consume.
"""
import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import text

from backend.tests.conftest import setup_test_project, _admin_setup

BASE = "/api/v1/magic-links"


# ================================================================
# HELPERS
# ================================================================

async def _generate_link_via_http(async_client, db, purpose="portal_remediacion"):
    """Helper: create project + generate magic link via HTTP endpoint.

    Returns (project_id, generate_response_json).

    Post-MB-4.bis2 default PORTAL_REMEDIACION (legitimate · NO requires OTP).
    Override max_uses=3 + ttl=168h cuando default (mantiene semantics legacy).
    """
    client_id, project_id = await setup_test_project(db)
    is_default = purpose == "portal_remediacion"
    body = {
        "project_id": project_id,
        "purpose": purpose,
        "recipient_email": "test@example.com",
    }
    if is_default:
        body["max_uses"] = 3
        body["ttl_hours"] = 168
    r = await async_client.post(f"{BASE}/generate", json=body)
    assert r.status_code == 201, f"Generate failed: {r.status_code} {r.text}"
    return project_id, r.json()


async def _generate_link_direct(db, purpose="portal_remediacion"):
    """Helper: generate magic link directly via service (faster, no HTTP).

    Returns (service, gen_response, project_id).
    """
    from backend.app.database import set_tenant_context
    from backend.app.motors.m12_magic_link.service import MagicLinkService
    from backend.app.motors.m12_magic_link.schemas import MagicLinkGenerateRequest
    from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose

    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(db, client_id=client_id, project_id=project_id)

    svc = MagicLinkService(db)
    is_default = purpose == "portal_remediacion"
    req = MagicLinkGenerateRequest(
        project_id=project_id,
        purpose=MagicLinkPurpose(purpose),
        recipient_email="test@example.com",
        max_uses=3 if is_default else None,
        ttl_hours=168 if is_default else None,
    )
    resp = await svc.generate_magic_link(req, base_url="https://test.fulkro.es")
    await db.flush()
    return svc, resp, project_id


# ================================================================
# POST /generate TESTS (H1-H3)
# ================================================================

class TestGenerateEndpoint:
    """Tests for POST /api/v1/magic-links/generate."""

    @pytest.mark.asyncio
    async def test_generate_success_no_otp(self, async_client, db):
        """H1: Generate link APORTE_EVIDENCIA returns 201 with token, no OTP."""
        _, data = await _generate_link_via_http(async_client, db, "portal_remediacion")

        assert "magic_link_id" in data
        assert "token" in data
        assert len(data["token"]) > 50  # JWT is long
        assert data["otp"] is None
        assert "url" in data
        assert data["token"] in data["url"]
        assert data["purpose"] == "portal_remediacion"
        assert data["action_label"] == "Acceder al portal de remediacion"

    @pytest.mark.asyncio
    async def test_generate_with_otp_purpose(self, async_client, db):
        """H2: Generate FIRMA_DOCUMENTO returns 201 with OTP of 6 digits."""
        _, data = await _generate_link_via_http(async_client, db, "firma_documento")

        assert data["otp"] is not None
        assert len(data["otp"]) == 6
        assert data["otp"].isdigit()
        assert data["token"] is not None

    @pytest.mark.asyncio
    async def test_generate_nonexistent_project_returns_404(self, async_client, db):
        """H3b: Generate with nonexistent project returns 404."""
        r = await async_client.post(
            f"{BASE}/generate",
            json={
                "project_id": str(uuid4()),
                "purpose": "portal_remediacion",
                "recipient_email": "test@example.com",
            },
        )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_generate_invalid_purpose_returns_422(self, async_client, db):
        """H3: Invalid purpose is rejected by Pydantic validation."""
        client_id, project_id = await setup_test_project(db)
        r = await async_client.post(
            f"{BASE}/generate",
            json={
                "project_id": project_id,
                "purpose": "purpose_inventado",
                "recipient_email": "test@example.com",
            },
        )
        assert r.status_code == 422


# ================================================================
# POST /consume TESTS (H4-H8) — SECURITY CRITICAL
# ================================================================

class TestConsumeEndpoint:
    """Tests for POST /api/v1/magic-links/consume.

    The consume endpoint is PUBLIC. All errors MUST return uniform 403
    with "Invalid magic link" detail. No information leakage.
    """

    @pytest.mark.asyncio
    async def test_consume_success(self, async_client, db):
        """H4: Consume valid link returns 200 with scope and remaining_uses."""
        _, gen_data = await _generate_link_via_http(async_client, db, "portal_remediacion")

        r = await async_client.post(
            f"{BASE}/consume",
            json={"token": gen_data["token"]},
        )
        assert r.status_code == 200, f"Consume failed: {r.status_code} {r.text}"
        data = r.json()
        assert data["magic_link_id"] == gen_data["magic_link_id"]
        assert data["purpose"] == "portal_remediacion"
        assert data["remaining_uses"] == 2  # max_uses=3, consumed 1

    @pytest.mark.asyncio
    async def test_consume_invalid_token_returns_403_uniform(self, async_client, db):
        """H5: Invalid token returns 403 with uniform message. No info leak."""
        r = await async_client.post(
            f"{BASE}/consume",
            json={"token": "completely.invalid.token"},
        )
        assert r.status_code == 403
        assert r.json()["detail"] == "Invalid magic link"

    @pytest.mark.asyncio
    async def test_consume_expired_returns_403_uniform(self, async_client, db):
        """H6: Expired link returns same 403 as invalid token. No distinction."""
        svc, gen_resp, _ = await _generate_link_direct(db, "portal_remediacion")

        # Force expiration in DB
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        await db.execute(
            text("UPDATE magic_links SET expira_at = :exp WHERE id = :id"),
            {"exp": past, "id": str(gen_resp.magic_link_id)},
        )
        await db.flush()

        r = await async_client.post(
            f"{BASE}/consume",
            json={"token": gen_resp.token},
        )
        assert r.status_code == 403
        assert r.json()["detail"] == "Invalid magic link"

    @pytest.mark.asyncio
    async def test_consume_revoked_returns_403_uniform(self, async_client, db):
        """H7: Revoked link returns same 403 as invalid. No distinction."""
        svc, gen_resp, _ = await _generate_link_direct(db, "portal_remediacion")

        await svc.revoke_magic_link(gen_resp.magic_link_id)
        await db.flush()

        r = await async_client.post(
            f"{BASE}/consume",
            json={"token": gen_resp.token},
        )
        assert r.status_code == 403
        assert r.json()["detail"] == "Invalid magic link"

    @pytest.mark.asyncio
    async def test_consume_captures_user_agent(self, async_client, db):
        """H8: Consume captures real HTTP User-Agent in audit trail."""
        _, gen_data = await _generate_link_via_http(async_client, db, "portal_remediacion")

        r = await async_client.post(
            f"{BASE}/consume",
            json={"token": gen_data["token"]},
            headers={"User-Agent": "TestClient/1.0"},
        )
        assert r.status_code == 200

        # Verify audit trail in client_interactions
        async with _admin_setup(db):
            result = await db.execute(
                text(
                    "SELECT user_agent, accion FROM client_interactions "
                    "WHERE magic_link_id = :mid AND accion = 'consumed'"
                ),
                {"mid": gen_data["magic_link_id"]},
            )
            row = result.mappings().first()
        assert row is not None, "Audit trail must exist"
        assert "TestClient/1.0" in (row["user_agent"] or "")


# ================================================================
# POST /{id}/revoke TESTS (H9-H10)
# ================================================================

class TestRevokeEndpoint:
    """Tests for POST /api/v1/magic-links/{id}/revoke."""

    @pytest.mark.asyncio
    async def test_revoke_success(self, async_client, db):
        """H9: Revoke active link returns 204."""
        _, gen_data = await _generate_link_via_http(async_client, db)

        r = await async_client.post(
            f"{BASE}/{gen_data['magic_link_id']}/revoke",
        )
        assert r.status_code == 204

    @pytest.mark.asyncio
    async def test_revoke_nonexistent_returns_404(self, async_client, db):
        """H10: Revoke nonexistent link returns 404."""
        fake_id = str(uuid4())
        r = await async_client.post(f"{BASE}/{fake_id}/revoke")
        assert r.status_code == 404


# ================================================================
# GET /{id}/status TESTS (H11-H13)
# ================================================================

class TestStatusEndpoint:
    """Tests for GET /api/v1/magic-links/{id}/status."""

    @pytest.mark.asyncio
    async def test_status_active_link(self, async_client, db):
        """H11: Active link returns status 'active'."""
        _, gen_data = await _generate_link_via_http(async_client, db)

        r = await async_client.get(
            f"{BASE}/{gen_data['magic_link_id']}/status",
        )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "active"
        assert data["uses"] == 0

    @pytest.mark.asyncio
    async def test_status_expired_link(self, async_client, db):
        """H12: Expired link returns status 'expired'."""
        svc, gen_resp, _ = await _generate_link_direct(db, "portal_remediacion")

        past = datetime.now(timezone.utc) - timedelta(hours=1)
        await db.execute(
            text("UPDATE magic_links SET expira_at = :exp WHERE id = :id"),
            {"exp": past, "id": str(gen_resp.magic_link_id)},
        )
        await db.flush()

        r = await async_client.get(
            f"{BASE}/{gen_resp.magic_link_id}/status",
        )
        assert r.status_code == 200
        assert r.json()["status"] == "expired"

    @pytest.mark.asyncio
    async def test_status_nonexistent_returns_404(self, async_client, db):
        """H14: Status of nonexistent link returns 404."""
        fake_id = str(uuid4())
        r = await async_client.get(f"{BASE}/{fake_id}/status")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_status_revoked_link(self, async_client, db):
        """H13: Revoked link returns status 'revoked'."""
        svc, gen_resp, _ = await _generate_link_direct(db, "portal_remediacion")

        await svc.revoke_magic_link(gen_resp.magic_link_id)
        await db.flush()

        r = await async_client.get(
            f"{BASE}/{gen_resp.magic_link_id}/status",
        )
        assert r.status_code == 200
        assert r.json()["status"] == "revoked"
