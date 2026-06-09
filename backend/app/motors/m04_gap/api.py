"""Motor 4 -- Gap Analysis Engine API endpoints.

Thin HTTP layer over GapAnalysisService. Pattern:
- Endpoints require tenant context (RLS findings)
- Service exceptions mapped to HTTP codes
- Zero business logic in api.py -- all in service.py

Consistent with M19 Project Risks and M3 DdA Engine patterns.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db, set_tenant_context
from backend.app.motors.m04_gap.schemas import (
    GapFindingOut,
    GapFindingUpdate,
    CloseGapRequest,
    AnalyzeProjectRequest,
    AnalyzeProjectResponse,
    GapDashboardResponse,
    GapDashboardItem,
)
from backend.app.motors.m04_gap.enums import SEVERITY_SCORING_STR
from backend.app.motors.m04_gap.service import GapAnalysisService
from backend.app.motors.m04_gap.exceptions import (
    GapNotFoundError,
    GapValidationError,
    GapStateError,
    DdANotReadyError,
    GapAlreadyAnalyzedError,
    SeverityCatalogNotFoundError,
    SeverityCatalogParseError,
)

from backend.app.auth.dependencies import require_owner

router = APIRouter(
    tags=["Motor 4 - Gap Analysis"],
    # TODO-RBAC-PER-ENDPOINT-001 Cat A: Marcos-only.
    dependencies=[Depends(require_owner)],
)


# ================================================================
# HELPERS
# ================================================================

async def _set_project_rls(project_id: uuid.UUID, db: AsyncSession):
    """Set RLS context for findings table via project owner lookup."""
    client_id = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
    )).scalar()
    if not client_id:  # pragma: no cover — project validated by caller or FK
        raise HTTPException(status_code=404, detail="Project not found")
    await set_tenant_context(db, client_id=client_id, project_id=project_id)


async def _set_gap_rls(gap_id: uuid.UUID, db: AsyncSession) -> uuid.UUID:
    """Set RLS context for a gap finding by looking up its project."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    result = await db.execute(
        text(
            "SELECT project_id FROM findings "
            "WHERE id = :gid AND deleted_at IS NULL AND fuente = 'gap_analysis'"
        ),
        {"gid": str(gap_id)},
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Gap {gap_id} not found")
    project_id = row[0]
    await db.execute(text("RESET ROLE"))
    await _set_project_rls(project_id, db)
    return project_id


# ================================================================
# ANALYSIS ENDPOINT
# ================================================================

@router.post(
    "/projects/{project_id}/gaps/analyze",
    status_code=status.HTTP_201_CREATED,
    response_model=AnalyzeProjectResponse,
)
async def analyze_project(
    project_id: uuid.UUID,
    body: AnalyzeProjectRequest,
    db: AsyncSession = Depends(get_db),
):
    """Run gap analysis for a project against its DdA."""
    await _set_project_rls(project_id, db)
    svc = GapAnalysisService(db)
    try:
        result = await svc.analyze_project(
            project_id=project_id,
            force=body.force,
            categoria_objetivo=body.categoria_objetivo,
        )
        await db.commit()
        return result
    except DdANotReadyError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except GapAlreadyAnalyzedError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except GapValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except SeverityCatalogNotFoundError as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(e))
    except SeverityCatalogParseError as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(e))


# ================================================================
# CRUD ENDPOINTS
# ================================================================

@router.get("/gaps/{gap_id}", response_model=GapFindingOut)
async def get_gap(
    gap_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a single gap finding by ID."""
    await _set_gap_rls(gap_id, db)
    svc = GapAnalysisService(db)
    try:
        return await svc.get_gap(gap_id)
    except GapNotFoundError as e:  # pragma: no cover -- _set_gap_rls catches 404 first
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/projects/{project_id}/gaps", response_model=list[GapFindingOut])
async def list_gaps(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    severidad: str | None = Query(None),
    estado: str | None = Query(None),
    familia: str | None = Query(None),
    only_quick_wins: bool = Query(False),
    only_nuclear: bool = Query(False),
):
    """List gap findings for a project with optional filters."""
    await _set_project_rls(project_id, db)
    svc = GapAnalysisService(db)
    return await svc.list_gaps(
        project_id=project_id,
        severidad=severidad,
        estado=estado,
        familia=familia,
        only_quick_wins=only_quick_wins,
        only_nuclear=only_nuclear,
    )


@router.patch("/gaps/{gap_id}", response_model=GapFindingOut)
async def update_gap(
    gap_id: uuid.UUID,
    body: GapFindingUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Partial update of a gap finding."""
    await _set_gap_rls(gap_id, db)
    svc = GapAnalysisService(db)
    try:
        updates = body.model_dump(exclude_unset=True)
        gap = await svc.update_gap(gap_id, **updates)
        await db.commit()
        return gap
    except GapNotFoundError as e:  # pragma: no cover
        raise HTTPException(status_code=404, detail=str(e))
    except GapValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.delete("/gaps/{gap_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_gap(
    gap_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Soft delete a gap finding."""
    await _set_gap_rls(gap_id, db)
    svc = GapAnalysisService(db)
    try:
        await svc.delete_gap(gap_id)
        await db.commit()
        return None
    except GapNotFoundError as e:  # pragma: no cover
        raise HTTPException(status_code=404, detail=str(e))


# ================================================================
# LIFECYCLE ENDPOINT
# ================================================================

@router.post("/gaps/{gap_id}/close", response_model=GapFindingOut)
async def close_gap(
    gap_id: uuid.UUID,
    body: CloseGapRequest,
    db: AsyncSession = Depends(get_db),
):
    """Close a gap finding."""
    await _set_gap_rls(gap_id, db)
    svc = GapAnalysisService(db)
    try:
        gap = await svc.close_gap(
            gap_id,
            resolution_notes=body.resolution_notes,
            closed_by=body.closed_by,
        )
        await db.commit()
        return gap
    except GapNotFoundError as e:  # pragma: no cover
        raise HTTPException(status_code=404, detail=str(e))
    except GapStateError as e:
        raise HTTPException(status_code=409, detail=str(e))


# ================================================================
# DASHBOARD & QUICK WINS
# ================================================================

@router.get("/projects/{project_id}/gaps/dashboard", response_model=GapDashboardResponse)
async def get_dashboard(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Gap analysis dashboard."""
    await _set_project_rls(project_id, db)
    svc = GapAnalysisService(db)
    return await svc.get_dashboard(project_id)


@router.get("/projects/{project_id}/gaps/quick-wins", response_model=list[GapDashboardItem])
async def get_quick_wins(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Quick-win gaps for a project (shortcut for only_quick_wins filter)."""
    await _set_project_rls(project_id, db)
    svc = GapAnalysisService(db)
    gaps = await svc.list_gaps(project_id, only_quick_wins=True)

    items = []
    for g in gaps:
        if g.estado == "cerrado":
            continue
        md = g.metadata_jsonb or {}
        items.append({
            "id": str(g.id),
            "medida_afectada": g.medida_afectada,
            "severidad": g.severidad,
            "severidad_numeric": SEVERITY_SCORING_STR.get(g.severidad or "", 1),
            "estado": g.estado,
            "esfuerzo_horas": md.get("esfuerzo_horas"),
            "quick_win": True,
            "nuclear": md.get("nuclear", False),
            "familia": md.get("familia"),
            "semaforo": "rojo" if g.severidad == "critica" else "amarillo",
        })
    return items


@router.post("/projects/{project_id}/gaps/prioritize-llm")
async def prioritize_gaps_llm(
    project_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    """Prioriza gaps del proyecto con LLM contextual (Sesion 9 Paso 3.3).

    Absorbe la logica del A7 Gap Analyzer eliminado en STEP B como
    funcion pura interna de M4 (NO agente separado).

    Body schema::

        {
          "client_context": {
            "sector": "sanidad|aapp|fintech|otro",
            "ens_category": "BASICA|MEDIA|ALTA",
            "size": "PYME|mediana|grande"     // opcional, default PYME
          },
          "only_open": true,                  // solo gaps no cerrados, default true
          "max_gaps": 30                      // limite input, default 30
        }

    Devuelve prioritized + summary + metadata LLM (tokens, coste,
    cache_*, fallback_used).
    """
    from backend.app.motors.m04_gap.llm_prioritizer import (
        prioritize_gaps_with_llm,
    )

    client_context = body.get("client_context")
    if not isinstance(client_context, dict) or not client_context:
        raise HTTPException(
            status_code=400,
            detail="Se requiere 'client_context' dict (sector + ens_category)",
        )

    await _set_project_rls(project_id, db)
    svc = GapAnalysisService(db)
    only_open = body.get("only_open", True)
    max_gaps = int(body.get("max_gaps", 30))
    all_gaps = await svc.list_gaps(project_id)

    gaps_dict: list[dict] = []
    for g in all_gaps:
        if only_open and g.estado == "cerrado":
            continue
        gaps_dict.append({
            "id": str(g.id),
            "medida_afectada": g.medida_afectada or "",
            "severidad": g.severidad or "",
            "descripcion": g.descripcion or "",
            "estado": g.estado or "",
        })
        if len(gaps_dict) >= max_gaps:
            break

    try:
        result = await prioritize_gaps_with_llm(
            gaps=gaps_dict,
            client_context=client_context,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "project_id": str(project_id),
        "input_gaps_count": len(gaps_dict),
        **result,
    }
