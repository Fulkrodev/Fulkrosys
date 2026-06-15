"""Invoices AAPP API · SAN-C MB-11.3.

Endpoints
---------
- POST /api/v1/projects/{id}/invoices/aapp · crea draft invoice
- POST /api/v1/invoices/aapp/{id}/generate-facturae · genera XML 3.2.x
- POST /api/v1/invoices/aapp/{id}/sign-xades · firma XAdES (graceful skip)
- POST /api/v1/invoices/aapp/{id}/submit-face · stub manual portal
- GET  /api/v1/invoices/aapp/{id}/late-interest · cálculo Ley 3/2004
- GET  /api/v1/projects/{id}/invoices/aapp · lista
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy import text as _sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db, set_tenant_context
from backend.app.models.core import Client, Project
from backend.app.models.invoices_aapp import InvoiceAapp
from backend.app.motors.m15_billing.face_submitter import submit_to_face
from backend.app.motors.m15_billing.facturae_generator import (
    InvoiceData,
    PartyData,
    generate_facturae_xml,
)
from backend.app.motors.m15_billing.late_interest_calculator import (
    calculate_late_interest,
    get_bce_rate_pct,
)
from backend.app.motors.m15_billing.xades_signer import (
    FacturaeSignatureNotAvailable,
    is_xades_available,
    sign_facturae_xades,
)

# ADR-013: la facturación a la AAPP es operación admin. require_owner cierra el
# IDOR (antes el router no tenía dependencia de auth).
router = APIRouter(
    tags=["M15 - AAPP Billing (MB-11.3)"],
    dependencies=[Depends(require_owner)],
)


async def _set_project_rls(db: AsyncSession, project_id: uuid.UUID) -> None:
    """FIX(RLS): projects + invoices_aapp son RLS fail-closed bajo fulkro_app.
    Resolver owner via get_project_owner() SECURITY DEFINER + fijar tenant context
    antes de leer/insertar (si no, db.get → None → 404 y el INSERT viola WITH
    CHECK)."""
    owner = (
        await db.execute(
            _sa_text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
        )
    ).scalar()
    if not owner:
        raise HTTPException(404, "Project not found")
    await set_tenant_context(db, client_id=owner, project_id=project_id)


async def _set_rls_for_invoice(
    db: AsyncSession, invoice_id: uuid.UUID
) -> None:
    """Resuelve el project_id de una invoice_aapp (cruzando RLS vía bypass admin
    acotado) y fija el tenant context del proyecto. Necesario porque los endpoints
    invoice-scoped reciben invoice_id sin project_id en la ruta."""
    await db.execute(_sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
    try:
        pid = (
            await db.execute(
                _sa_text("SELECT project_id FROM invoices_aapp WHERE id = :iid"),
                {"iid": str(invoice_id)},
            )
        ).scalar()
    finally:
        await db.execute(_sa_text("RESET ROLE"))
    if not pid:
        raise HTTPException(404, "Invoice not found")
    await _set_project_rls(db, pid)


class InvoiceAappCreate(BaseModel):
    invoice_number: str = Field(..., max_length=50)
    amount_eur: Decimal = Field(..., gt=0)
    dir3_oficina_contable: str = Field(..., max_length=20)
    dir3_organo_gestor: str = Field(..., max_length=20)
    dir3_unidad_tramitadora: str = Field(..., max_length=20)
    payment_due_date: Optional[date] = None
    issue_date: date = Field(default_factory=date.today)
    description: str = Field(default="Servicios consultoría ENS", max_length=500)


class InvoiceAappResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: uuid.UUID
    invoice_number: str
    amount_eur: Decimal
    dir3_oficina_contable: str
    dir3_organo_gestor: str
    dir3_unidad_tramitadora: str
    status: str
    payment_due_date: Optional[date]
    paid_at: Optional[datetime]
    interest_owed_eur: Optional[Decimal]
    submitted_to_face_at: Optional[datetime]
    face_reference: Optional[str]


class FacturaeGenerationResponse(BaseModel):
    invoice_id: uuid.UUID
    xml_size_bytes: int
    xades_signed: bool
    xades_skip_reason: Optional[str] = None


class FaceSubmitResponse(BaseModel):
    submission_method: str
    face_portal_url: str
    xml_attached: bool
    xml_signed: bool
    manual_steps: list[str]
    warning_no_signature: Optional[str] = None


class LateInterestResponse(BaseModel):
    invoice_id: uuid.UUID
    amount_eur: Decimal
    interest_owed_eur: Decimal
    days_late: int
    bce_rate_pct: Decimal
    total_rate_pct: Decimal


@router.post(
    "/projects/{project_id}/invoices/aapp",
    response_model=InvoiceAappResponse,
    status_code=201,
)
async def post_create_invoice(
    project_id: uuid.UUID,
    body: InvoiceAappCreate,
    db: AsyncSession = Depends(get_db),
) -> InvoiceAappResponse:
    await _set_project_rls(db, project_id)
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    invoice = InvoiceAapp(
        project_id=project_id,
        invoice_number=body.invoice_number,
        amount_eur=body.amount_eur,
        dir3_oficina_contable=body.dir3_oficina_contable,
        dir3_organo_gestor=body.dir3_organo_gestor,
        dir3_unidad_tramitadora=body.dir3_unidad_tramitadora,
        payment_due_date=body.payment_due_date,
        status="draft",
    )
    db.add(invoice)
    await db.flush()
    await db.commit()
    return InvoiceAappResponse.model_validate(invoice)


@router.get(
    "/projects/{project_id}/invoices/aapp",
    response_model=list[InvoiceAappResponse],
)
async def get_invoices(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[InvoiceAappResponse]:
    await _set_project_rls(db, project_id)
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    result = await db.execute(
        select(InvoiceAapp)
        .where(InvoiceAapp.project_id == project_id)
        .order_by(InvoiceAapp.created_at.desc())
    )
    return [InvoiceAappResponse.model_validate(i) for i in result.scalars().all()]


@router.post(
    "/invoices/aapp/{invoice_id}/generate-facturae",
    response_model=FacturaeGenerationResponse,
)
async def post_generate_facturae(
    invoice_id: uuid.UUID,
    issue_date: Optional[date] = None,
    description: str = "Servicios consultoría ENS",
    db: AsyncSession = Depends(get_db),
) -> FacturaeGenerationResponse:
    await _set_rls_for_invoice(db, invoice_id)
    invoice = await db.get(InvoiceAapp, invoice_id)
    if invoice is None:
        raise HTTPException(404, "Invoice not found")
    project = await db.get(Project, invoice.project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    client = await db.get(Client, project.client_id)
    if client is None:
        raise HTTPException(404, "Client not found")

    # Identidad fiscal del emisor (FUENTE ÚNICA · punto #44). Autónomo
    # persona física → PersonTypeCode 'F'. Degradación elegante: NIF/
    # domicilio vacíos si aún no configurado (sin placeholder B00000000).
    from backend.app.core.fiscal_identity import get_fiscal_identity
    fi = await get_fiscal_identity(db)
    seller = PartyData(
        nombre_razon_social=(
            fi.nombre_fiscal or fi.display_name or "FULKRO Consultoría ENS"
        ),
        cif_nif=fi.nif,
        address=fi.domicilio_via,
        postal_code=fi.domicilio_cp,
        town=fi.domicilio_municipio or "Madrid",
        province=fi.domicilio_provincia or "Madrid",
        person_type_code=fi.person_type_code,
    )
    buyer = PartyData(
        nombre_razon_social=client.nombre,
        cif_nif=client.cif,
    )
    inv_data = InvoiceData(
        invoice_number=invoice.invoice_number,
        issue_date=issue_date or date.today(),
        amount_eur=invoice.amount_eur,
        description=description,
        dir3_oficina_contable=invoice.dir3_oficina_contable,
        dir3_organo_gestor=invoice.dir3_organo_gestor,
        dir3_unidad_tramitadora=invoice.dir3_unidad_tramitadora,
    )
    xml = generate_facturae_xml(seller=seller, buyer=buyer, invoice=inv_data)
    invoice.facturae_xml = xml.decode("utf-8")

    # Try XAdES sign · graceful skip si cert no disponible
    xades_signed = False
    xades_skip_reason: Optional[str] = None
    available, reason = is_xades_available()
    if available:
        try:
            xml_signed = sign_facturae_xades(xml)
            invoice.facturae_xml_signed = xml_signed.decode("utf-8")
            xades_signed = True
        except FacturaeSignatureNotAvailable as e:
            xades_skip_reason = str(e)
    else:
        xades_skip_reason = reason

    invoice.status = "draft"
    await db.commit()

    return FacturaeGenerationResponse(
        invoice_id=invoice.id,
        xml_size_bytes=len(xml),
        xades_signed=xades_signed,
        xades_skip_reason=xades_skip_reason,
    )


@router.post(
    "/invoices/aapp/{invoice_id}/submit-face",
    response_model=FaceSubmitResponse,
)
async def post_submit_face(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> FaceSubmitResponse:
    await _set_rls_for_invoice(db, invoice_id)
    invoice = await db.get(InvoiceAapp, invoice_id)
    if invoice is None:
        raise HTTPException(404, "Invoice not found")
    if not invoice.facturae_xml:
        raise HTTPException(
            422,
            "Invoice no tiene XML Facturae. Llama generate-facturae primero.",
        )

    xml_signed_bytes = (
        invoice.facturae_xml_signed.encode("utf-8")
        if invoice.facturae_xml_signed
        else None
    )
    result = submit_to_face(
        xml_signed_bytes,
        dir3_oficina_contable=invoice.dir3_oficina_contable,
        dir3_organo_gestor=invoice.dir3_organo_gestor,
        dir3_unidad_tramitadora=invoice.dir3_unidad_tramitadora,
    )
    invoice.submitted_to_face_at = datetime.now(timezone.utc)
    invoice.status = "submitted"
    await db.commit()

    return FaceSubmitResponse(
        submission_method=result["submission_method"],
        face_portal_url=result["face_portal_url"],
        xml_attached=result["xml_attached"],
        xml_signed=result["xml_signed"],
        manual_steps=result["manual_steps"],
        warning_no_signature=result["warning_no_signature"],
    )


@router.get(
    "/invoices/aapp/{invoice_id}/late-interest",
    response_model=LateInterestResponse,
)
async def get_late_interest(
    invoice_id: uuid.UUID,
    today_override: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
) -> LateInterestResponse:
    await _set_rls_for_invoice(db, invoice_id)
    invoice = await db.get(InvoiceAapp, invoice_id)
    if invoice is None:
        raise HTTPException(404, "Invoice not found")
    if invoice.payment_due_date is None:
        raise HTTPException(422, "Invoice sin payment_due_date · no calculable")

    paid_date = invoice.paid_at.date() if invoice.paid_at else None
    interest = calculate_late_interest(
        amount_eur=invoice.amount_eur,
        payment_due_date=invoice.payment_due_date,
        paid_at=paid_date,
        today=today_override,
    )
    # §2.5: GET es seguro/idempotente · NO persistir desde un GET. El interés se
    # calcula puro y se devuelve; persistirlo (si hace falta para auditoría) va en
    # un POST dedicado, no en la lectura.

    ref_date = paid_date or today_override or date.today()
    days_late = max(0, (ref_date - invoice.payment_due_date).days)
    bce_rate = get_bce_rate_pct()

    return LateInterestResponse(
        invoice_id=invoice.id,
        amount_eur=invoice.amount_eur,
        interest_owed_eur=interest,
        days_late=days_late,
        bce_rate_pct=bce_rate,
        total_rate_pct=bce_rate + Decimal("8.00"),
    )
