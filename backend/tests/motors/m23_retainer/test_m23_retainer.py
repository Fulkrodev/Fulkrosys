"""Tests M23 Retainer Management Engine.

Cubre:
- 4 perfiles (R_LITE/R_STD/R_PLUS/R_CRITICAL) con SLAs distintos
- Activities generadas según cadencias del perfil
- Renewal clock (7 estados)
- Drift detector (10 dimensions × 4 severities)
- RAG calculator
- Dashboard multi-cliente (bypass RLS)
- API
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import text

from backend.app.database import set_tenant_context
from backend.app.motors.m23_retainer.retainer_service import (
    CADENCES_BY_PROFILE,
    DRIFT_DIMENSIONS,
    DRIFT_IMPACTS,
    DRIFT_SEVERITIES,
    HOURS_BY_PROFILE,
    SLA_BY_PROFILE,
    VALID_PROFILES,
    RetainerError,
    RetainerService,
)
from backend.tests.conftest import _admin_setup, setup_test_project


BASE = "/api/v1/retainer"


# ─────────── Helpers ───────────

async def _setup_tenant(db):
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db,
        client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
    )
    return client_id, project_id


async def _create_retainer(db, client_id: str, project_id: str, perfil: str = "R_STD"):
    return await RetainerService().create_retainer(
        db,
        client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
        perfil=perfil,
        precio_mensual=1000.0,
        inicio=date.today(),
    )


# ─────────── Catálogo ───────────

def test_five_profiles_exist():
    # Sesion 8 Paso 2: R_MICRO (150 EUR) anadido como 4o tier de la
    # imagen pricing 2026-04-21. R_CRITICAL se mantiene como legacy.
    assert VALID_PROFILES == (
        "R_MICRO", "R_LITE", "R_STD", "R_PLUS", "R_CRITICAL",
    )


def test_profiles_have_distinct_slas():
    assert SLA_BY_PROFILE["R_MICRO"] == 120
    assert SLA_BY_PROFILE["R_LITE"] == 72
    assert SLA_BY_PROFILE["R_STD"] == 48
    assert SLA_BY_PROFILE["R_PLUS"] == 24
    assert SLA_BY_PROFILE["R_CRITICAL"] == 8


def test_profiles_have_distinct_hours():
    assert HOURS_BY_PROFILE["R_MICRO"] < HOURS_BY_PROFILE["R_LITE"]
    assert HOURS_BY_PROFILE["R_LITE"] < HOURS_BY_PROFILE["R_STD"]
    assert HOURS_BY_PROFILE["R_STD"] < HOURS_BY_PROFILE["R_PLUS"]
    assert HOURS_BY_PROFILE["R_PLUS"] < HOURS_BY_PROFILE["R_CRITICAL"]


def test_cadences_have_activity_types_per_profile():
    # R_MICRO tiene 9 activity types (sin auditoria_interna); resto 10.
    expected_min = {"R_MICRO": 9}
    for p in VALID_PROFILES:
        minimum = expected_min.get(p, 10)
        assert len(CADENCES_BY_PROFILE[p]) >= minimum, (
            f"{p} tiene {len(CADENCES_BY_PROFILE[p])}, minimo {minimum}"
        )


def test_drift_catalog_10_dimensions_4_severities():
    assert len(DRIFT_DIMENSIONS) == 10
    assert len(DRIFT_SEVERITIES) == 4
    assert len(DRIFT_IMPACTS) == 5


# ─────────── Lifecycle ───────────

@pytest.mark.asyncio
async def test_create_retainer_r_std(db):
    client_id, project_id = await _setup_tenant(db)
    r = await _create_retainer(db, client_id, project_id, "R_STD")
    assert r.perfil == "R_STD"
    assert r.sla_respuesta_horas == 48
    assert r.horas_previstas_anual == 40.0
    assert r.estado == "active"
    assert r.rag_status == "green"


@pytest.mark.asyncio
async def test_create_retainer_r_critical_sla_8h(db):
    client_id, project_id = await _setup_tenant(db)
    r = await _create_retainer(db, client_id, project_id, "R_CRITICAL")
    assert r.perfil == "R_CRITICAL"
    assert r.sla_respuesta_horas == 8
    assert r.horas_previstas_anual == 150.0


@pytest.mark.asyncio
async def test_create_retainer_invalid_profile(db):
    client_id, project_id = await _setup_tenant(db)
    with pytest.raises(RetainerError):
        await _create_retainer(db, client_id, project_id, "R_INVALID")


@pytest.mark.asyncio
async def test_update_profile_recalculates_sla(db):
    client_id, project_id = await _setup_tenant(db)
    r = await _create_retainer(db, client_id, project_id, "R_STD")
    updated = await RetainerService().update_retainer_profile(db, r.id, "R_PLUS")
    assert updated.perfil == "R_PLUS"
    assert updated.sla_respuesta_horas == 24
    assert updated.horas_previstas_anual == 80.0


@pytest.mark.asyncio
async def test_pause_and_cancel(db):
    client_id, project_id = await _setup_tenant(db)
    r = await _create_retainer(db, client_id, project_id)
    paused = await RetainerService().pause_retainer(db, r.id)
    assert paused.estado == "paused"
    cancelled = await RetainerService().cancel_retainer(db, r.id)
    assert cancelled.estado == "cancelled"


# ─────────── Activities ───────────

@pytest.mark.asyncio
async def test_generate_annual_activities_r_std(db):
    client_id, project_id = await _setup_tenant(db)
    r = await _create_retainer(db, client_id, project_id, "R_STD")
    activities = await RetainerService().generate_annual_activities(db, r.id, 2026)
    assert len(activities) > 0
    # R_STD: comite trimestral (4) + trimestral (4) + privilegios trimestral (4) +
    # semestral (2) + semanal-representado-mensual (12) + simulacro semestral (2)
    # + anuales (4x1=4) = 4+4+4+2+12+2+4 = 32 aprox
    tipos = {a.tipo_actividad for a in activities}
    assert "comite_seguridad" in tipos
    assert "auditoria_interna" in tipos
    assert "formacion_anual" in tipos


@pytest.mark.asyncio
async def test_r_lite_generates_fewer_than_r_plus(db):
    client_id, project_id = await _setup_tenant(db)
    r_lite = await _create_retainer(db, client_id, project_id, "R_LITE")
    lite_acts = await RetainerService().generate_annual_activities(db, r_lite.id, 2026)

    # Limpiar y crear R_PLUS
    async with _admin_setup(db):
        await db.execute(text("DELETE FROM retainer_activities"))
        await db.execute(text("DELETE FROM retainer_contracts WHERE id = :id"),
                         {"id": str(r_lite.id)})
    await db.flush()

    r_plus = await _create_retainer(db, client_id, project_id, "R_PLUS")
    plus_acts = await RetainerService().generate_annual_activities(db, r_plus.id, 2026)
    assert len(plus_acts) > len(lite_acts)


@pytest.mark.asyncio
async def test_start_activity(db):
    client_id, project_id = await _setup_tenant(db)
    r = await _create_retainer(db, client_id, project_id)
    acts = await RetainerService().generate_annual_activities(db, r.id, 2026)
    a = acts[0]
    started = await RetainerService().start_activity(db, a.id)
    assert started.estado == "en_curso"


@pytest.mark.asyncio
async def test_complete_activity_sums_hours(db):
    client_id, project_id = await _setup_tenant(db)
    r = await _create_retainer(db, client_id, project_id)
    acts = await RetainerService().generate_annual_activities(db, r.id, 2026)
    a = acts[0]
    await RetainerService().start_activity(db, a.id)
    completed = await RetainerService().complete_activity(
        db, a.id, horas_consumidas=3.5, resultado="OK",
    )
    assert completed.estado == "completada"
    assert completed.horas_consumidas == 3.5
    # Retainer debe haber sumado
    r_updated = await RetainerService().get_retainer(db, r.id)
    assert r_updated.horas_consumidas_total == 3.5


@pytest.mark.asyncio
async def test_overdue_activities(db):
    client_id, project_id = await _setup_tenant(db)
    r = await _create_retainer(db, client_id, project_id)
    # Crear actividad con fecha pasada
    from backend.app.models.retainer import RetainerActivity
    past_date = date.today() - timedelta(days=30)
    act = RetainerActivity(
        retainer_contract_id=r.id,
        project_id=uuid.UUID(project_id),
        tipo_actividad="auditoria_interna",
        titulo="Vencida",
        fecha_programada=past_date,
        estado="programada",
        horas_estimadas=4.0,
    )
    db.add(act)
    await db.flush()

    overdue = await RetainerService().get_overdue_activities(db, r.id)
    assert len(overdue) == 1
    assert overdue[0].id == act.id


# ─────────── Renewal clock ───────────

def test_renewal_status_none_when_far():
    assert RetainerService._renewal_status_from_days(200) is None


def test_renewal_status_t_minus_180():
    assert RetainerService._renewal_status_from_days(150) == "T_MINUS_180"


def test_renewal_status_t_minus_120():
    assert RetainerService._renewal_status_from_days(100) == "T_MINUS_120"


def test_renewal_status_t_minus_90():
    assert RetainerService._renewal_status_from_days(75) == "T_MINUS_90"


def test_renewal_status_t_minus_60():
    assert RetainerService._renewal_status_from_days(50) == "T_MINUS_60"


def test_renewal_status_t_minus_30():
    assert RetainerService._renewal_status_from_days(20) == "T_MINUS_30"


def test_renewal_lapsed_when_past():
    assert RetainerService._renewal_status_from_days(0) == "LAPSED"
    assert RetainerService._renewal_status_from_days(-10) == "LAPSED"


@pytest.mark.asyncio
async def test_update_renewal_status_from_db(db):
    client_id, project_id = await _setup_tenant(db)
    r = await RetainerService().create_retainer(
        db,
        client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
        perfil="R_STD", precio_mensual=1000.0,
        inicio=date.today(),
        next_renewal_date=date.today() + timedelta(days=45),
    )
    updated = await RetainerService().update_renewal_status(db, r.id)
    assert updated.renewal_status == "T_MINUS_60"


@pytest.mark.asyncio
async def test_mark_renewed_sets_status_and_new_date(db):
    client_id, project_id = await _setup_tenant(db)
    r = await _create_retainer(db, client_id, project_id)
    new_date = date.today() + timedelta(days=730)
    renewed = await RetainerService().mark_renewed(db, r.id, new_date)
    assert renewed.renewal_status == "RENEWED"
    assert renewed.next_renewal_date == new_date


# ─────────── Drift ───────────

@pytest.mark.asyncio
async def test_register_drift_critical_sets_rag_red(db):
    client_id, project_id = await _setup_tenant(db)
    r = await _create_retainer(db, client_id, project_id)
    assert r.rag_status == "green"
    await RetainerService().register_drift(
        db, retainer_id=r.id, project_id=uuid.UUID(project_id),
        dimension="identidad",
        descripcion="MFA dropped 40% coverage",
        severidad="CRITICAL", impacto="CONTROL",
    )
    r_updated = await RetainerService().get_retainer(db, r.id)
    assert r_updated.rag_status == "red"


@pytest.mark.asyncio
async def test_register_drift_invalid_dimension(db):
    client_id, project_id = await _setup_tenant(db)
    r = await _create_retainer(db, client_id, project_id)
    with pytest.raises(RetainerError):
        await RetainerService().register_drift(
            db, retainer_id=r.id, project_id=uuid.UUID(project_id),
            dimension="invalid_dim",
            descripcion="x", severidad="HIGH", impacto="CONTROL",
        )


@pytest.mark.asyncio
async def test_list_drifts_filter_severidad(db):
    client_id, project_id = await _setup_tenant(db)
    r = await _create_retainer(db, client_id, project_id)
    await RetainerService().register_drift(
        db, retainer_id=r.id, project_id=uuid.UUID(project_id),
        dimension="normativa", descripcion="X",
        severidad="LOW", impacto="DOCUMENT",
    )
    await RetainerService().register_drift(
        db, retainer_id=r.id, project_id=uuid.UUID(project_id),
        dimension="evidencias", descripcion="Y",
        severidad="HIGH", impacto="EVIDENCE",
    )
    highs = await RetainerService().list_drifts(
        db, retainer_id=r.id, severidad="HIGH",
    )
    assert len(highs) == 1
    assert highs[0].severidad == "HIGH"


@pytest.mark.asyncio
async def test_resolve_drift(db):
    client_id, project_id = await _setup_tenant(db)
    r = await _create_retainer(db, client_id, project_id)
    d = await RetainerService().register_drift(
        db, retainer_id=r.id, project_id=uuid.UUID(project_id),
        dimension="roles", descripcion="X",
        severidad="MEDIUM", impacto="ROUTE",
    )
    resolved = await RetainerService().resolve_drift(db, d.id)
    assert resolved.estado == "resolved"
    assert resolved.resuelto_at is not None


# ─────────── RAG calculator ───────────

@pytest.mark.asyncio
async def test_rag_green_no_issues(db):
    client_id, project_id = await _setup_tenant(db)
    r = await _create_retainer(db, client_id, project_id)
    rag = await RetainerService().calculate_rag(db, r.id)
    assert rag == "green"


@pytest.mark.asyncio
async def test_rag_red_critical_drift(db):
    client_id, project_id = await _setup_tenant(db)
    r = await _create_retainer(db, client_id, project_id)
    await RetainerService().register_drift(
        db, retainer_id=r.id, project_id=uuid.UUID(project_id),
        dimension="continuidad", descripcion="Backup falló",
        severidad="CRITICAL", impacto="AUDIT",
    )
    rag = await RetainerService().calculate_rag(db, r.id)
    assert rag == "red"


@pytest.mark.asyncio
async def test_rag_amber_when_high_drift(db):
    client_id, project_id = await _setup_tenant(db)
    r = await _create_retainer(db, client_id, project_id)
    await RetainerService().register_drift(
        db, retainer_id=r.id, project_id=uuid.UUID(project_id),
        dimension="overlay", descripcion="Drift HIGH",
        severidad="HIGH", impacto="CONTROL",
    )
    rag = await RetainerService().calculate_rag(db, r.id)
    assert rag == "amber"


# ─────────── Dashboard (sin RLS) ───────────

@pytest.mark.asyncio
async def test_dashboard_returns_structure(db):
    client_id, project_id = await _setup_tenant(db)
    await _create_retainer(db, client_id, project_id, "R_STD")
    dashboard = await RetainerService().get_dashboard(db)
    assert "total_clientes" in dashboard
    assert "green" in dashboard
    assert "amber" in dashboard
    assert "red" in dashboard
    assert "clientes" in dashboard
    assert "mes_actual" in dashboard
    assert dashboard["total_clientes"] >= 1


# ─────────── API ───────────

@pytest.mark.asyncio
async def test_api_list_profiles(async_client):
    r = await async_client.get(f"{BASE}/profiles")
    assert r.status_code == 200
    profiles = r.json()["profiles"]
    # Sesion 8 Paso 2: 5 tiers (R_MICRO + R_LITE + R_STD + R_PLUS + R_CRITICAL)
    assert len(profiles) == 5
    codigos = {p["codigo"] for p in profiles}
    assert "R_MICRO" in codigos


@pytest.mark.asyncio
async def test_api_profile_cadences(async_client):
    r = await async_client.get(f"{BASE}/profiles/R_STD/cadences")
    assert r.status_code == 200
    data = r.json()
    assert data["profile"] == "R_STD"
    assert data["sla_respuesta_horas"] == 48


@pytest.mark.asyncio
async def test_api_drift_catalog(async_client):
    r = await async_client.get(f"{BASE}/drift-catalog")
    assert r.status_code == 200
    data = r.json()
    assert len(data["dimensions"]) == 10
    assert len(data["severities"]) == 4


@pytest.mark.asyncio
async def test_api_create_retainer(async_client, db):
    client_id, project_id = await setup_test_project(db)
    r = await async_client.post(
        f"{BASE}/projects/{project_id}/retainer",
        json={
            "client_id": client_id,
            "perfil": "R_STD",
            "precio_mensual": 800.0,
            "inicio": date.today().isoformat(),
        },
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["perfil"] == "R_STD"
    assert data["sla_respuesta_horas"] == 48


@pytest.mark.asyncio
async def test_api_generate_activities(async_client, db):
    client_id, project_id = await setup_test_project(db)
    await async_client.post(
        f"{BASE}/projects/{project_id}/retainer",
        json={
            "client_id": client_id, "perfil": "R_STD",
            "precio_mensual": 800.0, "inicio": date.today().isoformat(),
        },
    )
    r = await async_client.post(
        f"{BASE}/projects/{project_id}/retainer/activities/generate",
        json={"year": 2026},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["year"] == 2026
    assert data["count"] > 0


@pytest.mark.asyncio
async def test_api_dashboard(async_client, db):
    # setup: crear 2 retainers en 2 proyectos
    c1, p1 = await setup_test_project(db)
    r = await async_client.post(
        f"{BASE}/projects/{p1}/retainer",
        json={
            "client_id": c1, "perfil": "R_STD",
            "precio_mensual": 800.0, "inicio": date.today().isoformat(),
        },
    )
    assert r.status_code == 201

    r2 = await async_client.get(f"{BASE}/dashboard")
    assert r2.status_code == 200
    data = r2.json()
    assert "total_clientes" in data
    assert data["total_clientes"] >= 1
