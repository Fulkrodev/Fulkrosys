"""Motor adapters NotificationOrchestrator MB-16.6 (ADR-039).

Funciones de conveniencia per event type para que motors existentes
(m21 portal cliente · m07 evidence · m23 retainer · etc) deleguen
notificaciones cross-canal al orchestrator sin acoplarse a la API
verbose ``enqueue_with_template``.

Cada adapter:
- Resuelve template name + render context apropiado al event_type.
- Resuelve cta_url vía DeepLinkGenerator canónico.
- Enqueue via NotificationOrchestrator preservando preferences cliente
  + DND.
- Captura excepciones y loggea (NUNCA bloquear el flow del motor por
  fallo notificación · política conservadora MVP).

API uniforme:
    await notify_<event>(db, *args, **kwargs)

Retorna ``DispatchOutcome`` o ``None`` si fallo capturado.

Refactor motors: MB-16.6 integra m21 chat_service + task_service.
Resto motors (m07 evidence freshness · m12 magic-link onboarding ·
m18 communication · m23 retainer alerts · m25 lifecycle) re-asignados
MB-19+ DEC-MB16-MOTORS-REFACTOR-INCREMENTAL (deferrable cerrado en
ADR-039 sección Deferrables).
"""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.notifications.deep_links import DeepLinkGenerator, _coerce_id
from backend.app.notifications.orchestrator import (
    DispatchOutcome,
    NotificationOrchestrator,
)

logger = logging.getLogger(__name__)


def _safe_str(value: object) -> str:
    if value is None:
        return ""
    return str(value)


async def _safe_dispatch(
    *,
    orchestrator: NotificationOrchestrator,
    event_type: str,
    template_name: str,
    template_context: dict,
    recipient_email: str,
    recipient_user_id: UUID | None,
    project_id: UUID | None,
    payload: dict | None = None,
) -> Optional[DispatchOutcome]:
    """Wrapper que captura excepciones · NO bloquea flow motor."""
    try:
        return await orchestrator.enqueue_with_template(
            event_type=event_type,
            template_name=template_name,
            template_context=template_context,
            recipient_email=recipient_email,
            recipient_user_id=recipient_user_id,
            project_id=project_id,
            payload={
                **(payload or {}),
                "_render_context": template_context,
            },
        )
    except Exception:
        logger.exception(
            "notification adapter %s failed · event=%s recipient=%s",
            template_name, event_type, recipient_email,
        )
        return None


async def notify_chat_admin_reply(
    db: AsyncSession,
    *,
    recipient_user_id: UUID,
    recipient_email: str,
    recipient_name: str,
    project_id: UUID,
    project_name: str,
    thread_id: UUID,
    message_preview: str,
    orchestrator: NotificationOrchestrator | None = None,
    deep_links: DeepLinkGenerator | None = None,
) -> Optional[DispatchOutcome]:
    """Cliente recibe notificación de respuesta admin en chat.

    Disparado desde m21_portal_cliente.chat_service.post_message
    cuando ``sender_type == 'admin'``.
    """
    orchestrator = orchestrator or NotificationOrchestrator(db)
    deep_links = deep_links or DeepLinkGenerator()
    cta_url = deep_links.chat_thread(thread_id)
    return await _safe_dispatch(
        orchestrator=orchestrator,
        event_type="chat_admin_reply",
        template_name="chat_admin_reply",
        template_context={
            "recipient_name": recipient_name,
            "project_name": project_name,
            "message_preview": message_preview[:280],
            "cta_url": cta_url,
        },
        recipient_email=recipient_email,
        recipient_user_id=recipient_user_id,
        project_id=project_id,
        payload={
            "thread_id": str(thread_id),
        },
    )


async def notify_task_assigned(
    db: AsyncSession,
    *,
    recipient_user_id: UUID,
    recipient_email: str,
    recipient_name: str,
    project_id: UUID,
    project_name: str,
    task_id: UUID,
    task_title: str,
    task_description: str = "",
    task_due_date: str = "",
    orchestrator: NotificationOrchestrator | None = None,
    deep_links: DeepLinkGenerator | None = None,
) -> Optional[DispatchOutcome]:
    """Cliente recibe notificación de nueva tarea asignada.

    Disparado desde m21_portal_cliente.task_service.create_task /
    create_from_template cuando un client_user_id concreto recibe
    asignación.
    """
    orchestrator = orchestrator or NotificationOrchestrator(db)
    deep_links = deep_links or DeepLinkGenerator()
    cta_url = deep_links.task(task_id)
    return await _safe_dispatch(
        orchestrator=orchestrator,
        event_type="task_assigned",
        template_name="task_assigned",
        template_context={
            "recipient_name": recipient_name,
            "project_name": project_name,
            "task_title": task_title,
            "task_description": task_description,
            "task_due_date": task_due_date,
            "cta_url": cta_url,
        },
        recipient_email=recipient_email,
        recipient_user_id=recipient_user_id,
        project_id=project_id,
        payload={"task_id": str(task_id)},
    )


async def notify_evidence_expiring(
    db: AsyncSession,
    *,
    recipient_user_id: UUID,
    recipient_email: str,
    recipient_name: str,
    project_id: UUID,
    project_name: str,
    evidence_id: UUID,
    evidence_name: str,
    days_to_expire: int,
    expiration_date: str,
    orchestrator: NotificationOrchestrator | None = None,
    deep_links: DeepLinkGenerator | None = None,
) -> Optional[DispatchOutcome]:
    """Cliente recibe alerta de evidencia próxima a expirar.

    Para integración futura desde m07_evidence.tasks
    check_expiring_evidence (re-asignado MB-19+ por scope incremental).
    """
    orchestrator = orchestrator or NotificationOrchestrator(db)
    deep_links = deep_links or DeepLinkGenerator()
    cta_url = deep_links.evidence(evidence_id)
    return await _safe_dispatch(
        orchestrator=orchestrator,
        event_type="evidence_expiring",
        template_name="evidence_expiring",
        template_context={
            "recipient_name": recipient_name,
            "project_name": project_name,
            "evidence_name": evidence_name,
            "days_to_expire": days_to_expire,
            "expiration_date": expiration_date,
            "cta_url": cta_url,
        },
        recipient_email=recipient_email,
        recipient_user_id=recipient_user_id,
        project_id=project_id,
        payload={
            "evidence_id": str(evidence_id),
            "days_to_expire": days_to_expire,
        },
    )


async def notify_phase_changed(
    db: AsyncSession,
    *,
    recipient_user_id: UUID,
    recipient_email: str,
    recipient_name: str,
    project_id: UUID,
    project_name: str,
    new_phase: str,
    previous_phase: str = "",
    next_milestone: str = "",
    orchestrator: NotificationOrchestrator | None = None,
    deep_links: DeepLinkGenerator | None = None,
) -> Optional[DispatchOutcome]:
    """Cliente recibe notificación de cambio de fase workflow."""
    orchestrator = orchestrator or NotificationOrchestrator(db)
    deep_links = deep_links or DeepLinkGenerator()
    cta_url = deep_links.phase(new_phase)
    return await _safe_dispatch(
        orchestrator=orchestrator,
        event_type="phase_changed",
        template_name="phase_changed",
        template_context={
            "recipient_name": recipient_name,
            "project_name": project_name,
            "new_phase": new_phase,
            "previous_phase": previous_phase,
            "next_milestone": next_milestone,
            "cta_url": cta_url,
        },
        recipient_email=recipient_email,
        recipient_user_id=recipient_user_id,
        project_id=project_id,
        payload={"new_phase": new_phase},
    )


async def notify_audit_due(
    db: AsyncSession,
    *,
    recipient_user_id: UUID,
    recipient_email: str,
    recipient_name: str,
    project_id: UUID,
    project_name: str,
    audit_id: UUID,
    audit_type: str,
    audit_date: str,
    days_until: int,
    audit_scope: str,
    orchestrator: NotificationOrchestrator | None = None,
    deep_links: DeepLinkGenerator | None = None,
) -> Optional[DispatchOutcome]:
    """Cliente recibe alerta de auditoría programada próxima."""
    orchestrator = orchestrator or NotificationOrchestrator(db)
    deep_links = deep_links or DeepLinkGenerator()
    cta_url = deep_links.audit(audit_id)
    return await _safe_dispatch(
        orchestrator=orchestrator,
        event_type="audit_due",
        template_name="audit_due",
        template_context={
            "recipient_name": recipient_name,
            "project_name": project_name,
            "audit_type": audit_type,
            "audit_date": audit_date,
            "days_until": days_until,
            "audit_scope": audit_scope,
            "cta_url": cta_url,
        },
        recipient_email=recipient_email,
        recipient_user_id=recipient_user_id,
        project_id=project_id,
        payload={
            "audit_id": str(audit_id),
            "days_until": days_until,
        },
    )


async def notify_milestone_billed(
    db: AsyncSession,
    *,
    recipient_user_id: UUID,
    recipient_email: str,
    recipient_name: str,
    project_id: UUID,
    project_name: str,
    invoice_id: UUID,
    invoice_number: str,
    milestone_index: int,
    milestone_name: str,
    amount_eur,
    payment_due_date: str | None = None,
    orchestrator: NotificationOrchestrator | None = None,
    deep_links: DeepLinkGenerator | None = None,
) -> Optional[DispatchOutcome]:
    """Cliente recibe notificación de hito facturado + datos transferencia.

    Disparado desde ``AutoBillingService._bill_milestone`` tras éxito
    ``BillingService.generate_invoice``. Template ``milestone_billed``
    incluye instrucciones IBAN info-mode auto-append vía
    ``ManualTransferProvider`` (si configurado).

    MB-18.2 (ADR-040).
    """
    from backend.app.billing.manual_transfer import ManualTransferProvider

    orchestrator = orchestrator or NotificationOrchestrator(db)
    deep_links = deep_links or DeepLinkGenerator()
    transfer = ManualTransferProvider()
    bank_text = transfer.render_text_block(
        invoice_number=invoice_number,
        amount_eur=amount_eur,
        payment_due_date=payment_due_date,
    )
    bank_html = transfer.render_html_block(
        invoice_number=invoice_number,
        amount_eur=amount_eur,
        payment_due_date=payment_due_date,
    )

    cta_url = deep_links._build("/client-portal/billing")
    # Notificación in-portal realtime (fix 2026-06-07): el orchestrator emitía a
    # client_user:{id} (canal SIN suscriptores) → la bandeja/panel no refrescaban.
    # emit_client_notification dispatcha a project:{id} con client_notification.created
    # (escuchado por useClientProjectEvents · invalida client-inbox). Best-effort.
    try:
        from backend.app.motors.m21_portal_cliente.notification_service import (
            emit_client_notification,
        )
        await emit_client_notification(
            db, project_id=project_id, client_user_id=recipient_user_id,
            type="milestone_billed",
            title=f"Hito facturado: {milestone_name}",
            body=f"Factura {invoice_number} · {amount_eur:.2f} € · transferencia pendiente",
            target_url="/client-portal/billing", emitted_by_motor="m15_billing",
            payload={"invoice_id": str(invoice_id), "invoice_number": invoice_number},
        )
    except Exception:
        logger.exception("emit_client_notification milestone_billed failed (best-effort)")
    return await _safe_dispatch(
        orchestrator=orchestrator,
        event_type="milestone_billed",
        template_name="milestone_billed",
        template_context={
            "recipient_name": recipient_name,
            "project_name": project_name,
            "invoice_number": invoice_number,
            "milestone_number": milestone_index + 1,
            "milestone_name": milestone_name,
            "amount_eur": f"{amount_eur:.2f}",
            "bank_instructions_text": bank_text,
            "bank_instructions_html": bank_html,
            "payment_due_date": payment_due_date or "",
            "cta_url": cta_url,
        },
        recipient_email=recipient_email,
        recipient_user_id=recipient_user_id,
        project_id=project_id,
        payload={
            "invoice_id": str(invoice_id),
            "invoice_number": invoice_number,
            "milestone_index": milestone_index,
        },
    )


async def notify_payment_received(
    db: AsyncSession,
    *,
    recipient_user_id: UUID,
    recipient_email: str,
    recipient_name: str,
    project_id: UUID,
    project_name: str,
    milestone_name: str,
    amount_eur,
    orchestrator: NotificationOrchestrator | None = None,
    deep_links: DeepLinkGenerator | None = None,
) -> Optional[DispatchOutcome]:
    """Cliente recibe confirmación pago recibido + workflow advance.

    Disparado desde ``AutoBillingService.mark_milestone_paid`` tras
    Marcos confirmar transferencia recibida en extracto banco.

    MB-18.2 (ADR-040).
    """
    orchestrator = orchestrator or NotificationOrchestrator(db)
    deep_links = deep_links or DeepLinkGenerator()
    cta_url = deep_links.dashboard()
    # Notificación in-portal realtime (fix 2026-06-07 · canal project:{id} vivo)
    try:
        from backend.app.motors.m21_portal_cliente.notification_service import (
            emit_client_notification,
        )
        await emit_client_notification(
            db, project_id=project_id, client_user_id=recipient_user_id,
            type="payment_received",
            title=f"Pago recibido: {milestone_name}",
            body=f"Hemos registrado tu pago de {amount_eur:.2f} €. ¡Gracias!",
            target_url="/client-portal/billing", emitted_by_motor="m15_billing",
        )
    except Exception:
        logger.exception("emit_client_notification payment_received failed (best-effort)")
    return await _safe_dispatch(
        orchestrator=orchestrator,
        event_type="payment_received",
        template_name="payment_received",
        template_context={
            "recipient_name": recipient_name,
            "project_name": project_name,
            "milestone_name": milestone_name,
            "amount_eur": f"{amount_eur:.2f}",
            "cta_url": cta_url,
        },
        recipient_email=recipient_email,
        recipient_user_id=recipient_user_id,
        project_id=project_id,
        payload={
            "milestone_name": milestone_name,
            "amount_eur": f"{amount_eur:.2f}",
        },
    )


# ════════════════════════════════════════════════════════════════════
# MB-6 atom 8 · Cross-motor signoff + workflow events
# ════════════════════════════════════════════════════════════════════


async def notify_signoff_completed(
    db: AsyncSession,
    *,
    recipient_user_id: UUID,
    recipient_email: str,
    recipient_name: str,
    project_id: UUID,
    project_name: str,
    signable_type: str,
    signable_label: str,
    signable_codigo: str,
    signed_at_short: str,
    chain_position: str = "trazabilidad continua",
    orchestrator: NotificationOrchestrator | None = None,
    deep_links: DeepLinkGenerator | None = None,
) -> Optional[DispatchOutcome]:
    """Cliente firma genérica completada · MB-6 atom 8.

    Disparado desde process_*_signoff helpers cross-motor (M02 magerit ·
    M03 dda · M06 policies · M27 conformidad/dpc · M_meetings actas).
    Template signoff_completed.yaml variant por signable_type via context.
    """
    orchestrator = orchestrator or NotificationOrchestrator(db)
    deep_links = deep_links or DeepLinkGenerator()
    cta_url = deep_links._build("/client-portal/firmas-hub")
    return await _safe_dispatch(
        orchestrator=orchestrator,
        event_type=f"signoff_{signable_type}",
        template_name="signoff_completed",
        template_context={
            "recipient_name": recipient_name,
            "project_name": project_name,
            "signable_type": signable_type,
            "signable_label": signable_label,
            "signable_codigo": signable_codigo,
            "signed_at_short": signed_at_short,
            "chain_position": chain_position,
            "cta_url": cta_url,
        },
        recipient_email=recipient_email,
        recipient_user_id=recipient_user_id,
        project_id=project_id,
        payload={
            "signable_type": signable_type,
            "signable_codigo": signable_codigo,
        },
    )


async def notify_incident_resolved_cliente(
    db: AsyncSession,
    *,
    recipient_user_id: UUID,
    recipient_email: str,
    recipient_name: str,
    project_id: UUID,
    project_name: str,
    incident_id: UUID,
    incident_codigo: str,
    incident_titulo: str,
    signed_at_short: str,
    orchestrator: NotificationOrchestrator | None = None,
    deep_links: DeepLinkGenerator | None = None,
) -> Optional[DispatchOutcome]:
    """Cliente firma cierre incidente · MB-6 atom 8 · CCN-STIC 817."""
    orchestrator = orchestrator or NotificationOrchestrator(db)
    deep_links = deep_links or DeepLinkGenerator()
    cta_url = deep_links._build(f"/client-portal/incidents/{_coerce_id(incident_id)}")
    return await _safe_dispatch(
        orchestrator=orchestrator,
        event_type="incident_resolved_cliente",
        template_name="incident_resolved_cliente",
        template_context={
            "recipient_name": recipient_name,
            "project_name": project_name,
            "incident_codigo": incident_codigo,
            "incident_titulo": incident_titulo,
            "signed_at_short": signed_at_short,
            "cta_url": cta_url,
        },
        recipient_email=recipient_email,
        recipient_user_id=recipient_user_id,
        project_id=project_id,
        payload={"incident_id": str(incident_id)},
    )


async def notify_evidence_quarantined_admin(
    db: AsyncSession,
    *,
    admin_email: str,
    project_id: UUID,
    project_name: str,
    evidence_id: UUID,
    filename: str,
    virus_name: str,
    scanned_at_short: str,
    orchestrator: NotificationOrchestrator | None = None,
    deep_links: DeepLinkGenerator | None = None,
) -> Optional[DispatchOutcome]:
    """Admin Marcos notificado de archivo en cuarentena · MB-6 atom 8 · atom 6 integration."""
    orchestrator = orchestrator or NotificationOrchestrator(db)
    deep_links = deep_links or DeepLinkGenerator()
    cta_url = deep_links._build("/admin/evidence/quarantined")
    return await _safe_dispatch(
        orchestrator=orchestrator,
        event_type="evidence_quarantined_admin",
        template_name="evidence_quarantined_admin",
        template_context={
            "project_name": project_name,
            "filename": filename,
            "virus_name": virus_name,
            "scanned_at_short": scanned_at_short,
            "cta_url": cta_url,
        },
        recipient_email=admin_email,
        recipient_user_id=None,
        project_id=project_id,
        payload={
            "evidence_id": str(evidence_id),
            "virus_name": virus_name,
        },
    )


async def notify_retainer_quarterly_signed(
    db: AsyncSession,
    *,
    recipient_user_id: UUID,
    recipient_email: str,
    recipient_name: str,
    project_id: UUID,
    project_name: str,
    report_id: UUID,
    period_quarter: str,
    rag_overall: str,
    activities_completed: int,
    incidents_detected: int,
    vulns_critical: int,
    signed_at_short: str,
    orchestrator: NotificationOrchestrator | None = None,
    deep_links: DeepLinkGenerator | None = None,
) -> Optional[DispatchOutcome]:
    """Cliente firma comité retainer trimestral · MB-6 atom 8 · atom 4 integration."""
    orchestrator = orchestrator or NotificationOrchestrator(db)
    deep_links = deep_links or DeepLinkGenerator()
    cta_url = deep_links._build("/client-portal/retainer-checkin")
    return await _safe_dispatch(
        orchestrator=orchestrator,
        event_type="retainer_quarterly_signed",
        template_name="retainer_quarterly_signed",
        template_context={
            "recipient_name": recipient_name,
            "project_name": project_name,
            "period_quarter": period_quarter,
            "rag_overall": rag_overall,
            "activities_completed": activities_completed,
            "incidents_detected": incidents_detected,
            "vulns_critical": vulns_critical,
            "signed_at_short": signed_at_short,
            "cta_url": cta_url,
        },
        recipient_email=recipient_email,
        recipient_user_id=recipient_user_id,
        project_id=project_id,
        payload={
            "report_id": str(report_id),
            "period_quarter": period_quarter,
        },
    )


async def notify_acta_signed(
    db: AsyncSession,
    *,
    recipient_user_id: UUID,
    recipient_email: str,
    recipient_name: str,
    project_id: UUID,
    project_name: str,
    meeting_id: UUID,
    acta_codigo: str,
    acta_titulo: str,
    acta_subtype: str,
    acta_subtype_label: str,
    signed_at_short: str,
    orchestrator: NotificationOrchestrator | None = None,
    deep_links: DeepLinkGenerator | None = None,
) -> Optional[DispatchOutcome]:
    """Cliente firma acta · MB-6 atom 8 · atom 5 integration."""
    orchestrator = orchestrator or NotificationOrchestrator(db)
    deep_links = deep_links or DeepLinkGenerator()
    cta_url = deep_links._build("/client-portal/actas")
    return await _safe_dispatch(
        orchestrator=orchestrator,
        event_type="acta_signed",
        template_name="acta_signed",
        template_context={
            "recipient_name": recipient_name,
            "project_name": project_name,
            "acta_codigo": acta_codigo,
            "acta_titulo": acta_titulo,
            "acta_subtype": acta_subtype,
            "acta_subtype_label": acta_subtype_label,
            "signed_at_short": signed_at_short,
            "cta_url": cta_url,
        },
        recipient_email=recipient_email,
        recipient_user_id=recipient_user_id,
        project_id=project_id,
        payload={
            "meeting_id": str(meeting_id),
            "acta_subtype": acta_subtype,
        },
    )


__all__ = [
    "notify_chat_admin_reply",
    "notify_task_assigned",
    "notify_evidence_expiring",
    "notify_phase_changed",
    "notify_audit_due",
    "notify_milestone_billed",
    "notify_payment_received",
    # MB-6 atom 8 · cross-motor signoff/workflow events
    "notify_signoff_completed",
    "notify_incident_resolved_cliente",
    "notify_evidence_quarantined_admin",
    "notify_retainer_quarterly_signed",
    "notify_acta_signed",
]
