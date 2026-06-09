"""Evidence renewal request service.

Creates renewal requests for expiring or expired evidence.
Idempotent — avoids duplicate pending requests.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m07_evidence.freshness_service import (
    check_freshness_for_project,
    _classify,
)


@dataclass
class RenewalOutcome:
    """Result of a renewal request creation."""
    renewal_id: uuid.UUID | None = None
    evidence_id: uuid.UUID | None = None
    created: bool = False
    already_pending: bool = False
    error: str | None = None
    motivo: str | None = None


async def create_renewal_request(
    session: AsyncSession,
    evidence_id: uuid.UUID,
    motivo: str | None = None,
) -> RenewalOutcome:
    """Create a renewal request for a single evidence.

    Idempotent: if a pending request already exists, returns it.
    Auto-detects motivo from freshness state if not provided.
    """
    # Check evidence exists
    ev_result = await session.execute(
        text(
            "SELECT id, project_id, measure_code, fecha_caducidad "
            "FROM evidence WHERE id = :eid AND deleted_at IS NULL"
        ),
        {"eid": str(evidence_id)},
    )
    ev_row = ev_result.fetchone()
    if ev_row is None:
        return RenewalOutcome(
            evidence_id=evidence_id,
            error="Evidence not found",
        )

    project_id = ev_row[1]
    measure_code = ev_row[2] or ""
    fecha_caducidad = ev_row[3]

    # Auto-detect motivo
    if motivo is None:
        estado, _ = _classify(fecha_caducidad, warning_days=30)
        if estado == "caducada":
            motivo = "caducada"
        elif estado == "proxima_caducidad":
            motivo = "proxima_caducidad"
        else:
            motivo = "renovacion_manual"

    # Check for existing pending request (idempotent)
    existing = await session.execute(
        text(
            "SELECT id FROM evidence_renewal_requests "
            "WHERE evidence_id = :eid AND estado = 'pending' AND deleted_at IS NULL "
            "LIMIT 1"
        ),
        {"eid": str(evidence_id)},
    )
    existing_row = existing.fetchone()
    if existing_row is not None:
        rid = existing_row[0] if isinstance(existing_row[0], uuid.UUID) else uuid.UUID(str(existing_row[0]))
        return RenewalOutcome(
            renewal_id=rid,
            evidence_id=evidence_id,
            created=False,
            already_pending=True,
            motivo=motivo,
        )

    # Create new renewal request
    renewal_id = uuid.uuid4()
    dias = (fecha_caducidad - date.today()).days if fecha_caducidad else None

    await session.execute(
        text("""
            INSERT INTO evidence_renewal_requests (
                id, evidence_id, project_id, measure_code,
                motivo, estado, fecha_caducidad_original,
                dias_para_caducar, created_at
            ) VALUES (
                :id, :eid, :pid, :mc,
                :motivo, 'pending', :fco,
                :dias, now()
            )
        """),
        {
            "id": str(renewal_id),
            "eid": str(evidence_id),
            "pid": str(project_id),
            "mc": measure_code,
            "motivo": motivo,
            "fco": fecha_caducidad,
            "dias": dias,
        },
    )
    await session.flush()

    return RenewalOutcome(
        renewal_id=renewal_id,
        evidence_id=evidence_id,
        created=True,
        already_pending=False,
        motivo=motivo,
    )


async def create_renewal_requests_from_freshness_report(
    session: AsyncSession,
    project_id: uuid.UUID,
    warning_days: int = 30,
) -> list[RenewalOutcome]:
    """Batch-create renewal requests for all expiring/expired evidence.

    Runs freshness check, then creates renewal requests for items
    classified as proxima_caducidad or caducada.
    """
    report = await check_freshness_for_project(session, project_id, warning_days)

    outcomes: list[RenewalOutcome] = []
    for item in report.items:
        if item.estado in ("caducada", "proxima_caducidad"):
            outcome = await create_renewal_request(
                session,
                evidence_id=item.evidence_id,
                motivo=item.estado,
            )
            outcomes.append(outcome)

    return outcomes
