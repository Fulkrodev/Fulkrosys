"""#36 Ola IV · el intake/versionado IDMS persiste el BINARIO real en MinIO.

Antes de #36 ``intake_document`` y ``create_version`` calculaban ``storage_path``
y guardaban la metadata pero DESCARTABAN los bytes → el objeto nunca existía en el
object store. Estos tests verifican el round-trip real: tras el intake, el objeto
existe en ``fulkro-documents`` y ``get_object`` devuelve EXACTAMENTE los mismos
bytes; y una nueva versión sube su propio binario distinto.

Requiere MinIO arriba + bucket ``fulkro-documents`` (parte del stack dev/CI, igual
que los e2e de m14 adenda y m25 backup que ya suben sin mock).
"""
from __future__ import annotations

import uuid

import pytest

from backend.app.core.storage.minio_client import (
    BUCKET_DOCUMENTS,
    get_object,
    remove_object,
)
from backend.app.database import set_tenant_context
from backend.app.motors.m24_idms.idms_service import IDMSService
from backend.tests.conftest import setup_test_project


async def _setup_tenant(db):
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db,
        client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
    )
    return client_id, project_id


@pytest.mark.asyncio
async def test_intake_uploads_real_bytes_to_minio(db):
    _, project_id = await _setup_tenant(db)
    svc = IDMSService()
    contenido = b"#36 binario real intake \x00\x01\x02 ENS op.exp.8"

    result = await svc.intake_document(
        db,
        project_id=uuid.UUID(project_id),
        nombre="evidencia_36.bin",
        contenido=contenido,
        tipo_mime="application/octet-stream",
    )
    assert result["duplicate"] is False
    storage_path = result["document"].storage_path

    # CRÍTICO (#36 fix): storage_path canónico minio://{bucket}/{key} · sin él el
    # portal cliente m21 devuelve 503 (file_path.startswith('minio://')).
    assert storage_path.startswith(f"minio://{BUCKET_DOCUMENTS}/")
    # contenido_path de la versión v1 también canónico
    assert result["version"].contenido_path == storage_path

    # round-trip parseando igual que el lector m21 (rest.partition('/'))
    rest = storage_path[len("minio://"):]
    bucket, _, key = rest.partition("/")
    assert bucket == BUCKET_DOCUMENTS
    try:
        assert get_object(bucket, key) == contenido
    finally:
        remove_object(bucket, key)


@pytest.mark.asyncio
async def test_create_version_uploads_its_own_bytes(db):
    _, project_id = await _setup_tenant(db)
    svc = IDMSService()
    v1_bytes = b"version uno"
    v2_bytes = b"version dos distinta"

    intake = await svc.intake_document(
        db,
        project_id=uuid.UUID(project_id),
        nombre="doc_versionado_36.txt",
        contenido=v1_bytes,
        tipo_mime="text/plain",
    )
    doc_id = intake["document"].id
    v1_path = intake["document"].storage_path

    ver = await svc.create_version(
        db,
        document_id=doc_id,
        contenido=v2_bytes,
        descripcion_cambio="rev #36",
    )
    v2_path = ver["document"].storage_path
    assert v2_path != v1_path  # rutas distintas por versión + hash
    assert v1_path.startswith(f"minio://{BUCKET_DOCUMENTS}/")
    assert v2_path.startswith(f"minio://{BUCKET_DOCUMENTS}/")

    def _key(p: str) -> str:
        return p[len("minio://"):].partition("/")[2]

    try:
        assert get_object(BUCKET_DOCUMENTS, _key(v1_path)) == v1_bytes
        assert get_object(BUCKET_DOCUMENTS, _key(v2_path)) == v2_bytes
    finally:
        remove_object(BUCKET_DOCUMENTS, _key(v1_path))
        remove_object(BUCKET_DOCUMENTS, _key(v2_path))
