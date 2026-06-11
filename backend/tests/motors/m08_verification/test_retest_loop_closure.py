"""Regresión: el re-test post-remediación CIERRA el bucle canónico ENS.

Lo que el auditor ENAC certifica en MEDIA (mp.s.2) es el bucle cerrado:
hallazgo → remediación → VERIFICACIÓN post-remediación DOCUMENTADA. Antes,
``run_retest`` solo tocaba la columna legacy ``status`` y dejaba ``finding_state``
en 'triaged', y no emitía evidencia R6 del acto de verificación. Estos tests
fijan que un re-test 'fixed' lleva el finding a ``closed`` y deja un
``EvidenceRecord`` append-only ('finding.remediation_verified').
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select, text as sa_text

from backend.app.database import set_tenant_context
from backend.app.motors.m08_verification.finding_state_machine import FindingState
from backend.app.motors.m08_verification.models import (
    EvidenceRecord, VerificationFinding, VerificationRun,
)
from backend.app.motors.m08_verification.remediation import retest_runner
from backend.tests.conftest import _admin_setup, setup_test_project


async def _set_tenant(db, project_id):
    client_id = (await db.execute(
        sa_text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)},
    )).scalar()
    await set_tenant_context(db, client_id=client_id, project_id=uuid.UUID(str(project_id)))


async def _mk_finding(db, project_id, *, state=FindingState.TRIAGED):
    async with _admin_setup(db):
        run = VerificationRun(
            project_id=uuid.UUID(str(project_id)),
            category="BASICO", mode="internal", status="completed",
            scope_jsonb={"targets": ["test.example.es"]},
            completed_at=datetime.now(timezone.utc),
        )
        db.add(run)
        await db.flush()
        vf = VerificationFinding(
            project_id=run.project_id, run_id=run.id,
            finding_hash=f"t_{uuid.uuid4().hex[:12]}",
            title="TLS debil", description="d", severity="high",
            affected_host="test.example.es", cve_id="CVE-2024-X",
            tool_sources=["nuclei"], raw_outputs=[{"tool": "nuclei", "excerpt": "x"}],
            confidence_score=0.95, zfp_gate1_dedup=True, zfp_gate2_fp_filter=True,
            zfp_gate3_cross_tool=1, zfp_gate4_retest="not_applicable",
            zfp_gate5_classification="confirmed",
            ens_measures=[{"measure": "op.exp.5", "title": "t", "method": "rule"}],
            ens_primary_measure="op.exp.5", remediation_summary="patch",
            status="open", finding_state=state,
        )
        db.add(vf)
        await db.flush()
    return run, vf


@pytest.mark.asyncio
async def test_retest_fixed_closes_canonical_loop_and_emits_r6_evidence(db, monkeypatch):
    _, project_id = await setup_test_project(db)
    _, vf = await _mk_finding(db, project_id)
    await _set_tenant(db, project_id)

    async def _fake_fixed(_finding):
        return ("fixed", "nuclei -t cves/CVE-2024-X.yaml -u test.example.es", "0 matches")
    monkeypatch.setitem(retest_runner._DISPATCHERS, "cve", _fake_fixed)

    retest = await retest_runner.run_retest(
        db, vf, triggered_by="client_portal", retest_type="cve",
    )
    await db.flush()

    assert retest.result == "fixed"
    assert vf.status == "remediated"
    assert vf.remediated_verified is True
    assert vf.remediated_retest_run_id == retest.id
    # Pista canónica: bucle cerrado de verdad.
    assert vf.finding_state == FindingState.CLOSED

    ev = (await db.execute(
        select(EvidenceRecord).where(
            EvidenceRecord.finding_id == vf.id,
            EvidenceRecord.action == "finding.remediation_verified",
        )
    )).scalars().all()
    assert len(ev) == 1, "falta la evidencia R6 de la verificacion post-remediacion"
    assert ev[0].component == "m08:remediation.retest_runner"
    assert ev[0].ens_relevance == "op.exp.5"


@pytest.mark.asyncio
async def test_retest_still_present_marks_in_remediation(db, monkeypatch):
    _, project_id = await setup_test_project(db)
    _, vf = await _mk_finding(db, project_id)
    await _set_tenant(db, project_id)

    async def _fake_still(_finding):
        return ("still_present", "nuclei -t cves/CVE-2024-X.yaml", "1 match")
    monkeypatch.setitem(retest_runner._DISPATCHERS, "cve", _fake_still)

    await retest_runner.run_retest(db, vf, triggered_by="client_portal", retest_type="cve")
    await db.flush()

    assert vf.status == "open"  # legacy no se marca remediado
    assert vf.finding_state == FindingState.IN_REMEDIATION
    ev = (await db.execute(
        select(EvidenceRecord).where(
            EvidenceRecord.finding_id == vf.id,
            EvidenceRecord.action == "finding.retest_still_present",
        )
    )).scalars().all()
    assert len(ev) == 1
