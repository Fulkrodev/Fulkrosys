"""Tests M24 permisos granulares (Sesion 9 Paso 3.1).

Cubre:
- grant_permission (upsert) + revoke_permission (soft delete).
- check_access con jerarquia owner > editor > viewer.
- Fallback RLS project_id cuando NO hay permisos explicitos.
- my_accessible_documents.
- Role enum validation.
"""
from __future__ import annotations

import uuid

import pytest

from backend.app.database import set_tenant_context
from backend.app.models.auth import User
from backend.app.motors.m24_idms.idms_service import (
    IDMSError,
    IDMSService,
    ROLE_EDITOR,
    ROLE_OWNER,
    ROLE_VIEWER,
    VALID_ROLES,
)
from backend.tests.conftest import _admin_setup, setup_test_project


async def _make_user(db, label: str) -> uuid.UUID:
    async with _admin_setup(db):
        u = User(
            email=f"u-{label}-{uuid.uuid4().hex[:6]}@test.es",
            display_name=label,
            password_hash="h",
        )
        db.add(u)
        await db.flush()
        return u.id


async def _setup(db) -> tuple[str, uuid.UUID, uuid.UUID]:
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db,
        client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
    )
    svc = IDMSService()
    await svc.initialize_standard_folders(db, uuid.UUID(project_id))
    r = await svc.intake_document(
        db, project_id=uuid.UUID(project_id),
        nombre="politica_shared.pdf", contenido=b"shared body",
    )
    return project_id, r["document"].id, uuid.UUID(project_id)


# ─────────── Role enum + catalogo ───────────


def test_valid_roles_set():
    assert set(VALID_ROLES) == {ROLE_OWNER, ROLE_EDITOR, ROLE_VIEWER}


# ─────────── grant_permission ───────────


@pytest.mark.asyncio
async def test_grant_permission_creates_row(db):
    _, doc_id, _ = await _setup(db)
    user_id = await _make_user(db, "viewer1")
    svc = IDMSService()
    perm = await svc.grant_permission(
        db, document_id=doc_id, user_id=user_id, role=ROLE_VIEWER,
    )
    assert perm.document_id == doc_id
    assert perm.user_id == user_id
    assert perm.role == ROLE_VIEWER
    assert perm.granted_at is not None


@pytest.mark.asyncio
async def test_grant_permission_invalid_role_raises(db):
    _, doc_id, _ = await _setup(db)
    user_id = await _make_user(db, "u1")
    svc = IDMSService()
    with pytest.raises(IDMSError, match="Role invalido"):
        await svc.grant_permission(
            db, document_id=doc_id, user_id=user_id, role="bogus",
        )


@pytest.mark.asyncio
async def test_grant_permission_upserts_existing(db):
    """Si el user ya tiene permiso, grant_permission actualiza el role."""
    _, doc_id, _ = await _setup(db)
    user_id = await _make_user(db, "u1")
    svc = IDMSService()

    p1 = await svc.grant_permission(
        db, document_id=doc_id, user_id=user_id, role=ROLE_VIEWER,
    )
    p2 = await svc.grant_permission(
        db, document_id=doc_id, user_id=user_id, role=ROLE_EDITOR,
    )
    # Mismo id (upsert, no crea nuevo)
    assert p1.id == p2.id
    assert p2.role == ROLE_EDITOR

    perms = await svc.list_permissions(db, doc_id)
    assert len(perms) == 1


# ─────────── revoke_permission ───────────


@pytest.mark.asyncio
async def test_revoke_permission_soft_delete(db):
    _, doc_id, _ = await _setup(db)
    user_id = await _make_user(db, "u1")
    svc = IDMSService()
    await svc.grant_permission(
        db, document_id=doc_id, user_id=user_id, role=ROLE_VIEWER,
    )
    removed = await svc.revoke_permission(db, doc_id, user_id)
    assert removed is True

    perms = await svc.list_permissions(db, doc_id)
    assert len(perms) == 0  # soft deleted fuera de lista


@pytest.mark.asyncio
async def test_revoke_permission_nonexistent_returns_false(db):
    _, doc_id, _ = await _setup(db)
    user_id = await _make_user(db, "u1")
    svc = IDMSService()
    removed = await svc.revoke_permission(db, doc_id, user_id)
    assert removed is False


# ─────────── check_access: fallback RLS ───────────


@pytest.mark.asyncio
async def test_check_access_no_permissions_fallback_allows_all(db):
    """Sin permisos explicitos, TODOS los users del proyecto acceden (RLS)."""
    _, doc_id, _ = await _setup(db)
    random_user_id = await _make_user(db, "random")
    svc = IDMSService()
    # Sin grant_permission previo -> fallback True
    assert await svc.check_access(
        db, doc_id, random_user_id, required_role=ROLE_VIEWER,
    ) is True


# ─────────── check_access: permisos explicitos + jerarquia ───────────


@pytest.mark.asyncio
async def test_check_access_explicit_viewer_cannot_edit(db):
    _, doc_id, _ = await _setup(db)
    viewer_id = await _make_user(db, "viewer")
    svc = IDMSService()
    await svc.grant_permission(
        db, document_id=doc_id, user_id=viewer_id, role=ROLE_VIEWER,
    )

    # Viewer puede leer
    assert await svc.check_access(db, doc_id, viewer_id, ROLE_VIEWER) is True
    # Viewer NO puede editar
    assert await svc.check_access(db, doc_id, viewer_id, ROLE_EDITOR) is False
    assert await svc.check_access(db, doc_id, viewer_id, ROLE_OWNER) is False


@pytest.mark.asyncio
async def test_check_access_editor_hierarchy(db):
    _, doc_id, _ = await _setup(db)
    editor_id = await _make_user(db, "editor")
    svc = IDMSService()
    await svc.grant_permission(
        db, document_id=doc_id, user_id=editor_id, role=ROLE_EDITOR,
    )

    # Editor puede ver Y editar
    assert await svc.check_access(db, doc_id, editor_id, ROLE_VIEWER) is True
    assert await svc.check_access(db, doc_id, editor_id, ROLE_EDITOR) is True
    # Editor NO puede ejercer owner-only
    assert await svc.check_access(db, doc_id, editor_id, ROLE_OWNER) is False


@pytest.mark.asyncio
async def test_check_access_owner_has_all(db):
    _, doc_id, _ = await _setup(db)
    owner_id = await _make_user(db, "owner")
    svc = IDMSService()
    await svc.grant_permission(
        db, document_id=doc_id, user_id=owner_id, role=ROLE_OWNER,
    )
    assert await svc.check_access(db, doc_id, owner_id, ROLE_VIEWER) is True
    assert await svc.check_access(db, doc_id, owner_id, ROLE_EDITOR) is True
    assert await svc.check_access(db, doc_id, owner_id, ROLE_OWNER) is True


@pytest.mark.asyncio
async def test_check_access_non_listed_user_denied(db):
    """Si HAY permisos explicitos, users no listados son denegados."""
    _, doc_id, _ = await _setup(db)
    listed_id = await _make_user(db, "listed")
    stranger_id = await _make_user(db, "stranger")
    svc = IDMSService()
    await svc.grant_permission(
        db, document_id=doc_id, user_id=listed_id, role=ROLE_VIEWER,
    )
    # Stranger no esta en la lista -> denegado
    assert await svc.check_access(db, doc_id, stranger_id, ROLE_VIEWER) is False


# ─────────── my_accessible_documents ───────────


@pytest.mark.asyncio
async def test_my_accessible_documents_combines_fallback_and_explicit(db):
    project_id, doc_id, _ = await _setup(db)
    svc = IDMSService()
    # Crear otro doc en mismo proyecto
    r2 = await svc.intake_document(
        db, project_id=uuid.UUID(project_id),
        nombre="otro_doc.pdf", contenido=b"another",
    )
    doc2_id = r2["document"].id

    user_a = await _make_user(db, "A")
    user_b = await _make_user(db, "B")

    # doc_id: explicit permission SOLO a user_a viewer
    await svc.grant_permission(
        db, document_id=doc_id, user_id=user_a, role=ROLE_VIEWER,
    )
    # doc2_id: sin permisos -> fallback RLS (ambos acceden)

    accessible_a = await svc.my_accessible_documents(
        db, uuid.UUID(project_id), user_a,
    )
    accessible_b = await svc.my_accessible_documents(
        db, uuid.UUID(project_id), user_b,
    )

    ids_a = {d.id for d in accessible_a}
    ids_b = {d.id for d in accessible_b}
    # user_a ve ambos (explicit + fallback)
    assert doc_id in ids_a
    assert doc2_id in ids_a
    # user_b solo ve el del fallback (no esta en la lista del doc_id)
    assert doc_id not in ids_b
    assert doc2_id in ids_b
