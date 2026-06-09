"""#45 OlaIII · vista cruzada estado-implementación × pagos.

Cubre los helpers puros (derive_payment_state / is_overdue / current_phase_index /
phase_label) y el builder async que cruza projects.fase × contract_milestones:
fase alcanzada → 'due', no alcanzada → 'upcoming', pagada → 'paid'; vencidos y
totales (total/pagado/pendiente/próximo) coherentes.
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.billing.implementation_payments import (
    build_implementation_payments,
    current_phase_index,
    derive_payment_state,
    is_overdue,
    phase_label,
)
from backend.app.billing.milestone_factory import MilestoneFactory
from backend.tests.conftest import _admin_setup, setup_test_project


# ─────────────── helpers puros ───────────────

def test_current_phase_index_known_and_unknown():
    assert current_phase_index("onboarding") == 1
    assert current_phase_index("implantacion") == 5
    assert current_phase_index("conformidad") == 8
    assert current_phase_index(None) == 0
    assert current_phase_index("fase_inexistente") == 0


def test_phase_label_friendly():
    assert phase_label(1) == "Inicio del proyecto"
    assert phase_label(8) == "Certificación"
    assert phase_label(999).startswith("Fase ")


def test_derive_payment_state():
    assert derive_payment_state(True, "paid") == "paid"
    assert derive_payment_state(False, "refunded") == "paid"
    assert derive_payment_state(True, "pending") == "due"      # fase alcanzada, sin pagar
    assert derive_payment_state(False, "pending") == "upcoming"  # fase no llega


def test_is_overdue():
    today = date(2026, 6, 5)
    past = today - timedelta(days=10)
    future = today + timedelta(days=10)
    assert is_overdue(past, "pending", today) is True
    assert is_overdue(past, "paid", today) is False     # liquidado no vence
    assert is_overdue(future, "pending", today) is False
    assert is_overdue(None, "pending", today) is False


# ─────────────── builder con DB ───────────────

async def _mk_contract(db) -> uuid.UUID:
    cid = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(
            sa_text(
                "INSERT INTO contracts (id, tipo, estado, created_at) "
                "VALUES (:id, 'c001', 'draft', now())"
            ),
            {"id": str(cid)},
        )
    await db.flush()
    return cid


@pytest.mark.asyncio
async def test_build_crosses_phase_and_payment(db: AsyncSession):
    _, project_id = await setup_test_project(db)
    contract_id = await _mk_contract(db)
    created = await MilestoneFactory(db).create_milestones_for_contract(
        contract_id=contract_id,
        project_id=uuid.UUID(project_id),
        categoria="MEDIA",
        contract_total=Decimal("11500.00"),
        start_date=date(2026, 1, 1),
    )
    assert len(created) >= 4

    # Proyecto en 'implantacion' (idx 5): fases <=5 alcanzadas, 7/8 no.
    async with _admin_setup(db):
        await db.execute(
            sa_text("UPDATE projects SET fase='implantacion' WHERE id=:pid"),
            {"pid": project_id},
        )
        # marca el primer hito (firma, fase 1) como pagado
        await db.execute(
            sa_text(
                "UPDATE contract_milestones SET status='paid', paid_at=now() "
                "WHERE project_id=:pid AND milestone_index=0"
            ),
            {"pid": project_id},
        )
    await db.flush()

    view = await build_implementation_payments(
        db, uuid.UUID(project_id), today=date(2026, 6, 5),
    )
    assert view["found"] is True
    assert view["current_phase_index"] == 5
    assert view["current_phase_label"] == "Implantación"

    by_phase = {m["workflow_phase_index"]: m for m in view["milestones"]}
    # hito firma fase 1 → pagado
    firma = next(m for m in view["milestones"] if m["milestone_index"] == 0)
    assert firma["payment_state"] == "paid"
    assert firma["phase_reached"] is True
    # algún hito de fase alcanzada y sin pagar → 'due'
    assert any(
        m["payment_state"] == "due" for m in view["milestones"]
    ), "debe haber hitos 'due' (fase alcanzada, sin pagar)"
    # los hitos de fase 7/8 (verificación/certificación) → 'upcoming'
    assert any(
        m["payment_state"] == "upcoming" and m["workflow_phase_index"] >= 7
        for m in view["milestones"]
    )

    # totales coherentes
    total = Decimal(view["totals"]["total_eur"])
    paid = Decimal(view["totals"]["paid_eur"])
    pending = Decimal(view["totals"]["pending_eur"])
    assert total == paid + pending
    assert paid == Decimal(firma["amount_eur"])  # solo el hito de firma pagado


@pytest.mark.asyncio
async def test_refunded_milestone_coherent_totals(db: AsyncSession):
    """#45 fix · un hito 'refunded' se ve 'Pagado' por línea Y su importe cuenta
    como liquidado (no cae en pendiente · total == paid + pending coherente)."""
    _, project_id = await setup_test_project(db)
    contract_id = await _mk_contract(db)
    await MilestoneFactory(db).create_milestones_for_contract(
        contract_id=contract_id,
        project_id=uuid.UUID(project_id),
        categoria="MEDIA",
        contract_total=Decimal("11500.00"),
    )
    async with _admin_setup(db):
        await db.execute(
            sa_text(
                "UPDATE contract_milestones SET status='refunded' "
                "WHERE project_id=:pid AND milestone_index=0"
            ),
            {"pid": project_id},
        )
    await db.flush()

    view = await build_implementation_payments(
        db, uuid.UUID(project_id), today=date(2026, 6, 5),
    )
    refunded = next(m for m in view["milestones"] if m["milestone_index"] == 0)
    assert refunded["payment_state"] == "paid"  # liquidado
    # su importe NO está en pendiente
    paid = Decimal(view["totals"]["paid_eur"])
    pending = Decimal(view["totals"]["pending_eur"])
    total = Decimal(view["totals"]["total_eur"])
    assert total == paid + pending
    assert paid >= Decimal(refunded["amount_eur"])  # el refunded cuenta como liquidado


@pytest.mark.asyncio
async def test_build_unknown_project_graceful(db: AsyncSession):
    await setup_test_project(db)  # fija contexto RLS de un proyecto real
    ghost = uuid.uuid4()
    view = await build_implementation_payments(db, ghost, today=date(2026, 6, 5))
    assert view["found"] is False
    assert view["milestones"] == []
    assert view["totals"]["total_eur"] == "0.00"
