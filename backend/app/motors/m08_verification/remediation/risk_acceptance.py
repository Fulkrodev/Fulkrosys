"""Aceptación de riesgo con justificación, autoridad y caducidad (doc §8).

No todo se arregla; aceptar un riesgo justificado es legítimo y el auditor
lo admite SI está documentado y acotado. Flujo:

  propuesta → justificación registrada → aprobación con autoridad →
  estado `risk_accepted` con FECHA DE CADUCIDAD → re-revisión al caducar.

Evita la ficción de "todo perfecto": a veces la respuesta auditable correcta
es "riesgo aceptado y revisado". Emite evidencia append-only (R6).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m08_verification.finding_state_machine import (
    FindingState, transition,
)
from backend.app.motors.m08_verification.models import (
    EvidenceRecord, VerificationFinding,
)


class RiskAcceptanceError(Exception):
    pass


async def accept_risk(
    db: AsyncSession,
    finding: VerificationFinding,
    *,
    justification: str,
    approved_by: str,
    expires_at: datetime,
    now: datetime | None = None,
) -> VerificationFinding:
    """Acepta el riesgo de un finding (doc §8). Requiere justificación,
    autoridad aprobadora y caducidad. Transición de estado validada."""
    now = now or datetime.now(timezone.utc)
    if not justification or not justification.strip():
        raise RiskAcceptanceError("risk_accepted requiere justificación")
    if not approved_by or not approved_by.strip():
        raise RiskAcceptanceError("risk_accepted requiere autoridad aprobadora")
    if expires_at is None:
        raise RiskAcceptanceError("risk_accepted requiere fecha de caducidad")
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        raise RiskAcceptanceError("la caducidad debe ser futura")

    current = finding.finding_state or FindingState.DETECTED
    # Valida transición (risk_accepted alcanzable desde estados vivos)
    finding.finding_state = transition(current, FindingState.RISK_ACCEPTED)
    finding.status = "accepted_risk"
    finding.accepted_risk_justification = justification.strip()
    finding.accepted_risk_approved_by = approved_by.strip()
    finding.risk_accepted_by = approved_by.strip()
    finding.risk_accepted_expires_at = expires_at

    db.add(EvidenceRecord(
        project_id=finding.project_id, client_id=None,
        run_id=finding.run_id, finding_id=finding.id,
        actor=f"human:{approved_by.strip()}",
        action="finding.risk_accepted",
        component="m08:remediation.risk_acceptance",
        output_hash=finding.finding_hash,
        ens_relevance=finding.ens_primary_measure,
        payload={
            "justification": justification.strip()[:2000],
            "approved_by": approved_by.strip(),
            "expires_at": expires_at.isoformat(),
            "severity": finding.severity,
        },
    ))
    await db.flush()
    return finding


async def list_expired_risk_acceptances(
    db: AsyncSession,
    project_id: uuid.UUID,
    *,
    now: datetime | None = None,
) -> list[VerificationFinding]:
    """Findings con riesgo aceptado YA CADUCADO → exigen re-revisión (doc §8)."""
    now = now or datetime.now(timezone.utc)
    stmt = select(VerificationFinding).where(
        VerificationFinding.project_id == project_id,
        VerificationFinding.deleted_at.is_(None),
        VerificationFinding.finding_state == FindingState.RISK_ACCEPTED,
        VerificationFinding.risk_accepted_expires_at.isnot(None),
        VerificationFinding.risk_accepted_expires_at <= now,
    )
    return list((await db.execute(stmt)).scalars().all())


def risk_acceptance_status(
    finding: VerificationFinding, *, now: datetime | None = None,
) -> dict[str, Any]:
    """Estado de la aceptación de riesgo de un finding (para UI/auditoría)."""
    now = now or datetime.now(timezone.utc)
    if finding.finding_state != FindingState.RISK_ACCEPTED:
        return {"accepted": False}
    expires = finding.risk_accepted_expires_at
    if expires is not None and expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    expired = bool(expires and expires <= now)
    return {
        "accepted": True,
        "approved_by": finding.risk_accepted_by,
        "expires_at": expires.isoformat() if expires else None,
        "expired": expired,
        "needs_rereview": expired,
        "justification": finding.accepted_risk_justification,
    }
