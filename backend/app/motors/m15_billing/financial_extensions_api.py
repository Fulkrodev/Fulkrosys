"""M15 Financial Extensions · ADR-046 v3 SAN-E.MB-3.F.

Gap-fill endpoints sobre M15 billing existing (15+ endpoints already · NO
recreate · NO duplicate AAPP chain modules face_submitter / facturae_generator
/ xades_signer · NO duplicate billing/summary).

3 endpoints NEW alineados con frontend MB-3.2 FinancialPanel:
    GET  /api/v1/projects/{id}/financial-summary (alias enriquecido sobre billing/summary)
    GET  /api/v1/projects/{id}/aapp-billing/status (3-stage chain status)
    POST /api/v1/projects/{id}/invoices/{invoice_id}/send (Postmark + portal · stub)
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import CurrentUser, require_owner
from backend.app.database import get_db, set_tenant_context
from backend.app.models.commercial import Invoice


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/projects/{project_id}",
    tags=["Motor 15 - Financial Extensions"],
    dependencies=[Depends(require_owner)],
)


async def _set_project_rls(project_id: uuid.UUID, db: AsyncSession) -> None:
    client_id = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
    )).scalar()
    if not client_id:
        raise HTTPException(status_code=404, detail="Project not found")
    await set_tenant_context(db, client_id=client_id, project_id=project_id)


@router.get("/financial-summary")
async def get_financial_summary(
    project_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Snapshot financiero consolidado · alias enriquecido sobre billing/summary.

    Retorna: contract_value · invoiced · paid · outstanding ·
    next_milestone · invoices · payments_summary.
    """
    await _set_project_rls(project_id, db)

    # Aggregate desde tabla invoices existing
    invoices = (await db.execute(
        select(Invoice).where(
            Invoice.project_id == project_id,
            Invoice.deleted_at.is_(None),
        )
    )).scalars().all()
    # Invoice fields: total · estado_pago (pendiente/vencida/pagada/anulada)
    total_invoiced = sum(
        (Decimal(str(i.total or 0)) for i in invoices if i.estado_pago != "anulada"),
        Decimal("0"),
    )
    total_paid = sum(
        (Decimal(str(i.total or 0)) for i in invoices if i.estado_pago == "pagada"),
        Decimal("0"),
    )
    total_outstanding = total_invoiced - total_paid
    next_milestone_q = await db.execute(
        text(
            "SELECT amount_eur, milestone_name, milestone_index, billing_trigger "
            "FROM contract_milestones "
            "WHERE project_id = :pid AND status = 'pending' "
            "ORDER BY milestone_index ASC LIMIT 1"
        ),
        {"pid": str(project_id)},
    )
    nm = next_milestone_q.fetchone()
    next_milestone = (
        {
            "amount_eur": float(nm[0]) if nm[0] else None,
            "label": nm[1],
            "milestone_index": nm[2],
            "billing_trigger": nm[3],
        }
        if nm else None
    )

    # #45 E0 · fase REAL del proyecto (ordinal canónico 0-based) = base correcta
    # del timeline. NO confundir con milestone_index (secuencial del hito · otra
    # cosa); el bug era pintar la fase usando milestone_index.
    from backend.app.core.workflow_phase import WorkflowPhase
    fase_val = (await db.execute(
        text("SELECT fase FROM projects WHERE id = :pid"), {"pid": str(project_id)}
    )).scalar()
    current_phase_index: int | None = None
    if fase_val:
        try:
            current_phase_index = WorkflowPhase.ordered().index(WorkflowPhase(fase_val))
        except (ValueError, KeyError):
            current_phase_index = None

    return {
        "project_id": str(project_id),
        "totals": {
            "invoiced": float(total_invoiced),
            "paid": float(total_paid),
            "outstanding": float(total_outstanding),
        },
        "next_milestone": next_milestone,
        "current_phase_index": current_phase_index,
        "invoices_count": len(invoices),
        "invoices_paid_count": sum(1 for i in invoices if i.estado_pago == "pagada"),
        "invoices_pending_count": sum(
            1 for i in invoices if i.estado_pago in ("pendiente", "vencida")
        ),
        "invoices_overdue_count": sum(1 for i in invoices if i.estado_pago == "vencida"),
    }


@router.get("/aapp-billing/status")
async def get_aapp_billing_status(
    project_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """3-stage chain status: Facturae XAdES → FACE → Verifactu.

    Si proyecto NO tiene factura AAPP activa devuelve placeholder
    sin error. Modulos AAPP (facturae_generator / xades_signer /
    face_submitter / late_interest_calculator) ya implementados M15.
    """
    await _set_project_rls(project_id, db)
    # Query soft sin asumir tabla invoices_aapp existe (mb11_invaapp puede
    # no estar en chain alembic actual)
    try:
        rows = (await db.execute(
            text(
                # Nombres reales de columna (antes total_amount/face_submitted_at
                # NO existían → SELECT fallaba → except tragaba el error → SIEMPRE
                # 'sin factura AAPP'). Posiciones rows[2]/rows[5] se conservan.
                "SELECT id, invoice_number, amount_eur, status, "
                "facturae_xml_signed, submitted_to_face_at "
                "FROM invoices_aapp WHERE project_id = :pid "
                "ORDER BY created_at DESC LIMIT 1"
            ),
            {"pid": str(project_id)},
        )).fetchone()
    except Exception:
        rows = None

    if rows is None:
        return {
            "project_id": str(project_id),
            "has_active_aapp_invoice": False,
            "stage_facturae_xades": "n/a",
            "stage_face": "n/a",
            "stage_verifactu": "n/a",
            "next_action": "Generar factura AAPP via /invoices/aapp endpoint",
        }
    return {
        "project_id": str(project_id),
        "has_active_aapp_invoice": True,
        "invoice_id": str(rows[0]),
        "invoice_number": rows[1],
        "total_amount": float(rows[2]) if rows[2] else None,
        "stage_facturae_xades": "ok" if rows[4] else "pending",
        "stage_face": "ok" if rows[5] else "pending",
        "stage_verifactu": "pending",  # Verifactu hash chain se cabla MB-7
        "current_status": rows[3],
    }


@router.post("/invoices/{invoice_id}/send")
async def send_invoice(
    project_id: uuid.UUID,
    invoice_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Envía la factura al cliente: notificación en el portal (inbox + SSE) +
    email best-effort + timestamp dedicado (FIX P1-7).

    Antes era un STUB: marcaba ``verifactu_enviado_at`` (semántica de la cadena
    VeriFactu MB-7, NO de email) y NO enviaba nada → la UI ("Reenviar al cliente")
    confirmaba el envío al admin mientras al cliente no le llegaba nada. Ahora
    crea una ClientNotification ``invoice_review`` (inbox + SSE realtime), envía
    un email best-effort con enlace al portal, y registra el timestamp en el
    campo DEDICADO ``email_enviado_at``.
    """
    await _set_project_rls(project_id, db)
    invoice = (await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.project_id == project_id,
            Invoice.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.estado_pago == "anulada":
        raise HTTPException(
            status_code=409,
            detail="Invoice anulada · no se puede enviar",
        )

    # Contacto del cliente (ClientUser primario del proyecto).
    cu_row = (await db.execute(text(
        "SELECT id, email, full_name FROM client_users "
        "WHERE client_id = :cid AND deleted_at IS NULL "
        "ORDER BY created_at ASC LIMIT 1"
    ), {"cid": str(invoice.client_id)})).first()

    titulo = f"Nueva factura {invoice.numero_correlativo or ''}".strip()
    cuerpo = (
        f"Tienes una factura disponible por {float(invoice.total or 0):.2f} € "
        f"(vencimiento {invoice.fecha_vencimiento})."
    )
    target_url = f"/client-portal/facturas/{invoice_id}"
    notified_portal = False
    emailed = False

    if cu_row is not None:
        client_user_id, email, nombre = cu_row[0], cu_row[1], cu_row[2]
        # 1. Notificación en el portal (inbox + SSE realtime · best-effort).
        try:
            from backend.app.motors.m21_portal_cliente.notification_service import (
                emit_client_notification,
            )
            await emit_client_notification(
                db,
                project_id=project_id,
                client_user_id=client_user_id,
                type="invoice_review",
                title=titulo,
                body=cuerpo,
                target_url=target_url,
                emitted_by_motor="m15_billing",
                priority="normal",
                payload={
                    "invoice_id": str(invoice_id),
                    "numero": invoice.numero_correlativo,
                    "total": float(invoice.total or 0),
                },
            )
            notified_portal = True
        except Exception:
            logger.exception("send_invoice: emit_client_notification falló")
        # 2. Email best-effort (notifica + enlace al portal · sin adjuntar PDF).
        if email:
            try:
                from backend.app.core.email.sender import get_email_sender
                saludo = f" {nombre}" if nombre else ""
                html = (
                    f"<p>Hola{saludo},</p><p>{cuerpo}</p>"
                    f"<p>Puedes consultarla y descargarla desde tu portal.</p>"
                )
                res = await get_email_sender().send(
                    db,
                    to=email,
                    subject=titulo,
                    html_body=html,
                    template_used="invoice_send",
                    client_id=invoice.client_id,
                    metadata={"invoice_id": str(invoice_id)},
                )
                emailed = bool(getattr(res, "ok", False))
            except Exception:
                logger.exception("send_invoice: envío de email falló")

    # 3. Timestamp DEDICADO (NO reutiliza verifactu_enviado_at).
    invoice.email_enviado_at = datetime.now(timezone.utc)
    await db.commit()
    return {
        "invoice_id": str(invoice_id),
        "estado_pago": invoice.estado_pago,
        "sent_at": invoice.email_enviado_at.isoformat(),
        "notified_portal": notified_portal,
        "emailed": emailed,
    }
