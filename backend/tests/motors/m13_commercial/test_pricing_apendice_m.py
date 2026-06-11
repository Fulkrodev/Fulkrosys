"""Tests M13/M14/M15 integracion con Apendice M v2.2 — Paso 6."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text as sa_text

from backend.app.motors.m13_commercial.proposal_service import ProposalService
from backend.app.motors.m14_contracts.contract_service import ContractService
from backend.app.motors.m15_billing.billing_service import BillingService
from backend.tests.conftest import _admin_setup, setup_test_project


async def _seed_lead(db, *, is_aapp: bool = False) -> uuid.UUID:
    """Crea Lead minimo + retorna lead_id. Escape de RLS mediante fulkro role."""
    lead_id = uuid.uuid4()
    prefix = "P" if is_aapp else "B"
    cif = f"{prefix}{uuid.uuid4().hex[:8].upper()}"
    sector = "sanidad" if not is_aapp else "administracion_publica"
    nombre = (
        "Ayuntamiento Test" if is_aapp else "DataForma Test SL"
    )
    async with _admin_setup(db):
        await db.execute(sa_text(
            "INSERT INTO leads (id, empresa_nombre, empresa_cif, sector, "
            "estado, created_at) "
            "VALUES (:id, :nm, :cif, :sector, 'nuevo', now())"
        ), {"id": str(lead_id), "nm": nombre, "cif": cif, "sector": sector})
    return lead_id


async def _make_cliente_dict(is_aapp: bool = False, sector: str = "sanidad") -> dict:
    prefix = "P" if is_aapp else "B"
    return {
        "cif": f"{prefix}12345678",
        "razon_social": "Ayuntamiento Test" if is_aapp else "DataForma SL",
        "sector": sector,
    }


# ══════════════════════════════════════════════════════════════════════
# M13 — ProposalService.generate_proposal_apendice_m
# ══════════════════════════════════════════════════════════════════════


class TestProposalApendiceM:
    @pytest.mark.asyncio
    async def test_media_sanidad_total(self, db):
        lead_id = await _seed_lead(db)
        cliente = await _make_cliente_dict(is_aapp=False, sector="sanidad")
        p = await ProposalService().generate_proposal_apendice_m(
            db, lead_id=lead_id, categoria="MEDIA", cliente=cliente,
            sector="sanidad",
        )
        assert p.importe_total == 12700.0
        assert p.categoria_objetivo == "MEDIA"
        hitos = (p.hitos_pago or {}).get("hitos", [])
        assert len(hitos) == 5
        assert sum(h["amount"] for h in hitos) == pytest.approx(12700.0)

    @pytest.mark.asyncio
    async def test_basica_ayto_urgent_total(self, db):
        lead_id = await _seed_lead(db, is_aapp=True)
        cliente = await _make_cliente_dict(is_aapp=True)
        p = await ProposalService().generate_proposal_apendice_m(
            db, lead_id=lead_id, categoria="BASICA", cliente=cliente,
            dias_hasta_plazo=28,
        )
        assert p.importe_total == 4160.0
        desglose = p.importe_desglose or {}
        assert desglose.get("urgent") is True
        assert desglose.get("is_aapp") is True
        assert desglose.get("payment_days") == 60

    @pytest.mark.asyncio
    async def test_alta_total(self, db):
        lead_id = await _seed_lead(db)
        p = await ProposalService().generate_proposal_apendice_m(
            db, lead_id=lead_id, categoria="ALTA",
        )
        assert p.importe_total == 22800.0
        hitos = (p.hitos_pago or {}).get("hitos", [])
        assert len(hitos) == 7

    @pytest.mark.asyncio
    async def test_proposal_records_breakdown_text(self, db):
        lead_id = await _seed_lead(db)
        p = await ProposalService().generate_proposal_apendice_m(
            db, lead_id=lead_id, categoria="MEDIA", sector="sanidad",
        )
        assert "Sector regulado" in (p.importe_desglose or {}).get(
            "breakdown_text", ""
        )

    @pytest.mark.asyncio
    async def test_proposal_records_garantia(self, db):
        lead_id = await _seed_lead(db)
        p = await ProposalService().generate_proposal_apendice_m(
            db, lead_id=lead_id, categoria="MEDIA", sector="sanidad",
        )
        assert "Garantia" in (p.notas_marcos or "")
        assert "1.000 EUR" in (p.notas_marcos or "")


# ══════════════════════════════════════════════════════════════════════
# M14 — ContractService.generate_contract_apendice_m
# ══════════════════════════════════════════════════════════════════════


class TestContractApendiceM:
    @pytest.mark.asyncio
    async def test_contract_inherits_hitos_from_proposal(self, db):
        lead_id = await _seed_lead(db)
        client_id, project_id = await setup_test_project(db)
        from backend.app.database import set_tenant_context
        await set_tenant_context(
            db, client_id=uuid.UUID(client_id), project_id=uuid.UUID(project_id),
        )
        cliente = await _make_cliente_dict(sector="sanidad")
        p = await ProposalService().generate_proposal_apendice_m(
            db, lead_id=lead_id, categoria="MEDIA", cliente=cliente,
            sector="sanidad", project_id=uuid.UUID(project_id),
        )
        c = await ContractService().generate_contract_apendice_m(
            db,
            proposal_id=p.id,
            project_id=uuid.UUID(project_id),
            cliente=cliente,
            cliente_firmante_nombre="RSEG Test",
            cliente_firmante_cargo="Responsable Seguridad",
        )
        assert c.plantilla_id == "C-001"
        params = c.parametros_xyzpr or {}
        assert params.get("apendice_m_version") == "v2.2"
        pricing = params.get("pricing", {})
        assert pricing.get("categoria") == "MEDIA"
        assert pricing.get("total") == 12700.0
        assert len(pricing.get("hitos", [])) == 5

    @pytest.mark.asyncio
    async def test_contract_aapp_flags_lcsp(self, db):
        lead_id = await _seed_lead(db, is_aapp=True)
        client_id, project_id = await setup_test_project(db)
        from backend.app.database import set_tenant_context
        await set_tenant_context(
            db, client_id=uuid.UUID(client_id), project_id=uuid.UUID(project_id),
        )
        cliente = {"cif": "P12345678", "razon_social": "Ayto test", "sector": "publico"}
        p = await ProposalService().generate_proposal_apendice_m(
            db, lead_id=lead_id, categoria="BASICA", cliente=cliente,
            project_id=uuid.UUID(project_id),
        )
        c = await ContractService().generate_contract_apendice_m(
            db,
            proposal_id=p.id,
            project_id=uuid.UUID(project_id),
            cliente=cliente,
            cliente_firmante_nombre="Alcalde Test",
            cliente_firmante_cargo="Alcalde",
        )
        params = c.parametros_xyzpr or {}
        assert params.get("is_aapp") is True
        assert params.get("payment_days") == 60

    @pytest.mark.asyncio
    async def test_contract_sum_hitos_equals_total(self, db):
        lead_id = await _seed_lead(db)
        client_id, project_id = await setup_test_project(db)
        from backend.app.database import set_tenant_context
        await set_tenant_context(
            db, client_id=uuid.UUID(client_id), project_id=uuid.UUID(project_id),
        )
        cliente = await _make_cliente_dict()
        p = await ProposalService().generate_proposal_apendice_m(
            db, lead_id=lead_id, categoria="MEDIA", cliente=cliente,
            sector="sanidad", sedes=2, madurez_pct=15,
            project_id=uuid.UUID(project_id),
        )
        c = await ContractService().generate_contract_apendice_m(
            db, proposal_id=p.id, project_id=uuid.UUID(project_id),
            cliente=cliente, cliente_firmante_nombre="X",
            cliente_firmante_cargo="Y",
        )
        hitos = c.parametros_xyzpr["pricing"]["hitos"]
        total_hitos = sum(h["amount"] for h in hitos)
        assert total_hitos == pytest.approx(c.parametros_xyzpr["pricing"]["total"])


# ══════════════════════════════════════════════════════════════════════
# M15 — BillingService invoices
# ══════════════════════════════════════════════════════════════════════


class TestBillingApendiceM:
    @pytest.mark.asyncio
    async def test_milestone_invoice_basica_hito_1(self, db):
        lead_id = await _seed_lead(db)
        client_id, project_id = await setup_test_project(db)
        from backend.app.database import set_tenant_context
        await set_tenant_context(
            db, client_id=uuid.UUID(client_id), project_id=uuid.UUID(project_id),
        )
        cliente = await _make_cliente_dict()
        p = await ProposalService().generate_proposal_apendice_m(
            db, lead_id=lead_id, categoria="BASICA", cliente=cliente,
            project_id=uuid.UUID(project_id),
        )
        c = await ContractService().generate_contract_apendice_m(
            db, proposal_id=p.id, project_id=uuid.UUID(project_id),
            cliente=cliente, cliente_firmante_nombre="X",
            cliente_firmante_cargo="Y",
        )
        inv = await BillingService().generate_milestone_invoice_apendice_m(
            db, contract_id=c.id, milestone_code="hito_1_firma",
            cliente=cliente,
        )
        # Basica total 3200 × 30% = 960
        assert float(inv.base_imponible) == 960.0
        assert inv.fecha_vencimiento is not None

    @pytest.mark.asyncio
    async def test_milestone_invoice_aapp_plazo_60d(self, db):
        lead_id = await _seed_lead(db, is_aapp=True)
        client_id, project_id = await setup_test_project(db)
        from backend.app.database import set_tenant_context
        await set_tenant_context(
            db, client_id=uuid.UUID(client_id), project_id=uuid.UUID(project_id),
        )
        cliente = {"cif": "P12345678", "razon_social": "Ayto", "sector": "publico"}
        p = await ProposalService().generate_proposal_apendice_m(
            db, lead_id=lead_id, categoria="BASICA", cliente=cliente,
            project_id=uuid.UUID(project_id),
        )
        c = await ContractService().generate_contract_apendice_m(
            db, proposal_id=p.id, project_id=uuid.UUID(project_id),
            cliente=cliente, cliente_firmante_nombre="X",
            cliente_firmante_cargo="Y",
        )
        inv = await BillingService().generate_milestone_invoice_apendice_m(
            db, contract_id=c.id, milestone_code="hito_1_firma",
            cliente=cliente,
        )
        days_delta = (inv.fecha_vencimiento - inv.fecha_emision).days
        assert days_delta == 60  # LCSP AAPP
        assert "LCSP" in (inv.concepto or "")

    @pytest.mark.asyncio
    async def test_bolsa_flex_100h_invoice(self, db):
        client_id, project_id = await setup_test_project(db)
        from backend.app.database import set_tenant_context
        await set_tenant_context(db, client_id=uuid.UUID(client_id))
        inv = await BillingService().generate_bolsa_flex_invoice(
            db, client_id=uuid.UUID(client_id), hours=100,
        )
        assert float(inv.base_imponible) == 6375.0  # 100 × 63.75
        assert "15% descuento" in (inv.concepto or "")

    @pytest.mark.asyncio
    async def test_bolsa_flex_30h_no_discount(self, db):
        client_id, project_id = await setup_test_project(db)
        from backend.app.database import set_tenant_context
        await set_tenant_context(db, client_id=uuid.UUID(client_id))
        inv = await BillingService().generate_bolsa_flex_invoice(
            db, client_id=uuid.UUID(client_id), hours=30,
        )
        assert float(inv.base_imponible) == 2250.0

    @pytest.mark.asyncio
    async def test_quick_scan_invoice(self, db):
        client_id, project_id = await setup_test_project(db)
        from backend.app.database import set_tenant_context
        await set_tenant_context(db, client_id=uuid.UUID(client_id))
        inv = await BillingService().generate_quick_scan_invoice(
            db, client_id=uuid.UUID(client_id), with_future_discount=True,
        )
        assert float(inv.base_imponible) == 1500.0
        assert "Descontable" in (inv.concepto or "")

    @pytest.mark.asyncio
    async def test_audit_interna_basica(self, db):
        client_id, project_id = await setup_test_project(db)
        from backend.app.database import set_tenant_context
        await set_tenant_context(db, client_id=uuid.UUID(client_id))
        inv = await BillingService().generate_audit_interna_invoice(
            db, client_id=uuid.UUID(client_id), categoria="BASICA",
        )
        assert float(inv.base_imponible) == 2500.0

    @pytest.mark.asyncio
    async def test_audit_interna_media(self, db):
        client_id, project_id = await setup_test_project(db)
        from backend.app.database import set_tenant_context
        await set_tenant_context(db, client_id=uuid.UUID(client_id))
        inv = await BillingService().generate_audit_interna_invoice(
            db, client_id=uuid.UUID(client_id), categoria="MEDIA",
        )
        assert float(inv.base_imponible) == 5500.0
