"""Tests M24 workflow status (Sesion 9 Paso 3.1).

Cubre transiciones draft -> review -> approved -> archived/deprecated
+ enforcement de reglas + approval timestamp + restore_to_draft.
"""
from __future__ import annotations

import uuid

import pytest

from backend.app.database import set_tenant_context
from backend.app.motors.m24_idms.idms_service import (
    IDMSError,
    IDMSService,
    STATUS_APPROVED,
    STATUS_ARCHIVED,
    STATUS_DEPRECATED,
    STATUS_DRAFT,
    STATUS_REVIEW,
    VALID_STATUSES,
    VALID_TRANSITIONS,
)
from backend.tests.conftest import setup_test_project


async def _setup_tenant_with_intake(db) -> tuple[str, str, uuid.UUID]:
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db,
        client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
    )
    svc = IDMSService()
    await svc.initialize_standard_folders(db, uuid.UUID(project_id))
    result = await svc.intake_document(
        db,
        project_id=uuid.UUID(project_id),
        nombre="politica_seguridad.pdf",
        contenido=b"Policy body v1",
    )
    doc_id = result["document"].id
    # intake deja el documento con estado legacy / None; el workflow
    # arranca desde draft cuando llamamos la primera transicion.
    return client_id, project_id, doc_id


# ─────────── Catalogo de transiciones ───────────


def test_valid_statuses_set():
    assert set(VALID_STATUSES) == {
        STATUS_DRAFT, STATUS_REVIEW, STATUS_APPROVED,
        STATUS_ARCHIVED, STATUS_DEPRECATED,
    }


def test_transitions_matrix_coherente():
    # draft puede ir a review o archived
    assert STATUS_REVIEW in VALID_TRANSITIONS[STATUS_DRAFT]
    assert STATUS_ARCHIVED in VALID_TRANSITIONS[STATUS_DRAFT]
    # approved NO puede regresar a draft directamente
    assert STATUS_DRAFT not in VALID_TRANSITIONS[STATUS_APPROVED]
    # deprecated SOLO a draft via restore
    assert VALID_TRANSITIONS[STATUS_DEPRECATED] == {STATUS_DRAFT}


# ─────────── Transiciones happy path ───────────


@pytest.mark.asyncio
async def test_submit_for_review_from_draft(db):
    _, _, doc_id = await _setup_tenant_with_intake(db)
    svc = IDMSService()
    doc = await svc.submit_for_review(db, doc_id)
    assert doc.estado == STATUS_REVIEW


@pytest.mark.asyncio
async def test_approve_sets_approver_and_timestamp(db):
    _, _, doc_id = await _setup_tenant_with_intake(db)
    svc = IDMSService()
    await svc.submit_for_review(db, doc_id)
    # approver_user_id debe ser FK a auth_users; creamos uno ficticio
    from backend.app.models.auth import User
    from backend.tests.conftest import _admin_setup

    async with _admin_setup(db):
        user = User(
            email=f"approver-{uuid.uuid4().hex[:8]}@test.es",
            display_name="Ana Approver",
            password_hash="hashed",
        )
        db.add(user)
        await db.flush()
        approver_id = user.id

    doc = await svc.approve_document(db, doc_id, approver_id)
    assert doc.estado == STATUS_APPROVED
    assert doc.approved_by_user_id == approver_id
    assert doc.approved_at is not None


@pytest.mark.asyncio
async def test_archive_from_approved(db):
    _, _, doc_id = await _setup_tenant_with_intake(db)
    svc = IDMSService()
    await svc.submit_for_review(db, doc_id)
    from backend.app.models.auth import User
    from backend.tests.conftest import _admin_setup

    async with _admin_setup(db):
        user = User(
            email=f"u-{uuid.uuid4().hex[:8]}@test.es",
            display_name="U",
            password_hash="h",
        )
        db.add(user)
        await db.flush()
    await svc.approve_document(db, doc_id, user.id)
    doc = await svc.archive_document(db, doc_id)
    assert doc.estado == STATUS_ARCHIVED


@pytest.mark.asyncio
async def test_deprecate_from_approved(db):
    _, _, doc_id = await _setup_tenant_with_intake(db)
    svc = IDMSService()
    await svc.submit_for_review(db, doc_id)
    from backend.app.models.auth import User
    from backend.tests.conftest import _admin_setup

    async with _admin_setup(db):
        user = User(
            email=f"u-{uuid.uuid4().hex[:8]}@test.es",
            display_name="U", password_hash="h",
        )
        db.add(user)
        await db.flush()
    await svc.approve_document(db, doc_id, user.id)
    doc = await svc.deprecate_document(db, doc_id)
    assert doc.estado == STATUS_DEPRECATED


# ─────────── Transiciones prohibidas ───────────


@pytest.mark.asyncio
async def test_approve_fails_from_draft_direct(db):
    """approve() desde draft debe fallar (requiere pasar por review)."""
    _, _, doc_id = await _setup_tenant_with_intake(db)
    svc = IDMSService()
    from backend.app.models.auth import User
    from backend.tests.conftest import _admin_setup

    async with _admin_setup(db):
        user = User(
            email=f"u-{uuid.uuid4().hex[:8]}@test.es",
            display_name="U", password_hash="h",
        )
        db.add(user)
        await db.flush()
    with pytest.raises(IDMSError, match="Transicion no permitida"):
        await svc.approve_document(db, doc_id, user.id)


@pytest.mark.asyncio
async def test_deprecate_fails_from_draft(db):
    """deprecate() desde draft debe fallar."""
    _, _, doc_id = await _setup_tenant_with_intake(db)
    svc = IDMSService()
    with pytest.raises(IDMSError, match="Transicion no permitida"):
        await svc.deprecate_document(db, doc_id)


# ─────────── restore_to_draft ───────────


@pytest.mark.asyncio
async def test_restore_from_archived_to_draft(db):
    _, _, doc_id = await _setup_tenant_with_intake(db)
    svc = IDMSService()
    await svc.submit_for_review(db, doc_id)
    from backend.app.models.auth import User
    from backend.tests.conftest import _admin_setup

    async with _admin_setup(db):
        user = User(
            email=f"u-{uuid.uuid4().hex[:8]}@test.es",
            display_name="U", password_hash="h",
        )
        db.add(user)
        await db.flush()
    await svc.approve_document(db, doc_id, user.id)
    await svc.archive_document(db, doc_id)
    doc = await svc.restore_to_draft(db, doc_id)
    assert doc.estado == STATUS_DRAFT


# ─────────── list_documents_by_status ───────────


@pytest.mark.asyncio
async def test_list_documents_by_status(db):
    _, project_id, doc_id = await _setup_tenant_with_intake(db)
    svc = IDMSService()

    # Crear 2 documentos mas
    await svc.intake_document(
        db, project_id=uuid.UUID(project_id),
        nombre="procedimiento_backups.pdf",
        contenido=b"another doc",
    )
    await svc.intake_document(
        db, project_id=uuid.UUID(project_id),
        nombre="politica_accesos.pdf",
        contenido=b"yet another doc",
    )

    await svc.submit_for_review(db, doc_id)

    in_review = await svc.list_documents_by_status(
        db, uuid.UUID(project_id), STATUS_REVIEW,
    )
    in_draft = await svc.list_documents_by_status(
        db, uuid.UUID(project_id), STATUS_DRAFT,
    )
    assert len(in_review) == 1
    assert in_review[0].id == doc_id
    # Los otros 2 siguen con estado legacy (None) y NO matchean draft
    # estricto. Es correcto: solo listamos lo que EXPLICITAMENTE esta
    # en ese estado.
    assert len(in_draft) == 0


@pytest.mark.asyncio
async def test_list_documents_by_status_invalid_raises(db):
    _, project_id, _ = await _setup_tenant_with_intake(db)
    svc = IDMSService()
    with pytest.raises(IDMSError, match="Status invalido"):
        await svc.list_documents_by_status(db, uuid.UUID(project_id), "bogus")
