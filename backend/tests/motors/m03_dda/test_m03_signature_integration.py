"""Tests for M3 + M12 re-integration: DdA E-040 RSEG signature via magic link.

Closes TODO-M3-G2 and completes Bloque A of the roadmap.
Tests exercise the full HTTP flow:
  POST /dda/projects/{id}/e040/request-signature
  GET  /dda/projects/{id}/e040/signature-status

Seeds data through the M3 DdA API (generate + implement + freeze) to
produce a real frozen DdA, then exercises the signature endpoints.
"""
import uuid

import pytest
from sqlalchemy import text, select

from backend.tests.conftest import setup_test_project, _admin_setup

BASE = "/api/v1/dda"


# ================================================================
# HELPERS
# ================================================================

async def _generate_and_freeze_dda(async_client, db):
    """Create project + generate DdA + implement all + freeze. Return project_id."""
    _, project_id = await setup_test_project(db)

    r = await async_client.post(
        f"{BASE}/generate",
        json={"project_id": project_id, "system_category": "BASICA", "responsable": "RSEG"},
    )
    assert r.status_code == 201, f"Generate failed: {r.text}"

    # Implement all applicable entries to pass the 80% threshold for freeze
    async with _admin_setup(db):
        await db.execute(
            text(
                "UPDATE dda_entries SET estado_implementacion = 'implantada' "
                "WHERE project_id = :pid AND aplicabilidad != 'no_aplica' AND deleted_at IS NULL"
            ),
            {"pid": project_id},
        )
    await db.flush()

    # Freeze (aprobado_por is a query param, not body)
    r = await async_client.post(
        f"{BASE}/projects/{project_id}/freeze?aprobado_por=RSEG+Test",
    )
    assert r.status_code == 200, f"Freeze failed: {r.text}"
    return project_id


async def _generate_draft_dda(async_client, db):
    """Create project + generate DdA (unfrozen). Return project_id."""
    _, project_id = await setup_test_project(db)
    r = await async_client.post(
        f"{BASE}/generate",
        json={"project_id": project_id, "system_category": "BASICA", "responsable": "RSEG"},
    )
    assert r.status_code == 201, f"Generate failed: {r.text}"
    return project_id


# ================================================================
# REQUEST SIGNATURE TESTS
# ================================================================

class TestRequestE040Signature:

    @pytest.mark.asyncio
    async def test_returns_200_for_frozen_dda(self, async_client, db):
        """POST request-signature on frozen DdA returns magic link."""
        project_id = await _generate_and_freeze_dda(async_client, db)

        r = await async_client.post(
            f"{BASE}/projects/{project_id}/e040/request-signature",
            json={"recipient_email": "rseg@example.com", "recipient_name": "Carmen Vidal"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["magic_link_url"].startswith("http")
        assert len(body["otp"]) == 6
        assert body["recipient_email"] == "rseg@example.com"
        assert body["previous_link_revoked"] is False
        assert len(body["dda_snapshot_hash"]) == 64
        assert body["total_entries"] == 73

    @pytest.mark.asyncio
    async def test_fails_for_draft_dda(self, async_client, db):
        """Unfrozen DdA rejects signature with clear message."""
        project_id = await _generate_draft_dda(async_client, db)

        r = await async_client.post(
            f"{BASE}/projects/{project_id}/e040/request-signature",
            json={"recipient_email": "x@example.com"},
        )
        assert r.status_code == 422
        detail = r.json()["detail"].lower()
        assert "congelad" in detail or "freeze" in detail

    @pytest.mark.asyncio
    async def test_fails_for_project_without_dda(self, async_client, db):
        """Project without generated DdA returns 422."""
        _, project_id = await setup_test_project(db)

        r = await async_client.post(
            f"{BASE}/projects/{project_id}/e040/request-signature",
            json={"recipient_email": "x@example.com"},
        )
        assert r.status_code == 422
        detail = r.json()["detail"].lower()
        assert "generad" in detail or "dda" in detail

    @pytest.mark.asyncio
    async def test_fails_nonexistent_project(self, async_client, db):
        """Non-existent project returns 404 (from RLS helper)."""
        r = await async_client.post(
            f"{BASE}/projects/{uuid.uuid4()}/e040/request-signature",
            json={"recipient_email": "x@example.com"},
        )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_persists_link_id(self, async_client, db):
        """Signature state row gets magic_link_id populated."""
        from backend.app.models.ens import DdaProjectSignature
        project_id = await _generate_and_freeze_dda(async_client, db)

        r = await async_client.post(
            f"{BASE}/projects/{project_id}/e040/request-signature",
            json={"recipient_email": "rseg@example.com"},
        )
        link_id = r.json()["link_id"]

        state = await db.get(DdaProjectSignature, uuid.UUID(project_id))
        assert str(state.signature_magic_link_id) == link_id

    @pytest.mark.asyncio
    async def test_idempotent_revokes_previous(self, async_client, db):
        """Second request revokes the first link."""
        project_id = await _generate_and_freeze_dda(async_client, db)

        r1 = await async_client.post(
            f"{BASE}/projects/{project_id}/e040/request-signature",
            json={"recipient_email": "a@example.com"},
        )
        r2 = await async_client.post(
            f"{BASE}/projects/{project_id}/e040/request-signature",
            json={"recipient_email": "b@example.com"},
        )
        assert r1.json()["link_id"] != r2.json()["link_id"]
        assert r2.json()["previous_link_revoked"] is True

    @pytest.mark.asyncio
    async def test_rejects_invalid_email(self, async_client, db):
        """Invalid email returns 422."""
        project_id = await _generate_and_freeze_dda(async_client, db)

        r = await async_client.post(
            f"{BASE}/projects/{project_id}/e040/request-signature",
            json={"recipient_email": "not-an-email"},
        )
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_uses_default_rseg_role(self, async_client, db):
        """Default role = Responsable de Seguridad, scope has dda_e040_rseg."""
        from backend.app.models.operations import MagicLink
        project_id = await _generate_and_freeze_dda(async_client, db)

        r = await async_client.post(
            f"{BASE}/projects/{project_id}/e040/request-signature",
            json={"recipient_email": "rseg@example.com"},
        )
        link_id = uuid.UUID(r.json()["link_id"])
        ml = (await db.execute(select(MagicLink).where(MagicLink.id == link_id))).scalar_one()
        assert ml.scope["recipient_role"] == "Responsable de Seguridad"
        assert ml.scope["document_type"] == "dda_e040_rseg"
        assert ml.scope["total_entries"] == 73


# ================================================================
# SIGNATURE STATUS TESTS
# ================================================================

class TestE040SignatureStatus:

    @pytest.mark.asyncio
    async def test_status_frozen_no_request(self, async_client, db):
        """Frozen DdA with no signature request."""
        project_id = await _generate_and_freeze_dda(async_client, db)

        r = await async_client.get(f"{BASE}/projects/{project_id}/e040/signature-status")
        assert r.status_code == 200
        body = r.json()
        assert body["has_signature_request"] is False
        assert body["is_frozen"] is True
        assert body["total_entries"] == 73

    @pytest.mark.asyncio
    async def test_status_draft_not_frozen(self, async_client, db):
        """Draft DdA returns is_frozen=False."""
        project_id = await _generate_draft_dda(async_client, db)

        r = await async_client.get(f"{BASE}/projects/{project_id}/e040/signature-status")
        assert r.status_code == 200
        body = r.json()
        assert body["is_frozen"] is False
        assert body["has_signature_request"] is False
        assert body["total_entries"] == 73

    @pytest.mark.asyncio
    async def test_status_after_request(self, async_client, db):
        """After signature request, status shows active link."""
        project_id = await _generate_and_freeze_dda(async_client, db)

        await async_client.post(
            f"{BASE}/projects/{project_id}/e040/request-signature",
            json={"recipient_email": "rseg@example.com"},
        )
        r = await async_client.get(f"{BASE}/projects/{project_id}/e040/signature-status")
        assert r.status_code == 200
        body = r.json()
        assert body["has_signature_request"] is True
        assert body["is_frozen"] is True
        assert body["link_id"] is not None
        assert body["state"] == "active"
        assert body["recipient_email"] == "rseg@example.com"

    @pytest.mark.asyncio
    async def test_status_empty_project(self, async_client, db):
        """Project without DdA returns empty status (not error)."""
        _, project_id = await setup_test_project(db)

        r = await async_client.get(f"{BASE}/projects/{project_id}/e040/signature-status")
        assert r.status_code == 200
        body = r.json()
        assert body["has_signature_request"] is False
        assert body["is_frozen"] is False
        assert body["total_entries"] == 0


# ================================================================
# HASH TESTS
# ================================================================

class TestDdaSnapshotHash:

    def test_hash_is_deterministic(self):
        """Same entries produce same hash."""
        from backend.app.motors.m03_dda.signature_integration import _compute_dda_snapshot_hash
        pid = uuid.uuid4()
        entries = [
            {"measure_code": "org.1", "aplicabilidad": "aplica", "estado_implementacion": "implantada"},
            {"measure_code": "org.2", "aplicabilidad": "aplica", "estado_implementacion": "parcial"},
        ]
        h1 = _compute_dda_snapshot_hash(pid, "2026-04-16", entries)
        h2 = _compute_dda_snapshot_hash(pid, "2026-04-16", entries)
        assert h1 == h2
        assert len(h1) == 64

    def test_hash_changes_with_different_entries(self):
        """Different entries produce different hash."""
        from backend.app.motors.m03_dda.signature_integration import _compute_dda_snapshot_hash
        pid = uuid.uuid4()
        e1 = [{"measure_code": "org.1", "aplicabilidad": "aplica", "estado_implementacion": "implantada"}]
        e2 = [{"measure_code": "org.1", "aplicabilidad": "no_aplica", "estado_implementacion": None}]
        h1 = _compute_dda_snapshot_hash(pid, "2026-04-16", e1)
        h2 = _compute_dda_snapshot_hash(pid, "2026-04-16", e2)
        assert h1 != h2
