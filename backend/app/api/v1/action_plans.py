"""Action Plans Aggregator · Dashboard K.3 · sub-atom 1.D.C.A v3.11.

Aggregator cross-motor que combina findings críticos/altos desde 4 fuentes:
  - M04 Gap (`findings` table · severidad critica/alta + estado abierto/en_curso)
  - M09 audit_prep checklist items (status open + priority high/critical)
  - M19 incidents impacto alto/crítico abiertos
  - A21 discrepancies open critical/high (1.D.A v3.10 cross-motor SQL)

Sostiene R23 + R24 + R32 v3.11 · admin-only view aggregated cross-motor.
Cliente NO ve este aggregator (suyo subset segregado per motor cliente-portal).

Materializa Anexo K dimension 3 (K.3 · Planes Acción consolidados ENS).
Cierra GAP 10 audit v4 (top 10 cross-motor findings visible admin).

OPS-045 17ª aplicación consecutiva: M09 dossier + M04 gap dashboard +
A21 discrepancies existing reuse · POLISH añadir aggregator endpoint.
"""
from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db


router = APIRouter(
    prefix="/projects",
    tags=["Action Plans · Dashboard K.3 cross-motor"],
    dependencies=[Depends(require_owner)],
)


# ════════════════════════════════════════════════════════════════════
# Schemas
# ════════════════════════════════════════════════════════════════════


ActionPlanSeverity = Literal["critica", "alta", "media", "baja"]
ActionPlanSource = Literal["m04_gap", "m09_audit_prep", "m19_incident", "a21_discrepancy"]
ActionPlanFamilia = Literal["org", "op", "mp", "cross"]
ActionPlanEstado = Literal["abierto", "en_curso", "cerrado", "descartado"]


class ActionPlanItem(BaseModel):
    """Item cross-motor aggregated para Dashboard K.3."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="UUID único item")
    source: ActionPlanSource = Field(..., description="Motor origen")
    severity: ActionPlanSeverity
    familia: ActionPlanFamilia = Field(
        "cross", description="org · op · mp · cross",
    )
    medida_afectada: str | None = Field(None, description="ENS Anexo II medida code")
    description: str
    responsable: str | None = Field(None, description="Responsable asignado")
    estado: ActionPlanEstado = Field("abierto")
    fecha_objetivo: str | None = Field(None, description="ISO date deadline")
    project_id: str
    motor_link: str | None = Field(
        None, description="URL admin sub-route para drill-down",
    )


class ActionPlansResponse(BaseModel):
    """Top 10 action plan items cross-motor + counts por source."""

    project_id: str
    total_count: int
    counts_by_source: dict[str, int]
    counts_by_severity: dict[str, int]
    items: list[ActionPlanItem]


# ════════════════════════════════════════════════════════════════════
# Aggregator service · cross-motor SQL queries
# ════════════════════════════════════════════════════════════════════


def _classify_familia(medida: str | None) -> ActionPlanFamilia:
    """Map medida ENS code → familia (org · op · mp · cross)."""
    if not medida:
        return "cross"
    m_lower = medida.lower()
    if m_lower.startswith("org."):
        return "org"
    if m_lower.startswith("op."):
        return "op"
    if m_lower.startswith("mp."):
        return "mp"
    return "cross"


async def _fetch_m04_gap_findings(
    db: AsyncSession,
    project_id: uuid.UUID,
    severity_filter: list[str] | None,
    estado_filter: list[str] | None,
) -> list[ActionPlanItem]:
    """M04 gap findings · severidad critica/alta + estado abierto/en_curso."""
    severities = severity_filter or ["critica", "alta"]
    estados = estado_filter or ["abierto", "en_curso"]
    rows = (await db.execute(sa_text(
        """
        SELECT id, severidad, medida_afectada, descripcion, estado,
               asignado_a, fecha_objetivo
        FROM findings
        WHERE project_id = :pid
          AND deleted_at IS NULL
          AND severidad = ANY(:sev)
          AND COALESCE(estado, 'abierto') = ANY(:est)
        ORDER BY
          CASE severidad
            WHEN 'critica' THEN 0 WHEN 'alta' THEN 1
            WHEN 'media' THEN 2 ELSE 3 END,
          fecha_objetivo NULLS LAST
        """,
    ), {"pid": str(project_id), "sev": severities, "est": estados})).fetchall()

    items: list[ActionPlanItem] = []
    for row in rows:
        items.append(ActionPlanItem(
            id=str(row[0]),
            source="m04_gap",
            severity=row[1] or "media",
            familia=_classify_familia(row[2]),
            medida_afectada=row[2],
            description=row[3] or "(sin descripción)",
            responsable=row[5],
            estado=row[4] or "abierto",
            fecha_objetivo=row[6].isoformat() if row[6] else None,
            project_id=str(project_id),
            motor_link=f"/admin/projects/{project_id}/plan",
        ))
    return items


async def _fetch_a21_discrepancies(
    db: AsyncSession,
    project_id: uuid.UUID,
    severity_filter: list[str] | None,
) -> list[ActionPlanItem]:
    """A21 discrepancies open critical/high (1.D.A v3.10 cross-motor SQL)."""
    # Map A21 severity (critical/high/medium/low) to action plan severity
    sev_map = {"critical": "critica", "high": "alta", "medium": "media", "low": "baja"}
    a21_severities: list[str] = []
    if severity_filter:
        for s in severity_filter:
            for k, v in sev_map.items():
                if v == s:
                    a21_severities.append(k)
    else:
        a21_severities = ["critical", "high"]

    rows = (await db.execute(sa_text(
        """
        SELECT id, severity, motor_a, motor_b, description, discrepancy_type
        FROM a21_discrepancies
        WHERE project_id = :pid
          AND deleted_at IS NULL
          AND resolution_status = 'open'
          AND severity = ANY(:sev)
        ORDER BY
          CASE severity
            WHEN 'critical' THEN 0 WHEN 'high' THEN 1
            WHEN 'medium' THEN 2 ELSE 3 END,
          created_at DESC
        """,
    ), {"pid": str(project_id), "sev": a21_severities})).fetchall()

    items: list[ActionPlanItem] = []
    for row in rows:
        items.append(ActionPlanItem(
            id=str(row[0]),
            source="a21_discrepancy",
            severity=sev_map.get(row[1], "media"),  # type: ignore[arg-type]
            familia="cross",
            medida_afectada=None,
            description=(row[4] or "")[:300] or "(sin descripción)",
            responsable=None,
            estado="abierto",
            fecha_objetivo=None,
            project_id=str(project_id),
            motor_link=f"/admin/projects/{project_id}/discrepancies",
        ))
    return items


async def _fetch_m09_audit_items(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> list[ActionPlanItem]:
    """M09 audit checklist items abiertos priority high/critical."""
    rows = (await db.execute(sa_text(
        """
        SELECT aci.id, aci.priority, aci.description, aci.measure_code,
               aci.status, aci.deadline
        FROM audit_checklist_items aci
        JOIN audit_preparation_runs apr ON aci.run_id = apr.id
        WHERE apr.project_id = :pid
          AND aci.deleted_at IS NULL
          AND aci.status IN ('open', 'in_progress')
          AND aci.priority IN ('critical', 'high')
        ORDER BY
          CASE aci.priority
            WHEN 'critical' THEN 0 WHEN 'high' THEN 1 ELSE 2 END,
          aci.deadline NULLS LAST
        """,
    ), {"pid": str(project_id)})).fetchall()

    pri_map = {"critical": "critica", "high": "alta", "medium": "media", "low": "baja"}
    items: list[ActionPlanItem] = []
    for row in rows:
        items.append(ActionPlanItem(
            id=str(row[0]),
            source="m09_audit_prep",
            severity=pri_map.get(row[1] or "high", "alta"),  # type: ignore[arg-type]
            familia=_classify_familia(row[3]),
            medida_afectada=row[3],
            description=(row[2] or "")[:300] or "(sin descripción)",
            responsable=None,
            estado=row[4] or "abierto",
            fecha_objetivo=row[5].isoformat() if row[5] else None,
            project_id=str(project_id),
            motor_link=f"/admin/projects/{project_id}/dossier",
        ))
    return items


async def aggregate_action_plans(
    db: AsyncSession,
    project_id: uuid.UUID,
    *,
    limit: int = 10,
    severity_filter: list[str] | None = None,
    estado_filter: list[str] | None = None,
    source_filter: list[str] | None = None,
) -> ActionPlansResponse:
    """Aggregate cross-motor top N findings ordenados severity desc + deadline."""
    sources = source_filter or ["m04_gap", "m09_audit_prep", "a21_discrepancy"]
    all_items: list[ActionPlanItem] = []

    if "m04_gap" in sources:
        try:
            items_m04 = await _fetch_m04_gap_findings(
                db, project_id, severity_filter, estado_filter,
            )
            all_items.extend(items_m04)
        except Exception:
            pass  # Best-effort cross-motor · NO break si una fuente falla

    if "a21_discrepancy" in sources:
        try:
            items_a21 = await _fetch_a21_discrepancies(
                db, project_id, severity_filter,
            )
            all_items.extend(items_a21)
        except Exception:
            pass

    if "m09_audit_prep" in sources:
        try:
            items_m09 = await _fetch_m09_audit_items(db, project_id)
            all_items.extend(items_m09)
        except Exception:
            pass

    # Sort severity desc + dateline · top N
    sev_order = {"critica": 0, "alta": 1, "media": 2, "baja": 3}
    all_items.sort(
        key=lambda x: (
            sev_order.get(x.severity, 4),
            x.fecha_objetivo or "9999-12-31",
        ),
    )

    top_items = all_items[:limit]
    counts_by_source: dict[str, int] = {}
    counts_by_severity: dict[str, int] = {}
    for item in all_items:
        counts_by_source[item.source] = counts_by_source.get(item.source, 0) + 1
        counts_by_severity[item.severity] = counts_by_severity.get(item.severity, 0) + 1

    return ActionPlansResponse(
        project_id=str(project_id),
        total_count=len(all_items),
        counts_by_source=counts_by_source,
        counts_by_severity=counts_by_severity,
        items=top_items,
    )


# ════════════════════════════════════════════════════════════════════
# Endpoints
# ════════════════════════════════════════════════════════════════════


@router.get(
    "/{project_id}/action-plans",
    response_model=ActionPlansResponse,
)
async def get_action_plans(
    project_id: uuid.UUID,
    limit: int = Query(10, ge=1, le=100, description="Top N items"),
    severity: list[str] | None = Query(
        None, description="Filter severities (critica · alta · media · baja)",
    ),
    estado: list[str] | None = Query(
        None, description="Filter estados (abierto · en_curso · cerrado · descartado)",
    ),
    source: list[str] | None = Query(
        None, description="Filter sources (m04_gap · m09_audit_prep · a21_discrepancy)",
    ),
    db: AsyncSession = Depends(get_db),
) -> ActionPlansResponse:
    """Dashboard K.3 · top N action plan items cross-motor admin view.

    Aggregates findings desde M04 gap + M09 audit_prep + A21 discrepancies ·
    sostiene Anexo K dimension 3 · cierra GAP 10 audit v4.
    """
    # Verify project exists via simple lookup
    project = (await db.execute(sa_text(
        "SELECT 1 FROM projects WHERE id = :pid AND deleted_at IS NULL",
    ), {"pid": str(project_id)})).first()
    if not project:
        raise HTTPException(404, "Project not found")

    return await aggregate_action_plans(
        db, project_id,
        limit=limit,
        severity_filter=severity,
        estado_filter=estado,
        source_filter=source,
    )
