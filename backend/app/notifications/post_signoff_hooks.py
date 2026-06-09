"""Post-signoff hooks · SAN-E v3.MB-6 atom 8.

Helper functions cross-motor para emit notification events + M30 log_interaction
post-firma cliente. Reuse motor_adapters.py existing + ClientContactService
log_interaction pattern (MinutesService.create line 178-197 reference).

Pattern atomic:
- Each motor calls `await post_signoff_<motor>(db, ...)` después de su
  `process_*_signoff` business logic.
- Internal try/except silent-fail · NUNCA bloquea signoff.
- Resolve recipient + project metadata best-effort.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def _resolve_project_metadata(
    db: AsyncSession, project_id: uuid.UUID,
) -> dict | None:
    """Resolve project_name + client_id + primary cliente user · best-effort."""
    try:
        row = await db.execute(
            text(
                "SELECT p.nombre AS project_name, p.client_id, "
                "cu.id AS user_id, cu.email AS user_email, "
                "cu.full_name AS user_name "
                "FROM projects p "
                "LEFT JOIN client_users cu ON cu.client_id = p.client_id "
                "AND cu.deleted_at IS NULL "
                "WHERE p.id = :pid AND p.deleted_at IS NULL "
                "ORDER BY cu.created_at ASC LIMIT 1"
            ),
            {"pid": str(project_id)},
        )
        hit = row.mappings().first()
        if hit is None:
            return None
        return dict(hit)
    except Exception:
        logger.debug("post-signoff: project metadata lookup failed", exc_info=True)
        return None


async def _resolve_primary_contact_id(
    db: AsyncSession, client_id: uuid.UUID,
) -> uuid.UUID | None:
    """Resolve primary client_contact_id · used for M30 log_interaction."""
    try:
        row = await db.execute(
            text(
                "SELECT id FROM client_contacts "
                "WHERE client_id = :cid AND deleted_at IS NULL "
                "ORDER BY created_at ASC LIMIT 1"
            ),
            {"cid": str(client_id)},
        )
        hit = row.first()
        return hit[0] if hit else None
    except Exception:
        return None


def _fmt_short(dt: datetime | None) -> str:
    if dt is None:
        return ""
    try:
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(dt)


async def _log_m30_interaction(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    client_id: uuid.UUID,
    interaction_type: str,
    source_motor: str,
    source_id: uuid.UUID,
    summary: str,
    details: dict | None = None,
) -> None:
    """M30 log_interaction silent-fail wrapper."""
    contact_id = await _resolve_primary_contact_id(db, client_id)
    if contact_id is None:
        return
    try:
        from backend.app.motors.m30_client_contacts.service import (
            ClientContactService,
        )
        await ClientContactService(db).log_interaction(
            contact_id=contact_id,
            interaction_type=interaction_type,
            source_motor=source_motor,
            source_id=source_id,
            summary=summary,
            details=details or {},
        )
    except Exception:
        logger.debug(
            "post-signoff: M30 log_interaction failed motor=%s source=%s",
            source_motor, source_id, exc_info=True,
        )


# ════════════════════════════════════════════════════════════════════
# Cross-motor post-signoff entry points
# ════════════════════════════════════════════════════════════════════


async def post_signoff_acta(
    db: AsyncSession,
    *,
    meeting,
) -> None:
    """Atom 5 actas · post-firma cliente · M30 log + Orchestrator email.

    Args:
        meeting: CommitteeMeeting persisted post-firma (estado='fully_signed').
    """
    project_meta = await _resolve_project_metadata(db, meeting.project_id)
    if project_meta is None:
        return
    signed_at_short = _fmt_short(meeting.fully_signed_at)
    subtype_label = getattr(meeting, "acta_subtype_label", "") or "Acta"

    await _log_m30_interaction(
        db,
        project_id=meeting.project_id,
        client_id=project_meta["client_id"],
        interaction_type=f"signoff_acta_{meeting.acta_subtype or 'other'}",
        source_motor="m_meetings",
        source_id=meeting.id,
        summary=f"{subtype_label} firmada · {meeting.codigo or meeting.id}",
        details={
            "acta_subtype": meeting.acta_subtype,
            "codigo": meeting.codigo,
            "titulo": meeting.titulo,
            "signed_at": meeting.fully_signed_at.isoformat() if meeting.fully_signed_at else None,
        },
    )

    if project_meta.get("user_email"):
        try:
            from backend.app.notifications.motor_adapters import notify_acta_signed
            await notify_acta_signed(
                db,
                recipient_user_id=project_meta["user_id"],
                recipient_email=project_meta["user_email"],
                recipient_name=project_meta.get("user_name") or "",
                project_id=meeting.project_id,
                project_name=project_meta.get("project_name") or "",
                meeting_id=meeting.id,
                acta_codigo=meeting.codigo or "",
                acta_titulo=meeting.titulo or "",
                acta_subtype=meeting.acta_subtype or "other",
                acta_subtype_label=subtype_label,
                signed_at_short=signed_at_short,
            )
        except Exception:
            logger.debug("post-signoff acta orchestrator failed", exc_info=True)


async def post_signoff_retainer_quarterly(
    db: AsyncSession,
    *,
    report,
) -> None:
    """Atom 4 retainer · post-firma cliente · M30 log + Orchestrator email."""
    project_meta = await _resolve_project_metadata(db, report.project_id)
    if project_meta is None:
        return
    signed_at_short = _fmt_short(datetime.now(report.created_at.tzinfo) if report.created_at else None)

    await _log_m30_interaction(
        db,
        project_id=report.project_id,
        client_id=project_meta["client_id"],
        interaction_type="signoff_retainer_quarterly",
        source_motor="m23_retainer",
        source_id=report.id,
        summary=f"Comité Retainer {report.period_quarter} firmado",
        details={
            "period_quarter": report.period_quarter,
            "rag_overall": report.rag_overall,
            "activities_completed": report.activities_completed,
            "incidents_detected": report.incidents_detected,
            "vulns_critical": report.vulns_critical,
        },
    )

    if project_meta.get("user_email"):
        try:
            from backend.app.notifications.motor_adapters import (
                notify_retainer_quarterly_signed,
            )
            await notify_retainer_quarterly_signed(
                db,
                recipient_user_id=project_meta["user_id"],
                recipient_email=project_meta["user_email"],
                recipient_name=project_meta.get("user_name") or "",
                project_id=report.project_id,
                project_name=project_meta.get("project_name") or "",
                report_id=report.id,
                period_quarter=report.period_quarter or "",
                rag_overall=report.rag_overall or "—",
                activities_completed=report.activities_completed or 0,
                incidents_detected=report.incidents_detected or 0,
                vulns_critical=report.vulns_critical or 0,
                signed_at_short=signed_at_short,
            )
        except Exception:
            logger.debug("post-signoff retainer orchestrator failed", exc_info=True)


async def post_signoff_incident(
    db: AsyncSession,
    *,
    incident,
) -> None:
    """Atom 3 incident · post-firma cliente cierre · M30 log + Orchestrator email."""
    project_meta = await _resolve_project_metadata(db, incident.project_id)
    if project_meta is None:
        return
    signed_at_short = _fmt_short(
        getattr(incident, "client_reviewed_at", None) or
        getattr(incident, "updated_at", None)
    )

    await _log_m30_interaction(
        db,
        project_id=incident.project_id,
        client_id=project_meta["client_id"],
        interaction_type="signoff_incident_close",
        source_motor="m19_risk",
        source_id=incident.id,
        summary=f"Incidente {getattr(incident, 'codigo', incident.id)} firmado cerrado",
        details={
            "codigo": getattr(incident, "codigo", None),
            "titulo": getattr(incident, "titulo", None),
            "workflow_state": getattr(incident, "workflow_state", None),
        },
    )

    if project_meta.get("user_email"):
        try:
            from backend.app.notifications.motor_adapters import (
                notify_incident_resolved_cliente,
            )
            await notify_incident_resolved_cliente(
                db,
                recipient_user_id=project_meta["user_id"],
                recipient_email=project_meta["user_email"],
                recipient_name=project_meta.get("user_name") or "",
                project_id=incident.project_id,
                project_name=project_meta.get("project_name") or "",
                incident_id=incident.id,
                incident_codigo=getattr(incident, "codigo", "") or "",
                incident_titulo=getattr(incident, "titulo", "") or "",
                signed_at_short=signed_at_short,
            )
        except Exception:
            logger.debug("post-signoff incident orchestrator failed", exc_info=True)


async def post_event_evidence_quarantined(
    db: AsyncSession,
    *,
    evidence_id: uuid.UUID,
    project_id: uuid.UUID,
    filename: str,
    virus_name: str | None,
    scanned_at: datetime | None,
    admin_email: str | None = None,
) -> None:
    """Atom 6 quarantine · admin notify · M30 NO log (admin event NOT cliente interaction).

    NotificationOrchestrator email a admin Marcos para revisión cuarentena.
    Si admin_email None, intenta resolver via env FULKRO_ADMIN_EMAIL.
    """
    if admin_email is None:
        import os
        admin_email = os.environ.get("FULKRO_ADMIN_EMAIL")
    if not admin_email:
        return
    project_meta = await _resolve_project_metadata(db, project_id)
    project_name = (project_meta or {}).get("project_name") or "—"
    scanned_at_short = _fmt_short(scanned_at)

    try:
        from backend.app.notifications.motor_adapters import (
            notify_evidence_quarantined_admin,
        )
        await notify_evidence_quarantined_admin(
            db,
            admin_email=admin_email,
            project_id=project_id,
            project_name=project_name,
            evidence_id=evidence_id,
            filename=filename,
            virus_name=virus_name or "unknown",
            scanned_at_short=scanned_at_short,
        )
    except Exception:
        logger.debug("post-event quarantine orchestrator failed", exc_info=True)


async def post_signoff_generic(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    signable_type: str,
    signable_label: str,
    signable_codigo: str,
    signable_source_id: uuid.UUID,
    source_motor: str,
    signed_at: datetime | None = None,
) -> None:
    """Generic post-signoff hook · M30 log + notify_signoff_completed.

    For motors sin dedicated adapter (m02 magerit_validation · m03 dda ·
    m06 policies · m27 conformidad/dpc). Adapter signoff_completed maneja
    template variant via context.
    """
    project_meta = await _resolve_project_metadata(db, project_id)
    if project_meta is None:
        return
    signed_at_short = _fmt_short(signed_at or datetime.now())

    await _log_m30_interaction(
        db,
        project_id=project_id,
        client_id=project_meta["client_id"],
        interaction_type=f"signoff_{signable_type}",
        source_motor=source_motor,
        source_id=signable_source_id,
        summary=f"{signable_label} firmada · {signable_codigo}",
        details={
            "signable_type": signable_type,
            "codigo": signable_codigo,
        },
    )

    if project_meta.get("user_email"):
        try:
            from backend.app.notifications.motor_adapters import (
                notify_signoff_completed,
            )
            await notify_signoff_completed(
                db,
                recipient_user_id=project_meta["user_id"],
                recipient_email=project_meta["user_email"],
                recipient_name=project_meta.get("user_name") or "",
                project_id=project_id,
                project_name=project_meta.get("project_name") or "",
                signable_type=signable_type,
                signable_label=signable_label,
                signable_codigo=signable_codigo,
                signed_at_short=signed_at_short,
            )
        except Exception:
            logger.debug("post-signoff generic orchestrator failed", exc_info=True)
