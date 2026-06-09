"""Inyección de identidad fiscal del emisor en factura/Facturae (#44).

Prueba empírica de la fase de consumidores:
- PDF de factura lleva NIF + IBAN + bloques Emisor/Receptor reales.
- QR Verifactu usa el NIF real (no el placeholder).
- Degradación elegante: fiscal vacío → PDF SIN ``__CONSULTOR_NIF__``.
- Facturae seller autónomo → PersonTypeCode 'F'.

La identidad fiscal se inyecta por la FUENTE ÚNICA ``AdminSettings.fiscal``
(leída vía ``core.fiscal_identity.get_fiscal_identity``).
"""
from __future__ import annotations

import io
import json
import uuid
from datetime import date
from decimal import Decimal

import pytest
from docx import Document
from sqlalchemy import text

from backend.app.database import set_tenant_context
from backend.app.motors.m15_billing.billing_service import BillingService
from backend.app.motors.m15_billing.facturae_generator import (
    InvoiceData,
    PartyData,
    generate_facturae_xml,
)
from backend.tests.conftest import _admin_setup, setup_test_project


_MARCOS_FISCAL = {
    "nif": "77171140E",
    "nombre_fiscal": "Marcos Mata García",
    "nombre_comercial": "FULKRO",
    "tipo_persona": "F",
    "domicilio_via": "Paseo de la Dirección, 46",
    "domicilio_municipio": "Madrid",
    "domicilio_provincia": "Madrid",
    "iban": "ES34 1465 0260 6317 5549 5007",
    "bank_holder": "Marcos Mata García",
}


async def _setup_tenant(db):
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id), project_id=uuid.UUID(project_id),
    )
    return client_id, project_id


async def _set_fiscal(db, data: dict) -> None:
    """Escribe AdminSettings.fiscal (bypass RLS para el setup)."""
    async with _admin_setup(db):
        await db.execute(
            text("UPDATE admin_settings SET fiscal = CAST(:j AS jsonb)"),
            {"j": json.dumps(data)},
        )


async def _make_invoice(db, client_id, project_id):
    return await BillingService().generate_invoice(
        db,
        client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
        contract_id=None,
        concepto="Proyecto ENS",
        lineas=[{"descripcion": "Fase 1", "cantidad": 1, "precio_unitario": 5000}],
    )


def _docx_text(blob: bytes) -> str:
    doc = Document(io.BytesIO(blob))
    return "\n".join(p.text for p in doc.paragraphs)


@pytest.mark.asyncio
async def test_invoice_pdf_carries_emisor_nif_iban(db):
    """Factura con datos reales → PDF con NIF + IBAN + Emisor/Receptor."""
    client_id, project_id = await _setup_tenant(db)
    await _set_fiscal(db, _MARCOS_FISCAL)
    inv = await _make_invoice(db, client_id, project_id)

    pdf = await BillingService().generate_invoice_pdf(db, inv.id)
    txt = _docx_text(pdf)

    assert "77171140E" in txt                              # NIF emisor
    assert "ES34 1465 0260 6317 5549 5007" in txt          # IBAN
    assert "Emisor" in txt
    assert "Receptor" in txt
    assert "Paseo de la Dirección, 46" in txt              # domicilio fiscal
    assert "__CONSULTOR_NIF__" not in txt                  # NUNCA el placeholder


@pytest.mark.asyncio
async def test_invoice_qr_uses_real_nif(db):
    """El QR Verifactu codifica el NIF real, no el placeholder."""
    client_id, project_id = await _setup_tenant(db)
    await _set_fiscal(db, _MARCOS_FISCAL)
    inv = await _make_invoice(db, client_id, project_id)

    qr = BillingService()._build_verifactu_qr_payload(inv, "77171140E")
    assert "nif=77171140E" in qr
    assert "__CONSULTOR_NIF__" not in qr


@pytest.mark.asyncio
async def test_invoice_pdf_degrades_without_placeholder(db):
    """Anti-falso-verde: fiscal vacío → PDF degrada, SIN __CONSULTOR_NIF__."""
    client_id, project_id = await _setup_tenant(db)
    await _set_fiscal(db, {})
    inv = await _make_invoice(db, client_id, project_id)

    pdf = await BillingService().generate_invoice_pdf(db, inv.id)
    txt = _docx_text(pdf)

    assert "__CONSULTOR_NIF__" not in txt
    assert "pendientes de configurar" in txt  # nota degradación clara


def test_facturae_seller_person_type_F():
    """Seller autónomo → PersonTypeCode 'F'; buyer AAPP → 'J' (default)."""
    seller = PartyData(
        nombre_razon_social="Marcos Mata García",
        cif_nif="77171140E",
        person_type_code="F",
    )
    buyer = PartyData(nombre_razon_social="AAPP Ejemplo", cif_nif="P0000000A")
    inv = InvoiceData(
        invoice_number="F-1",
        issue_date=date.today(),
        amount_eur=Decimal("1000.00"),
        description="Servicios ENS",
        dir3_oficina_contable="OC1",
        dir3_organo_gestor="OG1",
        dir3_unidad_tramitadora="UT1",
    )
    xml = generate_facturae_xml(seller=seller, buyer=buyer, invoice=inv).decode("utf-8")

    assert ">F</PersonTypeCode>" in xml   # seller persona física
    assert ">J</PersonTypeCode>" in xml   # buyer jurídica
    assert "77171140E" in xml


@pytest.mark.asyncio
async def test_pdf_e2e_via_patch_path_with_audit_log(db):
    """E2E: datos fiscales ENTRADOS POR PATCH (audit_log) → factura con NIF/IBAN.

    Camino real de producción: Marcos rellena la pestaña fiscal →
    update_section('fiscal') (setea app.current_user → trigger audit_log) →
    la factura emitida lleva su NIF/IBAN reales.
    """
    from backend.app.admin_settings.schemas import FiscalSettings
    from backend.app.admin_settings.service import update_section
    from backend.app.auth.crypto import hash_password
    from backend.app.models.auth import User

    client_id, project_id = await _setup_tenant(db)

    owner = User(
        email="fiscal-e2e@fulkro.test",
        password_hash=hash_password("TestP@ssw0rd123!"),
        display_name="Owner",
        is_active=True,
        role="owner",
    )
    db.add(owner)
    await db.flush()

    # PATCH fiscal por el camino real (genera audit_log vía trigger).
    await update_section(
        db=db, section="fiscal",
        payload=FiscalSettings(**_MARCOS_FISCAL), user=owner,
    )
    # El commit del PATCH puede limpiar el contexto tenant transaction-local;
    # lo re-aseguramos antes de emitir la factura.
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id), project_id=uuid.UUID(project_id),
    )

    inv = await _make_invoice(db, client_id, project_id)
    txt = _docx_text(await BillingService().generate_invoice_pdf(db, inv.id))
    assert "77171140E" in txt
    assert "ES34 1465 0260 6317 5549 5007" in txt
    assert "__CONSULTOR_NIF__" not in txt

    # El PATCH dejó rastro auditado (R6) con el NIF.
    row = (await db.execute(text(
        "SELECT payload_new FROM audit_log WHERE tabla = 'admin_settings' "
        "AND usuario = 'fiscal-e2e@fulkro.test' ORDER BY timestamp DESC LIMIT 1"
    ))).first()
    assert row is not None
    assert row.payload_new["fiscal"]["nif"] == "77171140E"
