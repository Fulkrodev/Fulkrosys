"""Tests post_signoff_hooks · SAN-E v3.MB-6 atom 8.

8 tests cubren:
  Project metadata + contact resolution:
    1. test_resolve_project_metadata_returns_first_client_user
    2. test_resolve_project_metadata_returns_none_for_missing_project
  M30 log_interaction silent-fail:
    3. test_log_m30_silent_fail_when_no_contact
    4. test_log_m30_persists_when_contact_exists
  Cross-motor post-signoff hooks:
    5. test_post_signoff_acta_logs_m30_interaction
    6. test_post_signoff_retainer_quarterly_logs_m30_interaction
    7. test_post_signoff_incident_logs_m30_interaction
  Generic + quarantine:
    8. test_post_signoff_generic_logs_m30_interaction
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.notifications.post_signoff_hooks import (
    _log_m30_interaction,
    _resolve_primary_contact_id,
    _resolve_project_metadata,
    post_signoff_acta,
    post_signoff_generic,
    post_signoff_incident,
    post_signoff_retainer_quarterly,
)
from backend.tests.conftest import _admin_setup


async def _setup_client_project(
    db: AsyncSession,
    *,
    with_user: bool = True,
    with_contact: bool = True,
) -> tuple[uuid.UUID, uuid.UUID]:
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    unique_cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(sa_text(
            "INSERT INTO clients (id, nombre, cif, created_at) "
            "VALUES (:id, 'Test Client M21', :cif, now())"
        ), {"id": str(client_id), "cif": unique_cif})
        await db.execute(sa_text(
            "INSERT INTO projects (id, client_id, nombre, created_at) "
            "VALUES (:id, :cid, 'Test Project', now())"
        ), {"id": str(project_id), "cid": str(client_id)})
        if with_user:
            await db.execute(sa_text(
                "INSERT INTO client_users (id, client_id, email, password_hash, "
                "full_name, must_change_password, created_at) "
                "VALUES (:uid, :cid, :email, 'x', :name, false, now())"
            ), {
                "uid": str(uuid.uuid4()),
                "cid": str(client_id),
                "email": f"u{uuid.uuid4().hex[:6]}@test.es",
                "name": "Cliente Test",
            })
        if with_contact:
            await db.execute(sa_text(
                "INSERT INTO client_contacts (id, client_id, full_name, email, "
                "role_title, role_category, created_at) "
                "VALUES (:id, :cid, 'Primary Contact', :email, 'CISO', 'sponsor', now())"
            ), {
                "id": str(uuid.uuid4()),
                "cid": str(client_id),
                "email": f"contact-{uuid.uuid4().hex[:6]}@test.es",
            })
    await db.execute(
        sa_text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(project_id)},
    )
    await db.execute(
        sa_text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": str(client_id)},
    )
    await db.flush()
    return client_id, project_id


# ════════════════════════════════════════════════════════════════════
# Project metadata + contact resolution
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_resolve_project_metadata_returns_first_client_user(
    db: AsyncSession,
):
    _, project_id = await _setup_client_project(db)
    meta = await _resolve_project_metadata(db, project_id)
    assert meta is not None
    assert meta["project_name"] == "Test Project"
    assert meta["user_email"] is not None
    assert meta["user_name"] == "Cliente Test"


@pytest.mark.asyncio
async def test_resolve_project_metadata_returns_none_for_missing_project(
    db: AsyncSession,
):
    meta = await _resolve_project_metadata(db, uuid.uuid4())
    assert meta is None


@pytest.mark.asyncio
async def test_log_m30_silent_fail_when_no_contact(db: AsyncSession):
    client_id, _ = await _setup_client_project(db, with_contact=False)
    # No raise · silent fail
    await _log_m30_interaction(
        db,
        project_id=uuid.uuid4(),
        client_id=client_id,
        interaction_type="signoff_test",
        source_motor="test",
        source_id=uuid.uuid4(),
        summary="Test",
    )
    # No interaction inserted
    row = await db.execute(sa_text("SELECT count(*) FROM client_contact_interactions"))
    assert row.scalar_one() == 0


@pytest.mark.asyncio
async def test_log_m30_persists_when_contact_exists(db: AsyncSession):
    client_id, _ = await _setup_client_project(db)
    contact_id = await _resolve_primary_contact_id(db, client_id)
    assert contact_id is not None

    source_id = uuid.uuid4()
    await _log_m30_interaction(
        db,
        project_id=uuid.uuid4(),
        client_id=client_id,
        interaction_type="signoff_test",
        source_motor="test_motor",
        source_id=source_id,
        summary="Test signoff",
        details={"k": "v"},
    )
    row = await db.execute(sa_text(
        "SELECT interaction_type, source_motor, source_id, summary "
        "FROM client_contact_interactions WHERE contact_id = :cid"
    ), {"cid": str(contact_id)})
    hit = row.first()
    assert hit is not None
    assert hit[0] == "signoff_test"
    assert hit[1] == "test_motor"
    assert str(hit[2]) == str(source_id)
    assert hit[3] == "Test signoff"


# ════════════════════════════════════════════════════════════════════
# Cross-motor post-signoff hooks (per atom)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_post_signoff_acta_logs_m30_interaction(db: AsyncSession):
    _, project_id = await _setup_client_project(db)

    meeting = SimpleNamespace(
        id=uuid.uuid4(),
        project_id=project_id,
        codigo="E-005-001",
        titulo="Acta Kickoff",
        acta_subtype="kickoff",
        acta_subtype_label="Acta Inicio Proyecto",
        fully_signed_at=datetime.now(UTC),
    )
    await post_signoff_acta(db, meeting=meeting)

    row = await db.execute(sa_text(
        "SELECT interaction_type, source_motor FROM client_contact_interactions "
        "WHERE source_id = :sid"
    ), {"sid": str(meeting.id)})
    hit = row.first()
    assert hit is not None
    assert hit[0] == "signoff_acta_kickoff"
    assert hit[1] == "m_meetings"


@pytest.mark.asyncio
async def test_post_signoff_retainer_quarterly_logs_m30_interaction(
    db: AsyncSession,
):
    _, project_id = await _setup_client_project(db)

    report = SimpleNamespace(
        id=uuid.uuid4(),
        project_id=project_id,
        period_quarter="2026-Q2",
        rag_overall="green",
        activities_completed=10,
        incidents_detected=2,
        vulns_critical=0,
        created_at=datetime.now(UTC),
    )
    await post_signoff_retainer_quarterly(db, report=report)

    row = await db.execute(sa_text(
        "SELECT interaction_type, source_motor FROM client_contact_interactions "
        "WHERE source_id = :sid"
    ), {"sid": str(report.id)})
    hit = row.first()
    assert hit is not None
    assert hit[0] == "signoff_retainer_quarterly"
    assert hit[1] == "m23_retainer"


@pytest.mark.asyncio
async def test_post_signoff_incident_logs_m30_interaction(db: AsyncSession):
    _, project_id = await _setup_client_project(db)

    incident = SimpleNamespace(
        id=uuid.uuid4(),
        project_id=project_id,
        codigo="INC-001",
        titulo="Test Incident",
        workflow_state="closed",
        client_reviewed_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await post_signoff_incident(db, incident=incident)

    row = await db.execute(sa_text(
        "SELECT interaction_type, source_motor FROM client_contact_interactions "
        "WHERE source_id = :sid"
    ), {"sid": str(incident.id)})
    hit = row.first()
    assert hit is not None
    assert hit[0] == "signoff_incident_close"
    assert hit[1] == "m19_risk"


@pytest.mark.asyncio
async def test_post_signoff_generic_logs_m30_interaction(db: AsyncSession):
    _, project_id = await _setup_client_project(db)
    source_id = uuid.uuid4()

    await post_signoff_generic(
        db,
        project_id=project_id,
        signable_type="policy_approval",
        signable_label="Política Aprobada",
        signable_codigo="E-100",
        signable_source_id=source_id,
        source_motor="m06_document_factory",
    )

    row = await db.execute(sa_text(
        "SELECT interaction_type, source_motor, summary FROM client_contact_interactions "
        "WHERE source_id = :sid"
    ), {"sid": str(source_id)})
    hit = row.first()
    assert hit is not None
    assert hit[0] == "signoff_policy_approval"
    assert hit[1] == "m06_document_factory"
    assert "Política Aprobada" in hit[2]
