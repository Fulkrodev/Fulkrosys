"""Tests AutoBillingService (MB-18.2 ADR-040)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select, text

from backend.app.auth.crypto import hash_password
from backend.app.billing.auto_billing import AutoBillingService
from backend.app.billing.milestone_factory import MilestoneFactory
from backend.app.models.billing_milestones import ContractMilestone
from backend.app.models.client_portal import ClientUser
from backend.tests.conftest import _admin_setup


async def _bootstrap_full(
    db,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, ClientUser]:
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    contract_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, 'T-Auto', :cif, now())"
            ),
            {"id": str(client_id), "cif": cif},
        )
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, fase, "
                "created_at) "
                "VALUES (:id, :cid, 'P-Auto', 'adecuacion', now())"
            ),
            {"id": str(project_id), "cid": str(client_id)},
        )
        await db.execute(
            text(
                "INSERT INTO contracts (id, project_id, estado, created_at) "
                "VALUES (:id, :pid, 'firmado', now())"
            ),
            {"id": str(contract_id), "pid": str(project_id)},
        )
        user = ClientUser(
            client_id=client_id,
            email=f"auto-{uuid.uuid4().hex[:8]}@example.com",
            password_hash=hash_password("TestP@ssw0rd123!"),
            full_name="Cliente Auto",
            must_change_password=False,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(project_id)},
    )
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": str(client_id)},
    )
    return client_id, project_id, contract_id, user


@pytest.mark.asyncio
async def test_handle_phase_completion_no_milestones(db):
    _, project_id, _, _ = await _bootstrap_full(db)
    service = AutoBillingService(db)
    outcomes = await service.handle_phase_completion(
        project_id=project_id, completed_phase_index=4,
    )
    assert outcomes == []


@pytest.mark.asyncio
async def test_handle_phase_completion_bills_eligible(db):
    _, project_id, contract_id, _ = await _bootstrap_full(db)
    factory = MilestoneFactory(db)
    await factory.create_milestones_for_contract(
        contract_id=contract_id,
        project_id=project_id,
        categoria="BASICA",
        contract_total=Decimal("3000"),
    )

    service = AutoBillingService(db)
    outcomes = await service.handle_phase_completion(
        project_id=project_id, completed_phase_index=4,  # ADECUACION
    )

    eligible = [o for o in outcomes if o.status == "billed"]
    assert len(eligible) >= 1
    for o in eligible:
        assert o.invoice_id is not None
        assert o.invoice_number is not None
        assert o.amount_eur is not None

    rows = (await db.execute(
        select(ContractMilestone).where(
            ContractMilestone.workflow_phase_index == 4,
            ContractMilestone.project_id == project_id,
        )
    )).scalars().all()
    assert all(m.status == "invoice_issued" for m in rows)
    assert all(m.invoice_id is not None for m in rows)


@pytest.mark.asyncio
async def test_handle_phase_completion_skips_disabled(db):
    _, project_id, contract_id, _ = await _bootstrap_full(db)
    m = ContractMilestone(
        contract_id=contract_id,
        project_id=project_id,
        milestone_index=99,
        milestone_name="hito_disabled",
        workflow_phase_index=4,
        amount_eur=Decimal("100"),
        percent_of_total=Decimal("10"),
        auto_billing_enabled=False,
    )
    db.add(m)
    await db.flush()

    service = AutoBillingService(db)
    outcomes = await service.handle_phase_completion(
        project_id=project_id, completed_phase_index=4,
    )
    billed_ids = {o.milestone_id for o in outcomes if o.status == "billed"}
    assert m.id not in billed_ids


@pytest.mark.asyncio
async def test_handle_phase_completion_skips_already_billed(db):
    _, project_id, contract_id, _ = await _bootstrap_full(db)
    m = ContractMilestone(
        contract_id=contract_id,
        project_id=project_id,
        milestone_index=98,
        milestone_name="hito_already",
        workflow_phase_index=4,
        amount_eur=Decimal("100"),
        percent_of_total=Decimal("10"),
        status="invoice_issued",
        billed_at=datetime.now(timezone.utc),
    )
    db.add(m)
    await db.flush()

    service = AutoBillingService(db)
    outcomes = await service.handle_phase_completion(
        project_id=project_id, completed_phase_index=4,
    )
    billed_ids = {o.milestone_id for o in outcomes}
    assert m.id not in billed_ids


@pytest.mark.asyncio
async def test_mark_milestone_paid_advances_workflow(db):
    _, project_id, contract_id, user = await _bootstrap_full(db)
    factory = MilestoneFactory(db)
    await factory.create_milestones_for_contract(
        contract_id=contract_id,
        project_id=project_id,
        categoria="BASICA",
        contract_total=Decimal("3000"),
    )
    service = AutoBillingService(db)
    await service.handle_phase_completion(
        project_id=project_id, completed_phase_index=4,
    )

    # Get one billed milestone in phase 4
    m_row = (await db.execute(
        select(ContractMilestone).where(
            ContractMilestone.project_id == project_id,
            ContractMilestone.workflow_phase_index == 4,
            ContractMilestone.status == "invoice_issued",
        ).limit(1)
    )).scalar_one()

    paid = await service.mark_milestone_paid(
        milestone_id=m_row.id,
        by_user_id=user.id,
        payment_reference="REF-TEST-12345",
        payment_notes="Test reconciliación",
    )
    assert paid.status == "paid"
    assert paid.payment_reference == "REF-TEST-12345"
    assert paid.paid_at is not None

    # Verify projects.fase advanced
    fase_row = (await db.execute(
        text("SELECT fase FROM projects WHERE id = :pid"),
        {"pid": str(project_id)},
    )).first()
    assert fase_row[0] == "implantacion"  # phase 5 (after ADECUACION=4)

    # Verify invoice estado_pago='paid'
    if paid.invoice_id:
        inv_row = (await db.execute(
            text("SELECT estado_pago FROM invoices WHERE id = :iid"),
            {"iid": str(paid.invoice_id)},
        )).first()
        assert inv_row[0] == "paid"


@pytest.mark.asyncio
async def test_mark_milestone_paid_idempotent(db):
    _, project_id, contract_id, user = await _bootstrap_full(db)
    m = ContractMilestone(
        contract_id=contract_id,
        project_id=project_id,
        milestone_index=0,
        milestone_name="hito_already_paid",
        workflow_phase_index=1,
        amount_eur=Decimal("100"),
        percent_of_total=Decimal("10"),
        status="paid",
        paid_at=datetime.now(timezone.utc),
        blocking_next_phase=False,
    )
    db.add(m)
    await db.flush()

    service = AutoBillingService(db)
    result = await service.mark_milestone_paid(
        milestone_id=m.id, by_user_id=user.id,
    )
    assert result.status == "paid"


@pytest.mark.asyncio
async def test_mark_milestone_paid_not_blocking_no_advance(db):
    _, project_id, contract_id, user = await _bootstrap_full(db)
    m = ContractMilestone(
        contract_id=contract_id,
        project_id=project_id,
        milestone_index=0,
        milestone_name="hito_no_block",
        workflow_phase_index=1,
        amount_eur=Decimal("100"),
        percent_of_total=Decimal("10"),
        status="invoice_issued",
        billed_at=datetime.now(timezone.utc),
        blocking_next_phase=False,
    )
    db.add(m)
    await db.flush()

    fase_before = (await db.execute(
        text("SELECT fase FROM projects WHERE id = :pid"),
        {"pid": str(project_id)},
    )).first()[0]

    service = AutoBillingService(db)
    await service.mark_milestone_paid(
        milestone_id=m.id, by_user_id=user.id,
    )

    fase_after = (await db.execute(
        text("SELECT fase FROM projects WHERE id = :pid"),
        {"pid": str(project_id)},
    )).first()[0]
    assert fase_after == fase_before  # no advance


@pytest.mark.asyncio
async def test_mark_milestone_paid_not_found_raises(db):
    _, _, _, user = await _bootstrap_full(db)
    service = AutoBillingService(db)
    from backend.app.billing.auto_billing import AutoBillingError

    with pytest.raises(AutoBillingError):
        await service.mark_milestone_paid(
            milestone_id=uuid.uuid4(), by_user_id=user.id,
        )
