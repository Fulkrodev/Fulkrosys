"""Tests audit_schedule_service · SAN-C.MB-10.6."""
from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m27_conformity.audit_schedule_service import (
    list_upcoming_audits,
    reschedule_on_substantial_change,
    schedule_biannual_audit,
)
from backend.tests.conftest import _admin_setup

# O1 · el bienio del art. 31 es de ANYOS de calendario, no de un numero fijo
# de dias: 2026-05-05 + 2 anyos cruza el 29-F de 2028 y son 731 dias, no
# 730. Por eso se asevera contra la funcion canonica y no contra una
# constante: la constante en dias es justo lo que estaba mal.
from backend.app.motors.m27_conformity.bienio import proxima_fecha_bienal


async def _create_project(db: AsyncSession) -> tuple[uuid.UUID, uuid.UUID]:
    from backend.app.database import set_tenant_context

    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, sector, created_at) "
                "VALUES (:cid, :nombre, :cif, 'publico', now())"
            ),
            {"cid": str(client_id), "nombre": f"AS {cif}", "cif": cif},
        )
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, fase, created_at) "
                "VALUES (:pid, :cid, 'Audit sched test', 'conformidad', now())"
            ),
            {"pid": str(project_id), "cid": str(client_id)},
        )
    await set_tenant_context(db, client_id=client_id, project_id=project_id)
    return client_id, project_id


@pytest.mark.asyncio
async def test_schedule_biannual_audit_creates_entry(db: AsyncSession):
    """Crea biannual schedule con next_due = conformity + 730d."""
    _, project_id = await _create_project(db)
    conformity_date = date(2026, 5, 5)

    sched_id = await schedule_biannual_audit(db, project_id, conformity_date)
    assert sched_id is not None

    upcoming = await list_upcoming_audits(db, project_id, horizon_days=1000)
    assert len(upcoming) == 1
    entry = upcoming[0]
    assert entry.audit_type == "biannual"
    assert entry.next_audit_due == proxima_fecha_bienal(conformity_date)
    assert entry.triggered_by == "art_31_periodic"


@pytest.mark.asyncio
async def test_schedule_biannual_idempotent(db: AsyncSession):
    """Re-llamar con diferente conformity_date actualiza entry existente."""
    _, project_id = await _create_project(db)
    await schedule_biannual_audit(db, project_id, date(2026, 5, 5))
    await schedule_biannual_audit(db, project_id, date(2026, 8, 1))

    upcoming = await list_upcoming_audits(db, project_id, horizon_days=1000)
    biannual = [e for e in upcoming if e.audit_type == "biannual"]
    assert len(biannual) == 1
    assert biannual[0].next_audit_due == proxima_fecha_bienal(date(2026, 8, 1))


@pytest.mark.asyncio
async def test_substantial_change_creates_extraordinary_and_cancels_biannual(
    db: AsyncSession,
):
    """Cambio sustancial cancela bienal + crea extraordinary 90d."""
    _, project_id = await _create_project(db)
    await schedule_biannual_audit(db, project_id, date(2026, 5, 5))

    change_date = date(2026, 7, 1)
    extra_id = await reschedule_on_substantial_change(
        db, project_id, "cloud_migration", change_date
    )
    assert extra_id is not None

    upcoming = await list_upcoming_audits(db, project_id, horizon_days=1000)
    types = {e.audit_type for e in upcoming}
    assert "biannual" not in types  # canceled
    assert "extraordinary" in types

    extra = next(e for e in upcoming if e.audit_type == "extraordinary")
    assert extra.next_audit_due == change_date + timedelta(days=90)
    assert extra.triggered_by == "cloud_migration"


@pytest.mark.asyncio
async def test_non_substantial_change_returns_none(db: AsyncSession):
    """Cambio no sustancial no crea extraordinary ni cancela bienal."""
    _, project_id = await _create_project(db)
    await schedule_biannual_audit(db, project_id, date(2026, 5, 5))

    extra_id = await reschedule_on_substantial_change(
        db, project_id, "minor_update", date(2026, 7, 1)
    )
    assert extra_id is None

    upcoming = await list_upcoming_audits(db, project_id, horizon_days=1000)
    assert any(e.audit_type == "biannual" for e in upcoming)
    assert not any(e.audit_type == "extraordinary" for e in upcoming)


@pytest.mark.asyncio
async def test_list_horizon_filters_far_future(db: AsyncSession):
    """horizon_days excluye auditorías muy alejadas."""
    _, project_id = await _create_project(db)
    await schedule_biannual_audit(db, project_id, date(2026, 5, 5))

    upcoming_30d = await list_upcoming_audits(db, project_id, horizon_days=30)
    upcoming_full = await list_upcoming_audits(db, project_id, horizon_days=1000)
    assert len(upcoming_30d) == 0  # bienal está a ~2 años
    assert len(upcoming_full) == 1
