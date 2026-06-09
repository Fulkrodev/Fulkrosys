"""Tests Facturae 3.2.x + XAdES + FACe + Ley 3/2004 · SAN-C MB-11.3."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from lxml import etree

from backend.app.motors.m15_billing.face_submitter import (
    FACE_PORTAL_URL,
    submit_to_face,
)
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


# ============================================================
# Facturae XML 3.2.x generator
# ============================================================


def _sample_invoice_data() -> InvoiceData:
    return InvoiceData(
        invoice_number="FULKRO-2026-001",
        issue_date=date(2026, 5, 5),
        amount_eur=Decimal("1500.00"),
        description="Consultoría ENS Mayo 2026",
        dir3_oficina_contable="A04003003",
        dir3_organo_gestor="A04003001",
        dir3_unidad_tramitadora="A04003002",
    )


def test_generate_facturae_xml_produces_valid_xml():
    xml = generate_facturae_xml(
        seller=PartyData("FULKRO Consultoría", "B12345678"),
        buyer=PartyData("Ayuntamiento Test", "P0000000A"),
        invoice=_sample_invoice_data(),
    )
    parsed = etree.fromstring(xml)
    # Root namespace + tag
    assert parsed.tag.endswith("Facturae")
    assert "facturae.es" in parsed.tag


def test_generate_facturae_xml_contains_schema_version():
    xml = generate_facturae_xml(
        seller=PartyData("X", "B11111111"),
        buyer=PartyData("Y", "P22222222"),
        invoice=_sample_invoice_data(),
    )
    assert b"<SchemaVersion>3.2.2</SchemaVersion>" in xml


def test_generate_facturae_xml_includes_dir3_codes():
    xml = generate_facturae_xml(
        seller=PartyData("X", "B11111111"),
        buyer=PartyData("Y", "P22222222"),
        invoice=_sample_invoice_data(),
    )
    assert b"A04003003" in xml  # OC
    assert b"A04003001" in xml  # OG
    assert b"A04003002" in xml  # UT


def test_generate_facturae_xml_calculates_iva_21pct():
    xml = generate_facturae_xml(
        seller=PartyData("X", "B11111111"),
        buyer=PartyData("Y", "P22222222"),
        invoice=_sample_invoice_data(),  # 1500 base + 21% = 315 IVA
    )
    assert b"315.00" in xml
    # Total = 1500 * 1.21 = 1815.00
    assert b"1815.00" in xml


# ============================================================
# XAdES signer (graceful skip per briefing)
# ============================================================


def test_xades_not_available_without_lib_or_cert():
    available, reason = is_xades_available()
    assert available is False
    assert isinstance(reason, str)
    assert len(reason) > 10


def test_sign_facturae_raises_clear_exception_when_unavailable():
    with pytest.raises(FacturaeSignatureNotAvailable) as exc_info:
        sign_facturae_xades(b"<xml/>")
    assert "TODO-FACE-XADES-CERT-FNMT-001" in str(exc_info.value)


# ============================================================
# FACe submitter (manual portal)
# ============================================================


def test_submit_to_face_returns_manual_portal_method():
    result = submit_to_face(
        None,
        dir3_oficina_contable="OC1",
        dir3_organo_gestor="OG1",
        dir3_unidad_tramitadora="UT1",
    )
    assert result["submission_method"] == "manual_portal"
    assert result["face_portal_url"] == FACE_PORTAL_URL
    assert result["xml_attached"] is False
    assert result["xml_signed"] is False
    assert result["warning_no_signature"] is not None
    assert len(result["manual_steps"]) >= 3


def test_submit_to_face_with_signed_xml_no_warning():
    result = submit_to_face(
        b"<signed/>",
        dir3_oficina_contable="OC1",
        dir3_organo_gestor="OG1",
        dir3_unidad_tramitadora="UT1",
    )
    assert result["xml_signed"] is True
    assert result["warning_no_signature"] is None


# ============================================================
# Late interest calculator (Ley 3/2004)
# ============================================================


def test_no_interest_when_paid_on_time():
    interest = calculate_late_interest(
        amount_eur=Decimal("1000"),
        payment_due_date=date(2026, 6, 1),
        paid_at=date(2026, 5, 31),
    )
    assert interest == Decimal("0.00")


def test_interest_calc_30_days_late():
    interest = calculate_late_interest(
        amount_eur=Decimal("10000"),
        payment_due_date=date(2026, 1, 1),
        paid_at=date(2026, 1, 31),
    )
    # 30 días late · BCE 4.50 + 8 puntos = 12.50% anual
    # 10000 * 0.1250 * 30/365 = 102.74
    assert interest == Decimal("102.74")


def test_interest_calc_unpaid_uses_today_override():
    interest = calculate_late_interest(
        amount_eur=Decimal("5000"),
        payment_due_date=date(2026, 4, 1),
        today=date(2026, 5, 1),
    )
    # 30 días late · 5000 * 0.1250 * 30/365 = 51.37
    assert interest == Decimal("51.37")


def test_get_bce_rate_default_4_5pct():
    """Default BCE rate Q1 2026 conservador."""
    assert get_bce_rate_pct() == Decimal("4.50")


# ============================================================
# HTTP API integration
# ============================================================


@pytest.mark.asyncio
async def test_create_invoice_endpoint(async_client, db):
    from backend.tests.conftest import setup_test_project

    _, project_id = await setup_test_project(db)
    response = await async_client.post(
        f"/api/v1/projects/{project_id}/invoices/aapp",
        json={
            "invoice_number": "INV-001",
            "amount_eur": "1500.00",
            "dir3_oficina_contable": "A04003003",
            "dir3_organo_gestor": "A04003001",
            "dir3_unidad_tramitadora": "A04003002",
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["invoice_number"] == "INV-001"
    assert data["status"] == "draft"


@pytest.mark.asyncio
async def test_generate_facturae_endpoint(async_client, db):
    from backend.tests.conftest import setup_test_project

    _, project_id = await setup_test_project(db)
    create_resp = await async_client.post(
        f"/api/v1/projects/{project_id}/invoices/aapp",
        json={
            "invoice_number": "INV-002",
            "amount_eur": "2500.00",
            "dir3_oficina_contable": "OC1",
            "dir3_organo_gestor": "OG1",
            "dir3_unidad_tramitadora": "UT1",
        },
    )
    invoice_id = create_resp.json()["id"]
    response = await async_client.post(
        f"/api/v1/invoices/aapp/{invoice_id}/generate-facturae",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["xml_size_bytes"] > 1000
    # XAdES skip esperado en CI sin cert FNMT
    assert data["xades_signed"] is False
    assert data["xades_skip_reason"] is not None


@pytest.mark.asyncio
async def test_submit_face_returns_manual_portal(async_client, db):
    from backend.tests.conftest import setup_test_project

    _, project_id = await setup_test_project(db)
    create_resp = await async_client.post(
        f"/api/v1/projects/{project_id}/invoices/aapp",
        json={
            "invoice_number": "INV-003",
            "amount_eur": "1000.00",
            "dir3_oficina_contable": "OC2",
            "dir3_organo_gestor": "OG2",
            "dir3_unidad_tramitadora": "UT2",
        },
    )
    invoice_id = create_resp.json()["id"]
    await async_client.post(
        f"/api/v1/invoices/aapp/{invoice_id}/generate-facturae",
    )
    response = await async_client.post(
        f"/api/v1/invoices/aapp/{invoice_id}/submit-face",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["submission_method"] == "manual_portal"
    assert "face.gob.es" in data["face_portal_url"]


@pytest.mark.asyncio
async def test_late_interest_endpoint(async_client, db):
    from backend.tests.conftest import setup_test_project

    _, project_id = await setup_test_project(db)
    create_resp = await async_client.post(
        f"/api/v1/projects/{project_id}/invoices/aapp",
        json={
            "invoice_number": "INV-004",
            "amount_eur": "10000.00",
            "dir3_oficina_contable": "OC3",
            "dir3_organo_gestor": "OG3",
            "dir3_unidad_tramitadora": "UT3",
            "payment_due_date": "2026-01-01",
        },
    )
    invoice_id = create_resp.json()["id"]
    response = await async_client.get(
        f"/api/v1/invoices/aapp/{invoice_id}/late-interest?today_override=2026-05-01",
    )
    assert response.status_code == 200
    data = response.json()
    # 120 días late · 10000 * 12.5% * 120/365 = 410.96
    assert Decimal(data["interest_owed_eur"]) == Decimal("410.96")
    assert data["days_late"] == 120


@pytest.mark.asyncio
async def test_submit_face_without_xml_returns_422(async_client, db):
    from backend.tests.conftest import setup_test_project

    _, project_id = await setup_test_project(db)
    create_resp = await async_client.post(
        f"/api/v1/projects/{project_id}/invoices/aapp",
        json={
            "invoice_number": "INV-005",
            "amount_eur": "500.00",
            "dir3_oficina_contable": "OC5",
            "dir3_organo_gestor": "OG5",
            "dir3_unidad_tramitadora": "UT5",
        },
    )
    invoice_id = create_resp.json()["id"]
    response = await async_client.post(
        f"/api/v1/invoices/aapp/{invoice_id}/submit-face",
    )
    assert response.status_code == 422
