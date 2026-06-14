"""Motor 1 — Categorization Engine: REST API endpoints."""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text, func as sa_func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.config import get_settings
from backend.app.core.sse_dispatcher import sse_dispatcher
from backend.app.database import get_db, set_tenant_context
from backend.app.models.core import (
    Categorization,
    InformationType,
    ScopeExclusion,
    Service,
    System,
    SystemSite,
)
from backend.app.motors.m01_categorization.service import (
    CategorizationService,
)
from backend.app.motors.m01_categorization.schemas import (
    CategorizationHistoryItem,
    CategorizationVersionDetail,
    SystemCreate,
    SystemOut,
    InformationTypeBatchRequest,
    InformationTypeOut,
    ServiceBatchRequest,
    ServiceOut,
    ServiceTipoUpdate,
    SiteBatchRequest,
    SiteOut,
    ExclusionBatchRequest,
    ExclusionOut,
    CategorizeRequest,
    CategorizationOut,
    ActaE012Out,
    DimensionSummaryOut,
    RequestSignatureBody,
    RequestSignatureResponse,
    SignatureStatusResponse,
    InheritedFloorBody,
    InheritedFloorOut,
)
from backend.app.motors.m01_categorization.signature_integration import (
    SignatureIntegrationError,
    request_acta_signature,
    get_signature_status,
    request_acta_double_signature,
    get_acta_double_signature_status,
)

router = APIRouter(
    prefix="/categorization",
    tags=["Motor 1 - Categorization"],
    # TODO-RBAC-PER-ENDPOINT-001 Cat A: Marcos-only.
    dependencies=[Depends(require_owner)],
)


# ================================================================
# HELPERS
# ================================================================

async def _get_system_with_rls(
    system_id: uuid.UUID,
    db: AsyncSession,
) -> System:
    """Load system and set RLS context via get_system_owner() SECURITY DEFINER."""
    row = await db.execute(
        text("SELECT * FROM get_system_owner(:sid)"),
        {"sid": str(system_id)},
    )
    owner = row.mappings().first()
    if not owner or not owner["client_id"]:
        raise HTTPException(status_code=404, detail="Sistema no encontrado")
    await set_tenant_context(
        db, client_id=owner["client_id"], project_id=owner["project_id"]
    )
    system = await db.get(System, system_id)
    if not system:
        raise HTTPException(status_code=404, detail="Sistema no encontrado")  # pragma: no cover
    return system


# ================================================================
# ENDPOINT 1: Create system
# ================================================================

@router.post(
    "/projects/{project_id}/systems",
    response_model=SystemOut,
    status_code=201,
)
async def create_system(
    project_id: uuid.UUID,
    body: SystemCreate,
    db: AsyncSession = Depends(get_db),
):
    """Crear un sistema dentro de un proyecto para categorizar."""
    client_id = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
    )).scalar()
    if not client_id:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    await set_tenant_context(db, client_id=client_id, project_id=project_id)

    system = System(
        project_id=project_id,
        nombre=body.nombre,
        descripcion=body.descripcion,
        frontera=body.frontera,
    )
    db.add(system)
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        if "uq_systems_project_id_nombre" in str(e.orig):
            raise HTTPException(
                status_code=409,
                detail=f"Ya existe un sistema con el nombre '{body.nombre}' en este proyecto",
            )
        raise  # pragma: no cover  # Re-raise unexpected IntegrityError (not unique name)
    await db.refresh(system)
    return system


# ================================================================
# ENDPOINT 2: List systems
# ================================================================

@router.get(
    "/projects/{project_id}/systems",
    response_model=list[SystemOut],
)
async def list_systems(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Listar los sistemas de un proyecto."""
    client_id = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
    )).scalar()
    if not client_id:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    await set_tenant_context(db, client_id=client_id, project_id=project_id)

    result = await db.execute(
        select(System).where(
            System.project_id == project_id,
            System.deleted_at.is_(None),
        )
    )
    return result.scalars().all()


# ================================================================
# ENDPOINT 3: Load information types (batch)
# ================================================================

@router.post(
    "/systems/{system_id}/information-types",
    response_model=list[InformationTypeOut],
    status_code=201,
)
async def load_information_types(
    system_id: uuid.UUID,
    body: InformationTypeBatchRequest,
    db: AsyncSession = Depends(get_db),
):
    """Cargar tipos de informacion con valoracion DICAT.

    Replace semantics: soft-deletes existing information_types for this system
    before inserting the new batch. Preserves audit trail while ensuring
    idempotency on retries.
    """
    await _get_system_with_rls(system_id, db)
    # Soft-delete existing active items for this system (replace mode)
    await db.execute(
        text("UPDATE information_types SET deleted_at = NOW() WHERE system_id = :sid AND deleted_at IS NULL"),
        {"sid": str(system_id)},
    )
    created = []
    for item in body.items:
        it = InformationType(
            system_id=system_id,
            nombre=item.nombre,
            valoracion_d=item.valoracion_d,
            valoracion_i=item.valoracion_i,
            valoracion_c=item.valoracion_c,
            valoracion_a=item.valoracion_a,
            valoracion_t=item.valoracion_t,
            justificacion=item.justificacion,
        )
        db.add(it)
        created.append(it)
    await db.commit()
    for it in created:
        await db.refresh(it)
    return created


# ================================================================
# ENDPOINT 4: Load services (batch)
# ================================================================

@router.post(
    "/systems/{system_id}/services",
    response_model=list[ServiceOut],
    status_code=201,
)
async def load_services(
    system_id: uuid.UUID,
    body: ServiceBatchRequest,
    db: AsyncSession = Depends(get_db),
):
    """Cargar servicios con valoracion DICAT.

    Replace semantics: soft-deletes existing services for this system
    before inserting the new batch. Preserves audit trail while ensuring
    idempotency on retries.
    """
    await _get_system_with_rls(system_id, db)
    # Soft-delete existing active items for this system (replace mode)
    await db.execute(
        text("UPDATE services SET deleted_at = NOW() WHERE system_id = :sid AND deleted_at IS NULL"),
        {"sid": str(system_id)},
    )
    created = []
    for item in body.items:
        svc = Service(
            system_id=system_id,
            nombre=item.nombre,
            valoracion_d=item.valoracion_d,
            valoracion_i=item.valoracion_i,
            valoracion_c=item.valoracion_c,
            valoracion_a=item.valoracion_a,
            valoracion_t=item.valoracion_t,
            justificacion=item.justificacion,
            tipo=item.tipo,  # R05 · finalista/instrumental (alcance E-155)
        )
        db.add(svc)
        created.append(svc)
    await db.commit()
    for svc in created:
        await db.refresh(svc)
    return created


# ================================================================
# SCOPE E-155 (R05) · tipo de servicio + sedes + exclusiones
# ================================================================

@router.patch(
    "/systems/{system_id}/services/{service_id}/tipo",
    response_model=ServiceOut,
)
async def set_service_tipo(
    system_id: uuid.UUID,
    service_id: uuid.UUID,
    body: ServiceTipoUpdate,
    db: AsyncSession = Depends(get_db),
):
    """R05 · fija el tipo (finalista/instrumental) de un servicio del alcance."""
    await _get_system_with_rls(system_id, db)
    svc = await db.get(Service, service_id)
    if not svc or svc.system_id != system_id or svc.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    svc.tipo = body.tipo
    await db.commit()
    await db.refresh(svc)
    return svc


@router.post(
    "/systems/{system_id}/sites",
    response_model=list[SiteOut],
    status_code=201,
)
async def load_sites(
    system_id: uuid.UUID,
    body: SiteBatchRequest,
    db: AsyncSession = Depends(get_db),
):
    """R05 · cargar sedes/regiones cloud del alcance (E-155 §3.3).

    Replace semantics: soft-delete de las sedes activas + insert del lote nuevo.
    """
    await _get_system_with_rls(system_id, db)
    await db.execute(
        text("UPDATE system_sites SET deleted_at = NOW() WHERE system_id = :sid AND deleted_at IS NULL"),
        {"sid": str(system_id)},
    )
    created = []
    for item in body.items:
        site = SystemSite(
            system_id=system_id,
            nombre=item.nombre,
            tipo=item.tipo,
            direccion=item.direccion,
            pais=item.pais,
            descripcion=item.descripcion,
        )
        db.add(site)
        created.append(site)
    await db.commit()
    for site in created:
        await db.refresh(site)
    return created


@router.get(
    "/systems/{system_id}/sites",
    response_model=list[SiteOut],
)
async def list_sites(
    system_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """R05 · listar las sedes/regiones cloud del alcance de un sistema."""
    await _get_system_with_rls(system_id, db)
    result = await db.execute(
        select(SystemSite).where(
            SystemSite.system_id == system_id,
            SystemSite.deleted_at.is_(None),
        ).order_by(SystemSite.created_at.asc())
    )
    return result.scalars().all()


@router.post(
    "/systems/{system_id}/exclusions",
    response_model=list[ExclusionOut],
    status_code=201,
)
async def load_exclusions(
    system_id: uuid.UUID,
    body: ExclusionBatchRequest,
    db: AsyncSession = Depends(get_db),
):
    """R05 · cargar exclusiones justificadas del alcance (E-155 §4).

    Replace semantics: soft-delete de las exclusiones activas + insert del lote.
    """
    await _get_system_with_rls(system_id, db)
    await db.execute(
        text("UPDATE scope_exclusions SET deleted_at = NOW() WHERE system_id = :sid AND deleted_at IS NULL"),
        {"sid": str(system_id)},
    )
    created = []
    for item in body.items:
        ex = ScopeExclusion(
            system_id=system_id,
            elemento=item.elemento,
            justificacion=item.justificacion,
        )
        db.add(ex)
        created.append(ex)
    await db.commit()
    for ex in created:
        await db.refresh(ex)
    return created


@router.get(
    "/systems/{system_id}/exclusions",
    response_model=list[ExclusionOut],
)
async def list_exclusions(
    system_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """R05 · listar las exclusiones justificadas del alcance de un sistema."""
    await _get_system_with_rls(system_id, db)
    result = await db.execute(
        select(ScopeExclusion).where(
            ScopeExclusion.system_id == system_id,
            ScopeExclusion.deleted_at.is_(None),
        ).order_by(ScopeExclusion.created_at.asc())
    )
    return result.scalars().all()


# ================================================================
# ENDPOINT 5: Execute categorization
# ================================================================

@router.post(
    "/systems/{system_id}/categorize",
    response_model=CategorizationOut,
)
async def categorize_system(
    system_id: uuid.UUID,
    body: CategorizeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Ejecutar la regla del maximo y persistir la categorizacion."""
    system = await _get_system_with_rls(system_id, db)

    # Prerequisite check
    it_count = await db.scalar(
        select(sa_func.count()).select_from(InformationType).where(
            InformationType.system_id == system_id,
            InformationType.deleted_at.is_(None),
        )
    )
    svc_count = await db.scalar(
        select(sa_func.count()).select_from(Service).where(
            Service.system_id == system_id,
            Service.deleted_at.is_(None),
        )
    )
    if not it_count and not svc_count:
        raise HTTPException(
            status_code=409,
            detail=(
                "El sistema no tiene tipos de informacion ni servicios cargados. "
                "Carga al menos uno antes de categorizar."
            ),
        )

    cat_svc = CategorizationService(db)
    result = cat_svc.compute_for_system(system_id)
    # compute_for_system is async
    result = await result
    cat = await cat_svc.save_categorization(
        system_id=system_id,
        result=result,
        aprobado_por=body.aprobado_por,
        input_snapshot=getattr(cat_svc, '_last_snapshot', None),
    )
    await db.commit()
    await db.refresh(cat)

    # Sesión 3B-2B.8 Phase 1A · SSE emit admin → cliente sync (notify cliente
    # portal subscribers que admin completó categorización). Best-effort ·
    # try/except + logger.exception · NO bloquea primary persist.
    try:
        await sse_dispatcher.dispatch(
            f"project:{system.project_id}",
            "m01.categorizacion.completed",
            {
                "system_id": str(system_id),
                "system_nombre": system.nombre,
                "categoria_resultante": cat.categoria_resultante,
                "determining_dimension": result.determining_dimension,
                "aprobado_por": cat.aprobado_por,
                "fecha_acta": (
                    cat.fecha_acta.isoformat() if cat.fecha_acta else None
                ),
                "primary_actor": "admin",
            },
        )
    except Exception:  # pragma: no cover · best-effort
        logging.getLogger(__name__).exception(
            "SSE m01.categorizacion.completed dispatch failed · system_id=%s",
            system_id,
        )

    # Sesión 3B-2B.8 CLUSTER 2 Phase 2B · SSE + ClientNotification dual emit
    # pattern (#14 cumulative). Admin action surfacing cliente VE/RECIBE ·
    # filosofía cliente-mínimo aligned · best-effort independent dispatch.
    try:
        from backend.app.models.client_portal import ClientUser
        from backend.app.motors.m21_portal_cliente.notification_service import (
            emit_client_notification,
        )

        # Lookup cliente users del project (pilot single-user assumption)
        project_row = (await db.execute(
            text(
                "SELECT client_id FROM projects "
                "WHERE id = :pid AND deleted_at IS NULL"
            ),
            {"pid": str(system.project_id)},
        )).fetchone()
        if project_row:
            client_id = project_row[0]
            users_q = await db.execute(
                select(ClientUser).where(
                    ClientUser.client_id == client_id,
                    ClientUser.deactivated_at.is_(None),
                )
            )
            for user in users_q.scalars().all():
                await emit_client_notification(
                    db,
                    project_id=system.project_id,
                    client_user_id=user.id,
                    type="compliance_confirmation",
                    title="Marcos finalizó tu categorización ENS",
                    body=(
                        f"El sistema '{system.nombre}' quedó categorizado "
                        f"como {cat.categoria_resultante}. Revisa los "
                        "detalles cuando puedas."
                    ),
                    target_url="/client-portal/categorizacion",
                    priority="normal",
                    emitted_by_motor="m01_categorization",
                    payload={
                        "system_id": str(system_id),
                        "system_nombre": system.nombre,
                        "categoria_resultante": cat.categoria_resultante,
                        "source": "m01.categorizacion.completed",
                    },
                )
            await db.commit()
    except Exception:  # pragma: no cover · best-effort
        logging.getLogger(__name__).exception(
            "ClientNotification emit failed post m01.categorizacion.completed · "
            "system_id=%s",
            system_id,
        )

    return CategorizationOut(
        id=cat.id,
        system_id=cat.system_id,
        categoria_resultante=cat.categoria_resultante,
        determining_dimension=result.determining_dimension,
        justification=result.justification,
        fecha_acta=cat.fecha_acta,
        aprobado_por=cat.aprobado_por,
        created_at=cat.created_at,
    )


# ================================================================
# ENDPOINT 6: Get result
# ================================================================

@router.get(
    "/systems/{system_id}/result",
    response_model=CategorizationOut,
)
async def get_categorization_result(
    system_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Consultar la ultima categorizacion del sistema."""
    await _get_system_with_rls(system_id, db)

    result = await db.execute(
        select(Categorization)
        .where(Categorization.system_id == system_id)
        .order_by(Categorization.created_at.desc())
        .limit(1)
    )
    cat = result.scalars().first()
    if not cat:
        raise HTTPException(
            status_code=404,
            detail="El sistema no ha sido categorizado todavia.",
        )

    return CategorizationOut(
        id=cat.id,
        system_id=cat.system_id,
        categoria_resultante=cat.categoria_resultante,
        determining_dimension=None,
        justification=None,
        fecha_acta=cat.fecha_acta,
        aprobado_por=cat.aprobado_por,
        created_at=cat.created_at,
    )


# ================================================================
# ENDPOINT 7: Generate Acta E-012
# ================================================================

@router.get(
    "/systems/{system_id}/acta-e012",
    response_model=ActaE012Out,
)
async def generate_acta_e012(
    system_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Generar el Acta de Categorizacion E-012."""
    system = await _get_system_with_rls(system_id, db)

    # Prerequisite: must be categorized
    cat_result = await db.execute(
        select(Categorization)
        .where(Categorization.system_id == system_id)
        .order_by(Categorization.created_at.desc())
        .limit(1)
    )
    cat = cat_result.scalars().first()
    if not cat:
        raise HTTPException(
            status_code=409,
            detail="El sistema no ha sido categorizado. Ejecute categorize primero.",
        )

    # Re-compute the result to get dimension details for the acta
    cat_svc = CategorizationService(db)
    result = await cat_svc.compute_for_system(system_id)

    # Get project name
    proj_row = await db.execute(
        text("SELECT nombre FROM projects WHERE id = :pid"),
        {"pid": str(system.project_id)},
    )
    project_name = proj_row.scalar_one_or_none() or "Proyecto"

    markdown = cat_svc.generate_acta_e012(
        result=result,
        project_name=project_name,
        system_name=system.nombre,
    )

    return ActaE012Out(
        markdown_content=markdown,
        metadata={
            "category": cat.categoria_resultante,
            "fecha_acta": cat.fecha_acta.isoformat() if cat.fecha_acta else None,
            "system_id": str(system_id),
            "system_name": system.nombre,
            "project_name": project_name,
            "determining_dimension": result.determining_dimension,
            "aprobado_por": cat.aprobado_por,
        },
    )


# ================================================================
# ENDPOINT 8: Dimension summary
# ================================================================

@router.get(
    "/systems/{system_id}/dimensions",
    response_model=DimensionSummaryOut,
)
async def get_dimension_summary(
    system_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Consultar valoraciones DICAT maximas actuales del sistema."""
    await _get_system_with_rls(system_id, db)

    info_types = (await db.execute(
        select(InformationType).where(
            InformationType.system_id == system_id,
            InformationType.deleted_at.is_(None),
        )
    )).scalars().all()

    services = (await db.execute(
        select(Service).where(
            Service.system_id == system_id,
            Service.deleted_at.is_(None),
        )
    )).scalars().all()

    # Compute max per dimension
    level_order = {"BAJO": 1, "MEDIO": 2, "ALTO": 3}
    max_per_dim = {"D": "BAJO", "I": "BAJO", "C": "BAJO", "A": "BAJO", "T": "BAJO"}

    for item in list(info_types) + list(services):
        for attr, dim in [
            ("valoracion_d", "D"), ("valoracion_i", "I"),
            ("valoracion_c", "C"), ("valoracion_a", "A"),
            ("valoracion_t", "T"),
        ]:
            val = getattr(item, attr, None)
            if val and val.upper() in level_order:
                if level_order[val.upper()] > level_order[max_per_dim[dim]]:
                    max_per_dim[dim] = val.upper()

    # Project category from max rule
    max_level = max(level_order[v] for v in max_per_dim.values())
    projected = {1: "BASICA", 2: "MEDIA", 3: "ALTA"}[max_level]

    return DimensionSummaryOut(
        max_d=max_per_dim["D"],
        max_i=max_per_dim["I"],
        max_c=max_per_dim["C"],
        max_a=max_per_dim["A"],
        max_t=max_per_dim["T"],
        projected_category=projected,
        info_types_count=len(info_types),
        services_count=len(services),
    )



# ================================================================
# ENDPOINT 9: Soft delete system (cascade to info_types + services)
# ================================================================

@router.delete(
    "/systems/{system_id}",
    status_code=204,
)
async def soft_delete_system(
    system_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Marca el sistema como eliminado (soft delete).

    Los datos no se borran fisicamente para preservar trazabilidad de auditoria.
    Cascade: tambien soft-deletes los info_types y services del sistema.
    """
    system = await _get_system_with_rls(system_id, db)

    # Check not already deleted
    if system.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Sistema no encontrado")

    await db.execute(
        text("UPDATE systems SET deleted_at = NOW() WHERE id = :sid AND deleted_at IS NULL"),
        {"sid": str(system_id)},
    )
    # Cascade soft-delete
    await db.execute(
        text("UPDATE information_types SET deleted_at = NOW() WHERE system_id = :sid AND deleted_at IS NULL"),
        {"sid": str(system_id)},
    )
    await db.execute(
        text("UPDATE services SET deleted_at = NOW() WHERE system_id = :sid AND deleted_at IS NULL"),
        {"sid": str(system_id)},
    )
    await db.commit()
    return None


# ================================================================
# ENDPOINT 10: Soft delete information type
# ================================================================

@router.delete(
    "/systems/{system_id}/information-types/{info_type_id}",
    status_code=204,
)
async def soft_delete_information_type(
    system_id: uuid.UUID,
    info_type_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Marca un tipo de informacion como eliminado (soft delete)."""
    await _get_system_with_rls(system_id, db)

    result = await db.execute(
        text(
            "UPDATE information_types SET deleted_at = NOW() "
            "WHERE id = :iid AND system_id = :sid AND deleted_at IS NULL"
        ),
        {"iid": str(info_type_id), "sid": str(system_id)},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Tipo de informacion no encontrado")
    await db.commit()
    return None


# ================================================================
# ENDPOINT 11: Soft delete service
# ================================================================

@router.delete(
    "/systems/{system_id}/services/{service_id}",
    status_code=204,
)
async def soft_delete_service(
    system_id: uuid.UUID,
    service_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Marca un servicio como eliminado (soft delete)."""
    await _get_system_with_rls(system_id, db)

    result = await db.execute(
        text(
            "UPDATE services SET deleted_at = NOW() "
            "WHERE id = :svid AND system_id = :sid AND deleted_at IS NULL"
        ),
        {"svid": str(service_id), "sid": str(system_id)},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    await db.commit()
    return None



# ================================================================
# ENDPOINT 12: Categorization history (list all versions)
# ================================================================

@router.get(
    "/systems/{system_id}/history",
    response_model=list[CategorizationHistoryItem],
)
async def get_categorization_history(
    system_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Lista todas las categorizaciones del sistema, ordenadas DESC por version."""
    await _get_system_with_rls(system_id, db)
    result = await db.execute(
        select(Categorization)
        .where(
            Categorization.system_id == system_id,
            Categorization.deleted_at.is_(None),
        )
        .order_by(Categorization.version.desc())
    )
    return result.scalars().all()


# ================================================================
# ENDPOINT 13: Categorization version detail (with input snapshot)
# ================================================================

@router.get(
    "/systems/{system_id}/history/{version_id}",
    response_model=CategorizationVersionDetail,
)
async def get_categorization_version(
    system_id: uuid.UUID,
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Devuelve una version especifica de la categorizacion con input_snapshot completo."""
    await _get_system_with_rls(system_id, db)
    cat = await db.get(Categorization, version_id)
    if not cat or cat.system_id != system_id or cat.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Version de categorizacion no encontrada")
    return cat



# ================================================================
# ENDPOINT 14: Acta E-012 as PDF
# ================================================================

@router.get(
    "/systems/{system_id}/acta-e012.pdf",
)
async def get_acta_e012_pdf(
    system_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Genera el Acta E-012 en formato PDF para descarga.

    Usa docxtpl para rellenar plantilla provisional + LibreOffice headless
    para convertir a PDF. Pipeline reusable via core/pdf_renderer.py.
    """
    from fastapi.responses import Response as FastAPIResponse

    system = await _get_system_with_rls(system_id, db)

    # Check categorization exists
    cat_result = await db.execute(
        select(Categorization)
        .where(Categorization.system_id == system_id, Categorization.deleted_at.is_(None))
        .order_by(Categorization.version.desc())
        .limit(1)
    )
    cat = cat_result.scalars().first()
    if not cat:
        raise HTTPException(status_code=404, detail="Sistema no categorizado. Ejecute categorize primero.")

    # R03-wiring · CANÓNICO: plantilla m06 E-012 (doble firma competente art.40.2
    # RD 311/2022 · RInfo+RServ aprueban, RSeg conforme) + contexto m06 desde m01.
    # Reemplaza la variante B (acta_e012_provisional.docx · firmantes incorrectos).
    # Render por el pipeline m06 (render_docx aplica marca/firmas/filtros ES, que
    # PDFRenderer estricto NO inyecta) → PDF vía convert_docx_to_pdf (LibreOffice).
    import tempfile
    from pathlib import Path

    from backend.app.motors.m06_document_factory.acta_e012_generator import (
        build_e012_context,
    )
    from backend.app.motors.m06_document_factory.rendering import (
        convert_docx_to_pdf,
        render_docx,
    )

    context, _ = await build_e012_context(db, system_id)
    template_path = (
        Path(__file__).resolve().parents[4] / "var" / "templates_docx" / "E-012.docx"
    )
    try:
        with tempfile.TemporaryDirectory(prefix="fulkro_acta_e012_") as td:
            tdp = Path(td)
            docx_out = tdp / "acta_e012.docx"
            render_docx(template_path, context, docx_out)
            pdf_path = convert_docx_to_pdf(docx_out, tdp)
            if pdf_path is None:
                raise HTTPException(
                    status_code=503,
                    detail="Conversión a PDF no disponible (LibreOffice).",
                )
            pdf_bytes = pdf_path.read_bytes()
    except HTTPException:
        raise
    except Exception as e:  # pragma: no cover — render/convert hard failure
        raise HTTPException(status_code=500, detail=f"Error generando PDF del acta E-012: {e}")

    return FastAPIResponse(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="acta_e012_{system_id}.pdf"'},
    )


# ================================================================
# ENDPOINT 15: Acta E-012 as DOCX
# ================================================================

@router.get(
    "/systems/{system_id}/acta-e012.docx",
)
async def get_acta_e012_docx(
    system_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Genera el Acta E-012 en formato DOCX para edicion por el responsable ENS."""
    from fastapi.responses import Response as FastAPIResponse

    system = await _get_system_with_rls(system_id, db)

    cat_result = await db.execute(
        select(Categorization)
        .where(Categorization.system_id == system_id, Categorization.deleted_at.is_(None))
        .order_by(Categorization.version.desc())
        .limit(1)
    )
    cat = cat_result.scalars().first()
    if not cat:
        raise HTTPException(status_code=404, detail="Sistema no categorizado. Ejecute categorize primero.")

    # R03-wiring · CANÓNICO: plantilla m06 E-012 (doble firma art.40.2) + contexto
    # m06 desde m01 · render por el pipeline m06 (marca/firmas/filtros ES).
    import tempfile
    from pathlib import Path

    from backend.app.motors.m06_document_factory.acta_e012_generator import (
        build_e012_context,
    )
    from backend.app.motors.m06_document_factory.rendering import render_docx

    context, _ = await build_e012_context(db, system_id)
    template_path = (
        Path(__file__).resolve().parents[4] / "var" / "templates_docx" / "E-012.docx"
    )
    try:
        with tempfile.TemporaryDirectory(prefix="fulkro_acta_e012_") as td:
            docx_out = Path(td) / "acta_e012.docx"
            render_docx(template_path, context, docx_out)
            docx_bytes = docx_out.read_bytes()
    except Exception as e:  # pragma: no cover — render hard failure
        raise HTTPException(status_code=500, detail=f"Error generando DOCX del acta E-012: {e}")

    return FastAPIResponse(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="acta_e012_{system_id}.docx"'},
    )



# ================================================================
# ENDPOINT 16: Acta E-012 as JSON
# ================================================================

@router.get(
    "/systems/{system_id}/acta-e012.json",
)
async def get_acta_e012_json(
    system_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Genera el Acta E-012 en formato JSON.

    Esquema propio FULKRO Acta E-012 v1. NO es formato oficial CCN-CERT
    (no existe estandar oficial). Documentacion: docs/schemas/fulkro_acta_e012_v1.md
    """
    system = await _get_system_with_rls(system_id, db)

    # Check categorization exists
    cat_result = await db.execute(
        select(Categorization)
        .where(Categorization.system_id == system_id, Categorization.deleted_at.is_(None))
        .order_by(Categorization.version.desc())
        .limit(1)
    )
    cat = cat_result.scalars().first()
    if not cat:
        raise HTTPException(status_code=404, detail="Sistema no categorizado. Ejecute categorize primero.")

    # Re-compute to get dimension details
    cat_svc = CategorizationService(db)
    result = await cat_svc.compute_for_system(system_id)

    # Load project + client
    proj_row = await db.execute(
        text("SELECT id, nombre FROM projects WHERE id = :pid"),
        {"pid": str(system.project_id)},
    )
    project_data = proj_row.mappings().first()

    client_row = await db.execute(
        text("SELECT c.nombre, c.cif FROM clients c JOIN projects p ON p.client_id = c.id WHERE p.id = :pid"),
        {"pid": str(system.project_id)},
    )
    client_data = client_row.mappings().first()

    # Load active info_types + services
    info_types = (await db.execute(
        select(InformationType).where(
            InformationType.system_id == system_id,
            InformationType.deleted_at.is_(None),
        )
    )).scalars().all()
    services_list = (await db.execute(
        select(Service).where(
            Service.system_id == system_id,
            Service.deleted_at.is_(None),
        )
    )).scalars().all()

    from datetime import datetime, timezone
    return {
        "schema": "fulkro.acta_e012",
        "schema_version": "1.0",
        "document_id": "E-012",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "act": {
            "version": cat.version,
            "fecha_acta": cat.fecha_acta.isoformat() if cat.fecha_acta else None,
            "approved_by": cat.aprobado_por,
        },
        "client": {
            "nombre": client_data["nombre"] if client_data else "",
            "cif": client_data["cif"] if client_data else "",
        },
        "project": {
            "id": str(system.project_id),
            "nombre": project_data["nombre"] if project_data else "",
        },
        "system": {
            "id": str(system_id),
            "nombre": system.nombre,
            "descripcion": system.descripcion,
        },
        "information_types": sorted([
            {
                "nombre": it.nombre,
                "valoraciones": {
                    "D": it.valoracion_d or "BAJO",
                    "I": it.valoracion_i or "BAJO",
                    "C": it.valoracion_c or "BAJO",
                    "A": it.valoracion_a or "BAJO",
                    "T": it.valoracion_t or "BAJO",
                },
            }
            for it in info_types
        ], key=lambda x: x["nombre"]),
        "services": sorted([
            {
                "nombre": s.nombre,
                "valoraciones": {
                    "D": s.valoracion_d or "BAJO",
                    "I": s.valoracion_i or "BAJO",
                    "C": s.valoracion_c or "BAJO",
                    "A": s.valoracion_a or "BAJO",
                    "T": s.valoracion_t or "BAJO",
                },
            }
            for s in services_list
        ], key=lambda x: x["nombre"]),
        "result": {
            "dimensiones": {
                dim: result.dimension_assessments[dim].value
                for dim in ["D", "I", "C", "A", "T"]
            },
            "categoria_final": result.category.value,
            "determining_dimension": result.determining_dimension,
        },
        "justificacion": result.justification,
        "normative_basis": {
            "primary": "Real Decreto 311/2022 Anexo I",
            "guides": ["CCN-STIC 803"],
        },
    }


# ================================================================
# SIGNATURE RE-INTEGRATION M1 + M12 (M12-G1)
# ================================================================

@router.post(
    "/systems/{system_id}/acta-e012/request-signature",
    response_model=RequestSignatureResponse,
    tags=["Motor 1 - Categorization"],
)
async def request_signature_endpoint(
    system_id: uuid.UUID,
    body: RequestSignatureBody,
    db: AsyncSession = Depends(get_db),
) -> RequestSignatureResponse:
    """Solicita firma electronica avanzada del Acta E-012 via magic link.

    Genera un magic link de tipo firma_documento con scope al acta E-012
    del sistema. El link se envia al firmante (Responsable de la Informacion)
    por canal separado. Si ya existe una solicitud previa, la revoca y
    emite una nueva.
    """
    # FIX(RLS): resolver owner + fijar tenant context antes de tocar
    # categorizations/magic_links (RLS fail-closed bajo fulkro_app), espejo
    # del endpoint de doble firma.
    await _get_system_with_rls(system_id, db)
    try:
        result = await request_acta_signature(
            session=db,
            system_id=system_id,
            recipient_email=str(body.recipient_email),
            recipient_name=body.recipient_name,
            recipient_role=body.recipient_role,
            base_url=get_settings().app_base_url,
        )
    except SignatureIntegrationError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        )
    # FIX(commit): get_db NO auto-commitea → sin esto el magic_link insertado y
    # categorization.signature_magic_link_id se revierten y el firmante recibe un
    # link 404. Espejo de request_double_signature_endpoint.
    await db.commit()
    return RequestSignatureResponse(**result)


@router.get(
    "/systems/{system_id}/acta-e012/signature-status",
    response_model=SignatureStatusResponse,
    tags=["Motor 1 - Categorization"],
)
async def signature_status_endpoint(
    system_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> SignatureStatusResponse:
    """Estado actual de la solicitud de firma del Acta E-012."""
    try:
        result = await get_signature_status(db, system_id)
    except SignatureIntegrationError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )
    return SignatureStatusResponse(**result)


# ================================================================
# R03 · DOBLE FIRMA COMPETENTE del Acta E-012 (art. 40.2 RD 311/2022)
# RInfo + RServ APRUEBAN · RSeg conforme · acta aprobada solo con AMBAS.
# ================================================================

@router.post(
    "/systems/{system_id}/acta-e012/request-double-signature",
    tags=["Motor 1 - Categorization"],
)
async def request_double_signature_endpoint(
    system_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Solicita la DOBLE firma competente del acta E-012 (R03).

    Crea (idempotente) dos signing_intents m05 ``acta_comite`` —Responsable de la
    Información y Responsable del Servicio— vinculados al mismo hash del acta. El
    acta se considera aprobada SOLO cuando AMBOS firman (art. 40.2 RD 311/2022).
    """
    await _get_system_with_rls(system_id, db)
    try:
        result = await request_acta_double_signature(db, system_id)
    except SignatureIntegrationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    await db.commit()
    return result


@router.get(
    "/systems/{system_id}/acta-e012/double-signature-status",
    tags=["Motor 1 - Categorization"],
)
async def double_signature_status_endpoint(
    system_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Estado de la doble firma del acta E-012 + gate ``aprobada`` (R03).

    ``aprobada=True`` solo cuando los dos intents competentes (RInfo + RServ)
    están firmados.
    """
    await _get_system_with_rls(system_id, db)
    try:
        return await get_acta_double_signature_status(db, system_id)
    except SignatureIntegrationError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ================================================================
# ENDPOINTS 17/18: Inherited AAPP floor (#5 · Sub-bloque E)
# ================================================================
# Captura/edición del suelo de categoría heredado de la AAPP por Marcos en
# Fase 1 (decisión-producto A). Project-scoped · require_owner (router) ·
# RLS via get_project_owner + set_tenant_context (patrón _get_system_with_rls).


@router.get(
    "/projects/{project_id}/inherited-floor",
    response_model=InheritedFloorOut,
)
async def get_inherited_floor(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Consultar el suelo de categoría heredado de la AAPP del proyecto."""
    client_id = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
    )).scalar()
    if not client_id:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    await set_tenant_context(db, client_id=client_id, project_id=project_id)

    row = (await db.execute(
        text(
            "SELECT categoria_heredada_aapp, categoria_objetivo "
            "FROM projects WHERE id = :pid AND deleted_at IS NULL"
        ),
        {"pid": str(project_id)},
    )).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return InheritedFloorOut(
        project_id=project_id,
        categoria_heredada_aapp=row["categoria_heredada_aapp"],
        categoria_objetivo=row["categoria_objetivo"],
    )


@router.put(
    "/projects/{project_id}/inherited-floor",
    response_model=InheritedFloorOut,
)
async def set_inherited_floor(
    project_id: uuid.UUID,
    body: InheritedFloorBody,
    db: AsyncSession = Depends(get_db),
):
    """Fijar/actualizar el suelo AAPP (Fase 1 · Marcos · decisión A).

    Variante 2 · eleva ``categoria_objetivo`` si quedó por debajo del suelo
    (solo SUBE, nunca baja · es lo que leen pricing/workflow/retainer/pentest).

    #5 cabo · si el suelo se introduce TARDE (ya existen propuesta/contrato/plan
    de la categoría inferior), esos artefactos son snapshots inmutables y quedan
    stale: se devuelve ``downstream_stale_warning`` para no resolverlo a ciegas.
    El recompute downstream es un Future-X dedicado (no se regenera aquí).
    """
    client_id = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
    )).scalar()
    if not client_id:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    await set_tenant_context(db, client_id=client_id, project_id=project_id)

    # #5 cabo · orquestador con guard por nivel (N1 libre · N2 eleva+regenera ·
    # N2.5 bloquea contrato en vuelo · N3 bloquea 409 contrato firmado/factura +
    # constancia). Sustituye el "siempre eleva + warn" de #5 base.
    from backend.app.motors.m01_categorization.floor_elevation_service import (
        elevate_inherited_floor,
        InFlightContractError,
        SignedContractError,
        FloorElevationError,
    )
    try:
        result = await elevate_inherited_floor(
            db, project_id, body.categoria_heredada_aapp,
        )
    except (InFlightContractError, SignedContractError) as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except FloorElevationError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return InheritedFloorOut(
        project_id=project_id,
        categoria_heredada_aapp=result.categoria_heredada_aapp,
        categoria_objetivo=result.categoria_objetivo,
        categoria_objetivo_elevated=result.categoria_objetivo_elevated,
        level=result.level,
        regenerated=result.regenerated,
    )
