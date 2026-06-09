"""Tests M27 Renewal Extensions · ADR-046 v3 SAN-E.MB-3.D.

Cubre:
- timeline lazy seeds 8 milestones default
- timeline retorna milestones sorted por due_date
- contact-auditor marca milestone auditor_contact completado
- auditor-info consolida estado outreach + audit window
- contact-auditor body validation (email + message length)
"""
from __future__ import annotations


import pytest

from backend.tests.conftest import setup_test_project


BASE = "/api/v1/projects"


@pytest.mark.asyncio
async def test_timeline_seeds_8_default_milestones(async_client, db):
    _, project_id = await setup_test_project(db)
    r = await async_client.get(f"{BASE}/{project_id}/renewal/timeline")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["project_id"] == project_id
    assert len(body["milestones"]) == 8
    codes = {m["milestone_code"] for m in body["milestones"]}
    assert codes == {
        "prep", "review_docs", "gap_close", "pentest_refresh",
        "evidencia_refresh", "dossier", "auditor_contact", "audit_window",
    }
    assert body["progress"]["completed"] == 0
    assert body["progress"]["total"] == 8


@pytest.mark.asyncio
async def test_timeline_idempotent_no_double_seed(async_client, db):
    _, project_id = await setup_test_project(db)
    r1 = await async_client.get(f"{BASE}/{project_id}/renewal/timeline")
    r2 = await async_client.get(f"{BASE}/{project_id}/renewal/timeline")
    assert len(r1.json()["milestones"]) == len(r2.json()["milestones"]) == 8


@pytest.mark.asyncio
async def test_contact_auditor_marks_milestone_completed(async_client, db):
    _, project_id = await setup_test_project(db)
    await async_client.get(f"{BASE}/{project_id}/renewal/timeline")
    r = await async_client.post(
        f"{BASE}/{project_id}/renewal/contact-auditor",
        json={
            "auditor_email": "auditor@enac.example",
            "auditor_name": "Juan Auditor",
            "audit_entity": "ENAC-AC-12345",
            "message": "Solicito briefing inicial recertificacion bianual.",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "completado"
    assert body["completed_at"] is not None
    assert body["auditor_email"] == "auditor@enac.example"


@pytest.mark.asyncio
async def test_contact_auditor_validation_short_message(async_client, db):
    _, project_id = await setup_test_project(db)
    r = await async_client.post(
        f"{BASE}/{project_id}/renewal/contact-auditor",
        json={
            "auditor_email": "x@y.com",
            "auditor_name": "Auditor",
            "message": "corto",  # < 10 chars
        },
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_auditor_info_initial_state(async_client, db):
    _, project_id = await setup_test_project(db)
    r = await async_client.get(f"{BASE}/{project_id}/renewal/auditor-info")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["auditor_contacted"] is False
    assert body["audit_window_due"] is not None


@pytest.mark.asyncio
async def test_auditor_info_after_contact(async_client, db):
    _, project_id = await setup_test_project(db)
    await async_client.post(
        f"{BASE}/{project_id}/renewal/contact-auditor",
        json={
            "auditor_email": "auditor@enac.example",
            "auditor_name": "Juan",
            "message": "Briefing inicial recertificacion bianual ENS.",
        },
    )
    r = await async_client.get(f"{BASE}/{project_id}/renewal/auditor-info")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["auditor_contacted"] is True
    assert body["auditor_contacted_at"] is not None
    assert "auditor@enac.example" in body["auditor_contact_notes"]


@pytest.mark.asyncio
async def test_timeline_milestones_sorted_by_due_date(async_client, db):
    _, project_id = await setup_test_project(db)
    r = await async_client.get(f"{BASE}/{project_id}/renewal/timeline")
    milestones = r.json()["milestones"]
    due_dates = [m["due_date"] for m in milestones]
    assert due_dates == sorted(due_dates)
