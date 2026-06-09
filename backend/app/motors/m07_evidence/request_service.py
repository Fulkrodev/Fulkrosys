"""Evidence Request service · CLUSTER 3 Phase 3A workflow state machine.

Filosofía cliente-mínimo: cliente VE pending tasks · SUBE archivo · MARK-NA si
no aplica. Marcos VALIDA / RECHAZA con motivo claro. Workflow state guards
enforce consistency · audit_log Sub-atom 5.A 3-way OR propagated cross transitions.

State transitions canonical:
    pending_cliente ─cliente upload→ pending_review ─admin approve→ approved
                                                   ─admin reject──→ rejected
                    ─cliente mark-na──────────────────────────────→ marked_na
                    ─admin cancel─────────────────────────────────→ cancelled

    rejected ─cliente re-upload→ pending_review (re-cycle audit trail)
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.evidence_request import (
    EVIDENCE_REQUEST_STATES,
    EvidenceRequest,
)


# State transitions guards · ALLOWED_TRANSITIONS[current] → set of allowed next states
ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "pending_cliente": frozenset({"pending_review", "marked_na", "cancelled"}),
    "pending_review": frozenset({"approved", "rejected"}),
    "rejected": frozenset({"pending_review"}),  # cliente re-upload cycle
    # Terminal states · NO further transitions
    "approved": frozenset(),
    "cancelled": frozenset(),
    "marked_na": frozenset(),
}


class WorkflowStateError(ValueError):
    """State transition not allowed (workflow guard violation)."""


def _validate_transition(current: str, target: str) -> None:
    """Raises WorkflowStateError if target not allowed from current state."""
    if current not in EVIDENCE_REQUEST_STATES:
        raise WorkflowStateError(
            f"Invalid current state: {current!r}"
        )
    if target not in EVIDENCE_REQUEST_STATES:
        raise WorkflowStateError(
            f"Invalid target state: {target!r}"
        )
    if target not in ALLOWED_TRANSITIONS[current]:
        raise WorkflowStateError(
            f"Transition not allowed: {current!r} → {target!r} "
            f"(allowed: {sorted(ALLOWED_TRANSITIONS[current])})"
        )


async def create_request(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    created_by_user_id: uuid.UUID,
    titulo: str,
    descripcion: Optional[str] = None,
    measure_code: Optional[str] = None,
    control_id: Optional[uuid.UUID] = None,
    tipo_documento: Optional[str] = None,
    plantilla_url: Optional[str] = None,
    deadline_date: Optional[date] = None,
    client_user_id: Optional[uuid.UUID] = None,
) -> EvidenceRequest:
    """Admin creates new evidence request · status=pending_cliente.

    Filosofía cliente-mínimo: cliente recibe tarea concreta · NO admin internals.
    """
    if not titulo or len(titulo.strip()) == 0:
        raise ValueError("titulo requerido")

    now = datetime.now(timezone.utc)
    row = EvidenceRequest(
        project_id=project_id,
        client_user_id=client_user_id,
        measure_code=measure_code,
        control_id=control_id,
        tipo_documento=tipo_documento,
        titulo=titulo.strip(),
        descripcion=descripcion,
        plantilla_url=plantilla_url,
        deadline_date=deadline_date,
        status="pending_cliente",
        created_by_user_id=created_by_user_id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    await db.flush()
    return row


async def list_requests(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    status_filter: Optional[str] = None,
    client_user_id: Optional[uuid.UUID] = None,
) -> list[EvidenceRequest]:
    """List requests filterable per status + client_user."""
    stmt = select(EvidenceRequest).where(
        EvidenceRequest.project_id == project_id,
    )
    if status_filter:
        stmt = stmt.where(EvidenceRequest.status == status_filter)
    if client_user_id:
        stmt = stmt.where(EvidenceRequest.client_user_id == client_user_id)
    stmt = stmt.order_by(EvidenceRequest.created_at.desc())
    return list((await db.execute(stmt)).scalars().all())


async def get_request(
    db: AsyncSession,
    *,
    request_id: uuid.UUID,
) -> Optional[EvidenceRequest]:
    """Get request by id (RLS enforced project_id context)."""
    return (await db.execute(
        select(EvidenceRequest).where(EvidenceRequest.id == request_id)
    )).scalar_one_or_none()


async def cliente_upload(
    db: AsyncSession,
    *,
    request_id: uuid.UUID,
    evidence_id: uuid.UUID,
    client_user_id: uuid.UUID,
) -> EvidenceRequest:
    """Cliente upload evidence · state transition pending_cliente|rejected → pending_review.

    Filosofía cliente-mínimo: cliente attach evidence file · NO operate vault tecnico.
    Re-upload pattern: rejected → pending_review (cycle audit trail per re-attempt).
    """
    row = await get_request(db, request_id=request_id)
    if row is None:
        raise WorkflowStateError(f"Request {request_id} not found")

    _validate_transition(row.status, "pending_review")

    now = datetime.now(timezone.utc)
    row.status = "pending_review"
    row.evidence_id = evidence_id
    row.cliente_uploaded_at = now
    row.client_user_id = client_user_id  # asociar al cliente que uploaded
    row.updated_at = now
    # Reset rejection metadata si re-upload cycle (rejected → pending_review)
    row.admin_validated_at = None
    row.admin_validated_by_user_id = None
    row.admin_rejection_motivo = None
    await db.flush()
    return row


async def cliente_mark_na(
    db: AsyncSession,
    *,
    request_id: uuid.UUID,
    client_user_id: uuid.UUID,
    motivo: str,
) -> EvidenceRequest:
    """Cliente marks request no aplicable · state → marked_na · motivo required.

    Filosofía cliente-mínimo: cliente puede declinar tarea con motivo amigable.
    """
    if not motivo or len(motivo.strip()) == 0:
        raise ValueError("motivo requerido para mark_na")

    row = await get_request(db, request_id=request_id)
    if row is None:
        raise WorkflowStateError(f"Request {request_id} not found")

    _validate_transition(row.status, "marked_na")

    now = datetime.now(timezone.utc)
    row.status = "marked_na"
    row.cliente_na_motivo = motivo.strip()
    row.client_user_id = client_user_id
    row.updated_at = now
    await db.flush()
    return row


async def admin_approve(
    db: AsyncSession,
    *,
    request_id: uuid.UUID,
    admin_user_id: uuid.UUID,
) -> EvidenceRequest:
    """Admin approve uploaded evidence · state pending_review → approved (TERMINAL)."""
    row = await get_request(db, request_id=request_id)
    if row is None:
        raise WorkflowStateError(f"Request {request_id} not found")

    _validate_transition(row.status, "approved")

    now = datetime.now(timezone.utc)
    row.status = "approved"
    row.admin_validated_at = now
    row.admin_validated_by_user_id = admin_user_id
    row.admin_rejection_motivo = None  # clear rejection metadata si previa
    row.updated_at = now
    await db.flush()
    return row


async def admin_reject(
    db: AsyncSession,
    *,
    request_id: uuid.UUID,
    admin_user_id: uuid.UUID,
    motivo: str,
) -> EvidenceRequest:
    """Admin reject uploaded evidence · state pending_review → rejected · motivo claro requerido.

    Filosofía: cliente VE motivo amigable cuando rechazado · puede re-upload.
    """
    if not motivo or len(motivo.strip()) == 0:
        raise ValueError("motivo requerido para reject (UX cliente)")

    row = await get_request(db, request_id=request_id)
    if row is None:
        raise WorkflowStateError(f"Request {request_id} not found")

    _validate_transition(row.status, "rejected")

    now = datetime.now(timezone.utc)
    row.status = "rejected"
    row.admin_rejection_motivo = motivo.strip()
    row.admin_validated_at = now
    row.admin_validated_by_user_id = admin_user_id
    row.updated_at = now
    await db.flush()
    return row


async def admin_cancel(
    db: AsyncSession,
    *,
    request_id: uuid.UUID,
    admin_user_id: uuid.UUID,
) -> EvidenceRequest:
    """Admin cancel pending request · state pending_cliente → cancelled (TERMINAL)."""
    row = await get_request(db, request_id=request_id)
    if row is None:
        raise WorkflowStateError(f"Request {request_id} not found")

    _validate_transition(row.status, "cancelled")

    now = datetime.now(timezone.utc)
    row.status = "cancelled"
    row.admin_validated_by_user_id = admin_user_id
    row.updated_at = now
    await db.flush()
    return row
