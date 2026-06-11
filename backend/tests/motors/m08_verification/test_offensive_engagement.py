"""Infra ofensiva on-demand: provisión efímera + engagement + teardown garantizado.

mock-by-default (sin HETZNER_CLOUD_TOKEN no toca red). Verifica:
- provision_box mock + decline de wireless (físico) + teardown.
- gate FAIL-CLOSED: sin authorized_by o sin attestor_cert NO corre.
- engagement completo en mock: provisión → (sin candidatos) → teardown garantizado
  + 3 EvidenceRecords R6 (provisioned/executed/destroyed).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select, text as sa_text

from backend.app.database import set_tenant_context
from backend.app.motors.m08_verification.autopilot import offensive_provisioner as prov
from backend.app.motors.m08_verification.autopilot.offensive_engagement import (
    OffensiveAuthorizationError,
    run_offensive_engagement,
)
from backend.app.motors.m08_verification.models import EvidenceRecord, VerificationRun
from backend.tests.conftest import _admin_setup, setup_test_project


async def _set_tenant(db, project_id):
    client_id = (await db.execute(
        sa_text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)},
    )).scalar()
    await set_tenant_context(db, client_id=client_id, project_id=uuid.UUID(str(project_id)))


async def _mk_run(db, project_id):
    async with _admin_setup(db):
        run = VerificationRun(
            project_id=uuid.UUID(str(project_id)),
            category="ALTO", mode="external_handoff", status="completed",
            scope_jsonb={"targets": ["10.0.0.0/24"], "allowed_test_types": ["scan", "active_safe"]},
            run_manifest_hash="m" + uuid.uuid4().hex,
            completed_at=datetime.now(timezone.utc),
        )
        db.add(run)
        await db.flush()
    return run


@pytest.mark.asyncio
async def test_provision_mock_and_teardown():
    box = await prov.provision_box("cracking")
    assert box.mock is True
    assert box.status == "mocked"
    assert box.host
    await prov.teardown_box(box)
    assert box.status == "destroyed"
    assert box.destroyed_at is not None


@pytest.mark.asyncio
async def test_wireless_is_declined_physically():
    box = await prov.provision_box("wireless")
    assert box.status == "error"
    assert "antena" in (box.error or "").lower() or "monitor" in (box.error or "").lower()


@pytest.mark.asyncio
async def test_engagement_fail_closed_without_authorization(db):
    _, project_id = await setup_test_project(db)
    run = await _mk_run(db, project_id)
    await _set_tenant(db, project_id)

    with pytest.raises(OffensiveAuthorizationError):
        await run_offensive_engagement(
            db, run.id, "phishing", authorized_by="", attestor_cert="OSCP-1",
            tool_invocations=[],
        )
    with pytest.raises(OffensiveAuthorizationError):
        await run_offensive_engagement(
            db, run.id, "phishing", authorized_by="Marcos", attestor_cert="",
            tool_invocations=[],
        )


@pytest.mark.asyncio
async def test_engagement_mock_provisions_runs_and_tears_down(db):
    _, project_id = await setup_test_project(db)
    run = await _mk_run(db, project_id)
    await _set_tenant(db, project_id)

    summary = await run_offensive_engagement(
        db, run.id, "phishing",
        authorized_by="Marcos Mata",
        attestor_cert="OSCP-99887 (pentester independiente subcontratado)",
        independence_note="pentester externo · NO es el implantador del ENS",
        tool_invocations=[{"server": "phishing", "tool": "gophish_campaign", "args": {}}],
    )
    await db.flush()

    assert summary["box_status"] == "mocked"
    assert summary["mock"] is True
    # En mock (USE_MCP_REAL=false) no hay candidatos reales → 0 findings, sin fingir.
    assert summary["findings_persisted"] == 0

    # 3 evidencias R6 del ciclo de vida (provisión + ejecución + destrucción).
    evs = (await db.execute(
        select(EvidenceRecord.action).where(
            EvidenceRecord.run_id == run.id,
            EvidenceRecord.component == "m08:offensive.engagement",
        )
    )).scalars().all()
    assert "offensive.box_provisioned" in evs
    assert "offensive.engagement_executed" in evs
    assert "offensive.box_destroyed" in evs
