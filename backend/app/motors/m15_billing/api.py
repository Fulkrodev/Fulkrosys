"""Motor 15 - Billing API."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db, set_tenant_context

from .billing_service import BillingError, BillingService, IVA_DEFAULT, IRPF_DEFAULT


router = APIRouter(prefix="/billing", tags=["Motor 15 - Billing"])


async def _set_project_rls(project_id: uuid.UUID, db: AsyncSession):
    client_id = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
    )).scalar()
    if not client_id:
        raise HTTPException(status_code=404, detail="Project not found")
    await set_tenant_context(db, client_id=client_id, project_id=project_id)


# ---------------- Schemas ----------------

class InvoiceLineBody(BaseModel):
    descripcion: str = Field(..., min_length=1, max_length=500)
    cantidad: float = Field(1.0, gt=0)
    precio_unitario: float
    hito_asociado: Optional[str] = Field(None, max_length=100)


class GenerateInvoiceBody(BaseModel):
    client_id: uuid.UUID
    contract_id: Optional[uuid.UUID] = None
    concepto: str = Field(..., min_length=2, max_length=500)
    lineas: list[InvoiceLineBody] = Field(..., min_length=1)
    tipo: str = Field("ordinaria", min_length=3, max_length=20)
    aplicar_irpf: bool = False
    iva_percent: float = Field(IVA_DEFAULT, ge=0, le=100)
    irpf_percent: float = Field(IRPF_DEFAULT, ge=0, le=100)
    hito_asociado: Optional[str] = None
    dias_vencimiento: int = Field(30, ge=1, le=365)


class GenerateFromMilestoneBody(BaseModel):
    contract_id: uuid.UUID
    hito: str = Field(..., min_length=1, max_length=100)


class GenerateReminderBody(BaseModel):
    dias_vencida: int = Field(..., ge=1, le=365)


# ---------------- Endpoints ----------------

@router.post(
    "/projects/{project_id}/invoices/generate",
    status_code=status.HTTP_201_CREATED,
)
async def generate_invoice(
    project_id: uuid.UUID,
    body: GenerateInvoiceBody,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        inv = await BillingService().generate_invoice(
            db,
            client_id=body.client_id,
            project_id=project_id,
            contract_id=body.contract_id,
            concepto=body.concepto,
            lineas=[ln.model_dump() for ln in body.lineas],
            tipo=body.tipo,
            aplicar_irpf=body.aplicar_irpf,
            iva_percent=body.iva_percent,
            irpf_percent=body.irpf_percent,
            hito_asociado=body.hito_asociado,
            dias_vencimiento=body.dias_vencimiento,
        )
    except BillingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize(inv)


@router.post(
    "/projects/{project_id}/invoices/from-milestone",
    status_code=status.HTTP_201_CREATED,
)
async def generate_from_milestone(
    project_id: uuid.UUID,
    body: GenerateFromMilestoneBody,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        inv = await BillingService().generate_from_milestone(
            db, contract_id=body.contract_id, hito=body.hito,
        )
    except BillingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize(inv)


@router.get("/projects/{project_id}/invoices")
async def list_invoices(
    project_id: uuid.UUID,
    estado: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    rows = await BillingService().list_invoices(db, project_id=project_id, estado=estado)
    return {"invoices": [_serialize(r) for r in rows]}


@router.get("/projects/{project_id}/invoices/{invoice_id}")
async def get_invoice(
    project_id: uuid.UUID,
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    svc = BillingService()
    inv = await svc.get_invoice(db, invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    lines = await svc.list_lines(db, invoice_id)
    return {
        **_serialize(inv),
        "lineas": [_serialize_line(ln) for ln in lines],
    }


@router.get("/projects/{project_id}/invoices/{invoice_id}/pdf")
async def download_pdf(
    project_id: uuid.UUID,
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        content = await BillingService().generate_invoice_pdf(db, invoice_id)
    except BillingError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="factura_{invoice_id}.docx"'
        },
    )


@router.post("/projects/{project_id}/invoices/{invoice_id}/mark-paid")
async def mark_paid(
    project_id: uuid.UUID,
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        inv = await BillingService().mark_paid(db, invoice_id)
    except BillingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize(inv)


@router.post("/projects/{project_id}/invoices/{invoice_id}/cancel")
async def cancel_invoice(
    project_id: uuid.UUID,
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        original, rectificativa = await BillingService().cancel_invoice(db, invoice_id)
    except BillingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return {
        "original": _serialize(original),
        "rectificativa": _serialize(rectificativa),
    }


@router.post(
    "/projects/{project_id}/invoices/{invoice_id}/reminders",
    status_code=status.HTTP_201_CREATED,
)
async def generate_reminder(
    project_id: uuid.UUID,
    invoice_id: uuid.UUID,
    body: GenerateReminderBody,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        rem = await BillingService().generate_reminder(
            db, invoice_id, body.dias_vencida,
        )
    except BillingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return {
        "id": str(rem.id),
        "invoice_id": str(rem.invoice_id),
        "dias_vencida": rem.dias_vencida,
        "template_usado": rem.template_usado,
        "canal": rem.canal,
        "contenido": rem.contenido,
        "enviado_at": rem.enviado_at.isoformat() if rem.enviado_at else None,
    }


@router.get("/projects/{project_id}/billing/summary")
async def billing_summary(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    return await BillingService().get_billing_summary(db, project_id=project_id)


# ---------------- Endpoint agregado por cliente (sub-fase 5.A FASE 5) ----------------

@router.get(
    "/clients/{client_id}/invoices",
    dependencies=[Depends(require_owner)],
)
async def list_invoices_by_client_endpoint(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Tab Facturas en panel /admin/clients/{id}.

    Endpoint agregado: evita N+1 que tendría el frontend si listase
    projects e iterase invoices por cada uno (decisión audit pre-FASE 5
    H4). Retorna lista plana enriquecida con ``project_name``.
    """
    # Agregado admin cross-proyecto del cliente (require_owner): invoices tiene
    # RLS por client_id; sin fijar contexto daría [] en prod bajo fulkro_app.
    from sqlalchemy import text as _t
    await db.execute(_t("SET LOCAL ROLE fulkro_app_bypassrls"))
    rows = await BillingService().list_invoices_by_client(db, client_id)
    return [
        {
            "invoice_id": str(invoice.id),
            "project_id": (
                str(invoice.project_id) if invoice.project_id else None
            ),
            "project_name": project_name,
            "numero_correlativo": invoice.numero_correlativo,
            "tipo": invoice.tipo,
            "total": (
                float(invoice.total) if invoice.total is not None else None
            ),
            "estado_pago": invoice.estado_pago,
            "fecha_emision": (
                invoice.fecha_emision.isoformat()
                if invoice.fecha_emision
                else None
            ),
            "fecha_vencimiento": (
                invoice.fecha_vencimiento.isoformat()
                if invoice.fecha_vencimiento
                else None
            ),
        }
        for invoice, project_name in rows
    ]


# ---------------- Helpers ----------------

def _serialize(inv):
    return {
        "id": str(inv.id),
        "client_id": str(inv.client_id),
        "project_id": str(inv.project_id) if inv.project_id else None,
        "contract_id": str(inv.contract_id) if inv.contract_id else None,
        "numero_correlativo": inv.numero_correlativo,
        "tipo": inv.tipo,
        "concepto": inv.concepto,
        "base_imponible": float(inv.base_imponible) if inv.base_imponible is not None else None,
        "iva_percent": inv.iva_percent,
        "iva_importe": float(inv.iva_importe) if inv.iva_importe is not None else None,
        "irpf_percent": inv.irpf_percent,
        "irpf_importe": float(inv.irpf_importe) if inv.irpf_importe is not None else None,
        "total": float(inv.total) if inv.total is not None else None,
        "fecha_emision": inv.fecha_emision.isoformat() if inv.fecha_emision else None,
        "fecha_vencimiento": inv.fecha_vencimiento.isoformat() if inv.fecha_vencimiento else None,
        "estado_pago": inv.estado_pago,
        "verifactu_hash": inv.verifactu_hash,
    }


def _serialize_line(ln):
    return {
        "id": str(ln.id),
        "descripcion": ln.descripcion,
        "cantidad": float(ln.cantidad),
        "precio_unitario": float(ln.precio_unitario),
        "subtotal": float(ln.subtotal),
        "hito_asociado": ln.hito_asociado,
        "paron_asociado": ln.paron_asociado,
        "orden": ln.orden,
    }
