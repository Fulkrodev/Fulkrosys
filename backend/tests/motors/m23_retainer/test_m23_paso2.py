"""Tests M23 Sesion 8 Paso 2 — R_MICRO + pricing_catalog + Agente 26 +
billing integration + health + renewal + material_change.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select, text as sa_text

from backend.app.database import set_tenant_context
from backend.app.models.retainer import (
    PricingCatalog, RetainerActivity, RetainerBillingEvent,
    RetainerContract, RetainerDriftEvent, RetainerQuarterlyReport,
)
from backend.app.motors.m23_retainer import (
    agent_26, billing_integration, paso2_extensions,
    retainer_service as rs_module,
)
from backend.app.motors.m23_retainer.agent_26 import (
    RetainerAlert, draft_client_email_offline, run_weekly_analysis,
)
from backend.app.motors.m23_retainer.pricing_catalog_seed import (
    PRICING_ENTRIES, seed_pricing_catalog,
)
from backend.app.motors.m23_retainer.retainer_service import (
    CADENCES_BY_PROFILE, SLA_BY_PROFILE, RetainerService,
)
from backend.tests.conftest import _admin_setup, setup_test_project


async def _set_tenant(db, project_id: str) -> uuid.UUID:
    client_id = (await db.execute(
        sa_text("SELECT get_project_owner(:pid)"), {"pid": project_id},
    )).scalar()
    pid = uuid.UUID(project_id)
    await set_tenant_context(db, client_id=client_id, project_id=pid)
    return pid


async def _ensure_pricing(db) -> None:
    async with _admin_setup(db):
        await seed_pricing_catalog(db)


# ════════════════════════════════════════════════════════════════════
# R_MICRO tier
# ════════════════════════════════════════════════════════════════════

class TestRMicroTier:
    def test_r_micro_in_cadences(self):
        assert "R_MICRO" in CADENCES_BY_PROFILE
        cadences = CADENCES_BY_PROFILE["R_MICRO"]
        assert "comite_seguridad" in cadences
        assert cadences["comite_seguridad"]["frecuencia"] == "semestral"
        assert cadences["vigilancia_vulnerabilidades"]["frecuencia"] == "mensual"

    def test_r_micro_sla_120h(self):
        assert SLA_BY_PROFILE["R_MICRO"] == 120

    def test_r_micro_cadencies_fewer_than_r_std(self):
        r_micro = CADENCES_BY_PROFILE["R_MICRO"]
        r_std = CADENCES_BY_PROFILE["R_STD"]
        # R_MICRO tiene menos actividades anuales que R_STD
        assert len(r_micro) <= len(r_std)


# ════════════════════════════════════════════════════════════════════
# pricing_catalog seed + lookup
# ════════════════════════════════════════════════════════════════════

class TestPricingCatalog:
    @pytest.mark.asyncio
    async def test_seed_pricing_catalog_inserts_all(self, db):
        async with _admin_setup(db):
            result = await seed_pricing_catalog(db)
        # Re-execute idempotent
        async with _admin_setup(db):
            r = await db.execute(sa_text(
                "SELECT COUNT(*) FROM pricing_catalog"
            ))
            total = r.scalar() or 0
        assert total >= len(PRICING_ENTRIES)

    @pytest.mark.asyncio
    async def test_seed_idempotent(self, db):
        async with _admin_setup(db):
            r1 = await seed_pricing_catalog(db)
            r2 = await seed_pricing_catalog(db)
        assert r2.get("inserted", 0) == 0

    @pytest.mark.asyncio
    async def test_r_micro_price_150(self, db):
        await _ensure_pricing(db)
        async with _admin_setup(db):
            price = await paso2_extensions.get_tier_price(db, "R_MICRO")
        assert price == Decimal("150.00")

    @pytest.mark.asyncio
    async def test_r_lite_price_300(self, db):
        await _ensure_pricing(db)
        async with _admin_setup(db):
            price = await paso2_extensions.get_tier_price(db, "R_LITE")
        assert price == Decimal("300.00")

    @pytest.mark.asyncio
    async def test_r_std_price_700(self, db):
        await _ensure_pricing(db)
        async with _admin_setup(db):
            price = await paso2_extensions.get_tier_price(db, "R_STD")
        assert price == Decimal("700.00")

    @pytest.mark.asyncio
    async def test_r_plus_price_1200(self, db):
        await _ensure_pricing(db)
        async with _admin_setup(db):
            price = await paso2_extensions.get_tier_price(db, "R_PLUS")
        assert price == Decimal("1200.00")

    @pytest.mark.asyncio
    async def test_implantacion_media_price_9500(self, db):
        await _ensure_pricing(db)
        async with _admin_setup(db):
            r = await db.execute(sa_text(
                "SELECT base_price FROM pricing_catalog "
                "WHERE category = 'implantacion' AND tier_code = 'MEDIA'"
            ))
            price = r.scalar()
        assert float(price) == 9500.00


# ════════════════════════════════════════════════════════════════════
# suggest_tier — 12 casos matriz
# ════════════════════════════════════════════════════════════════════

class TestSuggestTier:
    def test_basica_small_nonreg_suggests_micro(self):
        r = paso2_extensions.suggest_tier(
            "BASICA", empleados=8, sector="servicios_profesionales",
        )
        assert r["tier_sugerido"] == "R_MICRO"

    def test_basica_regulated_suggests_lite(self):
        r = paso2_extensions.suggest_tier(
            "BASICA", empleados=20, sector="sanidad_privada",
        )
        assert r["tier_sugerido"] == "R_LITE"

    def test_media_standard_suggests_std(self):
        r = paso2_extensions.suggest_tier(
            "MEDIA", empleados=80, sector="servicios_profesionales",
        )
        assert r["tier_sugerido"] == "R_STD"

    def test_media_complex_suggests_plus(self):
        r = paso2_extensions.suggest_tier(
            "MEDIA", empleados=180, sector="sanidad_privada",
            datos_sensibles=True,
        )
        assert r["tier_sugerido"] == "R_PLUS"

    def test_media_multi_site_suggests_plus(self):
        r = paso2_extensions.suggest_tier(
            "MEDIA", empleados=80, sector="fintech", ubicaciones=3,
        )
        assert r["tier_sugerido"] == "R_PLUS"

    def test_alta_suggests_plus(self):
        r = paso2_extensions.suggest_tier(
            "ALTA", empleados=300, sector="sanidad_privada",
        )
        assert r["tier_sugerido"] == "R_PLUS"


# ════════════════════════════════════════════════════════════════════
# Annual calendar per tier
# ════════════════════════════════════════════════════════════════════

class TestAnnualCalendar:
    @pytest.mark.asyncio
    async def test_r_micro_calendar_has_mensual_vuln(self, db):
        _, project_id = await setup_test_project(db)
        pid = await _set_tenant(db, project_id)
        async with _admin_setup(db):
            client_id = (await db.execute(sa_text(
                "SELECT get_project_owner(:pid)"), {"pid": project_id},
            )).scalar()
            svc = RetainerService()
            rc = await svc.create_retainer(
                db, client_id=client_id, project_id=pid,
                perfil="R_MICRO", precio_mensual=150.00,
                inicio=date.today(),
            )
            created = await svc.generate_annual_activities(
                db, rc.id, year=date.today().year,
            )
        vuln_count = sum(
            1 for a in created if a.tipo_actividad == "vigilancia_vulnerabilidades"
        )
        # Mensual = 12 vuln scans
        assert vuln_count == 12

    @pytest.mark.asyncio
    async def test_r_plus_calendar_has_monthly_comite(self, db):
        _, project_id = await setup_test_project(db)
        pid = await _set_tenant(db, project_id)
        async with _admin_setup(db):
            client_id = (await db.execute(sa_text(
                "SELECT get_project_owner(:pid)"), {"pid": project_id},
            )).scalar()
            svc = RetainerService()
            rc = await svc.create_retainer(
                db, client_id=client_id, project_id=pid,
                perfil="R_PLUS", precio_mensual=1200.00,
                inicio=date.today(),
            )
            created = await svc.generate_annual_activities(
                db, rc.id, year=date.today().year,
            )
        comite = sum(
            1 for a in created if a.tipo_actividad == "comite_seguridad"
        )
        # Mensual = 12 comites
        assert comite == 12


# ════════════════════════════════════════════════════════════════════
# Health status
# ════════════════════════════════════════════════════════════════════

class TestHealthStatus:
    @pytest.mark.asyncio
    async def test_health_green_fresh_retainer(self, db):
        _, project_id = await setup_test_project(db)
        pid = await _set_tenant(db, project_id)
        async with _admin_setup(db):
            client_id = (await db.execute(sa_text(
                "SELECT get_project_owner(:pid)"), {"pid": project_id},
            )).scalar()
            svc = RetainerService()
            rc = await svc.create_retainer(
                db, client_id=client_id, project_id=pid,
                perfil="R_STD", precio_mensual=700.00,
                inicio=date.today(),
            )
            h = await paso2_extensions.calculate_health_status(db, rc.id)
        assert h["health"] in ("verde", "ambar")  # verde sin activities

    @pytest.mark.asyncio
    async def test_health_red_with_critical_drift(self, db):
        _, project_id = await setup_test_project(db)
        pid = await _set_tenant(db, project_id)
        async with _admin_setup(db):
            client_id = (await db.execute(sa_text(
                "SELECT get_project_owner(:pid)"), {"pid": project_id},
            )).scalar()
            svc = RetainerService()
            rc = await svc.create_retainer(
                db, client_id=client_id, project_id=pid,
                perfil="R_STD", precio_mensual=700.00,
                inicio=date.today(),
            )
            # Inject critical drift
            db.add(RetainerDriftEvent(
                retainer_contract_id=rc.id, project_id=pid,
                dimension="normativa", descripcion="Critical change",
                severidad="CRITICAL", impacto="AUDIT", estado="open",
            ))
            await db.flush()
            h = await paso2_extensions.calculate_health_status(db, rc.id)
        assert h["health"] == "rojo"
        assert h["drivers"]["drift_critical_open"] == 1


# ════════════════════════════════════════════════════════════════════
# Renewal prep + material change
# ════════════════════════════════════════════════════════════════════

class TestRenewalAndMaterialChange:
    @pytest.mark.asyncio
    async def test_schedule_renewal_prep_creates_activity(self, db):
        _, project_id = await setup_test_project(db)
        pid = await _set_tenant(db, project_id)
        async with _admin_setup(db):
            client_id = (await db.execute(sa_text(
                "SELECT get_project_owner(:pid)"), {"pid": project_id},
            )).scalar()
            svc = RetainerService()
            rc = await svc.create_retainer(
                db, client_id=client_id, project_id=pid,
                perfil="R_STD", precio_mensual=700.00,
                inicio=date.today(),
                next_renewal_date=date.today() + timedelta(days=730),
            )
            activity = await paso2_extensions.schedule_renewal_prep(db, rc.id)
        assert activity.tipo_actividad == "renewal_prep"
        assert activity.prioridad == "alta"

    @pytest.mark.asyncio
    async def test_schedule_renewal_prep_idempotent(self, db):
        _, project_id = await setup_test_project(db)
        pid = await _set_tenant(db, project_id)
        async with _admin_setup(db):
            client_id = (await db.execute(sa_text(
                "SELECT get_project_owner(:pid)"), {"pid": project_id},
            )).scalar()
            svc = RetainerService()
            rc = await svc.create_retainer(
                db, client_id=client_id, project_id=pid,
                perfil="R_STD", precio_mensual=700.00,
                inicio=date.today(),
                next_renewal_date=date.today() + timedelta(days=730),
            )
            a1 = await paso2_extensions.schedule_renewal_prep(db, rc.id)
            a2 = await paso2_extensions.schedule_renewal_prep(db, rc.id)
        assert a1.id == a2.id

    @pytest.mark.asyncio
    async def test_material_change_creates_extraordinary_audit(self, db):
        _, project_id = await setup_test_project(db)
        pid = await _set_tenant(db, project_id)
        async with _admin_setup(db):
            client_id = (await db.execute(sa_text(
                "SELECT get_project_owner(:pid)"), {"pid": project_id},
            )).scalar()
            svc = RetainerService()
            await svc.create_retainer(
                db, client_id=client_id, project_id=pid,
                perfil="R_PLUS", precio_mensual=1200.00,
                inicio=date.today(),
            )
            activity = await paso2_extensions.trigger_material_change_audit(
                db, pid,
                "Migracion nuevo CPD con cambio de proveedor cloud.",
                urgent=True,
            )
        assert "auditoria_extraordinaria" in activity.tipo_actividad
        assert activity.prioridad == "urgente"


# ════════════════════════════════════════════════════════════════════
# Billing integration M23 <-> M15
# ════════════════════════════════════════════════════════════════════

class TestBillingIntegration:
    @pytest.mark.asyncio
    async def test_generate_retainer_invoice_creates_billing_event(self, db):
        _, project_id = await setup_test_project(db)
        pid = await _set_tenant(db, project_id)
        await _ensure_pricing(db)
        async with _admin_setup(db):
            client_id = (await db.execute(sa_text(
                "SELECT get_project_owner(:pid)"), {"pid": project_id},
            )).scalar()
            svc = RetainerService()
            rc = await svc.create_retainer(
                db, client_id=client_id, project_id=pid,
                perfil="R_STD", precio_mensual=700.00,
                inicio=date.today(),
            )
            event = await billing_integration.generate_retainer_invoice(
                db, rc.id,
            )
        assert event.retainer_contract_id == rc.id
        assert event.invoice_id is not None
        assert event.amount > 0

    @pytest.mark.asyncio
    async def test_generate_retainer_invoice_idempotent(self, db):
        _, project_id = await setup_test_project(db)
        pid = await _set_tenant(db, project_id)
        await _ensure_pricing(db)
        async with _admin_setup(db):
            client_id = (await db.execute(sa_text(
                "SELECT get_project_owner(:pid)"), {"pid": project_id},
            )).scalar()
            svc = RetainerService()
            rc = await svc.create_retainer(
                db, client_id=client_id, project_id=pid,
                perfil="R_LITE", precio_mensual=300.00,
                inicio=date.today(),
            )
            e1 = await billing_integration.generate_retainer_invoice(db, rc.id)
            e2 = await billing_integration.generate_retainer_invoice(db, rc.id)
        assert e1.id == e2.id  # mismo mes -> idempotente

    @pytest.mark.asyncio
    async def test_run_retainer_billing_cycle_facturates_active(self, db):
        """#31 · el ciclo mensual (que el task generate_monthly_invoices ahora
        invoca, antes stub log-only) factura los retainers activos."""
        _, project_id = await setup_test_project(db)
        pid = await _set_tenant(db, project_id)
        await _ensure_pricing(db)
        async with _admin_setup(db):
            client_id = (await db.execute(sa_text(
                "SELECT get_project_owner(:pid)"), {"pid": project_id},
            )).scalar()
            svc = RetainerService()
            rc = await svc.create_retainer(
                db, client_id=client_id, project_id=pid,
                perfil="R_STD", precio_mensual=700.00,
                inicio=date.today(),
            )
            result = await billing_integration.run_retainer_billing_cycle(db)
        assert result["retainers_total"] >= 1
        generated_ids = {g["retainer_id"] for g in result["generated"]}
        assert str(rc.id) in generated_ids


# ════════════════════════════════════════════════════════════════════
# Quarterly report
# ════════════════════════════════════════════════════════════════════

class TestQuarterlyReport:
    @pytest.mark.asyncio
    async def test_generate_quarterly_report_prev_trimester(self, db):
        _, project_id = await setup_test_project(db)
        pid = await _set_tenant(db, project_id)
        async with _admin_setup(db):
            client_id = (await db.execute(sa_text(
                "SELECT get_project_owner(:pid)"), {"pid": project_id},
            )).scalar()
            svc = RetainerService()
            rc = await svc.create_retainer(
                db, client_id=client_id, project_id=pid,
                perfil="R_STD", precio_mensual=700.00,
                inicio=date.today(),
            )
            report = await paso2_extensions.generate_quarterly_report(
                db, rc.id, period_type="trimestral",
            )
        assert report.period_type == "trimestral"
        assert report.rag_overall in ("verde", "ambar", "rojo")

    def test_compute_period_bounds_anual(self):
        start, end = paso2_extensions._compute_period_bounds(
            "anual", date(2026, 4, 22),
        )
        assert start == date(2025, 1, 1)
        assert end == date(2025, 12, 31)

    def test_compute_period_bounds_q1_returns_q4_prev_year(self):
        start, end = paso2_extensions._compute_period_bounds(
            "trimestral", date(2026, 1, 15),
        )
        assert start == date(2025, 10, 1)
        assert end == date(2025, 12, 31)


# ════════════════════════════════════════════════════════════════════
# Agent 26
# ════════════════════════════════════════════════════════════════════

class TestAgent26:
    @pytest.mark.asyncio
    async def test_agent_26_no_retainers_empty_alerts(self, db):
        async with _admin_setup(db):
            alerts = await run_weekly_analysis(db)
        assert isinstance(alerts, list)

    @pytest.mark.asyncio
    async def test_agent_26_critical_drift_raises_alert(self, db):
        _, project_id = await setup_test_project(db)
        pid = await _set_tenant(db, project_id)
        async with _admin_setup(db):
            client_id = (await db.execute(sa_text(
                "SELECT get_project_owner(:pid)"), {"pid": project_id},
            )).scalar()
            svc = RetainerService()
            rc = await svc.create_retainer(
                db, client_id=client_id, project_id=pid,
                perfil="R_STD", precio_mensual=700.00,
                inicio=date.today(),
            )
            db.add(RetainerDriftEvent(
                retainer_contract_id=rc.id, project_id=pid,
                dimension="evidencias", descripcion="Evidencia caducada",
                severidad="CRITICAL", impacto="AUDIT", estado="open",
            ))
            await db.flush()
            alerts = await run_weekly_analysis(db)
        assert any(a.code == "A26_CRITICAL_DRIFT" for a in alerts)
        critical_alerts = [a for a in alerts if a.priority == "critical"]
        assert len(critical_alerts) >= 1

    @pytest.mark.asyncio
    async def test_agent_26_summary_structure(self, db):
        async with _admin_setup(db):
            summary = await agent_26.summary_for_marcos(db)
        assert "total_alerts" in summary
        assert "by_priority" in summary
        assert "by_code" in summary
        assert "top_5" in summary

    def test_draft_email_offline(self):
        alert = RetainerAlert(
            retainer_contract_id=uuid.uuid4(),
            client_name="Test Client",
            tier="R_STD",
            priority="high",
            code="A26_OVERDUE_ACTIVITIES",
            title="Test",
            description="Desc",
            suggested_action="Action",
            metadata={"overdue_count": 5},
        )
        email = draft_client_email_offline(alert)
        assert "subject" in email
        assert "body" in email
        assert "actividades" in email["body"].lower()
