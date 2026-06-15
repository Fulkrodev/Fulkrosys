"""Client Compliance Summary Aggregator · Bloque 4 Phase A v3.12.

Endpoint aggregator que combina compliance status per-project cliente desde
multiples motores existing · cliente portal feed unificado.

Sources aggregated:
  - M27 Conformity readiness (estado declaración + categoría + fecha)
  - M04 Gap findings open + pending tasks cliente
  - M07 Evidencias cliente_can_see count
  - Cloud Remediations Bloque 3+5 (proposed_to_cliente + executing pending)
  - Tasks cliente pending action (m21_portal_cliente)

R29 firmísimo · per area genera friendly_message Spanish primer principios ·
NUNCA jerga técnica · NUNCA presión coercitiva.

ADR-013 doble pool · require_client_user (cliente pool).
ADR-025 28ª aplicación · NO new tables · query cross-motor data existing.

Per cliente piloto MEDIA: 1 cliente ≈ 1 project típico (Audit Bloque 1 #4
cliente portal single-project assumption sostained 1.E.2.bis).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_client_user
from backend.app.database import get_db, set_tenant_context


HealthIndicator = Literal["ok", "warning", "critical", "unknown"]


router = APIRouter(
    prefix="/client-portal/compliance-summary",
    tags=["Client Portal · Compliance Summary (Bloque 4)"],
    dependencies=[Depends(require_client_user)],
)


# ──────────────────────────────────────────────────────────────────────
# Schemas


class ComplianceArea(BaseModel):
    area_key: str
    title: str
    status: HealthIndicator
    friendly_message: str
    pending_count: int
    detail_url: str | None = None


class ComplianceSummaryResponse(BaseModel):
    project_id: str | None
    overall_health: HealthIndicator
    generated_at: str
    areas: list[ComplianceArea]


# ──────────────────────────────────────────────────────────────────────
# Helpers · per-area friendly_message generators


def _conformity_message(status: str, pending: int) -> tuple[HealthIndicator, str]:
    """M27 conformity readiness friendly Spanish."""
    if status == "ok" and pending == 0:
        return "ok", "Tu declaración de conformidad está al día."
    if status == "warning":
        return "warning", "Tu declaración necesita una revisión cuando puedas."
    if status == "critical":
        return (
            "critical",
            "Hay algo en tu declaración que necesita tu atención.",
        )
    return "unknown", "Aún no hemos generado tu declaración."


def _remediations_message(pending: int) -> tuple[HealthIndicator, str]:
    """Cloud remediations Bloque 3+5 friendly Spanish."""
    if pending == 0:
        return "ok", "No tienes mejoras pendientes de decidir."
    if pending == 1:
        return "warning", "Tienes 1 mejora pendiente de decidir."
    return "warning", f"Tienes {pending} mejoras pendientes de decidir."


def _tasks_message(pending: int) -> tuple[HealthIndicator, str]:
    """Tasks cliente pending friendly Spanish."""
    if pending == 0:
        return "ok", "Estás al día con tus tareas."
    if pending == 1:
        return "warning", "Tienes 1 tarea pendiente."
    return "warning", f"Tienes {pending} tareas pendientes."


def _evidencias_message(missing_count: int) -> tuple[HealthIndicator, str]:
    """Evidencias cliente friendly Spanish."""
    if missing_count == 0:
        return "ok", "Las evidencias necesarias están subidas."
    if missing_count <= 3:
        return (
            "warning",
            f"Faltan {missing_count} documentos por subir cuando puedas.",
        )
    return (
        "warning",
        f"Faltan {missing_count} documentos por subir.",
    )


def _gaps_message(critical_open: int) -> tuple[HealthIndicator, str]:
    """M04 gaps críticos abiertos friendly Spanish."""
    if critical_open == 0:
        return "ok", "Sin temas críticos abiertos."
    if critical_open == 1:
        return "critical", "Hay 1 tema crítico abierto que Marcos te explicará."
    return "critical", f"Hay {critical_open} temas críticos abiertos."


# ──────────────────────────────────────────────────────────────────────
# Aggregator core


def _overall_from_areas(areas: list[ComplianceArea]) -> HealthIndicator:
    """Compute overall_health desde max severity across areas (deterministic)."""
    statuses = [a.status for a in areas]
    if "critical" in statuses:
        return "critical"
    if "warning" in statuses:
        return "warning"
    if "unknown" in statuses and "ok" not in statuses:
        return "unknown"
    return "ok"


async def _resolve_project_for_client(
    db: AsyncSession, cliente_user,
) -> str | None:
    """Resolve project_id del cliente (single-project assumption 1.E.2.bis)."""
    cliente_client_id = getattr(cliente_user, "client_id", None)
    if cliente_client_id is None:
        return None

    row = await db.execute(
        sa_text(
            "SELECT id FROM projects "
            "WHERE client_id = :cid AND deleted_at IS NULL "
            "ORDER BY created_at ASC LIMIT 1"
        ),
        {"cid": str(cliente_client_id)},
    )
    project_row = row.first()
    return str(project_row[0]) if project_row else None


async def _safe_scalar(
    db: AsyncSession, sql: str, params: dict, default: int = 0,
) -> int:
    """Run a COUNT/scalar query inside a SAVEPOINT (best-effort).

    Bug auditoría 2026-06-12: un helper que tragaba la excepción con `except`
    pero SIN rollback dejaba la transacción asyncpg en estado *aborted*; la
    siguiente query (no envuelta) moría con `InFailedSQLTransactionError` y el
    endpoint devolvía 500 (p.ej. `conformity_declarations` inexistente
    envenenaba el COUNT de `cloud_gaps`). El SAVEPOINT aísla cada fallo: el
    rollback afecta solo al savepoint y NUNCA a la transacción externa ni al
    contexto RLS (`set_config(... , is_local=true)`).
    """
    try:
        async with db.begin_nested():
            row = await db.execute(sa_text(sql), params)
            val = row.scalar()
        return int(val) if val is not None else default
    except Exception:  # noqa: BLE001 · tolerate schema variant / absence
        return default


async def _count_pending_remediations(
    db: AsyncSession, project_id: str,
) -> int:
    return await _safe_scalar(
        db,
        "SELECT COUNT(*) FROM cloud_gaps "
        "WHERE project_id = :pid "
        "  AND cliente_can_see = true "
        "  AND approval_status = 'proposed_to_cliente' "
        "  AND deleted_at IS NULL",
        {"pid": project_id},
    )


async def _count_pending_tasks(
    db: AsyncSession, project_id: str,
) -> int:
    """ClientTask pending (status pending OR in_progress · NO done)."""
    return await _safe_scalar(
        db,
        "SELECT COUNT(*) FROM client_tasks "
        "WHERE project_id = :pid "
        "  AND status IN ('pending', 'in_progress') "
        "  AND deleted_at IS NULL",
        {"pid": project_id},
    )


async def _count_critical_open_gaps(
    db: AsyncSession, project_id: str,
) -> int:
    """M04 gap findings critical/high open (best-effort · tolerates schema variant)."""
    # Bug auditoría 2026-06-07: la columna es `severidad` (NO `severity`).
    # Valores reales incl. critica/alta + variantes en inglés por compat.
    return await _safe_scalar(
        db,
        "SELECT COUNT(*) FROM findings "
        "WHERE project_id = :pid "
        "  AND severidad IN ('critica', 'alta', 'critical', 'high') "
        "  AND estado IN ('abierto', 'open', 'en_curso')",
        {"pid": project_id},
    )


async def _conformity_status_raw(
    db: AsyncSession, project_id: str,
) -> tuple[str, int]:
    """M27 conformity readiness coarse status · best-effort.

    Bug auditoría 2026-06-12: leía de `conformity_declarations` (tabla
    INEXISTENTE) → el cliente nunca veía estado real y además envenenaba la
    transacción (ver `_safe_scalar`). La tabla real es `conformity_routes`
    (columna `status`: REGISTERED / SUBMITTED / ACCEPTED / ...). Se lee la
    ruta más reciente del proyecto dentro de un SAVEPOINT.
    """
    estado = ""
    try:
        async with db.begin_nested():
            row = await db.execute(
                sa_text(
                    "SELECT status FROM conformity_routes "
                    "WHERE project_id = :pid "
                    "ORDER BY created_at DESC LIMIT 1"
                ),
                {"pid": project_id},
            )
            hit = row.first()
        if hit is None:
            return "unknown", 0
        estado = (hit[0] or "").upper()
    except Exception:  # noqa: BLE001
        return "unknown", 0
    # §2.2 audit-2026-06-15 · membership EXPLÍCITA contra RouteState (route_machine)
    # en vez de substring-keyword (que daba falsos verdes CERTIFICATION_IN_PROGRESS
    # y falsos amarillos CONFORMANT). Sólo conforme/registrado/vigente = al día.
    if estado in ("CONFORMANT", "REGISTERED", "ACTIVE"):
        return "ok", 0
    # En curso → warning con 1 pendiente.
    return "warning", 1


async def _count_missing_evidences(
    db: AsyncSession, project_id: str,
) -> int:
    """Evidencias cliente_can_see missing (status pending OR rejected · best-effort)."""
    # Bug auditoría 2026-06-07: la tabla es `evidence_requests`. Estados que
    # exigen acción del cliente: pending_cliente (subir) + rejected (re-subir).
    return await _safe_scalar(
        db,
        "SELECT COUNT(*) FROM evidence_requests "
        "WHERE project_id = :pid "
        "  AND status IN ('pending_cliente', 'rejected')",
        {"pid": project_id},
    )


# ──────────────────────────────────────────────────────────────────────
# Endpoint


@router.get("", response_model=ComplianceSummaryResponse)
async def get_compliance_summary(
    cliente_user=Depends(require_client_user),
    db: AsyncSession = Depends(get_db),
) -> ComplianceSummaryResponse:
    """Aggregator cliente compliance summary · 5 áreas cross-motor."""
    project_id = await _resolve_project_for_client(db, cliente_user)
    if project_id is None:
        return ComplianceSummaryResponse(
            project_id=None,
            overall_health="unknown",
            generated_at=datetime.now(timezone.utc).isoformat(),
            areas=[],
        )

    await set_tenant_context(db, project_id=project_id)

    # Per area · query data + generate friendly_message
    conformity_raw_status, conformity_pending = await _conformity_status_raw(
        db, project_id,
    )
    conformity_status, conformity_msg = _conformity_message(
        conformity_raw_status, conformity_pending,
    )

    remediations_pending = await _count_pending_remediations(db, project_id)
    rem_status, rem_msg = _remediations_message(remediations_pending)

    tasks_pending = await _count_pending_tasks(db, project_id)
    tasks_status, tasks_msg = _tasks_message(tasks_pending)

    missing_evidences = await _count_missing_evidences(db, project_id)
    ev_status, ev_msg = _evidencias_message(missing_evidences)

    critical_gaps = await _count_critical_open_gaps(db, project_id)
    gaps_status, gaps_msg = _gaps_message(critical_gaps)

    areas: list[ComplianceArea] = [
        ComplianceArea(
            area_key="conformity",
            title="Declaración de conformidad",
            status=conformity_status,
            friendly_message=conformity_msg,
            pending_count=conformity_pending,
            detail_url="/client-portal/conformidad",
        ),
        ComplianceArea(
            area_key="remediations",
            title="Mejoras propuestas",
            status=rem_status,
            friendly_message=rem_msg,
            pending_count=remediations_pending,
            detail_url="/client-portal/remediaciones",
        ),
        ComplianceArea(
            area_key="tasks",
            title="Tareas pendientes",
            status=tasks_status,
            friendly_message=tasks_msg,
            pending_count=tasks_pending,
            detail_url="/client-portal/tasks",
        ),
        ComplianceArea(
            area_key="evidences",
            title="Documentos a subir",
            status=ev_status,
            friendly_message=ev_msg,
            pending_count=missing_evidences,
            detail_url="/client-portal/files",
        ),
        ComplianceArea(
            area_key="gaps",
            title="Temas críticos abiertos",
            status=gaps_status,
            friendly_message=gaps_msg,
            pending_count=critical_gaps,
            detail_url=None,
        ),
    ]

    overall = _overall_from_areas(areas)

    return ComplianceSummaryResponse(
        project_id=project_id,
        overall_health=overall,
        generated_at=datetime.now(timezone.utc).isoformat(),
        areas=areas,
    )
