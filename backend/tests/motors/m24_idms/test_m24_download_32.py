"""#32 (FRENTE B) · descarga admin del binario IDMS desde el gestor documental.

El gestor documental admin tenía listado pero NO endpoint de descarga del binario
(gap #32). Este test verifica el round-trip real vía HTTP:
intake (sube bytes a MinIO · storage_path canónico minio://) → GET admin
``/download`` → mismos bytes + Content-Disposition attachment.

Requiere MinIO arriba + bucket ``fulkro-documents`` (igual que
``test_m24_minio_persist_36``, parte del stack dev/CI).
"""
from __future__ import annotations

import uuid

import pytest

from backend.app.core.storage.minio_client import BUCKET_DOCUMENTS, remove_object
from backend.app.database import set_tenant_context
from backend.app.motors.m24_idms.idms_service import IDMSService
from backend.tests.conftest import setup_test_project

BASE = "/api/v1/idms"


@pytest.mark.asyncio
async def test_admin_download_returns_binary(async_client, db):
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id), project_id=uuid.UUID(project_id),
    )
    contenido = b"#32 binario admin download \x00\x01 ENS dossier entregable"
    res = await IDMSService().intake_document(
        db,
        project_id=uuid.UUID(project_id),
        nombre="entregable_32.pdf",
        contenido=contenido,
        tipo_mime="application/pdf",
    )
    doc_id = res["document"].id
    storage_path = res["document"].storage_path
    assert storage_path.startswith(f"minio://{BUCKET_DOCUMENTS}/")

    try:
        r = await async_client.get(
            f"{BASE}/projects/{project_id}/idms/documents/{doc_id}/download",
        )
        assert r.status_code == 200, r.text
        assert r.content == contenido
        assert "attachment" in r.headers.get("content-disposition", "").lower()
    finally:
        key = storage_path[len("minio://"):].partition("/")[2]
        remove_object(BUCKET_DOCUMENTS, key)


@pytest.mark.asyncio
async def test_admin_download_404_for_unknown(async_client, db):
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id), project_id=uuid.UUID(project_id),
    )
    r = await async_client.get(
        f"{BASE}/projects/{project_id}/idms/documents/{uuid.uuid4()}/download",
    )
    assert r.status_code == 404
