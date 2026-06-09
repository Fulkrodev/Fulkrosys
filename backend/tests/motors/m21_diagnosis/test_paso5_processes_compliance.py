"""Tests M21 Paso 5 — Processes sector templates + BIA feed + cross
compliance RGPD/NIS2/DORA/AI Act/ENI."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text as sa_text

from backend.app.database import set_tenant_context
from backend.app.models.diagnosis import BusinessProcess, LegalObligation
from backend.app.motors.m21_diagnosis.cross_compliance_service import (
    ALL_RULES, ComplianceContext, build_summary, context_from_hints,
    detect_obligations, persist_obligations,
)
from backend.app.motors.m21_diagnosis.m1_m2_feeds import (
    suggest_category, suggest_magerit_assets,
)
from backend.app.motors.m21_diagnosis.paso5_orchestrator import (
    build_e090_context, run_full_diagnosis_paso5,
)
from backend.app.motors.m21_diagnosis.processes_service import (
    SECTOR_TEMPLATES, feed_bia, load_sector_template, seed_sector_processes,
)
from backend.tests.conftest import _admin_setup, setup_test_project


async def _set_tenant(db, project_id):
    client_id = (await db.execute(
        sa_text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)},
    )).scalar()
    await set_tenant_context(
        db, client_id=client_id,
        project_id=uuid.UUID(project_id) if isinstance(project_id, str) else project_id,
    )


# ════════════════════════════════════════════════════════════════════
# Processes — sector templates
# ════════════════════════════════════════════════════════════════════

class TestSectorTemplates:
    def test_six_sectors_defined(self):
        expected = {
            "sanidad_privada", "fintech", "servicios_profesionales",
            "industria", "educacion_privada", "administracion_publica",
        }
        assert expected.issubset(set(SECTOR_TEMPLATES.keys()))

    def test_each_sector_has_ten_processes(self):
        for sector, processes in SECTOR_TEMPLATES.items():
            assert len(processes) >= 10, f"{sector} tiene {len(processes)}"

    def test_sanidad_includes_historia_clinica(self):
        names = {p.nombre for p in SECTOR_TEMPLATES["sanidad_privada"]}
        assert any("historia clinica" in n.lower() for n in names)

    def test_fintech_includes_kyc_and_dora(self):
        names = {p.nombre for p in SECTOR_TEMPLATES["fintech"]}
        assert any("KYC" in n for n in names)
        assert any("DORA" in n for n in names)

    def test_aliases_resolve_to_full_name(self):
        templates = load_sector_template("sanidad")
        assert len(templates) >= 10


class TestSeedAndBia:
    @pytest.mark.asyncio
    async def test_seed_persists_processes(self, db):
        _, project_id = await setup_test_project(db)
        await _set_tenant(db, project_id)
        async with _admin_setup(db):
            created = await seed_sector_processes(
                db, uuid.UUID(project_id), "sanidad_privada",
            )
        assert len(created) == 10
        # Re-seed con skip_existing no duplica
        async with _admin_setup(db):
            created2 = await seed_sector_processes(
                db, uuid.UUID(project_id), "sanidad_privada",
            )
        assert created2 == []

    @pytest.mark.asyncio
    async def test_feed_bia_returns_structured_result(self, db):
        _, project_id = await setup_test_project(db)
        await _set_tenant(db, project_id)
        async with _admin_setup(db):
            await seed_sector_processes(
                db, uuid.UUID(project_id), "fintech",
            )
        bia = await feed_bia(db, uuid.UUID(project_id))
        assert bia["total_procesos"] == 10
        assert "por_criticidad" in bia
        assert "alta" in bia["por_criticidad"]
        assert bia["rto_objetivo_horas"] >= 0
        assert bia["recomendacion"] in (
            "alta_disponibilidad", "continuidad_estandar",
            "continuidad_basica",
        )


# ════════════════════════════════════════════════════════════════════
# Cross compliance rules
# ════════════════════════════════════════════════════════════════════

class TestCrossCompliance:
    def test_rgpd_always_applies_with_personal_data(self):
        ctx = ComplianceContext(sector="servicios", empleados=20)
        obs = detect_obligations(ctx)
        assert any(o.norma == "RGPD" for o in obs)
        # DPO NO obligatorio (20 empleados, no sensibles)
        assert not any(
            "Designar Delegado" in o.obligacion and o.norma == "RGPD"
            for o in obs
        )

    def test_rgpd_dpo_required_over_250_employees(self):
        ctx = ComplianceContext(sector="servicios", empleados=300)
        obs = detect_obligations(ctx)
        assert any(
            "Designar Delegado" in o.obligacion for o in obs
        )

    def test_rgpd_dpo_required_if_sensibles(self):
        ctx = ComplianceContext(
            sector="sanidad", empleados=20, maneja_datos_sensibles=True,
        )
        obs = detect_obligations(ctx)
        assert any("Designar Delegado" in o.obligacion for o in obs)
        assert any("EIPD" in o.obligacion for o in obs)

    def test_nis2_esencial_applies(self):
        ctx = ComplianceContext(
            sector="sanidad_privada", empleados=100,
            es_sector_esencial_nis2=True,
        )
        obs = detect_obligations(ctx)
        nis2_obligaciones = [o for o in obs if o.norma == "NIS2"]
        assert len(nis2_obligaciones) == 3
        assert any("esencial" in o.obligacion for o in nis2_obligaciones)

    def test_dora_applies_for_financial_entity(self):
        ctx = ComplianceContext(
            sector="fintech", empleados=50,
            es_entidad_financiera_ue=True,
        )
        obs = detect_obligations(ctx)
        dora_obs = [o for o in obs if o.norma == "DORA"]
        assert len(dora_obs) == 3

    def test_ai_act_applies_when_flag_set(self):
        ctx = ComplianceContext(
            sector="servicios", empleados=50,
            tiene_sistemas_ia_alto_riesgo=True,
        )
        obs = detect_obligations(ctx)
        assert any(o.norma == "AI Act" for o in obs)

    def test_eni_applies_for_admin_publica(self):
        ctx = ComplianceContext(
            sector="administracion_publica", empleados=200,
            es_administracion_publica=True,
        )
        obs = detect_obligations(ctx)
        assert any(o.norma == "ENI" for o in obs)

    def test_iso27001_always_sugerida(self):
        ctx = ComplianceContext(sector="servicios", empleados=10)
        obs = detect_obligations(ctx)
        assert any(o.norma == "ISO 27001" for o in obs)

    def test_context_from_hints_sanidad_sensibles(self):
        ctx = context_from_hints("sanidad_privada", empleados=120)
        assert ctx.maneja_datos_sensibles is True
        assert ctx.es_sector_esencial_nis2 is True

    @pytest.mark.asyncio
    async def test_persist_obligations_saves_rows(self, db):
        _, project_id = await setup_test_project(db)
        await _set_tenant(db, project_id)
        ctx = context_from_hints("sanidad_privada", empleados=300)
        async with _admin_setup(db):
            created = await persist_obligations(
                db, uuid.UUID(project_id), ctx,
            )
        assert len(created) >= 6
        normativas = {o.normativa for o in created}
        assert "RGPD" in normativas
        assert "NIS2" in normativas

    @pytest.mark.asyncio
    async def test_persist_obligations_idempotent(self, db):
        _, project_id = await setup_test_project(db)
        await _set_tenant(db, project_id)
        ctx = context_from_hints("servicios_profesionales", empleados=20)
        async with _admin_setup(db):
            first = await persist_obligations(
                db, uuid.UUID(project_id), ctx,
            )
            second = await persist_obligations(
                db, uuid.UUID(project_id), ctx,
            )
        assert len(first) > 0
        assert second == []


# ════════════════════════════════════════════════════════════════════
# M1 + M2 feeds
# ════════════════════════════════════════════════════════════════════

class TestFeedsM1M2:
    @pytest.mark.asyncio
    async def test_m1_suggest_empty_project_is_basica(self, db):
        _, project_id = await setup_test_project(db)
        await _set_tenant(db, project_id)
        hint = await suggest_category(db, uuid.UUID(project_id))
        assert hint["categoria_sugerida"] == "BASICA"

    @pytest.mark.asyncio
    async def test_m1_suggest_goes_up_with_obligations(self, db):
        _, project_id = await setup_test_project(db)
        await _set_tenant(db, project_id)
        ctx = context_from_hints("sanidad_privada", empleados=400)
        async with _admin_setup(db):
            await persist_obligations(db, uuid.UUID(project_id), ctx)
            await seed_sector_processes(
                db, uuid.UUID(project_id), "sanidad_privada",
            )
        hint = await suggest_category(db, uuid.UUID(project_id))
        assert hint["categoria_sugerida"] in ("MEDIA", "ALTA")
        assert hint["score_obligaciones"] > 0

    @pytest.mark.asyncio
    async def test_m2_suggest_assets_from_processes(self, db):
        _, project_id = await setup_test_project(db)
        await _set_tenant(db, project_id)
        async with _admin_setup(db):
            await seed_sector_processes(
                db, uuid.UUID(project_id), "sanidad_privada",
            )
        assets = await suggest_magerit_assets(db, uuid.UUID(project_id))
        assert len(assets) > 10
        types = {a["asset_type_code"] for a in assets}
        assert "S" in types  # Servicios
        assert "D" in types  # Datos
        assert "SW" in types  # Software de sistemas


# ════════════════════════════════════════════════════════════════════
# Orchestrator + E-090 context
# ════════════════════════════════════════════════════════════════════

class TestOrchestrator:
    @pytest.mark.asyncio
    async def test_full_diagnosis_returns_expected_keys(self, db):
        _, project_id = await setup_test_project(db)
        await _set_tenant(db, project_id)
        async with _admin_setup(db):
            result = await run_full_diagnosis_paso5(
                db, uuid.UUID(project_id), sector="sanidad_privada",
                empleados=400,
            )
        assert "bia" in result
        assert "compliance" in result
        assert "stakeholders" in result
        assert "m1_category_hint" in result
        assert "m2_assets_hint" in result

    def test_build_e090_context_structure(self):
        sample = {
            "generated_at": "2026-04-21T00:00:00Z",
            "sector": "sanidad_privada",
            "bia": {
                "total_procesos": 10,
                "rto_objetivo_horas": 4,
                "rpo_objetivo_horas": 1,
                "recomendacion": "alta_disponibilidad",
                "por_criticidad": {"alta": [], "media": [], "baja": []},
            },
            "compliance": {
                "total_obligaciones": 6,
                "por_norma": {"RGPD": [], "NIS2": []},
                "flags": {"dpo_obligatorio": True},
            },
            "stakeholders": {
                "total_personas": 4,
                "ens_responsibles": {
                    "coverage_pct": 100.0, "missing": [],
                },
                "conflictos": [],
            },
            "m1_category_hint": {
                "categoria_sugerida": "MEDIA",
                "justificacion": "...",
            },
            "m2_assets_hint": [{"code": "SRV-X"}],
        }
        ctx = build_e090_context(
            sample,
            cliente={"razon_social": "Test SL"},
            proyecto={"nombre": "p1"},
        )
        assert ctx["diagnostico"]["categoria_sugerida"] == "MEDIA"
        assert ctx["diagnostico"]["total_obligaciones"] == 6
        assert ctx["diagnostico"]["assets_sugeridos_m2"] == 1
        assert len(ctx["recomendaciones_fase2"]) >= 3
