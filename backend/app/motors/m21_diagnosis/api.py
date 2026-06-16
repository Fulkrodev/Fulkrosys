"""Endpoints REST Motor 21 — Organizational Diagnosis."""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db, set_tenant_context
from backend.app.models.diagnosis import DiagnosisRun

from .report_generator import ReportGeneratorError, generate_report, generate_report_docx
from .service import DiagnosisError, get_latest_diagnosis, list_diagnosis_runs, run_diagnosis

from backend.app.auth.dependencies import require_owner

router = APIRouter(
    prefix="/diagnosis", tags=["Motor 21 - Diagnosis"],
    # TODO-RBAC-PER-ENDPOINT-001 Cat A: Marcos-only.
    dependencies=[Depends(require_owner)],
)


async def _set_project_rls(project_id: uuid.UUID, db: AsyncSession):
    client_id = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
    )).scalar()
    if not client_id:
        raise HTTPException(status_code=404, detail="Project not found")
    await set_tenant_context(db, client_id=client_id, project_id=project_id)


class RunDiagnosisBody(BaseModel):
    sector: str = Field(..., min_length=2, max_length=40)
    triggered_by: str = Field("marcos", max_length=120)
    confidential_notes: Optional[str] = Field(None, max_length=5000)


@router.post("/projects/{project_id}/run")
async def run_diagnosis_endpoint(
    project_id: uuid.UUID,
    body: RunDiagnosisBody,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    try:
        return await run_diagnosis(
            session, project_id, sector=body.sector,
            triggered_by=body.triggered_by, confidential_notes=body.confidential_notes,
        )
    except DiagnosisError as exc:
        raise HTTPException(status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))


@router.get("/projects/{project_id}/latest")
async def get_latest_endpoint(
    project_id: uuid.UUID,
    include_confidential: bool = Query(False),
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    result = await get_latest_diagnosis(session, project_id, include_confidential)
    if result is None:
        raise HTTPException(status_code=404, detail="No hay diagnostico")
    return result


@router.get("/projects/{project_id}/runs")
async def list_runs_endpoint(project_id: uuid.UUID, session: AsyncSession = Depends(get_db)):
    await _set_project_rls(project_id, session)
    return await list_diagnosis_runs(session, project_id)


@router.get("/projects/{project_id}/maturity")
async def get_maturity_endpoint(project_id: uuid.UUID, session: AsyncSession = Depends(get_db)):
    await _set_project_rls(project_id, session)
    result = await get_latest_diagnosis(session, project_id)
    if result is None:
        raise HTTPException(status_code=404, detail="No hay diagnostico")
    return result.get("maturity_scoring", {})


@router.get("/projects/{project_id}/stakeholders")
async def get_stakeholders_endpoint(project_id: uuid.UUID, session: AsyncSession = Depends(get_db)):
    await _set_project_rls(project_id, session)
    result = await get_latest_diagnosis(session, project_id)
    if result is None:
        raise HTTPException(status_code=404, detail="No hay diagnostico")
    return result.get("stakeholder_analysis", {})


@router.get("/projects/{project_id}/compliance")
async def get_compliance_endpoint(project_id: uuid.UUID, session: AsyncSession = Depends(get_db)):
    await _set_project_rls(project_id, session)
    result = await get_latest_diagnosis(session, project_id)
    if result is None:
        raise HTTPException(status_code=404, detail="No hay diagnostico")
    return result.get("compliance_detection", {})


@router.post("/projects/{project_id}/runs/{run_id}/generate-report")
async def generate_report_endpoint(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    """Genera report_data estructurado + quick wins + recomendaciones."""
    await _set_project_rls(project_id, session)
    try:
        return await generate_report(session, run_id)
    except ReportGeneratorError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        )


@router.post("/projects/{project_id}/runs/{run_id}/generate-docx")
async def generate_docx_endpoint(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    """Renderiza DOCX del informe. Requiere generate-report previo."""
    await _set_project_rls(project_id, session)
    try:
        path = await generate_report_docx(session, run_id)
    except ReportGeneratorError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        )
    if path is None:
        raise HTTPException(status_code=501, detail="docxtpl no disponible en este entorno")
    return {"docx_path": path, "status": "generated"}


@router.get("/projects/{project_id}/runs/{run_id}/download-docx")
async def download_docx_endpoint(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    """Descarga el DOCX del informe."""
    await _set_project_rls(project_id, session)
    r = await session.execute(select(DiagnosisRun).where(
        DiagnosisRun.id == run_id, DiagnosisRun.project_id == project_id))
    run = r.scalar_one_or_none()
    if run is None or not run.report_docx_path:
        raise HTTPException(status_code=404, detail="DOCX no generado")
    path = Path(run.report_docx_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Fichero DOCX no encontrado en disco")
    return FileResponse(
        str(path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"informe_fase1_{run_id}.docx",
    )


@router.get("/projects/{project_id}/runs/{run_id}/quick-wins")
async def get_quick_wins_endpoint(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    """Devuelve solo los quick wins del informe generado."""
    await _set_project_rls(project_id, session)
    r = await session.execute(select(DiagnosisRun).where(
        DiagnosisRun.id == run_id, DiagnosisRun.project_id == project_id))
    run = r.scalar_one_or_none()
    if run is None or run.report_data is None:
        raise HTTPException(status_code=404, detail="Informe no generado")
    wins = (run.report_data or {}).get("quick_wins", []) or []
    return {"quick_wins": wins, "total": len(wins)}


# ═══════════════════════════════════════════════════════════════
# Sprint C4: CRUD stakeholders/business_processes/legal_obligations
# + exporter M21 → M2 MAGERIT
# ═══════════════════════════════════════════════════════════════
from backend.app.models.diagnosis import (  # noqa: E402
    BusinessProcess, LegalObligation, Stakeholder,
)


class StakeholderBody(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=255)
    cargo: str | None = Field(None, max_length=200)
    departamento: str | None = Field(None, max_length=200)
    poder: int | None = Field(None, ge=1, le=5)
    interes: int | None = Field(None, ge=1, le=5)
    actitud: str | None = Field(None, max_length=30)
    email: str | None = Field(None, max_length=255)
    telefono: str | None = Field(None, max_length=50)
    notas_confidenciales: str | None = None


class ProcessBody(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=255)
    descripcion: str | None = None
    criticidad: str | None = Field(None, max_length=20)
    propietario: str | None = Field(None, max_length=200)
    bpmn_mermaid: str | None = None
    rto_horas: int | None = Field(None, ge=0)
    rpo_horas: int | None = Field(None, ge=0)


class LegalObligationBody(BaseModel):
    normativa: str = Field(..., min_length=2, max_length=200)
    articulo: str | None = Field(None, max_length=100)
    alcance: str | None = None
    impacto_ens: str | None = None
    estado: str | None = Field(None, max_length=30)
    notas: str | None = None


def _ser_stake(s: Stakeholder) -> dict:
    return {
        "id": str(s.id), "project_id": str(s.project_id),
        "nombre": s.nombre, "cargo": s.cargo, "departamento": s.departamento,
        "poder": s.poder, "interes": s.interes, "actitud": s.actitud,
        "email": s.email,
    }


def _ser_proc(p: BusinessProcess) -> dict:
    return {
        "id": str(p.id), "project_id": str(p.project_id),
        "nombre": p.nombre, "descripcion": p.descripcion,
        "criticidad": p.criticidad, "propietario": p.propietario,
        "rto_horas": p.rto_horas, "rpo_horas": p.rpo_horas,
    }


def _ser_legal(lo: LegalObligation) -> dict:
    return {
        "id": str(lo.id), "project_id": str(lo.project_id),
        "normativa": lo.normativa, "articulo": lo.articulo,
        "alcance": lo.alcance, "impacto_ens": lo.impacto_ens, "estado": lo.estado,
    }


@router.post(
    "/projects/{project_id}/diagnosis/stakeholders",
    status_code=http_status.HTTP_201_CREATED,
)
async def create_stakeholder(
    project_id: uuid.UUID, body: StakeholderBody,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    s = Stakeholder(project_id=project_id, **body.model_dump(exclude_none=True))
    session.add(s)
    await session.flush()
    await session.commit()  # get_db() no auto-commitea
    return _ser_stake(s)


@router.get("/projects/{project_id}/diagnosis/stakeholders")
async def list_stakeholders(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    res = await session.execute(
        select(Stakeholder).where(
            Stakeholder.project_id == project_id,
            Stakeholder.deleted_at.is_(None),
        ).order_by(Stakeholder.created_at.desc())
    )
    return {"stakeholders": [_ser_stake(s) for s in res.scalars().all()]}


@router.post(
    "/projects/{project_id}/diagnosis/processes",
    status_code=http_status.HTTP_201_CREATED,
)
async def create_process(
    project_id: uuid.UUID, body: ProcessBody,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    p = BusinessProcess(project_id=project_id, **body.model_dump(exclude_none=True))
    session.add(p)
    await session.flush()
    await session.commit()  # get_db() no auto-commitea
    return _ser_proc(p)


@router.get("/projects/{project_id}/diagnosis/processes")
async def list_processes(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    res = await session.execute(
        select(BusinessProcess).where(
            BusinessProcess.project_id == project_id,
            BusinessProcess.deleted_at.is_(None),
        ).order_by(BusinessProcess.created_at.desc())
    )
    return {"processes": [_ser_proc(p) for p in res.scalars().all()]}


@router.post(
    "/projects/{project_id}/diagnosis/legal-obligations",
    status_code=http_status.HTTP_201_CREATED,
)
async def create_legal_obligation(
    project_id: uuid.UUID, body: LegalObligationBody,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    lo = LegalObligation(project_id=project_id, **body.model_dump(exclude_none=True))
    session.add(lo)
    await session.flush()
    await session.commit()  # get_db() no auto-commitea
    return _ser_legal(lo)


@router.get("/projects/{project_id}/diagnosis/legal-obligations")
async def list_legal_obligations(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    res = await session.execute(
        select(LegalObligation).where(
            LegalObligation.project_id == project_id,
            LegalObligation.deleted_at.is_(None),
        ).order_by(LegalObligation.created_at.desc())
    )
    return {"legal_obligations": [_ser_legal(lo) for lo in res.scalars().all()]}


# Exporter M21 → M2 MAGERIT
@router.post(
    "/projects/{project_id}/diagnosis/export-to-magerit",
    status_code=http_status.HTTP_201_CREATED,
)
async def export_processes_to_magerit(
    project_id: uuid.UUID,
    magerit_analysis_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    """Exporta BusinessProcess a MageritAsset (tipo servicio interno)."""
    await _set_project_rls(project_id, session)
    from backend.app.motors.m02_magerit.models import MageritAnalysis
    # IDOR guard: el analisis destino DEBE pertenecer a ESTE proyecto. Sin esto,
    # un magerit_analysis_id arbitrario inyectaria MageritAsset en el analisis de
    # otro proyecto/cliente (export cross-tenant).
    owns_analysis = await session.execute(
        select(MageritAnalysis.id).where(
            MageritAnalysis.id == magerit_analysis_id,
            MageritAnalysis.project_id == project_id,
        )
    )
    if owns_analysis.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Analysis no encontrado en este proyecto",
        )
    res = await session.execute(
        select(BusinessProcess).where(
            BusinessProcess.project_id == project_id,
            BusinessProcess.deleted_at.is_(None),
        )
    )
    processes = list(res.scalars().all())
    if not processes:
        return {"exported": 0, "message": "No hay procesos"}

    from backend.app.motors.m02_magerit.models import MageritAsset
    criticidad_to_value = {"alta": 8, "media": 5, "baja": 2}
    created = 0
    for p in processes:
        val = criticidad_to_value.get(p.criticidad or "media", 5)
        session.add(MageritAsset(
            analysis_id=magerit_analysis_id,
            code=f"PROC-{str(p.id)[:8]}",
            name=p.nombre,
            asset_type_code="S",  # Servicio interno (catálogo MAGERIT)
            description=p.descripcion or f"Proceso: {p.nombre}",
            owner=p.propietario,
            value_d=val, value_i=val, value_c=val,
            value_a=val, value_t=val,
        ))
        created += 1
    await session.flush()
    await session.commit()  # get_db() no auto-commitea: persistir los MageritAsset
    return {
        "exported": created,
        "analysis_id": str(magerit_analysis_id),
        "processes_source": len(processes),
    }


# ================================================================
# ENS ↔ ISO 27001 cross-compliance (SAN-C.MB-10.7 · CCN-STIC 825)
# ================================================================


class IsoCoverageRequest(BaseModel):
    iso_controls_implemented: list[str] = Field(
        ...,
        description=(
            "Lista controles ISO 27001:2022 Anexo A implementados "
            "(ej. ['A.5.1', 'A.8.5'])."
        ),
    )


class IsoCoverageResponse(BaseModel):
    project_id: str | None
    iso_controls_implemented: list[str]
    ens_measures_total: int
    ens_measures_covered: list[str]
    ens_measures_gaps: list[str]
    coverage_percent: float
    effort_hours_saved_estimate: float
    coverage_per_family: dict


@router.post(
    "/projects/{project_id}/cross-compliance/iso27001/coverage",
    response_model=IsoCoverageResponse,
)
async def calculate_iso27001_coverage_endpoint(
    project_id: uuid.UUID,
    body: IsoCoverageRequest,
    session: AsyncSession = Depends(get_db),
):
    """Calcula cobertura ENS desde controles ISO 27001 implementados.

    Útil para clientes con ISO 27001 vigente que evalúan migrar / añadir
    cumplimiento ENS · cuantifica % cobertura automática + gaps específicos
    ENS-only.

    Refs: SAN-C.MB-10.7 · CCN-STIC 825
    """
    from .iso27001_coverage import calculate_iso27001_coverage

    result = await calculate_iso27001_coverage(
        session,
        body.iso_controls_implemented,
        project_id=project_id,
    )
    return IsoCoverageResponse(
        project_id=str(project_id),
        iso_controls_implemented=result.iso_controls_implemented,
        ens_measures_total=result.ens_measures_total,
        ens_measures_covered=result.ens_measures_covered,
        ens_measures_gaps=result.ens_measures_gaps,
        coverage_percent=result.coverage_percent,
        effort_hours_saved_estimate=result.effort_hours_saved_estimate,
        coverage_per_family=result.coverage_per_family,
    )
