"""M8 Autopilot · API REST (doc §13-§14 · 2 gates humanos).

Endpoints admin (require_owner · Cat A Marcos-only):
- POST /projects/{id}/verification/autopilot/start    → Gate 1 done → "Continuar"
- GET  /projects/{id}/verification/autopilot/status   → estado live del run
- GET  /projects/{id}/verification/metrics            → observabilidad (§12)
- GET  /projects/{id}/verification/runs/{rid}/evidence-pack → evidencia ENAC (§16)
- POST /projects/{id}/verification/findings/{fid}/accept-risk → aceptación riesgo (§8)
- POST /projects/{id}/verification/runs/{rid}/attest  → Gate 2 atestación (Alto)

El autopilot corre en background task (sesión propia) tras el start, y emite
progreso por SSE (canal project:{id}). Patrón espejo de mcp_executor_service.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db, set_tenant_context, async_session

from .models import EvidenceRecord, VerificationFinding, VerificationRun
from .observability import build_enac_evidence_pack, compute_observability_metrics
from .remediation.risk_acceptance import accept_risk, risk_acceptance_status
from .service import FindingNotFoundError, VerificationService

router = APIRouter(
    tags=["Motor 8 - Autopilot Pentesting v2.0"],
    dependencies=[Depends(require_owner)],
)

# Refs fuertes a background tasks (evita GC mid-run · patrón mcp_executor)
_BG_TASKS: set[asyncio.Task] = set()


async def _set_project_rls(project_id: uuid.UUID, db: AsyncSession) -> uuid.UUID:
    client_id = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)},
    )).scalar()
    if not client_id:
        raise HTTPException(status_code=404, detail="Project not found")
    await set_tenant_context(db, client_id=client_id, project_id=project_id)
    return client_id


async def _run_autopilot_bg(run_id: uuid.UUID, project_id: uuid.UUID) -> None:
    """Ejecuta el orquestador en una sesión propia (NO la del request)."""
    from .autopilot.orchestrator import orchestrate_run
    try:
        async with async_session() as db:
            await _set_project_rls(project_id, db)
            await orchestrate_run(db, run_id)
            await db.commit()
    except Exception:  # pragma: no cover — el orquestador ya marca status=failed
        import logging
        logging.getLogger(__name__).exception("autopilot bg run %s falló", run_id)


# ════════════════════════════════════════════════════════════════════
# Schemas
# ════════════════════════════════════════════════════════════════════

class AutopilotStartBody(BaseModel):
    category: str = Field(..., description="BASICA|MEDIA|ALTA (o BASICO/MEDIO/ALTO)")
    mode: str = "internal"


class AcceptRiskBody(BaseModel):
    justification: str
    approved_by: str
    expires_at: datetime


class AttestBody(BaseModel):
    attested_by: str
    cert: Optional[str] = None
    opinion: Optional[str] = None


def _serialize_autopilot(run: VerificationRun) -> dict:
    return {
        "run_id": str(run.id),
        "category": run.category,
        "mode": run.mode,
        "status": run.status,
        "autopilot_status": run.autopilot_status,
        "autopilot_phase": run.autopilot_phase,
        "coverage_pct": float(run.coverage_pct) if run.coverage_pct is not None else None,
        "assets_in_scope": run.assets_in_scope,
        "assets_scanned": run.assets_scanned,
        "partial_run": bool(run.partial_run),
        "run_manifest_hash": run.run_manifest_hash,
        "total_findings": run.total_findings or 0,
        "critical_count": run.critical_count or 0,
        "high_count": run.high_count or 0,
        "medium_count": run.medium_count or 0,
        "low_count": run.low_count or 0,
        "info_count": run.info_count or 0,
        "tools_attempted": run.tools_attempted or [],
        "tools_failed": run.tools_failed or [],
        "ephemeral_active": (
            run.ephemeral_session_id is not None and run.ephemeral_revoked_at is None
        ),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }


# ════════════════════════════════════════════════════════════════════
# Endpoints
# ════════════════════════════════════════════════════════════════════

@router.post(
    "/projects/{project_id}/verification/autopilot/start",
    status_code=http_status.HTTP_201_CREATED,
)
async def start_autopilot(
    project_id: uuid.UUID,
    body: AutopilotStartBody,
    db: AsyncSession = Depends(get_db),
):
    """Gate 1 superado (autorización/scope) → "Continuar": crea el run y lanza
    el autopilot en background. Devuelve el run_id para suscribir SSE."""
    await _set_project_rls(project_id, db)
    try:
        run = await VerificationService(db).create_run(
            project_id=project_id, category=body.category, mode=body.mode,
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    run.autopilot_status = "authorized"
    await db.commit()

    task = asyncio.create_task(_run_autopilot_bg(run.id, project_id))
    _BG_TASKS.add(task)
    task.add_done_callback(_BG_TASKS.discard)

    return {
        "run_id": str(run.id),
        "autopilot_status": "authorized",
        "category": run.category,
        "sse_channel": f"project:{project_id}",
        "message": "Autopilot lanzado · suscribe SSE para progreso live",
    }


@router.get("/projects/{project_id}/verification/autopilot/status")
async def autopilot_status(
    project_id: uuid.UUID,
    run_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Estado live del autopilot (run concreto o el último del proyecto)."""
    await _set_project_rls(project_id, db)
    stmt = select(VerificationRun).where(
        VerificationRun.project_id == project_id,
        VerificationRun.deleted_at.is_(None),
    )
    if run_id:
        stmt = stmt.where(VerificationRun.id == run_id)
    stmt = stmt.order_by(VerificationRun.created_at.desc()).limit(1)
    run = (await db.execute(stmt)).scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="No autopilot runs")
    return _serialize_autopilot(run)


@router.get("/projects/{project_id}/verification/metrics")
async def get_metrics(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Observabilidad (doc §12): coverage% / FP-rate / MTTR / drift / health."""
    await _set_project_rls(project_id, db)
    return await compute_observability_metrics(db, project_id)


@router.get("/projects/{project_id}/verification/runs/{run_id}/evidence-pack")
async def get_evidence_pack(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Pack de evidencia ENAC (doc §16) para un run."""
    await _set_project_rls(project_id, db)
    try:
        pack = await build_enac_evidence_pack(db, run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    if pack.get("project_id") != str(project_id):
        raise HTTPException(status_code=404, detail="Run no pertenece al proyecto")
    return pack


@router.post("/projects/{project_id}/verification/findings/{finding_id}/accept-risk")
async def accept_finding_risk(
    project_id: uuid.UUID,
    finding_id: uuid.UUID,
    body: AcceptRiskBody,
    db: AsyncSession = Depends(get_db),
):
    """Aceptación de riesgo con justificación + autoridad + caducidad (doc §8)."""
    await _set_project_rls(project_id, db)
    try:
        finding = await VerificationService(db).get_finding(finding_id)
    except FindingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    if finding.project_id != project_id:
        raise HTTPException(status_code=404, detail="Finding no pertenece al proyecto")
    try:
        await accept_risk(
            db, finding, justification=body.justification,
            approved_by=body.approved_by, expires_at=body.expires_at,
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    await db.commit()
    return {"finding_id": str(finding.id), "finding_state": finding.finding_state,
            "risk_acceptance": risk_acceptance_status(finding)}


@router.post("/projects/{project_id}/verification/runs/{run_id}/attest")
async def attest_run(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    body: AttestBody,
    db: AsyncSession = Depends(get_db),
):
    """Gate 2 humano (Alto · doc §14): validación cualificada + atestación.

    Cierra el run pausado en `paused_gate2` tras la validación del pentester
    acreditado (CPSTIC/OSCP). Registra evidencia append-only de la atestación.
    """
    await _set_project_rls(project_id, db)
    run = await db.get(VerificationRun, run_id)
    if run is None or run.project_id != project_id:
        raise HTTPException(status_code=404, detail="Run no encontrado")
    run.external_pentester_name = body.attested_by
    if body.cert:
        run.external_pentester_cert = body.cert
    run.autopilot_status = "completed"
    run.status = "completed"
    db.add(EvidenceRecord(
        project_id=project_id, client_id=None, run_id=run.id, finding_id=None,
        run_manifest_hash=run.run_manifest_hash,
        actor=f"human:{body.attested_by}", action="gate2.attested",
        component="m08:autopilot.gate2",
        payload={"attested_by": body.attested_by, "cert": body.cert,
                 "opinion": (body.opinion or "")[:2000],
                 "attested_at": datetime.now(timezone.utc).isoformat()},
    ))
    await db.commit()
    return {"run_id": str(run.id), "autopilot_status": run.autopilot_status,
            "attested_by": body.attested_by}
