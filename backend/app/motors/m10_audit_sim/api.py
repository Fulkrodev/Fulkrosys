"""Motor 10 - Audit Simulation API."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db, set_tenant_context
from backend.app.auth.dependencies import require_owner

from .audit_questions import (
    AUDIT_QUESTIONS,
    FAMILIA_LABEL,
    get_families,
    get_questions_by_family,
    get_questions_for_categoria,
)
from .audit_simulator import AuditSimError, AuditSimulatorService


router = APIRouter(
    prefix="/audit-sim", tags=["Motor 10 - Audit Simulation"],
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


# ─────────── Schemas ───────────

class RunSimulationBody(BaseModel):
    categoria: str = Field(..., min_length=1, max_length=10)


# ─────────── Catálogo (sin RLS) ───────────

@router.get("/questions")
async def list_questions(
    categoria: Optional[str] = None,
    familia: Optional[str] = None,
):
    if categoria:
        data = get_questions_for_categoria(categoria)
    elif familia:
        data = get_questions_by_family(familia)
    else:
        data = AUDIT_QUESTIONS
    return {
        "total": len(data),
        "familias_cubiertas": sorted({q["familia"] for q in data.values()}),
        "questions": [
            {"code": code, **q} for code, q in data.items()
        ],
    }


@router.get("/questions/families")
async def list_families():
    return {
        "families": [
            {"code": fam, "label": FAMILIA_LABEL.get(fam, fam)}
            for fam in get_families()
        ],
    }


@router.get("/questions/{measure_code}")
async def get_question(measure_code: str):
    if measure_code not in AUDIT_QUESTIONS:
        raise HTTPException(status_code=404, detail="Measure not found")
    return {"code": measure_code, **AUDIT_QUESTIONS[measure_code]}


# ─────────── Runs (con RLS) ───────────

@router.post(
    "/projects/{project_id}/runs",
    status_code=status.HTTP_201_CREATED,
)
async def run_simulation(
    project_id: uuid.UUID,
    body: RunSimulationBody,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        run = await AuditSimulatorService().run_simulation(
            db, project_id=project_id, categoria=body.categoria,
        )
    except AuditSimError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize_run(run)


@router.get("/projects/{project_id}/runs")
async def list_runs(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    runs = await AuditSimulatorService().list_runs(db, project_id)
    return {"runs": [_serialize_run(r) for r in runs]}


@router.get("/projects/{project_id}/runs/{run_id}")
async def get_run(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    run = await AuditSimulatorService().get_run(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return _serialize_run(run)


@router.get("/projects/{project_id}/runs/{run_id}/findings")
async def list_findings(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    evaluacion: Optional[str] = None,
    familia: Optional[str] = None,
    nivel: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    findings = await AuditSimulatorService().list_findings(
        db, run_id, evaluacion=evaluacion, familia=familia, nivel=nivel,
    )
    return {"findings": [_serialize_finding(f) for f in findings]}


@router.get("/projects/{project_id}/runs/{run_id}/findings/{finding_id}")
async def get_finding(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    finding_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    f = await AuditSimulatorService().get_finding(db, finding_id)
    if not f or f.run_id != run_id:
        raise HTTPException(status_code=404, detail="Finding not found")
    return _serialize_finding(f)


@router.get("/projects/{project_id}/runs/{run_id}/report")
async def get_report_data(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    svc = AuditSimulatorService()
    run = await svc.get_run(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    findings = await svc.list_findings(db, run_id)
    return {
        "run": _serialize_run(run),
        "findings": [_serialize_finding(f) for f in findings],
        "contradicciones": [
            _serialize_finding(f) for f in findings if f.contradiccion_detectada
        ],
    }


@router.get("/projects/{project_id}/runs/{run_id}/report/docx")
async def download_report_docx(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        content = await AuditSimulatorService().generate_report_docx(db, run_id)
    except AuditSimError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="auditoria_{run_id}.docx"'
        },
    )


@router.get("/projects/{project_id}/summary")
async def get_summary(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    return await AuditSimulatorService().get_summary(db, project_id)


# ─────────── Serializers ───────────

def _serialize_run(r):
    return {
        "id": str(r.id),
        "project_id": str(r.project_id),
        "categoria": r.categoria,
        "estado": r.estado,
        "total_measures": r.total_measures,
        "measures_evaluated": r.measures_evaluated,
        "conformes": r.conformes,
        "no_conformes_mayores": r.no_conformes_mayores,
        "no_conformes_menores": r.no_conformes_menores,
        "observaciones": r.observaciones,
        "no_aplica": r.no_aplica,
        "score_global": r.score_global,
        "nivel_madurez_global": r.nivel_madurez_global,
        "scores_por_familia": r.scores_por_familia,
        "contradicciones_count": r.contradicciones_count,
        "recomendacion": r.recomendacion,
        "started_at": r.started_at.isoformat() if r.started_at else None,
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def _serialize_finding(f):
    return {
        "id": str(f.id),
        "run_id": str(f.run_id),
        "measure_code": f.measure_code,
        "measure_name": f.measure_name,
        "measure_family": f.measure_family,
        "pregunta_auditor": f.pregunta_auditor,
        "criterio_aceptacion": f.criterio_aceptacion,
        "documento_esperado": f.documento_esperado,
        "documento_encontrado": f.documento_encontrado,
        "evidencia_encontrada": f.evidencia_encontrada,
        "evidencia_vigente": f.evidencia_vigente,
        "evidencia_suficiente": f.evidencia_suficiente,
        "evaluacion": f.evaluacion,
        "nivel_madurez": f.nivel_madurez,
        "hallazgo_descripcion": f.hallazgo_descripcion,
        "accion_requerida": f.accion_requerida,
        "plazo_sugerido_dias": f.plazo_sugerido_dias,
        "contradiccion_detectada": f.contradiccion_detectada,
        "contradiccion_detalle": f.contradiccion_detalle,
        "evidencia_ids": f.evidencia_ids or [],
        "pentest_finding_id": str(f.pentest_finding_id) if f.pentest_finding_id else None,
    }
