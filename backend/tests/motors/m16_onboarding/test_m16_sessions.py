"""Tests de creacion y gestion de sessions M16 (lado admin).

Post-MB-4.bis3 (ADR-020 v3 IMPLEMENTED FULLY): create_session NO genera
magic_link · cliente accede /client-portal/onboarding directly (MB-4.3).
Tests legacy que dependían del flow magic_link están skipped a nivel módulo.
"""
import uuid

import pytest
from sqlalchemy import select, text

from backend.tests.conftest import setup_test_project, _admin_setup

# Module-level skip · M16 create_session drop magic_link emit post-bis3.
pytestmark = pytest.mark.skip(
    reason="MB-4.bis3 ADR-020 · M16 create_session drop magic_link · "
    "tests legacy obsoletos · alternativa MB-4.3 admin panel + portal"
)

BASE = "/api/v1/onboarding"


async def _seed_project(db):
    """Create client + project. Returns project_id string."""
    _, project_id = await setup_test_project(db)
    return project_id


class TestCreateSession:

    @pytest.mark.asyncio
    async def test_create_returns_200_with_magic_link(self, async_client, db):
        pid = await _seed_project(db)
        r = await async_client.post(
            f"{BASE}/projects/{pid}/sessions",
            json={
                "sector": "servicios_profesionales",
                "role": "sponsor",
                "interlocutor_email": "sponsor@example.com",
                "interlocutor_name": "Ana Lopez",
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["state"] == "created"
        assert body["magic_link_url"].startswith("http")
        assert body["total_questions"] >= 3
        assert body["tiempo_estimado_minutos"] > 0

    @pytest.mark.asyncio
    async def test_create_succeeds_for_full_matrix_combo(self, async_client, db):
        """Post-cierre, every (sector, role) combo has a template, so creation must succeed."""
        pid = await _seed_project(db)
        r = await async_client.post(
            f"{BASE}/projects/{pid}/sessions",
            json={
                "sector": "energia",
                "role": "rrhh",
                "interlocutor_email": "x@example.com",
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total_questions"] >= 3

    @pytest.mark.asyncio
    async def test_create_rejects_invalid_email(self, async_client, db):
        pid = await _seed_project(db)
        r = await async_client.post(
            f"{BASE}/projects/{pid}/sessions",
            json={
                "sector": "servicios_profesionales",
                "role": "sponsor",
                "interlocutor_email": "not-an-email",
            },
        )
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_create_persists_template_and_progress(self, async_client, db):
        pid = await _seed_project(db)
        r = await async_client.post(
            f"{BASE}/projects/{pid}/sessions",
            json={
                "sector": "servicios_profesionales",
                "role": "ti_cto",
                "interlocutor_email": "cto@example.com",
            },
        )
        sid = r.json()["session_id"]
        row = await db.execute(text(
            "SELECT template_id_str, total_questions, answered_questions, estado "
            "FROM onboarding_sessions WHERE id = :sid"
        ), {"sid": sid})
        data = row.mappings().first()
        assert data["template_id_str"] == "onb-servicios_profesionales-ti_cto-v1"
        assert data["total_questions"] > 0
        assert data["answered_questions"] == 0
        assert data["estado"] == "created"


class TestListSessions:

    @pytest.mark.asyncio
    async def test_list_empty_project(self, async_client, db):
        pid = await _seed_project(db)
        r = await async_client.get(f"{BASE}/projects/{pid}/sessions")
        assert r.status_code == 200
        assert r.json() == []

    @pytest.mark.asyncio
    async def test_list_after_create(self, async_client, db):
        pid = await _seed_project(db)
        await async_client.post(
            f"{BASE}/projects/{pid}/sessions",
            json={"sector": "servicios_profesionales", "role": "sponsor", "interlocutor_email": "a@x.com"},
        )
        await async_client.post(
            f"{BASE}/projects/{pid}/sessions",
            json={"sector": "servicios_profesionales", "role": "legal_dpo", "interlocutor_email": "b@x.com"},
        )
        r = await async_client.get(f"{BASE}/projects/{pid}/sessions")
        assert r.status_code == 200
        assert len(r.json()) == 2

    @pytest.mark.asyncio
    async def test_list_filters_by_role(self, async_client, db):
        pid = await _seed_project(db)
        await async_client.post(
            f"{BASE}/projects/{pid}/sessions",
            json={"sector": "servicios_profesionales", "role": "sponsor", "interlocutor_email": "a@x.com"},
        )
        await async_client.post(
            f"{BASE}/projects/{pid}/sessions",
            json={"sector": "servicios_profesionales", "role": "ti_cto", "interlocutor_email": "b@x.com"},
        )
        r = await async_client.get(f"{BASE}/projects/{pid}/sessions?role=sponsor")
        assert len(r.json()) == 1
        assert r.json()[0]["role"] == "sponsor"


class TestStateTransitions:

    @pytest.mark.asyncio
    async def test_mark_sent_transitions(self, async_client, db):
        pid = await _seed_project(db)
        r = await async_client.post(
            f"{BASE}/projects/{pid}/sessions",
            json={"sector": "servicios_profesionales", "role": "sponsor", "interlocutor_email": "a@x.com"},
        )
        sid = r.json()["session_id"]
        r2 = await async_client.post(f"{BASE}/sessions/{sid}/mark-sent")
        assert r2.status_code == 200
        assert r2.json()["state"] == "sent"

    @pytest.mark.asyncio
    async def test_mark_sent_fails_if_already_sent(self, async_client, db):
        pid = await _seed_project(db)
        r = await async_client.post(
            f"{BASE}/projects/{pid}/sessions",
            json={"sector": "servicios_profesionales", "role": "sponsor", "interlocutor_email": "a@x.com"},
        )
        sid = r.json()["session_id"]
        await async_client.post(f"{BASE}/sessions/{sid}/mark-sent")
        r2 = await async_client.post(f"{BASE}/sessions/{sid}/mark-sent")
        assert r2.status_code == 422

    @pytest.mark.asyncio
    async def test_cancel_revokes_magic_link(self, async_client, db):
        pid = await _seed_project(db)
        r = await async_client.post(
            f"{BASE}/projects/{pid}/sessions",
            json={"sector": "servicios_profesionales", "role": "sponsor", "interlocutor_email": "a@x.com"},
        )
        sid = r.json()["session_id"]
        r2 = await async_client.post(
            f"{BASE}/sessions/{sid}/cancel",
            json={"reason": "sponsor left"},
        )
        assert r2.status_code == 200
        body = r2.json()
        assert body["state"] == "cancelled"
        assert body["magic_link_revoked"] is True

    @pytest.mark.asyncio
    async def test_cancel_completed_fails(self, async_client, db):
        """Cannot cancel a completed session (tested via direct DB update)."""
        pid = await _seed_project(db)
        r = await async_client.post(
            f"{BASE}/projects/{pid}/sessions",
            json={"sector": "servicios_profesionales", "role": "sponsor", "interlocutor_email": "a@x.com"},
        )
        sid = r.json()["session_id"]
        # Force completed state in DB
        async with _admin_setup(db):
            await db.execute(text(
                "UPDATE onboarding_sessions SET estado = 'completed' WHERE id = :sid"
            ), {"sid": sid})
        await db.flush()
        r2 = await async_client.post(f"{BASE}/sessions/{sid}/cancel", json={})
        assert r2.status_code == 422


class TestCatalogEndpoint:

    @pytest.mark.asyncio
    async def test_catalog_returns_pilot(self, async_client):
        r = await async_client.get(f"{BASE}/catalog")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] >= 3
        assert any(t["sector"] == "servicios_profesionales" for t in body["templates"])

    @pytest.mark.asyncio
    async def test_template_detail(self, async_client):
        r = await async_client.get(f"{BASE}/catalog/onb-servicios_profesionales-sponsor-v1")
        assert r.status_code == 200
        body = r.json()
        assert "questions" in body
        assert len(body["questions"]) >= 3

    @pytest.mark.asyncio
    async def test_unknown_template_404(self, async_client):
        r = await async_client.get(f"{BASE}/catalog/onb-fake-999")
        assert r.status_code == 404
