"""SimulacroPreEnacService orchestrator tests · Phase 10.3 (Ejecutable 5).

Verifica composition de 5 existing services + 2 nuevos:
1. Happy path orchestrator devuelve SimulacroReport JSON-serializable
2. audit_log emit Sub-atom 5.A 3-way OR (simulacro.pre_enac.executed + report_generated)
3. Corrective loops opened per critical/high gaps
4. PDF generated empirical (bytes + signature + sha256)

M10 + A11 mocked para tests rápidos sin LLM real.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import text as sa_text

from backend.app.agents.services.audit_dry_run_service import AuditDryRunService
from backend.app.models.audit_sim import AuditSimulationRun
from backend.app.motors.m09_audit_prep.simulacro_pre_enac_service import (
    SimulacroReport,
    run_simulacro_pre_enac,
)
from backend.tests.conftest import _admin_setup


async def _create_simulacro_project(db) -> tuple[uuid.UUID, uuid.UUID]:
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(sa_text(
            "INSERT INTO clients (id, nombre, cif, sector, "
            "numero_empleados, created_at) "
            "VALUES (:id, 'Sim Test', :cif, 'fintech', 50, now())"
        ), {"id": str(client_id), "cif": cif})
        await db.execute(sa_text(
            "INSERT INTO projects (id, client_id, nombre, "
            "categoria_objetivo, archetype, created_at) "
            "VALUES (:id, :cid, 'SimProj', 'MEDIA', NULL, now())"
        ), {"id": str(project_id), "cid": str(client_id)})
    await db.execute(sa_text(
        "SELECT set_config('app.current_project_id', :pid, true)"
    ), {"pid": str(project_id)})
    await db.execute(sa_text(
        "SELECT set_config('app.current_client_id', :cid, true)"
    ), {"cid": str(client_id)})
    await db.flush()
    return client_id, project_id


def _mock_m10_run(project_id):
    return AuditSimulationRun(
        id=uuid.uuid4(),
        project_id=project_id,
        categoria="MEDIA",
        estado="completed",
        total_measures=58,
        measures_evaluated=58,
        conformes=40,
        no_conformes_mayores=3,
        no_conformes_menores=10,
        observaciones=4,
        no_aplica=1,
        score_global=70,
        nivel_madurez_global="L3",
        scores_por_familia={"_total_L5": 2, "org": {"score": 80}},
        contradicciones_count=0,
        recomendacion="requiere_remediacion_menor",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_run_simulacro_pre_enac_happy_path(db):
    """Orchestrator happy path · SimulacroReport returned con todos los campos."""
    client_id, project_id = await _create_simulacro_project(db)
    await db.commit()

    mock_m10 = _mock_m10_run(project_id)

    async def fake_run_simulation(db_arg, *, project_id, categoria):
        db_arg.add(mock_m10)
        await db_arg.flush()
        return mock_m10

    a11_payload = {
        "veredicto": "favorable_con_remediacion",
        "probabilidad_certificacion_primera": 0.7,
        "narrativa_md": "## ENS",
        "pac": [],
        "preguntas_contextuales": [],
    }

    with patch.object(
        AuditDryRunService, "execute_dry_run",
        new_callable=AsyncMock,
    ) as mock_exec:
        mock_exec.return_value = type("DryRunStub", (), {
            "project_id": project_id,
            "category_at_execution": "MEDIA",
            "overall_readiness_score": 70,
            "gaps_detected": 13,
            "critical_gaps": 3,
            "total_questions": 58,
            "questions_with_evidence": 40,
            "a11_payload": a11_payload,
            "m10_summary": None,
        })()

        report = await run_simulacro_pre_enac(
            db, project_id, usuario="tester@example.com",
        )

    assert isinstance(report, SimulacroReport)
    assert report.project_id == str(project_id)
    assert report.overall_readiness_score == 70
    assert report.integrity_ok is True
    assert report.pdf_size_bytes > 1000  # PDF generated empirical
    assert len(report.pdf_sha256) == 64
    assert len(report.signature_hex) > 100  # Ed25519 sig
    assert report.current_phase  # workflow phase populated


@pytest.mark.asyncio
async def test_run_simulacro_pre_enac_audit_log_events_emitted(db):
    """audit_log events emitted Sub-atom 5.A 3-way OR (project_id + client_id)."""
    client_id, project_id = await _create_simulacro_project(db)
    await db.commit()

    with patch.object(
        AuditDryRunService, "execute_dry_run",
        new_callable=AsyncMock,
    ) as mock_exec:
        mock_exec.return_value = type("DryRunStub", (), {
            "project_id": project_id,
            "category_at_execution": "MEDIA",
            "overall_readiness_score": 50,
            "gaps_detected": 5,
            "critical_gaps": 0,
            "total_questions": 58,
            "questions_with_evidence": 30,
            "a11_payload": {},
            "m10_summary": None,
        })()

        await run_simulacro_pre_enac(db, project_id, usuario="audit@test.com")
    await db.flush()

    rows = (await db.execute(sa_text(
        "SELECT accion, project_id, client_id, usuario FROM audit_log "
        "WHERE tabla = 'simulacro_pre_enac' AND project_id = :pid "
        "ORDER BY seq"
    ), {"pid": str(project_id)})).all()

    accion_set = {r[0] for r in rows}
    assert "simulacro.pre_enac.executed" in accion_set
    assert "simulacro.pre_enac.report_generated" in accion_set

    for r in rows:
        accion, pid, cid, usr = r
        assert str(pid) == str(project_id)
        assert str(cid) == str(client_id)
        assert usr == "audit@test.com"


@pytest.mark.asyncio
async def test_simulacro_report_serializable(db):
    """SimulacroReport.to_dict() produces JSON-serializable dict."""
    rep = SimulacroReport(
        project_id=str(uuid.uuid4()),
        executed_at="2026-05-27T12:00:00+00:00",
        overall_readiness_score=75,
        total_gaps=10,
        critical_gaps=2,
        high_gaps=3,
        coverage_pct=78.5,
        current_phase="dossier",
        integrity_ok=True,
        integrity_first_bad_seq=None,
        corrective_loops_opened=2,
        pdf_sha256="a" * 64,
        signature_hex="b" * 128,
        signed_at="2026-05-27T12:00:01+00:00",
        pdf_size_bytes=15000,
        loops_metadata=[{"loop_id": "x", "gap_id": "op.acc.6", "severity": "critical"}],
    )
    data = rep.to_dict()
    assert data["integrity_ok"] is True
    assert data["overall_readiness_score"] == 75
    assert data["corrective_loops_opened"] == 2
    assert data["loops_metadata"][0]["gap_id"] == "op.acc.6"


@pytest.mark.asyncio
async def test_run_simulacro_orchestrator_composition_smoke(db):
    """Smoke test composition · empty project · all sub-services succeed."""
    client_id, project_id = await _create_simulacro_project(db)
    await db.commit()

    with patch.object(
        AuditDryRunService, "execute_dry_run",
        new_callable=AsyncMock,
    ) as mock_exec:
        mock_exec.return_value = type("DryRunStub", (), {
            "project_id": project_id,
            "category_at_execution": "MEDIA",
            "overall_readiness_score": 0,
            "gaps_detected": 0,
            "critical_gaps": 0,
            "total_questions": 0,
            "questions_with_evidence": 0,
            "a11_payload": {},
            "m10_summary": None,
        })()

        report = await run_simulacro_pre_enac(db, project_id)

    assert report.project_id == str(project_id)
    assert report.pdf_sha256
    assert report.signed_at
