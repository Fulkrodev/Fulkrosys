"""Agent 11 · Project-scoped wrapper endpoint (MB-5.0).

Cierre fantasma A11: el endpoint base `/api/v1/agents/11/run-supplementary-audit`
requiere body manual con M10 result + client context. Este wrapper
project-scoped auto-compone el body desde el último M10 run del proyecto
+ client info, exponiendo un trigger UI más amigable.

POST /api/v1/projects/{project_id}/agents/11/run-supplementary-audit
Query opcional: ?run_id=<m10_run_uuid> (else picks latest completed)
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models.audit_sim import (
    AuditSimulationFinding,
    AuditSimulationRun,
)
from backend.app.models.core import Client, Project


router = APIRouter(tags=["Agent 11 - Auditor Virtual (project-scoped wrapper)"])


async def _set_project_rls(
    project_id: uuid.UUID, db: AsyncSession,
) -> uuid.UUID:
    cid = (await db.execute(
        sa_text("SELECT get_project_owner(:pid)"),
        {"pid": str(project_id)},
    )).scalar()
    if not cid:
        raise HTTPException(404, "Project not found")
    return cid


class A11WrapperResponse(BaseModel):
    run_id: str  # M10 run usado como base
    a11_result: dict


def _infer_sector(client: Client) -> str:
    """Heurística simple: cliente.sector → enum A11."""
    if not client.sector:
        return "otro"
    sector_lower = client.sector.lower()
    if any(k in sector_lower for k in ("salud", "sanid", "hospital", "clinic")):
        return "sanidad"
    if any(k in sector_lower for k in ("aapp", "publica", "ministerio", "ayunt", "gobierno")):
        return "aapp"
    if any(k in sector_lower for k in ("fintech", "banca", "seguros", "fondo")):
        return "fintech"
    return "otro"


def _infer_size(num_employees: int | None) -> str:
    if num_employees is None:
        return "PYME"
    if num_employees < 50:
        return "PYME"
    if num_employees < 250:
        return "mediana"
    return "grande"


@router.post(
    "/projects/{project_id}/agents/11/run-supplementary-audit",
    response_model=A11WrapperResponse,
)
async def run_supplementary_audit_for_project(
    project_id: uuid.UUID,
    run_id: uuid.UUID | None = Query(
        None, description="M10 run UUID (else latest completed)",
    ),
    db: AsyncSession = Depends(get_db),
) -> A11WrapperResponse:
    """Wrapper UI-friendly: resuelve M10 run + project context y llama A11."""
    await _set_project_rls(project_id, db)

    # Resolver M10 run: explicit run_id o último completed para el proyecto
    if run_id:
        m10_run = await db.get(AuditSimulationRun, run_id)
        if m10_run is None or m10_run.project_id != project_id:
            raise HTTPException(404, "M10 run no encontrado para este proyecto")
    else:
        m10_run = (await db.execute(
            select(AuditSimulationRun).where(
                AuditSimulationRun.project_id == project_id,
                AuditSimulationRun.estado == "completed",
                AuditSimulationRun.deleted_at.is_(None),
            ).order_by(AuditSimulationRun.completed_at.desc().nulls_last()).limit(1),
        )).scalar_one_or_none()
        if m10_run is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Sin auditoría M10 completada para este proyecto. "
                    "Ejecuta primero un audit-sim run y reintenta."
                ),
            )

    # Cargar findings para extraer NC mayores/menores con códigos
    findings_rows = (await db.execute(
        select(
            AuditSimulationFinding.measure_code,
            AuditSimulationFinding.measure_name,
            AuditSimulationFinding.evaluacion,
            AuditSimulationFinding.nivel_madurez,
        ).where(
            AuditSimulationFinding.run_id == m10_run.id,
            AuditSimulationFinding.deleted_at.is_(None),
        ),
    )).all()

    nc_mayores: list[dict[str, str]] = []
    nc_menores: list[dict[str, str]] = []
    counts_l: dict[str, int] = {f"L{i}": 0 for i in range(6)}
    for r in findings_rows:
        code, name, evaluacion, nivel = r[0], r[1], r[2], r[3]
        if evaluacion == "no_conforme_mayor":
            nc_mayores.append({"codigo": code, "descripcion": name or code})
        elif evaluacion == "no_conforme_menor":
            nc_menores.append({"codigo": code, "descripcion": name or code})
        # FIX(dead-default): poblar el histograma de madurez (counts_l se
        # declaraba pero nunca se llenaba → preguntas_L* leían claves _total_LX
        # inexistentes → siempre 0 en el input del auditor A11).
        if evaluacion != "no_aplica" and nivel in counts_l:
            counts_l[nivel] += 1

    # Project + Client context
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    client = await db.get(Client, project.client_id)
    if not client:
        raise HTTPException(404, "Client not found")

    m10_audit_result = {
        "score_conformidad": int(m10_run.score_global or 0),
        "categoria_ens": m10_run.categoria or "MEDIA",
        "nc_mayores": nc_mayores,
        "nc_menores": nc_menores,
        "preguntas_L5": counts_l["L5"],
        "preguntas_L4": counts_l["L4"],
        "preguntas_L3": counts_l["L3"],
        "preguntas_L2": counts_l["L2"],
        "preguntas_L1": counts_l["L1"],
        "preguntas_L0": counts_l["L0"],
        "preguntas_respondidas_total": int(m10_run.measures_evaluated or 0),
    }

    target_audit_str: str | None = None
    if isinstance(project.fecha_objetivo_certificacion, date):
        target_audit_str = project.fecha_objetivo_certificacion.isoformat()

    client_context: dict[str, Any] = {
        "company_name": client.nombre,
        "sector": _infer_sector(client),
        "size": _infer_size(client.numero_empleados),
        "ens_category": project.categoria_objetivo or m10_run.categoria or "MEDIA",
        "is_aapp": _infer_sector(client) == "aapp",
        "target_audit_date": target_audit_str,
    }

    # Invocar A11 vía servicio existing
    from backend.app.agents.agent_11_auditor_virtual import (
        Agent11AuditorVirtual,
    )
    agent = Agent11AuditorVirtual()
    try:
        result = await agent.generate_supplementary_audit(
            db,
            m10_audit_result=m10_audit_result,
            client_context=client_context,
            project_id=project_id,
        )
    except Exception as exc:
        raise HTTPException(500, f"A11 falló: {exc}")
    await db.commit()

    return A11WrapperResponse(
        run_id=str(m10_run.id),
        a11_result=result if isinstance(result, dict) else {"raw": str(result)},
    )
