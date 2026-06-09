"""Integration tests auto-population M19/M28/M14 → E-305/E-308/E-312.

Sub-atom 1.C.B fase 3c · LECCION-OPS-008 RLS + OPS-033 in-flight bug safety.

Tests usan los helpers ``auto_populate_*`` directamente con el session del
fixture ``db`` (caller-session mode · misma transacción rollback). Esto
permite asertions deterministas: el listener real abriría un session
separado que en tests rompería la transacción isolation. La instalación del
listener (registro idempotente) se valida aparte.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import select, text

from backend.app.models.live_record import LiveRecord
from backend.app.motors.m_live_records.auto_population import (
    auto_populate_change_to_e308,
    auto_populate_incident_to_e305,
    auto_populate_provider_assessment_to_e312,
)


async def _setup_project(db) -> tuple[uuid.UUID, uuid.UUID]:
    from backend.tests.conftest import setup_test_project  # type: ignore

    _client_id, project_id = await setup_test_project(db)
    return uuid.UUID(project_id), uuid.uuid4()


@pytest.mark.asyncio
async def test_auto_populate_incident_to_e305_creates_entry(db):
    project_id, user_id = await _setup_project(db)

    incident_id = uuid.uuid4()
    record_id = await auto_populate_incident_to_e305(
        project_id=project_id,
        incident_id=incident_id,
        severidad="alta",
        descripcion="Acceso no autorizado detectado en CPD",
        fecha=datetime(2026, 2, 10, 14, 30, tzinfo=timezone.utc),
        created_by=user_id,
        db=db,
    )
    assert record_id is not None

    result = await db.execute(
        select(LiveRecord).where(LiveRecord.id == record_id)
    )
    record = result.scalar_one()
    assert record.register_type == "E-305"
    assert record.entry_data["nivel_criticidad"] == "alto"
    assert record.entry_data["fase_nist"] == "deteccion"
    assert record.entry_data["notificado_lucia"] is False
    assert str(incident_id)[:8].upper() in record.entry_data["codigo_incidente"]


@pytest.mark.asyncio
async def test_auto_populate_change_to_e308_creates_entry(db):
    project_id, user_id = await _setup_project(db)

    change_id = uuid.uuid4()
    record_id = await auto_populate_change_to_e308(
        project_id=project_id,
        change_id=change_id,
        descripcion="Actualizacion firmware switches",
        solicitante="Equipo Networking",
        fecha=datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc),
        created_by=user_id,
        db=db,
    )
    assert record_id is not None

    result = await db.execute(
        select(LiveRecord).where(LiveRecord.id == record_id)
    )
    record = result.scalar_one()
    assert record.register_type == "E-308"
    assert record.entry_data["tipo_cambio"] == "normal"
    assert record.entry_data["solicitante"] == "Equipo Networking"
    assert record.entry_data["resultado"] == "pendiente"


@pytest.mark.asyncio
async def test_auto_populate_provider_assessment_to_e312_creates_entry(db):
    project_id, user_id = await _setup_project(db)

    assessment_id = uuid.uuid4()
    provider_id = uuid.uuid4()
    record_id = await auto_populate_provider_assessment_to_e312(
        project_id=project_id,
        assessment_id=assessment_id,
        provider_id=provider_id,
        assessment_date=date(2026, 4, 15),
        assessor="CISO interno",
        risk_score=0.85,
        risk_level="BAJO",
        decision="APROBADO",
        created_by=user_id,
        db=db,
    )
    assert record_id is not None

    result = await db.execute(
        select(LiveRecord).where(LiveRecord.id == record_id)
    )
    record = result.scalar_one()
    assert record.register_type == "E-312"
    assert record.entry_data["proveedor_codigo"] == str(provider_id)
    assert record.entry_data["puntuacion_global"] == 8.5
    assert record.entry_data["decision"] == "renovar"
    assert record.entry_data["periodo"] == "2026-04"
    assert "risk_level=BAJO" in record.entry_data["hallazgos"]


@pytest.mark.asyncio
async def test_auto_populate_failure_does_not_propagate(db):
    """Cuando ``create_record`` lanza, el helper devuelve None y no propaga."""
    project_id, user_id = await _setup_project(db)

    with patch(
        "backend.app.motors.m_live_records.auto_population.LiveRecordsService.create_record",
        side_effect=RuntimeError("synthetic failure"),
    ):
        result = await auto_populate_incident_to_e305(
            project_id=project_id,
            incident_id=uuid.uuid4(),
            severidad="alta",
            descripcion="x",
            fecha=datetime.now(timezone.utc),
            created_by=user_id,
            db=db,
        )

    assert result is None


@pytest.mark.asyncio
async def test_severity_mapping_normalizes_aliases(db):
    """Severidades sinónimos M19 mapean a valores válidos schema E-305."""
    project_id, user_id = await _setup_project(db)

    for raw, expected in [
        ("CRITICAL", "critico"),
        ("alta", "alto"),
        ("Media", "medio"),
        ("BAJA", "bajo"),
        ("info", "informativo"),
        ("xxx_unknown", "medio"),  # fallback
    ]:
        rid = await auto_populate_incident_to_e305(
            project_id=project_id,
            incident_id=uuid.uuid4(),
            severidad=raw,
            descripcion="probe",
            fecha=datetime.now(timezone.utc),
            created_by=user_id,
            db=db,
        )
        assert rid is not None
        rec = (
            await db.execute(select(LiveRecord).where(LiveRecord.id == rid))
        ).scalar_one()
        assert rec.entry_data["nivel_criticidad"] == expected


def test_register_listeners_is_idempotent():
    """register_listeners es idempotente: doble registro no duplica."""
    from backend.app.motors.m_live_records import listeners as lr_listeners

    lr_listeners.register_listeners()
    lr_listeners.register_listeners()
    assert lr_listeners._LISTENERS_REGISTERED is True
