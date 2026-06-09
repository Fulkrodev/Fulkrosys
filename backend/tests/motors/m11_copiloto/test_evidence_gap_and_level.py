"""#22 Ola 5 · cruce del semáforo por medida (#20) + adaptación por nivel ENS.

- evidence_gap_measures: medida aplicable SIN evidencia 'clean' aparece; con
  evidencia clean NO (anti-falso-verde · reusa criterio Evidence-based de #20).
- nivel ENS: BÁSICA en CONFORMIDAD = autodeclaración (sin ENAC); ALTA en
  VERIFICACION = pentest obligatorio (no hardcodear el cierre).
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.workflow_phase import WorkflowPhase
from backend.app.motors.m11_copiloto.workflow_state_scanner import (
    WorkflowScannerOptions,
    compute_workflow_state,
    top_action_for_role,
)
from backend.tests.conftest import _admin_setup, setup_test_project


pytestmark = pytest.mark.asyncio


async def _set_phase(db, pid: uuid.UUID, phase: WorkflowPhase) -> None:
    async with _admin_setup(db):
        await db.execute(text("SET LOCAL session_replication_role = 'replica'"))
        await db.execute(
            text("UPDATE projects SET fase = :p WHERE id = :pid"),
            {"p": phase.value, "pid": str(pid)},
        )
        await db.execute(text("SET LOCAL session_replication_role = 'origin'"))


async def _set_categoria(db, pid: uuid.UUID, cat: str) -> None:
    async with _admin_setup(db):
        await db.execute(
            text("UPDATE projects SET categoria_objetivo = :c WHERE id = :pid"),
            {"c": cat, "pid": str(pid)},
        )


async def test_evidence_gap_measures_crossing(db: AsyncSession):
    """Medida sin evidencia clean → en evidence_gap_measures · con clean → fuera."""
    _client_id, project_id = await setup_test_project(db)
    pid = uuid.UUID(project_id)
    await _set_phase(db, pid, WorkflowPhase.IMPLANTACION)

    async with _admin_setup(db):
        measures = (await db.execute(text(
            "SELECT id, codigo FROM ens_measures ORDER BY codigo LIMIT 2"
        ))).fetchall()
    assert len(measures) >= 2, "el catálogo ens_measures debe estar seeded"
    (gap_mid, gap_code), (ok_mid, ok_code) = measures[0], measures[1]

    async with _admin_setup(db):
        # dda_entries enlaza la medida por measure_id (NO tiene measure_code).
        for mid in (gap_mid, ok_mid):
            await db.execute(text(
                "INSERT INTO dda_entries "
                "(id, project_id, measure_id, aplicabilidad, created_at) "
                "VALUES (:id, :pid, :mid, 'aplica', now())"
            ), {"id": str(uuid.uuid4()), "pid": project_id, "mid": str(mid)})
        # Evidencia 'clean' SOLO para ok_code (la otra queda sin respaldo).
        await db.execute(text(
            "INSERT INTO evidence "
            "(id, project_id, measure_code, scan_status, vigente, created_at) "
            "VALUES (:id, :pid, :code, 'clean', true, now())"
        ), {"id": str(uuid.uuid4()), "pid": project_id, "code": ok_code})

    state = await compute_workflow_state(
        db, pid, options=WorkflowScannerOptions(role_filter="admin"),
    )
    assert gap_code in state.evidence_gap_measures, (
        "medida aplicable sin evidencia clean debe aparecer como gap"
    )
    assert ok_code not in state.evidence_gap_measures, (
        "medida con evidencia clean NO debe aparecer (anti-falso-verde)"
    )


async def test_evidence_gaps_empty_when_not_evidence_phase(db: AsyncSession):
    """Fuera de fases de evidencia el cruce no se computa (guard de scope)."""
    _client_id, project_id = await setup_test_project(db)
    pid = uuid.UUID(project_id)
    await _set_phase(db, pid, WorkflowPhase.DIAGNOSTICO)

    state = await compute_workflow_state(
        db, pid, options=WorkflowScannerOptions(role_filter="admin"),
    )
    assert state.evidence_gap_measures == []


async def test_level_basica_conformidad_es_autodeclaracion(db: AsyncSession):
    """BÁSICA en CONFORMIDAD → la acción admin habla de autodeclaración, no ENAC."""
    _client_id, project_id = await setup_test_project(db)
    pid = uuid.UUID(project_id)
    await _set_phase(db, pid, WorkflowPhase.CONFORMIDAD)
    await _set_categoria(db, pid, "basica")

    state = await compute_workflow_state(
        db, pid, options=WorkflowScannerOptions(role_filter="admin"),
    )
    top = top_action_for_role(state, "admin")
    assert top is not None and top.motor == "m09"
    assert "AUTODECLARACIÓN" in top.description_admin.upper(), (
        "BÁSICA cierra por autodeclaración 808/809"
    )
    assert "NO requiere auditoría ENAC" in top.description_admin


async def test_level_alta_verificacion_exige_pentest(db: AsyncSession):
    """ALTA en VERIFICACION → la acción admin exige pentest obligatorio."""
    _client_id, project_id = await setup_test_project(db)
    pid = uuid.UUID(project_id)
    await _set_phase(db, pid, WorkflowPhase.VERIFICACION)
    await _set_categoria(db, pid, "alta")

    state = await compute_workflow_state(
        db, pid, options=WorkflowScannerOptions(role_filter="admin"),
    )
    top = top_action_for_role(state, "admin")
    assert top is not None and top.motor == "m08"
    assert "pentest" in top.description_admin.lower()
    assert "ALTA" in top.description_admin
