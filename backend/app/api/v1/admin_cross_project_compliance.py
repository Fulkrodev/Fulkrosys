"""Admin Cross-Project Compliance Aggregator · Bloque 4 Phase B v3.12.

Aggregator admin que muestra compliance posture de TODOS los projects cliente
en single pane of glass. Reuse data existing cross-motor · NO new tables.

Endpoint: GET /api/v1/admin/cross-project-compliance
Auth: require_owner (admin-only · NO cliente data leak)

Per project agg row:
  - client_name + project_id + project_name
  - lifecycle_state + categoria_objetivo (BASICA/MEDIA/ALTA)
  - overall_health (computed from sub-counts)
  - 5 area counts (conformity_status · remediations_pending · tasks_pending · evidences_missing · gaps_critical)
  - last_activity_at

R23 sostener · TODO admin-scoped global (multi-cliente legítimo per R23 explicit
exception · same pattern /admin/projects/ root list).
ADR-025 28a aplicacion sostained · NO new tables · query aggregate cross-motor.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db


HealthIndicator = Literal["ok", "warning", "critical", "unknown"]


router = APIRouter(
    prefix="/admin/cross-project-compliance",
    tags=["Admin · Cross-Project Compliance (Bloque 4)"],
    dependencies=[Depends(require_owner)],
)


# ──────────────────────────────────────────────────────────────────────
# Schemas


class ProjectComplianceRow(BaseModel):
    project_id: str
    project_name: str
    client_id: str
    client_name: str
    lifecycle_state: str | None
    categoria_objetivo: str | None
    overall_health: HealthIndicator
    conformity_status: HealthIndicator
    remediations_pending: int
    tasks_pending: int
    evidences_missing: int
    gaps_critical_open: int
    last_activity_at: str | None


class CrossProjectComplianceResponse(BaseModel):
    generated_at: str
    total_projects: int
    counts_by_health: dict[str, int]
    projects: list[ProjectComplianceRow]


# ──────────────────────────────────────────────────────────────────────
# Helpers


def _overall_from_counts(
    conformity: HealthIndicator,
    remediations_pending: int,
    tasks_pending: int,
    evidences_missing: int,
    gaps_critical: int,
) -> HealthIndicator:
    if gaps_critical > 0 or conformity == "critical":
        return "critical"
    if (
        remediations_pending > 0
        or tasks_pending > 0
        or evidences_missing > 0
        or conformity == "warning"
    ):
        return "warning"
    if conformity == "unknown":
        return "unknown"
    return "ok"


# ──────────────────────────────────────────────────────────────────────
# Endpoint


@router.get("", response_model=CrossProjectComplianceResponse)
async def list_cross_project_compliance(
    only_active: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
) -> CrossProjectComplianceResponse:
    """List ALL projects compliance aggregated · admin single pane of glass."""

    # Query base · projects + client info (no RLS · admin-scoped)
    project_filter = "AND p.deleted_at IS NULL "
    if only_active:
        project_filter += "AND (p.lifecycle_state IS NULL OR p.lifecycle_state != 'ARCHIVED') "

    projects_query = sa_text(
        f"""
        SELECT p.id AS project_id, p.nombre AS project_name,
               c.id AS client_id, c.nombre AS client_name,
               p.lifecycle_state, p.categoria_objetivo,
               p.updated_at AS last_activity_at
        FROM projects p
        JOIN clients c ON c.id = p.client_id
        WHERE c.deleted_at IS NULL
        {project_filter}
        ORDER BY c.nombre ASC, p.nombre ASC
        """
    )
    rows = (await db.execute(projects_query)).mappings().all()

    # Per project · count from each source (cross-motor aggregator)
    project_rows: list[ProjectComplianceRow] = []
    counts_by_health: dict[str, int] = {
        "ok": 0, "warning": 0, "critical": 0, "unknown": 0,
    }

    for row in rows:
        project_id = str(row["project_id"])

        # Remediations pending cliente (Bloque 3+5)
        try:
            rem = (await db.execute(
                sa_text(
                    "SELECT COUNT(*) FROM cloud_gaps "
                    "WHERE project_id = :pid "
                    "  AND approval_status = 'proposed_to_cliente' "
                    "  AND deleted_at IS NULL"
                ),
                {"pid": project_id},
            )).scalar()
            remediations_pending = int(rem or 0)
        except Exception:  # noqa: BLE001
            remediations_pending = 0

        # Tasks pending
        try:
            t = (await db.execute(
                sa_text(
                    "SELECT COUNT(*) FROM client_tasks "
                    "WHERE project_id = :pid "
                    "  AND status IN ('pending', 'in_progress') "
                    "  AND deleted_at IS NULL"
                ),
                {"pid": project_id},
            )).scalar()
            tasks_pending = int(t or 0)
        except Exception:  # noqa: BLE001
            tasks_pending = 0

        # Evidences missing
        # §2.2 audit-2026-06-15 · la tabla es `evidence_requests` (NO
        # evidence_collection_requests · inexistente) + status pending_cliente/
        # rejected. SAVEPOINT (begin_nested) para que un fallo NO envenene la
        # transacción y haga 500 el resto de COUNTs (mirror client_compliance_summary).
        try:
            async with db.begin_nested():
                e = (await db.execute(
                    sa_text(
                        "SELECT COUNT(*) FROM evidence_requests "
                        "WHERE project_id = :pid "
                        "  AND status IN ('pending_cliente', 'rejected')"
                    ),
                    {"pid": project_id},
                )).scalar()
            evidences_missing = int(e or 0)
        except Exception:  # noqa: BLE001
            evidences_missing = 0

        # Gaps critical M04 · §2.2 · la columna es `severidad` (NO `severity`).
        try:
            async with db.begin_nested():
                g = (await db.execute(
                    sa_text(
                        "SELECT COUNT(*) FROM findings "
                        "WHERE project_id = :pid "
                        "  AND severidad IN ('critica', 'alta', 'critical', 'high') "
                        "  AND estado IN ('abierto', 'open', 'en_curso')"
                    ),
                    {"pid": project_id},
                )).scalar()
            gaps_critical = int(g or 0)
        except Exception:  # noqa: BLE001
            gaps_critical = 0

        # Conformity coarse status · §2.2 · la tabla es `conformity_routes`
        # (col `status`) · `conformity_declarations` NO existe.
        try:
            async with db.begin_nested():
                c_row = (await db.execute(
                    sa_text(
                        "SELECT status FROM conformity_routes "
                        "WHERE project_id = :pid "
                        "ORDER BY created_at DESC LIMIT 1"
                    ),
                    {"pid": project_id},
                )).first()
            if c_row is None:
                conformity_status: HealthIndicator = "unknown"
            else:
                estado = (c_row[0] or "").lower()
                if any(k in estado for k in (
                    "regist", "cert", "vigente", "firmad", "aprob",
                    "accept", "complet",
                )):
                    conformity_status = "ok"
                else:
                    conformity_status = "warning"
        except Exception:  # noqa: BLE001
            conformity_status = "unknown"

        overall = _overall_from_counts(
            conformity=conformity_status,
            remediations_pending=remediations_pending,
            tasks_pending=tasks_pending,
            evidences_missing=evidences_missing,
            gaps_critical=gaps_critical,
        )
        counts_by_health[overall] = counts_by_health.get(overall, 0) + 1

        project_rows.append(ProjectComplianceRow(
            project_id=project_id,
            project_name=str(row["project_name"]),
            client_id=str(row["client_id"]),
            client_name=str(row["client_name"]),
            lifecycle_state=(
                str(row["lifecycle_state"]) if row.get("lifecycle_state") else None
            ),
            categoria_objetivo=(
                str(row["categoria_objetivo"]) if row.get("categoria_objetivo") else None
            ),
            overall_health=overall,
            conformity_status=conformity_status,
            remediations_pending=remediations_pending,
            tasks_pending=tasks_pending,
            evidences_missing=evidences_missing,
            gaps_critical_open=gaps_critical,
            last_activity_at=(
                row["last_activity_at"].isoformat()
                if row.get("last_activity_at") else None
            ),
        ))

    return CrossProjectComplianceResponse(
        generated_at=datetime.now(timezone.utc).isoformat(),
        total_projects=len(project_rows),
        counts_by_health=counts_by_health,
        projects=project_rows,
    )
