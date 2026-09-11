"""Motor 3 — DdA Engine API endpoints.

Capa HTTP fina sobre DdaService. Patron:
- Endpoints protegidos requieren tenant context (RLS dda_entries)
- Excepciones del service mapeadas a HTTP codes apropiados
- Cero logica de negocio en api.py — todo en service.py
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db, set_tenant_context
from backend.app.motors.m03_dda.schemas import (
    DdaCreateRequest,
    DdaEntryUpdateRequest,
    RequestE040SignatureBody,
    RequestE040SignatureResponse,
    E040SignatureStatusResponse,
)
from backend.app.motors.m03_dda.signature_integration import (
    E040SignatureIntegrationError,
    request_e040_signature,
    get_e040_signature_status,
)
from backend.app.motors.m03_dda.service import (
    DdaService,
    DdaError,
    DdaNotFoundError,
    DdaFrozenError,
    DdaEntryNotFoundError,
    DdaIncompleteForFreezeError,
)
from backend.app.motors.m30_client_contacts.require_ens_role import require_ens_role
from backend.app.auth.dependencies import require_owner

router = APIRouter(
    prefix="/dda", tags=["Motor 3 - DdA Engine"],
    # TODO-RBAC-PER-ENDPOINT-001 Cat A: Marcos-only.
    dependencies=[Depends(require_owner)],
)


# ================================================================
# HELPERS
# ================================================================

async def _set_project_rls(project_id: uuid.UUID, db: AsyncSession):
    """Set RLS context for dda_entries table via project owner lookup."""
    client_id = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
    )).scalar()
    if not client_id:
        raise HTTPException(status_code=404, detail="Project not found")
    await set_tenant_context(db, client_id=client_id, project_id=project_id)


# ================================================================
# ENDPOINT 1: POST /generate
# ================================================================

@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def generate_dda(
    body: DdaCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Genera nueva DdA para un proyecto (73 entries atomicas)."""
    await _set_project_rls(body.project_id, db)
    svc = DdaService(db)
    try:
        result = await svc.generate_dda(
            project_id=body.project_id,
            system_category=body.system_category,
            responsable=body.responsable,
        )
        await db.commit()
        return result
    except DdaError as e:  # pragma: no cover — defensive server error
        logger.exception("Failed to generate DdA")  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(e))  # pragma: no cover


# ================================================================
# ENDPOINT 2: GET /projects/{project_id}/entries
# ================================================================

@router.get("/projects/{project_id}/entries")
async def list_dda_entries(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    marco: str | None = Query(None, description="Filtrar por marco: org/op/mp"),
    familia: str | None = Query(None, description="Filtrar por familia: op.exp, mp.com..."),
):
    """Lista entries de DdA con enrichment MAGERIT."""
    await _set_project_rls(project_id, db)
    svc = DdaService(db)
    try:
        return await svc.list_entries(project_id, marco=marco, familia=familia)
    except DdaNotFoundError:  # pragma: no cover — RLS _set_project_rls catches 404 first
        raise HTTPException(status_code=404, detail="No DdA found for project")


# ================================================================
# ENDPOINT 3: GET /projects/{project_id}/stats
# ================================================================

@router.get("/projects/{project_id}/stats")
async def get_dda_stats(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Stats de completitud de la DdA para dashboard."""
    await _set_project_rls(project_id, db)
    svc = DdaService(db)
    try:
        return await svc.get_completion_stats(project_id)
    except DdaNotFoundError:  # pragma: no cover — RLS _set_project_rls catches 404 first
        raise HTTPException(status_code=404, detail="No DdA found for project")


# ================================================================
# ENDPOINT 4: PATCH /entries/{entry_id}
# ================================================================

@router.patch("/entries/{entry_id}")
async def update_dda_entry(
    entry_id: uuid.UUID,
    body: DdaEntryUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Actualiza entry de DdA. Bloqueado con 409 si frozen."""
    # Use admin role to bypass RLS for entry lookup (same pattern as M12 consume)
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    svc = DdaService(db)
    try:
        updates = body.model_dump(exclude_unset=True, exclude_none=True)
        entry = await svc.update_entry(entry_id, updates)
        await db.commit()
        return {"id": str(entry.id), "version": entry.version, "updated": True}
    except DdaEntryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DdaFrozenError as e:
        raise HTTPException(status_code=409, detail=str(e))


# ================================================================
# SIGNATURE RE-INTEGRATION M3 + M12 (M3-G2)
# ================================================================

@router.post(
    "/projects/{project_id}/e040/request-signature",
    response_model=RequestE040SignatureResponse,
)
async def request_e040_signature_endpoint(
    project_id: uuid.UUID,
    body: RequestE040SignatureBody,
    db: AsyncSession = Depends(get_db),
) -> RequestE040SignatureResponse:
    """Solicita firma electronica avanzada de la DdA E-040 al RSEG via magic link.

    Requiere que la DdA del proyecto este generada y congelada (POST /freeze).
    """
    await _set_project_rls(project_id, db)
    try:
        result = await request_e040_signature(
            session=db,
            project_id=project_id,
            recipient_email=str(body.recipient_email),
            recipient_name=body.recipient_name,
            recipient_role=body.recipient_role,
        )
    except E040SignatureIntegrationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    # get_db() no auto-commitea: sin esto el magic link de firma E-040 (y el
    # signature_magic_link_id de la DdA) se revierten y el RSEG recibe un 404.
    # Espejo de m02_magerit request_e028_signature_endpoint.
    await db.commit()
    return RequestE040SignatureResponse(**result)


@router.get(
    "/projects/{project_id}/e040/signature-status",
    response_model=E040SignatureStatusResponse,
)
async def e040_signature_status_endpoint(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> E040SignatureStatusResponse:
    """Estado actual de la solicitud de firma de la DdA E-040."""
    await _set_project_rls(project_id, db)
    result = await get_e040_signature_status(db, project_id)
    return E040SignatureStatusResponse(**result)


# ================================================================
# ENDPOINT 5: POST /projects/{project_id}/freeze
# ================================================================

@router.post("/projects/{project_id}/freeze")
async def freeze_dda(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    aprobado_por: str = Query(..., description="Nombre del RSEG que aprueba"),
):
    """Congela la DdA. Requiere minimo 80% medidas valoradas.

    N4 · antes de tocar nada se comprueba que `aprobado_por` sea el Responsable
    de la Seguridad nombrado del proyecto. Hasta el bloque N este parametro era
    texto libre y no se validaba: la DdA quedaba congelada a nombre de quien se
    escribiera. RD 311/2022 art. 11 exige responsabilidades diferenciadas, y una
    firma que puede llevar cualquier nombre no las diferencia.

    El control de rol va PRIMERO, antes de buscar la DdA: autorizar y luego
    operar, no al reves.
    """
    await _set_project_rls(project_id, db)
    aprobado_por = await require_ens_role(
        db, project_id, "responsable_seguridad", aprobado_por,
    )
    svc = DdaService(db)
    try:
        result = await svc.freeze_dda(project_id, aprobado_por)
        await db.commit()
        return result
    except DdaNotFoundError as e:
        # N4 · un proyecto sin DdA generada devolvia 500 con la excepcion sin
        # capturar. No hay nada que congelar: eso es un 404, no un error del
        # servidor. Lo descubrio el test del control de rol al pasar el control
        # y seguir adelante, que es justo lo que ese test demuestra.
        raise HTTPException(status_code=404, detail=str(e))
    except DdaIncompleteForFreezeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DdaFrozenError as e:  # pragma: no cover — double-freeze edge case
        raise HTTPException(status_code=409, detail=str(e))


# ================================================================
# ENDPOINT 6: POST /projects/{project_id}/unfreeze
# ================================================================

@router.post("/projects/{project_id}/unfreeze", status_code=204)
async def unfreeze_dda(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Descongela la DdA."""
    await _set_project_rls(project_id, db)
    svc = DdaService(db)
    try:
        await svc.unfreeze_dda(project_id)
        await db.commit()
        return None
    except DdaError as e:
        raise HTTPException(status_code=409, detail=str(e))


# ================================================================
# ENDPOINT 7: GET /measures/catalog (read-only, no tenant)
# ================================================================

@router.get("/measures/catalog")
async def get_measures_catalog(
    db: AsyncSession = Depends(get_db),
    marco: str | None = Query(None),
):
    """Catalogo de las 73 medidas ENS (read-only, sin tenant context)."""
    # Admin role to read ens_measures (no RLS on this table, but safe)
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    svc = DdaService(db)
    return await svc.list_catalog_measures(marco=marco)


# ================================================================
# ENDPOINT 8: GET /projects/{project_id}/measures/{measure_codigo}
# ================================================================

@router.get("/projects/{project_id}/measures/{measure_codigo}")
async def get_entry_by_measure(
    project_id: uuid.UUID,
    measure_codigo: str,
    db: AsyncSession = Depends(get_db),
):
    """Entry especifica por codigo de medida."""
    await _set_project_rls(project_id, db)
    svc = DdaService(db)
    try:
        return await svc.get_entry_by_measure(project_id, measure_codigo)
    except DdaEntryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ================================================================
# ENDPOINT 9: GET /projects/{project_id}/status (FASE 9.D)
# ================================================================

@router.get("/projects/{project_id}/status")
async def get_dda_status(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """DdA status (FASE 9.D · TODO-FASE-9-DDA-GATE-UX-001).

    Devuelve estado mínimo del DdA del proyecto para que el UI gate
    GenerateDocumentButton pueda decidir si habilita la generación de
    políticas/procedimientos/entregables (categoría que requiere DdA
    congelado · workflow_gates.require_frozen_dda_if_needed).

    Lectura cheap: 1 query a dda_entries · COUNT + MAX(fecha_aprobacion).
    """
    await _set_project_rls(project_id, db)
    row = (await db.execute(
        text(
            "SELECT "
            "  COUNT(*) AS total, "
            "  COUNT(*) FILTER (WHERE fecha_aprobacion IS NOT NULL) AS aprobadas, "
            "  MAX(fecha_aprobacion) AS frozen_at, "
            "  MAX(aprobado_por) AS frozen_by "
            "FROM dda_entries "
            "WHERE project_id = :pid AND deleted_at IS NULL"
        ),
        {"pid": str(project_id)},
    )).mappings().first()
    total = int(row["total"]) if row else 0
    aprobadas = int(row["aprobadas"]) if row else 0
    # frozen = al menos 1 entry con fecha_aprobacion · consistente con
    # require_frozen_dda en workflow_gates.py
    frozen = aprobadas > 0
    return {
        "project_id": str(project_id),
        "exists": total > 0,
        "frozen": frozen,
        "frozen_at": row["frozen_at"].isoformat() if row and row["frozen_at"] else None,
        "frozen_by": row["frozen_by"] if row else None,
        "total_entries": total,
        "approved_entries": aprobadas,
    }
