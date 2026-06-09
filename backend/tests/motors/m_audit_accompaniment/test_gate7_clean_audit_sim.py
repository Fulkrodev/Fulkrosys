"""GATE-7 (#40/#43 · FRENTE D) · parón pre-ENAC sobre el último simulacro.

Verifica empirical (con los workflow gates HABILITADOS · el conftest los
desactiva por defecto · aquí los activamos vía env):
- #43: no se puede marcar internal_audit_completed sin un simulacro ejecutado.
- #40: no se puede solicitar ENAC (enac_audit_scheduled) con NC mayores
  (critical) abiertas en el último simulacro.
- escape-hatch admin (allow_open_nc=True) permite continuar y queda trazado.
- BÁSICA: no se puede firmar la Declaración (declaration_signed) sin simulacro.
"""
from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import text as sa_text

from backend.app.core.workflow_gates import WorkflowGateError
from backend.app.motors.m_audit_accompaniment.service import transition_state
from backend.app.motors.m_audit_accompaniment.state_machine import (
    STATE_BASICO_DECLARATION_DRAFTED,
    STATE_BASICO_DECLARATION_SIGNED,
    STATE_MA_DOCS_COLLECTED,
    STATE_MA_ENAC_AUDIT_SCHEDULED,
    STATE_MA_INTERNAL_AUDIT_COMPLETED,
    STATE_MA_INTERNAL_AUDIT_SCHEDULED,
    STATE_MA_PREPARATION,
)
from backend.tests.conftest import _admin_setup, setup_test_project


async def _create_project(db, categoria: str) -> uuid.UUID:
    client_id_str, project_id_str = await setup_test_project(db)
    project_id = uuid.UUID(project_id_str)
    async with _admin_setup(db):
        await db.execute(sa_text(
            "UPDATE projects SET categoria_objetivo = :cat WHERE id = :pid"
        ), {"cat": categoria, "pid": str(project_id)})
    return project_id


async def _emit_simulacro(db, project_id: uuid.UUID, *, critical_gaps: int) -> None:
    """Inserta un evento simulacro.pre_enac.report_generated con NC reales (#42)."""
    await db.execute(sa_text(
        "INSERT INTO audit_log (id, tabla, registro_id, accion, usuario, "
        "project_id, payload_new, timestamp) VALUES "
        "(gen_random_uuid(), 'm09_audit_prep', :rid, "
        "'simulacro.pre_enac.report_generated', 'tester', :pid, :payload, now())"
    ), {
        "rid": str(project_id),
        "pid": str(project_id),
        "payload": json.dumps({
            "critical_gaps": critical_gaps,
            "high_gaps": 0,
            "total_gaps": critical_gaps,
        }),
    })


@pytest.mark.asyncio
async def test_gate7_media_flow_blocks_and_allows(db, monkeypatch):
    monkeypatch.setenv("FULKRO_SKIP_WORKFLOW_GATES", "0")
    project_id = await _create_project(db, "MEDIA")

    async with _admin_setup(db):
        # Tramo sin gate: not_started → ... → internal_audit_scheduled
        await transition_state(db, project_id, STATE_MA_PREPARATION, usuario="m")
        await transition_state(db, project_id, STATE_MA_DOCS_COLLECTED, usuario="m")
        await transition_state(
            db, project_id, STATE_MA_INTERNAL_AUDIT_SCHEDULED, usuario="m",
        )

        # #43: internal_audit_completed SIN simulacro → bloqueado
        with pytest.raises(WorkflowGateError):
            await transition_state(
                db, project_id, STATE_MA_INTERNAL_AUDIT_COMPLETED, usuario="m",
            )

        # Ejecuta simulacro con 2 NC mayores (critical)
        await _emit_simulacro(db, project_id, critical_gaps=2)

        # #43 satisfecho (simulacro existe) → internal_audit_completed OK
        r = await transition_state(
            db, project_id, STATE_MA_INTERNAL_AUDIT_COMPLETED, usuario="m",
        )
        assert r["to_state"] == STATE_MA_INTERNAL_AUDIT_COMPLETED

        # #40: enac_audit_scheduled con 2 NC mayores → bloqueado
        with pytest.raises(WorkflowGateError):
            await transition_state(
                db, project_id, STATE_MA_ENAC_AUDIT_SCHEDULED, usuario="m",
            )

        # escape-hatch admin justificado → permite continuar (trazado nc_override)
        r2 = await transition_state(
            db, project_id, STATE_MA_ENAC_AUDIT_SCHEDULED, usuario="m",
            allow_open_nc=True,
        )
        assert r2["to_state"] == STATE_MA_ENAC_AUDIT_SCHEDULED


@pytest.mark.asyncio
async def test_gate7_media_clean_simulacro_allows_enac(db, monkeypatch):
    monkeypatch.setenv("FULKRO_SKIP_WORKFLOW_GATES", "0")
    project_id = await _create_project(db, "MEDIA")

    async with _admin_setup(db):
        await transition_state(db, project_id, STATE_MA_PREPARATION, usuario="m")
        await transition_state(db, project_id, STATE_MA_DOCS_COLLECTED, usuario="m")
        await transition_state(
            db, project_id, STATE_MA_INTERNAL_AUDIT_SCHEDULED, usuario="m",
        )
        # Simulacro LIMPIO (0 NC mayores)
        await _emit_simulacro(db, project_id, critical_gaps=0)
        await transition_state(
            db, project_id, STATE_MA_INTERNAL_AUDIT_COMPLETED, usuario="m",
        )
        # #40: con 0 NC mayores → ENAC permitido sin override
        r = await transition_state(
            db, project_id, STATE_MA_ENAC_AUDIT_SCHEDULED, usuario="m",
        )
        assert r["to_state"] == STATE_MA_ENAC_AUDIT_SCHEDULED


@pytest.mark.asyncio
async def test_gate7_basica_declaration_sign_requires_simulacro(db, monkeypatch):
    monkeypatch.setenv("FULKRO_SKIP_WORKFLOW_GATES", "0")
    project_id = await _create_project(db, "BASICA")

    async with _admin_setup(db):
        await transition_state(
            db, project_id, STATE_BASICO_DECLARATION_DRAFTED, usuario="m",
        )
        # #40: firmar la Declaración BÁSICA sin simulacro → bloqueado
        with pytest.raises(WorkflowGateError):
            await transition_state(
                db, project_id, STATE_BASICO_DECLARATION_SIGNED, usuario="m",
            )
        # Simulacro limpio → firma permitida
        await _emit_simulacro(db, project_id, critical_gaps=0)
        r = await transition_state(
            db, project_id, STATE_BASICO_DECLARATION_SIGNED, usuario="m",
        )
        assert r["to_state"] == STATE_BASICO_DECLARATION_SIGNED
