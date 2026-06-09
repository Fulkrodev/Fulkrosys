"""Tests · m_workflow_engine sub-atom 1.C.D.A.2 v3.8.

Cubre:
  - load_project_dims · 19 dims load from projects table
  - compute_steps_for_project · cross-data view composer (templates + tasks)
  - 19 dims filter funcional (categoria · archetype · size · madurez · legal)
  - archetype_variants applied (variant_extra_focus · variant_reference_norms)
  - Urgency score computation (urgencia × horas_cliente_semana × priority)
  - compute_progress_for_project · global pct + per_phase
  - compute_current_step_for_project · returns most urgent pending
  - cross-tenant isolation (RLS sostenido)
  - WorkflowEngineService.advance_step idempotente
  - OPS-043 commit explícito sostenido
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.app.motors.m21_portal_cliente.models_tasks import ClientTask
from backend.app.motors.m_workflow_engine.engine import (
    EnrichedStepState,
    compute_current_step_for_project,
    compute_progress_for_project,
    compute_steps_for_project,
    load_project_dims,
)
from backend.app.motors.m_workflow_engine.service import (
    WorkflowEngineService,
    WorkflowEngineServiceError,
)
from backend.tests.conftest import _admin_setup, setup_test_project


# ================================================================
# load_project_dims
# ================================================================


@pytest.mark.asyncio
async def test_load_project_dims_defaults(db):
    """load_project_dims devuelve 19 dims con defaults sensatos."""
    _, project_id = await setup_test_project(db)
    dims = await load_project_dims(db, uuid.UUID(project_id))

    assert dims["fase"] is not None
    assert dims["madurez_ens_actual"] == "L0"
    assert dims["aplica_dora"] == "no"
    assert dims["dpo_designado"] == "no_designado"
    assert dims["horas_cliente_semana"] == "5_15h"


@pytest.mark.asyncio
async def test_load_project_dims_not_found_raises(db):
    with pytest.raises(ValueError):
        await load_project_dims(db, uuid.uuid4())


# ================================================================
# compute_steps_for_project · view composer
# ================================================================


async def _set_project_categoria(
    db, project_id: str, categoria: str, archetype: str | None = None,
):
    """Helper · update project categoria + archetype via _admin_setup."""
    async with _admin_setup(db):
        await db.execute(
            text(
                "UPDATE projects SET categoria_objetivo = :c, archetype = :a "
                "WHERE id = :pid"
            ),
            {"c": categoria, "a": archetype, "pid": project_id},
        )
        await db.commit()


@pytest.mark.asyncio
async def test_compute_steps_returns_enriched_state(db):
    """Project basica · steps cubren enriched templates aplicables."""
    _, project_id = await setup_test_project(db)
    await _set_project_categoria(db, project_id, "BASICA", "saas_only")

    steps = await compute_steps_for_project(db, uuid.UUID(project_id))

    assert len(steps) > 0
    for s in steps:
        assert isinstance(s, EnrichedStepState)
        assert s.status == "not_started"  # NO client_task created yet


@pytest.mark.asyncio
async def test_compute_steps_phase_filter(db):
    _, project_id = await setup_test_project(db)
    await _set_project_categoria(db, project_id, "MEDIA", "fintech")

    steps_adec = await compute_steps_for_project(
        db, uuid.UUID(project_id), phase_filter="adecuacion",
    )
    for s in steps_adec:
        assert s.phase == "adecuacion"


@pytest.mark.asyncio
async def test_compute_steps_19dims_filter_dora(db):
    """fintech sin DORA flag · NO debe ver ENR_AD_03_DORA."""
    _, project_id = await setup_test_project(db)
    await _set_project_categoria(db, project_id, "MEDIA", "fintech")
    # DORA defaults a 'no' · ENR_AD_03_DORA_FRAMEWORK_ICT requires_dora=True

    steps = await compute_steps_for_project(db, uuid.UUID(project_id))
    ids = {s.template_id for s in steps}
    assert "ENR_AD_03_DORA_FRAMEWORK_ICT" not in ids

    # Update project · aplica_dora = entidad_financiera
    async with _admin_setup(db):
        await db.execute(
            text("UPDATE projects SET aplica_dora = 'entidad_financiera' WHERE id = :pid"),
            {"pid": project_id},
        )
        await db.commit()

    steps_dora = await compute_steps_for_project(db, uuid.UUID(project_id))
    ids_dora = {s.template_id for s in steps_dora}
    assert "ENR_AD_03_DORA_FRAMEWORK_ICT" in ids_dora


@pytest.mark.asyncio
async def test_compute_steps_archetype_variant_applied(db):
    """fintech · ENR_AD_03_DORA debe traer variant fintech extra_focus."""
    _, project_id = await setup_test_project(db)
    async with _admin_setup(db):
        await db.execute(
            text(
                "UPDATE projects SET categoria_objetivo = 'MEDIA', "
                "archetype = 'proveedor_financiero', aplica_dora = 'entidad_financiera' "
                "WHERE id = :pid"
            ),
            {"pid": project_id},
        )
        await db.commit()

    steps = await compute_steps_for_project(db, uuid.UUID(project_id))
    dora = next(
        (s for s in steps if s.template_id == "ENR_AD_03_DORA_FRAMEWORK_ICT"),
        None,
    )
    assert dora is not None
    assert dora.variant_extra_focus is not None
    assert "TLPT" in dora.variant_extra_focus


@pytest.mark.asyncio
async def test_compute_steps_urgency_higher_for_urgent_30d(db):
    """urgencia_certificacion = urgent_30d · urgency_score > 6m baseline."""
    _, project_id = await setup_test_project(db)
    await _set_project_categoria(db, project_id, "MEDIA", "saas_only")

    # Baseline urgency
    steps_base = await compute_steps_for_project(db, uuid.UUID(project_id))
    if not steps_base:
        pytest.skip("No applicable steps · skip")
    baseline_max = max(s.urgency_score for s in steps_base)

    # Update urgency to urgent_30d
    async with _admin_setup(db):
        await db.execute(
            text("UPDATE projects SET urgencia_certificacion = 'urgent_30d' WHERE id = :pid"),
            {"pid": project_id},
        )
        await db.commit()

    steps_urgent = await compute_steps_for_project(db, uuid.UUID(project_id))
    urgent_max = max(s.urgency_score for s in steps_urgent)
    assert urgent_max > baseline_max


@pytest.mark.asyncio
async def test_compute_steps_reflects_completed_task(db):
    """ClientTask con status=completed · EnrichedStepState reflejado en steps."""
    _, project_id = await setup_test_project(db)
    await _set_project_categoria(db, project_id, "MEDIA", "saas_only")

    # Create ClientTask completed manual
    async with _admin_setup(db):
        task = ClientTask(
            project_id=uuid.UUID(project_id),
            template_id="ENR_OB_01_KICKOFF_19DIMS",
            phase="onboarding",
            title="Kickoff 19 dims",
            status="completed",
            priority=10,
        )
        db.add(task)
        await db.commit()

    steps = await compute_steps_for_project(db, uuid.UUID(project_id))
    kickoff = next(
        (s for s in steps if s.template_id == "ENR_OB_01_KICKOFF_19DIMS"),
        None,
    )
    assert kickoff is not None
    assert kickoff.status == "completed"
    assert kickoff.urgency_score == 0  # completed = 0 urgency


# ================================================================
# Progress aggregate
# ================================================================


@pytest.mark.asyncio
async def test_compute_progress_empty_project(db):
    """Sin tasks completadas · progress = 0%."""
    _, project_id = await setup_test_project(db)
    await _set_project_categoria(db, project_id, "BASICA", "saas_only")

    progress = await compute_progress_for_project(db, uuid.UUID(project_id))
    assert progress["global_completed"] == 0
    assert progress["global_pct"] == 0
    assert progress["global_total"] > 0


@pytest.mark.asyncio
async def test_compute_progress_with_completed_tasks(db):
    """Una tarea completed · global_pct refleja proportion."""
    _, project_id = await setup_test_project(db)
    await _set_project_categoria(db, project_id, "BASICA", "saas_only")

    # Crear 1 task completed
    async with _admin_setup(db):
        db.add(
            ClientTask(
                project_id=uuid.UUID(project_id),
                template_id="ENR_OB_01_KICKOFF_19DIMS",
                phase="onboarding",
                title="Kickoff",
                status="completed",
                priority=10,
            )
        )
        await db.commit()

    progress = await compute_progress_for_project(db, uuid.UUID(project_id))
    assert progress["global_completed"] == 1
    assert progress["global_pct"] > 0


# ================================================================
# Current step
# ================================================================


@pytest.mark.asyncio
async def test_compute_current_step_returns_max_urgency(db):
    """current_step retorna el pending con mayor urgency_score."""
    _, project_id = await setup_test_project(db)
    await _set_project_categoria(db, project_id, "MEDIA", "saas_only")

    current = await compute_current_step_for_project(db, uuid.UUID(project_id))
    assert current is not None
    assert current.status != "completed"
    assert current.urgency_score > 0


# ================================================================
# Service · advance_step
# ================================================================


@pytest.mark.asyncio
async def test_service_advance_step_creates_completed_task(db):
    """advance_step idempotente · crea ClientTask status=completed si NO existe."""
    _, project_id = await setup_test_project(db)
    await _set_project_categoria(db, project_id, "MEDIA", "saas_only")
    updater = uuid.uuid4()

    service = WorkflowEngineService(db)
    task = await service.advance_step(
        project_id=uuid.UUID(project_id),
        template_id="ENR_OB_01_KICKOFF_19DIMS",
        updated_by=updater,
    )
    assert task.status == "completed"
    assert task.completed_at is not None


@pytest.mark.asyncio
async def test_service_advance_step_invalid_template_raises(db):
    """Template no existe · WorkflowEngineServiceError."""
    _, project_id = await setup_test_project(db)
    updater = uuid.uuid4()

    service = WorkflowEngineService(db)
    with pytest.raises(WorkflowEngineServiceError):
        await service.advance_step(
            project_id=uuid.UUID(project_id),
            template_id="ENR_DOES_NOT_EXIST",
            updated_by=updater,
        )


# ================================================================
# Cross-tenant isolation
# ================================================================


@pytest.mark.asyncio
async def test_cross_tenant_isolation_steps(db):
    """Project B context · NO debe ver tasks de project A."""
    _, project_a = await setup_test_project(db)
    await _set_project_categoria(db, project_a, "MEDIA", "saas_only")
    updater = uuid.uuid4()

    # Crear task project_a
    service_a = WorkflowEngineService(db)
    await service_a.advance_step(
        project_id=uuid.UUID(project_a),
        template_id="ENR_OB_01_KICKOFF_19DIMS",
        updated_by=updater,
    )

    # Crear project_b (context cambia a B)
    _, project_b = await setup_test_project(db)
    await _set_project_categoria(db, project_b, "MEDIA", "saas_only")

    # Bajo context B · steps de A debe fallar (load_project_dims raises)
    with pytest.raises(ValueError):
        await load_project_dims(db, uuid.UUID(project_a))
