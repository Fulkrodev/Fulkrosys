"""Motor 20 - Collaborative Workspace API."""
from __future__ import annotations

import base64
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_marcos_or_client
from backend.app.database import get_db, set_tenant_context

from .workspace_service import WorkspaceError, WorkspaceService


router = APIRouter(
    prefix="/workspace",
    tags=["Motor 20 - Workspace"],
    # TODO-RBAC-PER-ENDPOINT-001 Cat C: cliente accede a su workspace
    # propio, Marcos también. Ambos pools válidos.
    dependencies=[Depends(require_marcos_or_client)],
)


async def _set_project_rls(project_id: uuid.UUID, db: AsyncSession):
    client_id = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
    )).scalar()
    if not client_id:
        raise HTTPException(status_code=404, detail="Project not found")
    await set_tenant_context(db, client_id=client_id, project_id=project_id)


# ─────────── Schemas ───────────

class CreateWorkspaceBody(BaseModel):
    nombre: Optional[str] = Field(None, max_length=200)
    config: Optional[dict] = None


class ArchiveBody(BaseModel):
    retention_days: int = Field(90, ge=1, le=3650)


class DestroyBody(BaseModel):
    force: bool = Field(
        False,
        description=(
            "Si True, destruye el workspace antes de que caducidad_at venza. "
            "Por defecto exige que el plazo de retención haya expirado."
        ),
    )


class UploadFileBody(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=300)
    carpeta: str = Field("/", max_length=500)
    contenido_base64: str = Field(..., min_length=1)
    tipo_mime: str = Field("application/octet-stream", max_length=100)
    subido_por: str = Field("marcos", max_length=200)


class AddFeedItemBody(BaseModel):
    tipo: str = Field(..., min_length=2, max_length=50)
    titulo: str = Field(..., min_length=1, max_length=300)
    descripcion: Optional[str] = None
    autor: str = Field("plataforma", max_length=100)
    metadata: Optional[dict] = None


class SendMessageBody(BaseModel):
    autor: str = Field(..., min_length=1, max_length=200)
    autor_tipo: str = Field("marcos", max_length=20)
    mensaje: str = Field(..., min_length=1)
    adjunto_file_id: Optional[uuid.UUID] = None
    respondiendo_a: Optional[uuid.UUID] = None


class RequestVideocallBody(BaseModel):
    solicitada_por: str = Field(..., min_length=1, max_length=100)
    participantes: list[str] = Field(default_factory=list)


# ─────────── Workspace lifecycle ───────────

@router.post(
    "/projects/{project_id}/workspace",
    status_code=status.HTTP_201_CREATED,
)
async def create_workspace(
    project_id: uuid.UUID,
    body: CreateWorkspaceBody,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        ws = await WorkspaceService().create_workspace(
            db, project_id=project_id, nombre=body.nombre, config=body.config,
        )
    except WorkspaceError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize_workspace(ws)


@router.get("/projects/{project_id}/workspace")
async def get_workspace(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    ws = await WorkspaceService().get_workspace(db, project_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return _serialize_workspace(ws)


@router.post("/projects/{project_id}/workspace/archive")
async def archive_workspace(
    project_id: uuid.UUID,
    body: ArchiveBody,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        ws = await WorkspaceService().archive_workspace(
            db, project_id, retention_days=body.retention_days,
        )
    except WorkspaceError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize_workspace(ws)


@router.post("/projects/{project_id}/workspace/destroy")
async def destroy_workspace(
    project_id: uuid.UUID,
    body: DestroyBody,
    db: AsyncSession = Depends(get_db),
):
    """Transición terminal: archived → destroyed.

    Solo permitido si el workspace ya está archivado y el plazo de
    retención (caducidad_at) ha vencido. Use ``force=true`` para
    destruir antes del plazo (queda trazado en audit_log).
    """
    await _set_project_rls(project_id, db)
    try:
        ws = await WorkspaceService().destroy_workspace(
            db, project_id, force=body.force,
        )
    except WorkspaceError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize_workspace(ws)


@router.get("/projects/{project_id}/workspace/summary")
async def workspace_summary(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    svc = WorkspaceService()
    ws = await svc.get_workspace(db, project_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {
        "workspace_id": str(ws.id),
        **await svc.get_workspace_summary(db, ws.id),
    }


# ─────────── Files ───────────

@router.post(
    "/projects/{project_id}/workspace/files",
    status_code=status.HTTP_201_CREATED,
)
async def upload_file(
    project_id: uuid.UUID,
    body: UploadFileBody,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    svc = WorkspaceService()
    ws = await svc.get_workspace(db, project_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    try:
        contenido = base64.b64decode(body.contenido_base64)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"contenido_base64 inválido: {exc}")
    try:
        wf = await svc.upload_file(
            db, workspace_id=ws.id, project_id=project_id,
            nombre=body.nombre, carpeta=body.carpeta,
            contenido=contenido, tipo_mime=body.tipo_mime,
            subido_por=body.subido_por,
        )
    except WorkspaceError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize_file(wf)


@router.get("/projects/{project_id}/workspace/files")
async def list_files(
    project_id: uuid.UUID,
    carpeta: Optional[str] = None,
    estado: Optional[str] = "active",
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    svc = WorkspaceService()
    ws = await svc.get_workspace(db, project_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    files = await svc.list_files(db, ws.id, carpeta=carpeta, estado=estado)
    return {"files": [_serialize_file(f) for f in files]}


@router.get("/projects/{project_id}/workspace/files/tree")
async def files_tree(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    svc = WorkspaceService()
    ws = await svc.get_workspace(db, project_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return await svc.get_folder_tree(db, ws.id)


@router.get("/projects/{project_id}/workspace/files/{file_id}")
async def get_file(
    project_id: uuid.UUID,
    file_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    wf = await WorkspaceService().get_file(db, file_id)
    if not wf:
        raise HTTPException(status_code=404, detail="File not found")
    return _serialize_file(wf)


@router.delete("/projects/{project_id}/workspace/files/{file_id}")
async def delete_file(
    project_id: uuid.UUID,
    file_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        wf = await WorkspaceService().delete_file(db, file_id)
    except WorkspaceError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await db.commit()
    return _serialize_file(wf)


# ─────────── Feed ───────────

@router.post(
    "/projects/{project_id}/workspace/feed",
    status_code=status.HTTP_201_CREATED,
)
async def add_feed_item(
    project_id: uuid.UUID,
    body: AddFeedItemBody,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    svc = WorkspaceService()
    ws = await svc.get_workspace(db, project_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    item = await svc.add_feed_item(
        db, workspace_id=ws.id, project_id=project_id,
        tipo=body.tipo, titulo=body.titulo, descripcion=body.descripcion,
        autor=body.autor, metadata=body.metadata,
    )
    await db.commit()
    return _serialize_feed_item(item)


@router.get("/projects/{project_id}/workspace/feed")
async def list_feed(
    project_id: uuid.UUID,
    tipo: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    svc = WorkspaceService()
    ws = await svc.get_workspace(db, project_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    items = await svc.list_feed(db, ws.id, tipo=tipo, limit=limit, offset=offset)
    return {"items": [_serialize_feed_item(i) for i in items]}


@router.patch("/projects/{project_id}/workspace/feed/{item_id}/read")
async def mark_feed_read(
    project_id: uuid.UUID,
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        item = await WorkspaceService().mark_read(db, item_id)
    except WorkspaceError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await db.commit()
    return _serialize_feed_item(item)


@router.get("/projects/{project_id}/workspace/feed/unread-count")
async def unread_count(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    svc = WorkspaceService()
    ws = await svc.get_workspace(db, project_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {"unread_count": await svc.get_unread_count(db, ws.id)}


# ─────────── Chat ───────────

@router.post(
    "/projects/{project_id}/workspace/chat",
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    project_id: uuid.UUID,
    body: SendMessageBody,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    svc = WorkspaceService()
    ws = await svc.get_workspace(db, project_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    try:
        msg = await svc.send_message(
            db, workspace_id=ws.id, project_id=project_id,
            autor=body.autor, autor_tipo=body.autor_tipo,
            mensaje=body.mensaje,
            adjunto_file_id=body.adjunto_file_id,
            respondiendo_a=body.respondiendo_a,
        )
    except WorkspaceError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize_message(msg)


@router.get("/projects/{project_id}/workspace/chat")
async def list_messages(
    project_id: uuid.UUID,
    limit: int = 50,
    before: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    svc = WorkspaceService()
    ws = await svc.get_workspace(db, project_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    messages = await svc.list_messages(db, ws.id, limit=limit, before=before)
    return {"messages": [_serialize_message(m) for m in messages]}


@router.get("/projects/{project_id}/workspace/chat/{message_id}/thread")
async def message_thread(
    project_id: uuid.UUID,
    message_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        thread = await WorkspaceService().get_thread(db, message_id)
    except WorkspaceError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"thread": [_serialize_message(m) for m in thread]}


# ─────────── Videocalls ───────────

@router.post(
    "/projects/{project_id}/workspace/videocalls",
    status_code=status.HTTP_201_CREATED,
)
async def request_videocall(
    project_id: uuid.UUID,
    body: RequestVideocallBody,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    svc = WorkspaceService()
    ws = await svc.get_workspace(db, project_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    session = await svc.request_videocall(
        db, workspace_id=ws.id, project_id=project_id,
        solicitada_por=body.solicitada_por, participantes=body.participantes,
    )
    await db.commit()
    return _serialize_videocall(session)


@router.post("/projects/{project_id}/workspace/videocalls/{session_id}/accept")
async def accept_videocall(
    project_id: uuid.UUID,
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        session = await WorkspaceService().accept_videocall(db, session_id)
    except WorkspaceError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize_videocall(session)


@router.post("/projects/{project_id}/workspace/videocalls/{session_id}/start")
async def start_videocall(
    project_id: uuid.UUID,
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        session = await WorkspaceService().start_videocall(db, session_id)
    except WorkspaceError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize_videocall(session)


@router.post("/projects/{project_id}/workspace/videocalls/{session_id}/end")
async def end_videocall(
    project_id: uuid.UUID,
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        session = await WorkspaceService().end_videocall(db, session_id)
    except WorkspaceError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize_videocall(session)


@router.get("/projects/{project_id}/workspace/videocalls")
async def list_videocalls(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    svc = WorkspaceService()
    ws = await svc.get_workspace(db, project_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    sessions = await svc.list_videocalls(db, ws.id)
    return {"videocalls": [_serialize_videocall(s) for s in sessions]}


# ─────────── Serializers ───────────

def _serialize_workspace(ws):
    return {
        "id": str(ws.id),
        "project_id": str(ws.project_id),
        "nombre": ws.nombre,
        "estado": ws.estado,
        "config": ws.config,
        "carpeta_docs_path": ws.carpeta_docs_path,
        "caducidad_at": ws.caducidad_at.isoformat() if ws.caducidad_at else None,
        "livekit_room_id": ws.livekit_room_id,
        "created_at": ws.created_at.isoformat() if ws.created_at else None,
    }


def _serialize_file(wf):
    return {
        "id": str(wf.id),
        "workspace_id": str(wf.workspace_id),
        "project_id": str(wf.project_id) if wf.project_id else None,
        "nombre": wf.nombre,
        "carpeta": wf.carpeta,
        "tipo_mime": wf.tipo_mime,
        "tamano_bytes": wf.tamano_bytes,
        "hash_sha256": wf.hash_sha256,
        "storage_path": wf.storage_path,
        "version": wf.version,
        "subido_por": wf.subido_por,
        "subido_at": wf.subido_at.isoformat() if wf.subido_at else None,
        "estado": wf.estado,
    }


def _serialize_feed_item(item):
    return {
        "id": str(item.id),
        "workspace_id": str(item.workspace_id),
        "project_id": str(item.project_id),
        "tipo": item.tipo,
        "titulo": item.titulo,
        "descripcion": item.descripcion,
        "metadata": item.item_metadata,
        "autor": item.autor,
        "leido": item.leido,
        "leido_at": item.leido_at.isoformat() if item.leido_at else None,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def _serialize_message(m):
    return {
        "id": str(m.id),
        "workspace_id": str(m.workspace_id),
        "autor": m.autor,
        "autor_tipo": m.autor_tipo,
        "mensaje": m.mensaje,
        "adjunto_file_id": str(m.adjunto_file_id) if m.adjunto_file_id else None,
        "respondiendo_a": str(m.respondiendo_a) if m.respondiendo_a else None,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


def _serialize_videocall(s):
    return {
        "id": str(s.id),
        "workspace_id": str(s.workspace_id),
        "project_id": str(s.project_id) if s.project_id else None,
        "estado": s.estado,
        "solicitada_por": s.solicitada_por,
        "participantes": s.participantes,
        "solicitada_at": s.solicitada_at.isoformat() if s.solicitada_at else None,
        "aceptada_at": s.aceptada_at.isoformat() if s.aceptada_at else None,
        "iniciada_at": s.iniciada_at.isoformat() if s.iniciada_at else None,
        "finalizada_at": s.finalizada_at.isoformat() if s.finalizada_at else None,
        "duracion_minutos": s.duracion_minutos,
        "livekit_room_name": s.livekit_room_name,
    }
