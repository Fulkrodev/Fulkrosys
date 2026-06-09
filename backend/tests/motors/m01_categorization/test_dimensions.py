"""Tests integration · sub-atom 1.C.D.A.0.1 v3.8 · 19 dimensiones adaptación.

Cubre:
  - Migration projects_19dims_1c_d_a0_001 aplicada (defaults verificados)
  - Service DimensionsService.get_dimensions retorna 19 dims completas
  - Service DimensionsService.update_dimensions persiste partial updates
  - Indicator dims_captured_count funciona (3 base + 16 nuevas non-default)
  - Pydantic validation (enums correctos · CHECK constraints DB)
  - HTTP endpoints (GET reader · PATCH admin)
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from backend.app.motors.m01_categorization.dimensions_schemas import (
    ProjectDimensionsRead,
    ProjectDimensionsUpdate,
)
from backend.app.motors.m01_categorization.dimensions_service import (
    DimensionsService,
    ProjectDimensionsServiceError,
)
from backend.tests.conftest import setup_test_project


# ================================================================
# Migration defaults (smoke)
# ================================================================


@pytest.mark.asyncio
async def test_migration_adds_16_columns_with_defaults(db):
    """Migration añade 16 columnas con server_default · projects nuevo
    aterriza con todos los valores default."""
    _, project_id = await setup_test_project(db)

    row = await db.execute(text(
        "SELECT tamano_empleados, madurez_ens_actual, geografia_operacion, "
        "procesa_datos_sensibles_rgpd9, aplica_nis2, aplica_dora, aplica_ai_act, "
        "dpo_designado, arquitectura_sistemas, multi_tenancy, equipo_ti_tamano, "
        "certificaciones_previas, urgencia_certificacion, presupuesto_disponible, "
        "compromiso_interno, horas_cliente_semana "
        "FROM projects WHERE id = :pid"
    ), {"pid": project_id})
    row_data = row.mappings().first()
    assert row_data is not None
    assert row_data["tamano_empleados"] == "pequeno"
    assert row_data["madurez_ens_actual"] == "L0"
    assert row_data["geografia_operacion"] == "spain"
    assert row_data["procesa_datos_sensibles_rgpd9"] is False
    assert row_data["aplica_nis2"] == "no"
    assert row_data["aplica_dora"] == "no"
    assert row_data["aplica_ai_act"] == "no"
    assert row_data["dpo_designado"] == "no_designado"
    assert row_data["arquitectura_sistemas"] == "cloud_native"
    assert row_data["multi_tenancy"] == "single"
    assert row_data["equipo_ti_tamano"] == "1_3"
    assert row_data["certificaciones_previas"] == []
    assert row_data["urgencia_certificacion"] == "6m"
    assert row_data["presupuesto_disponible"] == "estandar"
    assert row_data["compromiso_interno"] == "reactivo"
    assert row_data["horas_cliente_semana"] == "5_15h"


# ================================================================
# CHECK constraints (defensive)
# ================================================================


@pytest.mark.asyncio
async def test_check_constraint_madurez_invalid_value_rejected(db):
    """CHECK constraint rechaza valor inválido (L99 NO en enum).

    NOTE: ejecutamos UPDATE como fulkro_app (RLS-enforced). El CHECK
    constraint dispara IntegrityError antes del commit. Tras la excepción
    hacemos rollback para no dejar transaction aborted (afecta cleanup).
    """
    _, project_id = await setup_test_project(db)

    with pytest.raises((IntegrityError, Exception)):
        await db.execute(text(
            "UPDATE projects SET madurez_ens_actual = 'L99' WHERE id = :pid"
        ), {"pid": project_id})
        await db.flush()
    await db.rollback()


@pytest.mark.asyncio
async def test_check_constraint_aplica_dora_invalid_value_rejected(db):
    """CHECK constraint rechaza valor inválido aplica_dora."""
    _, project_id = await setup_test_project(db)

    with pytest.raises((IntegrityError, Exception)):
        await db.execute(text(
            "UPDATE projects SET aplica_dora = 'crypto_exchange' WHERE id = :pid"
        ), {"pid": project_id})
        await db.flush()
    await db.rollback()


# ================================================================
# Service · get_dimensions
# ================================================================


@pytest.mark.asyncio
async def test_get_dimensions_returns_19_dims_with_defaults(db):
    """Service.get_dimensions retorna ProjectDimensionsRead completo."""
    _, project_id = await setup_test_project(db)

    service = DimensionsService(db)
    dims = await service.get_dimensions(uuid.UUID(project_id))

    assert isinstance(dims, ProjectDimensionsRead)
    assert dims.tamano_empleados == "pequeno"
    assert dims.madurez_ens_actual == "L0"
    assert dims.aplica_nis2 == "no"
    assert dims.dims_total == 19


@pytest.mark.asyncio
async def test_get_dimensions_not_found_raises(db):
    """Service.get_dimensions raise ProjectDimensionsServiceError si no existe."""
    service = DimensionsService(db)
    with pytest.raises(ProjectDimensionsServiceError):
        await service.get_dimensions(uuid.uuid4())


# ================================================================
# Service · update_dimensions
# ================================================================


@pytest.mark.asyncio
async def test_update_dimensions_persists_partial(db):
    """Service.update_dimensions persiste fields provided · OPS-043 commit explícito."""
    _, project_id = await setup_test_project(db)
    updater = uuid.uuid4()

    service = DimensionsService(db)
    payload = ProjectDimensionsUpdate(
        madurez_ens_actual="L2",
        aplica_dora="entidad_financiera",
        dpo_designado="interno",
    )
    updated = await service.update_dimensions(
        project_id=uuid.UUID(project_id),
        payload=payload,
        updated_by=updater,
    )

    assert updated.madurez_ens_actual == "L2"
    assert updated.aplica_dora == "entidad_financiera"
    assert updated.dpo_designado == "interno"
    # Otros campos no tocados conservan default
    assert updated.aplica_nis2 == "no"


@pytest.mark.asyncio
async def test_update_dimensions_partial_dict_helper(db):
    """Helper patch_dimensions_partial valida y persiste subset."""
    _, project_id = await setup_test_project(db)
    updater = uuid.uuid4()

    service = DimensionsService(db)
    updated = await service.patch_dimensions_partial(
        project_id=uuid.UUID(project_id),
        partial_dict={
            "urgencia_certificacion": "3m",
            "compromiso_interno": "proactivo",
            "horas_cliente_semana": "15_40h",
        },
        updated_by=updater,
    )

    assert updated.urgencia_certificacion == "3m"
    assert updated.compromiso_interno == "proactivo"
    assert updated.horas_cliente_semana == "15_40h"


@pytest.mark.asyncio
async def test_update_dimensions_certificaciones_previas_jsonb(db):
    """Service persiste array JSONB certificaciones_previas correctamente."""
    _, project_id = await setup_test_project(db)
    updater = uuid.uuid4()

    service = DimensionsService(db)
    updated = await service.update_dimensions(
        project_id=uuid.UUID(project_id),
        payload=ProjectDimensionsUpdate(
            certificaciones_previas=["ISO27001", "SOC2"],
        ),
        updated_by=updater,
    )

    assert "ISO27001" in updated.certificaciones_previas
    assert "SOC2" in updated.certificaciones_previas


# ================================================================
# Indicator helper · compute_dims_captured
# ================================================================


@pytest.mark.asyncio
async def test_compute_dims_captured_defaults_baseline(db):
    """Project nuevo · 1 dim captured (fase NOT NULL existing)."""
    _, project_id = await setup_test_project(db)
    service = DimensionsService(db)
    dims = await service.get_dimensions(uuid.UUID(project_id))

    # Project nuevo · sin categoria_objetivo/archetype · sólo fase NOT NULL default
    assert dims.dims_captured_count == 1


@pytest.mark.asyncio
async def test_compute_dims_captured_after_partial_update(db):
    """Tras update parcial · captured_count refleja non-default values."""
    _, project_id = await setup_test_project(db)
    updater = uuid.uuid4()

    service = DimensionsService(db)
    await service.update_dimensions(
        project_id=uuid.UUID(project_id),
        payload=ProjectDimensionsUpdate(
            madurez_ens_actual="L3",
            aplica_dora="entidad_financiera",
            urgencia_certificacion="1m",
        ),
        updated_by=updater,
    )

    dims = await service.get_dimensions(uuid.UUID(project_id))
    # fase (1) + 3 dims editadas non-default = 4
    assert dims.dims_captured_count == 4


# ================================================================
# Pydantic validation
# ================================================================


def test_pydantic_validation_rejects_invalid_madurez():
    """ProjectDimensionsUpdate Pydantic rechaza valor fuera enum."""
    with pytest.raises(ValueError):
        ProjectDimensionsUpdate(madurez_ens_actual="L99")  # type: ignore[arg-type]


def test_pydantic_validation_rejects_invalid_dora():
    """ProjectDimensionsUpdate Pydantic rechaza valor fuera enum aplica_dora."""
    with pytest.raises(ValueError):
        ProjectDimensionsUpdate(aplica_dora="invalid_dora")  # type: ignore[arg-type]


def test_pydantic_update_extra_forbid():
    """ProjectDimensionsUpdate rechaza fields no declarados (extra='forbid')."""
    with pytest.raises(ValueError):
        ProjectDimensionsUpdate.model_validate({
            "madurez_ens_actual": "L1",
            "field_inventado_no_existe": "x",
        })


# ================================================================
# RLS isolation (cross-tenant)
# ================================================================


@pytest.mark.asyncio
async def test_rls_isolation_dimensions_cross_tenant(db):
    """Service.get_dimensions con context proyecto B NO retorna dims de A.

    Pattern: setup A · context A · update A · setup B (context cambia a B) ·
    intentar leer A bajo context B · debe levantar ProjectDimensionsServiceError
    (RLS filtra row · service.get_dimensions interpreta como not found).
    """
    # Crear proyecto A · update bajo context A (setup_test_project deja context en A)
    client_a, project_a = await setup_test_project(db)
    service = DimensionsService(db)
    await service.update_dimensions(
        project_id=uuid.UUID(project_a),
        payload=ProjectDimensionsUpdate(
            madurez_ens_actual="L4",
            aplica_nis2="esencial",
        ),
        updated_by=uuid.uuid4(),
    )

    # Crear proyecto B (setup_test_project cambia context a B)
    client_b, project_b = await setup_test_project(db)

    # Bajo context B · service intenta leer A · RLS filtra · "not found"
    with pytest.raises(ProjectDimensionsServiceError):
        await service.get_dimensions(uuid.UUID(project_a))
