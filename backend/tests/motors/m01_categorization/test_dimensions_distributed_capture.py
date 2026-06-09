"""Tests integration · sub-atom 1.C.D.A.0.3 v3.8 · captura dims distribuida.

Cubre:
  - m16_onboarding.dimensions_capture.extract_dimension_updates_from_responses
  - m16_onboarding.dimensions_capture.apply_dimensions_from_responses
  - m_meetings · _action_create_project extiende dims pre-venta opcionales
  - m13_commercial._map_empleados_to_tamano helper
"""
from __future__ import annotations

import uuid

import pytest

from backend.app.motors.m01_categorization.dimensions_service import DimensionsService
from backend.app.motors.m13_commercial.services.commercial_workflow_service import (
    _map_empleados_to_tamano,
)
from backend.app.motors.m16_onboarding.dimensions_capture import (
    CANONICAL_DIM_QUESTION_MAPPING,
    apply_dimensions_from_responses,
    extract_dimension_updates_from_responses,
)
from backend.tests.conftest import setup_test_project


# ================================================================
# m13_commercial helper · _map_empleados_to_tamano
# ================================================================


def test_map_empleados_micro():
    assert _map_empleados_to_tamano(5) == "micro"


def test_map_empleados_pequeno():
    assert _map_empleados_to_tamano(25) == "pequeno"


def test_map_empleados_mediano():
    assert _map_empleados_to_tamano(100) == "mediano"


def test_map_empleados_grande():
    assert _map_empleados_to_tamano(300) == "grande"


def test_map_empleados_enterprise():
    assert _map_empleados_to_tamano(1000) == "enterprise"


def test_map_empleados_string_input():
    assert _map_empleados_to_tamano("25") == "pequeno"


def test_map_empleados_none_returns_none():
    assert _map_empleados_to_tamano(None) is None


def test_map_empleados_invalid_returns_none():
    assert _map_empleados_to_tamano("not-a-number") is None


# ================================================================
# m16_onboarding · extract_dimension_updates_from_responses
# ================================================================


def test_extract_dimension_updates_canonical_only():
    """Sólo extrae question_ids canónicas · ignora resto."""
    responses = {
        "q-madurez-ens-actual": "L2",
        "q-aplica-dora": "entidad_financiera",
        "q-not-canonical": "ignored",  # no en mapping
        "q-nombre-empresa": "Acme Corp",  # no en mapping
    }
    updates = extract_dimension_updates_from_responses(responses)

    assert updates == {
        "madurez_ens_actual": "L2",
        "aplica_dora": "entidad_financiera",
    }


def test_extract_dimension_updates_skip_none_values():
    responses = {
        "q-madurez-ens-actual": "L1",
        "q-aplica-dora": None,  # None se skipea
    }
    updates = extract_dimension_updates_from_responses(responses)
    assert updates == {"madurez_ens_actual": "L1"}


def test_extract_dimension_updates_empty():
    assert extract_dimension_updates_from_responses({}) == {}


def test_canonical_mapping_size():
    """Sub-atom 1.C.D.A.0.3 documenta 10 question_ids canónicas."""
    assert len(CANONICAL_DIM_QUESTION_MAPPING) == 10


# ================================================================
# m16_onboarding · apply_dimensions_from_responses (integration)
# ================================================================


@pytest.mark.asyncio
async def test_apply_dimensions_from_responses_persists(db):
    """apply_dimensions_from_responses persiste subset dims al project."""
    _, project_id = await setup_test_project(db)
    updater = uuid.uuid4()

    responses = {
        "q-madurez-ens-actual": "L3",
        "q-equipo-ti-tamano": "4_10",
        "q-aplica-nis2": "esencial",
        "q-aplica-dora": "proveedor_ict_critico",
        "q-procesa-datos-sensibles": True,
        "q-nombre-empresa": "Acme",  # ignorado · no canónico
    }

    applied = await apply_dimensions_from_responses(
        db=db,
        project_id=uuid.UUID(project_id),
        responses=responses,
        updated_by=updater,
    )

    assert applied is not None
    assert applied["madurez_ens_actual"] == "L3"
    assert applied["equipo_ti_tamano"] == "4_10"

    # Verify persisted via service
    service = DimensionsService(db)
    dims = await service.get_dimensions(uuid.UUID(project_id))
    assert dims.madurez_ens_actual == "L3"
    assert dims.equipo_ti_tamano == "4_10"
    assert dims.aplica_nis2 == "esencial"
    assert dims.aplica_dora == "proveedor_ict_critico"
    assert dims.procesa_datos_sensibles_rgpd9 is True


@pytest.mark.asyncio
async def test_apply_dimensions_from_responses_no_canonical_returns_none(db):
    """Sin respuestas canónicas · función retorna None · NO persiste."""
    _, project_id = await setup_test_project(db)
    updater = uuid.uuid4()

    applied = await apply_dimensions_from_responses(
        db=db,
        project_id=uuid.UUID(project_id),
        responses={"q-non-canonical": "anything"},
        updated_by=updater,
    )

    assert applied is None


@pytest.mark.asyncio
async def test_apply_dimensions_from_responses_invalid_project_warns(db):
    """Project no existe · función NO levanta · retorna None (OPS-040 non-invasive)."""
    fake_project_id = uuid.uuid4()
    updater = uuid.uuid4()

    # OPS-040 pattern · safe_fire NON-invasive · NO rompe motor origen
    applied = await apply_dimensions_from_responses(
        db=db,
        project_id=fake_project_id,
        responses={"q-madurez-ens-actual": "L1"},
        updated_by=updater,
    )

    assert applied is None
