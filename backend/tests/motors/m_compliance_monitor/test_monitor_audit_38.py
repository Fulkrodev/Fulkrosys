"""#38 Ola9 · el monitor de compliance se auto-traza en audit_log (dogfooding R6).

Subsistema platform-global (sin tenant) → audit_log system-level (project_id/
client_id NULL · la RLS 3-way OR de Sub-atom 5.A admite NULL+NULL).
"""
from __future__ import annotations

import pathlib
import uuid

import pytest
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

import backend.app.motors.m_compliance_monitor.api as monitor_api
from backend.app.motors.m_compliance_monitor.api import _emit_monitor_audit


@pytest.mark.asyncio
async def test_emit_monitor_audit_writes_system_level(db: AsyncSession):
    rid = uuid.uuid4()
    await _emit_monitor_audit(
        db,
        tabla="compliance_checks",
        registro_id=rid,
        accion="compliance.check.run",
        usuario="marcos@test.es",
        payload={"check": "x", "status": "green"},
    )
    await db.flush()
    row = (
        await db.execute(
            sa_text(
                "SELECT accion, project_id, client_id, usuario FROM audit_log "
                "WHERE registro_id=:rid AND accion='compliance.check.run'"
            ),
            {"rid": str(rid)},
        )
    ).first()
    assert row is not None
    assert row[0] == "compliance.check.run"
    assert row[1] is None  # system-level · sin project
    assert row[2] is None  # · sin client
    assert row[3] == "marcos@test.es"


def test_three_mutations_emit_audit():
    # #38 · run_check / resolve_alert / sync_registry invocan _emit_monitor_audit
    src = pathlib.Path(monitor_api.__file__).read_text(encoding="utf-8")
    assert src.count("_emit_monitor_audit(") >= 4  # 1 def + 3 llamadas
    assert "compliance.check.run" in src
    assert "compliance.alert.resolved" in src
    assert "compliance.registry.synced" in src
