"""Tests classifier 6 arquetipos PYME (SAN-C MB-11.6).

Cobertura 7 cases (6 formales + GENERICO fallback) + workflow adjustments.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from backend.app.motors.m01_categorization.pyme_archetypes import (
    PymeArquetipo,
    archetype_workflow_adjustments,
    classify_archetype,
)


def test_enum_has_8_values():
    """6 arquetipos formales + AUTONOMO_INDIVIDUAL (L-4 · FRENTE L) + GENERICO."""
    assert len(PymeArquetipo) == 8
    assert PymeArquetipo.AUTONOMO_INDIVIDUAL.value == "autonomo_individual"


@pytest.mark.parametrize(
    "data, expected_arq, min_confidence",
    [
        ({"cnae_code": "8610"}, PymeArquetipo.SECTOR_SALUD, "0.95"),
        ({"sector": "Sanidad privada"}, PymeArquetipo.SECTOR_SALUD, "0.95"),
        ({"cnae_code": "8520"}, PymeArquetipo.SECTOR_EDUCACION, "0.95"),
        ({"sector": "Universidad pública"}, PymeArquetipo.SECTOR_EDUCACION, "0.95"),
        ({"cnae_code": "6420"}, PymeArquetipo.PROVEEDOR_FINANCIERO, "0.90"),
        ({"sector": "Banca minorista"}, PymeArquetipo.PROVEEDOR_FINANCIERO, "0.90"),
        ({"is_aapp_developer": True}, PymeArquetipo.DESARROLLADOR_AAPP, "0.85"),
        ({"infrastructure_type": "saas_only"}, PymeArquetipo.SAAS_ONLY, "0.85"),
        ({"workforce_type": "fully_remote"}, PymeArquetipo.TELETRABAJO_TOTAL, "0.80"),
        ({}, PymeArquetipo.GENERICO, "0.50"),
        ({"cnae_code": "9999", "sector": "otro"}, PymeArquetipo.GENERICO, "0.50"),
    ],
)
def test_classify_returns_expected_archetype(data, expected_arq, min_confidence):
    result = classify_archetype(data)
    assert result.arquetipo == expected_arq
    assert result.confidence >= Decimal(min_confidence)
    assert isinstance(result.reasoning_path, list)
    assert len(result.reasoning_path) >= 1


def test_classify_priority_cnae_over_infra():
    """CNAE salud gana sobre infrastructure_type=saas_only."""
    result = classify_archetype({
        "cnae_code": "8610",
        "infrastructure_type": "saas_only",
    })
    assert result.arquetipo == PymeArquetipo.SECTOR_SALUD


def test_classify_priority_aapp_over_infra():
    """is_aapp_developer flag gana sobre saas_only."""
    result = classify_archetype({
        "is_aapp_developer": True,
        "infrastructure_type": "saas_only",
    })
    assert result.arquetipo == PymeArquetipo.DESARROLLADOR_AAPP


def test_classify_reasoning_path_explains_decision():
    result = classify_archetype({"cnae_code": "8610"})
    assert any("salud" in step.lower() for step in result.reasoning_path)


@pytest.mark.parametrize("arq", list(PymeArquetipo))
def test_workflow_adjustments_returns_dict_per_archetype(arq):
    adj = archetype_workflow_adjustments(arq)
    assert isinstance(adj, dict)
    assert "skip_marcos" in adj
    assert "highlight_marcos" in adj
    assert "notes" in adj
    assert isinstance(adj["skip_marcos"], list)
    assert isinstance(adj["highlight_marcos"], list)


def test_adjustments_specific_per_archetype():
    """Spot-check adjustments espera per-archetype."""
    salud = archetype_workflow_adjustments(PymeArquetipo.SECTOR_SALUD)
    assert "art.9" in salud["notes"] or "Alta" in salud["notes"]

    saas = archetype_workflow_adjustments(PymeArquetipo.SAAS_ONLY)
    assert "mp.if" in saas["skip_marcos"]

    teletrabajo = archetype_workflow_adjustments(PymeArquetipo.TELETRABAJO_TOTAL)
    assert "MFA" in teletrabajo["notes"] or "VPN" in teletrabajo["notes"]


# ================================================================
# HTTP API Integration tests (POST classify + GET archetype)
# ================================================================


@pytest.mark.asyncio
async def test_post_classify_archetype_persists_and_returns_200(async_client, db):
    """POST classify-archetype con CNAE salud → 200 + persiste enum value."""
    from backend.tests.conftest import setup_test_project

    _, project_id = await setup_test_project(db)
    response = await async_client.post(
        f"/api/v1/projects/{project_id}/classify-archetype",
        json={"cnae_code": "8610"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["archetype"] == "sector_salud"
    assert data["confidence"] >= 0.95
    assert isinstance(data["reasoning_path"], list)
    assert "adjustments" in data
    assert "notes" in data["adjustments"]


@pytest.mark.asyncio
async def test_get_archetype_returns_404_when_not_classified(async_client, db):
    """GET archetype antes de classify devuelve 404."""
    from backend.tests.conftest import setup_test_project

    _, project_id = await setup_test_project(db)
    response = await async_client.get(f"/api/v1/projects/{project_id}/archetype")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_archetype_returns_persisted_after_classify(async_client, db):
    """Classify → GET retorna mismo archetype persisted."""
    from backend.tests.conftest import setup_test_project

    _, project_id = await setup_test_project(db)
    await async_client.post(
        f"/api/v1/projects/{project_id}/classify-archetype",
        json={"infrastructure_type": "saas_only"},
    )
    response = await async_client.get(f"/api/v1/projects/{project_id}/archetype")
    assert response.status_code == 200
    data = response.json()
    assert data["archetype"] == "saas_only"


@pytest.mark.asyncio
async def test_classify_unknown_project_returns_404(async_client):
    """Project inexistente → 404."""
    fake = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    response = await async_client.post(
        f"/api/v1/projects/{fake}/classify-archetype",
        json={"cnae_code": "8610"},
    )
    assert response.status_code == 404
