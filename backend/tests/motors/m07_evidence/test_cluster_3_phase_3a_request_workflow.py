"""CLUSTER 3 Phase 3A · Evidence Request workflow state machine tests.

Sesión 3B-2B.8 CLUSTER 3 Phase 3A · workflow state machine canonical:
- pending_cliente → pending_review → approved | rejected | cancelled
- rejected → pending_review (re-upload cycle)
- pending_cliente → marked_na | cancelled
- Terminal states: approved · marked_na · cancelled

Coverage:
- create_request happy-path admin · status=pending_cliente default
- create_request validates titulo (raises sin titulo)
- list_requests filters por status correctly
- cliente_upload state transition pending_cliente → pending_review
- cliente_upload from rejected → pending_review (re-cycle reset metadata)
- cliente_upload rejected if current state NOT allowed (terminal · approved)
- cliente_mark_na state transition + motivo required
- admin_approve state transition pending_review → approved + terminal lock
- admin_reject requires motivo (ValueError sin motivo)
- admin_reject rejects from rejected (NOT allowed · terminal-like state)
- admin_cancel pending_cliente → cancelled · terminal
- ALLOWED_TRANSITIONS enforces canonical workflow

Pattern 18 cumulative formalized: Workflow state machine + canonical transition
validation (state transitions guards · admin/cliente actions per state · prevents
inconsistencies + re-upload cycle pattern).
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.evidence_request import (
    EVIDENCE_REQUEST_STATES,
    EvidenceRequest,
)
from backend.app.motors.m07_evidence.request_service import (
    ALLOWED_TRANSITIONS,
    WorkflowStateError,
    admin_approve,
    admin_cancel,
    admin_reject,
    cliente_mark_na,
    cliente_upload,
    create_request,
    list_requests,
)
from sqlalchemy import text

from backend.tests.conftest import _admin_setup, setup_test_project


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════


async def _create_request_pending_cliente(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    admin_user_id: uuid.UUID,
) -> EvidenceRequest:
    """Quick fixture: create pending_cliente request."""
    return await create_request(
        db,
        project_id=project_id,
        created_by_user_id=admin_user_id,
        titulo="Aportar log accesos administrador",
        descripcion="Necesitamos el log JSON de accesos último mes.",
        measure_code="op.acc.6",
        tipo_documento="log",
        deadline_date=date.today() + timedelta(days=14),
    )


async def _create_evidence_row(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
) -> uuid.UUID:
    """Create a real Evidence row · returns evidence_id (FK target)."""
    evidence_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO evidence "
                "(id, project_id, vigente, scan_status, created_at) "
                "VALUES (:eid, :pid, true, 'clean', now())"
            ),
            {"eid": str(evidence_id), "pid": str(project_id)},
        )
    return evidence_id


# ════════════════════════════════════════════════════════════════════
# Phase 3A · Workflow state machine validation
# ════════════════════════════════════════════════════════════════════


def test_evidence_request_states_canonical_set():
    """EVIDENCE_REQUEST_STATES contiene 6 estados canonical."""
    assert EVIDENCE_REQUEST_STATES == frozenset({
        "pending_cliente", "pending_review", "approved",
        "rejected", "cancelled", "marked_na",
    })


def test_allowed_transitions_pending_cliente():
    """pending_cliente puede → pending_review · marked_na · cancelled."""
    assert ALLOWED_TRANSITIONS["pending_cliente"] == frozenset({
        "pending_review", "marked_na", "cancelled",
    })


def test_allowed_transitions_pending_review():
    """pending_review puede → approved · rejected."""
    assert ALLOWED_TRANSITIONS["pending_review"] == frozenset({
        "approved", "rejected",
    })


def test_allowed_transitions_rejected_re_upload_cycle():
    """rejected puede → pending_review (cliente re-upload cycle)."""
    assert ALLOWED_TRANSITIONS["rejected"] == frozenset({"pending_review"})


def test_allowed_transitions_terminal_states_no_outgoing():
    """approved · cancelled · marked_na · terminal · NO outgoing transitions."""
    assert ALLOWED_TRANSITIONS["approved"] == frozenset()
    assert ALLOWED_TRANSITIONS["cancelled"] == frozenset()
    assert ALLOWED_TRANSITIONS["marked_na"] == frozenset()


# ════════════════════════════════════════════════════════════════════
# Phase 3A · create_request
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_request_happy_path(db: AsyncSession) -> None:
    """create_request defaults status=pending_cliente + populates all fields."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    admin_id = uuid.uuid4()

    row = await create_request(
        db,
        project_id=project_uuid,
        created_by_user_id=admin_id,
        titulo="Aportar política contraseñas",
        descripcion="PDF firmado vigente.",
        measure_code="org.4",
        tipo_documento="política",
        deadline_date=date.today() + timedelta(days=7),
    )

    assert row.id is not None
    assert row.status == "pending_cliente"
    assert row.titulo == "Aportar política contraseñas"
    assert row.measure_code == "org.4"
    assert row.created_by_user_id == admin_id
    assert row.evidence_id is None
    assert row.admin_validated_at is None


@pytest.mark.asyncio
async def test_create_request_validates_titulo(db: AsyncSession) -> None:
    """create_request raise sin titulo (strip empty)."""
    _, project_id_str = await setup_test_project(db)

    with pytest.raises(ValueError, match="titulo requerido"):
        await create_request(
            db,
            project_id=uuid.UUID(project_id_str),
            created_by_user_id=uuid.uuid4(),
            titulo="   ",  # whitespace only
        )


# ════════════════════════════════════════════════════════════════════
# Phase 3A · list_requests
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_list_requests_filter_by_status(db: AsyncSession) -> None:
    """list_requests filters per status."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    admin_id = uuid.uuid4()

    r1 = await _create_request_pending_cliente(
        db, project_id=project_uuid, admin_user_id=admin_id,
    )
    r2 = await _create_request_pending_cliente(
        db, project_id=project_uuid, admin_user_id=admin_id,
    )
    await admin_cancel(db, request_id=r2.id, admin_user_id=admin_id)

    pending = await list_requests(
        db, project_id=project_uuid, status_filter="pending_cliente",
    )
    cancelled = await list_requests(
        db, project_id=project_uuid, status_filter="cancelled",
    )

    assert len(pending) == 1
    assert pending[0].id == r1.id
    assert len(cancelled) == 1
    assert cancelled[0].id == r2.id


# ════════════════════════════════════════════════════════════════════
# Phase 3A · cliente_upload state transition
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_cliente_upload_pending_to_review(db: AsyncSession) -> None:
    """cliente_upload state transition pending_cliente → pending_review."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    admin_id = uuid.uuid4()
    client_user_id = uuid.uuid4()
    evidence_id = await _create_evidence_row(db, project_id=project_uuid)

    req = await _create_request_pending_cliente(
        db, project_id=project_uuid, admin_user_id=admin_id,
    )

    updated = await cliente_upload(
        db,
        request_id=req.id,
        evidence_id=evidence_id,
        client_user_id=client_user_id,
    )

    assert updated.status == "pending_review"
    assert updated.evidence_id == evidence_id
    assert updated.cliente_uploaded_at is not None
    assert updated.client_user_id == client_user_id


@pytest.mark.asyncio
async def test_cliente_upload_re_cycle_from_rejected(db: AsyncSession) -> None:
    """cliente re-upload after admin rejected · resets metadata + cycle pending_review."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    admin_id = uuid.uuid4()
    client_user_id = uuid.uuid4()
    evidence_id_v1 = await _create_evidence_row(db, project_id=project_uuid)
    evidence_id_v2 = await _create_evidence_row(db, project_id=project_uuid)

    req = await _create_request_pending_cliente(
        db, project_id=project_uuid, admin_user_id=admin_id,
    )

    # Cycle 1: cliente upload + admin reject
    await cliente_upload(
        db, request_id=req.id, evidence_id=evidence_id_v1,
        client_user_id=client_user_id,
    )
    rejected = await admin_reject(
        db, request_id=req.id, admin_user_id=admin_id,
        motivo="Falta la firma digital del documento.",
    )
    assert rejected.status == "rejected"
    assert rejected.admin_rejection_motivo == "Falta la firma digital del documento."

    # Cycle 2: cliente re-upload → pending_review · metadata reset
    re_upload = await cliente_upload(
        db, request_id=req.id, evidence_id=evidence_id_v2,
        client_user_id=client_user_id,
    )
    assert re_upload.status == "pending_review"
    assert re_upload.evidence_id == evidence_id_v2
    assert re_upload.admin_rejection_motivo is None
    assert re_upload.admin_validated_at is None


@pytest.mark.asyncio
async def test_cliente_upload_blocked_terminal_state(db: AsyncSession) -> None:
    """cliente_upload raise WorkflowStateError si state terminal (approved)."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    admin_id = uuid.uuid4()
    client_user_id = uuid.uuid4()

    req = await _create_request_pending_cliente(
        db, project_id=project_uuid, admin_user_id=admin_id,
    )
    evidence_id = await _create_evidence_row(db, project_id=project_uuid)
    await cliente_upload(
        db, request_id=req.id, evidence_id=evidence_id,
        client_user_id=client_user_id,
    )
    await admin_approve(db, request_id=req.id, admin_user_id=admin_id)

    with pytest.raises(WorkflowStateError, match="Transition not allowed"):
        evidence_id_2 = await _create_evidence_row(db, project_id=project_uuid)
        await cliente_upload(
            db, request_id=req.id, evidence_id=evidence_id_2,
            client_user_id=client_user_id,
        )


# ════════════════════════════════════════════════════════════════════
# Phase 3A · cliente_mark_na
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_cliente_mark_na_with_motivo(db: AsyncSession) -> None:
    """cliente_mark_na state transition pending_cliente → marked_na · motivo persistido."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    admin_id = uuid.uuid4()
    client_user_id = uuid.uuid4()

    req = await _create_request_pending_cliente(
        db, project_id=project_uuid, admin_user_id=admin_id,
    )

    updated = await cliente_mark_na(
        db, request_id=req.id, client_user_id=client_user_id,
        motivo="No usamos accesos administradores externos.",
    )

    assert updated.status == "marked_na"
    assert "accesos administradores externos" in updated.cliente_na_motivo
    assert updated.client_user_id == client_user_id


@pytest.mark.asyncio
async def test_cliente_mark_na_motivo_required(db: AsyncSession) -> None:
    """cliente_mark_na raise sin motivo (UX cliente · always with reason)."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    admin_id = uuid.uuid4()

    req = await _create_request_pending_cliente(
        db, project_id=project_uuid, admin_user_id=admin_id,
    )

    with pytest.raises(ValueError, match="motivo requerido"):
        await cliente_mark_na(
            db, request_id=req.id, client_user_id=uuid.uuid4(),
            motivo="   ",
        )


# ════════════════════════════════════════════════════════════════════
# Phase 3A · admin_approve / admin_reject / admin_cancel
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_admin_approve_terminal_state(db: AsyncSession) -> None:
    """admin_approve state pending_review → approved · terminal."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    admin_id = uuid.uuid4()
    client_user_id = uuid.uuid4()

    req = await _create_request_pending_cliente(
        db, project_id=project_uuid, admin_user_id=admin_id,
    )
    evidence_id = await _create_evidence_row(db, project_id=project_uuid)
    await cliente_upload(
        db, request_id=req.id, evidence_id=evidence_id,
        client_user_id=client_user_id,
    )

    approved = await admin_approve(
        db, request_id=req.id, admin_user_id=admin_id,
    )

    assert approved.status == "approved"
    assert approved.admin_validated_at is not None
    assert approved.admin_validated_by_user_id == admin_id

    # NO further transitions allowed
    with pytest.raises(WorkflowStateError, match="Transition not allowed"):
        await admin_reject(
            db, request_id=req.id, admin_user_id=admin_id, motivo="cambio criterio",
        )


@pytest.mark.asyncio
async def test_admin_reject_requires_motivo(db: AsyncSession) -> None:
    """admin_reject raise sin motivo (UX cliente always with claro reason)."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    admin_id = uuid.uuid4()
    client_user_id = uuid.uuid4()

    req = await _create_request_pending_cliente(
        db, project_id=project_uuid, admin_user_id=admin_id,
    )
    evidence_id = await _create_evidence_row(db, project_id=project_uuid)
    await cliente_upload(
        db, request_id=req.id, evidence_id=evidence_id,
        client_user_id=client_user_id,
    )

    with pytest.raises(ValueError, match="motivo requerido"):
        await admin_reject(
            db, request_id=req.id, admin_user_id=admin_id, motivo="",
        )


@pytest.mark.asyncio
async def test_admin_cancel_pending_only(db: AsyncSession) -> None:
    """admin_cancel state pending_cliente → cancelled · NOT allowed from pending_review."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    admin_id = uuid.uuid4()
    client_user_id = uuid.uuid4()

    # Cancel from pending_cliente (allowed)
    req1 = await _create_request_pending_cliente(
        db, project_id=project_uuid, admin_user_id=admin_id,
    )
    cancelled = await admin_cancel(
        db, request_id=req1.id, admin_user_id=admin_id,
    )
    assert cancelled.status == "cancelled"

    # NOT allowed from pending_review
    req2 = await _create_request_pending_cliente(
        db, project_id=project_uuid, admin_user_id=admin_id,
    )
    evidence_id = await _create_evidence_row(db, project_id=project_uuid)
    await cliente_upload(
        db, request_id=req2.id, evidence_id=evidence_id,
        client_user_id=client_user_id,
    )
    with pytest.raises(WorkflowStateError, match="Transition not allowed"):
        await admin_cancel(
            db, request_id=req2.id, admin_user_id=admin_id,
        )


# ════════════════════════════════════════════════════════════════════
# Phase 3A · End-to-end happy-path flow
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_end_to_end_full_happy_flow(db: AsyncSession) -> None:
    """E2E happy: admin create → cliente upload → admin approve · audit trail full."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    admin_id = uuid.uuid4()
    client_user_id = uuid.uuid4()
    evidence_id = await _create_evidence_row(db, project_id=project_uuid)

    # Step 1 · admin create
    req = await create_request(
        db,
        project_id=project_uuid,
        created_by_user_id=admin_id,
        titulo="Aportar política backup",
        measure_code="mp.info.6",
        tipo_documento="política",
        deadline_date=date.today() + timedelta(days=10),
    )
    assert req.status == "pending_cliente"

    # Step 2 · cliente upload
    after_upload = await cliente_upload(
        db, request_id=req.id, evidence_id=evidence_id,
        client_user_id=client_user_id,
    )
    assert after_upload.status == "pending_review"
    assert after_upload.evidence_id == evidence_id

    # Step 3 · admin approve · terminal state
    final = await admin_approve(
        db, request_id=req.id, admin_user_id=admin_id,
    )
    assert final.status == "approved"
    assert final.cliente_uploaded_at is not None
    assert final.admin_validated_at is not None

    # Verify persistence (single row · same id end-to-end)
    persisted = (await db.execute(
        select(EvidenceRequest).where(EvidenceRequest.id == req.id)
    )).scalar_one()
    assert persisted.status == "approved"
    assert persisted.evidence_id == evidence_id
