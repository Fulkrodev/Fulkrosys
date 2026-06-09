"""Motor 6 -- Document Factory API endpoints.

Thin HTTP layer over DocumentFactoryService. Pattern:
- Endpoints require tenant context (RLS)
- Service exceptions mapped to HTTP codes
- Zero business logic in api.py -- all in service.py

Consistent with M4 Gap Analysis and M19 Project Risks patterns.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db, set_tenant_context
from backend.app.motors.m06_document_factory.schemas import (
    TemplateOut,
    DocumentOut,
    GenerateDocumentRequest,
    GenerateDocumentResponse,
    RenderPreviewRequest,
    RenderPreviewResponse,
    DocumentFactoryDashboard,
)
from backend.app.motors.m06_document_factory.service import DocumentFactoryService
from backend.app.motors.m06_document_factory.exceptions import (
    TemplateNotFoundError,
    TemplateInactiveError,
    TemplateFileMissingError,
    DocumentNotFoundError,
    MissingPlaceholderError,
    RenderError,
    CatalogLoadError,
)

from backend.app.auth.dependencies import require_owner

router = APIRouter(
    tags=["Motor 6 - Document Factory"],
    # TODO-RBAC-PER-ENDPOINT-001 Cat A: Marcos-only.
    dependencies=[Depends(require_owner)],
)


# ================================================================
# HELPERS
# ================================================================

async def _set_project_rls(project_id: uuid.UUID, db: AsyncSession):
    """Set RLS context for documents table via project owner lookup."""
    client_id = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
    )).scalar()
    if not client_id:  # pragma: no cover
        raise HTTPException(status_code=404, detail="Project not found")
    await set_tenant_context(db, client_id=client_id, project_id=project_id)


async def _set_document_rls(document_id: uuid.UUID, db: AsyncSession) -> uuid.UUID:
    """Set RLS context for a document by looking up its project."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    result = await db.execute(
        text(
            "SELECT project_id FROM documents "
            "WHERE id = :did AND deleted_at IS NULL"
        ),
        {"did": str(document_id)},
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    project_id = row[0]
    await db.execute(text("RESET ROLE"))
    await _set_project_rls(project_id, db)
    return project_id


# ================================================================
# TEMPLATE ENDPOINTS
# ================================================================

@router.get("/templates", response_model=list[TemplateOut])
async def list_templates(
    db: AsyncSession = Depends(get_db),
    categoria: str | None = Query(None),
    familia_ens: str | None = Query(None),
    aplica_desde: str | None = Query(None),
    is_active: bool | None = Query(None),
):
    """List all templates with optional filters."""
    svc = DocumentFactoryService(db)
    return await svc.list_templates(
        categoria=categoria,
        familia_ens=familia_ens,
        aplica_desde=aplica_desde,
        is_active=is_active,
    )


@router.get("/templates/{codigo}", response_model=TemplateOut)
async def get_template(
    codigo: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a single template by codigo."""
    svc = DocumentFactoryService(db)
    try:
        return await svc.get_template_by_codigo(codigo)
    except TemplateNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/templates/sync-catalog")
async def sync_catalog(
    db: AsyncSession = Depends(get_db),
):
    """Sync template metadata from YAML catalog into DB."""
    svc = DocumentFactoryService(db)
    try:
        result = await svc.load_template_metadata_from_catalog()
        await db.commit()
        return result
    except CatalogLoadError as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(e))


# ================================================================
# DOCUMENT GENERATION ENDPOINTS
# ================================================================

@router.post(
    "/projects/{project_id}/documents/generate",
    status_code=status.HTTP_201_CREATED,
    response_model=GenerateDocumentResponse,
)
async def generate_document(
    project_id: uuid.UUID,
    body: GenerateDocumentRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate a document from a template for a project."""
    await _set_project_rls(project_id, db)
    svc = DocumentFactoryService(db)
    try:
        result = await svc.generate_document(
            project_id=project_id,
            template_codigo=body.template_codigo,
            context=body.context,
            generate_pdf=body.generate_pdf,
            sign=body.sign,
            generated_by=body.generated_by,
        )
        await db.commit()
        return result
    except TemplateNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except TemplateInactiveError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except TemplateFileMissingError as e:  # pragma: no cover — stubs always present
        raise HTTPException(status_code=404, detail=str(e))
    except MissingPlaceholderError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RenderError as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/projects/{project_id}/documents/preview",
    response_model=RenderPreviewResponse,
)
async def preview_render(
    project_id: uuid.UUID,
    body: RenderPreviewRequest,
    db: AsyncSession = Depends(get_db),
):
    """Preview placeholder coverage for a template (ephemeral)."""
    await _set_project_rls(project_id, db)
    svc = DocumentFactoryService(db)
    try:
        return await svc.preview_render(
            template_codigo=body.template_codigo,
            context=body.context,
        )
    except TemplateNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ================================================================
# DOCUMENT CRUD ENDPOINTS
# ================================================================

@router.get(
    "/projects/{project_id}/documents",
    response_model=list[DocumentOut],
)
async def list_documents(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    estado: str | None = Query(None),
    template_codigo: str | None = Query(None),
):
    """List generated documents for a project."""
    await _set_project_rls(project_id, db)
    svc = DocumentFactoryService(db)
    return await svc.list_documents(
        project_id=project_id,
        estado=estado,
        template_codigo=template_codigo,
    )


@router.get("/documents/{document_id}", response_model=DocumentOut)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a single document by ID."""
    await _set_document_rls(document_id, db)
    svc = DocumentFactoryService(db)
    try:
        return await svc.get_document(document_id)
    except DocumentNotFoundError as e:  # pragma: no cover — _set_document_rls catches first
        raise HTTPException(status_code=404, detail=str(e))


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Soft delete a document."""
    await _set_document_rls(document_id, db)
    svc = DocumentFactoryService(db)
    try:
        await svc.soft_delete_document(document_id)
        await db.commit()
        return None
    except DocumentNotFoundError as e:  # pragma: no cover — _set_document_rls catches first
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/documents/{document_id}/mark-delivered", response_model=DocumentOut)
async def mark_delivered(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Mark a document as delivered."""
    await _set_document_rls(document_id, db)
    svc = DocumentFactoryService(db)
    try:
        doc = await svc.mark_as_delivered(document_id)
        await db.commit()
        return doc
    except DocumentNotFoundError as e:  # pragma: no cover — _set_document_rls catches first
        raise HTTPException(status_code=404, detail=str(e))


# ================================================================
# DASHBOARD
# ================================================================

@router.get(
    "/projects/{project_id}/documents/dashboard",
    response_model=DocumentFactoryDashboard,
)
async def get_dashboard(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Document factory dashboard for a project."""
    await _set_project_rls(project_id, db)
    svc = DocumentFactoryService(db)
    return await svc.get_dashboard(project_id)


# ================================================================
# DOCUMENTOS RECTORES (SAN-C.MB-9.4) · Manual SGSI + Plan Director
# ================================================================


@router.post("/projects/{project_id}/manual-sgsi/generate")
async def generate_manual_sgsi_endpoint(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Genera Manual SGSI E-160 (CCN-STIC 805) DOCX firmable.

    Aglutina M01 categorización + M30 roles ENS + M22 activos esenciales
    + estructura procesos SGSI canónica (4 niveles documentación).

    Refs: SAN-C.MB-9.4
    """
    from fastapi.responses import Response

    from .rectores_generator import (
        build_rectores_context,
        generate_manual_sgsi_docx,
    )

    await _set_project_rls(project_id, db)
    ctx = await build_rectores_context(db, project_id)
    bio = generate_manual_sgsi_docx(ctx)
    return Response(
        content=bio.getvalue(),
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        headers={
            "Content-Disposition": (
                f'attachment; filename="manual_sgsi_{project_id}.docx"'
            ),
        },
    )


@router.post("/projects/{project_id}/plan-director/generate")
async def generate_plan_director_endpoint(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Genera Plan Director Seguridad E-170 (trianual) DOCX firmable.

    Aglutina M01 categorización + M30 roles + plantilla canónica con
    misión/visión + estrategia trianual + KPIs CCN-STIC 815.

    Refs: SAN-C.MB-9.4
    """
    from fastapi.responses import Response

    from .rectores_generator import (
        build_rectores_context,
        generate_plan_director_docx,
    )

    await _set_project_rls(project_id, db)
    ctx = await build_rectores_context(db, project_id)
    bio = generate_plan_director_docx(ctx)
    return Response(
        content=bio.getvalue(),
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        headers={
            "Content-Disposition": (
                f'attachment; filename="plan_director_{project_id}.docx"'
            ),
        },
    )


# ================================================================
# 16 PLANTILLAS EXCEL (SAN-C.MB-10.1) · openpyxl generators
# ================================================================


# ================================================================
# 4 niveles documentación CCN-STIC 805 (SAN-C.MB-10.8)
# ================================================================


@router.get("/documentation-levels")
async def get_documentation_levels_endpoint():
    """Estructura canónica 4 niveles documentación SGSI (CCN-STIC 805).

    PSI · Normativas · Procedimientos · Instrucciones técnicas con
    template_codes asociados a cada nivel.

    Refs: SAN-C.MB-10.8
    """
    from .documentation_levels import levels_summary

    return levels_summary()


@router.get("/excel-templates")
async def list_excel_templates_endpoint():
    """Catálogo canónico de las 16 plantillas Excel disponibles.

    Frontend lo consume para renderizar el grid sin hardcoding.

    Refs: SAN-C.MB-10.1
    """
    from .excel_generators import list_templates

    return [
        {
            "slug": t.slug,
            "code": t.code,
            "title": t.title,
            "description": t.description,
            "ccn_stic": t.ccn_stic,
        }
        for t in list_templates()
    ]


@router.post("/projects/{project_id}/excel-templates/{template_slug}/generate")
async def generate_excel_template_endpoint(
    project_id: uuid.UUID,
    template_slug: str,
    db: AsyncSession = Depends(get_db),
):
    """Genera plantilla Excel canónica del catálogo (16 disponibles).

    Aglutina datos cross-motor cuando aplica (DdA, inventario activos,
    etc.) o devuelve estructura canónica con placeholders para que el
    cliente complete durante reuniones.

    Refs: SAN-C.MB-10.1
    """
    import io

    from fastapi import HTTPException
    from fastapi.responses import Response

    from .excel_generators import dispatch

    await _set_project_rls(project_id, db)
    try:
        wb = await dispatch(template_slug, project_id, db)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)

    return Response(
        content=bio.getvalue(),
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": (
                f'attachment; filename="{template_slug}_{project_id}.xlsx"'
            ),
            "X-Template-Slug": template_slug,
        },
    )
