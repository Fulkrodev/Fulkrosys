"""Tests M20 Collaborative Workspace.

Cubre:
- Workspace lifecycle (create, get, archive, unique project_id)
- Files con SHA-256 + carpetas + árbol
- Feed append-only + read-state + unread count
- Chat append-only + threading
- Videocall state machine
- API endpoints
"""
from __future__ import annotations

import base64
import hashlib
import uuid
from datetime import datetime, timezone

import pytest

from backend.app.database import set_tenant_context
from backend.app.motors.m20_workspace.workspace_service import (
    WorkspaceError,
    WorkspaceService,
)
from backend.tests.conftest import setup_test_project


BASE = "/api/v1/workspace"


# ─────────── Helpers ───────────

async def _setup_tenant(db):
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db,
        client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
    )
    return client_id, project_id


async def _create_ws(db, project_id: str):
    return await WorkspaceService().create_workspace(
        db, project_id=uuid.UUID(project_id), nombre="Test WS",
    )


# ─────────── Workspace lifecycle ───────────

@pytest.mark.asyncio
async def test_create_workspace_for_project(db):
    _, project_id = await _setup_tenant(db)
    ws = await _create_ws(db, project_id)
    assert ws.estado == "active"
    assert str(ws.project_id) == project_id
    assert ws.config is not None
    assert ws.config["features"]["chat"] is True
    assert ws.carpeta_docs_path and project_id in ws.carpeta_docs_path


@pytest.mark.asyncio
async def test_create_workspace_unique_per_project(db):
    _, project_id = await _setup_tenant(db)
    await _create_ws(db, project_id)
    with pytest.raises(WorkspaceError):
        await _create_ws(db, project_id)


@pytest.mark.asyncio
async def test_get_workspace(db):
    _, project_id = await _setup_tenant(db)
    await _create_ws(db, project_id)
    ws = await WorkspaceService().get_workspace(db, uuid.UUID(project_id))
    assert ws is not None
    assert str(ws.project_id) == project_id


@pytest.mark.asyncio
async def test_archive_workspace_sets_caducidad(db):
    _, project_id = await _setup_tenant(db)
    await _create_ws(db, project_id)
    ws = await WorkspaceService().archive_workspace(
        db, uuid.UUID(project_id), retention_days=60,
    )
    assert ws.estado == "archived"
    assert ws.caducidad_at is not None
    delta = ws.caducidad_at - datetime.now(timezone.utc)
    assert 58 <= delta.days <= 61


# ─────────── Files ───────────

@pytest.mark.asyncio
async def test_upload_file_calculates_hash(db):
    _, project_id = await _setup_tenant(db)
    ws = await _create_ws(db, project_id)
    contenido = b"Test content for hashing"
    expected_hash = hashlib.sha256(contenido).hexdigest()

    wf = await WorkspaceService().upload_file(
        db, workspace_id=ws.id, project_id=uuid.UUID(project_id),
        nombre="test.txt", carpeta="/documentos/",
        contenido=contenido, tipo_mime="text/plain",
    )
    assert wf.hash_sha256 == expected_hash
    assert wf.tamano_bytes == len(contenido)
    assert wf.carpeta == "/documentos/"
    assert wf.estado == "active"
    assert wf.version == 1


@pytest.mark.asyncio
async def test_upload_empty_content_rejected(db):
    _, project_id = await _setup_tenant(db)
    ws = await _create_ws(db, project_id)
    with pytest.raises(WorkspaceError):
        await WorkspaceService().upload_file(
            db, workspace_id=ws.id, project_id=uuid.UUID(project_id),
            nombre="empty.txt", carpeta="/", contenido=b"",
        )


@pytest.mark.asyncio
async def test_upload_creates_feed_item_automatically(db):
    _, project_id = await _setup_tenant(db)
    ws = await _create_ws(db, project_id)
    svc = WorkspaceService()
    await svc.upload_file(
        db, workspace_id=ws.id, project_id=uuid.UUID(project_id),
        nombre="policy.pdf", carpeta="/politicas/",
        contenido=b"PDF content", tipo_mime="application/pdf",
    )
    feed = await svc.list_feed(db, ws.id)
    assert any(item.tipo == "documento_subido" for item in feed)


@pytest.mark.asyncio
async def test_list_files_filter_carpeta(db):
    _, project_id = await _setup_tenant(db)
    ws = await _create_ws(db, project_id)
    svc = WorkspaceService()
    await svc.upload_file(
        db, workspace_id=ws.id, project_id=uuid.UUID(project_id),
        nombre="a.txt", carpeta="/docs/", contenido=b"A",
    )
    await svc.upload_file(
        db, workspace_id=ws.id, project_id=uuid.UUID(project_id),
        nombre="b.txt", carpeta="/evidencias/", contenido=b"B",
    )
    docs = await svc.list_files(db, ws.id, carpeta="/docs/")
    assert len(docs) == 1
    assert docs[0].nombre == "a.txt"


@pytest.mark.asyncio
async def test_delete_file_soft(db):
    _, project_id = await _setup_tenant(db)
    ws = await _create_ws(db, project_id)
    svc = WorkspaceService()
    wf = await svc.upload_file(
        db, workspace_id=ws.id, project_id=uuid.UUID(project_id),
        nombre="x.txt", carpeta="/", contenido=b"x",
    )
    deleted = await svc.delete_file(db, wf.id)
    assert deleted.estado == "deleted"
    active = await svc.list_files(db, ws.id, estado="active")
    assert all(f.id != wf.id for f in active)


@pytest.mark.asyncio
async def test_folder_tree_nested_structure(db):
    _, project_id = await _setup_tenant(db)
    ws = await _create_ws(db, project_id)
    svc = WorkspaceService()
    await svc.upload_file(
        db, workspace_id=ws.id, project_id=uuid.UUID(project_id),
        nombre="p1.pdf", carpeta="/documentos/politicas/", contenido=b"P1",
    )
    await svc.upload_file(
        db, workspace_id=ws.id, project_id=uuid.UUID(project_id),
        nombre="p2.pdf", carpeta="/documentos/procedimientos/", contenido=b"P2",
    )
    tree = await svc.get_folder_tree(db, ws.id)
    assert tree["name"] == "/"
    assert len(tree["children"]) >= 1
    docs_node = next(c for c in tree["children"] if c["name"] == "documentos")
    child_names = {c["name"] for c in docs_node["children"]}
    assert "politicas" in child_names
    assert "procedimientos" in child_names


# ─────────── Feed ───────────

@pytest.mark.asyncio
async def test_add_feed_item_stores_metadata(db):
    _, project_id = await _setup_tenant(db)
    ws = await _create_ws(db, project_id)
    svc = WorkspaceService()
    item = await svc.add_feed_item(
        db, workspace_id=ws.id, project_id=uuid.UUID(project_id),
        tipo="hito_completado", titulo="Fase 1 completada",
        metadata={"entregable": "E-040", "link": "/dda"},
    )
    assert item.tipo == "hito_completado"
    assert item.item_metadata["entregable"] == "E-040"
    assert item.leido is False


@pytest.mark.asyncio
async def test_list_feed_ordered_desc(db):
    _, project_id = await _setup_tenant(db)
    ws = await _create_ws(db, project_id)
    svc = WorkspaceService()
    for i in range(3):
        await svc.add_feed_item(
            db, workspace_id=ws.id, project_id=uuid.UUID(project_id),
            tipo="comentario", titulo=f"Item {i}",
        )
    feed = await svc.list_feed(db, ws.id)
    assert len(feed) == 3
    titulos = {f.titulo for f in feed}
    assert titulos == {"Item 0", "Item 1", "Item 2"}
    # created_at no strict desc en misma transacción (mismo server now()),
    # basta con verificar orden monotónicamente no-creciente
    for a, b in zip(feed, feed[1:]):
        assert a.created_at >= b.created_at


@pytest.mark.asyncio
async def test_mark_read_updates_timestamp(db):
    _, project_id = await _setup_tenant(db)
    ws = await _create_ws(db, project_id)
    svc = WorkspaceService()
    item = await svc.add_feed_item(
        db, workspace_id=ws.id, project_id=uuid.UUID(project_id),
        tipo="alerta", titulo="Test",
    )
    read = await svc.mark_read(db, item.id)
    assert read.leido is True
    assert read.leido_at is not None


@pytest.mark.asyncio
async def test_unread_count(db):
    _, project_id = await _setup_tenant(db)
    ws = await _create_ws(db, project_id)
    svc = WorkspaceService()
    for _ in range(3):
        await svc.add_feed_item(
            db, workspace_id=ws.id, project_id=uuid.UUID(project_id),
            tipo="comentario", titulo="X",
        )
    count = await svc.get_unread_count(db, ws.id)
    assert count == 3


@pytest.mark.asyncio
async def test_feed_filter_by_tipo(db):
    _, project_id = await _setup_tenant(db)
    ws = await _create_ws(db, project_id)
    svc = WorkspaceService()
    await svc.add_feed_item(db, workspace_id=ws.id, project_id=uuid.UUID(project_id), tipo="comentario", titulo="A")
    await svc.add_feed_item(db, workspace_id=ws.id, project_id=uuid.UUID(project_id), tipo="alerta", titulo="B")
    alertas = await svc.list_feed(db, ws.id, tipo="alerta")
    assert len(alertas) == 1
    assert alertas[0].titulo == "B"


# ─────────── Chat ───────────

@pytest.mark.asyncio
async def test_send_message(db):
    _, project_id = await _setup_tenant(db)
    ws = await _create_ws(db, project_id)
    svc = WorkspaceService()
    msg = await svc.send_message(
        db, workspace_id=ws.id, project_id=uuid.UUID(project_id),
        autor="Marcos", autor_tipo="marcos", mensaje="Hola cliente",
    )
    assert msg.mensaje == "Hola cliente"
    assert msg.autor_tipo == "marcos"


@pytest.mark.asyncio
async def test_chat_empty_message_rejected(db):
    _, project_id = await _setup_tenant(db)
    ws = await _create_ws(db, project_id)
    svc = WorkspaceService()
    with pytest.raises(WorkspaceError):
        await svc.send_message(
            db, workspace_id=ws.id, project_id=uuid.UUID(project_id),
            autor="M", autor_tipo="marcos", mensaje="   ",
        )


@pytest.mark.asyncio
async def test_thread_original_plus_replies(db):
    _, project_id = await _setup_tenant(db)
    ws = await _create_ws(db, project_id)
    svc = WorkspaceService()
    original = await svc.send_message(
        db, workspace_id=ws.id, project_id=uuid.UUID(project_id),
        autor="Marcos", autor_tipo="marcos", mensaje="Pregunta",
    )
    reply = await svc.send_message(
        db, workspace_id=ws.id, project_id=uuid.UUID(project_id),
        autor="Cliente", autor_tipo="cliente", mensaje="Respuesta",
        respondiendo_a=original.id,
    )
    thread = await svc.get_thread(db, original.id)
    assert len(thread) == 2
    assert thread[0].id == original.id
    assert thread[1].id == reply.id


# ─────────── Videocall state machine ───────────

@pytest.mark.asyncio
async def test_videocall_lifecycle_solicitada_to_finalizada(db):
    _, project_id = await _setup_tenant(db)
    ws = await _create_ws(db, project_id)
    svc = WorkspaceService()
    s = await svc.request_videocall(
        db, workspace_id=ws.id, project_id=uuid.UUID(project_id),
        solicitada_por="Marcos", participantes=["Marcos", "Cliente"],
    )
    assert s.estado == "solicitada"

    s = await svc.accept_videocall(db, s.id)
    assert s.estado == "aceptada"
    assert s.aceptada_at is not None

    s = await svc.start_videocall(db, s.id)
    assert s.estado == "en_curso"
    assert s.livekit_room_name is not None  # TODO-M20-LIVEKIT placeholder

    s = await svc.end_videocall(db, s.id)
    assert s.estado == "finalizada"
    assert s.finalizada_at is not None
    assert s.duracion_minutos is not None and s.duracion_minutos >= 1


@pytest.mark.asyncio
async def test_videocall_invalid_transition(db):
    _, project_id = await _setup_tenant(db)
    ws = await _create_ws(db, project_id)
    svc = WorkspaceService()
    s = await svc.request_videocall(
        db, workspace_id=ws.id, project_id=uuid.UUID(project_id),
        solicitada_por="Marcos", participantes=[],
    )
    # solicitada → finalizada NO permitido (falta aceptar + iniciar)
    with pytest.raises(WorkspaceError):
        await svc.end_videocall(db, s.id)


# ─────────── Summary ───────────

@pytest.mark.asyncio
async def test_workspace_summary_counts(db):
    _, project_id = await _setup_tenant(db)
    ws = await _create_ws(db, project_id)
    svc = WorkspaceService()
    await svc.upload_file(
        db, workspace_id=ws.id, project_id=uuid.UUID(project_id),
        nombre="a.txt", carpeta="/", contenido=b"a",
    )
    await svc.add_feed_item(
        db, workspace_id=ws.id, project_id=uuid.UUID(project_id),
        tipo="comentario", titulo="x",
    )
    await svc.send_message(
        db, workspace_id=ws.id, project_id=uuid.UUID(project_id),
        autor="M", autor_tipo="marcos", mensaje="hola",
    )
    summary = await svc.get_workspace_summary(db, ws.id)
    assert summary["files_count"] == 1
    # upload genera 1 feed item + el que añadimos = 2
    assert summary["unread_feed_count"] >= 2
    assert summary["messages_count"] == 1


# ─────────── API ───────────

@pytest.mark.asyncio
async def test_api_create_workspace(async_client, db):
    _, project_id = await setup_test_project(db)
    r = await async_client.post(
        f"{BASE}/projects/{project_id}/workspace",
        json={"nombre": "Test"},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["estado"] == "active"
    assert data["nombre"] == "Test"


@pytest.mark.asyncio
async def test_api_upload_file_base64(async_client, db):
    _, project_id = await setup_test_project(db)
    await async_client.post(
        f"{BASE}/projects/{project_id}/workspace", json={"nombre": "WS"},
    )
    content = b"Hello API"
    r = await async_client.post(
        f"{BASE}/projects/{project_id}/workspace/files",
        json={
            "nombre": "hello.txt",
            "carpeta": "/test/",
            "contenido_base64": base64.b64encode(content).decode(),
            "tipo_mime": "text/plain",
        },
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["hash_sha256"] == hashlib.sha256(content).hexdigest()


@pytest.mark.asyncio
async def test_api_send_message_and_list(async_client, db):
    _, project_id = await setup_test_project(db)
    await async_client.post(
        f"{BASE}/projects/{project_id}/workspace", json={"nombre": "WS"},
    )
    r = await async_client.post(
        f"{BASE}/projects/{project_id}/workspace/chat",
        json={
            "autor": "Marcos", "autor_tipo": "marcos",
            "mensaje": "Hola desde API",
        },
    )
    assert r.status_code == 201, r.text

    r2 = await async_client.get(f"{BASE}/projects/{project_id}/workspace/chat")
    assert r2.status_code == 200
    assert len(r2.json()["messages"]) == 1


@pytest.mark.asyncio
async def test_api_videocall_lifecycle(async_client, db):
    _, project_id = await setup_test_project(db)
    await async_client.post(
        f"{BASE}/projects/{project_id}/workspace", json={"nombre": "WS"},
    )
    r = await async_client.post(
        f"{BASE}/projects/{project_id}/workspace/videocalls",
        json={"solicitada_por": "Marcos", "participantes": ["M", "C"]},
    )
    assert r.status_code == 201
    sid = r.json()["id"]

    r2 = await async_client.post(f"{BASE}/projects/{project_id}/workspace/videocalls/{sid}/accept")
    assert r2.status_code == 200
    assert r2.json()["estado"] == "aceptada"


# ─────────── Destroy lifecycle (Sesión 6) ───────────

from datetime import timedelta as _timedelta  # noqa: E402


@pytest.mark.asyncio
async def test_destroy_workspace_active_rejected(db):
    """Solo se puede destruir un workspace previamente archivado."""
    _, project_id = await _setup_tenant(db)
    await _create_ws(db, project_id)
    with pytest.raises(WorkspaceError, match="archivado"):
        await WorkspaceService().destroy_workspace(
            db, uuid.UUID(project_id),
        )


@pytest.mark.asyncio
async def test_destroy_workspace_caducidad_pending_rejected(db):
    """Sin force, no se puede destruir antes de que venza caducidad_at."""
    _, project_id = await _setup_tenant(db)
    await _create_ws(db, project_id)
    svc = WorkspaceService()
    await svc.archive_workspace(
        db, uuid.UUID(project_id), retention_days=90,
    )
    with pytest.raises(WorkspaceError, match="caduca|días"):
        await svc.destroy_workspace(db, uuid.UUID(project_id))


@pytest.mark.asyncio
async def test_destroy_workspace_caducidad_due_ok(db):
    """Si caducidad_at ya pasó, destrucción permitida sin force."""
    _, project_id = await _setup_tenant(db)
    await _create_ws(db, project_id)
    svc = WorkspaceService()
    ws = await svc.archive_workspace(
        db, uuid.UUID(project_id), retention_days=30,
    )
    # Forzamos caducidad en el pasado para simular plazo cumplido
    ws.caducidad_at = datetime.now(timezone.utc) - _timedelta(days=1)
    await db.flush()

    destroyed = await svc.destroy_workspace(db, uuid.UUID(project_id))
    assert destroyed.estado == "destroyed"


@pytest.mark.asyncio
async def test_destroy_workspace_force_skips_caducidad_check(db):
    """force=True permite destruir antes del plazo (decisión consultor)."""
    _, project_id = await _setup_tenant(db)
    await _create_ws(db, project_id)
    svc = WorkspaceService()
    await svc.archive_workspace(
        db, uuid.UUID(project_id), retention_days=365,
    )
    destroyed = await svc.destroy_workspace(
        db, uuid.UUID(project_id), force=True,
    )
    assert destroyed.estado == "destroyed"


@pytest.mark.asyncio
async def test_destroy_workspace_idempotent(db):
    """Llamar destroy dos veces no rompe; devuelve el mismo estado."""
    _, project_id = await _setup_tenant(db)
    await _create_ws(db, project_id)
    svc = WorkspaceService()
    await svc.archive_workspace(db, uuid.UUID(project_id))
    once = await svc.destroy_workspace(
        db, uuid.UUID(project_id), force=True,
    )
    twice = await svc.destroy_workspace(
        db, uuid.UUID(project_id), force=True,
    )
    assert once.estado == "destroyed"
    assert twice.estado == "destroyed"
    assert once.id == twice.id


@pytest.mark.asyncio
async def test_destroy_workspace_marks_files_destroyed(db):
    """Al destruir, todos los workspace_files pasan a estado 'destroyed'."""
    _, project_id = await _setup_tenant(db)
    ws = await _create_ws(db, project_id)
    svc = WorkspaceService()
    # Subimos 3 archivos
    for i in range(3):
        await svc.upload_file(
            db, workspace_id=ws.id, project_id=uuid.UUID(project_id),
            nombre=f"f{i}.txt", carpeta="/", contenido=f"data{i}".encode(),
        )
    # Archivar + destruir
    await svc.archive_workspace(db, uuid.UUID(project_id))
    await svc.destroy_workspace(
        db, uuid.UUID(project_id), force=True,
    )
    # Verificar todos los files ahora 'destroyed'
    files_destroyed = await svc.list_files(
        db, ws.id, estado="destroyed",
    )
    assert len(files_destroyed) == 3
    files_active = await svc.list_files(db, ws.id, estado="active")
    assert len(files_active) == 0


@pytest.mark.asyncio
async def test_destroy_workspace_blocks_uploads(db):
    """Después de destroyed, upload_file rechaza."""
    _, project_id = await _setup_tenant(db)
    ws = await _create_ws(db, project_id)
    svc = WorkspaceService()
    await svc.archive_workspace(db, uuid.UUID(project_id))
    await svc.destroy_workspace(
        db, uuid.UUID(project_id), force=True,
    )
    with pytest.raises(WorkspaceError, match="destruido"):
        await svc.upload_file(
            db, workspace_id=ws.id, project_id=uuid.UUID(project_id),
            nombre="late.txt", carpeta="/", contenido=b"too late",
        )


@pytest.mark.asyncio
async def test_destroy_workspace_blocks_chat(db):
    """Después de destroyed, send_message rechaza."""
    _, project_id = await _setup_tenant(db)
    ws = await _create_ws(db, project_id)
    svc = WorkspaceService()
    await svc.archive_workspace(db, uuid.UUID(project_id))
    await svc.destroy_workspace(
        db, uuid.UUID(project_id), force=True,
    )
    with pytest.raises(WorkspaceError, match="destruido"):
        await svc.send_message(
            db, workspace_id=ws.id, project_id=uuid.UUID(project_id),
            autor="Cliente", autor_tipo="cliente", mensaje="Hola",
        )


@pytest.mark.asyncio
async def test_destroy_workspace_blocks_feed(db):
    """Después de destroyed, add_feed_item rechaza."""
    _, project_id = await _setup_tenant(db)
    ws = await _create_ws(db, project_id)
    svc = WorkspaceService()
    await svc.archive_workspace(db, uuid.UUID(project_id))
    await svc.destroy_workspace(
        db, uuid.UUID(project_id), force=True,
    )
    with pytest.raises(WorkspaceError, match="destruido"):
        await svc.add_feed_item(
            db, workspace_id=ws.id, project_id=uuid.UUID(project_id),
            tipo="alerta", titulo="No debería entrar",
        )


@pytest.mark.asyncio
async def test_archive_destroyed_workspace_rejected(db):
    """No se puede re-archivar un workspace destruido."""
    _, project_id = await _setup_tenant(db)
    await _create_ws(db, project_id)
    svc = WorkspaceService()
    await svc.archive_workspace(db, uuid.UUID(project_id))
    await svc.destroy_workspace(
        db, uuid.UUID(project_id), force=True,
    )
    with pytest.raises(WorkspaceError, match="destruido"):
        await svc.archive_workspace(db, uuid.UUID(project_id))


@pytest.mark.asyncio
async def test_archived_workspace_blocks_writes(db):
    """Workspace archivado pasa a solo lectura: bloquea uploads/chat/feed."""
    _, project_id = await _setup_tenant(db)
    ws = await _create_ws(db, project_id)
    svc = WorkspaceService()
    await svc.archive_workspace(db, uuid.UUID(project_id))
    with pytest.raises(WorkspaceError, match="archivado"):
        await svc.upload_file(
            db, workspace_id=ws.id, project_id=uuid.UUID(project_id),
            nombre="x.txt", carpeta="/", contenido=b"x",
        )
    with pytest.raises(WorkspaceError, match="archivado"):
        await svc.send_message(
            db, workspace_id=ws.id, project_id=uuid.UUID(project_id),
            autor="C", autor_tipo="cliente", mensaje="late",
        )


@pytest.mark.asyncio
async def test_api_destroy_workspace_force(async_client, db):
    """Endpoint POST /workspace/destroy con force=true."""
    _, project_id = await setup_test_project(db)
    await async_client.post(
        f"{BASE}/projects/{project_id}/workspace", json={"nombre": "WS"},
    )
    # Archivar primero
    r1 = await async_client.post(
        f"{BASE}/projects/{project_id}/workspace/archive",
        json={"retention_days": 365},
    )
    assert r1.status_code == 200
    # Destruir con force
    r2 = await async_client.post(
        f"{BASE}/projects/{project_id}/workspace/destroy",
        json={"force": True},
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["estado"] == "destroyed"


@pytest.mark.asyncio
async def test_api_destroy_workspace_active_rejected(async_client, db):
    """Endpoint rechaza destruir un workspace que sigue activo."""
    _, project_id = await setup_test_project(db)
    await async_client.post(
        f"{BASE}/projects/{project_id}/workspace", json={"nombre": "WS"},
    )
    r = await async_client.post(
        f"{BASE}/projects/{project_id}/workspace/destroy",
        json={"force": True},
    )
    assert r.status_code == 400, r.text
