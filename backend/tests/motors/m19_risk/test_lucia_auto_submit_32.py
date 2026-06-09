"""#32 Ola8 · auto-notificación LUCIA (INCIBE-CERT) en incidente Alto/Crítico.

Obligación legal art. 33 RD 311/2022: un incidente critical/high en proyecto con
lucia_enabled debe notificarse automáticamente. Antes era dead-code (submit_incident
existía pero nadie lo invocaba). Sin credenciales del cliente → 'pending_credentials'
(fallback honesto). Siempre deja rastro en audit_log (R6).
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m19_risk.incident_workflow_service import (
    IncidentWorkflowService,
)
from backend.tests.conftest import _admin_setup, setup_test_project


async def _enable_lucia(db, project_id):
    async with _admin_setup(db):
        await db.execute(
            sa_text("UPDATE projects SET lucia_enabled=true WHERE id=:pid"),
            {"pid": project_id},
        )
    await db.flush()


@pytest.mark.asyncio
async def test_critical_incident_auto_submits_lucia(db: AsyncSession):
    _, project_id = await setup_test_project(db)
    await _enable_lucia(db, project_id)

    svc = IncidentWorkflowService(db)
    incident = await svc.create_incident(
        project_id=uuid.UUID(project_id),
        severidad="critical",
        descripcion="Brecha de datos critica - exfiltracion detectada",
    )

    # Incidente enlazado a submission LUCIA (sin creds cliente -> pending_credentials)
    sid = (
        await db.execute(
            sa_text("SELECT lucia_submission_id FROM incidents WHERE id=:iid"),
            {"iid": str(incident.id)},
        )
    ).scalar()
    assert sid is not None, "el incidente critico debe enlazar una submission LUCIA"

    sub = (
        await db.execute(
            sa_text("SELECT status FROM lucia_submissions WHERE id=:sid"),
            {"sid": str(sid)},
        )
    ).first()
    assert sub is not None
    assert sub[0] == "pending_credentials"

    # R6 · audit_log art.33 (no silent-fail)
    n = (
        await db.execute(
            sa_text(
                "SELECT count(*) FROM audit_log "
                "WHERE registro_id=:rid AND accion='submit_lucia'"
            ),
            {"rid": str(incident.id)},
        )
    ).scalar()
    assert n == 1


@pytest.mark.asyncio
async def test_medium_incident_no_lucia_submit(db: AsyncSession):
    _, project_id = await setup_test_project(db)
    await _enable_lucia(db, project_id)

    svc = IncidentWorkflowService(db)
    incident = await svc.create_incident(
        project_id=uuid.UUID(project_id),
        severidad="medium",
        descripcion="Incidencia menor sin impacto",
    )
    sid = (
        await db.execute(
            sa_text("SELECT lucia_submission_id FROM incidents WHERE id=:iid"),
            {"iid": str(incident.id)},
        )
    ).scalar()
    assert sid is None  # medium -> internal_only -> NO auto-submit
