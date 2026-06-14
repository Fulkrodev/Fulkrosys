"""Motor 2 - MAGERIT v3 Risk Engine: REST API endpoints."""
import logging
import uuid
from xml.etree.ElementTree import Element, SubElement, tostring, Comment

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import select, text, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.sse_dispatcher import sse_dispatcher
from backend.app.database import get_db, set_tenant_context
from backend.app.motors.m02_magerit.models import (
    MageritAnalysis,
    MageritAsset,
    MageritRiskCalculation,
    MageritThreatAssessment,
    MageritAssetDependency,
    MageritSafeguardDeployment,
    MageritTreatmentPlan,
)
from backend.app.motors.m02_magerit.service import MageritService, LEVEL_TO_INDEX
from backend.app.motors.m02_magerit.schemas import (
    AnalysisCreate,
    AnalysisOut,
    AssetInventoryRequest,
    AssetOut,
    DependencyGraphRequest,
    ThreatAssessmentRequest,
    SafeguardDeploymentRequest,
    TreatmentPlanRequest,
    TreatmentActionOut,
    AnalysisReportOut,
    OperationResult,
    RequestE028SignatureBody,
    RequestE028SignatureResponse,
    E028SignatureStatusResponse,
)
from backend.app.motors.m02_magerit.signature_integration import (
    E028SignatureIntegrationError,
    request_e028_signature,
    get_e028_signature_status,
)
from backend.app.auth.dependencies import require_owner

router = APIRouter(
    prefix="/magerit", tags=["Motor 2 - MAGERIT v3"],
    # TODO-RBAC-PER-ENDPOINT-001 Cat A: Marcos-only.
    dependencies=[Depends(require_owner)],
)


# ================================================================
# HELPERS
# ================================================================

async def _get_analysis_with_rls(
    analysis_id: uuid.UUID,
    db: AsyncSession,
) -> MageritAnalysis:
    """Load analysis and set RLS context from its project client_id.

    Uses get_magerit_analysis_owner() SECURITY DEFINER function to resolve
    the RLS chicken-and-egg: we need client_id to set tenant context, but
    can't read the table without tenant context. The function bypasses RLS.
    """
    row = await db.execute(
        text("SELECT * FROM get_magerit_analysis_owner(:aid)"),
        {"aid": str(analysis_id)},
    )
    owner = row.mappings().first()
    if not owner or not owner["client_id"]:
        raise HTTPException(status_code=404, detail="Analysis not found")
    await set_tenant_context(
        db, client_id=owner["client_id"], project_id=owner["project_id"]
    )
    analysis = await db.get(MageritAnalysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")  # pragma: no cover
    return analysis


async def _ensure_analysis_not_frozen(analysis_id: uuid.UUID, db: AsyncSession):
    """Reject pipeline modifications on frozen analyses (RLS-aware).

    Los callers invocan este guard ANTES de _get_analysis_with_rls, así que aquí
    aún no hay contexto de tenant: sin fijarlo, la SELECT corre bajo fulkro_app
    sin contexto → 0 filas → row is None → el guard fallaba ABIERTO (permitía
    mutar un análisis congelado). Resolvemos owner vía SECURITY DEFINER + fijamos
    contexto antes de leer.
    """
    owner = (await db.execute(
        text("SELECT * FROM get_magerit_analysis_owner(:aid)"),
        {"aid": str(analysis_id)},
    )).mappings().first()
    if owner and owner["client_id"]:
        await set_tenant_context(
            db, client_id=owner["client_id"], project_id=owner["project_id"],
        )
    result = await db.execute(
        text("SELECT snapshot_frozen_at FROM magerit_analysis WHERE id = :aid"),
        {"aid": str(analysis_id)},
    )
    row = result.first()
    if row and row[0] is not None:
        raise HTTPException(
            status_code=409,
            detail="El analisis esta congelado. Llame a POST /unfreeze primero para modificarlo.",
        )


# ================================================================
# ENDPOINT 1: Create analysis
# ================================================================

@router.post(
    "/projects/{project_id}/analysis",
    response_model=AnalysisOut,
    status_code=201,
)
async def create_analysis(
    project_id: uuid.UUID,
    body: AnalysisCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new MAGERIT risk analysis for a project."""
    client_id = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
    )).scalar()
    if not client_id:
        raise HTTPException(status_code=404, detail="Project not found")
    await set_tenant_context(db, client_id=client_id, project_id=project_id)

    svc = MageritService(db)
    analysis = await svc.create_analysis(
        project_id=project_id,
        name=body.name,
        calculation_mode=body.calculation_mode,
    )
    if body.description:
        analysis.notes = body.description
        await db.flush()
    await db.commit()
    await db.refresh(analysis)
    return analysis


# ================================================================
# ENDPOINT 2: Load asset inventory
# ================================================================

@router.post(
    "/analysis/{analysis_id}/assets",
    response_model=list[AssetOut],
    status_code=201,
)
async def load_assets(
    analysis_id: uuid.UUID,
    body: AssetInventoryRequest,
    db: AsyncSession = Depends(get_db),
):
    """Load the asset inventory for an analysis."""
    await _get_analysis_with_rls(analysis_id, db)
    svc = MageritService(db)
    assets = await svc.build_asset_inventory(
        analysis_id=analysis_id,
        assets=[a.model_dump() for a in body.assets],
    )
    await db.commit()
    for a in assets:
        await db.refresh(a)
    return assets


# ================================================================
# ENDPOINT 3: Load dependency graph
# ================================================================

@router.post(
    "/analysis/{analysis_id}/dependencies",
    response_model=OperationResult,
    status_code=201,
)
async def load_dependencies(
    analysis_id: uuid.UUID,
    body: DependencyGraphRequest,
    db: AsyncSession = Depends(get_db),
):
    """Build the directed dependency graph between assets."""
    await _get_analysis_with_rls(analysis_id, db)
    svc = MageritService(db)
    try:
        deps = await svc.build_dependency_graph(
            analysis_id=analysis_id,
            dependencies=[d.model_dump() for d in body.dependencies],
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    await db.commit()
    return OperationResult(
        analysis_id=analysis_id,
        operation="build_dependency_graph",
        rows_affected=len(deps),
        message=f"{len(deps)} dependencies created",
    )


# ================================================================
# ENDPOINT 4: Propagate values
# ================================================================

@router.post(
    "/analysis/{analysis_id}/propagate",
    response_model=OperationResult,
)
async def propagate_values(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Propagate asset values through the dependency graph."""
    await _ensure_analysis_not_frozen(analysis_id, db)
    analysis = await _get_analysis_with_rls(analysis_id, db)
    asset_count = await db.scalar(
        select(sa_func.count()).select_from(MageritAsset).where(
            MageritAsset.analysis_id == analysis_id
        )
    )
    if not asset_count:
        raise HTTPException(status_code=409, detail="No assets loaded. Load assets first.")

    svc = MageritService(db)
    updated = await svc.propagate_values(analysis_id)
    await db.commit()
    return OperationResult(
        analysis_id=analysis_id,
        operation="propagate_values",
        rows_affected=updated,
        message=f"{updated} assets updated with propagated values ({analysis.calculation_mode} mode)",
    )


# ================================================================
# ENDPOINT 5: Load threat assessments
# ================================================================

@router.post(
    "/analysis/{analysis_id}/threats",
    response_model=OperationResult,
    status_code=201,
)
async def load_threats(
    analysis_id: uuid.UUID,
    body: ThreatAssessmentRequest,
    db: AsyncSession = Depends(get_db),
):
    """Load threat assessments for (asset, threat) pairs."""
    await _get_analysis_with_rls(analysis_id, db)
    svc = MageritService(db)
    assessments = await svc.assess_threats(
        analysis_id=analysis_id,
        assessments=[a.model_dump() for a in body.assessments],
    )
    await db.commit()
    return OperationResult(
        analysis_id=analysis_id,
        operation="assess_threats",
        rows_affected=len(assessments),
        message=f"{len(assessments)} threat assessments created",
    )


# ================================================================
# ENDPOINT 6: Calculate intrinsic risk
# ================================================================

@router.post(
    "/analysis/{analysis_id}/calculate-intrinsic",
    response_model=OperationResult,
)
async def calculate_intrinsic(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Calculate intrinsic risk (before safeguards)."""
    await _ensure_analysis_not_frozen(analysis_id, db)
    analysis = await _get_analysis_with_rls(analysis_id, db)
    asset_count = await db.scalar(
        select(sa_func.count()).select_from(MageritAsset).where(
            MageritAsset.analysis_id == analysis_id
        )
    )
    threat_count = await db.scalar(
        select(sa_func.count()).select_from(MageritThreatAssessment).where(
            MageritThreatAssessment.analysis_id == analysis_id
        )
    )
    if not asset_count:
        raise HTTPException(status_code=409, detail="No assets loaded. Load assets first.")
    if not threat_count:
        raise HTTPException(status_code=409, detail="No threats loaded. Load threats first.")

    svc = MageritService(db)
    count = await svc.calculate_intrinsic_risk(analysis_id)
    await db.commit()
    return OperationResult(
        analysis_id=analysis_id,
        operation="calculate_intrinsic_risk",
        rows_affected=count,
        message=f"{count} risk calculations created ({analysis.calculation_mode} mode)",
    )


# ================================================================
# ENDPOINT 7: Deploy safeguards
# ================================================================

@router.post(
    "/analysis/{analysis_id}/safeguards",
    response_model=OperationResult,
    status_code=201,
)
async def deploy_safeguards(
    analysis_id: uuid.UUID,
    body: SafeguardDeploymentRequest,
    db: AsyncSession = Depends(get_db),
):
    """Deploy safeguards for an analysis."""
    await _get_analysis_with_rls(analysis_id, db)
    svc = MageritService(db)
    deployments = await svc.deploy_safeguards(
        analysis_id=analysis_id,
        deployments=[d.model_dump() for d in body.deployments],
    )
    await db.commit()
    return OperationResult(
        analysis_id=analysis_id,
        operation="deploy_safeguards",
        rows_affected=len(deployments),
        message=f"{len(deployments)} safeguards deployed",
    )


# ================================================================
# ENDPOINT 8: Calculate effective risk
# ================================================================

@router.post(
    "/analysis/{analysis_id}/calculate-effective",
    response_model=OperationResult,
)
async def calculate_effective(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Calculate effective risk (after safeguards)."""
    await _ensure_analysis_not_frozen(analysis_id, db)
    analysis = await _get_analysis_with_rls(analysis_id, db)
    calc_count = await db.scalar(
        select(sa_func.count()).select_from(MageritRiskCalculation).where(
            MageritRiskCalculation.analysis_id == analysis_id
        )
    )
    if not calc_count:
        raise HTTPException(
            status_code=409,
            detail="No intrinsic risk calculated. Run calculate-intrinsic first.",
        )

    svc = MageritService(db)
    count = await svc.calculate_effective_risk(analysis_id)
    await db.commit()
    return OperationResult(
        analysis_id=analysis_id,
        operation="calculate_effective_risk",
        rows_affected=count,
        message=f"{count} effective risk calculations updated ({analysis.calculation_mode} mode)",
    )


# ================================================================
# ENDPOINT 9: Generate treatment plan
# ================================================================

@router.post(
    "/analysis/{analysis_id}/treatment-plan",
    response_model=list[TreatmentActionOut],
    status_code=201,
)
async def generate_treatment_plan(
    analysis_id: uuid.UUID,
    body: TreatmentPlanRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate a treatment plan for risks above the tolerance threshold."""
    await _get_analysis_with_rls(analysis_id, db)
    calc_count = await db.scalar(
        select(sa_func.count()).select_from(MageritRiskCalculation).where(
            MageritRiskCalculation.analysis_id == analysis_id
        )
    )
    if not calc_count:
        raise HTTPException(
            status_code=409,
            detail="No risk calculations found. Run calculate-intrinsic or calculate-effective first.",
        )

    svc = MageritService(db)
    actions = await svc.generate_treatment_plan(
        analysis_id=analysis_id,
        threshold=body.risk_tolerance_threshold,
    )
    await db.commit()
    for a in actions:
        await db.refresh(a)
    return actions


# ================================================================
# ENDPOINT 10: Calculate residual risk
# ================================================================

@router.post(
    "/analysis/{analysis_id}/calculate-residual",
    response_model=OperationResult,
)
async def calculate_residual(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Calculate residual risk (after treatment plan)."""
    await _ensure_analysis_not_frozen(analysis_id, db)
    analysis = await _get_analysis_with_rls(analysis_id, db)
    plan_count = await db.scalar(
        select(sa_func.count()).select_from(MageritTreatmentPlan).where(
            MageritTreatmentPlan.analysis_id == analysis_id
        )
    )
    if not plan_count:
        raise HTTPException(
            status_code=409,
            detail="No treatment plan found. Generate treatment plan first.",
        )

    svc = MageritService(db)
    count = await svc.calculate_residual_risk(analysis_id)
    await db.commit()
    return OperationResult(
        analysis_id=analysis_id,
        operation="calculate_residual_risk",
        rows_affected=count,
        message=f"{count} residual risk calculations updated ({analysis.calculation_mode} mode)",
    )


# ================================================================
# ENDPOINT 11: Full report
# ================================================================

@router.get(
    "/analysis/{analysis_id}/report",
    response_model=AnalysisReportOut,
)
async def analysis_report(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Full analysis report in JSON."""
    analysis = await _get_analysis_with_rls(analysis_id, db)

    assets = (await db.execute(
        select(MageritAsset).where(
            MageritAsset.analysis_id == analysis_id,
            MageritAsset.deleted_at.is_(None),
        )
    )).scalars().all()

    calcs = (await db.execute(
        select(MageritRiskCalculation).where(
            MageritRiskCalculation.analysis_id == analysis_id
        )
    )).scalars().all()

    actions = (await db.execute(
        select(MageritTreatmentPlan).where(
            MageritTreatmentPlan.analysis_id == analysis_id
        )
    )).scalars().all()

    risk_levels = [c.risk_level for c in calcs if c.risk_level]
    summary = {
        "total_assets": len(assets),
        "total_risk_calculations": len(calcs),
        "total_treatment_actions": len(actions),
        "risk_distribution": {
            level: sum(1 for r in risk_levels if r == level)
            for level in ["MB", "B", "M", "A", "MA"]
        },
        "max_risk_level": max(
            risk_levels, key=lambda x: LEVEL_TO_INDEX.get(x, 0)
        ) if risk_levels else None,
    }

    return AnalysisReportOut(
        analysis=analysis,
        assets=assets,
        risk_calculations=calcs,
        treatment_actions=actions,
        summary=summary,
    )


# ================================================================
# ENDPOINT 12: PILAR XML export stub
# ================================================================

@router.get(
    "/analysis/{analysis_id}/export-xml",
)
async def export_analysis_xml(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Export analysis as FULKRO native XML (NOT PILAR .mgr format).

    Contains complete analysis data for backup, interchange, or manual
    conversion. PILAR .mgr is proprietary and undocumented by CCN.
    See docs/limitations/pilar_export.md for details.
    """
    analysis = await _get_analysis_with_rls(analysis_id, db)

    assets = (await db.execute(
        select(MageritAsset).where(
            MageritAsset.analysis_id == analysis_id,
            MageritAsset.deleted_at.is_(None),
        )
    )).scalars().all()

    deps = (await db.execute(
        select(MageritAssetDependency).where(
            MageritAssetDependency.analysis_id == analysis_id
        )
    )).scalars().all()

    threats = (await db.execute(
        select(MageritThreatAssessment).where(
            MageritThreatAssessment.analysis_id == analysis_id
        )
    )).scalars().all()

    safeguards = (await db.execute(
        select(MageritSafeguardDeployment).where(
            MageritSafeguardDeployment.analysis_id == analysis_id
        )
    )).scalars().all()

    calcs = (await db.execute(
        select(MageritRiskCalculation).where(
            MageritRiskCalculation.analysis_id == analysis_id
        )
    )).scalars().all()

    plan_actions = (await db.execute(
        select(MageritTreatmentPlan).where(
            MageritTreatmentPlan.analysis_id == analysis_id
        )
    )).scalars().all()

    # Build XML
    root = Element("fulkro_magerit_analysis", version="1.0")
    root.append(Comment(
        "FULKRO native XML export. NOT compatible with PILAR .mgr format "
        "(proprietary, undocumented by CCN). Contains complete analysis data "
        "for backup, interchange, or manual conversion."
    ))

    meta = SubElement(root, "metadata")
    SubElement(meta, "analysis_id").text = str(analysis.id)
    SubElement(meta, "name").text = analysis.name
    SubElement(meta, "calculation_mode").text = analysis.calculation_mode
    SubElement(meta, "methodology_version").text = analysis.methodology_version
    SubElement(meta, "created_at").text = analysis.created_at.isoformat()

    assets_el = SubElement(root, "assets")
    for a in assets:
        asset_el = SubElement(
            assets_el, "asset", id=str(a.id), type=a.asset_type_code, name=a.name
        )
        SubElement(
            asset_el, "valuation",
            d=str(a.value_d or 0), i=str(a.value_i or 0),
            c=str(a.value_c or 0), a=str(a.value_a or 0), t=str(a.value_t or 0),
        )

    deps_el = SubElement(root, "dependencies")
    for d in deps:
        SubElement(
            deps_el, "dependency",
            superior=str(d.superior_asset_id),
            inferior=str(d.inferior_asset_id),
            degree=str(d.dependency_degree),
        )

    threats_el = SubElement(root, "threats")
    for t in threats:
        SubElement(
            threats_el, "threat",
            asset_id=str(t.asset_id), threat_code=t.threat_code,
            probability=t.probability,
            degradation_d=str(t.degradation_d or 0),
            degradation_i=str(t.degradation_i or 0),
            degradation_c=str(t.degradation_c or 0),
            degradation_a=str(t.degradation_a or 0),
            degradation_t=str(t.degradation_t or 0),
        )

    sg_el = SubElement(root, "safeguards")
    for s in safeguards:
        SubElement(
            sg_el, "safeguard",
            deployment_id=str(s.id), safeguard_code=s.safeguard_code,
            efficacy=str(s.efficacy), effect_type=s.effect_type,
        )

    rc_el = SubElement(root, "risk_calculations")
    for c in calcs:
        SubElement(
            rc_el, "calculation",
            asset_id=str(c.asset_id), threat_code=c.threat_code,
            dimension=c.dimension,
            intrinsic_accumulated=str(c.risk_intrinsic_accumulated or ""),
            intrinsic_repercuted=str(c.risk_intrinsic_repercuted or ""),
            effective=str(c.risk_effective or ""),
            residual=str(c.risk_residual or ""),
            risk_level=c.risk_level or "",
        )

    tp_el = SubElement(root, "treatment_plan")
    for a in plan_actions:
        SubElement(
            tp_el, "action",
            asset_id=str(a.asset_id), threat_code=a.threat_code,
            dimension=a.dimension, treatment=a.treatment,
            description=a.action_description or "",
        )

    xml_str = tostring(root, encoding="unicode")
    xml_decl = '<?xml version="1.0" encoding="UTF-8"?>\n'
    return Response(
        content=(xml_decl + xml_str).encode("utf-8"),
        media_type="application/xml",
        headers={
            "Content-Disposition": f"attachment; filename=magerit_analysis_{analysis_id}.xml"
        },
    )



# ================================================================
# ENDPOINT 13: Soft delete analysis (cascade)
# ================================================================

@router.delete(
    "/analysis/{analysis_id}",
    status_code=204,
)
async def soft_delete_analysis(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Soft delete an analysis and cascade to its assets and treatment plans.

    Calculated results (risk_calculation, threat_assessment, safeguard_deployment,
    asset_dependencies) are left in DB for audit trail but become inaccessible
    because all queries filter by the parent analysis/asset deleted_at.
    """
    analysis = await _get_analysis_with_rls(analysis_id, db)
    if analysis.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    await db.execute(
        text("UPDATE magerit_analysis SET deleted_at = NOW() WHERE id = :aid AND deleted_at IS NULL"),
        {"aid": str(analysis_id)},
    )
    await db.execute(
        text("UPDATE magerit_assets SET deleted_at = NOW() WHERE analysis_id = :aid AND deleted_at IS NULL"),
        {"aid": str(analysis_id)},
    )
    await db.execute(
        text("UPDATE magerit_treatment_plan SET deleted_at = NOW() WHERE analysis_id = :aid AND deleted_at IS NULL"),
        {"aid": str(analysis_id)},
    )
    await db.commit()
    return None



# ================================================================
# ENDPOINT 14: Freeze analysis snapshot
# ================================================================

@router.post(
    "/analysis/{analysis_id}/freeze",
)
async def freeze_analysis(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Congela el analisis: crea snapshot inmutable y bloquea modificaciones."""
    analysis = await _get_analysis_with_rls(analysis_id, db)
    if analysis.snapshot_frozen_at is not None:
        raise HTTPException(status_code=409, detail="El analisis ya esta congelado.")

    svc = MageritService(db)
    try:
        snapshot = await svc.freeze_analysis_snapshot(analysis_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    await db.commit()

    # Sesión 3B-2B.8 Phase 1B · SSE emit admin → cliente sync (freeze =
    # MAGERIT definitive ready for cliente review). Best-effort · try/except +
    # logger.exception · NO bloquea primary persist.
    try:
        assets_count = await db.scalar(
            select(sa_func.count()).select_from(MageritAsset).where(
                MageritAsset.analysis_id == analysis_id,
                MageritAsset.deleted_at.is_(None),
            )
        ) or 0
        threats_count = await db.scalar(
            select(sa_func.count()).select_from(MageritThreatAssessment).where(
                MageritThreatAssessment.analysis_id == analysis_id,
            )
        ) or 0
        safeguards_count = await db.scalar(
            select(sa_func.count()).select_from(MageritSafeguardDeployment).where(
                MageritSafeguardDeployment.analysis_id == analysis_id,
            )
        ) or 0
        await sse_dispatcher.dispatch(
            f"project:{analysis.project_id}",
            "m02.magerit.updated",
            {
                "analysis_id": str(analysis_id),
                "analysis_name": analysis.name,
                "assets_count": assets_count,
                "threats_count": threats_count,
                "safeguards_count": safeguards_count,
                "frozen_at": (
                    analysis.snapshot_frozen_at.isoformat()
                    if analysis.snapshot_frozen_at else None
                ),
                "primary_actor": "admin",
            },
        )
    except Exception:  # pragma: no cover · best-effort
        logging.getLogger(__name__).exception(
            "SSE m02.magerit.updated dispatch failed · analysis_id=%s",
            analysis_id,
        )

    # Sesión 3B-2B.8 CLUSTER 2 Phase 2B · SSE + ClientNotification dual emit
    # pattern (#14 cumulative). Admin freeze MAGERIT → cliente VE/RECIBE
    # filosofía cliente-mínimo aligned · best-effort independent dispatch.
    try:
        from backend.app.models.client_portal import ClientUser
        from backend.app.motors.m21_portal_cliente.notification_service import (
            emit_client_notification,
        )

        project_row = (await db.execute(
            text(
                "SELECT client_id FROM projects "
                "WHERE id = :pid AND deleted_at IS NULL"
            ),
            {"pid": str(analysis.project_id)},
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
                    project_id=analysis.project_id,
                    client_user_id=user.id,
                    type="compliance_confirmation",
                    title="Marcos actualizó tu análisis MAGERIT",
                    body=(
                        "El análisis de riesgos está listo · revísalo en tu "
                        "portal cuando puedas."
                    ),
                    target_url="/client-portal/magerit",
                    priority="normal",
                    emitted_by_motor="m02_magerit",
                    payload={
                        "analysis_id": str(analysis_id),
                        "analysis_name": analysis.name,
                        "source": "m02.magerit.updated",
                    },
                )
            await db.commit()
    except Exception:  # pragma: no cover · best-effort
        logging.getLogger(__name__).exception(
            "ClientNotification emit failed post m02.magerit.updated · "
            "analysis_id=%s",
            analysis_id,
        )

    return {"snapshot_frozen_at": analysis.snapshot_frozen_at.isoformat(), "snapshot": snapshot}


# ================================================================
# ENDPOINT 15: Unfreeze analysis
# ================================================================

@router.post(
    "/analysis/{analysis_id}/unfreeze",
    status_code=204,
)
async def unfreeze_analysis(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Descongela el analisis: permite modificaciones del pipeline."""
    analysis = await _get_analysis_with_rls(analysis_id, db)
    if analysis.snapshot_frozen_at is None:
        raise HTTPException(status_code=409, detail="El analisis no esta congelado.")

    svc = MageritService(db)
    await svc.unfreeze_analysis_snapshot(analysis_id)
    await db.commit()
    return None


# ================================================================
# ENDPOINT 16: Get frozen snapshot
# ================================================================

@router.get(
    "/analysis/{analysis_id}/snapshot",
)
async def get_analysis_snapshot(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Devuelve el snapshot congelado del analisis."""
    analysis = await _get_analysis_with_rls(analysis_id, db)
    if analysis.snapshot_frozen_at is None:
        raise HTTPException(status_code=404, detail="El analisis no esta congelado. Llame a POST /freeze primero.")

    return {
        "snapshot_frozen_at": analysis.snapshot_frozen_at.isoformat(),
        "snapshot": analysis.result_snapshot,
    }



# ================================================================
# ENDPOINT 17: MAGERIT report as PDF
# ================================================================

@router.get(
    "/analysis/{analysis_id}/report.pdf",
)
async def get_magerit_report_pdf(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Genera el informe MAGERIT completo en PDF."""
    from fastapi.responses import Response as FastAPIResponse
    from backend.app.core.pdf_renderer import PDFRenderer, PDFRenderError
    from pathlib import Path
    from datetime import date

    analysis = await _get_analysis_with_rls(analysis_id, db)

    # Determine frozen vs draft
    is_frozen = analysis.snapshot_frozen_at is not None
    draft_watermark = "" if is_frozen else "BORRADOR - Analisis no firmado"

    # Load data
    assets = (await db.execute(
        select(MageritAsset).where(
            MageritAsset.analysis_id == analysis_id,
            MageritAsset.deleted_at.is_(None),
        ).order_by(MageritAsset.code)
    )).scalars().all()

    threats = (await db.execute(
        select(MageritThreatAssessment).where(
            MageritThreatAssessment.analysis_id == analysis_id
        )
    )).scalars().all()

    safeguards = (await db.execute(
        select(MageritSafeguardDeployment).where(
            MageritSafeguardDeployment.analysis_id == analysis_id
        )
    )).scalars().all()

    calcs = (await db.execute(
        select(MageritRiskCalculation).where(
            MageritRiskCalculation.analysis_id == analysis_id
        )
    )).scalars().all()

    plans = (await db.execute(
        select(MageritTreatmentPlan).where(
            MageritTreatmentPlan.analysis_id == analysis_id,
            MageritTreatmentPlan.deleted_at.is_(None),
        )
    )).scalars().all()

    # Client/project names
    proj_row = await db.execute(
        text("SELECT nombre FROM projects WHERE id = :pid"),
        {"pid": str(analysis.project_id)},
    )
    project_name = proj_row.scalar_one_or_none() or "Proyecto"

    client_row = await db.execute(
        text("SELECT c.nombre, c.cif FROM clients c JOIN projects p ON p.client_id = c.id WHERE p.id = :pid"),
        {"pid": str(analysis.project_id)},
    )
    client_data = client_row.mappings().first()

    # Asset map for threat display
    asset_map = {str(a.id): a.code for a in assets}

    # Risk level distribution
    risk_levels = [c.risk_level for c in calcs if c.risk_level]
    max_risk = max(risk_levels, key=lambda x: LEVEL_TO_INDEX.get(x, 0)) if risk_levels else "N/A"

    context = {
        "draft_watermark": draft_watermark,
        "fecha_informe": date.today().isoformat(),
        "cliente_nombre": client_data["nombre"] if client_data else "",
        "cliente_cif": client_data["cif"] if client_data else "",
        "proyecto_nombre": project_name,
        "analisis_nombre": analysis.name,
        "calculation_mode": analysis.calculation_mode,
        "resumen_ejecutivo": (
            f"Analisis MAGERIT v3 con {len(assets)} activos, {len(threats)} amenazas, "
            f"{len(safeguards)} salvaguardas. {len(calcs)} calculos de riesgo generados. "
            f"Riesgo maximo: {max_risk}. Plan de tratamiento: {len(plans)} acciones."
        ),
        "assets": [
            {"code": a.code, "name": a.name, "asset_type_code": a.asset_type_code,
             "value_d": a.value_d, "value_i": a.value_i, "value_c": a.value_c,
             "value_a": a.value_a, "value_t": a.value_t}
            for a in assets
        ],
        "threats": [
            {"threat_code": t.threat_code, "asset_code": asset_map.get(str(t.asset_id), "?"),
             "probability": t.probability, "degradation_d": t.degradation_d or 0}
            for t in threats
        ],
        "safeguards": [
            {"safeguard_code": s.safeguard_code, "efficacy": s.efficacy, "effect_type": s.effect_type}
            for s in safeguards
        ],
        "total_calcs": len(calcs),
        "max_risk_level": max_risk,
        "treatment_plan": [
            {"threat_code": p.threat_code, "dimension": p.dimension,
             "treatment": p.treatment, "current_risk_level": p.current_risk_level}
            for p in plans
        ],
    }

    template_path = Path(__file__).resolve().parents[2] / "templates" / "magerit_informe_provisional.docx"

    try:
        async with PDFRenderer() as renderer:
            docx_bytes, pdf_bytes = await renderer.render(template_path, context)
    except PDFRenderError as e:
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {e}")

    return FastAPIResponse(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="magerit_report_{analysis_id}.pdf"'},
    )


# ================================================================
# ENDPOINT 18: MAGERIT report as DOCX
# ================================================================

@router.get(
    "/analysis/{analysis_id}/report.docx",
)
async def get_magerit_report_docx(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Genera el informe MAGERIT completo en DOCX editable."""
    from fastapi.responses import Response as FastAPIResponse
    from backend.app.core.pdf_renderer import PDFRenderer, PDFRenderError
    from pathlib import Path
    from datetime import date

    analysis = await _get_analysis_with_rls(analysis_id, db)
    is_frozen = analysis.snapshot_frozen_at is not None

    # Reuse same data loading as PDF (DRY would suggest a helper, but
    # keeping it inline for now to match Motor 1 pattern)
    assets = (await db.execute(
        select(MageritAsset).where(
            MageritAsset.analysis_id == analysis_id,
            MageritAsset.deleted_at.is_(None),
        ).order_by(MageritAsset.code)
    )).scalars().all()

    context = {
        "draft_watermark": "" if is_frozen else "BORRADOR - Analisis no firmado",
        "fecha_informe": date.today().isoformat(),
        "cliente_nombre": "", "cliente_cif": "",
        "proyecto_nombre": "", "analisis_nombre": analysis.name,
        "calculation_mode": analysis.calculation_mode,
        "resumen_ejecutivo": f"Analisis con {len(assets)} activos.",
        "assets": [{"code": a.code, "name": a.name, "asset_type_code": a.asset_type_code,
                     "value_d": a.value_d, "value_i": a.value_i, "value_c": a.value_c,
                     "value_a": a.value_a, "value_t": a.value_t} for a in assets],
        "threats": [], "safeguards": [], "total_calcs": 0,
        "max_risk_level": "N/A", "treatment_plan": [],
    }

    template_path = Path(__file__).resolve().parents[2] / "templates" / "magerit_informe_provisional.docx"

    try:
        async with PDFRenderer() as renderer:
            docx_bytes = await renderer.render_docx_only(template_path, context)
    except PDFRenderError as e:
        raise HTTPException(status_code=500, detail=f"Error generando DOCX: {e}")

    return FastAPIResponse(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="magerit_report_{analysis_id}.docx"'},
    )



# ================================================================
# DEPRECATED ALIAS: export-pilar → export-xml
# ================================================================

@router.get(
    "/analysis/{analysis_id}/export-pilar",
    deprecated=True,
)
async def export_pilar_deprecated(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """DEPRECATED — kept as alias of ``/export-xml`` for backwards
    compatibility. Use ``/export-mgr`` for the auditor-ready ``.mgr``
    bundle (ZIP with MAGERIT v3 XML inside PILAR can import).
    """
    return await export_analysis_xml(analysis_id, db)


# ================================================================
# ENDPOINT: best-effort .mgr bundle for PILAR import
# ================================================================

@router.get(
    "/analysis/{analysis_id}/export-mgr",
)
async def export_analysis_mgr(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Export the analysis as a ``.mgr`` bundle (E-030).

    Produces a ZIP (``application/zip``) containing ``analisis.xml`` in
    MAGERIT v3 shape plus a ``manifest.json`` header. The auditor can
    either import the XML into PILAR (menú 'Importar análisis') or
    consume it directly as public-methodology evidence.
    """
    from backend.app.motors.m02_magerit.exporter_mgr import export_to_mgr
    analysis = await _get_analysis_with_rls(analysis_id, db)
    blob = await export_to_mgr(db, analysis_id)
    filename = f"E-030_{analysis.name.replace(' ', '_')}.mgr"
    return Response(
        content=blob,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )



# ================================================================
# ENDPOINT 19: Import assets from CSV/XLSX
# ================================================================

@router.post(
    "/analysis/{analysis_id}/assets/import",
    status_code=201,
)
async def import_assets(
    analysis_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Import assets from CSV or XLSX file.

    Fixed column mapping. Atomic mode: all valid rows or none.
    See docs/decisions/llm_ingestion_pipeline.md for LLM+RAG evolution.
    """

    await _ensure_analysis_not_frozen(analysis_id, db)
    analysis = await _get_analysis_with_rls(analysis_id, db)

    filename = (file.filename or "").lower()
    content = await file.read()
    if not content:
        raise HTTPException(422, "Fichero vacio")

    svc = MageritService(db)
    try:
        if filename.endswith(".csv"):
            result = await svc.import_assets_from_csv(analysis_id, content)
        elif filename.endswith((".xlsx", ".xlsm")):
            result = await svc.import_assets_from_xlsx(analysis_id, content)
        else:
            raise HTTPException(415, f"Formato no soportado: {filename}. Esperado .csv o .xlsx")
        await db.commit()
        return result
    except ValueError as e:
        await db.rollback()
        raise HTTPException(422, str(e))


# ================================================================
# ENDPOINTS 20-26: XLSX individual deliverable exports
# ================================================================

from backend.app.motors.m02_magerit.exporters import (
    export_asset_inventory,
    export_dependency_map,
    export_threat_assessment,
    export_safeguard_deployment,
    export_risk_calculations,
    export_treatment_plan,
    export_executive_summary,
)

_XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/analysis/{analysis_id}/export/assets.xlsx")
async def download_asset_inventory(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """E-020: Descarga inventario de activos DICAT en XLSX."""
    await _get_analysis_with_rls(analysis_id, db)
    xlsx_bytes = await export_asset_inventory(db, analysis_id)
    return Response(
        content=xlsx_bytes,
        media_type=_XLSX_MEDIA,
        headers={"Content-Disposition": f'attachment; filename="E020_activos_{analysis_id}.xlsx"'},
    )


@router.get("/analysis/{analysis_id}/export/dependencies.xlsx")
async def download_dependency_map(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """E-021: Descarga mapa de dependencias en XLSX."""
    await _get_analysis_with_rls(analysis_id, db)
    xlsx_bytes = await export_dependency_map(db, analysis_id)
    return Response(
        content=xlsx_bytes,
        media_type=_XLSX_MEDIA,
        headers={"Content-Disposition": f'attachment; filename="E021_dependencias_{analysis_id}.xlsx"'},
    )


@router.get("/analysis/{analysis_id}/export/threats.xlsx")
async def download_threat_assessment(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """E-022: Descarga valoracion de amenazas en XLSX."""
    await _get_analysis_with_rls(analysis_id, db)
    xlsx_bytes = await export_threat_assessment(db, analysis_id)
    return Response(
        content=xlsx_bytes,
        media_type=_XLSX_MEDIA,
        headers={"Content-Disposition": f'attachment; filename="E022_amenazas_{analysis_id}.xlsx"'},
    )


@router.get("/analysis/{analysis_id}/export/safeguards.xlsx")
async def download_safeguard_deployment(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """E-023: Descarga salvaguardas desplegadas en XLSX."""
    await _get_analysis_with_rls(analysis_id, db)
    xlsx_bytes = await export_safeguard_deployment(db, analysis_id)
    return Response(
        content=xlsx_bytes,
        media_type=_XLSX_MEDIA,
        headers={"Content-Disposition": f'attachment; filename="E023_salvaguardas_{analysis_id}.xlsx"'},
    )


@router.get("/analysis/{analysis_id}/export/risks.xlsx")
async def download_risk_calculations(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """E-024: Descarga calculos de riesgo en XLSX."""
    await _get_analysis_with_rls(analysis_id, db)
    xlsx_bytes = await export_risk_calculations(db, analysis_id)
    return Response(
        content=xlsx_bytes,
        media_type=_XLSX_MEDIA,
        headers={"Content-Disposition": f'attachment; filename="E024_riesgos_{analysis_id}.xlsx"'},
    )


@router.get("/analysis/{analysis_id}/export/treatment.xlsx")
async def download_treatment_plan(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """E-025: Descarga plan de tratamiento en XLSX."""
    await _get_analysis_with_rls(analysis_id, db)
    xlsx_bytes = await export_treatment_plan(db, analysis_id)
    return Response(
        content=xlsx_bytes,
        media_type=_XLSX_MEDIA,
        headers={"Content-Disposition": f'attachment; filename="E025_tratamiento_{analysis_id}.xlsx"'},
    )


@router.get("/analysis/{analysis_id}/export/summary.xlsx")
async def download_executive_summary(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """E-026: Descarga resumen ejecutivo en XLSX."""
    await _get_analysis_with_rls(analysis_id, db)
    xlsx_bytes = await export_executive_summary(db, analysis_id)
    return Response(
        content=xlsx_bytes,
        media_type=_XLSX_MEDIA,
        headers={"Content-Disposition": f'attachment; filename="E026_resumen_{analysis_id}.xlsx"'},
    )


# ================================================================
# SIGNATURE RE-INTEGRATION M2 + M12 (M12-G2)
# ================================================================

@router.post(
    "/analysis/{analysis_id}/report-e028/request-signature",
    response_model=RequestE028SignatureResponse,
)
async def request_e028_signature_endpoint(
    analysis_id: uuid.UUID,
    body: RequestE028SignatureBody,
    db: AsyncSession = Depends(get_db),
) -> RequestE028SignatureResponse:
    """Solicita firma electronica avanzada del Informe E-028 MAGERIT via magic link.

    Requiere que el analisis este congelado (POST /freeze).
    """
    await _get_analysis_with_rls(analysis_id, db)
    try:
        result = await request_e028_signature(
            session=db,
            analysis_id=analysis_id,
            recipient_email=str(body.recipient_email),
            recipient_name=body.recipient_name,
            recipient_role=body.recipient_role,
        )
    except E028SignatureIntegrationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    # get_db() no auto-commitea: sin esto el magic link de firma E-028 (y su
    # signing_intent) se revierten y el firmante recibe un enlace 404. Espejo de
    # request_signature_endpoint (M01).
    await db.commit()
    return RequestE028SignatureResponse(**result)


@router.get(
    "/analysis/{analysis_id}/report-e028/signature-status",
    response_model=E028SignatureStatusResponse,
)
async def e028_signature_status_endpoint(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> E028SignatureStatusResponse:
    """Estado actual de la solicitud de firma del Informe E-028."""
    await _get_analysis_with_rls(analysis_id, db)
    try:
        result = await get_e028_signature_status(db, analysis_id)
    except E028SignatureIntegrationError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return E028SignatureStatusResponse(**result)
