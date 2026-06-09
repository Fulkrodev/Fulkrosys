"""#34 Ola8 · gate lifecycle_state='RETAINER' en list_for_client.

El cliente solo ve sus check-ins trimestrales si su proyecto está en RETAINER.
Un cliente que rechazó/terminó el retainer no los ve aunque conozca los IDs
(la RLS por project_id sola no bastaba · gap señalado por el audit Ola II).
"""
from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m23_retainer.retainer_checkin_service import (
    RetainerCheckinService,
    compute_quarter_label,
)
from backend.tests.conftest import _admin_setup, setup_test_project


async def _seed_active_retainer(db, client_id, project_id):
    await db.execute(
        sa_text(
            "INSERT INTO retainer_contracts "
            "(id, client_id, project_id, perfil, estado, created_at) "
            "VALUES (:id, :cid, :pid, 'R_STD', 'active', now())"
        ),
        {"id": str(uuid.uuid4()), "cid": client_id, "pid": project_id},
    )
    await db.flush()


@pytest.mark.asyncio
async def test_list_for_client_gated_by_lifecycle_state(db: AsyncSession):
    client_id, project_id = await setup_test_project(db)
    await _seed_active_retainer(db, client_id, project_id)
    svc = RetainerCheckinService(db)

    report = await svc.generate_quarterly_report_draft(
        project_id=uuid.UUID(project_id),
        period_quarter=compute_quarter_label(date.today()),
    )

    # Curado → enviado al cliente + proyecto en RETAINER
    async with _admin_setup(db):
        await db.execute(
            sa_text(
                "UPDATE retainer_quarterly_reports "
                "SET admin_curation_status='sent_to_client' WHERE id=:id"
            ),
            {"id": str(report.id)},
        )
        await db.execute(
            sa_text("UPDATE projects SET lifecycle_state='RETAINER' WHERE id=:pid"),
            {"pid": project_id},
        )
    await db.flush()

    visible = await svc.list_for_client(uuid.UUID(project_id))
    assert len(visible) == 1  # en RETAINER → visible

    # Cliente fuera del retainer (rechazó) → NO visible aunque conozca IDs
    async with _admin_setup(db):
        await db.execute(
            sa_text("UPDATE projects SET lifecycle_state='ENDED_CHURN' WHERE id=:pid"),
            {"pid": project_id},
        )
    await db.flush()

    gated = await svc.list_for_client(uuid.UUID(project_id))
    assert gated == []  # #34 gate cierra el gap
