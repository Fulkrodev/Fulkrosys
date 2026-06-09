"""F-08-03 · check_expiring_evidence real (antes stub vivo en Celery beat).

El task estaba programado a diario 06:00 pero sólo logueaba y retornaba sin
consultar caducidad ni alertar. Aquí verificamos la implementación real:

  - Evidencia caducada (fecha_caducidad < hoy) → escalado M18
    'evidencia_critica_caducada'.
  - Segundo run → NO duplica (idempotencia por proyecto/evidencia).
  - Evidencia que caduca pronto (<30d, aún vigente) → sólo recuento, NO escala
    (semántica honesta del trigger 'caducada' · decisión Marcos).

Fuente: F-08-03 + trigger M18 evidencia_critica_caducada.
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m07_evidence.tasks import _run_check_expiring_evidence
from backend.tests.conftest import _admin_setup, setup_test_project


async def _insert_evidence(
    db: AsyncSession, project_id: str, fecha_caducidad: date,
    nombre: str = "Certificado SSL",
) -> uuid.UUID:
    eid = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO evidence "
                "(id, project_id, nombre_tipo, fecha_caducidad, scan_status, "
                " vigente, created_at, updated_at) "
                "VALUES (:id, :pid, :n, :f, 'clean', true, now(), now())"
            ),
            {"id": str(eid), "pid": project_id, "n": nombre, "f": fecha_caducidad},
        )
    return eid


async def _count_escalations(db: AsyncSession, project_id: str) -> int:
    async with _admin_setup(db):
        return int((await db.execute(
            text(
                "SELECT COUNT(*) FROM escalation_events "
                "WHERE project_id = :pid "
                "  AND trigger = 'evidencia_critica_caducada' "
                "  AND resuelto = false"
            ),
            {"pid": project_id},
        )).scalar() or 0)


@pytest.mark.asyncio
async def test_expired_evidence_escalates(db: AsyncSession) -> None:
    _, project_id = await setup_test_project(db)
    await _insert_evidence(db, project_id, date.today() - timedelta(days=3))

    async with _admin_setup(db):
        result = await _run_check_expiring_evidence(db)

    assert result["status"] == "ok"
    assert result["escalated"] == 1
    assert result["skipped_existing"] == 0
    assert await _count_escalations(db, project_id) == 1


@pytest.mark.asyncio
async def test_second_run_does_not_duplicate(db: AsyncSession) -> None:
    _, project_id = await setup_test_project(db)
    # -5d (no -1d): evita el boundary CURRENT_DATE servidor vs date.today() cliente.
    await _insert_evidence(db, project_id, date.today() - timedelta(days=5))

    async with _admin_setup(db):
        first = await _run_check_expiring_evidence(db)
        second = await _run_check_expiring_evidence(db)

    assert first["escalated"] == 1
    assert second["escalated"] == 0
    assert second["skipped_existing"] == 1
    # Sólo un escalado abierto pese a dos runs.
    assert await _count_escalations(db, project_id) == 1


@pytest.mark.asyncio
async def test_expiring_soon_not_escalated(db: AsyncSession) -> None:
    _, project_id = await setup_test_project(db)
    await _insert_evidence(db, project_id, date.today() + timedelta(days=10))

    async with _admin_setup(db):
        result = await _run_check_expiring_evidence(db)

    assert result["escalated"] == 0
    assert result["expiring_soon"] == 1
    assert await _count_escalations(db, project_id) == 0
