"""Tests M23 RetainerCheckinService · SAN-E v3.MB-6 atom 4.

10 tests cubren:
  Quarter math:
    1. test_compute_quarter_label
    2. test_quarter_bounds_q2
  Active retainer + draft generation:
    3. test_generate_draft_requires_active_retainer
    4. test_generate_draft_idempotent_per_quarter
    5. test_aggregate_quarter_data_returns_schema_v1
  Admin curation workflow:
    6. test_admin_curate_workflow_transition
    7. test_admin_send_to_client_requires_curated
  Cliente review (MixinA):
    8. test_client_review_blocked_until_sent_to_client
    9. test_client_review_invalid_action_raises
  Signoff:
   10. test_compute_signoff_hash_deterministic
   11. test_process_signoff_links_intent
"""
from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m23_retainer.retainer_checkin_service import (
    CheckinAlreadySignedError,
    CheckinReportNotFoundError,
    InvalidReviewActionError,
    InvalidWorkflowTransitionError,
    NoActiveRetainerError,
    RetainerCheckinError,
    RetainerCheckinService,
    compute_quarter_label,
    quarter_bounds,
)
from backend.tests.conftest import setup_test_project


async def _create_user_id(db: AsyncSession, client_id: str) -> uuid.UUID:
    user_id = uuid.uuid4()
    await db.execute(
        sa_text(
            "INSERT INTO client_users (id, client_id, email, password_hash, created_at) "
            "VALUES (:uid, :cid, :email, 'x', now())"
        ),
        {
            "uid": str(user_id),
            "cid": client_id,
            "email": f"u{user_id.hex[:6]}@test.es",
        },
    )
    await db.flush()
    return user_id


async def _seed_active_retainer(
    db: AsyncSession, client_id: str, project_id: str, perfil: str = "R_STD",
) -> uuid.UUID:
    """Seed retainer_contracts row active."""
    contract_id = uuid.uuid4()
    await db.execute(
        sa_text(
            "INSERT INTO retainer_contracts "
            "(id, client_id, project_id, perfil, estado, created_at) "
            "VALUES (:id, :cid, :pid, :perfil, 'active', now())"
        ),
        {
            "id": str(contract_id),
            "cid": client_id,
            "pid": project_id,
            "perfil": perfil,
        },
    )
    await db.flush()
    return contract_id


# ════════════════════════════════════════════════════════════════════
# Quarter math (pure functions)
# ════════════════════════════════════════════════════════════════════


def test_compute_quarter_label():
    assert compute_quarter_label(date(2026, 1, 1)) == "2026-Q1"
    assert compute_quarter_label(date(2026, 4, 15)) == "2026-Q2"
    assert compute_quarter_label(date(2026, 9, 30)) == "2026-Q3"
    assert compute_quarter_label(date(2026, 12, 31)) == "2026-Q4"


def test_quarter_bounds_q2():
    start, end = quarter_bounds("2026-Q2")
    assert start == date(2026, 4, 1)
    assert end == date(2026, 6, 30)


# ════════════════════════════════════════════════════════════════════
# Active retainer + draft generation
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_generate_draft_requires_active_retainer(db: AsyncSession):
    _, project_id = await setup_test_project(db)
    svc = RetainerCheckinService(db)

    with pytest.raises(NoActiveRetainerError):
        await svc.generate_quarterly_report_draft(
            project_id=uuid.UUID(project_id),
            period_quarter="2026-Q2",
        )


@pytest.mark.asyncio
async def test_generate_draft_idempotent_per_quarter(db: AsyncSession):
    client_id, project_id = await setup_test_project(db)
    await _seed_active_retainer(db, client_id, project_id)
    svc = RetainerCheckinService(db)

    report1 = await svc.generate_quarterly_report_draft(
        project_id=uuid.UUID(project_id),
        period_quarter="2026-Q2",
    )
    report2 = await svc.generate_quarterly_report_draft(
        project_id=uuid.UUID(project_id),
        period_quarter="2026-Q2",
    )

    assert report1.id == report2.id
    assert report1.period_quarter == "2026-Q2"
    assert report1.admin_curation_status == "draft"
    assert report1.schema_version == "1.0"


@pytest.mark.asyncio
async def test_generate_annual_report_requires_active_retainer(db: AsyncSession):
    """#37 (FRENTE C): sin retainer activo → NoActiveRetainerError."""
    _, project_id = await setup_test_project(db)
    svc = RetainerCheckinService(db)
    with pytest.raises(NoActiveRetainerError):
        await svc.generate_annual_report_draft(
            project_id=uuid.UUID(project_id), year=2025,
        )


@pytest.mark.asyncio
async def test_generate_annual_report_idempotent_per_year(db: AsyncSession):
    """#37 (FRENTE C): informe ANUAL E-802 idempotente per (project, año) ·
    period_type='anual' · etiqueta YYYY-ANNUAL."""
    client_id, project_id = await setup_test_project(db)
    await _seed_active_retainer(db, client_id, project_id)
    svc = RetainerCheckinService(db)

    r1 = await svc.generate_annual_report_draft(
        project_id=uuid.UUID(project_id), year=2025,
    )
    r2 = await svc.generate_annual_report_draft(
        project_id=uuid.UUID(project_id), year=2025,
    )
    assert r1.id == r2.id
    assert r1.period_type == "anual"
    assert r1.period_quarter == "2025-AN"
    assert r1.admin_curation_status == "draft"
    # bounds del año natural
    assert str(r1.period_start) == "2025-01-01"
    assert str(r1.period_end) == "2025-12-31"


@pytest.mark.asyncio
async def test_aggregate_quarter_data_returns_schema_v1(db: AsyncSession):
    _, project_id = await setup_test_project(db)
    svc = RetainerCheckinService(db)

    summary = await svc.aggregate_quarter_data(
        uuid.UUID(project_id),
        period_start=date(2026, 4, 1),
        period_end=date(2026, 6, 30),
    )

    assert summary["schema_version"] == "1.0"
    assert "actividades" in summary
    assert "incidents" in summary
    assert "vulnerabilidades" in summary
    assert "normativa_changes" in summary
    assert "rag_overall" in summary
    assert "stakeholder_changes" in summary
    assert "evidence_freshness" in summary
    assert summary["rag_overall"] in {"green", "amber", "red"}


# ════════════════════════════════════════════════════════════════════
# Admin curation workflow
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_admin_curate_workflow_transition(db: AsyncSession):
    client_id, project_id = await setup_test_project(db)
    admin_id = uuid.uuid4()
    await _seed_active_retainer(db, client_id, project_id)
    svc = RetainerCheckinService(db)

    report = await svc.generate_quarterly_report_draft(
        project_id=uuid.UUID(project_id),
        period_quarter="2026-Q2",
    )
    assert report.admin_curation_status == "draft"

    curated = await svc.admin_curate_report(report.id, admin_id)
    assert curated.admin_curation_status == "curated_by_admin"
    assert curated.admin_curated_by_user_id == admin_id

    sent = await svc.admin_send_to_client(report.id, admin_id)
    assert sent.admin_curation_status == "sent_to_client"
    assert sent.sent_at is not None


@pytest.mark.asyncio
async def test_admin_send_to_client_requires_curated(db: AsyncSession):
    client_id, project_id = await setup_test_project(db)
    admin_id = uuid.uuid4()
    await _seed_active_retainer(db, client_id, project_id)
    svc = RetainerCheckinService(db)

    report = await svc.generate_quarterly_report_draft(
        project_id=uuid.UUID(project_id),
        period_quarter="2026-Q2",
    )
    # Skip curate · directly send_to_client (must fail)
    with pytest.raises(InvalidWorkflowTransitionError):
        await svc.admin_send_to_client(report.id, admin_id)


# ════════════════════════════════════════════════════════════════════
# Cliente review (MixinA · 8ª aplicación)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_client_review_blocked_until_sent_to_client(db: AsyncSession):
    client_id, project_id = await setup_test_project(db)
    user_id = await _create_user_id(db, client_id)
    await _seed_active_retainer(db, client_id, project_id)
    svc = RetainerCheckinService(db)

    report = await svc.generate_quarterly_report_draft(
        project_id=uuid.UUID(project_id),
        period_quarter="2026-Q2",
    )

    # En draft · cliente NO puede revisar
    with pytest.raises(RetainerCheckinError):
        await svc.mark_client_review(
            report.id, "revisada_ok", None, user_id,
        )


@pytest.mark.asyncio
async def test_client_review_invalid_action_raises(db: AsyncSession):
    client_id, project_id = await setup_test_project(db)
    user_id = await _create_user_id(db, client_id)
    admin_id = uuid.uuid4()
    await _seed_active_retainer(db, client_id, project_id)
    svc = RetainerCheckinService(db)

    report = await svc.generate_quarterly_report_draft(
        project_id=uuid.UUID(project_id),
        period_quarter="2026-Q2",
    )
    await svc.admin_curate_report(report.id, admin_id)
    await svc.admin_send_to_client(report.id, admin_id)

    with pytest.raises(InvalidReviewActionError):
        await svc.mark_client_review(report.id, "approved", None, user_id)

    with pytest.raises(InvalidReviewActionError):
        await svc.mark_client_review(report.id, "con_pregunta", None, user_id)


# ════════════════════════════════════════════════════════════════════
# Signoff
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_compute_signoff_hash_deterministic(db: AsyncSession):
    client_id, project_id = await setup_test_project(db)
    await _seed_active_retainer(db, client_id, project_id)
    svc = RetainerCheckinService(db)
    report = await svc.generate_quarterly_report_draft(
        project_id=uuid.UUID(project_id),
        period_quarter="2026-Q2",
    )

    hash1, len1 = await svc.compute_signoff_hash(report.id)
    hash2, len2 = await svc.compute_signoff_hash(report.id)

    assert hash1 == hash2
    assert len(hash1) == 64
    assert len1 == len2


@pytest.mark.asyncio
async def test_process_signoff_links_intent(db: AsyncSession):
    client_id, project_id = await setup_test_project(db)
    user_id = await _create_user_id(db, client_id)
    admin_id = uuid.uuid4()
    await _seed_active_retainer(db, client_id, project_id)
    svc = RetainerCheckinService(db)

    report = await svc.generate_quarterly_report_draft(
        project_id=uuid.UUID(project_id),
        period_quarter="2026-Q2",
    )
    await svc.admin_curate_report(report.id, admin_id)
    await svc.admin_send_to_client(report.id, admin_id)
    await svc.mark_client_review(report.id, "revisada_ok", None, user_id)

    intent_id = uuid.uuid4()
    result = await svc.process_quarterly_signoff(report.id, intent_id)

    assert result.client_signing_intent_id == intent_id


@pytest.mark.asyncio
async def test_double_signoff_raises_already_signed(db: AsyncSession):
    client_id, project_id = await setup_test_project(db)
    user_id = await _create_user_id(db, client_id)
    admin_id = uuid.uuid4()
    await _seed_active_retainer(db, client_id, project_id)
    svc = RetainerCheckinService(db)

    report = await svc.generate_quarterly_report_draft(
        project_id=uuid.UUID(project_id),
        period_quarter="2026-Q2",
    )
    await svc.admin_curate_report(report.id, admin_id)
    await svc.admin_send_to_client(report.id, admin_id)
    await svc.mark_client_review(report.id, "revisada_ok", None, user_id)
    await svc.process_quarterly_signoff(report.id, uuid.uuid4())

    with pytest.raises(CheckinAlreadySignedError):
        await svc.process_quarterly_signoff(report.id, uuid.uuid4())
