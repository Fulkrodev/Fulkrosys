"""Tests AuditDryRunService orchestrator M10+A11 (ADR-037 SAN-D MB-15.1).

Mocks M10 + A11 para tests rápidos sin LLM real.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select, text

from backend.app.agents.models.dry_run import AuditDryRunResult
from backend.app.agents.services.audit_dry_run_service import (
    AuditDryRunService,
)
from backend.app.models.audit_sim import AuditSimulationRun
from backend.tests.conftest import _admin_setup


async def _create_project(
    db,
    *,
    categoria_objetivo: str = "MEDIA",
    archetype: str | None = None,
):
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, sector, "
                "numero_empleados, created_at) "
                "VALUES (:id, 'Test', :cif, :sec, 100, now())"
            ),
            {"id": str(client_id), "cif": cif, "sec": "fintech"},
        )
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, "
                "categoria_objetivo, archetype, created_at) "
                "VALUES (:id, :cid, 'TestProj', :cat, :arch, now())"
            ),
            {
                "id": str(project_id),
                "cid": str(client_id),
                "cat": categoria_objetivo,
                "arch": archetype,
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


def _mock_m10_run(project_id, categoria="MEDIA", score=75):
    """Stub AuditSimulationRun for mocked M10 trigger."""
    run = AuditSimulationRun(
        id=uuid.uuid4(),
        project_id=project_id,
        categoria=categoria,
        estado="completed",
        total_measures=58,
        measures_evaluated=58,
        conformes=40,
        no_conformes_mayores=3,
        no_conformes_menores=10,
        observaciones=4,
        no_aplica=1,
        score_global=score,
        nivel_madurez_global="L3",
        scores_por_familia={
            "_total_L0": 5,
            "_total_L1": 8,
            "_total_L2": 10,
            "_total_L3": 25,
            "_total_L4": 8,
            "_total_L5": 2,
            "org": {"score": 80},
        },
        contradicciones_count=0,
        recomendacion="requiere_remediacion_menor",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    return run


@pytest.mark.asyncio
async def test_execute_dry_run_persists_result(db):
    """execute_dry_run · M10 + A11 mocked · row persistido con métricas."""
    project_id = await _create_project(db, categoria_objetivo="MEDIA")
    service = AuditDryRunService(db)

    mock_m10 = _mock_m10_run(project_id, "MEDIA", score=75)

    async def _fake_run_simulation(db_arg, *, project_id, categoria):
        db_arg.add(mock_m10)
        await db_arg.flush()
        return mock_m10

    a11_payload = {
        "veredicto": "favorable_con_remediacion",
        "probabilidad_certificacion_primera": 0.7,
        "narrativa_md": "## Conclusión\n...",
        "pac": [{"fase": 1, "nc_origen": "org.1.1"}],
        "preguntas_contextuales": [{"pregunta": "¿DPO?", "criterio_l5": "..."}],
    }

    with patch.object(
        service._m10, "run_simulation",
        side_effect=_fake_run_simulation,
    ), patch.object(
        service._a11, "generate_supplementary_audit",
        AsyncMock(return_value=a11_payload),
    ):
        result = await service.execute_dry_run(project_id=project_id)

    assert result.project_id == project_id
    assert result.category_at_execution == "MEDIA"
    assert result.total_questions == 0  # no findings inserted in mock
    assert result.overall_readiness_score == 75
    assert result.gaps_detected == 0  # findings vacíos en mock
    assert result.a11_payload is not None
    assert result.a11_payload["veredicto"] == "favorable_con_remediacion"

    # Verify row persisted
    rows = (
        await db.execute(
            select(AuditDryRunResult)
            .where(AuditDryRunResult.project_id == project_id)
        )
    ).scalars().all()
    assert len(list(rows)) == 1


@pytest.mark.asyncio
async def test_execute_dry_run_a11_failure_persists_with_fallback(db):
    """A11 LLM falla · M10 score se persiste · a11_payload contiene error marker."""
    project_id = await _create_project(db, categoria_objetivo="ALTA")
    service = AuditDryRunService(db)

    mock_m10 = _mock_m10_run(project_id, "ALTA", score=60)

    async def _fake_run_simulation(db_arg, *, project_id, categoria):
        db_arg.add(mock_m10)
        await db_arg.flush()
        return mock_m10

    with patch.object(
        service._m10, "run_simulation",
        side_effect=_fake_run_simulation,
    ), patch.object(
        service._a11, "generate_supplementary_audit",
        AsyncMock(side_effect=RuntimeError("LLM rate-limited")),
    ):
        result = await service.execute_dry_run(project_id=project_id)

    assert result.overall_readiness_score == 60
    assert result.a11_payload is not None
    assert "error" in result.a11_payload
    assert result.a11_payload.get("fallback") is True


@pytest.mark.asyncio
async def test_execute_dry_run_project_not_found_raises(db):
    """Project_id inexistente · ValueError."""
    service = AuditDryRunService(db)
    with pytest.raises(ValueError):
        await service.execute_dry_run(project_id=uuid.uuid4())


@pytest.mark.asyncio
async def test_get_summary_empty_returns_defaults(db):
    """Sin ejecuciones previas · summary defaults."""
    project_id = await _create_project(db, categoria_objetivo="BASICA")
    service = AuditDryRunService(db)
    summary = await service.get_summary(project_id)
    assert summary.last_executed_at is None
    assert summary.overall_readiness_score == 0
    assert summary.history == []


@pytest.mark.asyncio
async def test_get_summary_returns_latest_5(db):
    """Summary devuelve last 5 ejecuciones ordenadas desc."""
    project_id = await _create_project(db, categoria_objetivo="MEDIA")

    # Crear 6 results (límite 5)
    for i in range(6):
        async with _admin_setup(db):
            row = AuditDryRunResult(
                project_id=project_id,
                executed_at=datetime.now(timezone.utc).replace(microsecond=i),
                category_at_execution="MEDIA",
                total_questions=58,
                questions_with_evidence=40,
                overall_readiness_score=70 + i,
                gaps_detected=10,
                critical_gaps=2,
                m10_payload={},
                a11_payload={},
            )
            db.add(row)
        await db.flush()

    service = AuditDryRunService(db)
    summary = await service.get_summary(project_id)

    assert summary.last_executed_at is not None
    assert len(summary.history) == 5  # cap a 5


@pytest.mark.asyncio
async def test_get_result_returns_detail(db):
    """get_result devuelve detalle con findings."""
    project_id = await _create_project(db, categoria_objetivo="MEDIA")

    m10_payload = {
        "run_id": str(uuid.uuid4()),
        "score_global": 80,
        "nivel_madurez_global": "L4",
        "conformes": 50,
        "no_conformes_mayores": 1,
        "no_conformes_menores": 5,
        "observaciones": 2,
        "no_aplica": 0,
        "contradicciones_count": 0,
        "findings": [
            {
                "measure_code": "org.1.1",
                "measure_name": "Política seguridad",
                "evaluacion": "conforme",
                "nivel_madurez": "L4",
                "contradiccion_detectada": False,
            }
        ],
    }

    async with _admin_setup(db):
        row = AuditDryRunResult(
            project_id=project_id,
            executed_at=datetime.now(timezone.utc),
            category_at_execution="MEDIA",
            total_questions=58,
            questions_with_evidence=50,
            overall_readiness_score=80,
            gaps_detected=6,
            critical_gaps=1,
            m10_payload=m10_payload,
            a11_payload={"veredicto": "favorable"},
        )
        db.add(row)
    await db.flush()

    service = AuditDryRunService(db)
    detail = await service.get_result(project_id, row.id)

    assert detail is not None
    assert detail.overall_readiness_score == 80
    assert detail.m10_summary is not None
    assert detail.m10_summary.score_global == 80
    assert len(detail.m10_summary.findings) == 1
    assert detail.m10_summary.findings[0].measure_code == "org.1.1"
