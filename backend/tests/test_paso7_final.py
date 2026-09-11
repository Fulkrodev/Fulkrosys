"""Tests Paso 7 final — reporting + renewal + discount + C-001 apendice."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import text as sa_text

from backend.app.motors.m12_magic_link.purposes import (
    MagicLinkPurpose,
    get_config,
)
from backend.app.motors.m13_commercial.discount_service import (
    DiscountError,
    DiscountService,
)
from backend.app.motors.m23_retainer.report_service import (
    ReportKPIs,
    ReportService,
)
from backend.app.motors.m27_conformity.renewal_scheduler import (
    ALERT_1M_BEFORE_DAYS,
    ALERT_3M_BEFORE_DAYS,
    ALERT_6M_BEFORE_DAYS,
    run_renewal_bianual_check,
)
# O1 · `CERTIFICATION_VALIDITY_DAYS` (730) desaparecio al unificar el bienio del
# art. 31: son DOS ANYOS de calendario, no 730 dias, y 730 se come el dia
# bisiesto. Este fichero seguia importandola, asi que llevaba desde entonces sin
# poder coleccionarse -- y no se veia porque la bateria se corria por
# directorios, nunca entera. La fecha se calcula ahora preguntandole a la
# funcion canonica donde cae el aniversario de verdad.
from backend.tests.helpers_bienio import certificado_para_que_falten
from backend.tests.conftest import _admin_setup, setup_test_project


C001_PATH = (
    Path(__file__).resolve().parents[1]
    / "app" / "motors" / "m06_document_factory"
    / "templates" / "commercial"
    / "C001_contrato_de_prestacion_de_servicios_de_consultoria.md"
)


# ══════════════════════════════════════════════════════════════════════
# 7.3 Magic link purposes reporting + renewal
# ══════════════════════════════════════════════════════════════════════


class TestMagicLinkPurposesPaso7Final:
    def test_34_purposes_total(self):
        # SAN-B.MB-6.6: AUTORIZACION_PENTEST eliminado · 35 -> 34.
        # SAN-D MB-19.4: FIRMA_CONTRATO añadido (#36 ADR-041) · 34 -> 35.
        # Ejecutable 8 Pasada 16: AUDITOR_PORTAL_ENAC añadido en Sesión 3B-2B.6 (auditor portal ·
        # CLAUDE.md + memoria auditor-portal-architecture.md) · 35 -> 36. (test desactualizado · fuente citada)
        # Batch A diagnóstico previo: DIAGNOSTICO_PRECLIENTE añadido (#38) · 36 -> 37.
        assert len(list(MagicLinkPurpose)) == 37

    def test_reporte_trimestral_ttl_60d(self):
        cfg = get_config(MagicLinkPurpose.REPORTE_TRIMESTRAL)
        assert cfg["ttl_hours"] == 60 * 24

    def test_reporte_anual_ttl_90d(self):
        cfg = get_config(MagicLinkPurpose.REPORTE_ANUAL)
        assert cfg["ttl_hours"] == 90 * 24

    def test_renewal_campaign_ttl_120d(self):
        cfg = get_config(MagicLinkPurpose.RENEWAL_CAMPAIGN_DETAILS)
        assert cfg["ttl_hours"] == 120 * 24


# ══════════════════════════════════════════════════════════════════════
# 7.3 Reporting E-801 + E-802
# ══════════════════════════════════════════════════════════════════════


class TestReportingE801E802:
    @pytest.mark.asyncio
    async def test_e801_quarterly_generates(self, db):
        client_id, project_id = await setup_test_project(db)
        report = await ReportService().generate_e801_quarterly(
            db,
            client_id=uuid.UUID(client_id),
            project_id=uuid.UUID(project_id),
            year=2026, quarter=1,
        )
        assert report.report_type == "E-801_quarterly"
        assert report.periodo_quarter == 1
        assert report.periodo_inicio == date(2026, 1, 1)
        assert report.periodo_fin == date(2026, 3, 31)
        assert report.hash_sha256 is not None
        assert len(report.hash_sha256) == 64
        assert report.signature_ed25519 is not None

    @pytest.mark.asyncio
    async def test_e801_idempotent(self, db):
        client_id, project_id = await setup_test_project(db)
        svc = ReportService()
        r1 = await svc.generate_e801_quarterly(
            db, client_id=uuid.UUID(client_id),
            project_id=uuid.UUID(project_id), year=2026, quarter=2,
        )
        r2 = await svc.generate_e801_quarterly(
            db, client_id=uuid.UUID(client_id),
            project_id=uuid.UUID(project_id), year=2026, quarter=2,
        )
        assert r1.id == r2.id  # misma instancia = idempotencia

    @pytest.mark.asyncio
    async def test_e802_annual_generates(self, db):
        client_id, project_id = await setup_test_project(db)
        report = await ReportService().generate_e802_annual(
            db, client_id=uuid.UUID(client_id),
            project_id=uuid.UUID(project_id), year=2026,
        )
        assert report.report_type == "E-802_annual"
        assert report.periodo_year == 2026
        assert report.periodo_quarter is None
        assert report.periodo_inicio == date(2026, 1, 1)
        assert report.periodo_fin == date(2026, 12, 31)
        assert "revision por direccion" in (
            report.payload_jsonb.get("recomendaciones") or ""
        )

    @pytest.mark.asyncio
    async def test_e801_invalid_quarter_raises(self, db):
        client_id, _ = await setup_test_project(db)
        with pytest.raises(ValueError, match="quarter invalido"):
            await ReportService().generate_e801_quarterly(
                db, client_id=uuid.UUID(client_id), year=2026, quarter=5,
            )

    def test_rag_calculation_verde(self):
        kpis = ReportKPIs(activities_ok_pct=95.0, vulns_abiertas=1)
        assert ReportService._calc_rag(kpis) == "VERDE"

    def test_rag_calculation_ambar(self):
        kpis = ReportKPIs(activities_ok_pct=80.0, vulns_abiertas=5)
        assert ReportService._calc_rag(kpis) == "AMBAR"

    def test_rag_calculation_rojo(self):
        kpis = ReportKPIs(activities_ok_pct=50.0, vulns_abiertas=15)
        assert ReportService._calc_rag(kpis) == "ROJO"


# ══════════════════════════════════════════════════════════════════════
# 7.4 Renewal bianual auto-trigger
# ══════════════════════════════════════════════════════════════════════


async def _certify_project_at(db, project_id: str, certified_at: date):
    async with _admin_setup(db):
        await db.execute(sa_text(
            "UPDATE projects SET certified_at = :c, "
            "lifecycle_state = 'CERTIFIED' WHERE id = :pid"
        ), {"pid": project_id, "c": certified_at})


class TestRenewalBianualAuto:
    @pytest.mark.asyncio
    async def test_alert_6m_before_anniversary(self, db):
        client_id, project_id = await setup_test_project(db)
        # Certificado hace 550 dias = 730 - 180 (6m antes aniv)
        certified = certificado_para_que_falten(ALERT_6M_BEFORE_DAYS)
        await _certify_project_at(db, project_id, certified)
        result = await run_renewal_bianual_check(db, today=date.today())
        assert str(project_id) in result.alerts_6m
        assert str(project_id) not in result.campaigns_created_3m

    @pytest.mark.asyncio
    async def test_campaign_created_3m_before(self, db):
        client_id, project_id = await setup_test_project(db)
        certified = certificado_para_que_falten(ALERT_3M_BEFORE_DAYS)
        await _certify_project_at(db, project_id, certified)
        result = await run_renewal_bianual_check(db, today=date.today())
        assert str(project_id) in result.campaigns_created_3m

        # Verificar campana persistida
        await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            count = (await db.execute(sa_text(
                "SELECT count(*) FROM renewal_campaigns "
                "WHERE project_id = :pid AND auto_triggered = true"
            ), {"pid": project_id})).scalar()
            assert count == 1
        finally:
            await db.execute(sa_text("RESET ROLE"))

    @pytest.mark.asyncio
    async def test_alert_1m_before(self, db):
        client_id, project_id = await setup_test_project(db)
        certified = certificado_para_que_falten(ALERT_1M_BEFORE_DAYS)
        await _certify_project_at(db, project_id, certified)
        result = await run_renewal_bianual_check(db, today=date.today())
        assert str(project_id) in result.alerts_1m

    @pytest.mark.asyncio
    async def test_no_duplicate_campaigns_on_repeated_run(self, db):
        client_id, project_id = await setup_test_project(db)
        certified = certificado_para_que_falten(ALERT_3M_BEFORE_DAYS)
        await _certify_project_at(db, project_id, certified)
        r1 = await run_renewal_bianual_check(db, today=date.today())
        r2 = await run_renewal_bianual_check(db, today=date.today())
        await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            count = (await db.execute(sa_text(
                "SELECT count(*) FROM renewal_campaigns "
                "WHERE project_id = :pid"
            ), {"pid": project_id})).scalar()
            # Idempotencia: no duplica si ya hay campana activa
            assert count == 1
        finally:
            await db.execute(sa_text("RESET ROLE"))

    @pytest.mark.asyncio
    async def test_no_alert_for_unexpected_day(self, db):
        client_id, project_id = await setup_test_project(db)
        # Certificado hace 365 dias - no cae en ningun checkpoint
        certified = date.today() - timedelta(days=365)
        await _certify_project_at(db, project_id, certified)
        result = await run_renewal_bianual_check(db, today=date.today())
        assert str(project_id) not in result.alerts_6m
        assert str(project_id) not in result.alerts_1m
        assert str(project_id) not in result.campaigns_created_3m


# ══════════════════════════════════════════════════════════════════════
# 7.8 Commercial discounts
# ══════════════════════════════════════════════════════════════════════


class TestDiscountService:
    @pytest.mark.asyncio
    async def test_quick_scan_discount_auto_created(self, db):
        client_id, _ = await setup_test_project(db)
        svc = DiscountService()
        d = await svc.create_quick_scan_discount(
            db, client_id=uuid.UUID(client_id), source_invoice_id=None,
        )
        assert d.discount_type == "quick_scan_to_implantacion"
        assert float(d.amount) == 1500.0
        assert d.applicable_to == "c001_implantacion"
        assert d.status == "available"
        assert d.expires_at > datetime.now(timezone.utc)
        # Ventana 30 dias
        days = (d.expires_at - d.granted_at).days
        assert 29 <= days <= 30

    @pytest.mark.asyncio
    async def test_apply_discount_to_contract(self, db):
        client_id, project_id = await setup_test_project(db)
        svc = DiscountService()
        d = await svc.create_quick_scan_discount(
            db, client_id=uuid.UUID(client_id),
            source_invoice_id=None,
        )
        fake_contract_id = uuid.uuid4()
        async with _admin_setup(db):
            await db.execute(sa_text(
                "INSERT INTO contracts (id, tipo, estado, created_at) "
                "VALUES (:id, 'c001', 'draft', now())"
            ), {"id": str(fake_contract_id)})

        used = await svc.apply_discount_to_contract(
            db, discount_id=d.id, contract_id=fake_contract_id,
        )
        assert used.status == "used"
        assert used.used_in_contract_id == fake_contract_id

    @pytest.mark.asyncio
    async def test_apply_expired_discount_raises(self, db):
        client_id, _ = await setup_test_project(db)
        svc = DiscountService()
        d = await svc.create_quick_scan_discount(
            db, client_id=uuid.UUID(client_id),
            source_invoice_id=None,
        )
        await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            await db.execute(sa_text(
                "UPDATE commercial_discounts SET expires_at = :e "
                "WHERE id = :id"
            ), {"id": str(d.id), "e": datetime.now(timezone.utc) - timedelta(days=1)})
            await db.flush()
        finally:
            await db.execute(sa_text("RESET ROLE"))

        await db.refresh(d)

        # Crear contrato valido para respetar FK (el rechazo debe ser
        # por 'expiro' antes de tocar la FK)
        fake_contract_id = uuid.uuid4()
        async with _admin_setup(db):
            await db.execute(sa_text(
                "INSERT INTO contracts (id, tipo, estado, created_at) "
                "VALUES (:id, 'c001', 'draft', now())"
            ), {"id": str(fake_contract_id)})

        with pytest.raises(DiscountError, match="expiro"):
            await svc.apply_discount_to_contract(
                db, discount_id=d.id, contract_id=fake_contract_id,
            )

    @pytest.mark.asyncio
    async def test_expire_old_discounts_task(self, db):
        client_id, _ = await setup_test_project(db)
        svc = DiscountService()
        d = await svc.create_quick_scan_discount(
            db, client_id=uuid.UUID(client_id),
            source_invoice_id=None,
        )
        await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            await db.execute(sa_text(
                "UPDATE commercial_discounts SET expires_at = :e "
                "WHERE id = :id"
            ), {"id": str(d.id), "e": datetime.now(timezone.utc) - timedelta(hours=1)})
            await db.flush()
        finally:
            await db.execute(sa_text("RESET ROLE"))
        result = await svc.expire_old_discounts(db)
        assert str(d.id) in result["expired_ids"]

    @pytest.mark.asyncio
    async def test_manual_discount_referral(self, db):
        client_id, _ = await setup_test_project(db)
        svc = DiscountService()
        d = await svc.create_manual_discount(
            db, client_id=uuid.UUID(client_id),
            discount_type="referral_bonus",
            applicable_to="any_implantacion",
            amount=Decimal("500.00"),
            granted_reason="Cliente refirio a otra PYME",
        )
        assert d.discount_type == "referral_bonus"
        assert float(d.amount) == 500.0

    @pytest.mark.asyncio
    async def test_manual_discount_invalid_type(self, db):
        client_id, _ = await setup_test_project(db)
        svc = DiscountService()
        with pytest.raises(DiscountError, match="invalido"):
            await svc.create_manual_discount(
                db, client_id=uuid.UUID(client_id),
                discount_type="bogus",
                applicable_to="any",
                amount=Decimal("100"),
            )

    @pytest.mark.asyncio
    async def test_revoke_available_discount(self, db):
        client_id, _ = await setup_test_project(db)
        svc = DiscountService()
        d = await svc.create_quick_scan_discount(
            db, client_id=uuid.UUID(client_id),
            source_invoice_id=None,
        )
        r = await svc.revoke_discount(db, discount_id=d.id, reason="test")
        assert r.status == "revoked"
        assert (r.metadata_jsonb or {}).get("revoke_reason") == "test"


# ══════════════════════════════════════════════════════════════════════
# 7.9 C-001 Apendice Economico template
# ══════════════════════════════════════════════════════════════════════


class TestC001ApendiceEconomico:
    def test_apendice_economico_section_present(self):
        content = C001_PATH.read_text(encoding="utf-8")
        assert "## APÉNDICE ECONÓMICO" in content

    def test_apendice_has_conditional_block(self):
        content = C001_PATH.read_text(encoding="utf-8")
        assert "{% if pricing_resumen %}" in content
        # Hay varios bloques if/endif (Anexo A LCSP previo + Apendice)
        assert content.count("{% endif %}") >= 2

    def test_apendice_references_hitos_loop(self):
        content = C001_PATH.read_text(encoding="utf-8")
        assert "{% for hito in hitos_apendice %}" in content

    def test_apendice_conditional_aapp_vs_privado(self):
        content = C001_PATH.read_text(encoding="utf-8")
        assert "{% if cliente.is_aapp %}" in content
        assert "Ley 9/2017 LCSP" in content or "198.4 LCSP" in content
        assert "Ley 3/2004" in content  # fallback privado morosidad

    def test_apendice_no_internal_nomenclature_M(self):
        """Client-facing usa 'Apendice Economico', no 'Apendice M' interno."""
        content = C001_PATH.read_text(encoding="utf-8")
        assert "APÉNDICE ECONÓMICO" in content
        # La unica mencion a "Apendice M" podria ser en comentarios internos
        # de desarrollo — pero el texto visible del client-facing NO debe
        # contener "Apendice M" como nomenclatura comercial
        bad_phrases = [
            "Apéndice M Económico",  # tipico leak
            "Apéndice M ENS",
        ]
        for phrase in bad_phrases:
            assert phrase not in content, f"Nomenclatura interna leak: {phrase}"

    def test_apendice_uses_format_currency_es(self):
        content = C001_PATH.read_text(encoding="utf-8")
        assert "| format_currency_es" in content

    def test_apendice_includes_iva_21(self):
        content = C001_PATH.read_text(encoding="utf-8")
        assert "IVA 21 %" in content or "IVA 21%" in content


# ══════════════════════════════════════════════════════════════════════
# Integracion quick scan -> discount auto
# ══════════════════════════════════════════════════════════════════════


class TestQuickScanDiscountIntegration:
    @pytest.mark.asyncio
    async def test_quick_scan_invoice_creates_discount(self, db):
        from backend.app.database import set_tenant_context
        from backend.app.motors.m15_billing.billing_service import BillingService

        client_id, project_id = await setup_test_project(db)
        cid = uuid.UUID(client_id)
        await set_tenant_context(db, client_id=cid)

        billing = BillingService()
        inv = await billing.generate_quick_scan_invoice(
            db, client_id=cid, with_future_discount=True,
        )
        assert float(inv.base_imponible) == 1500.0

        # Verify discount auto-created
        await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            d = (await db.execute(sa_text(
                "SELECT id, amount, status, discount_type "
                "FROM commercial_discounts WHERE client_id = :cid"
            ), {"cid": str(cid)})).first()
            assert d is not None
            assert float(d.amount) == 1500.0
            assert d.status == "available"
            assert d.discount_type == "quick_scan_to_implantacion"
        finally:
            await db.execute(sa_text("RESET ROLE"))

    @pytest.mark.asyncio
    async def test_quick_scan_without_flag_no_discount(self, db):
        from backend.app.database import set_tenant_context
        from backend.app.motors.m15_billing.billing_service import BillingService

        client_id, project_id = await setup_test_project(db)
        cid = uuid.UUID(client_id)
        await set_tenant_context(db, client_id=cid)

        billing = BillingService()
        await billing.generate_quick_scan_invoice(
            db, client_id=cid, with_future_discount=False,
        )
        await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            count = (await db.execute(sa_text(
                "SELECT count(*) FROM commercial_discounts WHERE client_id = :cid"
            ), {"cid": str(cid)})).scalar()
            assert count == 0
        finally:
            await db.execute(sa_text("RESET ROLE"))
