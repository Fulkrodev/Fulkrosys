"""Tests M24 IDMS.

Cubre:
- 15 carpetas estándar (idempotente)
- Intake pipeline: SHA-256, dedupe exacta, auto-classify por nombre
- Búsqueda ILIKE + filtros
- Tags manuales
- Versionado
- Stats
"""
from __future__ import annotations

import base64
import hashlib
import uuid

import pytest

from backend.app.database import set_tenant_context
from backend.app.motors.m24_idms.idms_service import (
    CLASSIFICATION_RULES,
    IDMSError,
    IDMSService,
    STANDARD_FOLDERS,
)
from backend.tests.conftest import setup_test_project


BASE = "/api/v1/idms"


async def _setup_tenant(db):
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db,
        client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
    )
    return client_id, project_id


# ─────────── Catálogo ───────────

def test_standard_folders_15():
    assert len(STANDARD_FOLDERS) == 15
    codes = [f["code"] for f in STANDARD_FOLDERS]
    assert "00" in codes and "99" in codes


def test_classification_rules_cover_main_types():
    classifications = {clas for _, _, clas in CLASSIFICATION_RULES}
    assert "politica" in classifications
    assert "procedimiento" in classifications
    assert "evidencia" in classifications
    assert "informe" in classifications
    assert "contrato" in classifications


# ─────────── Folders ───────────

@pytest.mark.asyncio
async def test_initialize_standard_folders_creates_15(db):
    _, project_id = await _setup_tenant(db)
    folders = await IDMSService().initialize_standard_folders(
        db, project_id=uuid.UUID(project_id),
    )
    assert len(folders) == 15
    assert all(f.is_standard for f in folders)
    codes = {f.standard_code for f in folders}
    assert codes == {f["code"] for f in STANDARD_FOLDERS}


@pytest.mark.asyncio
async def test_initialize_idempotent(db):
    _, project_id = await _setup_tenant(db)
    svc = IDMSService()
    first = await svc.initialize_standard_folders(db, uuid.UUID(project_id))
    second = await svc.initialize_standard_folders(db, uuid.UUID(project_id))
    assert len(first) == len(second) == 15


@pytest.mark.asyncio
async def test_create_custom_subfolder(db):
    _, project_id = await _setup_tenant(db)
    svc = IDMSService()
    stds = await svc.initialize_standard_folders(db, uuid.UUID(project_id))
    politicas = next(f for f in stds if f.standard_code == "06")
    sub = await svc.create_folder(
        db, project_id=uuid.UUID(project_id),
        name="infra", parent_folder_id=politicas.id,
    )
    assert sub.parent_folder_id == politicas.id
    assert sub.virtual_path.endswith("/infra/")
    assert sub.is_standard is False


@pytest.mark.asyncio
async def test_folder_tree_with_document_counts(db):
    _, project_id = await _setup_tenant(db)
    svc = IDMSService()
    await svc.initialize_standard_folders(db, uuid.UUID(project_id))
    await svc.intake_document(
        db, project_id=uuid.UUID(project_id),
        nombre="politica_seguridad.pdf",
        contenido=b"P1", tipo_mime="application/pdf",
    )
    tree = await svc.get_folder_tree(db, uuid.UUID(project_id))
    # 06_Normativa debería tener 1 documento
    politicas = next((f for f in tree["folders"] if f["standard_code"] == "06"), None)
    assert politicas is not None
    assert politicas["documents_count"] == 1


# ─────────── Intake ───────────

@pytest.mark.asyncio
async def test_intake_calculates_hash(db):
    _, project_id = await _setup_tenant(db)
    svc = IDMSService()
    await svc.initialize_standard_folders(db, uuid.UUID(project_id))
    contenido = b"Test content"
    expected = hashlib.sha256(contenido).hexdigest()
    result = await svc.intake_document(
        db, project_id=uuid.UUID(project_id),
        nombre="test.txt", contenido=contenido,
    )
    assert result["content_hash"] == expected
    assert result["document"].content_hash == expected
    assert result["duplicate"] is False


@pytest.mark.asyncio
async def test_intake_detects_duplicate_exact(db):
    _, project_id = await _setup_tenant(db)
    svc = IDMSService()
    await svc.initialize_standard_folders(db, uuid.UUID(project_id))
    contenido = b"Same content"
    first = await svc.intake_document(
        db, project_id=uuid.UUID(project_id),
        nombre="doc_v1.txt", contenido=contenido,
    )
    second = await svc.intake_document(
        db, project_id=uuid.UUID(project_id),
        nombre="doc_v2_renamed.txt", contenido=contenido,
    )
    assert first["duplicate"] is False
    assert second["duplicate"] is True
    assert second["document"].id == first["document"].id


@pytest.mark.asyncio
async def test_intake_auto_classifies_politica(db):
    _, project_id = await _setup_tenant(db)
    svc = IDMSService()
    folders = await svc.initialize_standard_folders(db, uuid.UUID(project_id))
    result = await svc.intake_document(
        db, project_id=uuid.UUID(project_id),
        nombre="politica_seguridad.pdf",
        contenido=b"X",
    )
    politicas = next(f for f in folders if f.standard_code == "06")
    assert result["document"].folder_id == politicas.id
    assert result["document"].clasificacion == "politica"


@pytest.mark.asyncio
async def test_intake_auto_classifies_informe_tecnico(db):
    _, project_id = await _setup_tenant(db)
    svc = IDMSService()
    folders = await svc.initialize_standard_folders(db, uuid.UUID(project_id))
    result = await svc.intake_document(
        db, project_id=uuid.UUID(project_id),
        nombre="informe_pentest_ext.pdf", contenido=b"Y",
    )
    tecnicos = next(f for f in folders if f.standard_code == "13")
    assert result["document"].folder_id == tecnicos.id
    assert result["document"].clasificacion == "informe"


@pytest.mark.asyncio
async def test_intake_unknown_goes_to_misc(db):
    _, project_id = await _setup_tenant(db)
    svc = IDMSService()
    folders = await svc.initialize_standard_folders(db, uuid.UUID(project_id))
    result = await svc.intake_document(
        db, project_id=uuid.UUID(project_id),
        nombre="archivo_random_xyz.dat", contenido=b"Z",
    )
    misc = next(f for f in folders if f.standard_code == "99")
    assert result["document"].folder_id == misc.id
    assert result["document"].clasificacion == "otro"


@pytest.mark.asyncio
async def test_intake_creates_tags(db):
    _, project_id = await _setup_tenant(db)
    svc = IDMSService()
    await svc.initialize_standard_folders(db, uuid.UUID(project_id))
    result = await svc.intake_document(
        db, project_id=uuid.UUID(project_id),
        nombre="doc.pdf", contenido=b"A",
        tags=[
            {"type": "measure_ens", "value": "op.acc.5"},
            {"type": "category", "value": "evidencia"},
        ],
    )
    assert len(result["tags"]) == 2


@pytest.mark.asyncio
async def test_intake_creates_version_1(db):
    _, project_id = await _setup_tenant(db)
    svc = IDMSService()
    await svc.initialize_standard_folders(db, uuid.UUID(project_id))
    result = await svc.intake_document(
        db, project_id=uuid.UUID(project_id),
        nombre="doc.pdf", contenido=b"first",
    )
    assert result["document"].version_actual == "1"
    assert result["version"].version == "1"


@pytest.mark.asyncio
async def test_intake_empty_content_rejected(db):
    _, project_id = await _setup_tenant(db)
    svc = IDMSService()
    with pytest.raises(IDMSError):
        await svc.intake_document(
            db, project_id=uuid.UUID(project_id),
            nombre="empty.txt", contenido=b"",
        )


# ─────────── Search ───────────

@pytest.mark.asyncio
async def test_search_by_name_ilike(db):
    _, project_id = await _setup_tenant(db)
    svc = IDMSService()
    await svc.initialize_standard_folders(db, uuid.UUID(project_id))
    await svc.intake_document(
        db, project_id=uuid.UUID(project_id),
        nombre="politica_acceso.pdf", contenido=b"A",
    )
    await svc.intake_document(
        db, project_id=uuid.UUID(project_id),
        nombre="procedimiento_backup.pdf", contenido=b"B",
    )
    results = await svc.search_documents(
        db, project_id=uuid.UUID(project_id), query="politica",
    )
    assert len(results) == 1
    assert "politica" in results[0].nombre.lower()


@pytest.mark.asyncio
async def test_search_by_clasificacion(db):
    _, project_id = await _setup_tenant(db)
    svc = IDMSService()
    await svc.initialize_standard_folders(db, uuid.UUID(project_id))
    await svc.intake_document(
        db, project_id=uuid.UUID(project_id),
        nombre="politica_x.pdf", contenido=b"P",
    )
    await svc.intake_document(
        db, project_id=uuid.UUID(project_id),
        nombre="procedimiento_x.pdf", contenido=b"Q",
    )
    results = await svc.search_documents(
        db, project_id=uuid.UUID(project_id), clasificacion="politica",
    )
    assert len(results) == 1


@pytest.mark.asyncio
async def test_search_by_measure_tag(db):
    _, project_id = await _setup_tenant(db)
    svc = IDMSService()
    await svc.initialize_standard_folders(db, uuid.UUID(project_id))
    await svc.intake_document(
        db, project_id=uuid.UUID(project_id),
        nombre="mfa_config.pdf", contenido=b"M",
        tags=[{"type": "measure_ens", "value": "op.acc.5"}],
    )
    await svc.intake_document(
        db, project_id=uuid.UUID(project_id),
        nombre="otro.pdf", contenido=b"N",
    )
    results = await svc.search_by_measure(
        db, project_id=uuid.UUID(project_id), measure_code="op.acc.5",
    )
    assert len(results) == 1
    assert "mfa" in results[0].nombre.lower()


# ─────────── Tags ───────────

@pytest.mark.asyncio
async def test_add_and_list_tags(db):
    _, project_id = await _setup_tenant(db)
    svc = IDMSService()
    await svc.initialize_standard_folders(db, uuid.UUID(project_id))
    result = await svc.intake_document(
        db, project_id=uuid.UUID(project_id),
        nombre="x.pdf", contenido=b"X",
    )
    doc = result["document"]
    await svc.add_tag(
        db, document_id=doc.id, project_id=uuid.UUID(project_id),
        tag_type="measure_ens", tag_value="org.1",
    )
    tags = await svc.get_tags(db, doc.id)
    assert len(tags) == 1
    assert tags[0].tag_value == "org.1"
    assert tags[0].confidence == 1.0
    assert tags[0].source == "manual"


@pytest.mark.asyncio
async def test_remove_tag(db):
    _, project_id = await _setup_tenant(db)
    svc = IDMSService()
    await svc.initialize_standard_folders(db, uuid.UUID(project_id))
    result = await svc.intake_document(
        db, project_id=uuid.UUID(project_id),
        nombre="x.pdf", contenido=b"X",
    )
    tag = await svc.add_tag(
        db, document_id=result["document"].id,
        project_id=uuid.UUID(project_id),
        tag_type="custom", tag_value="pendiente_revision",
    )
    await svc.remove_tag(db, tag.id)
    tags = await svc.get_tags(db, result["document"].id)
    assert len(tags) == 0


# ─────────── Versions ───────────

@pytest.mark.asyncio
async def test_create_version_increments(db):
    _, project_id = await _setup_tenant(db)
    svc = IDMSService()
    await svc.initialize_standard_folders(db, uuid.UUID(project_id))
    first = await svc.intake_document(
        db, project_id=uuid.UUID(project_id),
        nombre="x.pdf", contenido=b"v1",
    )
    result = await svc.create_version(
        db, document_id=first["document"].id, contenido=b"v2",
        descripcion_cambio="Update",
    )
    assert result["version"].version == "2"
    assert result["document"].version_actual == "2"
    versions = await svc.list_versions(db, first["document"].id)
    assert len(versions) == 2


# ─────────── Stats ───────────

@pytest.mark.asyncio
async def test_project_stats(db):
    _, project_id = await _setup_tenant(db)
    svc = IDMSService()
    await svc.initialize_standard_folders(db, uuid.UUID(project_id))
    await svc.intake_document(
        db, project_id=uuid.UUID(project_id),
        nombre="politica_x.pdf", contenido=b"P",
    )
    await svc.intake_document(
        db, project_id=uuid.UUID(project_id),
        nombre="informe_y.pdf", contenido=b"I",
    )
    stats = await svc.get_project_stats(db, uuid.UUID(project_id))
    assert stats["total_documents"] == 2
    assert stats["total_folders"] == 15
    assert "politica" in stats["by_clasificacion"]
    assert "informe" in stats["by_clasificacion"]


# ─────────── API ───────────

@pytest.mark.asyncio
async def test_api_list_standard_folders(async_client):
    r = await async_client.get(f"{BASE}/standard-folders")
    assert r.status_code == 200
    assert r.json()["count"] == 15


@pytest.mark.asyncio
async def test_api_initialize_folders(async_client, db):
    _, project_id = await setup_test_project(db)
    r = await async_client.post(
        f"{BASE}/projects/{project_id}/idms/folders/initialize"
    )
    assert r.status_code == 201
    assert r.json()["count"] == 15


@pytest.mark.asyncio
async def test_api_intake_document(async_client, db):
    _, project_id = await setup_test_project(db)
    await async_client.post(f"{BASE}/projects/{project_id}/idms/folders/initialize")
    contenido = b"%PDF-1.4\nHello IDMS"  # cabecera PDF válida (magic-bytes · FIX P2-4)
    r = await async_client.post(
        f"{BASE}/projects/{project_id}/idms/intake",
        json={
            "nombre": "politica_acceso.pdf",
            "contenido_base64": base64.b64encode(contenido).decode(),
            "tipo_mime": "application/pdf",
        },
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["duplicate"] is False
    assert data["document"]["clasificacion"] == "politica"


@pytest.mark.asyncio
async def test_api_search(async_client, db):
    _, project_id = await setup_test_project(db)
    await async_client.post(f"{BASE}/projects/{project_id}/idms/folders/initialize")
    await async_client.post(
        f"{BASE}/projects/{project_id}/idms/intake",
        json={
            "nombre": "mfa_policy.pdf",
            "contenido_base64": base64.b64encode(b"%PDF-1.4 M").decode(),
        },
    )
    r = await async_client.get(
        f"{BASE}/projects/{project_id}/idms/search?query=mfa"
    )
    assert r.status_code == 200
    assert len(r.json()["documents"]) == 1


@pytest.mark.asyncio
async def test_api_folder_tree(async_client, db):
    _, project_id = await setup_test_project(db)
    await async_client.post(f"{BASE}/projects/{project_id}/idms/folders/initialize")
    r = await async_client.get(f"{BASE}/projects/{project_id}/idms/folders/tree")
    assert r.status_code == 200
    assert len(r.json()["folders"]) == 15
