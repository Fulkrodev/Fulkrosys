"""Motor 24 - IDMS API."""
from __future__ import annotations

import base64
import contextvars
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_marcos_or_client
from backend.app.database import get_db, set_tenant_context

from .idms_service import (
    IDMSError,
    IDMSService,
    STANDARD_FOLDERS,
    VALID_ROLES,
)


# Ejecutable 8 OLA 0 (#5): contextvar para que _set_project_rls conozca al caller
# (lo fija la dependency de router _capture_subject) y enforce aislamiento por
# tenant SIN tocar las 27 firmas de endpoint. Se sobrescribe en CADA request
# (la dep corre antes del handler) → nunca queda valor stale.
_current_subject: contextvars.ContextVar = contextvars.ContextVar(
    "m24_current_subject", default=None,
)


async def _capture_subject(request: Request) -> None:
    """Router-level dep · stash el AuthSubject del request (request.state)."""
    _current_subject.set(getattr(request.state, "auth_subject", None))


def _authenticated_uploader(fallback: str = "marcos") -> str:
    """§1.4 audit-2026-06-15 · procedencia REAL del documento desde la identidad
    AUTENTICADA, NO desde body.subido_por (forjable: un ClientUser podía poner
    'marcos' y suplantar la autoría · rompe no-repudio/trazabilidad ENAC R6).
    marcos → 'marcos'; cliente → su email (identidad verificada del JWT)."""
    subject = _current_subject.get()
    if subject is None:
        return fallback
    if getattr(subject, "role_pool", None) == "marcos":
        return "marcos"
    email = getattr(subject, "email", None)
    return str(email) if email else fallback


router = APIRouter(
    prefix="/idms",
    tags=["Motor 24 - IDMS"],
    # TODO-RBAC-PER-ENDPOINT-001 Cat C: Marcos crea/gestiona, cliente firma
    # documentos. Ambos pools válidos · pero un ClientUser SOLO puede operar
    # sobre SU propio proyecto (#5 · enforce en _set_project_rls).
    dependencies=[
        Depends(require_marcos_or_client),
        Depends(_capture_subject),
    ],
)


async def _set_project_rls(project_id: uuid.UUID, db: AsyncSession):
    client_id = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
    )).scalar()
    if not client_id:
        raise HTTPException(status_code=404, detail="Project not found")
    # Ejecutable 8 OLA 0 (#5 · aislamiento cross-tenant): si el caller es un
    # ClientUser, su client_id DEBE coincidir con el owner del proyecto de la URL.
    # Antes el RLS se fijaba al owner del project de la URL sin mirar quién llamaba
    # → un cliente del tenant A podía leer/escribir documentos del tenant B pasando
    # el project_id de B. 404 (no 403) para no revelar existencia cross-tenant.
    subject = _current_subject.get()
    if subject is not None and getattr(subject, "role_pool", None) == "cliente":
        caller_client_id = getattr(subject.user, "client_id", None)
        if caller_client_id is None or str(caller_client_id) != str(client_id):
            raise HTTPException(status_code=404, detail="Project not found")
    await set_tenant_context(db, client_id=client_id, project_id=project_id)


async def _assert_document_in_project(
    document_id: uuid.UUID, project_id: uuid.UUID, db: AsyncSession,
) -> None:
    """B5 IDOR fix (per-recurso) · el documento DEBE pertenecer al proyecto de
    la URL. ``_set_project_rls`` ya verifica que el caller es dueño del
    project_id de la URL, pero las queries del servicio (get_document, get_tags,
    list_versions, transiciones, permisos…) buscan por ``document_id`` SIN
    filtrar project_id y bajo el pool cliente RLS está OFF → un cliente podía
    pasar SU project_id + el ``document_id`` de otro tenant y leer/mutar el
    documento ajeno. Este guard ata el recurso al proyecto ya verificado.
    404 (no revela existencia cross-tenant). Idéntico contrato que el filtro que
    ya aplican ``set_document_visibility`` / ``download_document``.
    """
    row = (await db.execute(
        text(
            "SELECT 1 FROM documents "
            "WHERE id = :did AND project_id = :pid AND deleted_at IS NULL"
        ),
        {"did": str(document_id), "pid": str(project_id)},
    )).scalar()
    if row is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado")


# ─────────── Schemas ───────────

class CreateFolderBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    parent_folder_id: Optional[uuid.UUID] = None
    virtual_path: Optional[str] = None


class IntakeTag(BaseModel):
    type: str = Field(..., min_length=2, max_length=30)
    value: str = Field(..., min_length=1, max_length=100)
    source: str = Field("manual", max_length=20)
    confidence: float = Field(1.0, ge=0.0, le=1.0)


class IntakeBody(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=255)
    contenido_base64: str = Field(..., min_length=1)
    tipo_mime: str = Field("application/octet-stream", max_length=100)
    folder_id: Optional[uuid.UUID] = None
    clasificacion: Optional[str] = Field(None, max_length=30)
    tags: Optional[list[IntakeTag]] = None
    # §1.4 · IGNORADO: la procedencia se deriva de la identidad autenticada
    # (_authenticated_uploader) · se conserva por compat de callers pero NO se usa.
    subido_por: str = Field("marcos", max_length=100)
    full_text_content: Optional[str] = None


class AddTagBody(BaseModel):
    tag_type: str = Field(..., min_length=2, max_length=30)
    tag_value: str = Field(..., min_length=1, max_length=100)
    source: str = Field("manual", max_length=20)
    confidence: float = Field(1.0, ge=0.0, le=1.0)


class CreateVersionBody(BaseModel):
    contenido_base64: str = Field(..., min_length=1)
    descripcion_cambio: Optional[str] = None
    subido_por: str = Field("marcos", max_length=100)


# ─────────── Catálogo ───────────

@router.get("/standard-folders")
async def list_standard_folders():
    return {"folders": STANDARD_FOLDERS, "count": len(STANDARD_FOLDERS)}


# ─────────── Folders ───────────

@router.post(
    "/projects/{project_id}/idms/folders/initialize",
    status_code=status.HTTP_201_CREATED,
)
async def initialize_folders(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    folders = await IDMSService().initialize_standard_folders(db, project_id)
    await db.commit()
    return {
        "folders": [_serialize_folder(f) for f in folders],
        "count": len(folders),
    }


@router.post(
    "/projects/{project_id}/idms/folders",
    status_code=status.HTTP_201_CREATED,
)
async def create_folder(
    project_id: uuid.UUID,
    body: CreateFolderBody,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        folder = await IDMSService().create_folder(
            db, project_id=project_id,
            name=body.name,
            parent_folder_id=body.parent_folder_id,
            virtual_path=body.virtual_path,
        )
    except IDMSError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize_folder(folder)


@router.get("/projects/{project_id}/idms/folders/tree")
async def folder_tree(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    return await IDMSService().get_folder_tree(db, project_id)


@router.post("/projects/{project_id}/idms/documents/{document_id}/move")
async def move_document(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    folder_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    await _assert_document_in_project(document_id, project_id, db)
    try:
        doc = await IDMSService().move_document_to_folder(db, document_id, folder_id)
    except IDMSError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize_document(doc)


class SetVisibilityBody(BaseModel):
    interno: bool


@router.post("/projects/{project_id}/idms/documents/{document_id}/visibility")
async def set_document_visibility(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    body: SetVisibilityBody,
    db: AsyncSession = Depends(get_db),
):
    """Marca/desmarca un documento como SOLO-INTERNO (no visible al cliente).

    Flag de visibilidad: con ``interno=true`` el portal cliente deja de mostrar
    el documento (borradores / notas internas del consultor). Operación de
    gestión IDMS (admin) · acotada por _set_project_rls al proyecto.
    """
    await _set_project_rls(project_id, db)
    res = await db.execute(
        text(
            "UPDATE documents SET interno = :v "
            "WHERE id = :did AND project_id = :pid AND deleted_at IS NULL "
            "RETURNING id"
        ),
        {"v": body.interno, "did": str(document_id), "pid": str(project_id)},
    )
    if res.first() is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    await db.commit()
    return {"document_id": str(document_id), "interno": body.interno}


# ─────────── Intake ───────────

@router.post(
    "/projects/{project_id}/idms/intake",
    status_code=status.HTTP_201_CREATED,
)
async def intake_document(
    project_id: uuid.UUID,
    body: IntakeBody,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        contenido = base64.b64decode(body.contenido_base64)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"contenido_base64 inválido: {exc}")
    # FIX P2-4: validar magic-bytes (el contenido podría estar suplantado · un
    # ejecutable renombrado a .pdf). Mismo guard que m07/m21.
    from pathlib import Path as _Path

    from backend.app.core.upload_validation import (
        MagicByteMismatch,
        validate_magic_bytes,
    )
    try:
        validate_magic_bytes(contenido, _Path(body.nombre or "").suffix)
    except MagicByteMismatch as exc:
        raise HTTPException(status_code=415, detail=str(exc))
    try:
        result = await IDMSService().intake_document(
            db, project_id=project_id,
            nombre=body.nombre, contenido=contenido,
            tipo_mime=body.tipo_mime,
            folder_id=body.folder_id,
            clasificacion=body.clasificacion,
            tags=[t.model_dump() for t in (body.tags or [])],
            subido_por=_authenticated_uploader(),  # §1.4 · no body.subido_por (forjable)
            full_text_content=body.full_text_content,
        )
    except IDMSError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    # FIX P2-3 · realtime gestor documental: el cliente ve el documento nuevo sin
    # refrescar (best-effort post-commit · NO bloquea la respuesta). Sólo emitir
    # si NO fue un duplicado (no se creó fila nueva).
    if not result["duplicate"]:
        from backend.app.core.document_events import notify_document_uploaded

        await notify_document_uploaded(
            project_id=project_id,
            document_id=result["document"].id,
            nombre=getattr(result["document"], "nombre", None),
            source="admin",
            interno=bool(getattr(result["document"], "interno", False)),
        )
    return {
        "document": _serialize_document(result["document"]),
        "duplicate": result["duplicate"],
        "content_hash": result["content_hash"],
        "tags": [_serialize_tag(t) for t in (result["tags"] or [])],
    }


# ─────────── Search ───────────

@router.get("/projects/{project_id}/idms/search")
async def search(
    project_id: uuid.UUID,
    query: Optional[str] = None,
    folder_id: Optional[uuid.UUID] = None,
    clasificacion: Optional[str] = None,
    tag_type: Optional[str] = None,
    tag_value: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    docs = await IDMSService().search_documents(
        db, project_id=project_id,
        query=query, folder_id=folder_id, clasificacion=clasificacion,
        tag_type=tag_type, tag_value=tag_value, limit=limit,
    )
    return {"documents": [_serialize_document(d) for d in docs]}


@router.get("/projects/{project_id}/idms/search/by-measure/{measure_code}")
async def search_by_measure(
    project_id: uuid.UUID,
    measure_code: str,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    docs = await IDMSService().search_by_measure(db, project_id, measure_code)
    return {
        "measure_code": measure_code,
        "documents": [_serialize_document(d) for d in docs],
    }


# ─────────── Tags ───────────

@router.post(
    "/projects/{project_id}/idms/documents/{document_id}/tags",
    status_code=status.HTTP_201_CREATED,
)
async def add_tag(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    body: AddTagBody,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    await _assert_document_in_project(document_id, project_id, db)
    tag = await IDMSService().add_tag(
        db, document_id=document_id, project_id=project_id,
        tag_type=body.tag_type, tag_value=body.tag_value,
        source=body.source, confidence=body.confidence,
    )
    await db.commit()
    return _serialize_tag(tag)


@router.delete("/projects/{project_id}/idms/documents/{document_id}/tags/{tag_id}")
async def remove_tag(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    tag_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    await _assert_document_in_project(document_id, project_id, db)
    try:
        await IDMSService().remove_tag(
            db, tag_id, expected_document_id=document_id,
        )
    except IDMSError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await db.commit()
    return {"ok": True}


@router.get("/projects/{project_id}/idms/documents/{document_id}/tags")
async def list_tags(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    await _assert_document_in_project(document_id, project_id, db)
    tags = await IDMSService().get_tags(db, document_id)
    return {"tags": [_serialize_tag(t) for t in tags]}


# ─────────── Versions ───────────

@router.post(
    "/projects/{project_id}/idms/documents/{document_id}/versions",
    status_code=status.HTTP_201_CREATED,
)
async def create_version(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    body: CreateVersionBody,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        contenido = base64.b64decode(body.contenido_base64)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"contenido_base64 inválido: {exc}")
    try:
        await _assert_document_in_project(document_id, project_id, db)
        result = await IDMSService().create_version(
            db, document_id=document_id,
            contenido=contenido,
            descripcion_cambio=body.descripcion_cambio,
            subido_por=_authenticated_uploader(),  # §1.4 · no body.subido_por (forjable)
        )
    except IDMSError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await db.commit()
    return {
        "document": _serialize_document(result["document"]),
        "version": _serialize_version(result["version"]),
    }


@router.get("/projects/{project_id}/idms/documents/{document_id}/versions")
async def list_versions(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    await _assert_document_in_project(document_id, project_id, db)
    versions = await IDMSService().list_versions(db, document_id)
    return {"versions": [_serialize_version(v) for v in versions]}


# ─────────── Documents wrapper ───────────

@router.get("/projects/{project_id}/idms/documents")
async def list_documents(
    project_id: uuid.UUID,
    folder_id: Optional[uuid.UUID] = None,
    clasificacion: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    docs = await IDMSService().list_documents(
        db, project_id=project_id, folder_id=folder_id, clasificacion=clasificacion,
    )
    return {"documents": [_serialize_document(d) for d in docs]}


# NOTA: las rutas ESTÁTICAS (/documents/expiring, /documents/expired) DEBEN
# declararse ANTES que la dinámica /documents/{document_id}; si no, FastAPI casa
# "expiring"/"expired" contra {document_id} (UUID) → 422 y nunca las alcanza.
@router.get("/projects/{project_id}/idms/documents/expiring")
async def list_documents_expiring(
    project_id: uuid.UUID,
    days: int = 30,
    db: AsyncSession = Depends(get_db),
):
    """Documentos activos cuya expires_at cae en los proximos N dias."""
    await _set_project_rls(project_id, db)
    if days < 0 or days > 365:
        raise HTTPException(
            status_code=400, detail="days debe estar en rango [0, 365]",
        )
    docs = await IDMSService().list_expiring_soon(db, project_id, days_ahead=days)
    return {
        "project_id": str(project_id),
        "days_ahead": days,
        "count": len(docs),
        "documents": [_serialize_document(d) for d in docs],
    }


@router.get("/projects/{project_id}/idms/documents/expired")
async def list_documents_expired(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Documentos activos cuya expires_at ya paso (alerta inmediata)."""
    await _set_project_rls(project_id, db)
    docs = await IDMSService().list_expired(db, project_id)
    return {
        "project_id": str(project_id),
        "count": len(docs),
        "documents": [_serialize_document(d) for d in docs],
    }


@router.get("/projects/{project_id}/idms/documents/{document_id}")
async def get_document(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    await _assert_document_in_project(document_id, project_id, db)
    svc = IDMSService()
    doc = await svc.get_document(db, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    tags = await svc.get_tags(db, document_id)
    versions = await svc.list_versions(db, document_id)
    folder = await svc.get_folder(db, doc.folder_id) if doc.folder_id else None
    return {
        **_serialize_document(doc),
        "tags": [_serialize_tag(t) for t in tags],
        "versions": [_serialize_version(v) for v in versions],
        "folder": _serialize_folder(folder) if folder else None,
    }


# ─────────── Download (#32 · FRENTE B · gestor admin) ───────────

@router.get("/projects/{project_id}/idms/documents/{document_id}/download")
async def download_document(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """#32 (FRENTE B): descarga del binario IDMS desde el gestor admin.

    El gestor documental admin no tenía endpoint de descarga (solo listado).
    Resuelve el ``storage_path`` canónico ``minio://`` (preferido · durable)
    con fallback a las rutas locales ``pdf_path``/``docx_path`` (dev mismo host).
    RLS por proyecto (#5 · ``_set_project_rls``). Mismo contrato de resolución
    que el portal cliente (``portal_document_download``) · OPS-026 DRY.
    """
    from io import BytesIO

    from fastapi.responses import StreamingResponse

    await _set_project_rls(project_id, db)
    res = await db.execute(
        text(
            "SELECT d.nombre, d.template_codigo, d.docx_path, d.pdf_path, "
            "       d.storage_path, d.deleted_at "
            "FROM documents d "
            "WHERE d.id = :did AND d.project_id = :pid"
        ),
        {"did": str(document_id), "pid": str(project_id)},
    )
    row = res.mappings().first()
    if row is None or row["deleted_at"] is not None:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    file_path = row["storage_path"] or row["pdf_path"] or row["docx_path"]
    if not file_path:
        raise HTTPException(
            status_code=404,
            detail="Documento sin archivo asociado · pendiente generación",
        )

    if file_path.startswith("minio://"):
        from backend.app.core.storage.minio_client import get_object

        rest = file_path[len("minio://"):]
        bucket, _, key = rest.partition("/")
        try:
            file_bytes = get_object(bucket, key)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=502, detail=f"MinIO unreachable: {exc}"
            )
    else:
        # Fallback local (dev · mismo host). En prod los binarios viven en MinIO.
        from pathlib import Path as _Path

        local = _Path(file_path)
        if not local.exists():
            raise HTTPException(
                status_code=503,
                detail="Archivo no disponible en este entorno (local://).",
            )
        file_bytes = local.read_bytes()

    is_pdf = bool(row["pdf_path"]) or file_path.endswith(".pdf")
    is_docx = bool(row["docx_path"]) or file_path.endswith(".docx")
    ext = ".pdf" if is_pdf else (".docx" if is_docx else ".bin")
    media_type = (
        "application/pdf" if ext == ".pdf"
        else "application/vnd.openxmlformats-officedocument."
             "wordprocessingml.document" if ext == ".docx"
        else "application/octet-stream"
    )
    base_name = (
        row["template_codigo"] or row["nombre"] or f"document_{document_id}"
    )
    safe = base_name.replace("/", "_").replace(" ", "_")
    return StreamingResponse(
        BytesIO(file_bytes),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{safe}{ext}"',
        },
    )


# ─────────── Stats ───────────

@router.get("/projects/{project_id}/idms/stats")
async def project_stats(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    return await IDMSService().get_project_stats(db, project_id)


# ─────────── Serializers ───────────

def _serialize_folder(f):
    if not f:
        return None
    return {
        "id": str(f.id),
        "project_id": str(f.project_id) if f.project_id else None,
        "parent_folder_id": str(f.parent_folder_id) if f.parent_folder_id else None,
        "name": f.name,
        "virtual_path": f.virtual_path,
        "is_standard": f.is_standard,
        "standard_code": f.standard_code,
        "custom_order": f.custom_order,
    }


def _serialize_tag(t):
    return {
        "id": str(t.id),
        "document_id": str(t.document_id),
        "tag_type": t.tag_type,
        "tag_value": t.tag_value,
        "confidence": float(t.confidence),
        "source": t.source,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


def _serialize_version(v):
    return {
        "id": str(v.id),
        "document_id": str(v.document_id),
        "version": v.version,
        "hash_sha256": v.hash_sha256,
        "contenido_path": v.contenido_path,
        "generado_por": v.generado_por,
        "generado_at": v.generado_at.isoformat() if v.generado_at else None,
    }


def _serialize_document(d) -> dict:
    return {
        "id": str(d.id),
        "project_id": str(d.project_id),
        "folder_id": str(d.folder_id) if d.folder_id else None,
        "nombre": d.nombre,
        "tipo": d.tipo,
        # FIX (bug-hunt 2026-06-14): estos 3 campos los perdía el serializador
        # porque había DOS def _serialize_document y la 2ª (esta) los omitía →
        # el gestor documental admin mostraba en blanco el código E-XXX, la
        # versión y la ruta. El frontend (lib/api/idms.ts) los declara/consume.
        "template_codigo": d.template_codigo,
        "storage_path": d.storage_path,
        "version_actual": d.version_actual,
        "clasificacion": d.clasificacion,
        "estado": d.estado,
        "approved_by_user_id": (
            str(d.approved_by_user_id) if d.approved_by_user_id else None
        ),
        "approved_at": d.approved_at.isoformat() if d.approved_at else None,
        "expires_at": d.expires_at.isoformat() if d.expires_at else None,
        "review_period_months": d.review_period_months,
        "content_hash": d.content_hash,
        "file_size_bytes": d.file_size_bytes,
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }


def _serialize_permission(p) -> dict:
    return {
        "id": str(p.id),
        "document_id": str(p.document_id),
        "user_id": str(p.user_id),
        "role": p.role,
        "granted_by_user_id": (
            str(p.granted_by_user_id) if p.granted_by_user_id else None
        ),
        "granted_at": p.granted_at.isoformat() if p.granted_at else None,
    }


# ═══════════════════════════════════════════════════════════════
# Workflow status endpoints (Sesion 9 Paso 3.1)
# ═══════════════════════════════════════════════════════════════


@router.post(
    "/projects/{project_id}/idms/documents/{document_id}/submit-review",
    status_code=status.HTTP_200_OK,
)
async def submit_document_for_review(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Transicion draft -> review."""
    await _set_project_rls(project_id, db)
    try:
        await _assert_document_in_project(document_id, project_id, db)
        doc = await IDMSService().submit_for_review(db, document_id)
    except IDMSError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize_document(doc)


class ApproveBody(BaseModel):
    approver_user_id: uuid.UUID


@router.post(
    "/projects/{project_id}/idms/documents/{document_id}/approve",
    status_code=status.HTTP_200_OK,
)
async def approve_document_endpoint(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    body: ApproveBody,
    db: AsyncSession = Depends(get_db),
):
    """Transicion review -> approved. Persiste approver + timestamp."""
    await _set_project_rls(project_id, db)
    try:
        await _assert_document_in_project(document_id, project_id, db)
        doc = await IDMSService().approve_document(
            db, document_id, body.approver_user_id,
        )
    except IDMSError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize_document(doc)


@router.post(
    "/projects/{project_id}/idms/documents/{document_id}/archive",
    status_code=status.HTTP_200_OK,
)
async def archive_document_endpoint(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Transicion a archived (caducidad, reemplazo)."""
    await _set_project_rls(project_id, db)
    try:
        await _assert_document_in_project(document_id, project_id, db)
        doc = await IDMSService().archive_document(db, document_id)
    except IDMSError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize_document(doc)


@router.post(
    "/projects/{project_id}/idms/documents/{document_id}/deprecate",
    status_code=status.HTTP_200_OK,
)
async def deprecate_document_endpoint(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Transicion approved -> deprecated (nueva version lo reemplaza)."""
    await _set_project_rls(project_id, db)
    try:
        await _assert_document_in_project(document_id, project_id, db)
        doc = await IDMSService().deprecate_document(db, document_id)
    except IDMSError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize_document(doc)


# ═══════════════════════════════════════════════════════════════
# Expiration endpoints (Sesion 9 Paso 3.1)
# ═══════════════════════════════════════════════════════════════


class SetExpirationBody(BaseModel):
    expires_at: Optional[datetime] = None
    review_period_months: Optional[int] = Field(None, gt=0, le=120)


@router.post(
    "/projects/{project_id}/idms/documents/{document_id}/set-expiration",
    status_code=status.HTTP_200_OK,
)
async def set_document_expiration(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    body: SetExpirationBody,
    db: AsyncSession = Depends(get_db),
):
    """Establece expires_at + review_period_months."""
    await _set_project_rls(project_id, db)
    try:
        await _assert_document_in_project(document_id, project_id, db)
        doc = await IDMSService().set_expiration(
            db, document_id,
            expires_at=body.expires_at,
            review_period_months=body.review_period_months,
        )
    except IDMSError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize_document(doc)


@router.post("/projects/{project_id}/idms/documents/auto-deprecate-expired")
async def auto_deprecate_expired_endpoint(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Marca como deprecated los documentos expired. Cron candidate."""
    await _set_project_rls(project_id, db)
    deprecated = await IDMSService().auto_deprecate_expired(db, project_id)
    await db.commit()
    return {
        "project_id": str(project_id),
        "deprecated_count": len(deprecated),
        "documents": [_serialize_document(d) for d in deprecated],
    }


# ═══════════════════════════════════════════════════════════════
# Permissions endpoints (Sesion 9 Paso 3.1)
# ═══════════════════════════════════════════════════════════════


class GrantPermissionBody(BaseModel):
    user_id: uuid.UUID
    role: str = Field(..., description=f"Uno de: {VALID_ROLES}")
    granted_by_user_id: Optional[uuid.UUID] = None


@router.post(
    "/projects/{project_id}/idms/documents/{document_id}/permissions",
    status_code=status.HTTP_201_CREATED,
)
async def grant_permission_endpoint(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    body: GrantPermissionBody,
    db: AsyncSession = Depends(get_db),
):
    """Concede permiso granular sobre un documento."""
    await _set_project_rls(project_id, db)
    try:
        await _assert_document_in_project(document_id, project_id, db)
        perm = await IDMSService().grant_permission(
            db,
            document_id=document_id,
            user_id=body.user_id,
            role=body.role,
            granted_by_user_id=body.granted_by_user_id,
        )
    except IDMSError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize_permission(perm)


@router.delete(
    "/projects/{project_id}/idms/documents/{document_id}/permissions/{user_id}",
    status_code=status.HTTP_200_OK,
)
async def revoke_permission_endpoint(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Revoca permiso granular (soft delete)."""
    await _set_project_rls(project_id, db)
    await _assert_document_in_project(document_id, project_id, db)
    removed = await IDMSService().revoke_permission(db, document_id, user_id)
    await db.commit()
    return {"removed": removed}


@router.get(
    "/projects/{project_id}/idms/documents/{document_id}/permissions",
)
async def list_permissions_endpoint(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Lista permisos activos sobre el documento."""
    await _set_project_rls(project_id, db)
    await _assert_document_in_project(document_id, project_id, db)
    perms = await IDMSService().list_permissions(db, document_id)
    return {
        "document_id": str(document_id),
        "count": len(perms),
        "permissions": [_serialize_permission(p) for p in perms],
    }
