"""Tests for M27 API endpoints — DB-backed post sub-fase 5.5.F.0.G refactor.

Pre-refactor: tests usaban random UUIDs y dicts in-memory.
Post-refactor (commit ``a1b2c3d4e5f6``): endpoints persisten en
``conformity_routes``, ``conformity_submissions``, ``basic_declarations``,
``renewal_campaigns`` y ``conformity_state_snapshots`` con FK strict
a ``projects.id``. Tests ahora crean un cliente+proyecto sintético
vía ``setup_test_project`` (bypass RLS via ``_admin_setup``).
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.tests.conftest import setup_test_project


@pytest.mark.asyncio
class TestM27Api:
    async def test_lock_route_then_status(
        self, async_client, db: AsyncSession,
    ):
        _, pid = await setup_test_project(db)
        r = await async_client.post(
            f"/api/v1/conformity/projects/{pid}/route/lock",
            json={
                "route_type": "DECLARATION",
                "category": "BASICA",
                "rationale": "Project is BASICA category, declaration applies",
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["state"] == "ROUTE_LOCKED"

        r2 = await async_client.get(
            f"/api/v1/conformity/projects/{pid}/status"
        )
        assert r2.status_code == 200
        assert r2.json()["invariants_ok"] is True

    async def test_lock_route_rejects_basica_with_certification(
        self, async_client, db: AsyncSession,
    ):
        _, pid = await setup_test_project(db)
        r = await async_client.post(
            f"/api/v1/conformity/projects/{pid}/route/lock",
            json={
                "route_type": "CERTIFICATION",
                "category": "BASICA",
                "rationale": "wrong combination must be rejected",
            },
        )
        assert r.status_code == 422

    async def test_create_submission_then_attach_proof(
        self, async_client, db: AsyncSession,
    ):
        _, pid = await setup_test_project(db)
        await async_client.post(
            f"/api/v1/conformity/projects/{pid}/route/lock",
            json={"route_type": "CERTIFICATION", "category": "MEDIA",
                  "rationale": "Cert route for MEDIA"},
        )
        r = await async_client.post(
            f"/api/v1/conformity/projects/{pid}/submissions",
            json={"target": "AUDITOR", "payload_template": "p001"},
        )
        assert r.status_code == 201, r.text
        sid = r.json()["submission_id"]
        r2 = await async_client.post(
            f"/api/v1/conformity/projects/{pid}/submissions/{sid}/submit-proof",
            json={"proof_type": "pdf", "proof_reference": "/path/file.pdf", "completed": True},
        )
        assert r2.status_code == 200, r2.text
        assert r2.json()["state"] == "COMPLETED"

    async def test_renewal_states_present(
        self, async_client, db: AsyncSession,
    ):
        _, pid = await setup_test_project(db)
        target = (date.today() + timedelta(days=200)).isoformat()
        r = await async_client.post(
            f"/api/v1/conformity/projects/{pid}/renewal/start?target_date={target}",
        )
        assert r.status_code == 200, r.text
        assert r.json()["state"] in (
            "T-180", "T-120", "T-90", "T-60", "T-30",
            "DUE", "IN_PROGRESS", "COMPLETED", "LAPSED",
        )

    async def test_external_export_pilar(
        self, async_client, db: AsyncSession,
    ):
        _, pid = await setup_test_project(db)
        r = await async_client.post(
            f"/api/v1/conformity/projects/{pid}/external-exports",
            json={"tool": "PILAR", "params": {"version": "v1"}},
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["tool"] == "PILAR"
        assert len(body["artifact_hash"]) == 64

    async def test_route_history_grows(
        self, async_client, db: AsyncSession,
    ):
        _, pid = await setup_test_project(db)
        await async_client.post(
            f"/api/v1/conformity/projects/{pid}/route/lock",
            json={"route_type": "DECLARATION", "category": "BASICA",
                  "rationale": "history check"},
        )
        h = await async_client.get(
            f"/api/v1/conformity/projects/{pid}/route/history"
        )
        assert h.status_code == 200
        assert len(h.json()["history"]) >= 1
