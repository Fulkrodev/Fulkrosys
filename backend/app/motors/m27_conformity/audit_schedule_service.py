"""Audit schedule service · SAN-C.MB-10.6 · art. 31 RD 311/2022.

Gestión de auditorías bienales (Media/Alta) + extraordinarias por
cambios sustanciales (cloud migration, datacenter change, merger).

* ``schedule_biannual_audit`` · trigger automático al obtener conformidad.
* ``reschedule_on_substantial_change`` · cambio sustancial reinicia
  cómputo + crea audit extraordinaria que anula la bienal pendiente.
* ``upcoming_audits`` · lista próximos N días vencer (notificación).

Refs: SAN-C.MB-10.6 · art. 31 RD 311/2022 · CCN-STIC 802
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.motors.m27_conformity.bienio import (
    proxima_fecha_bienal,
)


# O1 · el plazo del art. 31 vive en m27_conformity/bienio.py. Antes aqui habia
# "730  # 2 años exactos", que ni son exactos (se come el bisiesto) ni eran
# los mismos que los 720 de conformity_service_paso5.
SUBSTANTIAL_CHANGE_TYPES: set[str] = {
    "cloud_migration",
    "datacenter_change",
    "merger",
    "categoria_change",
    "scope_expansion_significant",
}


@dataclass(slots=True)
class AuditScheduleEntry:
    id: uuid.UUID
    project_id: uuid.UUID
    audit_type: str
    next_audit_due: date
    last_audit_completed: date | None
    last_audit_result: str | None
    triggered_by: str
    days_until_due: int


async def schedule_biannual_audit(
    db: AsyncSession,
    project_id: uuid.UUID,
    conformity_date: date,
    *,
    metadata: dict[str, Any] | None = None,
) -> uuid.UUID:
    """Trigger automático: art. 31 exige auditoría externa cada 2 años para Media/Alta.

    Llamado típicamente al obtener conformidad inicial. Crea entrada
    audit_schedule con ``next_audit_due = conformity_date + 2 años`` (art. 31).
    Idempotente: si ya existe biannual activa, actualiza fecha.
    """
    next_due = proxima_fecha_bienal(conformity_date)
    sched_id = uuid.uuid4()

    existing = await db.execute(
        sa_text(
            "SELECT id FROM audit_schedules "
            "WHERE project_id = :pid AND audit_type = 'biannual' "
            "  AND deleted_at IS NULL "
            "ORDER BY created_at DESC LIMIT 1"
        ),
        {"pid": str(project_id)},
    )
    existing_id = existing.scalar()

    metadata_json = json.dumps(metadata or {})

    if existing_id is not None:
        await db.execute(
            sa_text(
                "UPDATE audit_schedules SET "
                "  next_audit_due = :due, "
                "  last_audit_completed = :last, "
                "  triggered_by = 'art_31_periodic', "
                "  metadata_jsonb = CAST(:meta AS jsonb), "
                "  updated_at = NOW() "
                "WHERE id = :id"
            ),
            {
                "due": next_due,
                "last": conformity_date,
                "meta": metadata_json,
                "id": str(existing_id),
            },
        )
        return uuid.UUID(str(existing_id))

    await db.execute(
        sa_text(
            "INSERT INTO audit_schedules "
            "(id, project_id, audit_type, next_audit_due, "
            " last_audit_completed, triggered_by, metadata_jsonb) "
            "VALUES (:id, :pid, 'biannual', :due, :last, "
            "        'art_31_periodic', CAST(:meta AS jsonb))"
        ),
        {
            "id": str(sched_id),
            "pid": str(project_id),
            "due": next_due,
            "last": conformity_date,
            "meta": metadata_json,
        },
    )
    return sched_id


async def reschedule_on_substantial_change(
    db: AsyncSession,
    project_id: uuid.UUID,
    change_type: str,
    change_date: date,
    *,
    metadata: dict[str, Any] | None = None,
) -> uuid.UUID | None:
    """Cambio sustancial reinicia cómputo 2 años + crea extraordinary audit.

    Anula la auditoría bienal previa (soft-delete) y crea una
    extraordinaria con ``next_audit_due = change_date + 90 días``
    (plazo razonable para evaluación post-cambio).

    Devuelve None si ``change_type`` no es sustancial.
    """
    if change_type not in SUBSTANTIAL_CHANGE_TYPES:
        return None

    # Anular bienal vigente
    await db.execute(
        sa_text(
            "UPDATE audit_schedules "
            "SET deleted_at = NOW() "
            "WHERE project_id = :pid AND audit_type = 'biannual' "
            "  AND deleted_at IS NULL"
        ),
        {"pid": str(project_id)},
    )

    sched_id = uuid.uuid4()
    next_due = change_date + timedelta(days=90)
    metadata_json = json.dumps({**(metadata or {}), "change_date": change_date.isoformat()})

    await db.execute(
        sa_text(
            "INSERT INTO audit_schedules "
            "(id, project_id, audit_type, next_audit_due, "
            " triggered_by, metadata_jsonb) "
            "VALUES (:id, :pid, 'extraordinary', :due, "
            "        :triggered, CAST(:meta AS jsonb))"
        ),
        {
            "id": str(sched_id),
            "pid": str(project_id),
            "due": next_due,
            "triggered": change_type,
            "meta": metadata_json,
        },
    )
    return sched_id


async def list_upcoming_audits(
    db: AsyncSession,
    project_id: uuid.UUID,
    *,
    horizon_days: int = 365,
) -> list[AuditScheduleEntry]:
    """Lista auditorías programadas en horizonte de N días."""
    horizon = date.today() + timedelta(days=horizon_days)
    rows = await db.execute(
        sa_text(
            "SELECT id::text, audit_type, next_audit_due, "
            "       last_audit_completed, last_audit_result, triggered_by "
            "FROM audit_schedules "
            "WHERE project_id = :pid "
            "  AND deleted_at IS NULL "
            "  AND next_audit_due <= :horizon "
            "ORDER BY next_audit_due ASC"
        ),
        {"pid": str(project_id), "horizon": horizon},
    )
    today_d = date.today()
    return [
        AuditScheduleEntry(
            id=uuid.UUID(r[0]),
            project_id=project_id,
            audit_type=r[1],
            next_audit_due=r[2],
            last_audit_completed=r[3],
            last_audit_result=r[4],
            triggered_by=r[5],
            days_until_due=(r[2] - today_d).days,
        )
        for r in rows.fetchall()
    ]
