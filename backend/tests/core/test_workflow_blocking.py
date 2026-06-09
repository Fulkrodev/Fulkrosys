"""Tests workflow blocking service (ADR-036 SAN-D MB-17.5)."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.app.core.workflow_blocking_service import WorkflowBlockingService
from backend.tests.conftest import _admin_setup


async def _create_project(db, *, categoria_objetivo: str | None = None):
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, 'Test', :cif, now())"
            ),
            {"id": str(client_id), "cif": cif},
        )
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, "
                "categoria_objetivo, created_at) "
                "VALUES (:id, :cid, 'TestProj', :cat, now())"
            ),
            {
                "id": str(project_id),
                "cid": str(client_id),
                "cat": categoria_objetivo,
            },
        )
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(project_id)},
    )
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": str(client_id)},
    )
    await db.flush()
    return project_id


@pytest.mark.asyncio
async def test_basica_no_blocking_to_conformidad(db):
    """BASICA · sin features bloqueantes Conformidad (autoevaluación basta)."""
    project_id = await _create_project(db, categoria_objetivo="BASICA")
    service = WorkflowBlockingService(db)

    result = await service.check_can_transition(project_id, target_phase=9)
    assert result.can_transition is True
    assert result.blocking_issues == []
    assert result.target_phase == 9
    assert result.target_phase_label == "conformidad"


@pytest.mark.asyncio
async def test_media_blocked_without_auditor_enac(db):
    """MEDIA sin auditor ENAC → bloqueada Conformidad (stub Future:)."""
    project_id = await _create_project(db, categoria_objetivo="MEDIA")
    service = WorkflowBlockingService(db)

    result = await service.check_can_transition(project_id, target_phase=9)
    assert result.can_transition is False
    keys = {issue.feature_key for issue in result.blocking_issues}
    assert "media_auditor_enac" in keys


@pytest.mark.asyncio
async def test_alta_blocked_multiple_features(db):
    """ALTA · pentest + productos + criptografía bloquean (3 issues)."""
    project_id = await _create_project(db, categoria_objetivo="ALTA")
    service = WorkflowBlockingService(db)

    result = await service.check_can_transition(project_id, target_phase=9)
    assert result.can_transition is False
    keys = {issue.feature_key for issue in result.blocking_issues}
    assert "alta_pentest_cpstic" in keys
    assert "alta_productos_cpstic" in keys
    assert "alta_criptografia_807" in keys
    # MEDIA features también bloquean en ALTA (heredan)
    assert "media_auditor_enac" in keys


@pytest.mark.asyncio
async def test_blocking_issue_fix_url_includes_project_id(db):
    """Fix URL incluye project_id formatted en path."""
    project_id = await _create_project(db, categoria_objetivo="ALTA")
    service = WorkflowBlockingService(db)

    result = await service.check_can_transition(project_id, target_phase=9)
    pentest_issue = next(
        i for i in result.blocking_issues if i.feature_key == "alta_pentest_cpstic"
    )
    assert str(project_id) in pentest_issue.fix_url
    assert "verification?focus=pentest_cpstic" in pentest_issue.fix_url


@pytest.mark.asyncio
async def test_project_not_found_returns_blocked(db):
    """Project_id inexistente · can_transition=False con feature_key especial."""
    service = WorkflowBlockingService(db)
    result = await service.check_can_transition(
        project_id=uuid.uuid4(), target_phase=9,
    )
    assert result.can_transition is False
    assert result.blocking_issues[0].feature_key == "project_not_found"


@pytest.mark.asyncio
async def test_media_auditor_enac_completes_when_assigned(db):
    """#17 · MEDIA con auditor ENAC asignado (M28 project_role_assignments)
    → media_auditor_enac deja de bloquear (autolimpia el gate)."""
    project_id = await _create_project(db, categoria_objetivo="MEDIA")
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO project_role_assignments "
                "(id, project_id, role_code, assigned_at, is_required, "
                "is_cross_compliance, created_at, updated_at) "
                "VALUES (:id, :pid, 'auditor', now(), true, true, now(), now())"
            ),
            {"id": str(uuid.uuid4()), "pid": str(project_id)},
        )
    await db.flush()
    service = WorkflowBlockingService(db)
    result = await service.check_can_transition(project_id, target_phase=9)
    keys = {i.feature_key for i in result.blocking_issues}
    assert "media_auditor_enac" not in keys


@pytest.mark.asyncio
async def test_media_blocked_without_vuln_scan(db):
    """#16 · MEDIA sin VerificationRun completado → media_vuln_scan bloquea."""
    project_id = await _create_project(db, categoria_objetivo="MEDIA")
    service = WorkflowBlockingService(db)
    result = await service.check_can_transition(project_id, target_phase=9)
    keys = {i.feature_key for i in result.blocking_issues}
    assert "media_vuln_scan" in keys


@pytest.mark.asyncio
async def test_media_vuln_scan_completes_when_run_completed(db):
    """#16 · MEDIA con VerificationRun completado → media_vuln_scan deja de bloquear."""
    project_id = await _create_project(db, categoria_objetivo="MEDIA")
    run_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO verification_runs (id, project_id, category, "
                "mode, status, scope_jsonb, created_at) "
                "VALUES (:id, :pid, 'MEDIO', 'internal', 'completed', "
                "'{}'::jsonb, now())"
            ),
            {"id": str(run_id), "pid": str(project_id)},
        )
    await db.flush()
    service = WorkflowBlockingService(db)
    result = await service.check_can_transition(project_id, target_phase=9)
    keys = {i.feature_key for i in result.blocking_issues}
    assert "media_vuln_scan" not in keys


@pytest.mark.asyncio
async def test_alta_pentest_completes_when_external_run_completed(db):
    """ALTA · VerificationRun ALTO + external_* + completed → pentest done."""
    project_id = await _create_project(db, categoria_objetivo="ALTA")
    run_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO verification_runs (id, project_id, category, "
                "mode, status, scope_jsonb, created_at) "
                "VALUES (:id, :pid, 'ALTO', 'external_handoff', 'completed', "
                "'{}'::jsonb, now())"
            ),
            {"id": str(run_id), "pid": str(project_id)},
        )
    await db.flush()

    service = WorkflowBlockingService(db)
    result = await service.check_can_transition(project_id, target_phase=9)
    keys = {i.feature_key for i in result.blocking_issues}
    assert "alta_pentest_cpstic" not in keys
