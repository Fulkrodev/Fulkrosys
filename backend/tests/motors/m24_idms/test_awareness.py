"""Tests Awareness tracker + API · SAN-C MB-11.5."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from backend.app.motors.m24_idms.awareness_tracker import (
    calculate_coverage,
    list_sessions,
    record_attendance,
    schedule_session,
)


@pytest.mark.asyncio
async def test_schedule_and_list_sessions(db):
    from backend.tests.conftest import setup_test_project

    _, project_id_str = await setup_test_project(db)
    project_id = uuid.UUID(project_id_str)

    s1 = await schedule_session(
        db, project_id=project_id, title="Sesión phishing",
        scheduled_date=datetime.now(timezone.utc) + timedelta(days=7),
        topics=["phishing", "ransomware"],
    )
    s2 = await schedule_session(
        db, project_id=project_id, title="Sesión RGPD",
        scheduled_date=datetime.now(timezone.utc) + timedelta(days=14),
    )
    await db.commit()

    sessions = await list_sessions(db, project_id)
    assert len(sessions) == 2
    # Ordenadas por scheduled_date descendente
    assert sessions[0].id == s2.id


@pytest.mark.asyncio
async def test_record_attendance_invalid_method_raises(db):
    from backend.tests.conftest import setup_test_project

    _, project_id_str = await setup_test_project(db)
    project_id = uuid.UUID(project_id_str)

    s = await schedule_session(
        db, project_id=project_id, title="X",
        scheduled_date=datetime.now(timezone.utc),
    )
    await db.commit()

    with pytest.raises(ValueError):
        await record_attendance(
            db, session_id=s.id, attendee_email="x@y.com",
            method="invalid_method",
        )


@pytest.mark.asyncio
async def test_calculate_coverage_with_attendance(db):
    from backend.tests.conftest import setup_test_project

    _, project_id_str = await setup_test_project(db)
    project_id = uuid.UUID(project_id_str)

    s = await schedule_session(
        db, project_id=project_id, title="Sesión",
        scheduled_date=datetime.now(timezone.utc),
    )
    await db.commit()

    await record_attendance(db, session_id=s.id, attendee_email="a@x.com", method="virtual")
    await record_attendance(db, session_id=s.id, attendee_email="b@x.com", method="virtual")
    # Duplicate email should count once via DISTINCT
    await record_attendance(db, session_id=s.id, attendee_email="a@x.com", method="recorded")
    await db.commit()

    cov = await calculate_coverage(db, project_id=project_id, expected_attendees=4)
    assert cov["unique_attendees"] == 2
    assert cov["expected_attendees"] == 4
    assert cov["coverage_pct"] == 50.0


@pytest.mark.asyncio
async def test_calculate_coverage_invalid_expected_raises(db):
    from backend.tests.conftest import setup_test_project

    _, project_id_str = await setup_test_project(db)
    project_id = uuid.UUID(project_id_str)
    with pytest.raises(ValueError):
        await calculate_coverage(db, project_id=project_id, expected_attendees=0)


@pytest.mark.asyncio
async def test_endpoint_schedule_session(async_client, db):
    from backend.tests.conftest import setup_test_project

    _, project_id = await setup_test_project(db)
    response = await async_client.post(
        f"/api/v1/projects/{project_id}/awareness/sessions",
        json={
            "title": "Sesión phishing",
            "scheduled_date": "2026-06-01T10:00:00+00:00",
            "topics": ["phishing"],
            "mandatory": True,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Sesión phishing"


@pytest.mark.asyncio
async def test_endpoint_record_attendance(async_client, db):
    from backend.tests.conftest import setup_test_project

    _, project_id = await setup_test_project(db)
    sess_resp = await async_client.post(
        f"/api/v1/projects/{project_id}/awareness/sessions",
        json={
            "title": "Sesión X",
            "scheduled_date": "2026-06-01T10:00:00+00:00",
        },
    )
    session_id = sess_resp.json()["id"]
    response = await async_client.post(
        f"/api/v1/awareness/sessions/{session_id}/attendance",
        json={"attendee_email": "user@cliente.com", "method": "virtual"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["attendee_email"] == "user@cliente.com"


@pytest.mark.asyncio
async def test_endpoint_coverage(async_client, db):
    from backend.tests.conftest import setup_test_project

    _, project_id = await setup_test_project(db)
    response = await async_client.get(
        f"/api/v1/projects/{project_id}/awareness/coverage?expected=10",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["expected_attendees"] == 10
    assert data["unique_attendees"] == 0
    assert data["coverage_pct"] == 0.0
