"""M8 v5.1 — Verificacion Tecnica — API REST (14 endpoints).

API operativa Checkpoints 1+2+3. Todos los endpoints implementados
contra BD real (no quedan 501 stubs).

Endpoints CRUD basicos:
- POST  /verification/run               → crea run + auto-scope
- GET   /verification/runs              → listado por proyecto
- GET   /verification/runs/{rid}        → detalle de run
- GET   /verification/runs/{rid}/findings  → findings filtrados
- PATCH /verification/findings/{fid}    → cambia estado finding
- PATCH /verification/findings/{fid}/mapping → corrige mapeo ENS
- POST  /verification/runs/{rid}/kill   → kill switch SIGTERM <5s

Endpoints orquestacion + reporting:
- POST  /verification/findings/{fid}/retest
- GET   /verification/remediation-plan
- POST  /verification/handoff
- POST  /verification/ingest
- POST  /verification/runs/{rid}/report
- GET   /verification/heatmap
- GET   /verification/score
- GET   /verification/delta
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db, set_tenant_context
from backend.app.auth.dependencies import require_owner

from .kill_switch import request_kill
from .external.findings_ingester import (
    ingest_external_findings, parse_pdf_payload, parse_structured_payload,
)
from .external.handoff_builder import build_handoff_package
from .models import (
    VerificationFinding,
    VerificationRun,
)
from .remediation.retest_runner import run_retest
from .remediation.sla_calculator import calculate_deadline, prioritize_findings
from .reports.delta_report import compute_delta
from .reports.heatmap_generator import (
    ENS_73_MEASURES, generate_heatmap, heatmap_summary,
)
from .reports.report_generator import VerificationReportGenerator
from .reports.score_calculator import calculate_score
from .schemas import (
    FindingMappingPatchBody,
    FindingPatchBody,
    HandoffCreateBody,
    IngestRequestBody,
    ReportRequestBody,
    RetestRequestBody,
    RunCreateBody,
)
from .service import (
    FindingNotFoundError,
    RunNotFoundError,
    RunStateError,
    ValidationError,
    VerificationService,
)


router = APIRouter(
    tags=["Motor 8 - Verificacion Tecnica"],
    # TODO-RBAC-PER-ENDPOINT-001 Cat A: Marcos-only.
    dependencies=[Depends(require_owner)],
)


# ─── RLS helpers ────────────────────────────────────────────────────

async def _set_project_rls(project_id: uuid.UUID, db: AsyncSession):
    client_id = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)},
    )).scalar()
    if not client_id:
        raise HTTPException(status_code=404, detail="Project not found")
    await set_tenant_context(db, client_id=client_id, project_id=project_id)


async def _set_rls_from_run(run_id: uuid.UUID, db: AsyncSession) -> uuid.UUID:
    row = (await db.execute(
        text(
            "SELECT project_id FROM verification_runs "
            "WHERE id = :rid AND deleted_at IS NULL"
        ),
        {"rid": str(run_id)},
    )).first()
    if not row:
        raise HTTPException(status_code=404, detail="Run not found")
    await _set_project_rls(row[0], db)
    return row[0]


async def _set_rls_from_finding(finding_id: uuid.UUID, db: AsyncSession) -> uuid.UUID:
    row = (await db.execute(
        text(
            "SELECT project_id FROM verification_findings "
            "WHERE id = :fid AND deleted_at IS NULL"
        ),
        {"fid": str(finding_id)},
    )).first()
    if not row:
        raise HTTPException(status_code=404, detail="Finding not found")
    await _set_project_rls(row[0], db)
    return row[0]


# ─── Serializers ────────────────────────────────────────────────────

def _serialize_run_summary(run) -> dict:
    return {
        "id": run.id,
        "project_id": run.project_id,
        "category": run.category,
        "mode": run.mode,
        "status": run.status,
        "scheduled_start": run.scheduled_start,
        "completed_at": run.completed_at,
        "total_findings": run.total_findings or 0,
        "confirmed_findings": run.confirmed_findings or 0,
        "critical_count": run.critical_count or 0,
        "high_count": run.high_count or 0,
        "medium_count": run.medium_count or 0,
        "low_count": run.low_count or 0,
        "security_score": run.security_score,
        "delta_new": run.delta_new or 0,
        "delta_resolved": run.delta_resolved or 0,
        "delta_persistent": run.delta_persistent or 0,
        "created_at": run.created_at,
    }


def _serialize_run_detail(run) -> dict:
    base = _serialize_run_summary(run)
    base.update({
        "scope_jsonb": run.scope_jsonb,
        "scope_derived_from": run.scope_derived_from,
        "tools_used": run.tools_used or [],
        "phase1_started_at": run.phase1_started_at,
        "phase1_completed_at": run.phase1_completed_at,
        "phase2_started_at": run.phase2_started_at,
        "phase2_completed_at": run.phase2_completed_at,
        "phase3_started_at": run.phase3_started_at,
        "authorized_by": run.authorized_by,
        "authorization_signed_at": run.authorization_signed_at,
        "previous_run_id": run.previous_run_id,
    })
    return base


def _serialize_finding_summary(f) -> dict:
    return {
        "id": f.id,
        "run_id": f.run_id,
        "title": f.title,
        "severity": f.severity,
        "cvss_score": float(f.cvss_score) if f.cvss_score is not None else None,
        "cve_id": f.cve_id,
        "affected_host": f.affected_host,
        "affected_port": f.affected_port,
        "confidence_score": float(f.confidence_score),
        "zfp_gate5_classification": f.zfp_gate5_classification,
        "ens_primary_measure": f.ens_primary_measure,
        "status": f.status,
        "remediation_priority": f.remediation_priority,
    }


# ════════════════════════════════════════════════════════════════════
# EJECUCION (3 endpoints)
# ════════════════════════════════════════════════════════════════════

@router.post(
    "/projects/{project_id}/verification/run",
    status_code=http_status.HTTP_201_CREATED,
)
async def create_verification_run(
    project_id: uuid.UUID,
    body: RunCreateBody,
    db: AsyncSession = Depends(get_db),
):
    """Crea un nuevo run de verificacion + auto-deriva scope."""
    await _set_project_rls(project_id, db)
    try:
        run = await VerificationService(db).create_run(
            project_id=project_id,
            category=body.category,
            mode=body.mode,
            tools_config=body.tools_config,
            schedule_now=body.schedule_now,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    # FIX 2026-06-07: get_db NO auto-commitea → sin esto el run se perdía al cerrar
    # la sesión (mismo patrón que retest/handoff/ingest que sí commitean).
    await db.commit()
    return _serialize_run_summary(run)


@router.get("/projects/{project_id}/verification/runs")
async def list_verification_runs(
    project_id: uuid.UUID,
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Lista runs del proyecto con filtro opcional por estado."""
    await _set_project_rls(project_id, db)
    runs = await VerificationService(db).list_runs(project_id, status=status)
    return {"runs": [_serialize_run_summary(r) for r in runs]}


@router.get("/projects/{project_id}/verification/runs/{run_id}")
async def get_verification_run(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Detalle de un run."""
    await _set_project_rls(project_id, db)
    try:
        run = await VerificationService(db).get_run(run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    if run.project_id != project_id:
        raise HTTPException(status_code=404, detail="Run no pertenece al proyecto")
    return _serialize_run_detail(run)


# ════════════════════════════════════════════════════════════════════
# FINDINGS (3 endpoints)
# ════════════════════════════════════════════════════════════════════

@router.get("/projects/{project_id}/verification/runs/{run_id}/findings")
async def list_findings(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    ens_measure: Optional[str] = Query(None),
    classification: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Findings del run con filtros opcionales."""
    await _set_project_rls(project_id, db)
    findings = await VerificationService(db).list_findings(
        run_id, severity=severity, status=status,
        ens_measure=ens_measure, classification=classification,
    )
    return {"findings": [_serialize_finding_summary(f) for f in findings]}


@router.patch("/projects/{project_id}/verification/findings/{finding_id}")
async def patch_finding(
    project_id: uuid.UUID,
    finding_id: uuid.UUID,
    body: FindingPatchBody,
    db: AsyncSession = Depends(get_db),
):
    """Actualiza estado del finding (FP / accepted_risk / remediated)."""
    await _set_project_rls(project_id, db)
    try:
        f = await VerificationService(db).patch_finding_status(
            finding_id,
            status=body.status,
            false_positive_reason=body.false_positive_reason,
            accepted_risk_justification=body.accepted_risk_justification,
            accepted_risk_approved_by=body.accepted_risk_approved_by,
        )
    except FindingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    await db.commit()  # get_db() no auto-commitea: persistir la disposición del finding
    return _serialize_finding_summary(f)


@router.patch("/projects/{project_id}/verification/findings/{finding_id}/mapping")
async def patch_finding_mapping(
    project_id: uuid.UUID,
    finding_id: uuid.UUID,
    body: FindingMappingPatchBody,
    db: AsyncSession = Depends(get_db),
):
    """Corrige el mapeo ENS de un finding manualmente."""
    await _set_project_rls(project_id, db)
    try:
        f = await VerificationService(db).patch_finding_mapping(
            finding_id,
            ens_measures=[m.model_dump() for m in body.ens_measures],
            ens_primary_measure=body.ens_primary_measure,
        )
    except FindingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await db.commit()  # get_db() no auto-commitea: persistir el mapeo ENS corregido
    return _serialize_finding_summary(f)


# ════════════════════════════════════════════════════════════════════
# REMEDIACION (2 endpoints)
# ════════════════════════════════════════════════════════════════════

@router.post("/projects/{project_id}/verification/findings/{finding_id}/retest")
async def request_retest(
    project_id: uuid.UUID,
    finding_id: uuid.UUID,
    body: RetestRequestBody,
    db: AsyncSession = Depends(get_db),
):
    """Ejecuta re-test quirurgico de un finding."""
    await _set_project_rls(project_id, db)
    try:
        f = await VerificationService(db).get_finding(finding_id)
    except FindingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    if f.project_id != project_id:
        raise HTTPException(status_code=404, detail="Finding no pertenece al proyecto")
    retest = await run_retest(
        db, f,
        triggered_by=body.triggered_by or "marcos",
        retest_type=body.retest_type,
    )
    await db.commit()
    return {
        "id": str(retest.id),
        "finding_id": str(retest.finding_id),
        "retest_type": retest.retest_type,
        "retest_command": retest.retest_command,
        "result": retest.result,
        "result_detail": retest.result_detail,
        "executed_at": retest.executed_at.isoformat() if retest.executed_at else None,
        "finding_status_after": f.status,
    }


@router.get("/projects/{project_id}/verification/remediation-plan")
async def get_remediation_plan(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Plan de remediacion priorizado por severity x effort con SLA deadlines."""
    await _set_project_rls(project_id, db)
    from sqlalchemy import select
    stmt = select(VerificationFinding).where(
        VerificationFinding.project_id == project_id,
        VerificationFinding.deleted_at.is_(None),
        VerificationFinding.status.in_(("open", "needs_review")),
        VerificationFinding.zfp_gate5_classification.in_(
            ("confirmed", "probable"),
        ),
    )
    findings = list((await db.execute(stmt)).scalars().all())
    ordered = prioritize_findings(findings)
    plan = []
    for f in ordered:
        sla = calculate_deadline(
            f.severity, f.created_at,
        )
        plan.append({
            "finding_id": str(f.id),
            "title": f.title,
            "severity": f.severity,
            "classification": f.zfp_gate5_classification,
            "affected_host": f.affected_host,
            "ens_primary_measure": f.ens_primary_measure,
            "remediation_effort": f.remediation_effort,
            "remediation_summary": f.remediation_summary,
            "status": f.status,
            "sla": sla.to_dict(),
        })
    return {"total": len(plan), "items": plan}


# ════════════════════════════════════════════════════════════════════
# HANDOFF PENTESTER EXTERNO (2 endpoints)
# ════════════════════════════════════════════════════════════════════

@router.post(
    "/projects/{project_id}/verification/handoff",
    status_code=http_status.HTTP_201_CREATED,
)
async def create_handoff(
    project_id: uuid.UUID,
    body: HandoffCreateBody,
    db: AsyncSession = Depends(get_db),
):
    """Genera paquete engagement (7 docs) para pentester externo."""
    await _set_project_rls(project_id, db)
    handoff = await build_handoff_package(db, body.run_id)
    # Actualizar datos del pentester en el run
    run = await db.get(VerificationRun, body.run_id)
    if run is not None and body.pentester_name:
        run.external_pentester_name = body.pentester_name
        run.external_pentester_cert = body.pentester_cert
        run.external_pentester_email = body.pentester_email
    await db.commit()
    return {
        "handoff_id": str(handoff.id),
        "project_id": str(handoff.project_id),
        "run_id": str(handoff.run_id),
        "status": handoff.status,
        "package_documents": handoff.package_documents,
        "pentester_name": body.pentester_name,
        "created_at": handoff.created_at.isoformat() if handoff.created_at else None,
    }


@router.post("/projects/{project_id}/verification/ingest")
async def ingest_external_findings_endpoint(
    project_id: uuid.UUID,
    body: IngestRequestBody,
    db: AsyncSession = Depends(get_db),
):
    """Ingesta findings de pentester externo (PDF o formulario estructurado)."""
    await _set_project_rls(project_id, db)
    if body.source == "structured_form":
        parsed = parse_structured_payload(body.findings or [])
    elif body.source == "pdf":
        if not body.pdf_base64:
            raise HTTPException(
                status_code=422,
                detail="source='pdf' requiere pdf_base64",
            )
        import base64
        pdf_bytes = base64.b64decode(body.pdf_base64)
        parsed = parse_pdf_payload(pdf_bytes)
    else:
        raise HTTPException(
            status_code=422,
            detail="source debe ser 'structured_form' o 'pdf'",
        )
    created = await ingest_external_findings(
        db, body.run_id, parsed,
        source=body.source,
        original_pdf_path=body.original_pdf_path,
    )
    await db.commit()
    return {
        "run_id": str(body.run_id),
        "source": body.source,
        "findings_ingested": len(created),
        "finding_ids": [str(f.id) for f in created],
    }


# ════════════════════════════════════════════════════════════════════
# INFORMES (4 endpoints)
# ════════════════════════════════════════════════════════════════════

@router.post("/projects/{project_id}/verification/runs/{run_id}/report")
async def generate_report_endpoint(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    body: ReportRequestBody,
    db: AsyncSession = Depends(get_db),
):
    """Genera informe E-702 / E-703 / E-704 via pipeline M6."""
    await _set_project_rls(project_id, db)
    gen = VerificationReportGenerator(db)
    try:
        result = await gen.generate_report(
            run_id, body.template_codigo,
            generate_pdf=body.generate_pdf,
            sign=body.sign,
            remediation_force_offline=body.remediation_force_offline,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await db.commit()
    return {
        "document_id": str(result["document_id"]),
        "template_codigo": result["template_codigo"],
        "nombre": result["nombre"],
        "docx_path": result["docx_path"],
        "pdf_path": result.get("pdf_path"),
        "rendered_hash": result["rendered_hash"],
        "signature_ed25519": result.get("signature_ed25519"),
        "estado": result["estado"],
    }


@router.get("/projects/{project_id}/verification/by-measure/{measure_code}")
async def findings_by_measure(
    project_id: uuid.UUID, measure_code: str,
    db: AsyncSession = Depends(get_db),
):
    """Findings de una medida ENS concreta + informes E-702/E-703 asociados.

    Alimenta K.5 Audit Mode para que Marcos ensene al auditor los
    hallazgos + evidencia del informe generado al preguntar sobre una
    medida.
    """
    await _set_project_rls(project_id, db)
    from sqlalchemy import select, or_ as _or
    from backend.app.models.documents import Document
    # Findings que mencionen la medida en ens_primary o en ens_measures
    stmt = select(VerificationFinding).where(
        VerificationFinding.project_id == project_id,
        VerificationFinding.deleted_at.is_(None),
        _or(
            VerificationFinding.ens_primary_measure == measure_code,
            VerificationFinding.ens_measures.contains(
                [{"measure": measure_code}]
            ),
        ),
    )
    findings = list((await db.execute(stmt)).scalars().all())

    severity_order = {
        "critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4,
    }
    findings.sort(key=lambda f: (
        severity_order.get((f.severity or "info").lower(), 99),
        -float(f.confidence_score or 0),
    ))

    # Documents E-702/E-703/E-704 del proyecto (el mas reciente por tipo)
    doc_stmt = (
        select(Document)
        .where(
            Document.project_id == project_id,
            Document.deleted_at.is_(None),
            Document.template_codigo.in_(("E-702", "E-703", "E-704")),
        )
        .order_by(Document.created_at.desc())
    )
    docs = list((await db.execute(doc_stmt)).scalars().all())
    latest_by_code: dict[str, Document] = {}
    for d in docs:
        code = d.template_codigo or ""
        if code and code not in latest_by_code:
            latest_by_code[code] = d

    last_verified = None
    if findings:
        dt = max(
            (f.updated_at or f.created_at) for f in findings
        )
        if dt:
            last_verified = dt.isoformat()

    open_critical_or_high = sum(
        1 for f in findings
        if (f.status or "open") in ("open", "needs_review")
        and (f.severity or "").lower() in ("critical", "high")
    )

    return {
        "measure_code": measure_code,
        "findings": [_serialize_finding_summary(f) for f in findings],
        "counts": {
            "total": len(findings),
            "open": sum(
                1 for f in findings
                if (f.status or "open") in ("open", "needs_review")
            ),
            "remediated": sum(
                1 for f in findings if f.status == "remediated"
            ),
            "critical_or_high_open": open_critical_or_high,
        },
        "reports": [
            {
                "document_id": str(d.id),
                "template_codigo": d.template_codigo,
                "nombre": d.nombre,
                "docx_path": d.docx_path,
                "pdf_path": d.pdf_path,
                "rendered_hash": d.rendered_hash,
                "generated_at": (
                    d.generated_at.isoformat() if d.generated_at else None
                ),
            }
            for d in latest_by_code.values()
        ],
        "last_verified": last_verified,
    }


@router.get("/projects/{project_id}/verification/heatmap")
async def get_compliance_heatmap(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Compliance heatmap de las 73 medidas ENS (Anexo II)."""
    await _set_project_rls(project_id, db)
    from sqlalchemy import select
    stmt = select(VerificationFinding).where(
        VerificationFinding.project_id == project_id,
        VerificationFinding.deleted_at.is_(None),
    )
    findings = list((await db.execute(stmt)).scalars().all())
    cells = generate_heatmap(findings, measures=ENS_73_MEASURES)
    summary = heatmap_summary(cells)
    total = summary["total"] or 1
    for key in ("compliant", "partial", "non_compliant", "not_verified"):
        summary[f"{key}_pct"] = round(100 * summary.get(key, 0) / total, 1)
    return {
        "cells": [c.to_dict() for c in cells],
        "summary": summary,
    }


@router.get("/projects/{project_id}/verification/score")
async def get_security_score(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Security score 0-100 actual + historico (ultimos 10 runs)."""
    await _set_project_rls(project_id, db)
    from sqlalchemy import select
    stmt = select(VerificationFinding).where(
        VerificationFinding.project_id == project_id,
        VerificationFinding.deleted_at.is_(None),
    )
    findings = list((await db.execute(stmt)).scalars().all())
    current = calculate_score(findings)

    history_stmt = (
        select(VerificationRun)
        .where(
            VerificationRun.project_id == project_id,
            VerificationRun.deleted_at.is_(None),
            VerificationRun.security_score.isnot(None),
        )
        .order_by(VerificationRun.completed_at.desc())
        .limit(10)
    )
    runs = list((await db.execute(history_stmt)).scalars().all())
    history = [
        {
            "run_id": str(r.id),
            "score": r.security_score,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in reversed(runs)
    ]
    return {
        "current": current.to_dict(),
        "history": history,
    }


@router.get("/projects/{project_id}/verification/delta")
async def get_delta_report(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delta vs run anterior: new / resolved / persistent + trend."""
    await _set_project_rls(project_id, db)
    from sqlalchemy import select
    last_runs_stmt = (
        select(VerificationRun)
        .where(
            VerificationRun.project_id == project_id,
            VerificationRun.deleted_at.is_(None),
            VerificationRun.status == "completed",
        )
        .order_by(VerificationRun.completed_at.desc())
        .limit(2)
    )
    runs = list((await db.execute(last_runs_stmt)).scalars().all())
    if len(runs) < 2:
        return {
            "previous_run_id": None,
            "current_run_id": str(runs[0].id) if runs else None,
            "new": [], "resolved": [], "persistent": [],
            "severity_changes": [],
            "overall_trend": "estable",
            "totals": {"new": 0, "resolved": 0, "persistent": 0, "severity_changes": 0},
            "weight_previous": 0, "weight_current": 0,
        }
    current_run, previous_run = runs[0], runs[1]
    cur_stmt = select(VerificationFinding).where(
        VerificationFinding.run_id == current_run.id,
        VerificationFinding.deleted_at.is_(None),
    )
    prev_stmt = select(VerificationFinding).where(
        VerificationFinding.run_id == previous_run.id,
        VerificationFinding.deleted_at.is_(None),
    )
    cur_findings = (await db.execute(cur_stmt)).scalars().all()
    prev_findings = (await db.execute(prev_stmt)).scalars().all()
    delta = compute_delta(prev_findings, cur_findings)
    payload = delta.to_dict()
    payload["previous_run_id"] = str(previous_run.id)
    payload["current_run_id"] = str(current_run.id)
    return payload


# ════════════════════════════════════════════════════════════════════
# KILL SWITCH (extra del esqueleto — funcional Checkpoint 1)
# ════════════════════════════════════════════════════════════════════

@router.post("/projects/{project_id}/verification/runs/{run_id}/kill")
async def kill_run(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Cancela un run en curso. Checkpoint 1: cambia estado en BD.
    Checkpoint 2.12 anade SIGTERM a procesos hijos + verificacion <5s.
    """
    await _set_project_rls(project_id, db)
    try:
        run = await request_kill(db, run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RunStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return _serialize_run_summary(run)
