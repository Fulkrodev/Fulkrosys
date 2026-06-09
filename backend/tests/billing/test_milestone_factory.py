"""Tests MilestoneFactory (MB-18.2 ADR-040)."""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select, text

from backend.app.billing.milestone_factory import (
    DEFAULT_PHASE_FALLBACK,
    MilestoneFactory,
    MILESTONE_PHASE_MAPPING,
    resolve_workflow_phase,
)
from backend.app.models.billing_milestones import ContractMilestone
from backend.tests.conftest import _admin_setup


async def _bootstrap(db) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    contract_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, 'T-Fact', :cif, now())"
            ),
            {"id": str(client_id), "cif": cif},
        )
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, created_at) "
                "VALUES (:id, :cid, 'P-Fact', now())"
            ),
            {"id": str(project_id), "cid": str(client_id)},
        )
        await db.execute(
            text(
                "INSERT INTO contracts (id, project_id, estado, created_at) "
                "VALUES (:id, :pid, 'draft', now())"
            ),
            {"id": str(contract_id), "pid": str(project_id)},
        )
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(project_id)},
    )
    return client_id, project_id, contract_id


def test_resolve_workflow_phase_known_codes():
    assert resolve_workflow_phase("hito_1_firma") == 1
    assert resolve_workflow_phase("hito_2_diagnostico_ar") == 3
    assert resolve_workflow_phase("hito_5_certificacion") == 8


def test_resolve_workflow_phase_unknown_uses_fallback():
    assert resolve_workflow_phase("hito_inventado") == DEFAULT_PHASE_FALLBACK


def test_phase_mapping_has_canonical_codes():
    """Sanity check: codes hardcoded en mapping coinciden con repo."""
    assert "hito_1_firma" in MILESTONE_PHASE_MAPPING
    assert "hito_5_certificacion" in MILESTONE_PHASE_MAPPING


@pytest.mark.asyncio
async def test_create_milestones_basica(db):
    _, project_id, contract_id = await _bootstrap(db)
    factory = MilestoneFactory(db)

    created = await factory.create_milestones_for_contract(
        contract_id=contract_id,
        project_id=project_id,
        categoria="BASICA",
        contract_total=Decimal("3000.00"),
    )

    assert len(created) == 3
    assert created[0].milestone_name == "hito_1_firma"
    assert created[0].workflow_phase_index == 1
    assert created[0].milestone_index == 0
    assert created[0].amount_eur == Decimal("900.00")
    assert created[0].percent_of_total == Decimal("30.00")
    assert created[0].billing_trigger == "phase_complete"
    assert created[0].auto_billing_enabled is True
    assert created[0].blocking_next_phase is True

    total_amount = sum(m.amount_eur for m in created)
    assert total_amount == Decimal("3000.00")


@pytest.mark.asyncio
async def test_create_milestones_media(db):
    _, project_id, contract_id = await _bootstrap(db)
    factory = MilestoneFactory(db)

    created = await factory.create_milestones_for_contract(
        contract_id=contract_id,
        project_id=project_id,
        categoria="MEDIA",
        contract_total=Decimal("8000.00"),
    )

    assert len(created) == 5
    codes = [m.milestone_name for m in created]
    assert codes == [
        "hito_1_firma",
        "hito_2_diagnostico_ar",
        "hito_3_dda_sgsi",
        "hito_4_dossier_auditor",
        "hito_5_certificacion",
    ]
    phases = [m.workflow_phase_index for m in created]
    assert phases == [1, 3, 4, 7, 8]


@pytest.mark.asyncio
async def test_create_milestones_idempotent(db):
    _, project_id, contract_id = await _bootstrap(db)
    factory = MilestoneFactory(db)

    first = await factory.create_milestones_for_contract(
        contract_id=contract_id,
        project_id=project_id,
        categoria="BASICA",
        contract_total=Decimal("3000"),
    )
    assert len(first) == 3

    second = await factory.create_milestones_for_contract(
        contract_id=contract_id,
        project_id=project_id,
        categoria="BASICA",
        contract_total=Decimal("3000"),
    )
    assert len(second) == 0  # all skipped (UNIQUE)

    rows = (await db.execute(
        select(ContractMilestone).where(
            ContractMilestone.contract_id == contract_id
        )
    )).scalars().all()
    assert len(rows) == 3


@pytest.mark.asyncio
async def test_create_milestones_metadata_persisted(db):
    _, project_id, contract_id = await _bootstrap(db)
    factory = MilestoneFactory(db)

    created = await factory.create_milestones_for_contract(
        contract_id=contract_id,
        project_id=project_id,
        categoria="BASICA",
        contract_total=Decimal("3000"),
    )
    assert created[0].metadata_jsonb["categoria"] == "BASICA"
    assert "description" in created[0].metadata_jsonb
