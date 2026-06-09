"""Marcos cockpit admin dashboard aggregator · FASE 2 H4 wire-up real.

Cross-motor aggregator para vista home admin (`/api/v1/dashboard/*`). Distinct
de:
- ``adaptive_dashboard_service.py`` (cliente portal · scope per-cliente)
- ``m21_diagnosis/dashboard_service.py`` (project-level · scope per-project)

Admin dashboard tiene scope **cross-clients cross-projects Marcos cockpit**
agregando KPIs + MyDay + Alerts + Activity desde múltiples motors existing.

NO scope creep guided mode (ADR-050 cement defer MB-14): simple REST
aggregator · NO state machine · NO next-best-action engine.

Endpoints servidos (registrados en ``api/v1/dashboard.py``):
    GET /api/v1/dashboard/kpis     → DashboardKpis
    GET /api/v1/dashboard/my-day   → list[MyDayItem]
    GET /api/v1/dashboard/alerts   → list[DashboardAlert]
    GET /api/v1/dashboard/activity → list[ActivityEvent]
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession


RagStatus = Literal["green", "amber", "red"]


# ──────────────────────────────────────────────────────────────────────
# Pydantic schemas · alineadas con frontend/lib/types.ts (admin dashboard)
# ──────────────────────────────────────────────────────────────────────


class DashboardKpis(BaseModel):
    """Cross-clients KPIs Marcos cockpit (header KpiRow)."""

    active_projects: int = Field(0, description="Proyectos activos (NO archived/purged)")
    leads_count: int = Field(0, description="Leads en pipeline (NO ganado/descartado/no_interesa)")
    leads_value_eur: float = Field(0.0, description="Suma proposals.importe_total de leads activos")
    retainers_active: int = Field(0, description="Retainer contracts estado='active'")
    mrr_eur: float = Field(0.0, description="Monthly Recurring Revenue · sum retainers.precio_mensual")
    treasury_30d_eur: float = Field(0.0, description="Sum invoices.total emitidas últimos 30 días")
    treasury_trend_pct: float = Field(0.0, description="% trend vs 30d previos (positivo=crece)")
    projects_rag: RagStatus = Field("green", description="Worst-of-all rag_status retainers activos")


class MyDayItem(BaseModel):
    """Item home Marcos · "Tu día" · 4 tipos (review/signature/meeting/other)."""

    id: str
    type: Literal["review_docs", "signature", "meeting", "other"]
    title: str
    href: Optional[str] = None
    count: Optional[int] = None
    scheduledAt: Optional[str] = None


class DashboardAlert(BaseModel):
    """Cross-motor alert agregado (m_compliance_monitor + m23 drift + m19 risk)."""

    id: str
    severity: RagStatus
    project: Optional[str] = None
    message: str
    createdAt: str


class ActivityEvent(BaseModel):
    """Recent activity event derivado de audit_log + signing/verification/proposals events."""

    id: str
    timestamp: str
    type: Literal[
        "evidence_generated",
        "scan_completed",
        "proposal_sent",
        "document_signed",
        "agent_run",
        "other",
    ]
    description: str
    project_slug: Optional[str] = None
    agent_id: Optional[int] = None


# ──────────────────────────────────────────────────────────────────────
# Service · stateless cross-motor aggregator
# ──────────────────────────────────────────────────────────────────────


class AdminDashboardService:
    """Aggregator stateless para Marcos cockpit admin dashboard.

    Cada método ejecuta queries SQL contra modelos existing (Lead · Proposal ·
    RetainerContract · Invoice · ComplianceAlert · audit_log · signing_intents ·
    verification_runs · exploratory_meetings).
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_kpis(self) -> DashboardKpis:
        """KPIs cross-clients · header KpiRow Marcos cockpit."""
        session = self.session

        active_projects = await session.execute(
            sa_text(
                "SELECT COUNT(*) FROM projects "
                "WHERE deleted_at IS NULL "
                "  AND (lifecycle_state IS NULL OR lifecycle_state NOT IN ('ARCHIVED', 'PURGED'))"
                # #7.3 guard de coherencia: los proyectos LIGEROS (lead en embudo ·
                # DRAFT + pre_venta) NO son proyectos activos.
                "  AND NOT (lifecycle_state = 'DRAFT' AND fase = 'pre_venta')"
            )
        )
        active_projects_count = active_projects.scalar_one() or 0

        leads_count_row = await session.execute(
            sa_text(
                "SELECT COUNT(*) FROM leads "
                "WHERE deleted_at IS NULL "
                "  AND (estado_contacto IS NULL "
                "       OR estado_contacto NOT IN ('ganado', 'descartado', 'no_interesa'))"
            )
        )
        leads_count = leads_count_row.scalar_one() or 0

        leads_value_row = await session.execute(
            sa_text(
                "SELECT COALESCE(SUM(p.importe_total), 0) "
                "FROM proposals p "
                "JOIN leads l ON p.lead_id = l.id "
                "WHERE p.deleted_at IS NULL "
                "  AND l.deleted_at IS NULL "
                "  AND (l.estado_contacto IS NULL "
                "       OR l.estado_contacto NOT IN ('ganado', 'descartado', 'no_interesa'))"
            )
        )
        leads_value_eur = float(leads_value_row.scalar_one() or 0)

        retainers_row = await session.execute(
            sa_text(
                "SELECT COUNT(*) FROM retainer_contracts "
                "WHERE deleted_at IS NULL AND estado = 'active'"
            )
        )
        retainers_active = retainers_row.scalar_one() or 0

        mrr_row = await session.execute(
            sa_text(
                "SELECT COALESCE(SUM(precio_mensual), 0) FROM retainer_contracts "
                "WHERE deleted_at IS NULL AND estado = 'active'"
            )
        )
        mrr_eur = float(mrr_row.scalar_one() or 0)

        treasury_30d_row = await session.execute(
            sa_text(
                "SELECT COALESCE(SUM(total), 0) FROM invoices "
                "WHERE deleted_at IS NULL "
                "  AND fecha_emision >= CURRENT_DATE - INTERVAL '30 days'"
            )
        )
        treasury_30d_eur = float(treasury_30d_row.scalar_one() or 0)

        treasury_prev_row = await session.execute(
            sa_text(
                "SELECT COALESCE(SUM(total), 0) FROM invoices "
                "WHERE deleted_at IS NULL "
                "  AND fecha_emision >= CURRENT_DATE - INTERVAL '60 days' "
                "  AND fecha_emision <  CURRENT_DATE - INTERVAL '30 days'"
            )
        )
        treasury_prev_eur = float(treasury_prev_row.scalar_one() or 0)

        if treasury_prev_eur > 0:
            treasury_trend_pct = round(
                ((treasury_30d_eur - treasury_prev_eur) / treasury_prev_eur) * 100.0, 1
            )
        else:
            treasury_trend_pct = 0.0

        # projects_rag: worst-of-all retainers activos rag_status
        rag_row = await session.execute(
            sa_text(
                "SELECT CASE "
                "  WHEN COUNT(*) FILTER (WHERE rag_status = 'red') > 0 THEN 'red' "
                "  WHEN COUNT(*) FILTER (WHERE rag_status = 'amber') > 0 THEN 'amber' "
                "  ELSE 'green' "
                "END "
                "FROM retainer_contracts "
                "WHERE deleted_at IS NULL AND estado = 'active'"
            )
        )
        projects_rag: RagStatus = rag_row.scalar_one() or "green"

        return DashboardKpis(
            active_projects=active_projects_count,
            leads_count=leads_count,
            leads_value_eur=leads_value_eur,
            retainers_active=retainers_active,
            mrr_eur=mrr_eur,
            treasury_30d_eur=treasury_30d_eur,
            treasury_trend_pct=treasury_trend_pct,
            projects_rag=projects_rag,
        )

    async def get_my_day(self, limit: int = 5) -> list[MyDayItem]:
        """Today's tasks Marcos · documents pending review + signatures + meetings."""
        session = self.session
        items: list[MyDayItem] = []

        # 1 · Documents pending Marcos approval (M06 documents · approved_at IS NULL)
        docs_pending_row = await session.execute(
            sa_text(
                "SELECT COUNT(*) FROM documents "
                "WHERE deleted_at IS NULL "
                "  AND approved_at IS NULL "
                "  AND tipo = 'politica'"
            )
        )
        docs_pending = docs_pending_row.scalar_one() or 0
        if docs_pending > 0:
            items.append(
                MyDayItem(
                    id="md-docs",
                    type="review_docs",
                    title=f"Revisar {docs_pending} documento{'s' if docs_pending != 1 else ''} pendiente{'s' if docs_pending != 1 else ''}",
                    count=docs_pending,
                    href="/admin/projects",
                )
            )

        # 2 · Signatures pending Marcos counterparty (contratos firmado_cliente_at NOT NULL AND firmado_marcos_at IS NULL)
        sigs_pending_row = await session.execute(
            sa_text(
                "SELECT COUNT(*) FROM contracts "
                "WHERE deleted_at IS NULL "
                "  AND firmado_cliente_at IS NOT NULL "
                "  AND firmado_marcos_at IS NULL"
            )
        )
        sigs_pending = sigs_pending_row.scalar_one() or 0
        if sigs_pending > 0:
            items.append(
                MyDayItem(
                    id="md-signatures",
                    type="signature",
                    title=f"Firmar {sigs_pending} contrato{'s' if sigs_pending != 1 else ''} pendiente{'s' if sigs_pending != 1 else ''}",
                    count=sigs_pending,
                    href="/admin/projects",
                )
            )

        # 3 · Today's exploratory meetings (scheduled today · status='scheduled' implicit via meeting_date::date = today)
        # Note: exploratory_meetings uses UUIDPrimaryKeyMixin (NO deleted_at column).
        meetings_rows = await session.execute(
            sa_text(
                "SELECT em.id, em.title, em.meeting_date, em.client_id, c.nombre "
                "FROM exploratory_meetings em "
                "LEFT JOIN clients c ON c.id = em.client_id "
                "WHERE em.meeting_date::date = CURRENT_DATE "
                "  AND (em.conversion_status NOT IN ('cancelled')) "
                "ORDER BY em.meeting_date ASC "
                "LIMIT :lim"
            ),
            {"lim": limit},
        )
        for row in meetings_rows.fetchall():
            meeting_id, title, meeting_date, client_id, client_name = row
            display_title = title if title else f"Reunión con {client_name or 'cliente'}"
            items.append(
                MyDayItem(
                    id=f"md-mtg-{meeting_id}",
                    type="meeting",
                    title=display_title,
                    scheduledAt=meeting_date.isoformat() if meeting_date else None,
                    href="/admin/meeting",
                )
            )

        # 4 · M21 client_tasks active (admin pool · pending + in_progress)
        # · cross-project visibility Marcos. ClientTask NO tiene field category
        # empirical · all map type="other" (honest fallback Q2 cement Marcos).
        tasks_rows = await session.execute(
            sa_text(
                "SELECT ct.id, ct.title, ct.cta_url, ct.status "
                "FROM client_tasks ct "
                "WHERE ct.deleted_at IS NULL "
                "  AND ct.status IN ('pending', 'in_progress') "
                "ORDER BY ct.priority DESC, ct.due_date ASC NULLS LAST "
                "LIMIT :lim"
            ),
            {"lim": limit},
        )
        for row in tasks_rows.fetchall():
            task_id, title, cta_url, status = row
            items.append(
                MyDayItem(
                    id=f"md-task-{task_id}",
                    type="other",
                    title=title or "Tarea cliente pendiente",
                    href=cta_url or "/admin/projects",
                )
            )

        return items[:limit]

    async def get_alerts(self, limit: int = 10) -> list[DashboardAlert]:
        """Cross-motor alerts · compliance_alerts + retainer drift events."""
        session = self.session
        alerts: list[DashboardAlert] = []

        # Compliance alerts (m_compliance_monitor) · severity HIGH/CRITICAL → red, MEDIUM → amber, LOW → green
        compliance_rows = await session.execute(
            sa_text(
                "SELECT ca.id, ca.severity, ca.message, ca.created_at "
                "FROM compliance_alerts ca "
                "WHERE ca.status = 'open' "
                "ORDER BY ca.created_at DESC "
                "LIMIT :lim"
            ),
            {"lim": limit},
        )
        for row in compliance_rows.fetchall():
            alert_id, severity, message, created_at = row
            sev_lower = (severity or "low").lower()
            rag: RagStatus = (
                "red" if sev_lower in ("high", "critical")
                else "amber" if sev_lower == "medium"
                else "green"
            )
            alerts.append(
                DashboardAlert(
                    id=f"compliance-{alert_id}",
                    severity=rag,
                    project=None,
                    message=message or "Compliance alert",
                    createdAt=created_at.isoformat() if created_at else "",
                )
            )

        # Retainer drift events (m23 · severidad CRITICAL/HIGH → red, MEDIUM → amber, LOW → green)
        drift_rows = await session.execute(
            sa_text(
                "SELECT rde.id, rde.severidad, rde.descripcion, rde.created_at, "
                "       p.nombre AS project_name "
                "FROM retainer_drift_events rde "
                "LEFT JOIN projects p ON p.id = rde.project_id "
                "WHERE rde.deleted_at IS NULL "
                "  AND rde.estado IN ('open', 'acknowledged') "
                "ORDER BY rde.created_at DESC "
                "LIMIT :lim"
            ),
            {"lim": limit},
        )
        for row in drift_rows.fetchall():
            drift_id, severidad, descripcion, created_at, project_name = row
            sev_lower = (severidad or "low").lower()
            rag = (
                "red" if sev_lower in ("high", "critical")
                else "amber" if sev_lower == "medium"
                else "green"
            )
            alerts.append(
                DashboardAlert(
                    id=f"drift-{drift_id}",
                    severity=rag,
                    project=project_name,
                    message=descripcion or "Drift detected",
                    createdAt=created_at.isoformat() if created_at else "",
                )
            )

        # M19 incidents abiertos (workflow_state NOT IN resolved/closed)
        # · severidad map low/medium/high/critical → rag
        incident_rows = await session.execute(
            sa_text(
                "SELECT i.id, i.severidad, i.workflow_state, i.created_at, "
                "       p.nombre AS project_name "
                "FROM incidents i "
                "LEFT JOIN projects p ON p.id = i.project_id "
                "WHERE i.deleted_at IS NULL "
                "  AND (i.workflow_state IS NULL "
                "       OR i.workflow_state NOT IN ('resolved', 'closed')) "
                "ORDER BY i.created_at DESC "
                "LIMIT :lim"
            ),
            {"lim": limit},
        )
        for row in incident_rows.fetchall():
            inc_id, severidad, workflow_state, created_at, project_name = row
            sev_lower = (severidad or "").lower()
            rag = (
                "red" if sev_lower in ("high", "critical")
                else "amber" if sev_lower == "medium"
                else "green" if sev_lower == "low"
                else "amber"  # default unknown severity = amber (visible)
            )
            state_label = workflow_state or "abierto"
            alerts.append(
                DashboardAlert(
                    id=f"incident-{inc_id}",
                    severity=rag,
                    project=project_name,
                    message=f"Incidente seguridad · estado {state_label}",
                    createdAt=created_at.isoformat() if created_at else "",
                )
            )

        # Sort by createdAt DESC limited (most recent alerts surface first)
        alerts.sort(key=lambda a: a.createdAt, reverse=True)
        return alerts[:limit]

    async def get_activity(self, limit: int = 15) -> list[ActivityEvent]:
        """Recent activity feed · audit_log filtered por tablas relevantes."""
        session = self.session

        # Mapping tabla → activity type · keep simple cement
        TABLE_TYPE_MAP = {
            "evidence": "evidence_generated",
            "verification_runs": "scan_completed",
            "proposals": "proposal_sent",
            "signing_intents": "document_signed",
            "contracts": "document_signed",
            "signing_events": "document_signed",
            "agent_runs": "agent_run",
        }
        TABLE_DESCRIPTIONS = {
            "evidence": "Evidencia generada",
            "verification_runs": "Scan verificación completado",
            "proposals": "Propuesta comercial actualizada",
            "signing_intents": "Intent de firma actualizado",
            "contracts": "Contrato actualizado",
            "signing_events": "Evento de firma registrado",
            "agent_runs": "Agente ejecutado",
        }

        rows = await session.execute(
            sa_text(
                "SELECT id, tabla, registro_id, accion, timestamp "
                "FROM audit_log "
                "WHERE tabla IN ('evidence', 'verification_runs', 'proposals', "
                "                'signing_intents', 'contracts', 'signing_events', "
                "                'agent_runs') "
                "ORDER BY timestamp DESC "
                "LIMIT :lim"
            ),
            {"lim": limit},
        )

        events: list[ActivityEvent] = []
        for row in rows.fetchall():
            audit_id, tabla, registro_id, accion, ts = row
            event_type = TABLE_TYPE_MAP.get(tabla, "other")
            description = TABLE_DESCRIPTIONS.get(tabla, tabla)
            events.append(
                ActivityEvent(
                    id=str(audit_id),
                    timestamp=ts.isoformat() if ts else "",
                    type=event_type,
                    description=f"{description} ({accion})",
                    project_slug=None,
                    agent_id=None,
                )
            )

        return events
