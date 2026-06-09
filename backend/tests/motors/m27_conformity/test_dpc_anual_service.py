"""Tests M27 DpcAnualService · SAN-E v3.MB-6 atom 2.

8 tests cubren:
  Anniversary calculation + draft creation:
    1. test_get_conformidad_initial_signed_at_returns_none_if_no_data
    2. test_create_dpc_draft_requires_conformidad_signed
    3. test_create_dpc_draft_idempotent_per_anniversary_year
    4. test_anniversary_year_unique_constraint_enforced
  Context aggregation:
    5. test_aggregate_dpc_context_4_sections
  Review action:
    6. test_mark_dpc_reviewed_persists
    7. test_review_invalid_action_raises
  Document hash + signoff:
    8. test_dpc_document_hash_deterministic
    9. test_process_dpc_signoff_links_intent
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m27_conformity.dpc_anual_service import (
    ConformidadNotSignedError,
    DpcAlreadySignedError,
    DpcAnualService,
    DpcDeclarationNotFoundError,
    InvalidReviewActionError,
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


async def _seed_conformidad_signed(
    db: AsyncSession,
    project_id: str,
    signed_at: datetime,
) -> uuid.UUID:
    """Insert conformidad inicial firmada (base date anniversary)."""
    decl_id = uuid.uuid4()
    await db.execute(
        sa_text(
            "INSERT INTO basic_declarations "
            "(id, project_id, declaration_type, status, signed_at, "
            "signed_hash, created_at) "
            "VALUES (:i, :p, 'initial', 'signed', :sa, :sh, now())"
        ),
        {
            "i": str(decl_id),
            "p": project_id,
            "sa": signed_at,
            "sh": "a" * 64,
        },
    )
    await db.flush()
    return decl_id


# ════════════════════════════════════════════════════════════════════
# Anniversary + draft creation
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_conformidad_initial_signed_at_returns_none_if_no_data(
    db: AsyncSession,
):
    _, project_id = await setup_test_project(db)
    svc = DpcAnualService(db)

    result = await svc.get_conformidad_initial_signed_at(uuid.UUID(project_id))

    assert result is None


@pytest.mark.asyncio
async def test_create_dpc_draft_requires_conformidad_signed(db: AsyncSession):
    _, project_id = await setup_test_project(db)
    svc = DpcAnualService(db)

    with pytest.raises(ConformidadNotSignedError):
        await svc.create_dpc_anual_draft(
            project_id=uuid.UUID(project_id),
            anniversary_year=2027,
        )


@pytest.mark.asyncio
async def test_create_dpc_draft_idempotent_per_anniversary_year(
    db: AsyncSession,
):
    _, project_id = await setup_test_project(db)
    base = datetime(2026, 5, 1, tzinfo=UTC)
    await _seed_conformidad_signed(db, project_id, base)
    svc = DpcAnualService(db)

    decl1 = await svc.create_dpc_anual_draft(
        project_id=uuid.UUID(project_id),
        anniversary_year=2027,
    )
    decl2 = await svc.create_dpc_anual_draft(
        project_id=uuid.UUID(project_id),
        anniversary_year=2027,
    )

    assert decl1.id == decl2.id
    assert decl1.anniversary_year == 2027
    assert decl1.declaration_type == "dpc_anual"


@pytest.mark.asyncio
async def test_anniversary_year_unique_constraint_enforced(db: AsyncSession):
    """UNIQUE partial (project_id, anniversary_year) WHERE declaration_type='dpc_anual'."""
    _, project_id = await setup_test_project(db)
    base = datetime(2026, 5, 1, tzinfo=UTC)
    await _seed_conformidad_signed(db, project_id, base)
    svc = DpcAnualService(db)

    decl1 = await svc.create_dpc_anual_draft(
        project_id=uuid.UUID(project_id),
        anniversary_year=2027,
    )
    decl2 = await svc.create_dpc_anual_draft(
        project_id=uuid.UUID(project_id),
        anniversary_year=2028,
    )

    assert decl1.anniversary_year == 2027
    assert decl2.anniversary_year == 2028
    assert decl1.id != decl2.id


# ════════════════════════════════════════════════════════════════════
# Context aggregation
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_aggregate_dpc_context_4_sections(db: AsyncSession):
    """Q3.A · context snapshot contiene SLA + Recovery + Incidents + Roadmap."""
    _, project_id = await setup_test_project(db)
    svc = DpcAnualService(db)

    context = await svc.aggregate_dpc_context_snapshot(uuid.UUID(project_id))

    assert "bia_analyses_count" in context.sla_section
    assert "uptime_committed_pct" in context.sla_section
    assert "rto_documented_hours" in context.recovery_section
    assert "rpo_documented_hours" in context.recovery_section
    assert "total_incidents_last_12m" in context.incidents_section
    assert "severity_histogram" in context.incidents_section
    assert "new_evidences_last_12m" in context.roadmap_section


# ════════════════════════════════════════════════════════════════════
# Review action
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_mark_dpc_reviewed_persists(db: AsyncSession):
    client_id, project_id = await setup_test_project(db)
    user_id = await _create_user_id(db, client_id)
    base = datetime(2026, 5, 1, tzinfo=UTC)
    await _seed_conformidad_signed(db, project_id, base)
    svc = DpcAnualService(db)

    decl = await svc.create_dpc_anual_draft(
        project_id=uuid.UUID(project_id),
        anniversary_year=2027,
    )
    updated = await svc.mark_dpc_reviewed(
        declaration_id=decl.id,
        action="revisada_ok",
        note=None,
        user_id=user_id,
    )

    assert updated.client_reviewed_at is not None
    assert updated.client_reviewed_by_user_id == user_id


@pytest.mark.asyncio
async def test_review_invalid_action_raises(db: AsyncSession):
    client_id, project_id = await setup_test_project(db)
    user_id = await _create_user_id(db, client_id)
    base = datetime(2026, 5, 1, tzinfo=UTC)
    await _seed_conformidad_signed(db, project_id, base)
    svc = DpcAnualService(db)
    decl = await svc.create_dpc_anual_draft(
        project_id=uuid.UUID(project_id),
        anniversary_year=2027,
    )

    with pytest.raises(InvalidReviewActionError):
        await svc.mark_dpc_reviewed(
            declaration_id=decl.id,
            action="approved",
            note=None,
            user_id=user_id,
        )

    with pytest.raises(InvalidReviewActionError):
        await svc.mark_dpc_reviewed(
            declaration_id=decl.id,
            action="con_pregunta",
            note=None,
            user_id=user_id,
        )


# ════════════════════════════════════════════════════════════════════
# Document hash + signoff
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_dpc_document_hash_deterministic(db: AsyncSession):
    _, project_id = await setup_test_project(db)
    base = datetime(2026, 5, 1, tzinfo=UTC)
    await _seed_conformidad_signed(db, project_id, base)
    svc = DpcAnualService(db)
    decl = await svc.create_dpc_anual_draft(
        project_id=uuid.UUID(project_id),
        anniversary_year=2027,
    )

    hash1, _ = await svc.compute_dpc_document_hash(decl.id)
    hash2, _ = await svc.compute_dpc_document_hash(decl.id)

    assert hash1 == hash2
    assert len(hash1) == 64


@pytest.mark.asyncio
async def test_process_dpc_signoff_links_intent(db: AsyncSession):
    _, project_id = await setup_test_project(db)
    base = datetime(2026, 5, 1, tzinfo=UTC)
    await _seed_conformidad_signed(db, project_id, base)
    svc = DpcAnualService(db)
    decl = await svc.create_dpc_anual_draft(
        project_id=uuid.UUID(project_id),
        anniversary_year=2027,
    )
    intent_id = uuid.uuid4()

    result = await svc.process_dpc_signoff(
        declaration_id=decl.id,
        signing_intent_id=intent_id,
    )

    assert result.client_signing_intent_id == intent_id
    assert result.signed_at is not None
    assert result.status == "signed"
    assert result.signed_hash is not None
    assert len(result.signed_hash) == 64


@pytest.mark.asyncio
async def test_double_signoff_raises_already_signed(db: AsyncSession):
    _, project_id = await setup_test_project(db)
    base = datetime(2026, 5, 1, tzinfo=UTC)
    await _seed_conformidad_signed(db, project_id, base)
    svc = DpcAnualService(db)
    decl = await svc.create_dpc_anual_draft(
        project_id=uuid.UUID(project_id),
        anniversary_year=2027,
    )
    await svc.process_dpc_signoff(decl.id, uuid.uuid4())

    with pytest.raises(DpcAlreadySignedError):
        await svc.process_dpc_signoff(decl.id, uuid.uuid4())
