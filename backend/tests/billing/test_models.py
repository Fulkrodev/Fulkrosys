"""Tests modelos ContractMilestone + RetainerHealthSignal (MB-18.1).

Cubre invariantes schema migrations sand_billing_milestones_001 +
sand_retainer_health_001 (ADR-040):
- Insert básico defaults aplicados.
- CHECK constraints status / billing_trigger / amount_nonneg / percent_range.
- UNIQUE (contract_id, milestone_index).
- FK behavior CASCADE / SET NULL.
- RetainerHealthSignal CHECKs risk_level + score_range.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from backend.app.models.billing_milestones import (
    ContractMilestone,
    RetainerHealthSignal,
)
from backend.tests.conftest import _admin_setup


async def _bootstrap_contract(db) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    contract_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, 'T-Bill', :cif, now())"
            ),
            {"id": str(client_id), "cif": cif},
        )
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, created_at) "
                "VALUES (:id, :cid, 'P-Bill', now())"
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
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": str(client_id)},
    )
    return client_id, project_id, contract_id


async def _bootstrap_retainer(db) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    client_id, project_id, _ = await _bootstrap_contract(db)
    retainer_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO retainer_contracts (id, client_id, project_id, "
                "perfil, estado, created_at) "
                "VALUES (:id, :cid, :pid, 'R_STD', 'active', now())"
            ),
            {
                "id": str(retainer_id),
                "cid": str(client_id),
                "pid": str(project_id),
            },
        )
    return client_id, project_id, retainer_id


@pytest.mark.asyncio
async def test_milestone_insert_with_defaults(db):
    _, project_id, contract_id = await _bootstrap_contract(db)
    m = ContractMilestone(
        contract_id=contract_id,
        project_id=project_id,
        milestone_index=0,
        milestone_name="hito_1_firma",
        workflow_phase_index=1,
        amount_eur=Decimal("1500.00"),
        percent_of_total=Decimal("30.00"),
    )
    db.add(m)
    await db.flush()
    await db.refresh(m)

    assert m.id is not None
    assert m.status == "pending"
    assert m.billing_trigger == "phase_complete"
    assert m.vat_percent == Decimal("21.00")
    assert m.auto_billing_enabled is True
    assert m.blocking_next_phase is True
    assert m.metadata_jsonb == {}
    assert m.paid_at is None


@pytest.mark.asyncio
async def test_milestone_status_check(db):
    _, project_id, contract_id = await _bootstrap_contract(db)
    with pytest.raises(IntegrityError):
        await db.execute(
            text(
                "INSERT INTO contract_milestones "
                "(contract_id, project_id, milestone_index, milestone_name, "
                "workflow_phase_index, amount_eur, percent_of_total, status) "
                "VALUES (:cid, :pid, 0, 'x', 1, 100, 30, 'invalid_status')"
            ),
            {"cid": str(contract_id), "pid": str(project_id)},
        )
        await db.flush()


@pytest.mark.asyncio
async def test_milestone_billing_trigger_check(db):
    _, project_id, contract_id = await _bootstrap_contract(db)
    with pytest.raises(IntegrityError):
        await db.execute(
            text(
                "INSERT INTO contract_milestones "
                "(contract_id, project_id, milestone_index, milestone_name, "
                "workflow_phase_index, amount_eur, percent_of_total, "
                "billing_trigger) "
                "VALUES (:cid, :pid, 0, 'x', 1, 100, 30, 'invalid_trigger')"
            ),
            {"cid": str(contract_id), "pid": str(project_id)},
        )
        await db.flush()


@pytest.mark.asyncio
async def test_milestone_unique_contract_index(db):
    _, project_id, contract_id = await _bootstrap_contract(db)
    db.add(ContractMilestone(
        contract_id=contract_id,
        project_id=project_id,
        milestone_index=0,
        milestone_name="x",
        workflow_phase_index=1,
        amount_eur=Decimal("100"),
        percent_of_total=Decimal("30"),
    ))
    await db.flush()

    db.add(ContractMilestone(
        contract_id=contract_id,
        project_id=project_id,
        milestone_index=0,
        milestone_name="dup",
        workflow_phase_index=2,
        amount_eur=Decimal("200"),
        percent_of_total=Decimal("40"),
    ))
    with pytest.raises(IntegrityError):
        await db.flush()


@pytest.mark.asyncio
async def test_milestone_amount_nonneg(db):
    _, project_id, contract_id = await _bootstrap_contract(db)
    with pytest.raises(IntegrityError):
        await db.execute(
            text(
                "INSERT INTO contract_milestones "
                "(contract_id, project_id, milestone_index, milestone_name, "
                "workflow_phase_index, amount_eur, percent_of_total) "
                "VALUES (:cid, :pid, 0, 'x', 1, -100, 30)"
            ),
            {"cid": str(contract_id), "pid": str(project_id)},
        )
        await db.flush()


@pytest.mark.asyncio
async def test_milestone_percent_range(db):
    _, project_id, contract_id = await _bootstrap_contract(db)
    with pytest.raises(IntegrityError):
        await db.execute(
            text(
                "INSERT INTO contract_milestones "
                "(contract_id, project_id, milestone_index, milestone_name, "
                "workflow_phase_index, amount_eur, percent_of_total) "
                "VALUES (:cid, :pid, 0, 'x', 1, 100, 150)"
            ),
            {"cid": str(contract_id), "pid": str(project_id)},
        )
        await db.flush()


@pytest.mark.asyncio
async def test_milestone_invoice_set_null_on_invoice_delete(db):
    _, project_id, contract_id = await _bootstrap_contract(db)
    invoice_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO invoices "
                "(id, client_id, project_id, contract_id, "
                "numero_correlativo, total, created_at) "
                "VALUES (:iid, "
                "(SELECT client_id FROM projects WHERE id = :pid), "
                ":pid, :cid, 'TEST-001', 100, now())"
            ),
            {"iid": str(invoice_id), "pid": str(project_id), "cid": str(contract_id)},
        )
    m = ContractMilestone(
        contract_id=contract_id,
        project_id=project_id,
        milestone_index=0,
        milestone_name="x",
        workflow_phase_index=1,
        amount_eur=Decimal("100"),
        percent_of_total=Decimal("30"),
        invoice_id=invoice_id,
        status="invoice_issued",
    )
    db.add(m)
    await db.flush()
    m_id = m.id

    async with _admin_setup(db):
        await db.execute(
            text("DELETE FROM invoices WHERE id = :iid"),
            {"iid": str(invoice_id)},
        )

    row = (await db.execute(
        text("SELECT invoice_id FROM contract_milestones WHERE id = :id"),
        {"id": str(m_id)},
    )).first()
    assert row is not None
    assert row[0] is None


@pytest.mark.asyncio
async def test_retainer_health_insert_with_defaults(db):
    _, project_id, retainer_id = await _bootstrap_retainer(db)
    h = RetainerHealthSignal(
        project_id=project_id,
        retainer_id=retainer_id,
        computed_at=datetime.now(timezone.utc),
        churn_risk_score=Decimal("45.50"),
        risk_level="medium",
    )
    db.add(h)
    await db.flush()
    await db.refresh(h)

    assert h.id is not None
    assert h.tasks_overdue_count == 0
    assert h.invoices_overdue_count == 0
    assert h.primary_risk_factors == []
    assert h.days_since_portal_login is None


@pytest.mark.asyncio
async def test_retainer_health_risk_level_check(db):
    _, project_id, retainer_id = await _bootstrap_retainer(db)
    with pytest.raises(IntegrityError):
        await db.execute(
            text(
                "INSERT INTO retainer_health_signals "
                "(project_id, retainer_id, computed_at, churn_risk_score, "
                "risk_level) "
                "VALUES (:pid, :rid, now(), 50, 'invalid_level')"
            ),
            {"pid": str(project_id), "rid": str(retainer_id)},
        )
        await db.flush()


@pytest.mark.asyncio
async def test_retainer_health_score_range(db):
    _, project_id, retainer_id = await _bootstrap_retainer(db)
    with pytest.raises(IntegrityError):
        await db.execute(
            text(
                "INSERT INTO retainer_health_signals "
                "(project_id, retainer_id, computed_at, churn_risk_score, "
                "risk_level) "
                "VALUES (:pid, :rid, now(), 150, 'high')"
            ),
            {"pid": str(project_id), "rid": str(retainer_id)},
        )
        await db.flush()


@pytest.mark.asyncio
async def test_retainer_health_jsonb_factors(db):
    _, project_id, retainer_id = await _bootstrap_retainer(db)
    h = RetainerHealthSignal(
        project_id=project_id,
        retainer_id=retainer_id,
        computed_at=datetime.now(timezone.utc),
        days_since_portal_login=75,
        invoices_overdue_count=2,
        churn_risk_score=Decimal("85.00"),
        risk_level="critical",
        primary_risk_factors=[
            "days_since_portal_login>60",
            "invoices_overdue>0",
        ],
        recommended_action="Contactar Marcos urgente · check-in directo",
    )
    db.add(h)
    await db.flush()
    await db.refresh(h)

    assert h.risk_level == "critical"
    assert "days_since_portal_login>60" in h.primary_risk_factors
    assert "Contactar" in (h.recommended_action or "")
