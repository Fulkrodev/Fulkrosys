"""Tests Sprint C4 — M21 tablas nucleares + M21→M2."""
from __future__ import annotations

import uuid
import pytest

from backend.app.models.diagnosis import BusinessProcess, LegalObligation, Stakeholder
from backend.tests.conftest import setup_test_project


BASE = "/api/v1/diagnosis/projects"
# nota: el router M21 tiene prefix="/diagnosis"


def test_c4_three_core_tables_defined():
    assert Stakeholder.__tablename__ == "stakeholders"
    assert BusinessProcess.__tablename__ == "business_processes"
    assert LegalObligation.__tablename__ == "legal_obligations"


@pytest.mark.asyncio
async def test_c4_api_create_stakeholder(async_client, db):
    _, project_id = await setup_test_project(db)
    r = await async_client.post(
        f"{BASE}/{project_id}/diagnosis/stakeholders",
        json={
            "nombre": "Ana García",
            "cargo": "CISO",
            "poder": 5, "interes": 5, "actitud": "champion",
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["cargo"] == "CISO"


@pytest.mark.asyncio
async def test_c4_api_create_process(async_client, db):
    _, project_id = await setup_test_project(db)
    r = await async_client.post(
        f"{BASE}/{project_id}/diagnosis/processes",
        json={
            "nombre": "Gestión de pedidos",
            "criticidad": "alta",
            "rto_horas": 4, "rpo_horas": 1,
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["criticidad"] == "alta"


@pytest.mark.asyncio
async def test_c4_api_create_legal_obligation(async_client, db):
    _, project_id = await setup_test_project(db)
    r = await async_client.post(
        f"{BASE}/{project_id}/diagnosis/legal-obligations",
        json={
            "normativa": "RGPD",
            "articulo": "Art. 32",
            "alcance": "Medidas seguridad tratamiento",
            "estado": "identificada",
        },
    )
    assert r.status_code == 201, r.text


@pytest.mark.asyncio
async def test_c4_api_list_all(async_client, db):
    _, project_id = await setup_test_project(db)
    await async_client.post(
        f"{BASE}/{project_id}/diagnosis/stakeholders",
        json={"nombre": "Test"},
    )
    r = await async_client.get(f"{BASE}/{project_id}/diagnosis/stakeholders")
    assert r.status_code == 200
    assert len(r.json()["stakeholders"]) >= 1
