"""Tests · Diagnostic Gap Engine idempotent UPSERT + auto-resolve.

Verifica:
- 2nd run sin cambios resource → gaps_updated > 0 · gaps_created == 0
- Si finding deja de emitir (e.g. user añade MFA · re-sync) → gap_resolved automático
- Documental gap (org.1) siempre emite si no hay evidence link
- no_cloud_data=True cuando project sin resources cloud
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.app.motors.m_cloud_connectors import (
    CloudConnectorProvider,
    CloudConnectorService,
    DiagnosticGapEngine,
)
from backend.tests.conftest import setup_test_project


@pytest.mark.asyncio
async def test_no_cloud_data_flag_when_zero_resources(db):
    """Project sin cloud resources · flag no_cloud_data=True + documental gaps."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)

    engine = DiagnosticGapEngine(db)
    report = await engine.run_diagnosis(project_id=pid, category="BASICA")

    assert report.no_cloud_data is True
    # org.1 documental emite incluso sin cloud data
    assert "org.1" in report.gap_codes
    # op.exp.1 documental también (sin inventario detectado)
    assert "op.exp.1" in report.gap_codes


@pytest.mark.asyncio
async def test_run_diagnosis_no_category_returns_empty_report(db):
    """Project sin categoría asignada · 0 reglas evaluadas."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)

    engine = DiagnosticGapEngine(db)
    # No pasamos category override · projects.categoria_objetivo es NULL
    report = await engine.run_diagnosis(project_id=pid)

    assert report.rules_evaluated == 0
    assert report.findings_emitted == 0


async def _seed_unencrypted_bucket(
    db, *, project_id: uuid.UUID, encrypted: bool,
) -> uuid.UUID:
    """Inserta connector + 1 bucket con cifrado en estado dado."""
    svc = CloudConnectorService(db)
    connector = await svc.link_or_create_connector(
        project_id=project_id, provider=CloudConnectorProvider.AWS,
    )
    rid = uuid.uuid4()
    await db.execute(
        text(
            "INSERT INTO cloud_resources (id, project_id, connector_id, "
            "resource_type, resource_external_id, resource_name, attributes) "
            "VALUES (:id, :pid, :cid, 'asset.bucket', 'b1', 'main-bucket', "
            "CAST(:attrs AS JSONB))"
        ),
        {
            "id": str(rid),
            "pid": str(project_id),
            "cid": str(connector.id),
            "attrs": '{"encrypted_at_rest": ' + ("true" if encrypted else "false") + '}',
        },
    )
    await db.flush()
    return rid


@pytest.mark.asyncio
async def test_idempotent_rerun_updates_not_creates(db):
    """2nd run idéntico · gaps_updated > 0 · gaps_created == 0."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    await _seed_unencrypted_bucket(db, project_id=pid, encrypted=False)

    engine = DiagnosticGapEngine(db)
    r1 = await engine.run_diagnosis(project_id=pid, category="BASICA")
    r2 = await engine.run_diagnosis(project_id=pid, category="BASICA")

    assert r1.gaps_created >= 1
    assert "mp.info.3" in r1.gap_codes

    # Segunda iteración: actualiza · NO recrea
    assert r2.gaps_created == 0
    assert r2.gaps_updated >= 1


@pytest.mark.asyncio
async def test_auto_resolve_when_finding_disappears(db):
    """Cliente arregla MFA / cifrado · re-sync · re-diagnose auto-resuelve gap."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    bucket_id = await _seed_unencrypted_bucket(
        db, project_id=pid, encrypted=False,
    )

    engine = DiagnosticGapEngine(db)
    r1 = await engine.run_diagnosis(project_id=pid, category="BASICA")
    assert "mp.info.3" in r1.gap_codes

    # Cliente arregla · cifrado activado · re-sync mismo bucket
    await db.execute(
        text(
            "UPDATE cloud_resources SET attributes = "
            "CAST('{\"encrypted_at_rest\": true}' AS JSONB) WHERE id = :id"
        ),
        {"id": str(bucket_id)},
    )
    await db.flush()

    r2 = await engine.run_diagnosis(project_id=pid, category="BASICA")
    # mp.info.3 ya NO emite finding
    assert "mp.info.3" not in r2.gap_codes
    # Y debe haber 1 gap auto-resuelto
    assert r2.gaps_resolved >= 1


@pytest.mark.asyncio
async def test_documental_gap_persists_until_explicit_resolve(db):
    """org.1 documental sigue abierto incluso re-run · solo se cierra cuando
    admin marca resolved explícito con evidence_link."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)

    engine = DiagnosticGapEngine(db)
    r1 = await engine.run_diagnosis(project_id=pid, category="BASICA")
    r2 = await engine.run_diagnosis(project_id=pid, category="BASICA")

    assert "org.1" in r1.gap_codes
    assert "org.1" in r2.gap_codes  # sigue emitiendo · no auto-resuelve
