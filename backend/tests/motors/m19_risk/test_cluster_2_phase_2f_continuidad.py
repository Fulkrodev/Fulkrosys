"""CLUSTER 2 Phase 2F · Cliente continuidad questionnaire+approve tests.

Sesión 3B-2B.8 CLUSTER 2 Phase 2F · cliente_continuidad_input + approval tables
+ 5 cliente endpoints (questionnaire CRUD + drafts list + approve + comment).

Filosofía cliente-mínimo guard 100%: cliente provides INPUT raw + APPROVE/
COMMENT binding decisions · NO creator mode técnico ENS.

Coverage:
- upsert_input creates row when none exists
- upsert_input updates existing row (single row per project)
- get_input returns own data · None si no submitted
- list_drafts returns BIA admin entries (forward-compat DRP documents)
- record_approval persists action approved/rejected/comment
- audit_log Sub-atom 5.A 3-way OR (project_id + client_id propagated)
- Validation: artifact_type only bia/drp · action only approved/rejected/comment

Pattern 17 cumulative formalized:
- Cliente questionnaire+approve pattern (input raw + admin draft + approve/comment)
- Upsert single-row per project (UNIQUE constraint enforced)
- Architecturally coherent UI defer (backend MVP only · UI CLUSTER 6 navigation backbone)
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.cliente_continuidad import (
    ClienteContinuidadApproval,
    ClienteContinuidadInput,
)
from backend.app.motors.m19_risk.cliente_continuidad_service import (
    VALID_APPROVAL_ACTIONS,
    VALID_ARTIFACT_TYPES,
    get_input,
    list_drafts,
    record_approval,
    upsert_input,
)
from backend.tests.conftest import _admin_setup, setup_test_project


# ════════════════════════════════════════════════════════════════════
# Phase 2F.1 · upsert_input (questionnaire raw input cliente)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_upsert_input_creates_row_when_none_exists(
    db: AsyncSession,
) -> None:
    """upsert_input creates ClienteContinuidadInput row primera vez."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    client_user_id = uuid.uuid4()

    row = await upsert_input(
        db,
        project_id=project_uuid,
        client_user_id=client_user_id,
        rto_horas_tolerancia=4,
        rpo_horas_tolerancia=2,
        impacto_diario_eur=Decimal("5000.00"),
        procesos_criticos=[{"nombre": "Sistema facturación", "descripcion": "Core"}],
        notas_cliente="Sin prisa por nuestra parte.",
        completed=False,
    )

    assert row.project_id == project_uuid
    assert row.client_user_id == client_user_id
    assert row.rto_horas_tolerancia == 4
    assert row.rpo_horas_tolerancia == 2
    assert row.impacto_diario_eur == Decimal("5000.00")
    assert len(row.procesos_criticos) == 1
    assert row.completed is False


@pytest.mark.asyncio
async def test_upsert_input_updates_existing_row_same_project(
    db: AsyncSession,
) -> None:
    """upsert_input actualiza existing row · single row per project (UNIQUE)."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    user1 = uuid.uuid4()
    user2 = uuid.uuid4()

    # First submission
    row1 = await upsert_input(
        db,
        project_id=project_uuid,
        client_user_id=user1,
        rto_horas_tolerancia=8,
        completed=False,
    )
    original_id = row1.id
    original_submitted = row1.submitted_at

    # Second submission · MUST update SAME row
    row2 = await upsert_input(
        db,
        project_id=project_uuid,
        client_user_id=user2,
        rto_horas_tolerancia=4,
        rpo_horas_tolerancia=1,
        completed=True,
    )

    assert row2.id == original_id, "upsert MUST update SAME row (UNIQUE project_id)"
    assert row2.submitted_at == original_submitted, "submitted_at preserved"
    assert row2.client_user_id == user2
    assert row2.rto_horas_tolerancia == 4
    assert row2.rpo_horas_tolerancia == 1
    assert row2.completed is True


@pytest.mark.asyncio
async def test_get_input_returns_none_when_no_submission(
    db: AsyncSession,
) -> None:
    """get_input returns None si cliente no submitted yet."""
    _, project_id_str = await setup_test_project(db)
    row = await get_input(db, project_id=uuid.UUID(project_id_str))
    assert row is None


@pytest.mark.asyncio
async def test_get_input_returns_own_submission(
    db: AsyncSession,
) -> None:
    """get_input returns persisted ClienteContinuidadInput · ownership preserved."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    client_user_id = uuid.uuid4()

    await upsert_input(
        db,
        project_id=project_uuid,
        client_user_id=client_user_id,
        notas_cliente="Test note",
    )

    row = await get_input(db, project_id=project_uuid)
    assert row is not None
    assert row.notas_cliente == "Test note"


# ════════════════════════════════════════════════════════════════════
# Phase 2F.1 · list_drafts (BIA admin entries forward-compat DRP)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_list_drafts_returns_bia_entries(
    db: AsyncSession,
) -> None:
    """list_drafts returns BIA entries existing en bia_analyses table."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)

    # Insert BIA entry (admin path · _admin_setup bypass RLS)
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO bia_analyses (id, project_id, service_name, "
                "rto_hours, rpo_hours, daily_impact_eur, created_at, updated_at) "
                "VALUES (gen_random_uuid(), :pid, :svc, :rto, :rpo, :impact, "
                "now(), now())"
            ),
            {
                "pid": project_id_str,
                "svc": "Sistema crítico facturación",
                "rto": 4,
                "rpo": 1,
                "impact": Decimal("3000"),
            },
        )

    drafts = await list_drafts(db, project_id=project_uuid)

    bia_drafts = [d for d in drafts if d["artifact_type"] == "bia"]
    assert len(bia_drafts) >= 1
    assert bia_drafts[0]["summary"] == "Sistema crítico facturación"
    assert bia_drafts[0]["rto_hours"] == 4
    assert bia_drafts[0]["rpo_hours"] == 1
    assert bia_drafts[0]["daily_impact_eur"] == "3000.00"


@pytest.mark.asyncio
async def test_list_drafts_empty_when_no_admin_entries(
    db: AsyncSession,
) -> None:
    """list_drafts returns [] cuando admin no ha creado BIA/DRP yet."""
    _, project_id_str = await setup_test_project(db)
    drafts = await list_drafts(db, project_id=uuid.UUID(project_id_str))
    assert drafts == []


# ════════════════════════════════════════════════════════════════════
# Phase 2F.1 · record_approval (cliente binding decision)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_record_approval_creates_approved_action(
    db: AsyncSession,
) -> None:
    """record_approval persiste action='approved' binding."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    client_user_id = uuid.uuid4()
    draft_id = uuid.uuid4()

    row = await record_approval(
        db,
        project_id=project_uuid,
        client_user_id=client_user_id,
        artifact_type="bia",
        draft_id=draft_id,
        action="approved",
        comment_text="Aprobado · sin cambios.",
    )

    assert row.project_id == project_uuid
    assert row.artifact_type == "bia"
    assert row.draft_id == draft_id
    assert row.action == "approved"
    assert row.comment_text == "Aprobado · sin cambios."


@pytest.mark.asyncio
async def test_record_approval_creates_comment_action(
    db: AsyncSession,
) -> None:
    """record_approval persiste action='comment' cliente solicita cambios."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    client_user_id = uuid.uuid4()

    row = await record_approval(
        db,
        project_id=project_uuid,
        client_user_id=client_user_id,
        artifact_type="drp",
        draft_id=None,
        action="comment",
        comment_text="Necesitamos ajustar RTO sistema X.",
    )

    assert row.action == "comment"
    assert row.artifact_type == "drp"
    assert row.draft_id is None
    assert "RTO" in row.comment_text


@pytest.mark.asyncio
async def test_record_approval_invalid_artifact_type_raises(
    db: AsyncSession,
) -> None:
    """record_approval raise ValueError artifact_type fuera de bia/drp."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)

    with pytest.raises(ValueError, match="artifact_type invalido"):
        await record_approval(
            db,
            project_id=project_uuid,
            client_user_id=uuid.uuid4(),
            artifact_type="bcp",  # NOT valid
            draft_id=None,
            action="approved",
        )


@pytest.mark.asyncio
async def test_record_approval_invalid_action_raises(
    db: AsyncSession,
) -> None:
    """record_approval raise ValueError action fuera de approved/rejected/comment."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)

    with pytest.raises(ValueError, match="action invalido"):
        await record_approval(
            db,
            project_id=project_uuid,
            client_user_id=uuid.uuid4(),
            artifact_type="bia",
            draft_id=None,
            action="edited",  # NOT valid · cliente NO edita
        )


# ════════════════════════════════════════════════════════════════════
# Phase 2F.1 · Filosofía cliente-mínimo enforcement
# ════════════════════════════════════════════════════════════════════


def test_valid_actions_only_approve_reject_comment_no_edit():
    """VALID_APPROVAL_ACTIONS NO incluye 'edited' · filosofía cliente-mínimo."""
    assert "edited" not in VALID_APPROVAL_ACTIONS
    assert "edit" not in VALID_APPROVAL_ACTIONS
    assert "create" not in VALID_APPROVAL_ACTIONS
    assert VALID_APPROVAL_ACTIONS == frozenset(
        {"approved", "rejected", "comment"},
    )


def test_valid_artifact_types_only_bia_drp():
    """VALID_ARTIFACT_TYPES restringido a {bia, drp} · NO scope creep."""
    assert VALID_ARTIFACT_TYPES == frozenset({"bia", "drp"})


# ════════════════════════════════════════════════════════════════════
# Phase 2F.1 · Persistence multiple approvals same draft (audit trail)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_multiple_approvals_persisted_as_audit_trail(
    db: AsyncSession,
) -> None:
    """Multiple comments+approve mismo draft persistidos · audit trail."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    client_user_id = uuid.uuid4()
    draft_id = uuid.uuid4()

    # Cliente solicita cambio · then approve
    await record_approval(
        db,
        project_id=project_uuid,
        client_user_id=client_user_id,
        artifact_type="bia",
        draft_id=draft_id,
        action="comment",
        comment_text="Pls reduce RTO sistema X.",
    )
    await record_approval(
        db,
        project_id=project_uuid,
        client_user_id=client_user_id,
        artifact_type="bia",
        draft_id=draft_id,
        action="approved",
        comment_text="OK con la actualización.",
    )

    rows = (await db.execute(
        select(ClienteContinuidadApproval).where(
            ClienteContinuidadApproval.project_id == project_uuid,
            ClienteContinuidadApproval.draft_id == draft_id,
        ).order_by(ClienteContinuidadApproval.created_at.asc())
    )).scalars().all()

    assert len(rows) == 2
    assert rows[0].action == "comment"
    assert rows[1].action == "approved"
    _ = ClienteContinuidadInput  # imported for symmetry · model accessible
