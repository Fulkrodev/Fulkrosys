"""Unit tests workflow_state.get_current_phase (FASE 8 · ADR-026).

2 tests baseline:
- test_get_current_phase_uses_persisted_value · projects.fase persistido = priority
- test_get_current_phase_default_pre_venta_for_new_project · server_default
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text as sa_text

from backend.app.core.workflow_phase import WorkflowPhase
from backend.app.core.workflow_state import (
    get_current_phase,
    get_next_actions,
    get_phase_progress,
    get_phase_tasks,
    get_workflow_roadmap,
    verify_client_owns_project,
)
from backend.app.database import set_tenant_context
from backend.tests.conftest import _admin_setup


async def _setup_project_with_fase(
    db, project_id: uuid.UUID, client_id: uuid.UUID, fase: str, cif: str,
) -> None:
    """Helper · client + project con fase persisted (RLS-aware)."""
    async with _admin_setup(db):
        await db.execute(
            sa_text(
                "INSERT INTO clients (id, nombre, cif) "
                "VALUES (:cid, :name, :cif)"
            ),
            {"cid": str(client_id), "name": f"Test {cif}", "cif": cif},
        )
        await db.execute(
            sa_text(
                "INSERT INTO projects (id, client_id, nombre, fase) "
                "VALUES (:pid, :cid, :name, :fase)"
            ),
            {
                "pid": str(project_id),
                "cid": str(client_id),
                "name": f"Project {cif}",
                "fase": fase,
            },
        )
    await set_tenant_context(db, client_id=client_id, project_id=project_id)


@pytest.mark.asyncio
async def test_get_current_phase_uses_persisted_value(db):
    """projects.fase persistida = source of truth primaria (ADR-026)."""
    project_id = uuid.uuid4()
    client_id = uuid.uuid4()

    async with _admin_setup(db):
        await db.execute(
            sa_text(
                "INSERT INTO clients (id, nombre, cif) "
                "VALUES (:cid, 'Test Client', 'B-TEST-001')"
            ),
            {"cid": str(client_id)},
        )
        await db.execute(
            sa_text(
                "INSERT INTO projects (id, client_id, nombre, fase) "
                "VALUES (:pid, :cid, 'Test Project', 'verificacion')"
            ),
            {"pid": str(project_id), "cid": str(client_id)},
        )

    # SUT: tenant context para RLS read access
    await set_tenant_context(db, client_id=client_id, project_id=project_id)

    phase = await get_current_phase(db, project_id)

    assert phase == WorkflowPhase.VERIFICACION


@pytest.mark.asyncio
async def test_get_current_phase_default_pre_venta_for_new_project(db):
    """Proyecto nuevo (server_default 'pre_venta') retorna PRE_VENTA."""
    project_id = uuid.uuid4()
    client_id = uuid.uuid4()

    async with _admin_setup(db):
        await db.execute(
            sa_text(
                "INSERT INTO clients (id, nombre, cif) "
                "VALUES (:cid, 'Test Client 2', 'B-TEST-002')"
            ),
            {"cid": str(client_id)},
        )
        # No fase explícita · usa server_default 'pre_venta'
        await db.execute(
            sa_text(
                "INSERT INTO projects (id, client_id, nombre) "
                "VALUES (:pid, :cid, 'Test Project 2')"
            ),
            {"pid": str(project_id), "cid": str(client_id)},
        )

    await set_tenant_context(db, client_id=client_id, project_id=project_id)

    phase = await get_current_phase(db, project_id)

    assert phase == WorkflowPhase.PRE_VENTA


@pytest.mark.asyncio
async def test_get_current_phase_raises_for_unknown_project(db):
    """Proyecto inexistente raise ValueError."""
    unknown_id = uuid.uuid4()

    with pytest.raises(ValueError, match="not found"):
        await get_current_phase(db, unknown_id)


@pytest.mark.asyncio
async def test_cascade_ignores_pre_phase_change_data(db):
    """W3 ISSUE: CASCADE filtra data motor pre-ultimo phase_changed event.

    Setup proyecto con un ``verification_runs.completed`` antiguo + un
    ``phase_changed`` event posterior. ``_derive_phase_cascade`` NO debe
    retornar VERIFICACION (data legacy filtrada).

    Sin este filtro, una regresion de fase dejaba data motor pre-regresion
    disparando CASCADE a fase incorrecta. Test invoca CASCADE directamente
    (el CHECK constraint sobre projects.fase impide forzarlo via fase
    invalida en get_current_phase).
    """
    from datetime import datetime, timedelta, timezone

    from backend.app.core.workflow_state import _derive_phase_cascade

    project_id = uuid.uuid4()
    client_id = uuid.uuid4()
    long_ago = datetime.now(timezone.utc) - timedelta(days=180)
    recent = datetime.now(timezone.utc) - timedelta(days=1)

    async with _admin_setup(db):
        await db.execute(
            sa_text(
                "INSERT INTO clients (id, nombre, cif) "
                "VALUES (:cid, 'W3 Client', 'B-W3-001')"
            ),
            {"cid": str(client_id)},
        )
        await db.execute(
            sa_text(
                "INSERT INTO projects (id, client_id, nombre, fase) "
                "VALUES (:pid, :cid, 'W3 Project', 'pre_venta')"
            ),
            {"pid": str(project_id), "cid": str(client_id)},
        )
        # verification_run.completed antiguo (pre-regresion · debe filtrarse).
        await db.execute(
            sa_text(
                "INSERT INTO verification_runs "
                "(id, project_id, category, mode, scope_jsonb, status, "
                " created_at, completed_at) "
                "VALUES (:rid, :pid, 'BASICO', 'internal', "
                "        '{}'::jsonb, 'completed', :old, :old)"
            ),
            {
                "rid": str(uuid.uuid4()),
                "pid": str(project_id),
                "old": long_ago,
            },
        )
        # phase_changed event posterior (simula regresion · barrera temporal).
        await db.execute(
            sa_text(
                "INSERT INTO project_lifecycle_events "
                "(id, project_id, client_id, event_type, event_date, "
                " metadata_jsonb) "
                "VALUES (:eid, :pid, :cid, 'phase_changed', :recent, "
                "        '{\"to_phase\": \"pre_venta\"}'::jsonb)"
            ),
            {
                "eid": str(uuid.uuid4()),
                "pid": str(project_id),
                "cid": str(client_id),
                "recent": recent,
            },
        )

    await set_tenant_context(db, client_id=client_id, project_id=project_id)

    phase = await _derive_phase_cascade(db, project_id)

    # CASCADE: verification_run pre-regresion filtrado, no dispara VERIFICACION.
    # Default cae a PRE_VENTA (sin data motor post-regresion).
    assert phase == WorkflowPhase.PRE_VENTA


@pytest.mark.asyncio
async def test_cascade_no_phase_change_event_keeps_legacy_behaviour(db):
    """W3 retrocompat: si NO hay phase_changed events, COALESCE→epoch deja
    pasar toda la data (comportamiento equivalente al pre-W3).
    """
    from datetime import datetime, timedelta, timezone

    from backend.app.core.workflow_state import _derive_phase_cascade

    project_id = uuid.uuid4()
    client_id = uuid.uuid4()
    long_ago = datetime.now(timezone.utc) - timedelta(days=365)

    async with _admin_setup(db):
        await db.execute(
            sa_text(
                "INSERT INTO clients (id, nombre, cif) "
                "VALUES (:cid, 'W3 Client B', 'B-W3-002')"
            ),
            {"cid": str(client_id)},
        )
        await db.execute(
            sa_text(
                "INSERT INTO projects (id, client_id, nombre, fase) "
                "VALUES (:pid, :cid, 'W3 Project B', 'pre_venta')"
            ),
            {"pid": str(project_id), "cid": str(client_id)},
        )
        # verification_run.completed antiguo · sin phase_changed event existe.
        await db.execute(
            sa_text(
                "INSERT INTO verification_runs "
                "(id, project_id, category, mode, scope_jsonb, status, "
                " created_at, completed_at) "
                "VALUES (:rid, :pid, 'BASICO', 'internal', "
                "        '{}'::jsonb, 'completed', :old, :old)"
            ),
            {
                "rid": str(uuid.uuid4()),
                "pid": str(project_id),
                "old": long_ago,
            },
        )

    await set_tenant_context(db, client_id=client_id, project_id=project_id)

    phase = await _derive_phase_cascade(db, project_id)

    # Sin phase_changed events: COALESCE→epoch · verification cuenta normal.
    assert phase == WorkflowPhase.VERIFICACION


@pytest.mark.asyncio
async def test_get_next_actions_returns_phase_specific_template(db):
    """ACTION_TEMPLATES per fase devuelve actions priorizadas."""
    project_id = uuid.uuid4()
    client_id = uuid.uuid4()
    await _setup_project_with_fase(db, project_id, client_id, "onboarding", "B-T-003")

    actions = await get_next_actions(db, project_id, limit=5)

    assert len(actions) >= 2  # ONBOARDING tiene 3 actions defined
    assert actions[0].priority == 1
    assert all(a.motor for a in actions)
    assert all(a.action_id for a in actions)


@pytest.mark.asyncio
async def test_get_next_actions_respects_limit(db):
    """Limit honored independientemente de cuántas actions tenga la fase."""
    project_id = uuid.uuid4()
    client_id = uuid.uuid4()
    await _setup_project_with_fase(db, project_id, client_id, "implantacion", "B-T-004")

    actions = await get_next_actions(db, project_id, limit=2)

    assert len(actions) == 2
    # Sorted by priority ascending
    assert actions[0].priority <= actions[1].priority


@pytest.mark.asyncio
async def test_get_phase_progress_past_phase_done(db):
    """Fase pasada (orden < current) retorna status='done' pct=100."""
    project_id = uuid.uuid4()
    client_id = uuid.uuid4()
    await _setup_project_with_fase(db, project_id, client_id, "verificacion", "B-T-005")

    progress = await get_phase_progress(db, project_id, WorkflowPhase.ONBOARDING)

    assert progress.status == "done"
    assert progress.pct_completed == 100.0
    assert progress.items_done == progress.total_items


@pytest.mark.asyncio
async def test_get_phase_progress_current_phase_real_data(db):
    """W1: fase == current usa query motor real · diagnostico sin data → pending."""
    project_id = uuid.uuid4()
    client_id = uuid.uuid4()
    await _setup_project_with_fase(db, project_id, client_id, "diagnostico", "B-T-006")

    progress = await get_phase_progress(db, project_id, WorkflowPhase.DIAGNOSTICO)

    # W1 calibracion: sin diagnosis_runs en BD, pending real (era 50% MVP fake).
    assert progress.status == "pending"
    assert progress.pct_completed == 0.0
    assert progress.items_done == 0


@pytest.mark.asyncio
async def test_phase_progress_w1_partial_in_progress_onboarding(db):
    """W1: ONBOARDING parcial (1/5 items) → in_progress 20.0%."""
    project_id = uuid.uuid4()
    client_id = uuid.uuid4()
    await _setup_project_with_fase(db, project_id, client_id, "onboarding", "B-T-W1A")

    # Insert minimal onboarding_session (task 1 done · interlocutor null · resto pending).
    async with _admin_setup(db):
        await db.execute(
            sa_text(
                "INSERT INTO onboarding_sessions "
                "(id, project_id, sector, rol_receptor, "
                " interlocutor_nombre, "
                " preguntas, respuestas, conectores_autorizados, estado) "
                "VALUES (:sid, :pid, 'salud', 'rseg', "
                "        'Test Person', "
                "        '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, 'iniciada')"
            ),
            {"sid": str(uuid.uuid4()), "pid": str(project_id)},
        )

    progress = await get_phase_progress(db, project_id, WorkflowPhase.ONBOARDING)

    assert progress.status == "in_progress"
    assert progress.items_done == 1  # solo task 1 (sesion existe)
    assert progress.total_items == 5
    assert progress.pct_completed == 20.0


@pytest.mark.asyncio
async def test_phase_progress_w1_full_done_when_all_signals_present(db):
    """W1: ONBOARDING todos signals → status='done' pct=100."""
    project_id = uuid.uuid4()
    client_id = uuid.uuid4()
    await _setup_project_with_fase(db, project_id, client_id, "onboarding", "B-T-W1B")

    async with _admin_setup(db):
        # Sesion completa con todos los signals: interlocutor + sent + answers + completed.
        await db.execute(
            sa_text(
                "INSERT INTO onboarding_sessions "
                "(id, project_id, sector, rol_receptor, "
                " interlocutor_nombre, interlocutor_email, "
                " preguntas, respuestas, conectores_autorizados, estado, "
                " sent_at, answered_questions, total_questions) "
                "VALUES (:sid, :pid, 'salud', 'rseg', "
                "        'Test Person', 'test@example.com', "
                "        '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, 'completed', "
                "        now(), 10, 10)"
            ),
            {"sid": str(uuid.uuid4()), "pid": str(project_id)},
        )

    progress = await get_phase_progress(db, project_id, WorkflowPhase.ONBOARDING)

    assert progress.status == "done"
    assert progress.items_done == 5
    assert progress.pct_completed == 100.0


@pytest.mark.asyncio
async def test_get_phase_tasks_returns_template_items(db):
    """Tasks template per fase retorna lista ordenada con status real (W2)."""
    project_id = uuid.uuid4()
    client_id = uuid.uuid4()
    await _setup_project_with_fase(db, project_id, client_id, "onboarding", "B-T-007")

    tasks = await get_phase_tasks(db, project_id, WorkflowPhase.ONBOARDING)

    assert len(tasks) == 5  # ONBOARDING template tiene 5 tasks
    # Sorted ascending by ord
    ords = [t.ord for t in tasks]
    assert ords == sorted(ords)
    # W2: sin onboarding_session insertada todas las tasks 'pending' (no completed).
    statuses = [t.status for t in tasks]
    assert all(s == "pending" for s in statuses)


@pytest.mark.asyncio
async def test_phase_tasks_w2_pre_venta_manual_tracking(db):
    """W2: PRE_VENTA tasks 3/4 (proposals, contracts) son manual_tracking."""
    project_id = uuid.uuid4()
    client_id = uuid.uuid4()
    await _setup_project_with_fase(db, project_id, client_id, "pre_venta", "B-T-W2A")

    tasks = await get_phase_tasks(db, project_id, WorkflowPhase.PRE_VENTA)
    assert len(tasks) == 4

    # Task 1 'Cualificar lead' → completed (project existe).
    assert tasks[0].ord == 1
    assert tasks[0].status == "completed"
    # Task 2 'Reunion exploratoria' → pending (sin meeting completed insertado).
    assert tasks[1].ord == 2
    assert tasks[1].status == "pending"
    # Task 3 'Propuesta enviada' (lead_id sin link a project) → manual_tracking.
    assert tasks[2].ord == 3
    assert tasks[2].status == "manual_tracking"
    # Task 4 'Contrato firmado' (lead_id sin link a project) → manual_tracking.
    assert tasks[3].ord == 4
    assert tasks[3].status == "manual_tracking"


@pytest.mark.asyncio
async def test_phase_tasks_w2_partial_completion_real(db):
    """W2: ONBOARDING parcial (2/5 signals) → 2 completed, 3 pending."""
    project_id = uuid.uuid4()
    client_id = uuid.uuid4()
    await _setup_project_with_fase(
        db, project_id, client_id, "onboarding", "B-T-W2B"
    )

    # Insert sesion con interlocutor_email NOT NULL pero sin sent_at/answers/completed.
    async with _admin_setup(db):
        await db.execute(
            sa_text(
                "INSERT INTO onboarding_sessions "
                "(id, project_id, sector, rol_receptor, "
                " interlocutor_nombre, interlocutor_email, "
                " preguntas, respuestas, conectores_autorizados, estado) "
                "VALUES (:sid, :pid, 'salud', 'rseg', "
                "        'Test Person', 'test@example.com', "
                "        '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, 'iniciada')"
            ),
            {"sid": str(uuid.uuid4()), "pid": str(project_id)},
        )

    tasks = await get_phase_tasks(db, project_id, WorkflowPhase.ONBOARDING)

    statuses_by_ord = {t.ord: t.status for t in tasks}
    # task 1 sesion creada → completed
    assert statuses_by_ord[1] == "completed"
    # task 2 RSEG definido (interlocutor_email NOT NULL) → completed
    assert statuses_by_ord[2] == "completed"
    # task 3 magic link sent_at NULL → pending
    assert statuses_by_ord[3] == "pending"
    # task 4 answered_questions=0 → pending
    assert statuses_by_ord[4] == "pending"
    # task 5 estado='iniciada' (no completed) → pending
    assert statuses_by_ord[5] == "pending"


@pytest.mark.asyncio
async def test_get_workflow_roadmap_returns_10_phases(db):
    """Roadmap 10 fases canonical (SAN-C MB-11.1) con un is_current=True."""
    project_id = uuid.uuid4()
    client_id = uuid.uuid4()
    await _setup_project_with_fase(db, project_id, client_id, "adecuacion", "B-T-008")

    roadmap = await get_workflow_roadmap(db, project_id)

    assert roadmap.current_phase == WorkflowPhase.ADECUACION
    assert len(roadmap.phases) == 10
    current_count = sum(1 for p in roadmap.phases if p.is_current)
    assert current_count == 1


@pytest.mark.asyncio
async def test_verify_client_owns_project_true_when_match(db):
    """verify_client_owns_project=True si project.client_id matches."""
    project_id = uuid.uuid4()
    client_id = uuid.uuid4()
    await _setup_project_with_fase(db, project_id, client_id, "diagnostico", "B-T-009")

    owns = await verify_client_owns_project(db, project_id, client_id)
    assert owns is True


@pytest.mark.asyncio
async def test_verify_client_owns_project_false_when_mismatch(db):
    """verify_client_owns_project=False si project pertenece a otro cliente."""
    project_id = uuid.uuid4()
    owner_client_id = uuid.uuid4()
    other_client_id = uuid.uuid4()
    await _setup_project_with_fase(db, project_id, owner_client_id, "diagnostico", "B-T-010")

    owns = await verify_client_owns_project(db, project_id, other_client_id)
    assert owns is False


def test_portal_workflow_router_includes_phase_tasks_endpoint():
    """W4: portal_workflow router expone GET /phase-tasks/{project_id}/{phase}.

    Verifica registro del endpoint añadido en sub-bloque W4 (coherente con W2).
    No prueba RBAC (cubierto por test_portal_endpoints_have_require_client_user
    en suite RBAC general).
    """
    from backend.app.api.v1.portal_workflow import router as portal_router

    paths = {r.path for r in portal_router.routes}
    expected = "/portal/workflow/phase-tasks/{project_id}/{phase}"
    assert expected in paths, (
        f"Falta endpoint W4 en portal_workflow router. Paths: {paths}"
    )


# ════════════════════════════════════════════════════════════════════
# SAN-B.MB-6.1 · trigger BD phase_changed + SQL real instrumentations
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_phase_changed_trigger_emits_lifecycle_event(db):
    """UPDATE projects.fase emite row en project_lifecycle_events
    con event_type='phase_changed' y metadata_jsonb con old/new fase."""
    project_id = uuid.uuid4()
    client_id = uuid.uuid4()
    await _setup_project_with_fase(db, project_id, client_id, "diagnostico", "B-T-MB61A")

    async with _admin_setup(db):
        await db.execute(
            sa_text(
                "UPDATE projects SET fase = 'adecuacion' WHERE id = :pid"
            ),
            {"pid": str(project_id)},
        )

        events = (await db.execute(
            sa_text(
                "SELECT event_type, metadata_jsonb FROM project_lifecycle_events "
                "WHERE project_id = :pid AND event_type = 'phase_changed' "
                "ORDER BY event_date DESC"
            ),
            {"pid": str(project_id)},
        )).all()

    assert len(events) >= 1
    metadata = events[0][1]
    assert metadata["old_fase"] == "diagnostico"
    assert metadata["new_fase"] == "adecuacion"
    assert metadata["source"] == "tg_projects_phase_changed"


@pytest.mark.asyncio
async def test_phase_changed_trigger_NOT_emitted_when_unchanged(db):
    """UPDATE projects con fase = mismo valor previo NO emite event."""
    project_id = uuid.uuid4()
    client_id = uuid.uuid4()
    await _setup_project_with_fase(db, project_id, client_id, "diagnostico", "B-T-MB61B")

    async with _admin_setup(db):
        # UPDATE con mismo valor · trigger detecta IS DISTINCT FROM == false
        await db.execute(
            sa_text(
                "UPDATE projects SET fase = 'diagnostico' WHERE id = :pid"
            ),
            {"pid": str(project_id)},
        )

        count = (await db.execute(
            sa_text(
                "SELECT count(*) FROM project_lifecycle_events "
                "WHERE project_id = :pid AND event_type = 'phase_changed'"
            ),
            {"pid": str(project_id)},
        )).scalar()

    assert count == 0


@pytest.mark.asyncio
async def test_adecuacion_done_increments_with_gap_findings(db):
    """W1 instrumentation SAN-B.MB-6.1: gap_analysis task (Task 5
    de ADECUACION) increments done cuando existe finding con
    fuente='gap_analysis' (sustituye proxy MAGERIT approved)."""
    from backend.app.core.workflow_state import _adecuacion_items_done

    project_id = uuid.uuid4()
    client_id = uuid.uuid4()
    await _setup_project_with_fase(db, project_id, client_id, "adecuacion", "B-T-MB61C")

    # Pre: sin findings · gap task NO cuenta
    done_before = await _adecuacion_items_done(db, project_id)

    async with _admin_setup(db):
        await db.execute(
            sa_text(
                "INSERT INTO findings "
                "(id, project_id, fuente, severidad, medida_afectada, descripcion, estado) "
                "VALUES (:fid, :pid, 'gap_analysis', 'media', 'op.exp.4', "
                "        'Test gap finding', 'pendiente')"
            ),
            {"fid": str(uuid.uuid4()), "pid": str(project_id)},
        )

    done_after = await _adecuacion_items_done(db, project_id)

    assert done_after == done_before + 1


@pytest.mark.asyncio
async def test_adecuacion_done_does_not_count_non_gap_findings(db):
    """findings con fuente distinta NO se cuentan como gap_analysis done."""
    from backend.app.core.workflow_state import _adecuacion_items_done

    project_id = uuid.uuid4()
    client_id = uuid.uuid4()
    await _setup_project_with_fase(db, project_id, client_id, "adecuacion", "B-T-MB61D")

    done_before = await _adecuacion_items_done(db, project_id)

    async with _admin_setup(db):
        await db.execute(
            sa_text(
                "INSERT INTO findings "
                "(id, project_id, fuente, severidad, medida_afectada, descripcion, estado) "
                "VALUES (:fid, :pid, 'auditoria_externa', 'alta', "
                "        'op.exp.4', 'External audit finding', 'pendiente')"
            ),
            {"fid": str(uuid.uuid4()), "pid": str(project_id)},
        )

    done_after = await _adecuacion_items_done(db, project_id)

    assert done_after == done_before


@pytest.mark.asyncio
async def test_implantacion_done_increments_with_approved_policy(db):
    """W1 instrumentation SAN-B.MB-6.1: policies task increments done
    cuando existe Document tipo='politica' con approved_at IS NOT NULL."""
    from backend.app.core.workflow_state import _implantacion_items_done

    project_id = uuid.uuid4()
    client_id = uuid.uuid4()
    await _setup_project_with_fase(db, project_id, client_id, "implantacion", "B-T-MB61E")

    done_before = await _implantacion_items_done(db, project_id)

    async with _admin_setup(db):
        await db.execute(
            sa_text(
                "INSERT INTO documents "
                "(id, project_id, tipo, nombre, estado, plantilla_id, "
                " template_codigo, approved_at) "
                "VALUES (:did, :pid, 'politica', 'Política Seguridad', "
                "        'firmado', :tid, 'E-100', now())"
            ),
            {
                "did": str(uuid.uuid4()),
                "pid": str(project_id),
                "tid": str(uuid.uuid4()),
            },
        )

    done_after = await _implantacion_items_done(db, project_id)

    assert done_after == done_before + 1


@pytest.mark.asyncio
async def test_implantacion_done_excludes_unapproved_policy(db):
    """Política tipo='politica' SIN approved_at NO incrementa done count."""
    from backend.app.core.workflow_state import _implantacion_items_done

    project_id = uuid.uuid4()
    client_id = uuid.uuid4()
    await _setup_project_with_fase(db, project_id, client_id, "implantacion", "B-T-MB61F")

    done_before = await _implantacion_items_done(db, project_id)

    async with _admin_setup(db):
        await db.execute(
            sa_text(
                "INSERT INTO documents "
                "(id, project_id, tipo, nombre, estado, plantilla_id, "
                " template_codigo, approved_at) "
                "VALUES (:did, :pid, 'politica', 'Política Borrador', "
                "        'generado', :tid, 'E-100', NULL)"
            ),
            {
                "did": str(uuid.uuid4()),
                "pid": str(project_id),
                "tid": str(uuid.uuid4()),
            },
        )

    done_after = await _implantacion_items_done(db, project_id)

    assert done_after == done_before
