"""Tests m_live_records · REGISTER_TYPE_REQUIRED_CATEGORIES mapping centralizado.

Sub-atom 1.C.C.B.fix v3.9 · materializa Anexo K plan v3.9 (matriz adaptación
per category sistematizada · single source de truth).

Cubre:
  - Helper is_register_required_for_category · True/False per code+category
  - Helper get_required_registers_for_category · counts B=17 M=24 A=26 (plan v3.8 §32.K.2)
  - Helper get_categories_for_register · returns frozenset categorías
  - Consistency: 26 register_types totales (matches ENTRY_SCHEMAS schemas.py)
  - Endpoint GET /categories/required?category=X returns matriz per category
"""
from __future__ import annotations

import uuid

import pytest

from backend.app.motors.m_live_records.constants import (
    COUNTS_PER_CATEGORY,
    REGISTER_TYPE_REQUIRED_CATEGORIES,
    get_categories_for_register,
    get_required_registers_for_category,
    is_register_required_for_category,
)
from backend.app.motors.m_live_records.schemas import ENTRY_SCHEMAS
from backend.tests.conftest import setup_test_project


# ================================================================
# Helper unit tests
# ================================================================


def test_is_register_required_for_category_basica_subset():
    """BASICA = subset 17 registros · sostiene plan v3.8 §32.K.2."""
    # Activos · TODOS niveles
    assert is_register_required_for_category("E-300", "BASICA") is True
    assert is_register_required_for_category("E-301", "BASICA") is True
    # Vulnerabilidades sistemáticas E-306 · solo M+A
    assert is_register_required_for_category("E-306", "BASICA") is False
    # BCP pruebas E-317 · solo M+A
    assert is_register_required_for_category("E-317", "BASICA") is False
    # DRP ejercicios E-318 · solo A
    assert is_register_required_for_category("E-318", "BASICA") is False
    # RTO/RPO E-319 · solo A
    assert is_register_required_for_category("E-319", "BASICA") is False


def test_is_register_required_for_category_media_extends_basica():
    """MEDIA aÑade refuerzos sobre BASICA · sostiene K.2 counts."""
    # E-306 vulnerabilidades sistemáticas · M+A
    assert is_register_required_for_category("E-306", "MEDIA") is True
    # E-317 BCP pruebas · M+A
    assert is_register_required_for_category("E-317", "MEDIA") is True
    # E-318 DRP solo ALTA · NO MEDIA
    assert is_register_required_for_category("E-318", "MEDIA") is False
    # E-319 RTO/RPO solo ALTA · NO MEDIA
    assert is_register_required_for_category("E-319", "MEDIA") is False


def test_is_register_required_for_category_alta_all_26():
    """ALTA aplica TODOS los 26 registros."""
    for register_type in REGISTER_TYPE_REQUIRED_CATEGORIES.keys():
        assert is_register_required_for_category(register_type, "ALTA") is True, (
            f"ALTA debería aplicar {register_type}"
        )


def test_is_register_required_unknown_raises():
    with pytest.raises(ValueError, match="Unknown register_type"):
        is_register_required_for_category("E-999", "BASICA")


def test_get_required_registers_for_category_counts():
    """Counts B=17 · M=24 · A=26 (plan v3.8 §32.K.2 autoritative)."""
    basica = get_required_registers_for_category("BASICA")
    media = get_required_registers_for_category("MEDIA")
    alta = get_required_registers_for_category("ALTA")

    assert len(basica) == 17 == COUNTS_PER_CATEGORY["BASICA"]
    assert len(media) == 24 == COUNTS_PER_CATEGORY["MEDIA"]
    assert len(alta) == 26 == COUNTS_PER_CATEGORY["ALTA"]
    # Subset relationship · ENS escalada
    assert set(basica) <= set(media) <= set(alta)


def test_get_categories_for_register():
    # E-300 inventory activos · TODOS niveles
    cats = get_categories_for_register("E-300")
    assert cats == frozenset(("BASICA", "MEDIA", "ALTA"))
    # E-318 DRP ejercicios · solo ALTA
    cats_drp = get_categories_for_register("E-318")
    assert cats_drp == frozenset(("ALTA",))
    # Unknown register_type · empty frozenset
    cats_unknown = get_categories_for_register("E-999")
    assert cats_unknown == frozenset()


def test_categories_consistency_with_entry_schemas():
    """26 register_types matriz consistency con ENTRY_SCHEMAS schemas.py.

    Garantiza single source · NO drift entre constants.py y schemas.py.
    """
    matrix_codes = set(REGISTER_TYPE_REQUIRED_CATEGORIES.keys())
    schema_codes = set(ENTRY_SCHEMAS.keys())
    assert matrix_codes == schema_codes, (
        f"Drift matriz vs ENTRY_SCHEMAS · "
        f"matrix-only: {matrix_codes - schema_codes} · "
        f"schemas-only: {schema_codes - matrix_codes}"
    )
    assert len(matrix_codes) == 26


# ================================================================
# Endpoint integration test
# ================================================================


@pytest.fixture
async def authed_marcos_with_project(async_client, db):
    """Setup test project + override auth bypass."""
    _, project_id = await setup_test_project(db)
    yield async_client, project_id


@pytest.mark.asyncio
async def test_endpoint_categories_required_returns_matrix(
    authed_marcos_with_project,
):
    """GET /categories/required?category=MEDIA returns 24 register_types ordered."""
    client, project_id = authed_marcos_with_project
    r = await client.get(
        f"/api/v1/projects/{project_id}/records/categories/required",
        params={"category": "MEDIA"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["project_id"] == project_id
    assert data["category"] == "MEDIA"
    assert data["required_count"] == 24
    assert data["expected_count"] == 24
    assert data["total_register_types"] == 26
    assert len(data["required_register_types"]) == 24
    # E-318 DRP solo ALTA · NO incluido en MEDIA
    assert "E-318" not in data["required_register_types"]
    # E-317 BCP M+A · incluido
    assert "E-317" in data["required_register_types"]


@pytest.mark.asyncio
async def test_endpoint_categories_required_basica_subset(
    authed_marcos_with_project,
):
    """BASICA returns 17 registros · sostiene plan v3.8 §32.K.2."""
    client, project_id = authed_marcos_with_project
    r = await client.get(
        f"/api/v1/projects/{project_id}/records/categories/required",
        params={"category": "BASICA"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["required_count"] == 17
    # E-306 NO en BASICA (vulnerabilidades sistemáticas · M+A)
    assert "E-306" not in data["required_register_types"]


@pytest.mark.asyncio
async def test_endpoint_categories_required_invalid_category_400(
    authed_marcos_with_project,
):
    """Pydantic Literal valida category · rechaza unknown."""
    client, project_id = authed_marcos_with_project
    r = await client.get(
        f"/api/v1/projects/{project_id}/records/categories/required",
        params={"category": "INVALID"},
    )
    assert r.status_code == 422
