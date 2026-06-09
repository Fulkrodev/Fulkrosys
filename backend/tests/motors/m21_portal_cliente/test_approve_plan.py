"""#27 Ola 6 · aprobación explícita del Plan de Adecuación · traza R6.

Verifica bajo fulkro_app (contexto RLS cliente como el endpoint real):
- approve_plan marca la tarea done.
- emite audit_log canónico 'plan.approved' (Sub-atom 5.A · project_id+client_id).
- idempotente (segunda aprobación NO duplica el evento).
- guard: una tarea que NO es PHASE5_*_APPROVE_PDA es rechazada (TaskError).
- "aprobar" ≠ "firmar": NO se crea ninguna fila de firma (signing_events intacto).
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.app.motors.m21_portal_cliente.task_service import (
    ClientTaskService,
    TaskError,
)


pytestmark = [pytest.mark.asyncio, pytest.mark.requires_db]


async def _create_client_project(db, *, cif_prefix="P"):
    from backend.tests.conftest import _admin_setup

    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    cif = f"{cif_prefix}{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO clients (id, nombre, cif, created_at) "
            "VALUES (:id, 'Test Approve', :cif, now())"
        ), {"id": str(client_id), "cif": cif})
        await db.execute(text(
            "INSERT INTO projects (id, client_id, nombre, categoria_objetivo, created_at) "
            "VALUES (:id, :cid, 'PDA Project', 'BASICA', now())"
        ), {"id": str(project_id), "cid": str(client_id)})
    return client_id, project_id


async def _insert_task(db, *, project_id, template_id, title="Aprobar PDA"):
    from backend.tests.conftest import _admin_setup

    task_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO client_tasks "
            "(id, project_id, template_id, phase, title, status, priority, created_at) "
            "VALUES (:id, :pid, :tmpl, 'adecuacion', :title, 'pending', 9, now())"
        ), {
            "id": str(task_id),
            "pid": str(project_id),
            "tmpl": template_id,
            "title": title,
        })
    return task_id


async def _set_cliente_rls(db, *, project_id, client_id):
    # Mirror task_api._resolve_project_id · fulkro_app RLS context.
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(project_id)},
    )
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": str(client_id)},
    )


async def _count_plan_approved(db, *, project_id, task_id) -> int:
    from backend.tests.conftest import _admin_setup

    async with _admin_setup(db):
        return (await db.execute(text(
            "SELECT COUNT(*) FROM audit_log "
            "WHERE accion = 'plan.approved' AND project_id = :pid "
            "  AND registro_id = :tid"
        ), {"pid": str(project_id), "tid": str(task_id)})).scalar()


async def test_approve_plan_done_and_audit_log(db):
    client_id, project_id = await _create_client_project(db, cif_prefix="P")
    task_id = await _insert_task(
        db, project_id=project_id, template_id="PHASE5_BASICA_APPROVE_PDA",
    )
    client_user_id = uuid.uuid4()
    await _set_cliente_rls(db, project_id=project_id, client_id=client_id)

    service = ClientTaskService(db)
    task = await service.approve_plan(
        task_id, client_user_id=client_user_id, client_id=client_id,
    )
    assert task.status == "done", "aprobar marca la tarea done"

    count = await _count_plan_approved(db, project_id=project_id, task_id=task_id)
    assert count == 1, "debe emitir 1 evento audit_log plan.approved (R6)"


async def test_approve_plan_idempotent(db):
    client_id, project_id = await _create_client_project(db, cif_prefix="Q")
    task_id = await _insert_task(
        db, project_id=project_id, template_id="PHASE5_MEDIA_APPROVE_PDA",
    )
    client_user_id = uuid.uuid4()
    await _set_cliente_rls(db, project_id=project_id, client_id=client_id)
    service = ClientTaskService(db)

    await service.approve_plan(task_id, client_user_id=client_user_id, client_id=client_id)
    await service.approve_plan(task_id, client_user_id=client_user_id, client_id=client_id)

    count = await _count_plan_approved(db, project_id=project_id, task_id=task_id)
    assert count == 1, "idempotente · segunda aprobación NO duplica el evento"


async def test_approve_plan_rejects_non_pda_task(db):
    client_id, project_id = await _create_client_project(db, cif_prefix="R")
    task_id = await _insert_task(
        db, project_id=project_id, template_id="ENR_OB_01_KICKOFF_19DIMS",
        title="Kickoff",
    )
    await _set_cliente_rls(db, project_id=project_id, client_id=client_id)
    service = ClientTaskService(db)

    with pytest.raises(TaskError):
        await service.approve_plan(
            task_id, client_user_id=uuid.uuid4(), client_id=client_id,
        )


async def test_approve_plan_is_not_a_signature(db):
    """Aprobar ≠ firmar · NO crea fila en signing_events (Ed25519 intacto)."""
    client_id, project_id = await _create_client_project(db, cif_prefix="S")
    task_id = await _insert_task(
        db, project_id=project_id, template_id="PHASE5_ALTA_APPROVE_PDA",
    )
    await _set_cliente_rls(db, project_id=project_id, client_id=client_id)
    service = ClientTaskService(db)
    await service.approve_plan(
        task_id, client_user_id=uuid.uuid4(), client_id=client_id,
    )

    from backend.tests.conftest import _admin_setup

    async with _admin_setup(db):
        sign_rows = (await db.execute(text(
            "SELECT COUNT(*) FROM signing_events WHERE project_id = :pid"
        ), {"pid": str(project_id)})).scalar()
    assert sign_rows == 0, "aprobar NO debe generar firma criptográfica"
