"""#28 Ola8 · calendario de pagos: scheduled_date por hito.

La columna scheduled_date (fecha prevista de cobro) se puebla en el factory
cuando se aporta start_date, distribuyendo la duración del proyecto por fase/tier.
Backward-compat: sin start_date → None (los hitos siguen siendo phase_complete).
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.billing.milestone_factory import (
    MilestoneFactory,
    estimate_scheduled_date,
)
from backend.tests.conftest import _admin_setup, setup_test_project


def test_estimate_scheduled_date_distributes_by_phase():
    start = date(2026, 1, 1)
    # fase 1 (firma) → inicio del proyecto
    assert estimate_scheduled_date(start, 1, "MEDIA") == start
    # fase 8 (conformidad) → fin · MEDIA ~10 semanas
    assert estimate_scheduled_date(start, 8, "MEDIA") == start + timedelta(weeks=10)
    # ALTA dura más (~16 semanas)
    assert estimate_scheduled_date(start, 8, "ALTA") == start + timedelta(weeks=16)


async def _mk_contract(db, project_id) -> uuid.UUID:
    cid = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(
            sa_text(
                "INSERT INTO contracts (id, tipo, estado, created_at) "
                "VALUES (:id, 'c001', 'draft', now())"
            ),
            {"id": str(cid)},
        )
    await db.flush()
    return cid


@pytest.mark.asyncio
async def test_milestones_get_scheduled_date_when_start_provided(db: AsyncSession):
    _, project_id = await setup_test_project(db)
    contract_id = await _mk_contract(db, project_id)

    created = await MilestoneFactory(db).create_milestones_for_contract(
        contract_id=contract_id,
        project_id=uuid.UUID(project_id),
        categoria="MEDIA",
        contract_total=Decimal("11500.00"),
        start_date=date(2026, 1, 1),
    )
    assert len(created) > 0
    assert all(m.scheduled_date is not None for m in created)
    # el primer hito (firma · fase 1) cae en la fecha de inicio
    assert min(m.scheduled_date for m in created) == date(2026, 1, 1)


@pytest.mark.asyncio
async def test_milestones_no_scheduled_date_without_start(db: AsyncSession):
    _, project_id = await setup_test_project(db)
    contract_id = await _mk_contract(db, project_id)

    created = await MilestoneFactory(db).create_milestones_for_contract(
        contract_id=contract_id,
        project_id=uuid.UUID(project_id),
        categoria="MEDIA",
        contract_total=Decimal("11500.00"),
    )
    assert len(created) > 0
    assert all(m.scheduled_date is None for m in created)
