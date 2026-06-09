"""F1 + F8 (FRENTE F) · orquestador fase_runner end-to-end con seeds golden.

Sin binarios · sin Hetzner · corre en CI (USE_MCP_REAL=false). Prueba el
end-to-end del orquestador F1 (#38/#39): candidatos golden → ZFP 5 gates →
VerificationFinding persistido + counters + estado. PE-3: la ejecución REAL de
binarios es validación de deploy · aquí se valida CÓDIGO + ORQUESTACIÓN.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text as sa_text

from backend.app.motors.m08_verification.fase_runner import run_fases
from backend.app.motors.m08_verification.tools.base import FindingCandidate
from backend.tests.conftest import setup_test_project

pytestmark = pytest.mark.asyncio


GOLDEN: list[FindingCandidate] = [
    {
        "title": "Apache Log4j2 RCE (Log4Shell)",
        "description": "JNDI lookup remote code execution",
        "severity": "critical",
        "cve_id": "CVE-2021-44228",
        "cvss_score": 10.0,
        "affected_host": "10.0.0.5",
        "affected_port": 8080,
        "raw_output_excerpt": "CVE-2021-44228 detected via ${jndi:ldap...}",
        "tool": "nuclei",
    },
    {
        "title": "TLS 1.0 habilitado",
        "description": "Protocolo TLS obsoleto ofrecido por el servidor",
        "severity": "medium",
        "affected_host": "10.0.0.5",
        "affected_port": 443,
        "raw_output_excerpt": "TLSv1.0 offered",
        "tool": "testssl",
    },
]


async def _create_run(db, project_id: uuid.UUID) -> uuid.UUID:
    run_id = uuid.uuid4()
    await db.execute(sa_text(
        "INSERT INTO verification_runs (id, project_id, category, mode, status, "
        "scope_jsonb, created_at, updated_at) VALUES (:id, :pid, 'MEDIO', "
        "'internal', 'pending', '{}'::jsonb, now(), now())"
    ), {"id": str(run_id), "pid": str(project_id)})
    await db.flush()
    return run_id


async def test_fase_runner_seeds_flow_to_persisted_findings(db):
    _, project_id = await setup_test_project(db)
    run_id = await _create_run(db, uuid.UUID(project_id))

    async def provider(run):
        return list(GOLDEN)

    async def retest(_zf):
        return "confirmed"  # fuerza confirmación determinista (gate4)

    result = await run_fases(
        db, run_id, candidate_provider=provider, retest_callback=retest,
    )
    assert result["status"] == "completed", result
    assert result["candidates"] == 2
    assert result["findings_persisted"] == 2
    # gate5 confirma el crítico con CVE+retest; el medium sin CVE queda
    # probable/needs_review (clasificación por confianza, no solo retest).
    assert result["confirmed"] >= 1

    rows = (await db.execute(sa_text(
        "SELECT severity, status, cve_id, zfp_gate4_retest, "
        "zfp_gate5_classification, finding_hash "
        "FROM verification_findings WHERE run_id = :rid"
    ), {"rid": str(run_id)})).mappings().all()
    assert len(rows) == 2
    assert {r["severity"] for r in rows} == {"critical", "medium"}
    # status válido del CHECK (open|needs_review|...)
    assert all(r["status"] in {"open", "needs_review"} for r in rows)
    log4 = [r for r in rows if r["cve_id"] == "CVE-2021-44228"][0]
    assert log4["zfp_gate4_retest"] == "confirmed"
    assert log4["zfp_gate5_classification"] == "confirmed"

    # counters agregados en el run
    run_row = (await db.execute(sa_text(
        "SELECT status, total_findings, confirmed_findings, critical_count, "
        "medium_count, completed_at FROM verification_runs WHERE id = :id"
    ), {"id": str(run_id)})).mappings().first()
    assert run_row["status"] == "completed"
    assert run_row["total_findings"] == 2
    assert run_row["confirmed_findings"] >= 1
    assert run_row["critical_count"] == 1
    assert run_row["medium_count"] == 1
    assert run_row["completed_at"] is not None


async def test_fase_runner_empty_scan_completes_zero(db):
    """USE_MCP_REAL=false · scan simulado vacío → completed con 0 findings."""
    _, project_id = await setup_test_project(db)
    run_id = await _create_run(db, uuid.UUID(project_id))
    result = await run_fases(db, run_id)  # default provider → [] (sim)
    assert result["status"] == "completed"
    assert result["findings_persisted"] == 0


async def test_fase_runner_kill_switch_aborts(db):
    """Kill-switch: cancel_requested_at != NULL → run abortado a 'cancelled'."""
    _, project_id = await setup_test_project(db)
    run_id = await _create_run(db, uuid.UUID(project_id))
    await db.execute(sa_text(
        "UPDATE verification_runs SET cancel_requested_at = now() WHERE id = :id"
    ), {"id": str(run_id)})
    await db.flush()

    async def provider(run):
        return list(GOLDEN)

    result = await run_fases(db, run_id, candidate_provider=provider)
    assert result["status"] == "cancelled"
    # No se persistieron findings (abortó antes del scan)
    n = (await db.execute(sa_text(
        "SELECT count(*) FROM verification_findings WHERE run_id = :rid"
    ), {"rid": str(run_id)})).scalar()
    assert n == 0
