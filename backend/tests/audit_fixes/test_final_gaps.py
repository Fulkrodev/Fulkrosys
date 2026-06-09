"""Tests cierre final — 11 gaps restantes (sprint 82%→100%)."""
from __future__ import annotations

import uuid

import pytest

from backend.app.database import set_tenant_context
from backend.tests.conftest import _admin_setup, setup_test_project


BASE_M16 = "/api/v1/onboarding"
BASE_M23 = "/api/v1/retainer"
BASE_M5 = "/api/v1/projects"


async def _tenant(db):
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id), project_id=uuid.UUID(project_id),
    )
    return client_id, project_id


# ══════ GAP 1: M16 → M1 export ══════

@pytest.mark.asyncio
async def test_gap1_m16_export_for_categorization_basic(async_client, db):
    _, project_id = await setup_test_project(db)
    r = await async_client.get(
        f"{BASE_M16}/projects/{project_id}/onboarding/export-categorization",
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "dimensiones_sugeridas" in data
    assert "sector" in data
    assert "sistemas" in data
    assert "servicios" in data
    # DICAT default MEDIO si no hay sector
    for dim in ("D", "I", "C", "A", "T"):
        assert data["dimensiones_sugeridas"][dim] in ("BAJO", "MEDIO", "ALTO")


def test_gap1_suggest_dicat_sector_salud():
    from backend.app.motors.m16_onboarding.api import _suggest_dicat_by_sector
    dicat = _suggest_dicat_by_sector("salud", 100, 200)
    assert dicat["C"] == "ALTO"
    assert dicat["I"] == "ALTO"


def test_gap1_suggest_dicat_sector_fintech():
    from backend.app.motors.m16_onboarding.api import _suggest_dicat_by_sector
    dicat = _suggest_dicat_by_sector("fintech", 100, 200)
    assert dicat["C"] == "ALTO"
    assert dicat["T"] == "ALTO"


# ══════ GAP 2: M23 → M15 recurring billing ══════

def test_gap2_m23_has_generate_monthly_invoice():
    from backend.app.motors.m23_retainer.retainer_service import RetainerService
    assert hasattr(RetainerService, "generate_monthly_invoice")
    assert hasattr(RetainerService, "generate_monthly_invoices_for_all")


def test_gap2_beat_schedule_has_monthly_invoices():
    from backend.app.core.celery_app import get_beat_schedule
    schedule = get_beat_schedule()
    assert "retainer-monthly-invoices" in schedule


def test_gap2_m23_task_generate_monthly_invoices():
    from backend.app.motors.m23_retainer.tasks import generate_monthly_invoices
    assert callable(generate_monthly_invoices)


@pytest.mark.asyncio
async def test_gap2_retainer_missing_data_rejected(db):
    """Retainer sin precio_mensual válido debe rechazar generate_monthly_invoice."""
    from datetime import date
    from backend.app.motors.m23_retainer.retainer_service import (
        RetainerError, RetainerService,
    )
    client_id, project_id = await _tenant(db)
    svc = RetainerService()
    r = await svc.create_retainer(
        db,
        client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
        perfil="R_STD",
        precio_mensual=0.0,  # inválido
        inicio=date.today(),
    )
    with pytest.raises(RetainerError):
        await svc.generate_monthly_invoice(db, r.id)


@pytest.mark.asyncio
async def test_gap2_retainer_monthly_invoice_happy_path(db):
    """Retainer activo con precio_mensual válido genera factura vía M15."""
    from datetime import date
    from backend.app.motors.m23_retainer.retainer_service import RetainerService
    client_id, project_id = await _tenant(db)
    svc = RetainerService()
    r = await svc.create_retainer(
        db,
        client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
        perfil="R_STD",
        precio_mensual=500.0,
        inicio=date.today(),
    )
    result = await svc.generate_monthly_invoice(db, r.id)
    assert "invoice_id" in result
    assert "numero_correlativo" in result
    assert result["total"] > 0
    assert result["perfil"] == "R_STD"


# ══════ GAP 3: M5 library 150+ ══════

def test_gap3_library_150_templates():
    from backend.app.motors.m05_obligations.library_loader import load_library
    lib = load_library()
    assert len(lib.templates) >= 150


def test_gap3_library_version_3():
    from backend.app.motors.m05_obligations.library_loader import load_library
    lib = load_library()
    assert lib.version == "3.0"


# ══════ GAP 5: M5 cliente_aporta → notificación in-portal (ADR-020 v3) ══════

@pytest.mark.asyncio
async def test_gap5_create_obligation_cliente_aporta_emits_portal_notification(
    async_client, db,
):
    """Funcional: crear obligación modo `cliente_aporta_evidencia` con un
    ClientUser activo emite una notificación in-portal `evidence_request`
    (ADR-020 v3: NO magic link cliente · in-portal target_url evidencias).

    Reescrito de grep-de-string a test funcional (Ejecutable 8 Pasada 16).
    Fuente: ADR-020 v3 + _trigger_cliente_aporta_magic_link en
    backend/app/motors/m05_obligations/api.py (emit_client_notification).
    """
    from backend.app.models.client_portal import ClientUser

    client_id, project_id = await setup_test_project(db)
    # ClientUser activo del cliente → el hook lo resuelve y notifica
    async with _admin_setup(db):
        db.add(ClientUser(
            id=uuid.uuid4(),
            client_id=uuid.UUID(client_id),
            email=f"cliente-{uuid.uuid4().hex[:8]}@example.com",
            password_hash="fake_hash",
            must_change_password=False,
        ))
        await db.flush()

    r = await async_client.post(
        f"{BASE_M5}/{project_id}/obligations",
        json={
            "titulo": "Aportar política de seguridad firmada",
            "descripcion": "El cliente debe subir la política firmada.",
            "measure_code": "org.1",
            "modo_ejecucion": "cliente_aporta_evidencia",
        },
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["modo_ejecucion"] == "cliente_aporta_evidencia"
    # Hook GAP 5 disparado → notificación in-portal presente en la respuesta
    assert data.get("magic_link") is not None, (
        "create_obligation debe emitir notificación in-portal cuando "
        "modo_ejecucion=cliente_aporta_evidencia y hay ClientUser activo"
    )
    ml = data["magic_link"]
    assert ml["type"] == "evidence_request"
    assert "/client-portal/evidencias" in ml["target_url"]
    assert f"obligation={data['id']}" in ml["target_url"]


@pytest.mark.asyncio
async def test_gap5_create_obligation_cliente_aporta_no_clientuser_best_effort(
    async_client, db,
):
    """Sin ClientUser activo, el hook degrada best-effort (None) y NO bloquea
    la creación de la obligación (status 201, sin clave magic_link)."""
    _, project_id = await setup_test_project(db)
    r = await async_client.post(
        f"{BASE_M5}/{project_id}/obligations",
        json={
            "titulo": "Obligación interna sin cliente",
            "descripcion": "Ejecuta el equipo Fulkro.",
            "measure_code": "op.exp.1",
            "modo_ejecucion": "cliente_aporta_evidencia",
        },
    )
    assert r.status_code == 201, r.text
    assert r.json().get("magic_link") is None


# ══════ GAP 6: M8 autorizacion_pentest — DEMOLIDO Sesion 7 ══════
# El test verificaba run_service.py de M8 v4.2 (multi-agente). M8 v5.1
# sustituye autorizacion_pentest por dos magic links nuevos (autorizar_
# verificacion_tecnica y autorizar_pentest_externo). El test equivalente
# vivira en backend/tests/motors/m08_verification/test_magic_links.py.


# ══════ GAP 7: M11 no lo sé (falso positivo — ya existía) ══════

def test_gap7_m11_has_not_in_corpus_detection():
    from backend.app.agents.agent_14_copiloto.service import answer_question
    # Función existe — la detección no-in-corpus está en su servicio
    assert callable(answer_question)
    from pathlib import Path
    src = Path("backend/app/agents/agent_14_copiloto/service.py").read_text()
    assert "is_not_in_corpus" in src
    assert "low_grounding" in src


# ══════ GAP 8: M12 rate limiting ══════

def test_gap8_m12_otp_failure_threshold():
    """M12 tiene OTP_FAILURE_THRESHOLD."""
    from backend.app.motors.m12_magic_link.service import OTP_FAILURE_THRESHOLD
    assert OTP_FAILURE_THRESHOLD == 3


# ══════ GAP 11: M4 → M7 Evidence query ══════

def test_gap11_m4_has_evidence_coverage_method():
    from backend.app.motors.m04_gap.service import GapAnalysisService
    assert hasattr(GapAnalysisService, "_get_evidence_coverage")


@pytest.mark.asyncio
async def test_gap11_m4_evidence_coverage_query(db):
    """_get_evidence_coverage devuelve estructura correcta con SQL real."""
    from backend.app.motors.m04_gap.service import GapAnalysisService
    _, project_id = await _tenant(db)
    svc = GapAnalysisService(db)
    cov = await svc._get_evidence_coverage(uuid.UUID(project_id), "org.1")
    assert "total" in cov
    assert "vigentes" in cov
    assert "caducadas" in cov
    assert "has_any" in cov
    assert "has_vigente" in cov
    assert cov["total"] == 0  # proyecto vacío
