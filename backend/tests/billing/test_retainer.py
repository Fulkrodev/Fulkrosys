"""Tests RetainerStateMachine + ChurnPredictor (MB-18.4 ADR-040)."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select, text

from backend.app.auth.crypto import hash_password
from backend.app.models.billing_milestones import RetainerHealthSignal
from backend.app.models.client_portal import ClientUser
from backend.app.models.retainer import RetainerContract
from backend.app.retainer.churn_predictor import (
    ChurnSignals,
    ChurnPredictor,
    compute_churn_score,
)
from backend.app.retainer.state_machine import (
    RetainerStateMachine,
    RetainerStateMachineError,
    VALID_RETAINER_STATES,
    VALID_TRANSITIONS,
)
from backend.app.retainer.tasks import scan_churn_risk_with_session
from backend.tests.conftest import _admin_setup


async def _bootstrap_retainer(
    db, *, estado: str = "active",
) -> tuple[uuid.UUID, uuid.UUID, RetainerContract]:
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, 'T-Ret', :cif, now())"
            ),
            {"id": str(client_id), "cif": cif},
        )
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, created_at) "
                "VALUES (:id, :cid, 'P-Ret', now())"
            ),
            {"id": str(project_id), "cid": str(client_id)},
        )
        retainer = RetainerContract(
            client_id=client_id,
            project_id=project_id,
            perfil="R_STD",
            modalidad="mensual",
            precio_mensual=480,
            estado=estado,
            next_renewal_date=date.today() + timedelta(days=180),
        )
        db.add(retainer)
        await db.flush()
        await db.refresh(retainer)
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(project_id)},
    )
    return client_id, project_id, retainer


# ──────────────── ChurnPredictor compute ────────────────


def test_compute_score_low_no_signals():
    result = compute_churn_score(ChurnSignals())
    assert result.score == Decimal("0.00")
    assert result.risk_level == "low"
    assert result.factors == []


def test_compute_score_medium_overdue_invoices():
    result = compute_churn_score(
        ChurnSignals(invoices_overdue_count=2)
    )
    assert result.score == Decimal("25.00")
    assert result.risk_level == "low"


def test_compute_score_high_login_plus_invoices():
    result = compute_churn_score(
        ChurnSignals(
            days_since_portal_login=70,
            invoices_overdue_count=1,
        )
    )
    assert result.score == Decimal("65.00")
    assert result.risk_level == "high"


def test_compute_score_critical_all_signals():
    result = compute_churn_score(
        ChurnSignals(
            days_since_portal_login=90,
            tasks_overdue_count=5,
            invoices_overdue_count=2,
            avg_response_time_hours=Decimal("72"),
            nps_last_score=4,
            renewal_in_days=30,
        )
    )
    assert result.score == Decimal("100.00")
    assert result.risk_level == "critical"
    assert len(result.factors) == 6


def test_compute_score_capped_at_100():
    result = compute_churn_score(
        ChurnSignals(
            days_since_portal_login=200,
            tasks_overdue_count=20,
            invoices_overdue_count=10,
            avg_response_time_hours=Decimal("999"),
            nps_last_score=0,
            renewal_in_days=0,
        )
    )
    assert result.score == Decimal("100.00")


def test_compute_score_recommended_action_per_level():
    # low: score 0
    low = compute_churn_score(ChurnSignals())
    # medium: score 30-59 · 25+25 = 50
    med = compute_churn_score(ChurnSignals(
        invoices_overdue_count=1, tasks_overdue_count=4,
    ))
    # high: score 60-79 · 40+25 = 65
    high = compute_churn_score(ChurnSignals(
        days_since_portal_login=70, invoices_overdue_count=1,
    ))
    # critical: score >= 80 · 40+25+25 = 90
    crit = compute_churn_score(ChurnSignals(
        days_since_portal_login=90, tasks_overdue_count=5,
        invoices_overdue_count=2,
    ))
    assert low.risk_level == "low"
    assert "saludable" in low.recommended_action
    assert med.risk_level == "medium"
    assert "Monitorizar" in med.recommended_action
    assert high.risk_level == "high"
    assert "Llamar al cliente" in high.recommended_action
    assert crit.risk_level == "critical"
    assert "urgente" in crit.recommended_action


# ──────────────── ChurnPredictor compute_for_retainer ────────────────


@pytest.mark.asyncio
async def test_compute_for_retainer_persists_signal(db):
    _, project_id, retainer = await _bootstrap_retainer(db)
    predictor = ChurnPredictor(db)

    signal = await predictor.compute_for_retainer(retainer=retainer)
    assert signal.id is not None
    assert signal.retainer_id == retainer.id
    assert signal.project_id == project_id
    assert signal.risk_level in ("low", "medium", "high", "critical")
    assert signal.churn_risk_score >= Decimal("0")


# ──────────────── RetainerStateMachine ────────────────


def test_can_transition_active_to_paused():
    sm_check = RetainerStateMachine.can_transition
    assert sm_check("active", "paused") is True
    assert sm_check("active", "churned") is True
    assert sm_check("active", "upgraded") is True


def test_can_transition_cancelled_terminal():
    sm_check = RetainerStateMachine.can_transition
    assert sm_check("cancelled", "active") is False
    assert sm_check("cancelled", "churned") is False


def test_can_transition_invalid_state():
    assert RetainerStateMachine.can_transition("nonsense", "active") is False


@pytest.mark.asyncio
async def test_transition_active_to_paused(db):
    _, _, retainer = await _bootstrap_retainer(db, estado="active")
    sm = RetainerStateMachine(db)

    outcome = await sm.transition(
        retainer_id=retainer.id,
        target_state="paused",
        reason="Cliente solicita pausa por reorganizacion interna",
    )
    assert outcome.previous_state == "active"
    assert outcome.new_state == "paused"
    assert outcome.reason and "reorganizacion" in outcome.reason

    refreshed = await db.get(RetainerContract, retainer.id)
    assert refreshed.estado == "paused"


@pytest.mark.asyncio
async def test_transition_invalid_raises(db):
    _, _, retainer = await _bootstrap_retainer(db, estado="cancelled")
    sm = RetainerStateMachine(db)

    with pytest.raises(RetainerStateMachineError):
        await sm.transition(
            retainer_id=retainer.id,
            target_state="active",
        )


@pytest.mark.asyncio
async def test_transition_target_invalid_state_raises(db):
    _, _, retainer = await _bootstrap_retainer(db)
    sm = RetainerStateMachine(db)

    with pytest.raises(RetainerStateMachineError):
        await sm.transition(
            retainer_id=retainer.id,
            target_state="nonsense",
        )


@pytest.mark.asyncio
async def test_transition_not_found_raises(db):
    sm = RetainerStateMachine(db)
    with pytest.raises(RetainerStateMachineError):
        await sm.transition(
            retainer_id=uuid.uuid4(),
            target_state="paused",
        )


@pytest.mark.asyncio
async def test_transition_active_to_churned(db):
    _, _, retainer = await _bootstrap_retainer(db, estado="active")
    sm = RetainerStateMachine(db)

    outcome = await sm.transition(
        retainer_id=retainer.id,
        target_state="churned",
        reason="ChurnPredictor critical · 3 meses sin actividad",
    )
    assert outcome.new_state == "churned"


# ──────────────── scan_churn_risk_with_session ────────────────


@pytest.mark.asyncio
async def test_scan_churn_risk_processes_active_retainers(db):
    _, _, retainer = await _bootstrap_retainer(db, estado="active")

    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    stats = await scan_churn_risk_with_session(db)
    await db.execute(text("RESET ROLE"))

    assert stats["total_scanned"] >= 1
    assert stats["computed_count"] >= 1


@pytest.mark.asyncio
async def test_scan_churn_skips_paused(db):
    _, project_id, retainer = await _bootstrap_retainer(db, estado="paused")

    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    stats = await scan_churn_risk_with_session(db)
    await db.execute(text("RESET ROLE"))

    signals = (await db.execute(
        select(RetainerHealthSignal).where(
            RetainerHealthSignal.retainer_id == retainer.id
        )
    )).scalars().all()
    assert signals == []


# ──────────────── Beat schedule ────────────────


def test_beat_schedule_contains_scan_churn():
    from backend.app.core.celery_app import get_beat_schedule
    schedule = get_beat_schedule()
    assert "retainer-scan-churn-weekly" in schedule


def test_celery_app_includes_retainer_tasks():
    from backend.app.core.celery_app import celery_app
    if hasattr(celery_app, "conf") and isinstance(celery_app.conf, dict):
        return
    include = list(celery_app.conf.include or [])
    assert "backend.app.retainer.tasks" in include
