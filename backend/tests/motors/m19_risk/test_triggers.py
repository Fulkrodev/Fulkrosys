"""Tests M19 triggers automáticos magic-link en milestones lifecycle.

SAN-B.MB-6.3 · cierre TODO-M19-G1 (scope phase_changed listener):
- Mapping milestone → purpose 4 entries (post SAN-E v3.MB-5.0 cleanup ·
  ADR-020 v3 dropped retainer_cierre · OFERTA_RETAINER cliente-facing
  deprecated · ahora vía ClientNotification M21 cuando trigger BD active)
- process_phase_changed_event genera ML para fase mapeada
- Idempotency · re-run sobre mismo event devuelve None
- Skip events sin mapping
- Skip events con event_type incorrecto
- process_recent_phase_changes batch counters correctos
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text

from backend.app.database import set_tenant_context
from backend.app.models.lifecycle import ProjectLifecycleEvent
from backend.app.models.operations import MagicLink
from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
from backend.app.motors.m19_risk.triggers import (
    MILESTONE_TO_MAGIC_LINK_MAPPING,
    process_phase_changed_event,
    process_recent_phase_changes,
)
from backend.tests.conftest import setup_test_project


# ════════════════════════════════════════════════════════════════════
# 1. Mapping config sanity
# ════════════════════════════════════════════════════════════════════

def test_mapping_has_4_plus_milestones():
    """Spec exige minimum 4 milestones canonical workflow.

    Post SAN-E v3.MB-5.0 cleanup (ADR-020 v3): retainer_cierre dropped
    del mapping · OFERTA_RETAINER cliente-facing deprecated · cliente
    recibe oferta retainer vía ClientNotification (M21) cuando trigger
    BD project_lifecycle_events se active.
    """
    assert len(MILESTONE_TO_MAGIC_LINK_MAPPING) >= 4
    expected_keys = {
        "phase_changed:to:adecuacion",
        "phase_changed:to:implantacion",
        "phase_changed:to:verificacion",
        "phase_changed:to:conformidad",
    }
    assert expected_keys.issubset(set(MILESTONE_TO_MAGIC_LINK_MAPPING.keys()))
    # ADR-020 v3 guard: retainer_cierre no debe re-introducirse
    assert "phase_changed:to:retainer_cierre" not in MILESTONE_TO_MAGIC_LINK_MAPPING


def test_mapping_purposes_are_valid_enum_values():
    for key, config in MILESTONE_TO_MAGIC_LINK_MAPPING.items():
        assert isinstance(config["purpose"], MagicLinkPurpose), key
        assert config["ttl_hours"] > 0, key


# ════════════════════════════════════════════════════════════════════
# 2. process_phase_changed_event integration
# ════════════════════════════════════════════════════════════════════

async def _setup(db) -> tuple[uuid.UUID, uuid.UUID]:
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
    )
    return uuid.UUID(client_id), uuid.UUID(project_id)


async def _make_phase_changed_event(
    db,
    project_id: uuid.UUID,
    new_fase: str,
    *,
    event_type: str = "phase_changed",
) -> ProjectLifecycleEvent:
    event = ProjectLifecycleEvent(
        project_id=project_id,
        event_type=event_type,
        event_date=datetime.now(timezone.utc),
        metadata_jsonb={
            "old_fase": "diagnostico",
            "new_fase": new_fase,
            "changed_by": "marcos",
        },
    )
    db.add(event)
    await db.flush()
    return event


@pytest.mark.asyncio
async def test_process_event_to_adecuacion_generates_aprobacion_propuesta(db):
    _, project_id = await _setup(db)
    event = await _make_phase_changed_event(db, project_id, "adecuacion")

    ml_id = await process_phase_changed_event(
        db, event, recipient_email="cliente@example.com",
    )
    assert ml_id is not None

    ml = await db.get(MagicLink, ml_id)
    assert ml is not None
    assert ml.tipo_operacion == MagicLinkPurpose.APROBACION_PROPUESTA.value
    assert ml.scope["source_event_id"] == str(event.id)
    assert ml.scope["auto_generated"] is True
    assert ml.scope["trigger_source"] == "m19_phase_changed"


@pytest.mark.asyncio
async def test_process_event_unmapped_phase_returns_none(db):
    _, project_id = await _setup(db)
    event = await _make_phase_changed_event(db, project_id, "pre_venta")  # no mapping

    ml_id = await process_phase_changed_event(
        db, event, recipient_email="cliente@example.com",
    )
    assert ml_id is None


@pytest.mark.asyncio
async def test_process_event_idempotent_second_call_returns_none(db):
    _, project_id = await _setup(db)
    event = await _make_phase_changed_event(db, project_id, "verificacion")

    ml_id_1 = await process_phase_changed_event(
        db, event, recipient_email="cliente@example.com",
    )
    assert ml_id_1 is not None

    # Re-run · idempotency · retorna None (existing ML detected)
    ml_id_2 = await process_phase_changed_event(
        db, event, recipient_email="cliente@example.com",
    )
    assert ml_id_2 is None


@pytest.mark.asyncio
async def test_process_event_wrong_event_type_returns_none(db):
    _, project_id = await _setup(db)
    # Usa event_type valid pero != 'phase_changed' (CHECK constraint
    # acepta 'backup_generated' y otros 12 tipos · ver migration M25)
    event = await _make_phase_changed_event(
        db, project_id, "verificacion", event_type="backup_generated",
    )

    ml_id = await process_phase_changed_event(
        db, event, recipient_email="cliente@example.com",
    )
    assert ml_id is None


@pytest.mark.asyncio
async def test_process_event_no_new_fase_metadata_returns_none(db):
    _, project_id = await _setup(db)
    event = ProjectLifecycleEvent(
        project_id=project_id,
        event_type="phase_changed",
        event_date=datetime.now(timezone.utc),
        metadata_jsonb={"old_fase": "diagnostico"},  # no new_fase
    )
    db.add(event)
    await db.flush()

    ml_id = await process_phase_changed_event(
        db, event, recipient_email="cliente@example.com",
    )
    assert ml_id is None


# ════════════════════════════════════════════════════════════════════
# 3. process_recent_phase_changes batch
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_process_recent_batch_counters(db):
    _, project_id = await _setup(db)

    # Mix de events: 2 mapeados, 1 unmapped, 1 sin recipient
    await _make_phase_changed_event(db, project_id, "adecuacion")
    await _make_phase_changed_event(db, project_id, "verificacion")
    await _make_phase_changed_event(db, project_id, "pre_venta")  # unmapped
    e_no_recip = await _make_phase_changed_event(db, project_id, "implantacion")

    def resolver(event):
        if event.id == e_no_recip.id:
            return None  # simulate no recipient
        return ("cliente@example.com", None)

    counters = await process_recent_phase_changes(
        db, recipient_email_resolver=resolver,
    )
    assert counters["processed"] == 2
    assert counters["skipped_unmapped"] == 1
    assert counters["skipped_no_recipient"] == 1
    assert counters["skipped_idempotent"] == 0

    # Re-run con resolver completo · el event que era no_recipient
    # ahora se procesa (1 nuevo). Los 2 previously-processed son
    # idempotent skips. El unmapped sigue siendo skipped_unmapped.
    counters_2 = await process_recent_phase_changes(
        db, recipient_email_resolver=lambda ev: ("cliente@example.com", None),
    )
    assert counters_2["processed"] == 1  # el e_no_recip ahora procesado
    assert counters_2["skipped_idempotent"] == 2  # los 2 ML existentes
    assert counters_2["skipped_unmapped"] == 1  # pre_venta sigue unmapped
