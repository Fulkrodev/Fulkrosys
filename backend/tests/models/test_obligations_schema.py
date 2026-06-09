"""Tests for Obligation model schema (Motor 5 extended columns).

Verifies that the Obligation SQLAlchemy model correctly persists to
the obligations table with both original and new Motor 5 columns.
"""
import uuid

import pytest

from backend.app.models.ens import Obligation
from backend.tests.conftest import _admin_setup, setup_test_project


@pytest.mark.asyncio
async def test_insert_obligation_minimal(db):
    """Insert an obligation with only required fields."""
    _, project_id = await setup_test_project(db)

    async with _admin_setup(db):
        ob = Obligation(
            project_id=uuid.UUID(project_id),
            descripcion="Test obligation for Motor 5",
        )
        db.add(ob)
        await db.flush()

    assert ob.id is not None
    assert ob.descripcion == "Test obligation for Motor 5"
    # Motor 5 columns should be None when not set
    assert ob.template_id is None
    assert ob.measure_code is None
    assert ob.criterios_aceptacion is None


@pytest.mark.asyncio
async def test_insert_obligation_with_motor5_columns(db):
    """Insert an obligation with Motor 5 extended columns filled."""
    _, project_id = await setup_test_project(db)

    async with _admin_setup(db):
        ob = Obligation(
            project_id=uuid.UUID(project_id),
            descripcion="Obligation with Motor 5 fields",
            template_id="OBL-org.1-001",
            template_version="1.0",
            measure_code="org.1",
            titulo="Aprobar y publicar Politica de Seguridad",
            entregable_tipo="politica",
            estado="pending",
            criterios_aceptacion=["Documento aprobado", "Incluye alcance"],
            fuente_normativa=["ENS RD 311/2022 Anexo II - org.1"],
            dependencias_template_ids=[],
            metadata_extra={"source": "library_v1"},
        )
        db.add(ob)
        await db.flush()

    assert ob.id is not None
    assert ob.template_id == "OBL-org.1-001"
    assert ob.measure_code == "org.1"
    assert ob.titulo == "Aprobar y publicar Politica de Seguridad"
    assert ob.entregable_tipo == "politica"
    assert ob.estado == "pending"
    assert len(ob.criterios_aceptacion) == 2
    assert ob.fuente_normativa[0].startswith("ENS")
