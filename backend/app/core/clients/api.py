"""Core — Clients & Projects: REST API endpoints.

Auth via global dep ``authenticate_request`` (ADR-021, sub-fase 4.D).
RBAC owner-only via ``Depends(require_owner)`` aplicado en TODOS los
endpoints — Marcos es el único role con acceso a panel ``/admin/clients``.
"""
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.core.clients.schemas import (
    AuditLogPage,
    ClientCreate,
    ClientDetail,
    ClientOut,
    ClientUpdate,
    ProjectCreate,
    ProjectOut,
)
from backend.app.core.clients.service import (
    ClientNotFoundError,
    get_client_audit_log,
    get_client_by_id,
    resume_client,
    suspend_client,
    update_client,
)
from backend.app.core.storage.minio_client import BUCKET_DOCUMENTS, put_object
from backend.app.database import get_db
from backend.app.models.core import Client, Project

router = APIRouter(
    prefix="/clients",
    tags=["Core - Clients & Projects"],
    dependencies=[Depends(require_owner)],
)

ACCEPTED_LOGO_MIME = {"image/png", "image/jpeg", "image/svg+xml", "image/webp"}
MAX_LOGO_BYTES = 2 * 1024 * 1024  # 2 MB


# ================================================================
# ENDPOINT 1: Create client
# ================================================================

@router.post(
    "",
    response_model=ClientOut,
    status_code=201,
)
async def create_client(
    body: ClientCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new client."""
    existing = await db.execute(
        text("SELECT id FROM clients WHERE cif = :cif"),
        {"cif": body.cif},
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"Client with CIF {body.cif} already exists",
        )

    client = Client(
        nombre=body.nombre,
        cif=body.cif,
        sector=body.sector,
        contacto_email=body.contacto_email,
        contacto_telefono=body.contacto_telefono,
    )
    db.add(client)
    await db.commit()
    await db.refresh(client)
    return client


# ================================================================
# ENDPOINT 2: List clients
# ================================================================

@router.get(
    "",
    response_model=list[ClientOut],
)
async def list_clients(
    db: AsyncSession = Depends(get_db),
):
    """List all clients (owner view) con su project_id resuelto (1 proyecto/cliente).

    CRITICAL #1: el selector navega con project_id, NO con client.id. Elevamos a
    rol fulkro para que el subquery sobre projects (tabla con RLS) vea la fila.
    """
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    proj_subq = (
        select(Project.id)
        .where(Project.client_id == Client.id, Project.deleted_at.is_(None))
        .order_by(Project.created_at.desc())
        .limit(1)
        .correlate(Client)
        .scalar_subquery()
    )
    result = await db.execute(
        select(Client, proj_subq.label("project_id")).order_by(
            Client.created_at.desc()
        )
    )
    out: list[ClientOut] = []
    for client, project_id in result.all():
        item = ClientOut.model_validate(client)
        item.project_id = project_id
        out.append(item)
    return out


# ================================================================
# ENDPOINT 3: Get client detail (sub-fase 5.A FASE 5)
# ================================================================

@router.get(
    "/{client_id}",
    response_model=ClientDetail,
)
async def get_client_detail(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Detalle cliente + métricas agregadas para panel /admin/clients/{id}."""
    try:
        return await get_client_by_id(db, client_id)
    except ClientNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ================================================================
# ENDPOINT 4: Update client (sub-fase 5.A FASE 5)
# ================================================================

@router.patch(
    "/{client_id}",
    response_model=ClientOut,
)
async def patch_client(
    client_id: uuid.UUID,
    body: ClientUpdate,
    db: AsyncSession = Depends(get_db),
):
    """PATCH partial — solo los campos presentes en el body se aplican."""
    try:
        client = await update_client(
            db,
            client_id,
            body.model_dump(exclude_unset=True),
        )
        await db.commit()
        await db.refresh(client)
        return client
    except ClientNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ================================================================
# ENDPOINT 5: Suspend client (soft delete, sub-fase 5.A FASE 5)
# ================================================================

@router.post(
    "/{client_id}/suspend",
    response_model=ClientDetail,
)
async def suspend_client_endpoint(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Suspend cliente: SET deleted_at = now() (idempotent)."""
    try:
        await suspend_client(db, client_id)
        await db.commit()
        return await get_client_by_id(db, client_id)
    except ClientNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ================================================================
# ENDPOINT 6: Resume client (sub-fase 5.A FASE 5)
# ================================================================

@router.post(
    "/{client_id}/resume",
    response_model=ClientDetail,
)
async def resume_client_endpoint(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Resume cliente suspendido: SET deleted_at = NULL."""
    try:
        await resume_client(db, client_id)
        await db.commit()
        return await get_client_by_id(db, client_id)
    except ClientNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ================================================================
# ENDPOINT 7: Audit log filtered (sub-fase 5.A FASE 5)
# ================================================================

@router.get(
    "/{client_id}/audit",
    response_model=AuditLogPage,
)
async def get_client_audit(
    client_id: uuid.UUID,
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Audit log filtrado por client_id + projects + invoices asociados."""
    items, total = await get_client_audit_log(db, client_id, page=page, size=size)
    return AuditLogPage(items=items, total=total, page=page, size=size)


# ================================================================
# ENDPOINT 8: Create project
# ================================================================

@router.post(
    "/{client_id}/projects",
    response_model=ProjectOut,
    status_code=201,
)
async def create_project(
    client_id: uuid.UUID,
    body: ProjectCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a project for a client."""
    from backend.app.database import set_tenant_context
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    await set_tenant_context(db, client_id=client_id)

    project = Project(
        client_id=client_id,
        nombre=body.nombre,
        categoria_objetivo=body.categoria_objetivo,
        fase=body.fase,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


# ================================================================
# ENDPOINT 9: List projects of a client
# ================================================================

@router.get(
    "/{client_id}/projects",
    response_model=list[ProjectOut],
)
async def list_projects(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """List projects for a client."""
    from backend.app.database import set_tenant_context
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    await set_tenant_context(db, client_id=client_id)

    result = await db.execute(
        select(Project).where(Project.client_id == client_id)
    )
    return result.scalars().all()


# ================================================================
# ENDPOINT 9b: Soft delete (archive) project (sub-atom 1.E.2.bis Phase A)
# ================================================================

@router.delete(
    "/{client_id}/projects/{project_id}",
    response_model=ProjectOut,
)
async def archive_project(
    client_id: uuid.UUID,
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Soft delete (archive) project.

    Sets ``deleted_at = now()`` and ``lifecycle_state = 'ARCHIVED'`` ·
    ENAC traceability sostained (audit log + recovery via resume).
    Idempotent · re-archive returns same project sin error.
    """
    from datetime import datetime, timezone

    from backend.app.database import set_tenant_context

    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    await set_tenant_context(db, client_id=client_id)

    project = await db.get(Project, project_id)
    if not project or project.client_id != client_id:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.deleted_at is None:
        project.deleted_at = datetime.now(timezone.utc)
        project.lifecycle_state = "ARCHIVED"
        await db.commit()
        await db.refresh(project)
    return project


# ================================================================
# ENDPOINT 10: Upload client logo
# ================================================================

@router.post(
    "/{client_id}/logo",
    status_code=200,
)
async def upload_client_logo(
    client_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a client brand logo used as the left corner of every
    generated document header.

    Accepts PNG, JPEG, SVG or WebP up to 2 MB. Stored in the
    ``fulkro-documents`` bucket under ``clients/{id}/logo.{ext}`` and
    the client row is updated with path, mime type and SHA-256.
    """
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if file.content_type not in ACCEPTED_LOGO_MIME:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Tipo de archivo no soportado: {file.content_type}. "
                f"Admitidos: {sorted(ACCEPTED_LOGO_MIME)}"
            ),
        )
    payload = await file.read()
    if len(payload) > MAX_LOGO_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"El logo excede el tamaño máximo (2 MB). Recibido {len(payload)} bytes.",
        )

    ext_by_mime = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/svg+xml": "svg",
        "image/webp": "webp",
    }
    ext = ext_by_mime[file.content_type]
    key = f"clients/{client_id}/logo.{ext}"
    result = put_object(
        bucket=BUCKET_DOCUMENTS,
        key=key,
        data=payload,
        content_type=file.content_type,
        metadata={"client_cif": client.cif, "kind": "brand_logo"},
    )
    client.logo_path = f"{result.bucket}/{result.key}"
    client.logo_mime_type = result.content_type
    client.logo_sha256 = result.sha256
    await db.commit()
    await db.refresh(client)
    return {
        "client_id": str(client.id),
        "logo_path": client.logo_path,
        "logo_mime_type": client.logo_mime_type,
        "logo_sha256": client.logo_sha256,
        "size_bytes": result.size,
    }
