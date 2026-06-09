"""Tests m21 files extended endpoints · SAN-E v3.MB-6 atom 7.

10 tests cubren:
  Documents search + filter + pagination:
    1. test_documents_search_filename_ilike
    2. test_documents_search_full_text_content_ilike
    3. test_documents_filter_clasificacion
    4. test_documents_pagination_limit_offset
    5. test_documents_sort_recent_vs_name
  Document versions:
    6. test_document_versions_returns_empty_history_for_pristine_doc
    7. test_document_versions_returns_history_when_versions_exist
  Document preview (Q4 B iframe):
    8. test_document_preview_only_pdf_returns_inline_pdf
  Evidence list + filter scan_status:
    9. test_evidence_list_filter_scan_clean_only
   10. test_evidence_preview_blocks_non_clean_scan_status
"""
from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m21_portal_cliente.api import (
    portal_document_preview,
    portal_document_versions,
    portal_documents,
    portal_evidence_list,
    portal_evidence_preview,
)
from backend.tests.conftest import _admin_setup


_REPO_ROOT = Path(__file__).resolve().parents[4]


async def _create_client_user_with_project(
    db: AsyncSession,
) -> tuple[uuid.UUID, uuid.UUID, object]:
    """Create client + project + client_user · returns (client_id, project_id, user)."""
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()
    unique_cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(sa_text(
            "INSERT INTO clients (id, nombre, cif, created_at) "
            "VALUES (:id, 'Test Client', :cif, now())"
        ), {"id": str(client_id), "cif": unique_cif})
        await db.execute(sa_text(
            "INSERT INTO projects (id, client_id, nombre, created_at) "
            "VALUES (:id, :cid, 'Test Project', now())"
        ), {"id": str(project_id), "cid": str(client_id)})
        await db.execute(sa_text(
            "INSERT INTO client_users (id, client_id, email, password_hash, "
            "must_change_password, created_at) "
            "VALUES (:uid, :cid, :email, 'x', false, now())"
        ), {
            "uid": str(user_id),
            "cid": str(client_id),
            "email": f"u{user_id.hex[:6]}@test.es",
        })
    await db.execute(
        sa_text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(project_id)},
    )
    await db.execute(
        sa_text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": str(client_id)},
    )
    await db.flush()

    class _U:
        pass

    u = _U()
    u.id = user_id
    u.client_id = client_id
    return client_id, project_id, u


async def _seed_document(
    db: AsyncSession,
    project_id: uuid.UUID,
    *,
    nombre: str = "policy.pdf",
    template_codigo: str = "E-100",
    clasificacion: str = "policy",
    estado: str = "approved",
    version_actual: str = "1.0",
    full_text_content: str | None = None,
    pdf_path: str | None = None,
    file_size_bytes: int = 1024,
) -> uuid.UUID:
    document_id = uuid.uuid4()
    await db.execute(sa_text(
        "INSERT INTO documents (id, project_id, nombre, template_codigo, "
        "clasificacion, estado, version_actual, full_text_content, pdf_path, "
        "file_size_bytes, created_at) "
        "VALUES (:id, :pid, :nom, :tc, :cl, :est, :ver, :ftc, :pdf, :size, now())"
    ), {
        "id": str(document_id),
        "pid": str(project_id),
        "nom": nombre,
        "tc": template_codigo,
        "cl": clasificacion,
        "est": estado,
        "ver": version_actual,
        "ftc": full_text_content,
        "pdf": pdf_path,
        "size": file_size_bytes,
    })
    await db.flush()
    return document_id


async def _seed_evidence(
    db: AsyncSession,
    project_id: uuid.UUID,
    *,
    nombre: str = "evidencia.pdf",
    mime: str = "application/pdf",
    scan_status: str = "clean",
    fichero_path: str | None = None,
) -> uuid.UUID:
    eid = uuid.uuid4()
    await db.execute(sa_text(
        "INSERT INTO evidence (id, project_id, tipo, fichero_path, hash_sha256, "
        "vigente, fichero_nombre_original, fichero_mime_type, "
        "fichero_tamano_bytes, scan_status, created_at) "
        "VALUES (:id, :pid, 'test', :path, 'd', TRUE, :nom, :mime, 100, "
        ":status, now())"
    ), {
        "id": str(eid),
        "pid": str(project_id),
        "path": fichero_path,
        "nom": nombre,
        "mime": mime,
        "status": scan_status,
    })
    await db.flush()
    return eid


# ════════════════════════════════════════════════════════════════════
# Documents search + filter + pagination
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_documents_search_filename_ilike(db: AsyncSession):
    _, project_id, user = await _create_client_user_with_project(db)
    await _seed_document(db, project_id, nombre="security_policy.pdf")
    await _seed_document(db, project_id, nombre="backup_procedure.pdf")
    await _seed_document(db, project_id, nombre="incident_report.pdf")

    out = await portal_documents(
        q="security", clasificacion=None, folder_id=None, sort="recent",
        limit=50, offset=0, user=user, db=db,
    )
    assert len(out) == 1
    assert out[0]["nombre"] == "security_policy.pdf"


@pytest.mark.asyncio
async def test_documents_search_full_text_content_ilike(db: AsyncSession):
    _, project_id, user = await _create_client_user_with_project(db)
    await _seed_document(
        db, project_id, nombre="doc1.pdf",
        full_text_content="Lorem ipsum CCN-STIC 805 control logico",
    )
    await _seed_document(
        db, project_id, nombre="doc2.pdf",
        full_text_content="Otra cosa sin mencion",
    )

    out = await portal_documents(
        q="CCN-STIC", clasificacion=None, folder_id=None, sort="recent",
        limit=50, offset=0, user=user, db=db,
    )
    assert len(out) == 1
    assert out[0]["nombre"] == "doc1.pdf"


@pytest.mark.asyncio
async def test_documents_filter_clasificacion(db: AsyncSession):
    _, project_id, user = await _create_client_user_with_project(db)
    await _seed_document(db, project_id, clasificacion="policy", nombre="a.pdf")
    await _seed_document(db, project_id, clasificacion="procedure", nombre="b.pdf")
    await _seed_document(db, project_id, clasificacion="policy", nombre="c.pdf")

    out = await portal_documents(
        q=None, clasificacion="policy", folder_id=None, sort="recent",
        limit=50, offset=0, user=user, db=db,
    )
    names = {r["nombre"] for r in out}
    assert names == {"a.pdf", "c.pdf"}


@pytest.mark.asyncio
async def test_documents_pagination_limit_offset(db: AsyncSession):
    _, project_id, user = await _create_client_user_with_project(db)
    for i in range(7):
        await _seed_document(db, project_id, nombre=f"doc{i}.pdf")

    first = await portal_documents(
        q=None, clasificacion=None, folder_id=None, sort="recent",
        limit=3, offset=0, user=user, db=db,
    )
    second = await portal_documents(
        q=None, clasificacion=None, folder_id=None, sort="recent",
        limit=3, offset=3, user=user, db=db,
    )
    assert len(first) == 3
    assert len(second) == 3
    first_ids = {r["id"] for r in first}
    second_ids = {r["id"] for r in second}
    assert first_ids.isdisjoint(second_ids)


@pytest.mark.asyncio
async def test_documents_sort_recent_vs_name(db: AsyncSession):
    _, project_id, user = await _create_client_user_with_project(db)
    await _seed_document(db, project_id, nombre="zeta.pdf")
    await _seed_document(db, project_id, nombre="alpha.pdf")
    await _seed_document(db, project_id, nombre="mike.pdf")

    by_name = await portal_documents(
        q=None, clasificacion=None, folder_id=None, sort="name",
        limit=50, offset=0, user=user, db=db,
    )
    names_order = [r["nombre"] for r in by_name]
    assert names_order == ["alpha.pdf", "mike.pdf", "zeta.pdf"]


# ════════════════════════════════════════════════════════════════════
# Document versions
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_document_versions_returns_empty_history_for_pristine_doc(
    db: AsyncSession,
):
    _, project_id, user = await _create_client_user_with_project(db)
    doc_id = await _seed_document(db, project_id, version_actual="1.0")

    out = await portal_document_versions(
        document_id=doc_id, user=user, db=db,
    )
    assert out["current_version"] == "1.0"
    assert out["history"] == []
    assert out["document_id"] == str(doc_id)


@pytest.mark.asyncio
async def test_document_versions_returns_history_when_versions_exist(
    db: AsyncSession,
):
    _, project_id, user = await _create_client_user_with_project(db)
    doc_id = await _seed_document(db, project_id, version_actual="1.2")

    # Insert 2 version rows
    for v in ("1.0", "1.1"):
        await db.execute(sa_text(
            "INSERT INTO document_versions (id, document_id, version, "
            "hash_sha256, generado_at, created_at) "
            "VALUES (:id, :did, :ver, 'hsh', now(), now())"
        ), {
            "id": str(uuid.uuid4()),
            "did": str(doc_id),
            "ver": v,
        })
    await db.flush()

    out = await portal_document_versions(
        document_id=doc_id, user=user, db=db,
    )
    assert out["current_version"] == "1.2"
    assert len(out["history"]) == 2
    history_versions = {h["version"] for h in out["history"]}
    assert history_versions == {"1.0", "1.1"}


# ════════════════════════════════════════════════════════════════════
# Document preview (Q4 B iframe)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_document_preview_only_pdf_returns_inline_pdf(
    db: AsyncSession, tmp_path,
):
    _, project_id, user = await _create_client_user_with_project(db)

    # Create real PDF stub on disk (relative path under repo root expected)
    project_dir = _REPO_ROOT / "var" / "documents" / str(project_id)
    project_dir.mkdir(parents=True, exist_ok=True)
    pdf_file = project_dir / "preview_test.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\n%test stub\n%%EOF")
    relative_path = f"var/documents/{project_id}/preview_test.pdf"

    doc_id = await _seed_document(
        db, project_id, nombre="preview_test.pdf", pdf_path=relative_path,
    )

    resp = await portal_document_preview(
        document_id=doc_id, user=user, db=db,
    )
    assert resp.media_type == "application/pdf"
    assert "inline" in resp.headers.get("content-disposition", "")
    assert resp.headers.get("x-frame-options") == "SAMEORIGIN"


# ════════════════════════════════════════════════════════════════════
# Evidence list + scan filter
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_evidence_list_filter_scan_clean_only(db: AsyncSession):
    _, project_id, user = await _create_client_user_with_project(db)
    await _seed_evidence(db, project_id, nombre="a.pdf", scan_status="clean")
    await _seed_evidence(db, project_id, nombre="b.pdf", scan_status="quarantined")
    await _seed_evidence(db, project_id, nombre="c.pdf", scan_status="clean")
    await _seed_evidence(db, project_id, nombre="d.pdf", scan_status="scanning")

    all_items = await portal_evidence_list(
        q=None, scan_clean_only=False, sort="recent",
        limit=50, offset=0, user=user, db=db,
    )
    assert len(all_items) == 4

    only_clean = await portal_evidence_list(
        q=None, scan_clean_only=True, sort="recent",
        limit=50, offset=0, user=user, db=db,
    )
    names = {r["fichero_nombre_original"] for r in only_clean}
    assert names == {"a.pdf", "c.pdf"}


@pytest.mark.asyncio
async def test_evidence_preview_blocks_non_clean_scan_status(
    db: AsyncSession,
):
    from fastapi import HTTPException
    _, project_id, user = await _create_client_user_with_project(db)
    eid = await _seed_evidence(
        db, project_id, scan_status="quarantined",
        mime="application/pdf",
    )

    with pytest.raises(HTTPException) as exc_info:
        await portal_evidence_preview(
            evidence_id=eid, user=user, db=db,
        )
    assert exc_info.value.status_code == 403
    assert "scan_status" in exc_info.value.detail
