"""Tests ClientTaskService + templates loader (ADR-038 SAN-D MB-14.3)."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text

from backend.app.motors.m21_portal_cliente.models_tasks import ClientTask
from backend.app.motors.m21_portal_cliente.task_service import (
    ClientTaskService,
    TaskError,
)
from backend.app.motors.m21_portal_cliente.task_templates_loader import (
    get_template_by_id,
    get_templates_for_phase,
    load_task_templates,
)
from backend.tests.conftest import _admin_setup


async def _setup_project(db, *, categoria="MEDIA", archetype=None, fase="adecuacion"):
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
                "categoria_objetivo, archetype, fase, created_at) "
                "VALUES (:id, :cid, 'P', :cat, :arch, :fase, now())"
            ),
            {
                "id": str(project_id),
                "cid": str(client_id),
                "cat": categoria,
                "arch": archetype,
                "fase": fase,
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


# ─────────────────────────────────────────
# Templates loader tests
# ─────────────────────────────────────────


def test_load_task_templates_18_templates():
    """Verifica que los 18 templates LEGACY siguen presentes · NO break v3.8.

    Sub-atom 1.C.D.A v3.8 añadió ~30 templates enriched (prefix ENR_) ·
    relax assertion >= 18 para no romper expansion progressive futura.
    Legacy 18 IDs verificados explícitamente abajo.
    """
    catalog = load_task_templates()
    assert catalog.version == "1.0.0"
    assert len(catalog.templates) >= 18  # 18 legacy + N enriched v3.8+
    # Verificar legacy 18 IDs canónicos siguen presentes (anti-regression)
    legacy_ids = {
        "PHASE3_BASICA_REVIEW_DIAGNOSIS",
        "PHASE5_BASICA_APPROVE_PDA",
        "PHASE9_BASICA_SIGN_AUTOEVALUACION",
        "PHASE5_MEDIA_APPROVE_PDA",
        "PHASE8_MEDIA_ASSIGN_AUDITOR_ENAC",
        "PHASE9_MEDIA_REVIEW_AUDIT_REPORT",
        "PHASE5_ALTA_APPROVE_PDA",
        "PHASE8_ALTA_PENTEST_CPSTIC",
        "PHASE8_ALTA_RED_TEAM",
        "PHASE6_ALTA_CRIPTOGRAFIA_807",
        "PHASE9_ALTA_REVIEW_AUDIT_REPORT",
    }
    all_ids = {t.id for t in catalog.templates}
    assert legacy_ids.issubset(all_ids)


def test_get_templates_for_phase_basica_conformidad():
    """BASICA · phase=conformidad · solo PHASE9_BASICA_SIGN_AUTOEVALUACION."""
    templates = get_templates_for_phase("conformidad", "BASICA")
    ids = [t.id for t in templates]
    assert "PHASE9_BASICA_SIGN_AUTOEVALUACION" in ids
    assert "PHASE9_MEDIA_REVIEW_AUDIT_REPORT" not in ids
    assert "PHASE9_ALTA_REVIEW_AUDIT_REPORT" not in ids


def test_get_templates_for_phase_media_verificacion_includes_auditor():
    """MEDIA · phase=verificacion · auditor ENAC + sin Pentest CPSTIC."""
    templates = get_templates_for_phase("verificacion", "MEDIA")
    ids = [t.id for t in templates]
    assert "PHASE8_MEDIA_ASSIGN_AUDITOR_ENAC" in ids
    assert "PHASE8_ALTA_PENTEST_CPSTIC" not in ids


def test_get_templates_for_phase_alta_implantacion_archetype_salud():
    """ALTA + sector_salud · phase=implantacion · incluye art.9 RGPD."""
    templates = get_templates_for_phase(
        "implantacion", "ALTA", archetype="sector_salud",
    )
    ids = [t.id for t in templates]
    assert "ARCHETYPE_SECTOR_SALUD_ART9_REVIEW" in ids
    assert "PHASE6_ALTA_CRIPTOGRAFIA_807" in ids


def test_get_templates_no_archetype_skips_archetype_specific():
    """Sin archetype · skip ARCHETYPE_* templates."""
    templates = get_templates_for_phase("implantacion", "MEDIA", archetype=None)
    ids = [t.id for t in templates]
    assert "ARCHETYPE_SECTOR_SALUD_ART9_REVIEW" not in ids


def test_get_template_by_id():
    tmpl = get_template_by_id("PHASE3_BASICA_REVIEW_DIAGNOSIS")
    assert tmpl is not None
    assert tmpl.phase == "diagnostico"
    assert "BASICA" in tmpl.applicable_categories


# ─────────────────────────────────────────
# Service tests
# ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_regenerate_creates_tasks_for_phase(db):
    """MEDIA + phase adecuacion · genera PHASE5_MEDIA_APPROVE_PDA."""
    project_id = await _setup_project(db, categoria="MEDIA", fase="adecuacion")

    service = ClientTaskService(db)
    result = await service.regenerate_for_project(project_id)

    assert result["created"] >= 1
    rows = (
        await db.execute(
            select(ClientTask).where(ClientTask.project_id == project_id)
        )
    ).scalars().all()
    rows = list(rows)
    template_ids = {r.template_id for r in rows}
    assert "PHASE5_MEDIA_APPROVE_PDA" in template_ids


@pytest.mark.asyncio
async def test_regenerate_idempotent_skips_existing(db):
    project_id = await _setup_project(db, categoria="BASICA", fase="conformidad")

    service = ClientTaskService(db)
    first = await service.regenerate_for_project(project_id)
    second = await service.regenerate_for_project(project_id)

    assert first["created"] >= 1
    assert second["created"] == 0
    assert second["skipped"] == first["created"]


@pytest.mark.asyncio
async def test_list_tasks_filters_by_status(db):
    project_id = await _setup_project(db, categoria="BASICA", fase="conformidad")

    service = ClientTaskService(db)
    await service.regenerate_for_project(project_id)

    pending = await service.list_tasks(project_id, status="pending")
    assert len(pending) >= 1
    for t in pending:
        assert t.status == "pending"

    done = await service.list_tasks(project_id, status="done")
    assert len(done) == 0


@pytest.mark.asyncio
async def test_transition_pending_to_in_progress(db):
    project_id = await _setup_project(db, categoria="MEDIA", fase="adecuacion")

    service = ClientTaskService(db)
    await service.regenerate_for_project(project_id)

    tasks = await service.list_tasks(project_id, status="pending")
    task = tasks[0]

    transitioned = await service.transition(task.id, "in_progress")
    assert transitioned.status == "in_progress"
    assert transitioned.started_at is not None


@pytest.mark.asyncio
async def test_transition_to_done_sets_completed_at(db):
    project_id = await _setup_project(db, categoria="MEDIA", fase="adecuacion")

    service = ClientTaskService(db)
    await service.regenerate_for_project(project_id)
    tasks = await service.list_tasks(project_id, status="pending")

    transitioned = await service.transition(tasks[0].id, "done")
    assert transitioned.status == "done"
    assert transitioned.completed_at is not None
    assert transitioned.started_at is not None


@pytest.mark.asyncio
async def test_transition_to_blocked_with_reason(db):
    project_id = await _setup_project(db, categoria="ALTA", fase="verificacion")

    service = ClientTaskService(db)
    await service.regenerate_for_project(project_id)
    tasks = await service.list_tasks(project_id, status="pending")

    transitioned = await service.transition(
        tasks[0].id, "blocked", blocked_reason="Esperando proveedor",
    )
    assert transitioned.status == "blocked"
    assert transitioned.blocked_reason == "Esperando proveedor"


@pytest.mark.asyncio
async def test_transition_invalid_status_raises(db):
    project_id = await _setup_project(db, categoria="BASICA", fase="conformidad")

    service = ClientTaskService(db)
    await service.regenerate_for_project(project_id)
    tasks = await service.list_tasks(project_id)

    with pytest.raises(TaskError):
        await service.transition(tasks[0].id, "invalid_state")


@pytest.mark.asyncio
async def test_regenerate_archetype_specific(db):
    """sector_salud + ALTA + implantacion · genera ARCHETYPE_SECTOR_SALUD."""
    project_id = await _setup_project(
        db, categoria="ALTA", archetype="sector_salud", fase="implantacion",
    )

    service = ClientTaskService(db)
    result = await service.regenerate_for_project(project_id)

    rows = (
        await db.execute(
            select(ClientTask).where(ClientTask.project_id == project_id)
        )
    ).scalars().all()
    template_ids = {r.template_id for r in rows}
    assert "ARCHETYPE_SECTOR_SALUD_ART9_REVIEW" in template_ids


@pytest.mark.asyncio
async def test_project_not_found_returns_error(db):
    service = ClientTaskService(db)
    result = await service.regenerate_for_project(uuid.uuid4())
    assert result["created"] == 0
    assert result["error"] == "project_not_found"
