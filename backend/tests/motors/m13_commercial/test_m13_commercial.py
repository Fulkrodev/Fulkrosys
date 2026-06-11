"""Tests M13 Commercial Doc Factory.

Cubre:
- PricingService: cálculos deterministas por categoría
- ProposalService: ciclo draft → sent → version
- API: endpoints pricing + proposals + docx
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.app.motors.m13_commercial.pricing_service import (
    PRICING_CATALOG,
    PricingModelNotFoundError,
    PricingService,
)
from backend.tests.conftest import _admin_setup, setup_test_project


BASE = "/api/v1/commercial"


# ====================== Helpers ======================

async def _create_lead(db) -> str:
    lead_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO leads (id, empresa_nombre, estado, created_at) "
            "VALUES (:id, 'Test Lead SL', 'nuevo', now())"
        ), {"id": str(lead_id)})
    await db.flush()
    return str(lead_id)


# ====================== PricingService (unit) ======================

def test_pricing_catalog_has_5_models():
    assert len(PRICING_CATALOG) == 5
    ids = {m["id"] for m in PRICING_CATALOG}
    assert ids == {"basica_fijo", "media_hitos", "alta_fases_exito", "retainer_basico", "retainer_premium"}


def test_pricing_basica_fijo_base_without_extras():
    svc = PricingService()
    r = svc.calculate_price("basica_fijo", empleados=5, sistemas=1)
    assert r["base"] == 3200
    assert r["total"] == 3200
    assert r["iva_importe"] == 672.00
    assert r["total_con_iva"] == 3872.00
    # hitos del modelo: 30/40/30
    assert len(r["hitos"]) == 3
    assert sum(h["pct"] for h in r["hitos"]) == 100


def test_pricing_basica_fijo_with_employee_extras():
    svc = PricingService()
    r = svc.calculate_price("basica_fijo", empleados=25, sistemas=3)
    # 15 empleados extra × 80 + 1 sistema extra × 600 = 1200 + 600 = 1800 extra
    assert r["total"] == 3200 + 15 * 80 + 1 * 600
    assert any("empleados" in e["concepto"] for e in r["extras"])


def test_pricing_media_hitos_with_sector_regulado():
    svc = PricingService()
    r = svc.calculate_price(
        "media_hitos", empleados=40, sistemas=4,
        ubicaciones=2, sector_regulado=True,
    )
    # base 10700 + 15 empleados × 150 + 1 sistema × 1200 + 1 ubicacion × 1800 + 3000 sector
    assert r["total"] == 10700 + 15 * 150 + 1200 + 1800 + 3000
    assert any("sector" in e["concepto"].lower() for e in r["extras"])


def test_pricing_alta_with_cpds():
    svc = PricingService()
    r = svc.calculate_price(
        "alta_fases_exito", empleados=50, sistemas=5,
        ubicaciones=1, cpds=2,
    )
    # base 22800 + 0 empleados (=50 threshold) + 0 sistemas (=5) + 2 cpds × 4500 = 9000
    assert r["total"] == 22800 + 9000


def test_pricing_retainer_monthly_multi_month():
    svc = PricingService()
    r = svc.calculate_price("retainer_basico", sistemas=3, meses_retainer=6)
    # 700/mes × 6 + 2 sistemas extras × 50 × 6 = 4200 + 600 = 4800
    assert r["total"] == 4800


def test_pricing_invalid_model_raises():
    with pytest.raises(PricingModelNotFoundError):
        PricingService().get_model("inexistente")


def test_get_models_for_categoria_media():
    svc = PricingService()
    models = svc.get_models_for_categoria("MEDIA")
    ids = {m["id"] for m in models}
    assert "media_hitos" in ids
    assert "retainer_basico" in ids or "retainer_premium" in ids


# ====================== API pricing ======================

@pytest.mark.asyncio
@pytest.mark.skip(reason="API comercial m13 (pricing/proposals) no montada en Batch 2 · router comercial dormido")
async def test_api_list_pricing_models(async_client):
    r = await async_client.get(f"{BASE}/pricing-models")
    assert r.status_code == 200
    data = r.json()
    assert len(data["models"]) == 5


@pytest.mark.asyncio
@pytest.mark.skip(reason="API comercial m13 (pricing/proposals) no montada en Batch 2 · router comercial dormido")
async def test_api_list_pricing_models_filtered_by_categoria(async_client):
    r = await async_client.get(f"{BASE}/pricing-models?categoria=ALTA")
    assert r.status_code == 200
    data = r.json()
    ids = {m["id"] for m in data["models"]}
    assert "alta_fases_exito" in ids


@pytest.mark.asyncio
@pytest.mark.skip(reason="API comercial m13 (pricing/proposals) no montada en Batch 2 · router comercial dormido")
async def test_api_calculate_price_endpoint(async_client):
    r = await async_client.post(
        f"{BASE}/pricing-models/media_hitos/calculate",
        json={"empleados": 30, "sistemas": 4, "sector_regulado": True},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["model_id"] == "media_hitos"
    assert data["total"] > 22000
    assert data["iva_percent"] == 21.0


# ====================== API proposals ======================

@pytest.mark.asyncio
@pytest.mark.skip(reason="API comercial m13 (pricing/proposals) no montada en Batch 2 · router comercial dormido")
async def test_api_generate_proposal_creates_draft(async_client, db):
    _, project_id = await setup_test_project(db)
    lead_id = await _create_lead(db)
    r = await async_client.post(
        f"{BASE}/projects/{project_id}/proposals/generate",
        json={
            "lead_id": lead_id,
            "pricing_model_id": "media_hitos",
            "categoria": "MEDIA",
            "empleados": 40,
            "sistemas": 4,
        },
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["estado"] == "draft"
    assert data["pricing_model_id"] == "media_hitos"
    assert data["importe_total"] > 0
    assert data["duracion_semanas"] is not None
    assert data["hitos_pago"] is not None


@pytest.mark.asyncio
@pytest.mark.skip(reason="API comercial m13 (pricing/proposals) no montada en Batch 2 · router comercial dormido")
async def test_api_send_proposal_updates_status(async_client, db):
    _, project_id = await setup_test_project(db)
    lead_id = await _create_lead(db)
    r = await async_client.post(
        f"{BASE}/projects/{project_id}/proposals/generate",
        json={"lead_id": lead_id, "pricing_model_id": "basica_fijo", "categoria": "BASICA"},
    )
    pid = r.json()["id"]

    r2 = await async_client.post(f"{BASE}/projects/{project_id}/proposals/{pid}/send")
    assert r2.status_code == 200, r2.text
    data = r2.json()
    assert data["estado"] == "sent"
    assert data["enviado_at"] is not None


@pytest.mark.asyncio
@pytest.mark.skip(reason="API comercial m13 (pricing/proposals) no montada en Batch 2 · router comercial dormido")
async def test_api_create_version_increments(async_client, db):
    _, project_id = await setup_test_project(db)
    lead_id = await _create_lead(db)
    r = await async_client.post(
        f"{BASE}/projects/{project_id}/proposals/generate",
        json={"lead_id": lead_id, "pricing_model_id": "basica_fijo", "categoria": "BASICA"},
    )
    pid = r.json()["id"]

    r2 = await async_client.post(
        f"{BASE}/projects/{project_id}/proposals/{pid}/version",
        json={"importe_total": 8500, "notas_marcos": "Ajuste negociación"},
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["version"] == 2
    assert r2.json()["importe_total"] == 8500


@pytest.mark.asyncio
@pytest.mark.skip(reason="API comercial m13 (pricing/proposals) no montada en Batch 2 · router comercial dormido")
async def test_api_download_docx_returns_docx_bytes(async_client, db):
    _, project_id = await setup_test_project(db)
    lead_id = await _create_lead(db)
    r = await async_client.post(
        f"{BASE}/projects/{project_id}/proposals/generate",
        json={"lead_id": lead_id, "pricing_model_id": "basica_fijo", "categoria": "BASICA"},
    )
    pid = r.json()["id"]

    r2 = await async_client.get(f"{BASE}/projects/{project_id}/proposals/{pid}/docx")
    assert r2.status_code == 200
    assert "wordprocessingml" in r2.headers["content-type"]
    # PK signature of a zip/docx
    assert r2.content[:2] == b"PK"
    assert len(r2.content) > 1000
