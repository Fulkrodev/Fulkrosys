"""Motor 19 -- Project Risk Management API endpoints.

Capa HTTP fina sobre ProjectRiskService. Patron:
- Endpoints protegidos requieren tenant context (RLS project_risks)
- Excepciones del service mapeadas a HTTP codes apropiados
- Cero logica de negocio en api.py -- todo en service.py

Consistent with M3 DdA Engine and M12 Magic Link Engine patterns.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db, set_tenant_context
from backend.app.motors.m19_risk.schemas import (
    ProjectRiskCreate,
    ProjectRiskUpdate,
    ProjectRiskOut,
    MonitorRiskRequest,
    MaterializeRiskRequest,
    CloseRiskRequest,
    InstantiateCatalogRequest,
    InstantiateCatalogResponse,
    RiskDashboardResponse,
)
from backend.app.motors.m19_risk.service import ProjectRiskService
from backend.app.motors.m19_risk.exceptions import (
    ProjectRiskNotFoundError,
    ProjectRiskValidationError,
    ProjectRiskStateError,
    CatalogAlreadyInstantiatedError,
    CatalogNotFoundError,
    CatalogParseError,
)

from backend.app.auth.dependencies import require_owner

router = APIRouter(
    tags=["Motor 19 - Project Risks"],
    # TODO-RBAC-PER-ENDPOINT-001 Cat A: Marcos-only.
    dependencies=[Depends(require_owner)],
)


# ================================================================
# HELPERS
# ================================================================

async def _set_project_rls(project_id: uuid.UUID, db: AsyncSession):
    """Set RLS context for project_risks table via project owner lookup."""
    client_id = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
    )).scalar()
    if not client_id:
        raise HTTPException(status_code=404, detail="Project not found")
    await set_tenant_context(db, client_id=client_id, project_id=project_id)


async def _set_risk_rls(risk_id: uuid.UUID, db: AsyncSession) -> uuid.UUID:
    """Set RLS context for a risk by looking up its project.

    Returns the project_id for downstream use.
    """
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    result = await db.execute(
        text("SELECT project_id FROM project_risks WHERE id = :rid AND deleted_at IS NULL"),
        {"rid": str(risk_id)},
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Risk {risk_id} not found")
    project_id = row[0]
    await db.execute(text("RESET ROLE"))
    await _set_project_rls(project_id, db)
    return project_id


# ================================================================
# CRUD ENDPOINTS
# ================================================================

# ENDPOINT 1: POST /projects/{project_id}/risks
@router.post("/projects/{project_id}/risks", status_code=status.HTTP_201_CREATED, response_model=ProjectRiskOut)
async def create_risk(
    project_id: uuid.UUID,
    body: ProjectRiskCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new project risk manually."""
    await _set_project_rls(project_id, db)
    svc = ProjectRiskService(db)
    try:
        risk = await svc.create_risk(
            project_id=project_id,
            risk_code=body.risk_code,
            titulo=body.titulo,
            descripcion=body.descripcion,
            categoria=body.categoria,
            probabilidad=body.probabilidad,
            impacto_dias=body.impacto_dias,
            impacto_euros=body.impacto_euros,
            owner=body.owner,
            trigger_condicion=body.trigger_condicion,
            mitigation_plan=body.mitigation_plan,
            contingency_plan=body.contingency_plan,
        )
        await db.commit()
        return risk
    except ProjectRiskValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))


# ENDPOINT 2: GET /risks/{risk_id}
@router.get("/risks/{risk_id}", response_model=ProjectRiskOut)
async def get_risk(
    risk_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a single project risk by ID."""
    await _set_risk_rls(risk_id, db)
    svc = ProjectRiskService(db)
    try:
        return await svc.get_risk(risk_id)
    except ProjectRiskNotFoundError as e:  # pragma: no cover — _set_risk_rls catches 404 first
        raise HTTPException(status_code=404, detail=str(e))


# ENDPOINT 3: GET /projects/{project_id}/risks
@router.get("/projects/{project_id}/risks", response_model=list[ProjectRiskOut])
async def list_risks(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    categoria: str | None = Query(None, description="Filter by categoria"),
    owner: str | None = Query(None, description="Filter by owner"),
):
    """List all risks of a project with optional filters."""
    await _set_project_rls(project_id, db)
    svc = ProjectRiskService(db)
    return await svc.list_risks(
        project_id=project_id,
        status=status_filter,
        categoria=categoria,
        owner=owner,
    )


# ENDPOINT 4: PATCH /risks/{risk_id}
@router.patch("/risks/{risk_id}", response_model=ProjectRiskOut)
async def update_risk(
    risk_id: uuid.UUID,
    body: ProjectRiskUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Partial update of a project risk."""
    await _set_risk_rls(risk_id, db)
    svc = ProjectRiskService(db)
    try:
        updates = body.model_dump(exclude_unset=True)
        risk = await svc.update_risk(risk_id, **updates)
        await db.commit()
        return risk
    except ProjectRiskNotFoundError as e:  # pragma: no cover — _set_risk_rls catches 404 first
        raise HTTPException(status_code=404, detail=str(e))
    except ProjectRiskValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))


# ENDPOINT 5: DELETE /risks/{risk_id}
@router.delete("/risks/{risk_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_risk(
    risk_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Soft delete a project risk."""
    await _set_risk_rls(risk_id, db)
    svc = ProjectRiskService(db)
    try:
        await svc.delete_risk(risk_id)
        await db.commit()
        return None
    except ProjectRiskNotFoundError as e:  # pragma: no cover — _set_risk_rls catches 404 first
        raise HTTPException(status_code=404, detail=str(e))


# ================================================================
# LIFECYCLE TRANSITION ENDPOINTS
# ================================================================

# ENDPOINT 6: POST /risks/{risk_id}/monitor
@router.post("/risks/{risk_id}/monitor", response_model=ProjectRiskOut)
async def monitor_risk(
    risk_id: uuid.UUID,
    body: MonitorRiskRequest,
    db: AsyncSession = Depends(get_db),
):
    """Transition: identificado -> monitorizado."""
    await _set_risk_rls(risk_id, db)
    svc = ProjectRiskService(db)
    try:
        risk = await svc.monitor_risk(risk_id, notas=body.notas)
        await db.commit()
        return risk
    except ProjectRiskNotFoundError as e:  # pragma: no cover — _set_risk_rls catches 404 first
        raise HTTPException(status_code=404, detail=str(e))
    except ProjectRiskStateError as e:
        raise HTTPException(status_code=409, detail=str(e))


# ENDPOINT 7: POST /risks/{risk_id}/materialize
@router.post("/risks/{risk_id}/materialize", response_model=ProjectRiskOut)
async def materialize_risk(
    risk_id: uuid.UUID,
    body: MaterializeRiskRequest,
    db: AsyncSession = Depends(get_db),
):
    """Transition: monitorizado -> materializado."""
    await _set_risk_rls(risk_id, db)
    svc = ProjectRiskService(db)
    try:
        risk = await svc.materialize_risk(
            risk_id,
            trigger_evidence=body.trigger_evidence,
            materialized_by=body.materialized_by,
        )
        await db.commit()
        return risk
    except ProjectRiskNotFoundError as e:  # pragma: no cover — _set_risk_rls catches 404 first
        raise HTTPException(status_code=404, detail=str(e))
    except ProjectRiskStateError as e:
        raise HTTPException(status_code=409, detail=str(e))


# ENDPOINT 8: POST /risks/{risk_id}/close
@router.post("/risks/{risk_id}/close", response_model=ProjectRiskOut)
async def close_risk(
    risk_id: uuid.UUID,
    body: CloseRiskRequest,
    db: AsyncSession = Depends(get_db),
):
    """Transition: identificado|monitorizado|materializado -> cerrado."""
    await _set_risk_rls(risk_id, db)
    svc = ProjectRiskService(db)
    try:
        risk = await svc.close_risk(
            risk_id,
            resolution_notes=body.resolution_notes,
            closed_by=body.closed_by,
        )
        await db.commit()
        return risk
    except ProjectRiskNotFoundError as e:  # pragma: no cover — _set_risk_rls catches 404 first
        raise HTTPException(status_code=404, detail=str(e))
    except ProjectRiskStateError as e:
        raise HTTPException(status_code=409, detail=str(e))


# ================================================================
# CATALOG ENDPOINTS
# ================================================================

# ENDPOINT 9: POST /projects/{project_id}/risks/instantiate-catalog
@router.post(
    "/projects/{project_id}/risks/instantiate-catalog",
    status_code=status.HTTP_201_CREATED,
    response_model=InstantiateCatalogResponse,
)
async def instantiate_catalog(
    project_id: uuid.UUID,
    body: InstantiateCatalogRequest,
    db: AsyncSession = Depends(get_db),
):
    """Instantiate the base catalog of 30 risks for a project."""
    await _set_project_rls(project_id, db)
    svc = ProjectRiskService(db)
    try:
        result = await svc.instantiate_catalog_for_project(
            project_id=project_id,
            force=body.force,
            only_categorias=body.only_categorias,
        )
        await db.commit()
        return result
    except CatalogAlreadyInstantiatedError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except CatalogNotFoundError as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(e))
    except CatalogParseError as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(e))


# ENDPOINT 10: GET /projects/{project_id}/risks/catalog-status
@router.get("/projects/{project_id}/risks/catalog-status")
async def catalog_status(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Check if the catalog has been instantiated for a project."""
    await _set_project_rls(project_id, db)
    svc = ProjectRiskService(db)
    instantiated = await svc.is_catalog_instantiated(project_id)
    return {"instantiated": instantiated, "project_id": project_id}


# ================================================================
# DASHBOARD ENDPOINT
# ================================================================

# ENDPOINT 11: GET /projects/{project_id}/risks/dashboard
@router.get("/projects/{project_id}/risks/dashboard", response_model=RiskDashboardResponse)
async def get_dashboard(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Risk dashboard for Marcos weekly review."""
    await _set_project_rls(project_id, db)
    svc = ProjectRiskService(db)
    return await svc.get_dashboard(project_id)
