"""Agente 26 — Gestor de Retainers.

Analiza el estado de todos los retainers activos y genera alertas
deterministas a Marcos con priorizacion. Detecta patrones:
- Actividades sistematicamente atrasadas
- Clientes que no responden (sin magic link consumido en X dias)
- Incidents recurrentes
- Retainers infra-dimensionados (R_MICRO con demasiados incidents -> sugerir upgrade)
- Retainers sobre-dimensionados (R_PLUS con uso bajo -> sugerir downgrade)

Determinista por defecto (sin LLM). Capa LLM opcional para drafts
de emails al cliente via Haiku.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.core import Client
from backend.app.models.retainer import (
    RetainerActivity, RetainerContract, RetainerDriftEvent,
)


@dataclass
class RetainerAlert:
    """Alerta generada por agente 26 para un retainer concreto."""
    retainer_contract_id: uuid.UUID
    client_name: str
    tier: str
    priority: str  # critical | high | medium | low
    code: str
    title: str
    description: str
    suggested_action: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "retainer_contract_id": str(self.retainer_contract_id),
            "client_name": self.client_name,
            "tier": self.tier,
            "priority": self.priority,
            "code": self.code,
            "title": self.title,
            "description": self.description,
            "suggested_action": self.suggested_action,
            "metadata": self.metadata,
        }


# ════════════════════════════════════════════════════════════════════
# Reglas deterministas
# ════════════════════════════════════════════════════════════════════

async def _rule_overdue_activities(
    db: AsyncSession, rc: RetainerContract, client_name: str,
) -> list[RetainerAlert]:
    today = date.today()
    r = await db.execute(
        select(func.count(RetainerActivity.id)).where(
            RetainerActivity.retainer_contract_id == rc.id,
            RetainerActivity.estado.in_(["programada", "en_curso"]),
            RetainerActivity.fecha_programada < today,
            RetainerActivity.deleted_at.is_(None),
        )
    )
    overdue = r.scalar() or 0
    if overdue == 0:
        return []

    if overdue >= 3:
        priority = "critical"
    elif overdue == 2:
        priority = "high"
    else:
        priority = "medium"

    return [RetainerAlert(
        retainer_contract_id=rc.id,
        client_name=client_name,
        tier=rc.perfil or "R_STD",
        priority=priority,
        code="A26_OVERDUE_ACTIVITIES",
        title=f"{overdue} actividades vencidas en {client_name}",
        description=(
            f"El retainer de {client_name} ({rc.perfil}) tiene {overdue} "
            f"actividades programadas que han pasado su fecha sin ejecutar."
        ),
        suggested_action=(
            "Revisar calendario y reprogramar actividades no criticas; "
            "escalar a cliente las que dependen de su aportacion."
        ),
        metadata={"overdue_count": overdue},
    )]


async def _rule_critical_drift(
    db: AsyncSession, rc: RetainerContract, client_name: str,
) -> list[RetainerAlert]:
    r = await db.execute(
        select(func.count(RetainerDriftEvent.id)).where(
            RetainerDriftEvent.retainer_contract_id == rc.id,
            RetainerDriftEvent.severidad == "CRITICAL",
            RetainerDriftEvent.estado.in_(["open", "acknowledged"]),
            RetainerDriftEvent.deleted_at.is_(None),
        )
    )
    criticals = r.scalar() or 0
    if criticals == 0:
        return []
    return [RetainerAlert(
        retainer_contract_id=rc.id,
        client_name=client_name,
        tier=rc.perfil or "R_STD",
        priority="critical",
        code="A26_CRITICAL_DRIFT",
        title=f"{criticals} drift(s) CRITICAL abiertos en {client_name}",
        description=(
            f"Detectados {criticals} eventos de drift CRITICAL "
            f"sin resolver. Riesgo de perder la certificacion ENS."
        ),
        suggested_action=(
            "Planificar auditoria extraordinaria. "
            "Considerar trigger_material_change_audit() si aplica."
        ),
        metadata={"drift_critical_count": criticals},
    )]


async def _rule_renewal_urgent(
    rc: RetainerContract, client_name: str,
) -> list[RetainerAlert]:
    if rc.renewal_status not in {"T_MINUS_30", "T_MINUS_60", "LAPSED"}:
        return []
    priority = "critical" if rc.renewal_status == "LAPSED" else "high"
    return [RetainerAlert(
        retainer_contract_id=rc.id,
        client_name=client_name,
        tier=rc.perfil or "R_STD",
        priority=priority,
        code="A26_RENEWAL_URGENT",
        title=f"Renovacion bianual {rc.renewal_status} - {client_name}",
        description=(
            f"El proyecto esta en ventana de renovacion ({rc.renewal_status}). "
            f"Fecha: {rc.next_renewal_date}."
        ),
        suggested_action=(
            "Ejecutar generate_dossier(force=False) para preparar "
            "re-certificacion. Contactar al cliente para agendar auditor externo."
        ),
        metadata={
            "renewal_status": rc.renewal_status,
            "next_renewal_date": str(rc.next_renewal_date),
        },
    )]


async def _rule_upgrade_candidate(
    db: AsyncSession, rc: RetainerContract, client_name: str,
) -> list[RetainerAlert]:
    """Si un R_MICRO o R_LITE tiene muchos drift/incidents, sugerir upgrade."""
    if rc.perfil not in {"R_MICRO", "R_LITE"}:
        return []
    since = datetime.now(timezone.utc) - timedelta(days=90)
    r = await db.execute(
        select(func.count(RetainerDriftEvent.id)).where(
            RetainerDriftEvent.retainer_contract_id == rc.id,
            RetainerDriftEvent.severidad.in_(["HIGH", "CRITICAL"]),
            RetainerDriftEvent.created_at >= since,
            RetainerDriftEvent.deleted_at.is_(None),
        )
    )
    drift_90d = r.scalar() or 0
    if drift_90d < 3:
        return []
    suggested = "R_STD" if rc.perfil == "R_MICRO" else "R_PLUS"
    return [RetainerAlert(
        retainer_contract_id=rc.id,
        client_name=client_name,
        tier=rc.perfil,
        priority="medium",
        code="A26_UPGRADE_CANDIDATE",
        title=f"Candidato upgrade: {client_name} {rc.perfil} -> {suggested}",
        description=(
            f"Retainer {rc.perfil} con {drift_90d} drift events HIGH/CRITICAL "
            f"en 90 dias sugiere infra-dimensionado."
        ),
        suggested_action=(
            f"Proponer upgrade a {suggested} al cliente con justificacion "
            "tecnica (drift events + SLA)."
        ),
        metadata={
            "drift_90d": drift_90d,
            "suggested_tier": suggested,
        },
    )]


async def _rule_no_response(
    db: AsyncSession, rc: RetainerContract, client_name: str,
) -> list[RetainerAlert]:
    """S5 · Cliente sin acceso al portal en >45 días (o nunca) · riesgo de
    desatención del mantenimiento ENS."""
    row = (await db.execute(
        text(
            "SELECT MAX(last_login) FROM client_users "
            "WHERE client_id = :cid AND deleted_at IS NULL"
        ),
        {"cid": str(rc.client_id)},
    )).first()
    last_login = row[0] if row else None
    threshold = datetime.now(timezone.utc) - timedelta(days=45)
    if last_login is not None and last_login > threshold:
        return []
    dias = (
        (datetime.now(timezone.utc) - last_login).days
        if last_login is not None else None
    )
    return [RetainerAlert(
        retainer_contract_id=rc.id,
        client_name=client_name,
        tier=rc.perfil or "R_STD",
        priority="high",
        code="A26_CLIENT_NO_RESPONSE",
        title=f"Cliente sin actividad en portal — {client_name}",
        description=(
            f"{client_name} no ha accedido al portal "
            + (f"en {dias} días." if dias is not None else "nunca.")
            + " Riesgo de desatención del mantenimiento ENS."
        ),
        suggested_action=(
            "Contactar al cliente para reactivar el seguimiento; confirmar "
            "interlocutor y agendar check-in."
        ),
        metadata={"dias_sin_login": dias},
    )]


async def _rule_recurring_incidents(
    db: AsyncSession, rc: RetainerContract, client_name: str,
) -> list[RetainerAlert]:
    """S5 · Reincidencia: drift HIGH/CRITICAL en ≥2 meses distintos de los
    últimos 90 días (patrón crónico, no incidente puntual)."""
    since = datetime.now(timezone.utc) - timedelta(days=90)
    row = (await db.execute(
        text(
            "SELECT count(DISTINCT date_trunc('month', created_at)) "
            "FROM retainer_drift_events "
            "WHERE retainer_contract_id = :rid "
            "AND severidad IN ('HIGH', 'CRITICAL') "
            "AND created_at >= :since AND deleted_at IS NULL"
        ),
        {"rid": str(rc.id), "since": since},
    )).first()
    months = int(row[0] or 0) if row else 0
    if months < 2:
        return []
    return [RetainerAlert(
        retainer_contract_id=rc.id,
        client_name=client_name,
        tier=rc.perfil or "R_STD",
        priority="high",
        code="A26_RECURRING_DRIFT",
        title=f"Drift recurrente ({months} meses) — {client_name}",
        description=(
            f"{client_name} acumula drift HIGH/CRITICAL en {months} meses "
            "distintos de los últimos 90 días: patrón crónico, no puntual."
        ),
        suggested_action=(
            "Investigar causa raíz recurrente; valorar auditoría extraordinaria "
            "o ajuste del plan de tratamiento."
        ),
        metadata={"months_with_incidents": months},
    )]


async def _rule_downgrade_candidate(
    db: AsyncSession, rc: RetainerContract, client_name: str,
) -> list[RetainerAlert]:
    """S5 · Sobre-dimensionado: R_PLUS/R_CRITICAL con muy poca actividad
    ejecutada en 90 días · sugerir downgrade (inverso de upgrade_candidate)."""
    if rc.perfil not in {"R_PLUS", "R_CRITICAL"}:
        return []
    since = datetime.now(timezone.utc) - timedelta(days=90)
    r = await db.execute(
        select(func.count(RetainerActivity.id)).where(
            RetainerActivity.retainer_contract_id == rc.id,
            RetainerActivity.estado == "completada",
            RetainerActivity.fecha_ejecutada >= since,
            RetainerActivity.deleted_at.is_(None),
        )
    )
    actividades_90d = r.scalar() or 0
    if actividades_90d >= 2:
        return []
    suggested = "R_STD" if rc.perfil == "R_PLUS" else "R_PLUS"
    return [RetainerAlert(
        retainer_contract_id=rc.id,
        client_name=client_name,
        tier=rc.perfil,
        priority="low",
        code="A26_DOWNGRADE_CANDIDATE",
        title=f"Candidato downgrade: {client_name} {rc.perfil} -> {suggested}",
        description=(
            f"Retainer {rc.perfil} con solo {actividades_90d} actividades "
            "ejecutadas en 90 días: posible sobre-dimensionado."
        ),
        suggested_action=(
            f"Valorar downgrade a {suggested} o reactivar el uso del retainer "
            "con el cliente (revisar valor entregado)."
        ),
        metadata={"actividades_90d": actividades_90d, "suggested_tier": suggested},
    )]


# ════════════════════════════════════════════════════════════════════
# Runner
# ════════════════════════════════════════════════════════════════════

async def run_weekly_analysis(
    db: AsyncSession,
) -> list[RetainerAlert]:
    """Recorre todos los retainers active y genera alertas."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    r = await db.execute(
        select(RetainerContract).where(
            RetainerContract.estado == "active",
            RetainerContract.deleted_at.is_(None),
        )
    )
    retainers = list(r.scalars().all())

    # Cache de nombres cliente
    client_names: dict[uuid.UUID, str] = {}
    if retainers:
        client_ids = {rc.client_id for rc in retainers}
        r = await db.execute(
            select(Client.id, Client.nombre).where(Client.id.in_(client_ids))
        )
        client_names = {row[0]: row[1] for row in r.all()}

    alerts: list[RetainerAlert] = []
    for rc in retainers:
        client_name = client_names.get(rc.client_id, "Cliente")
        alerts.extend(await _rule_overdue_activities(db, rc, client_name))
        alerts.extend(await _rule_critical_drift(db, rc, client_name))
        alerts.extend(await _rule_renewal_urgent(rc, client_name))
        alerts.extend(await _rule_upgrade_candidate(db, rc, client_name))
        alerts.extend(await _rule_no_response(db, rc, client_name))
        alerts.extend(await _rule_recurring_incidents(db, rc, client_name))
        alerts.extend(await _rule_downgrade_candidate(db, rc, client_name))

    # Ordenar por priority
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    alerts.sort(key=lambda a: order.get(a.priority, 99))
    return alerts


async def summary_for_marcos(db: AsyncSession) -> dict[str, Any]:
    """Resumen ejecutivo para dashboard Marcos: N alertas por priority."""
    alerts = await run_weekly_analysis(db)
    by_priority: dict[str, int] = {}
    by_code: dict[str, int] = {}
    for a in alerts:
        by_priority[a.priority] = by_priority.get(a.priority, 0) + 1
        by_code[a.code] = by_code.get(a.code, 0) + 1
    return {
        "total_alerts": len(alerts),
        "by_priority": by_priority,
        "by_code": by_code,
        "top_5": [a.to_dict() for a in alerts[:5]],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def draft_client_email_offline(alert: RetainerAlert) -> dict[str, str]:
    """Draft determinista de email a cliente (sin LLM).

    Para alertas que justifican contacto con el cliente. Marcos puede
    revisar y enviar via M12 magic link con purpose notificacion.
    """
    templates = {
        "A26_OVERDUE_ACTIVITIES": {
            "subject": f"Accion requerida — {alert.client_name} · actividades pendientes",
            "body": (
                f"Estimado responsable de seguridad,\n\n"
                f"En el marco del mantenimiento ENS, hay {alert.metadata.get('overdue_count', 0)} "
                f"actividades programadas pendientes de completar. Te adjunto el listado "
                f"priorizado para que podamos agendar una llamada breve.\n\n"
                f"Un saludo,\nMarcos"
            ),
        },
        "A26_RENEWAL_URGENT": {
            "subject": f"Re-certificacion ENS — preparacion ({alert.client_name})",
            "body": (
                "Estimado responsable de seguridad,\n\n"
                "Nos acercamos a la fecha de renovacion de la certificacion ENS. "
                "Es el momento de agendar al auditor externo y revisar el dossier "
                "de re-certificacion. Propongo llamada esta semana.\n\n"
                "Un saludo,\nMarcos"
            ),
        },
        "A26_UPGRADE_CANDIDATE": {
            "subject": f"Revision nivel de servicio — {alert.client_name}",
            "body": (
                f"Estimado responsable de seguridad,\n\n"
                f"Tras analizar la actividad de los ultimos 3 meses, considero "
                f"adecuado valorar el upgrade a {alert.metadata.get('suggested_tier')}. "
                f"Te explico en una llamada breve los motivos tecnicos.\n\n"
                f"Un saludo,\nMarcos"
            ),
        },
        "A26_CLIENT_NO_RESPONSE": {
            "subject": f"Seguimiento ENS — {alert.client_name}",
            "body": (
                "Estimado responsable de seguridad,\n\n"
                "Hace tiempo que no registramos actividad por tu parte en el "
                "portal de seguimiento ENS. Para mantener al dia el mantenimiento "
                "y la conformidad, me gustaria agendar un breve check-in.\n\n"
                "Un saludo,\nMarcos"
            ),
        },
    }
    return templates.get(alert.code, {
        "subject": f"Notificacion — {alert.client_name}",
        "body": alert.description,
    })


__all__ = [
    "RetainerAlert",
    "run_weekly_analysis",
    "summary_for_marcos",
    "draft_client_email_offline",
]
