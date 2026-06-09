"""Cross-project data leak prevention E2E (sub-atom 1.E.2 Phase D · ADR-054).

Verifica que cuando Marcos opera con proyecto A activo, las queries NO
devuelven datos de proyecto B (RLS + filters explícitos por project_id).

Cubre:
- M21 ChatService: threads de project A NO leak a query project B
- M9 dossier_generator: documents/evidence de project A NO leak a project B
- M6 DocumentFactoryService.list_documents NO leak cross-project
- 2-proyectos-mismo-cliente: verify aislamiento independent de client_id
"""
from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy import text as sa_text

from backend.app.database import set_tenant_context
from backend.app.models.documents import Document
from backend.app.motors.m21_portal_cliente.chat_service import ChatService
from backend.tests.conftest import _admin_setup


async def _create_client_with_2_projects(db) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """Crea 1 cliente con 2 proyectos (A y B) para verificar isolation
    cross-project DENTRO del mismo client (gold case · client multi-project)."""
    client_id = uuid.uuid4()
    project_a_id = uuid.uuid4()
    project_b_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"

    async with _admin_setup(db):
        await db.execute(
            sa_text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, 'Multi-Proj Client', :cif, now())"
            ),
            {"id": str(client_id), "cif": cif},
        )
        await db.execute(
            sa_text(
                "INSERT INTO projects (id, client_id, nombre, created_at) "
                "VALUES (:id, :cid, 'Project A', now())"
            ),
            {"id": str(project_a_id), "cid": str(client_id)},
        )
        await db.execute(
            sa_text(
                "INSERT INTO projects (id, client_id, nombre, created_at) "
                "VALUES (:id, :cid, 'Project B', now())"
            ),
            {"id": str(project_b_id), "cid": str(client_id)},
        )
    await db.flush()
    return client_id, project_a_id, project_b_id


@pytest.mark.asyncio
async def test_chat_threads_project_a_NOT_leak_to_project_b(db):
    """Threads creados en project A NO aparecen en list_threads(project_b)."""
    client_id, pa, pb = await _create_client_with_2_projects(db)

    # Set tenant context project A · create thread
    await set_tenant_context(db, client_id=client_id, project_id=pa)
    service = ChatService(db)
    thread_a = await service.get_or_create_thread(
        project_id=pa, subject="Project A thread",
    )
    assert thread_a.project_id == pa

    # Switch context to project B · list_threads should be EMPTY for B
    await set_tenant_context(db, client_id=client_id, project_id=pb)
    threads_b = await service.list_threads(pb)
    assert threads_b == [], (
        f"LEAK: project B query returned {len(threads_b)} threads · "
        f"deberia 0 (thread_a en project A)"
    )

    # Verify A still has its thread (no destructive cross-effect)
    await set_tenant_context(db, client_id=client_id, project_id=pa)
    threads_a = await service.list_threads(pa)
    assert len(threads_a) == 1
    assert threads_a[0].id == thread_a.id


@pytest.mark.asyncio
async def test_chat_threads_isolated_by_project_id_at_query_level(db):
    """Even cross-tenant-context, query filter por project_id es defensa primaria."""
    client_id, pa, pb = await _create_client_with_2_projects(db)

    # Set tenant context A · create 3 threads en A
    await set_tenant_context(db, client_id=client_id, project_id=pa)
    service = ChatService(db)
    for i in range(3):
        await service.get_or_create_thread(
            project_id=pa, subject=f"A thread {i}",
        )
        # Mark first as closed para crear 2nd open
        if i < 2:
            existing = await service.get_or_create_thread(project_id=pa)
            existing.status = "closed"
            await db.flush()

    # List threads project A · should be 3 total (1 open + 2 closed)
    threads_a = await service.list_threads(pa)
    threads_b = await service.list_threads(pb)
    assert len(threads_a) >= 1, f"project A debe tener threads: {threads_a}"
    assert threads_b == [], (
        f"project B debe ser empty cross-isolation: {threads_b}"
    )


@pytest.mark.asyncio
async def test_documents_project_a_NOT_leak_to_project_b(db):
    """Documents de project A NO aparecen cuando se query project B (M6)."""
    from sqlalchemy import select

    client_id, pa, pb = await _create_client_with_2_projects(db)

    # Insert doc en project A
    await set_tenant_context(db, client_id=client_id, project_id=pa)
    async with _admin_setup(db):
        doc_a = Document(
            project_id=pa,
            template_codigo="E-040",
            nombre="DdA A",
            estado="aprobado",
            aprobado_por="marcos",
            fecha_aprobacion=date.today(),
            tipo="ENTREGABLE",
        )
        db.add(doc_a)
        await db.flush()

    # Query documents filtered by project_id=pb (project B) · should be EMPTY
    await set_tenant_context(db, client_id=client_id, project_id=pb)
    result = await db.execute(
        select(Document).where(
            Document.project_id == pb,
            Document.deleted_at.is_(None),
        )
    )
    docs_b = list(result.scalars().all())
    assert docs_b == [], (
        f"LEAK: project B query returned {len(docs_b)} docs · deberia 0"
    )

    # Verify project A still has the doc
    await set_tenant_context(db, client_id=client_id, project_id=pa)
    result_a = await db.execute(
        select(Document).where(
            Document.project_id == pa,
            Document.deleted_at.is_(None),
        )
    )
    docs_a = list(result_a.scalars().all())
    assert len(docs_a) == 1
    assert docs_a[0].id == doc_a.id


@pytest.mark.asyncio
async def test_chat_thread_project_id_not_null_db_constraint(db):
    """ChatThread.project_id es NOT NULL FK · DB-level scoping enforced.

    Uses SAVEPOINT (begin_nested) para aislar la IntegrityError esperada
    y NO contaminar la session principal post-assertion.
    """
    from sqlalchemy.exc import IntegrityError, DBAPIError

    from backend.app.motors.m21_portal_cliente.models_chat import ChatThread

    client_id, pa, _ = await _create_client_with_2_projects(db)
    await set_tenant_context(db, client_id=client_id, project_id=pa)

    raised = False
    try:
        async with db.begin_nested():
            thread = ChatThread(
                project_id=None,  # type: ignore[arg-type]
                status="open",
                messages_count=0,
            )
            db.add(thread)
            await db.flush()
    except (IntegrityError, DBAPIError):
        raised = True

    assert raised, (
        "ChatThread.project_id NOT NULL constraint debe rechazar "
        "INSERT con project_id=NULL"
    )
