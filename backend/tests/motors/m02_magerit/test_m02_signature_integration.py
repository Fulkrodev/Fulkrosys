"""Tests for M2 + M12 re-integration: Informe E-028 MAGERIT signature via magic link.

Closes TODO-M12-G2. Tests exercise the full HTTP flow:
  POST /analysis/{id}/report-e028/request-signature
  GET  /analysis/{id}/report-e028/signature-status

Pattern cloned from test_m01_signature_integration.py adapted to MAGERIT domain.
Key difference: prerequisite is frozen analysis (snapshot_frozen_at IS NOT NULL).
"""
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select, text

from backend.tests.conftest import _admin_setup


# ================================================================
# HELPERS: seed frozen and draft analyses
# ================================================================

async def _seed_frozen_analysis(db):
    """Create client + project + frozen MAGERIT analysis. Return analysis."""
    from backend.app.motors.m02_magerit.models import MageritAnalysis

    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"

    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO clients (id, nombre, cif, created_at) "
            "VALUES (:id, 'MAGERIT Test Client', :cif, now())"
        ), {"id": str(client_id), "cif": cif})
        await db.execute(text(
            "INSERT INTO projects (id, client_id, nombre, created_at) "
            "VALUES (:id, :cid, 'MAGERIT Test Project', now())"
        ), {"id": str(project_id), "cid": str(client_id)})
        analysis = MageritAnalysis(
            id=uuid.uuid4(),
            project_id=project_id,
            name="Frozen Analysis Test",
            calculation_mode="qualitative",
            result_snapshot={"risks": [{"id": "r1", "level": "high"}], "summary": "test"},
            snapshot_frozen_at=datetime.now(timezone.utc),
        )
        db.add(analysis)
        await db.flush()

    # Set tenant context para queries posteriores como fulkro_app (SAN-B.MB-2.1).
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(project_id)},
    )
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": str(client_id)},
    )
    return analysis


async def _seed_draft_analysis(db):
    """Create client + project + draft (unfrozen) MAGERIT analysis."""
    from backend.app.motors.m02_magerit.models import MageritAnalysis

    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"

    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO clients (id, nombre, cif, created_at) "
            "VALUES (:id, 'Draft MAGERIT Client', :cif, now())"
        ), {"id": str(client_id), "cif": cif})
        await db.execute(text(
            "INSERT INTO projects (id, client_id, nombre, created_at) "
            "VALUES (:id, :cid, 'Draft MAGERIT Project', now())"
        ), {"id": str(project_id), "cid": str(client_id)})
        analysis = MageritAnalysis(
            id=uuid.uuid4(),
            project_id=project_id,
            name="Draft Analysis Test",
            calculation_mode="qualitative",
        )
        db.add(analysis)
        await db.flush()

    # Set tenant context (SAN-B.MB-2.1).
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(project_id)},
    )
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": str(client_id)},
    )
    return analysis


# ================================================================
# REQUEST SIGNATURE TESTS
# ================================================================

class TestRequestE028Signature:

    @pytest.mark.asyncio
    async def test_returns_200_for_frozen_analysis(self, async_client, db):
        analysis = await _seed_frozen_analysis(db)
        r = await async_client.post(
            f"/api/v1/magerit/analysis/{analysis.id}/report-e028/request-signature",
            json={"recipient_email": "rsystem@example.com", "recipient_name": "Laura Gomez"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["magic_link_url"].startswith("http")
        assert len(body["otp"]) == 6
        assert body["recipient_email"] == "rsystem@example.com"
        assert body["previous_link_revoked"] is False
        assert len(body["report_snapshot_hash"]) == 64
        assert body["frozen_at"] is not None

    @pytest.mark.asyncio
    async def test_fails_for_draft_analysis(self, async_client, db):
        """Unfrozen analysis rejects signature with clear message."""
        analysis = await _seed_draft_analysis(db)
        r = await async_client.post(
            f"/api/v1/magerit/analysis/{analysis.id}/report-e028/request-signature",
            json={"recipient_email": "x@example.com"},
        )
        assert r.status_code == 422
        detail = r.json()["detail"].lower()
        assert "congelado" in detail or "frozen" in detail or "freeze" in detail

    @pytest.mark.asyncio
    async def test_fails_nonexistent_analysis(self, async_client):
        r = await async_client.post(
            f"/api/v1/magerit/analysis/{uuid.uuid4()}/report-e028/request-signature",
            json={"recipient_email": "x@example.com"},
        )
        assert r.status_code == 404
        assert "not found" in r.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_persists_link_id(self, async_client, db):
        from backend.app.motors.m02_magerit.models import MageritAnalysis
        analysis = await _seed_frozen_analysis(db)
        r = await async_client.post(
            f"/api/v1/magerit/analysis/{analysis.id}/report-e028/request-signature",
            json={"recipient_email": "rsystem@example.com"},
        )
        assert r.status_code == 200
        link_id = r.json()["link_id"]

        await db.refresh(analysis)
        assert str(analysis.signature_magic_link_id) == link_id

    @pytest.mark.asyncio
    async def test_idempotent_revokes_previous(self, async_client, db):
        analysis = await _seed_frozen_analysis(db)
        r1 = await async_client.post(
            f"/api/v1/magerit/analysis/{analysis.id}/report-e028/request-signature",
            json={"recipient_email": "a@example.com"},
        )
        r2 = await async_client.post(
            f"/api/v1/magerit/analysis/{analysis.id}/report-e028/request-signature",
            json={"recipient_email": "b@example.com"},
        )
        assert r1.json()["link_id"] != r2.json()["link_id"]
        assert r2.json()["previous_link_revoked"] is True

    @pytest.mark.asyncio
    async def test_rejects_invalid_email(self, async_client, db):
        analysis = await _seed_frozen_analysis(db)
        r = await async_client.post(
            f"/api/v1/magerit/analysis/{analysis.id}/report-e028/request-signature",
            json={"recipient_email": "not-an-email"},
        )
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_uses_default_role(self, async_client, db):
        """Default recipient_role = Responsable del Sistema."""
        from backend.app.models.operations import MagicLink
        analysis = await _seed_frozen_analysis(db)
        r = await async_client.post(
            f"/api/v1/magerit/analysis/{analysis.id}/report-e028/request-signature",
            json={"recipient_email": "rsystem@example.com"},
        )
        link_id = uuid.UUID(r.json()["link_id"])
        ml = (await db.execute(select(MagicLink).where(MagicLink.id == link_id))).scalar_one()
        assert ml.scope["recipient_role"] == "Responsable del Sistema"
        assert ml.scope["document_type"] == "informe_e028_magerit"


# ================================================================
# SIGNATURE STATUS TESTS
# ================================================================

class TestE028SignatureStatus:

    @pytest.mark.asyncio
    async def test_status_no_request_for_frozen(self, async_client, db):
        analysis = await _seed_frozen_analysis(db)
        r = await async_client.get(
            f"/api/v1/magerit/analysis/{analysis.id}/report-e028/signature-status"
        )
        assert r.status_code == 200
        body = r.json()
        assert body["has_signature_request"] is False
        assert body["is_frozen"] is True

    @pytest.mark.asyncio
    async def test_status_draft_not_frozen(self, async_client, db):
        analysis = await _seed_draft_analysis(db)
        r = await async_client.get(
            f"/api/v1/magerit/analysis/{analysis.id}/report-e028/signature-status"
        )
        assert r.status_code == 200
        body = r.json()
        assert body["is_frozen"] is False
        assert body["has_signature_request"] is False

    @pytest.mark.asyncio
    async def test_status_after_request(self, async_client, db):
        analysis = await _seed_frozen_analysis(db)
        await async_client.post(
            f"/api/v1/magerit/analysis/{analysis.id}/report-e028/request-signature",
            json={"recipient_email": "rsystem@example.com"},
        )
        r = await async_client.get(
            f"/api/v1/magerit/analysis/{analysis.id}/report-e028/signature-status"
        )
        assert r.status_code == 200
        body = r.json()
        assert body["has_signature_request"] is True
        assert body["is_frozen"] is True
        assert body["link_id"] is not None
        assert body["state"] == "active"
        assert body["recipient_email"] == "rsystem@example.com"

    @pytest.mark.asyncio
    async def test_status_404_nonexistent(self, async_client):
        r = await async_client.get(
            f"/api/v1/magerit/analysis/{uuid.uuid4()}/report-e028/signature-status"
        )
        assert r.status_code == 404


# ================================================================
# HASH DETERMINISM TESTS
# ================================================================

class TestReportSnapshotHash:

    def test_hash_is_deterministic(self):
        from backend.app.motors.m02_magerit.signature_integration import _compute_report_snapshot_hash
        snapshot = {"risks": [{"id": "r1", "level": "high"}], "count": 42}
        h1 = _compute_report_snapshot_hash(snapshot)
        h2 = _compute_report_snapshot_hash(snapshot)
        assert h1 == h2
        assert len(h1) == 64

    def test_hash_changes_with_different_snapshot(self):
        from backend.app.motors.m02_magerit.signature_integration import _compute_report_snapshot_hash
        h1 = _compute_report_snapshot_hash({"a": 1})
        h2 = _compute_report_snapshot_hash({"a": 2})
        assert h1 != h2
