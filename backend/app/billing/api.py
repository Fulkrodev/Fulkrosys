"""API endpoints AutoBilling + reconciliation manual (MB-18.3 ADR-040).

Routers:

- ``admin_finance_router`` (Marcos · ``require_owner``):
  - GET  ``/api/v1/admin/finance/kpis``
  - GET  ``/api/v1/admin/finance/pending-payments``
  - POST ``/api/v1/admin/finance/milestones/{id}/mark-paid``
  - POST ``/api/v1/admin/contracts/{id}/milestones/regenerate``

- ``client_billing_router`` (cliente · ``require_client_user``):
  - GET ``/api/v1/portal/billing/invoices``
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import desc, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import (
    require_client_user,
    require_owner,
)
from backend.app.billing.auto_billing import (
    AutoBillingError,
    AutoBillingService,
)
from backend.app.billing.manual_transfer import ManualTransferProvider
from backend.app.billing.implementation_payments import (
    build_implementation_payments,
)
from backend.app.billing.milestone_factory import (
    MilestoneFactory,
    MilestoneFactoryError,
)
from backend.app.database import get_db
from backend.app.models.auth import User
from backend.app.models.billing_milestones import ContractMilestone
from backend.app.models.client_portal import ClientUser
from backend.app.models.commercial import Contract, Invoice

logger = logging.getLogger(__name__)


admin_finance_router = APIRouter(
    prefix="/admin/finance",
    tags=["Admin - Finance (MB-18)"],
)

admin_contracts_router = APIRouter(
    prefix="/admin/contracts",
    tags=["Admin - Contracts (MB-18)"],
)

client_billing_router = APIRouter(
    prefix="/portal/billing",
    tags=["Portal Cliente - Billing (MB-18)"],
)


# ──────────────── Schemas ────────────────


class PendingPaymentRow(BaseModel):
    milestone_id: uuid.UUID
    milestone_name: str
    milestone_index: int
    project_id: uuid.UUID
    project_name: str
    invoice_id: uuid.UUID | None
    invoice_number: str | None
    amount_eur: str
    billed_at: datetime | None
    days_pending: int


class FinanceKpisResponse(BaseModel):
    billed_this_month_eur: str
    paid_this_month_eur: str
    pending_total_eur: str
    overdue_count: int


class MarkPaidRequest(BaseModel):
    payment_reference: str | None = None
    payment_notes: str | None = None
    paid_at: str | None = None  # ISO datetime opcional


class MarkPaidResponse(BaseModel):
    milestone_id: uuid.UUID
    status: str
    paid_at: datetime | None
    payment_reference: str | None
    workflow_advanced_to_phase: int | None


class RegenerateMilestonesResponse(BaseModel):
    contract_id: uuid.UUID
    created: int
    skipped: int


class ClientInvoiceRow(BaseModel):
    invoice_id: uuid.UUID
    invoice_number: str | None
    concepto: str | None
    base_imponible: str | None
    iva_importe: str | None
    total: str | None
    fecha_emision: str | None
    fecha_vencimiento: str | None
    estado_pago: str | None
    bank_instructions_html: str
    bank_instructions_text: str


# ──────────────── Helpers ────────────────


async def _set_admin_rls_context(db: AsyncSession) -> None:
    await db.execute(
        text(
            "SELECT set_config('app.current_role_pool', 'marcos', true)"
        )
    )
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))


async def _set_client_rls_context(
    db: AsyncSession, user: ClientUser,
) -> None:
    await db.execute(
        text(
            "SELECT set_config('app.current_client_id', :cid, true)"
        ),
        {"cid": str(user.client_id)},
    )


# ──────────────── Admin · finance endpoints ────────────────


@admin_finance_router.get("/kpis", response_model=FinanceKpisResponse)
async def get_finance_kpis(
    db: Annotated[AsyncSession, Depends(get_db)],
    _owner: Annotated[User, Depends(require_owner)],
):
    await _set_admin_rls_context(db)
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    billed_row = (await db.execute(
        text(
            "SELECT COALESCE(SUM(amount_eur), 0) FROM contract_milestones "
            "WHERE billed_at >= :start AND deleted_at IS NULL"
        ),
        {"start": month_start},
    )).first()
    billed = billed_row[0] if billed_row else 0

    paid_row = (await db.execute(
        text(
            "SELECT COALESCE(SUM(amount_eur), 0) FROM contract_milestones "
            "WHERE paid_at >= :start AND deleted_at IS NULL"
        ),
        {"start": month_start},
    )).first()
    paid = paid_row[0] if paid_row else 0

    pending_row = (await db.execute(
        text(
            "SELECT COALESCE(SUM(amount_eur), 0) FROM contract_milestones "
            "WHERE status IN ('invoice_issued','payment_pending') "
            "AND deleted_at IS NULL"
        )
    )).first()
    pending = pending_row[0] if pending_row else 0

    overdue_row = (await db.execute(
        text(
            "SELECT COUNT(*) FROM contract_milestones "
            "WHERE status IN ('invoice_issued','payment_pending') "
            "AND billed_at < NOW() - INTERVAL '30 days' "
            "AND deleted_at IS NULL"
        )
    )).first()
    overdue = overdue_row[0] if overdue_row else 0

    return FinanceKpisResponse(
        billed_this_month_eur=f"{Decimal(billed):.2f}",
        paid_this_month_eur=f"{Decimal(paid):.2f}",
        pending_total_eur=f"{Decimal(pending):.2f}",
        overdue_count=int(overdue),
    )


@admin_finance_router.get(
    "/pending-payments",
    response_model=list[PendingPaymentRow],
)
async def list_pending_payments(
    db: Annotated[AsyncSession, Depends(get_db)],
    _owner: Annotated[User, Depends(require_owner)],
    limit: int = 100,
):
    await _set_admin_rls_context(db)
    rows = (await db.execute(
        text(
            "SELECT cm.id, cm.milestone_name, cm.milestone_index, "
            "cm.project_id, p.nombre AS project_name, cm.invoice_id, "
            "i.numero_correlativo, cm.amount_eur, cm.billed_at "
            "FROM contract_milestones cm "
            "LEFT JOIN projects p ON p.id = cm.project_id "
            "LEFT JOIN invoices i ON i.id = cm.invoice_id "
            "WHERE cm.status IN ('invoice_issued','payment_pending') "
            "AND cm.deleted_at IS NULL "
            "ORDER BY cm.billed_at ASC NULLS LAST "
            "LIMIT :lim"
        ),
        {"lim": limit},
    )).all()

    now = datetime.now(timezone.utc)
    items: list[PendingPaymentRow] = []
    for r in rows:
        billed_at = r[8]
        days_pending = (now - billed_at).days if billed_at else 0
        items.append(PendingPaymentRow(
            milestone_id=r[0],
            milestone_name=r[1],
            milestone_index=r[2],
            project_id=r[3],
            project_name=r[4] or "Proyecto",
            invoice_id=r[5],
            invoice_number=r[6],
            amount_eur=f"{Decimal(r[7]):.2f}",
            billed_at=billed_at,
            days_pending=days_pending,
        ))
    return items


@admin_finance_router.post(
    "/milestones/{milestone_id}/mark-paid",
    response_model=MarkPaidResponse,
)
async def mark_milestone_paid(
    milestone_id: uuid.UUID,
    payload: MarkPaidRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    owner: Annotated[User, Depends(require_owner)],
):
    await _set_admin_rls_context(db)
    paid_at_dt: datetime | None = None
    if payload.paid_at:
        try:
            paid_at_dt = datetime.fromisoformat(payload.paid_at)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"paid_at debe ser ISO 8601: {exc}",
            ) from exc

    service = AutoBillingService(db)
    try:
        milestone = await service.mark_milestone_paid(
            milestone_id=milestone_id,
            by_user_id=owner.id,
            payment_reference=payload.payment_reference,
            payment_notes=payload.payment_notes,
            paid_at=paid_at_dt,
        )
    except AutoBillingError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    advanced_to: int | None = None
    if milestone.blocking_next_phase:
        advanced_to = milestone.workflow_phase_index + 1

    return MarkPaidResponse(
        milestone_id=milestone.id,
        status=milestone.status,
        paid_at=milestone.paid_at,
        payment_reference=milestone.payment_reference,
        workflow_advanced_to_phase=advanced_to,
    )


@admin_contracts_router.post(
    "/{contract_id}/milestones/regenerate",
    response_model=RegenerateMilestonesResponse,
)
async def regenerate_contract_milestones(
    contract_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _owner: Annotated[User, Depends(require_owner)],
):
    await _set_admin_rls_context(db)
    contract = await db.get(Contract, contract_id)
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract {contract_id} not found",
        )
    if contract.project_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contract sin project_id · no se pueden regenerar milestones",
        )

    pricing = (contract.parametros_xyzpr or {}).get("pricing") or {}
    categoria = (pricing.get("categoria") or "").upper()
    total_value = pricing.get("total")
    if not categoria or total_value is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Contract sin parametros_xyzpr.pricing (categoria + total) · "
                "completar pricing antes de regenerar milestones"
            ),
        )

    factory = MilestoneFactory(db)
    try:
        created = await factory.create_milestones_for_contract(
            contract_id=contract_id,
            project_id=contract.project_id,
            categoria=categoria,
            contract_total=Decimal(str(total_value)),
        )
    except MilestoneFactoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    existing_count = (await db.execute(
        select(ContractMilestone).where(
            ContractMilestone.contract_id == contract_id
        )
    )).scalars().all()
    skipped = len(existing_count) - len(created)

    return RegenerateMilestonesResponse(
        contract_id=contract_id,
        created=len(created),
        skipped=max(0, skipped),
    )


# ──────────── Admin · vista implementación × pagos (#45) ────────────


@admin_finance_router.get(
    "/projects/{project_id}/implementation-payments",
)
async def get_implementation_payments_admin(
    project_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _owner: Annotated[User, Depends(require_owner)],
):
    """#45 · vista cruzada fase × hito de cobro (detalle admin completo)."""
    await _set_admin_rls_context(db)
    return await build_implementation_payments(db, project_id)


# ──────────────── Cliente · billing endpoints ────────────────


async def _resolve_client_project_id(
    db: AsyncSession, user: ClientUser,
) -> uuid.UUID:
    """Resuelve el proyecto del cliente (R27 single-project LIMIT 1) y fija el
    contexto RLS project+client. Fija current_client_id ANTES de consultar
    projects (coherente con _set_client_rls_context de invoices · evita que la
    RLS por client_id bloquee el lookup)."""
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": str(user.client_id)},
    )
    project_id = (await db.execute(
        text(
            "SELECT id FROM projects WHERE client_id = :cid "
            "AND deleted_at IS NULL ORDER BY created_at DESC LIMIT 1"
        ),
        {"cid": str(user.client_id)},
    )).scalar_one_or_none()
    if not project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sin proyecto",
        )
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(project_id)},
    )
    return project_id


_CLIENT_PAYMENT_STATE_LABELS = {
    "paid": "Pagado",
    "due": "Pendiente de pago",
    "upcoming": "Próximo",
}


@client_billing_router.get("/implementation-payments")
async def get_implementation_payments_client(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[ClientUser, Depends(require_client_user)],
):
    """#45 · resumen amable (R29) de qué fases del proyecto están pagadas y cuáles
    quedan por pagar. Sin jerga interna · sin presión: estado factual + fecha
    prevista. El cliente VE su avance × pagos · no opera nada."""
    project_id = await _resolve_client_project_id(db, user)
    view = await build_implementation_payments(db, project_id)

    hitos = [
        {
            "concepto": m["description"] or m["phase_label"],
            "fase": m["phase_label"],
            "importe_eur": m["amount_with_vat_eur"],
            "estado": _CLIENT_PAYMENT_STATE_LABELS.get(
                m["payment_state"], m["payment_state"]
            ),
            "payment_state": m["payment_state"],
            "fecha_prevista": m["scheduled_date"],
            "vencido": m["is_overdue"],
            "pagado_el": m["paid_at"],
        }
        for m in view["milestones"]
    ]
    return {
        "project_name": view.get("project_name", "Tu proyecto"),
        "fase_actual": view.get("current_phase_label"),
        "total_eur": view["totals"]["total_eur"],
        "pagado_eur": view["totals"]["paid_eur"],
        "pendiente_eur": view["totals"]["pending_eur"],
        "proximo_pago_previsto": view["totals"]["next_due_date"],
        "hitos": hitos,
    }


@client_billing_router.get(
    "/invoices",
    response_model=list[ClientInvoiceRow],
)
async def list_my_invoices(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[ClientUser, Depends(require_client_user)],
):
    await _set_client_rls_context(db, user)
    rows = (await db.execute(
        select(Invoice).where(
            Invoice.client_id == user.client_id,
        ).order_by(desc(Invoice.fecha_emision))
    )).scalars().all()

    transfer = ManualTransferProvider()
    items: list[ClientInvoiceRow] = []
    for inv in rows:
        is_pending = (inv.estado_pago or "").lower() != "paid"
        bank_html = ""
        bank_text = ""
        if is_pending and inv.numero_correlativo:
            bank_html = transfer.render_html_block(
                invoice_number=inv.numero_correlativo,
                amount_eur=Decimal(str(inv.total or 0)),
                payment_due_date=(
                    inv.fecha_vencimiento.isoformat()
                    if inv.fecha_vencimiento else None
                ),
            )
            bank_text = transfer.render_text_block(
                invoice_number=inv.numero_correlativo,
                amount_eur=Decimal(str(inv.total or 0)),
                payment_due_date=(
                    inv.fecha_vencimiento.isoformat()
                    if inv.fecha_vencimiento else None
                ),
            )
        items.append(ClientInvoiceRow(
            invoice_id=inv.id,
            invoice_number=inv.numero_correlativo,
            concepto=inv.concepto,
            base_imponible=(
                f"{Decimal(str(inv.base_imponible)):.2f}"
                if inv.base_imponible is not None else None
            ),
            iva_importe=(
                f"{Decimal(str(inv.iva_importe)):.2f}"
                if inv.iva_importe is not None else None
            ),
            total=(
                f"{Decimal(str(inv.total)):.2f}"
                if inv.total is not None else None
            ),
            fecha_emision=(
                inv.fecha_emision.isoformat()
                if inv.fecha_emision else None
            ),
            fecha_vencimiento=(
                inv.fecha_vencimiento.isoformat()
                if inv.fecha_vencimiento else None
            ),
            estado_pago=inv.estado_pago,
            bank_instructions_html=bank_html,
            bank_instructions_text=bank_text,
        ))
    return items


__all__ = [
    "admin_finance_router",
    "admin_contracts_router",
    "client_billing_router",
]
