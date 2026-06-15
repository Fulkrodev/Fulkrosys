"""Project composer endpoints (FASE 9.B).

Endpoints aglutinadores cross-motor scoped a project_id. Reusan servicios
de motors específicos (M27 conformity, M30 contacts) sin duplicar lógica.

Endpoints expuestos en este módulo (mount prefix `/api/v1`):
- GET /projects/{project_id}/header        composer cliente+CISO+conformity
- GET /projects/{project_id}/summary       6 KPIs cross-motor
- GET /projects/{project_id}/timeline      M17 phases + M27 milestones
- GET /projects/{project_id}/risk-overview M02 risks + M19 treatments
- GET /projects/{project_id}/operations    M25+M26+M27 status

Pre-requisito: cada endpoint llama _set_project_rls para verificar
existencia + activar RLS antes de queries cross-motor.
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db, set_tenant_context
from backend.app.models.core import Client, Project
from backend.app.models.ens import DdaEntry
from backend.app.models.planning import ProjectPlan, WbsTask
from backend.app.motors.m02_magerit.models import (
    MageritAnalysis,
    MageritAsset,
    MageritRiskCalculation,
    MageritTreatmentPlan,
)
from backend.app.motors.m08_verification.models import VerificationFinding
from backend.app.motors.m27_conformity.conformity_service_paso5 import (
    ConformityServicePaso5,
)
from backend.app.motors.m30_client_contacts.models import ClientContact


router = APIRouter(
    tags=["Project Composer (FASE 9.B)"],
    # Composer admin cross-motor → Marcos-only. Sin esto, una sesión cliente
    # podía leer CUALQUIER proyecto por UUID: _set_project_rls fija el contexto
    # al owner del proyecto sin verificar que el llamante sea su dueño. Consumido
    # sólo desde páginas admin (wrapper api()).
    dependencies=[Depends(require_owner)],
)


async def _set_project_rls(
    project_id: uuid.UUID, db: AsyncSession,
) -> uuid.UUID:
    """Activa RLS para project_id · 404 si project no existe."""
    cid = (await db.execute(
        sa_text("SELECT get_project_owner(:pid)"),
        {"pid": str(project_id)},
    )).scalar()
    if not cid:
        raise HTTPException(404, "Project not found")
    # Setear el contexto RLS (app.current_client_id/project_id). Sin esto, la
    # policy `client_id = current_client_id()` de projects oculta la fila y el
    # db.get(Project) posterior devuelve None → 404 falso. Patrón canónico que
    # usan los motores (p.ej. m03_dda._set_project_rls · faltaba aquí).
    await set_tenant_context(db, client_id=cid, project_id=project_id)
    return cid


# ════════════════════════════════════════════════════════════════════
# Schemas
# ════════════════════════════════════════════════════════════════════


class ProjectInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nombre: str
    fase: str
    categoria_objetivo: str | None = None
    lifecycle_state: str | None = None
    fecha_kickoff: date | None = None
    fecha_objetivo_certificacion: date | None = None
    certified_at: date | None = None


class ClienteInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nombre: str
    cif: str
    sector: str | None = None
    provincia: str | None = None


class ContactInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    full_name: str
    email: str
    phone: str | None = None
    role_title: str
    role_category: str


class ConformitySnapshot(BaseModel):
    route_status: str | None = None
    route_type: str | None = None
    expiration_date: str | None = None
    submissions_count: int = 0
    renewals_count: int = 0
    material_changes_count: int = 0


class ProjectHeaderResponse(BaseModel):
    project: ProjectInfo
    cliente: ClienteInfo
    rseg_contact: ContactInfo | None
    ciso_contact: ContactInfo | None
    conformity: ConformitySnapshot


# ════════════════════════════════════════════════════════════════════
# C.1 · GET /projects/{project_id}/header
# ════════════════════════════════════════════════════════════════════


@router.get(
    "/projects/{project_id}/header",
    response_model=ProjectHeaderResponse,
)
async def get_project_header(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ProjectHeaderResponse:
    """Composer para vista cabecera del proyecto.

    Aglutina sin duplicar lógica:
    - Project (core.Project) · estado lifecycle + categoría ENS objetivo
    - Cliente (core.Client) · razón social + CIF + sector + provincia
    - RSEG + CISO contacts (M30 ClientContact filtered by role_category)
    - Conformity snapshot (M27 ConformityServicePaso5)
    """
    await _set_project_rls(project_id, db)

    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    cliente = await db.get(Client, project.client_id)
    if not cliente:
        raise HTTPException(404, "Client not found")

    rseg_contact = (await db.execute(
        select(ClientContact).where(
            ClientContact.client_id == cliente.id,
            ClientContact.role_category == "rseg",
            ClientContact.is_active.is_(True),
        ).limit(1),
    )).scalar_one_or_none()

    ciso_contact = (await db.execute(
        select(ClientContact).where(
            ClientContact.client_id == cliente.id,
            ClientContact.role_category == "ciso",
            ClientContact.is_active.is_(True),
        ).limit(1),
    )).scalar_one_or_none()

    conformity_raw: dict[str, Any] = await ConformityServicePaso5().get_conformity_status(
        db, project_id,
    )
    route = conformity_raw.get("route") or {}

    return ProjectHeaderResponse(
        project=ProjectInfo.model_validate(project),
        cliente=ClienteInfo.model_validate(cliente),
        rseg_contact=ContactInfo.model_validate(rseg_contact) if rseg_contact else None,
        ciso_contact=ContactInfo.model_validate(ciso_contact) if ciso_contact else None,
        conformity=ConformitySnapshot(
            route_status=route.get("status"),
            route_type=route.get("route_type"),
            expiration_date=route.get("expiration_date"),
            submissions_count=conformity_raw.get("submissions_count") or 0,
            renewals_count=conformity_raw.get("renewals_count") or 0,
            material_changes_count=conformity_raw.get("material_changes_count") or 0,
        ),
    )


# ════════════════════════════════════════════════════════════════════
# C.2 · GET /projects/{project_id}/summary · 6 KPIs aggregator
# ════════════════════════════════════════════════════════════════════


class DdaStats(BaseModel):
    total: int
    aplicables: int
    no_aplica: int
    pendientes_revision: int


class ProjectSummaryResponse(BaseModel):
    categoria_ens: str | None
    fase: str
    dda: DdaStats
    risks_critical_open: int
    findings_open: int
    fecha_objetivo_certificacion: date | None
    conformity: ConformitySnapshot


@router.get(
    "/projects/{project_id}/summary",
    response_model=ProjectSummaryResponse,
)
async def get_project_summary(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ProjectSummaryResponse:
    """6 KPIs cross-motor para vista resumen del proyecto."""
    await _set_project_rls(project_id, db)

    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    # DdA stats (M03)
    dda_total = (await db.execute(
        select(sa_text("count(*)")).select_from(DdaEntry).where(
            DdaEntry.project_id == project_id,
            DdaEntry.deleted_at.is_(None),
        ),
    )).scalar() or 0

    dda_aplicables = (await db.execute(
        select(sa_text("count(*)")).select_from(DdaEntry).where(
            DdaEntry.project_id == project_id,
            DdaEntry.deleted_at.is_(None),
            # FIX: "aplicable" no es valor del enum Aplicabilidad (aplica |
            # aplica_con_refuerzos | no_aplica | compensada) → la cuenta daba
            # SIEMPRE 0 y dda_pendientes sobrecontaba. Aplicables = todo lo que
            # no es no_aplica.
            DdaEntry.aplicabilidad != "no_aplica",
        ),
    )).scalar() or 0

    dda_no_aplica = (await db.execute(
        select(sa_text("count(*)")).select_from(DdaEntry).where(
            DdaEntry.project_id == project_id,
            DdaEntry.deleted_at.is_(None),
            DdaEntry.aplicabilidad == "no_aplica",
        ),
    )).scalar() or 0

    dda_pendientes = max(0, dda_total - dda_aplicables - dda_no_aplica)

    # M02 critical risks open (risk_level in {MC, C})
    risks_critical = (await db.execute(
        select(sa_text("count(*)")).select_from(MageritRiskCalculation).where(
            MageritRiskCalculation.risk_level.in_(("MC", "C")),
            MageritRiskCalculation.analysis_id.in_(
                select(sa_text("id")).select_from(sa_text("magerit_analysis")).where(
                    sa_text("project_id = :pid"),
                ).params(pid=str(project_id)),
            ),
        ),
    )).scalar() or 0

    # M08 findings open
    findings_open = (await db.execute(
        select(sa_text("count(*)")).select_from(VerificationFinding).where(
            VerificationFinding.project_id == project_id,
            VerificationFinding.deleted_at.is_(None),
            VerificationFinding.status.in_(("open", "needs_review")),
        ),
    )).scalar() or 0

    # M27 conformity reuse pattern from C.1
    conformity_raw: dict[str, Any] = await ConformityServicePaso5().get_conformity_status(
        db, project_id,
    )
    route = conformity_raw.get("route") or {}

    return ProjectSummaryResponse(
        categoria_ens=project.categoria_objetivo,
        fase=project.fase,
        dda=DdaStats(
            total=int(dda_total),
            aplicables=int(dda_aplicables),
            no_aplica=int(dda_no_aplica),
            pendientes_revision=int(dda_pendientes),
        ),
        risks_critical_open=int(risks_critical),
        findings_open=int(findings_open),
        fecha_objetivo_certificacion=project.fecha_objetivo_certificacion,
        conformity=ConformitySnapshot(
            route_status=route.get("status"),
            route_type=route.get("route_type"),
            expiration_date=route.get("expiration_date"),
            submissions_count=conformity_raw.get("submissions_count") or 0,
            renewals_count=conformity_raw.get("renewals_count") or 0,
            material_changes_count=conformity_raw.get("material_changes_count") or 0,
        ),
    )


# ════════════════════════════════════════════════════════════════════
# C.3 · GET /projects/{project_id}/timeline · M17 phases + M27 milestones
# ════════════════════════════════════════════════════════════════════


class TimelineTask(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    task_code: str
    task_name: str
    phase: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: str | None = None
    progress_pct: int = 0
    is_critical_path: bool = False


class TimelineMilestone(BaseModel):
    name: str
    date: date | None
    type: str  # plan_milestone | conformity_expiration | objective | kickoff
    status: str | None = None


class TimelineResponse(BaseModel):
    plan_start: date | None
    plan_end: date | None
    tasks: list[TimelineTask]
    milestones: list[TimelineMilestone]
    plan_estado: str | None = None


@router.get(
    "/projects/{project_id}/timeline",
    response_model=TimelineResponse,
)
async def get_project_timeline(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> TimelineResponse:
    """Composer timeline · M17 wbs_tasks + project_plan milestones + M27."""
    await _set_project_rls(project_id, db)

    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    # Plan más reciente
    plan_row = (await db.execute(
        select(ProjectPlan).where(
            ProjectPlan.project_id == project_id,
            ProjectPlan.deleted_at.is_(None),
        ).order_by(ProjectPlan.version.desc()).limit(1),
    )).scalar_one_or_none()

    tasks: list[TimelineTask] = []
    milestones: list[TimelineMilestone] = []
    plan_start: date | None = None
    plan_end: date | None = None
    plan_estado: str | None = None

    if plan_row is not None:
        plan_start = plan_row.start_date
        plan_end = plan_row.end_date_estimated
        plan_estado = plan_row.estado

        rows = (await db.execute(
            select(WbsTask).where(
                WbsTask.project_plan_id == plan_row.id,
                WbsTask.deleted_at.is_(None),
            ).order_by(WbsTask.start_date.asc().nulls_last()),
        )).scalars().all()
        tasks = [TimelineTask.model_validate(t) for t in rows]

        # plan_row.milestones (JSONB) puede tener forma:
        # [{"name": "...", "date": "YYYY-MM-DD", "status": "..."}, ...]
        raw_milestones = plan_row.milestones or {}
        milestone_list: list[Any]
        if isinstance(raw_milestones, list):
            milestone_list = raw_milestones
        elif isinstance(raw_milestones, dict):
            milestone_list = list(raw_milestones.get("items") or [])
        else:
            milestone_list = []
        for m in milestone_list:
            if not isinstance(m, dict):
                continue
            try:
                m_date = (
                    date.fromisoformat(m["date"])
                    if m.get("date") else None
                )
            except (ValueError, TypeError):
                m_date = None
            milestones.append(TimelineMilestone(
                name=str(m.get("name") or m.get("title") or "Milestone"),
                date=m_date,
                type="plan_milestone",
                status=m.get("status"),
            ))

    # Project metadata como milestones de alto nivel
    if project.fecha_kickoff:
        milestones.append(TimelineMilestone(
            name="Kickoff",
            date=project.fecha_kickoff,
            type="kickoff",
            status="completed" if project.fecha_kickoff <= date.today() else "pending",
        ))
    if project.fecha_objetivo_certificacion:
        milestones.append(TimelineMilestone(
            name="Objetivo certificación",
            date=project.fecha_objetivo_certificacion,
            type="objective",
            status="pending",
        ))
    if project.certified_at:
        milestones.append(TimelineMilestone(
            name="Certificado",
            date=project.certified_at,
            type="objective",
            status="completed",
        ))

    # M27 conformity expiration como milestone
    conformity_raw: dict[str, Any] = await ConformityServicePaso5().get_conformity_status(
        db, project_id,
    )
    route = conformity_raw.get("route") or {}
    if route.get("expiration_date"):
        try:
            exp = date.fromisoformat(str(route["expiration_date"]))
            milestones.append(TimelineMilestone(
                name="Expiración conformidad",
                date=exp,
                type="conformity_expiration",
                status=route.get("status"),
            ))
        except (ValueError, TypeError):
            pass

    # Si no hay plan_start/end · derivar de tasks o milestones
    if plan_start is None and tasks:
        candidates = [t.start_date for t in tasks if t.start_date]
        plan_start = min(candidates) if candidates else None
    if plan_end is None and tasks:
        candidates = [t.end_date for t in tasks if t.end_date]
        plan_end = max(candidates) if candidates else None
    if plan_end is None and milestones:
        candidates = [m.date for m in milestones if m.date]
        plan_end = max(candidates) if candidates else None

    # Sort milestones por fecha
    milestones.sort(key=lambda m: m.date or date.max)

    return TimelineResponse(
        plan_start=plan_start,
        plan_end=plan_end,
        tasks=tasks,
        milestones=milestones,
        plan_estado=plan_estado,
    )


# ════════════════════════════════════════════════════════════════════
# C.4 · GET /projects/{project_id}/risk-overview · MAGERIT M02 + treatments
# ════════════════════════════════════════════════════════════════════


class RiskLevelCounts(BaseModel):
    MC: int = 0  # Muy crítico
    C: int = 0   # Crítico
    I: int = 0   # Importante
    A: int = 0   # Aceptable
    D: int = 0   # Despreciable


class TreatmentCounts(BaseModel):
    pending: int = 0
    in_progress: int = 0
    completed: int = 0


class CriticalRiskItem(BaseModel):
    risk_calculation_id: uuid.UUID
    asset_id: uuid.UUID
    asset_name: str
    threat_code: str
    dimension: str
    risk_level: str | None
    risk_effective: float | None
    risk_intrinsic_accumulated: float | None
    treatment_status: str | None = None
    treatment_decision: str | None = None


class RiskOverviewResponse(BaseModel):
    total_risks: int
    by_risk_level: RiskLevelCounts
    by_treatment: TreatmentCounts
    top_critical: list[CriticalRiskItem]
    analyses_count: int


@router.get(
    "/projects/{project_id}/risk-overview",
    response_model=RiskOverviewResponse,
)
async def get_project_risk_overview(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> RiskOverviewResponse:
    """Composer riesgos · M02 magerit_risk_calculation + treatment_plan."""
    await _set_project_rls(project_id, db)

    # Analyses count
    analyses_count = (await db.execute(
        select(sa_text("count(*)")).select_from(MageritAnalysis).where(
            MageritAnalysis.project_id == project_id,
            MageritAnalysis.deleted_at.is_(None),
        ),
    )).scalar() or 0

    analysis_ids_subq = select(MageritAnalysis.id).where(
        MageritAnalysis.project_id == project_id,
        MageritAnalysis.deleted_at.is_(None),
    )

    # Total risks for project
    total_risks = (await db.execute(
        select(sa_text("count(*)")).select_from(MageritRiskCalculation).where(
            MageritRiskCalculation.analysis_id.in_(analysis_ids_subq),
        ),
    )).scalar() or 0

    # Counts por risk_level
    counts: dict[str, int] = {}
    rows = (await db.execute(
        select(
            MageritRiskCalculation.risk_level,
            sa_text("count(*) AS cnt"),
        ).where(
            MageritRiskCalculation.analysis_id.in_(analysis_ids_subq),
            MageritRiskCalculation.risk_level.isnot(None),
        ).group_by(MageritRiskCalculation.risk_level),
    )).all()
    for r in rows:
        level = r[0]
        cnt = int(r[1] or 0)
        if level:
            counts[level] = cnt

    # Treatment status counts
    treatment_rows = (await db.execute(
        select(
            MageritTreatmentPlan.status,
            sa_text("count(*) AS cnt"),
        ).where(
            MageritTreatmentPlan.analysis_id.in_(analysis_ids_subq),
            MageritTreatmentPlan.deleted_at.is_(None),
        ).group_by(MageritTreatmentPlan.status),
    )).all()
    treatment_counts = TreatmentCounts()
    for r in treatment_rows:
        status = r[0]
        cnt = int(r[1] or 0)
        if status == "pending":
            treatment_counts.pending = cnt
        elif status == "in_progress":
            treatment_counts.in_progress = cnt
        elif status == "completed":
            treatment_counts.completed = cnt

    # Top 10 críticos (risk_level in MC, C) ordenados por risk_effective desc
    top_rows = (await db.execute(
        select(
            MageritRiskCalculation.id,
            MageritRiskCalculation.asset_id,
            MageritAsset.name,
            MageritRiskCalculation.threat_code,
            MageritRiskCalculation.dimension,
            MageritRiskCalculation.risk_level,
            MageritRiskCalculation.risk_effective,
            MageritRiskCalculation.risk_intrinsic_accumulated,
        ).join(
            MageritAsset, MageritAsset.id == MageritRiskCalculation.asset_id,
        ).where(
            MageritRiskCalculation.analysis_id.in_(analysis_ids_subq),
            MageritRiskCalculation.risk_level.in_(("MC", "C")),
        ).order_by(
            MageritRiskCalculation.risk_effective.desc().nulls_last(),
        ).limit(10),
    )).all()

    top_critical: list[CriticalRiskItem] = []
    for r in top_rows:
        # Buscar treatment status para este risk (asset_id + threat + dimension)
        tp = (await db.execute(
            select(
                MageritTreatmentPlan.status,
                MageritTreatmentPlan.treatment,
            ).where(
                MageritTreatmentPlan.analysis_id.in_(analysis_ids_subq),
                MageritTreatmentPlan.asset_id == r[1],
                MageritTreatmentPlan.threat_code == r[3],
                MageritTreatmentPlan.dimension == r[4],
                MageritTreatmentPlan.deleted_at.is_(None),
            ).limit(1),
        )).first()
        top_critical.append(CriticalRiskItem(
            risk_calculation_id=r[0],
            asset_id=r[1],
            asset_name=r[2],
            threat_code=r[3],
            dimension=r[4],
            risk_level=r[5],
            risk_effective=float(r[6]) if r[6] is not None else None,
            risk_intrinsic_accumulated=float(r[7]) if r[7] is not None else None,
            treatment_status=tp[0] if tp else None,
            treatment_decision=tp[1] if tp else None,
        ))

    return RiskOverviewResponse(
        total_risks=int(total_risks),
        by_risk_level=RiskLevelCounts(
            MC=counts.get("MC", 0),
            C=counts.get("C", 0),
            I=counts.get("I", 0),
            A=counts.get("A", 0),
            D=counts.get("D", 0),
        ),
        by_treatment=treatment_counts,
        top_critical=top_critical,
        analyses_count=int(analyses_count),
    )
