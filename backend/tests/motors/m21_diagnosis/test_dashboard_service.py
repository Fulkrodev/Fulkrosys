"""Tests ProjectDashboardService aglutinador (MB-13.1 · ADR-035).

Cobertura:
- Aggregation cross-motor (next_actions + readiness + phase + estimated_days)
- ValueError → HTTPException 404 (caller)
- Estimación días lookup BASICA / MEDIA / ALTA con factor readiness
- Sin AuditPreparationRun → readiness_score=0 sin error
- NextAction priority urgent/blocking flags derivation
"""
import uuid

import pytest

from backend.app.core.workflow_phase import WorkflowPhase
from backend.app.motors.m21_diagnosis.dashboard_service import (
    DAYS_REMAINING_PER_PHASE,
    PHASE_LABELS_ES,
    ProjectDashboardService,
)
from backend.tests.conftest import setup_test_project


@pytest.mark.asyncio
async def test_dashboard_basic_aggregation(db):
    """get_dashboard retorna campos mínimos para proyecto vacío."""
    _, project_id = await setup_test_project(db)
    pid = uuid.UUID(project_id)

    service = ProjectDashboardService(db)
    dashboard = await service.get_dashboard(pid)

    assert dashboard.project_id == pid
    assert dashboard.phase_total == 10
    assert 0 <= dashboard.phase_index <= 9
    assert dashboard.current_phase in {p.value for p in WorkflowPhase}
    assert dashboard.current_phase_label in PHASE_LABELS_ES.values()
    assert isinstance(dashboard.next_actions, list)
    assert 0 <= dashboard.readiness_score <= 100
    assert dashboard.active_alerts == []
    assert dashboard.active_alerts_count == 0
    assert isinstance(dashboard.blocking_issues, list)
    assert dashboard.last_updated is not None


@pytest.mark.asyncio
async def test_dashboard_no_audit_run_zero_readiness(db):
    """Proyecto recién creado · sin AuditPreparationRun → readiness=0."""
    _, project_id = await setup_test_project(db)
    pid = uuid.UUID(project_id)

    service = ProjectDashboardService(db)
    dashboard = await service.get_dashboard(pid)

    assert dashboard.readiness_score == 0
    assert dashboard.blocking_issues == []


@pytest.mark.asyncio
async def test_dashboard_unknown_project_raises_value_error(db):
    """Project_id no existente → ValueError (caller convierte 404)."""
    service = ProjectDashboardService(db)
    fake_id = uuid.uuid4()

    with pytest.raises(ValueError, match="not found"):
        await service.get_dashboard(fake_id)


@pytest.mark.asyncio
async def test_dashboard_default_category_basica(db):
    """Proyecto sin categoria_objetivo → BASICA default + lookup BASICA."""
    _, project_id = await setup_test_project(db)
    pid = uuid.UUID(project_id)

    service = ProjectDashboardService(db)
    dashboard = await service.get_dashboard(pid)

    # setup_test_project no setea categoria → default BASICA
    assert dashboard.category == "BASICA"


def test_estimate_days_lookup_basica_full_remaining():
    """Estimación BASICA fase 1 (onboarding) · readiness 0 → factor 1.5x."""
    days = ProjectDashboardService._estimate_days(
        phase_idx=1, category="BASICA", readiness=0,
    )
    base_total = sum(DAYS_REMAINING_PER_PHASE["BASICA"][1:])
    # readiness=0 → factor=2.0 clamped a 1.5
    assert days == int(base_total * 1.5)


def test_estimate_days_lookup_media_high_readiness():
    """MEDIA fase 5 con readiness 90 · factor ~0.7 (clamp inferior)."""
    days = ProjectDashboardService._estimate_days(
        phase_idx=5, category="MEDIA", readiness=90,
    )
    base = sum(DAYS_REMAINING_PER_PHASE["MEDIA"][5:])
    # readiness=90 → factor=2-0.9=1.1 NO 0.7 (no llega a clamp)
    expected = int(base * 1.1)
    assert days == expected


def test_estimate_days_post_conformidad_zero():
    """Fase >= 8 (conformidad o retainer) → 0 días."""
    assert (
        ProjectDashboardService._estimate_days(
            phase_idx=8, category="ALTA", readiness=50,
        )
        == 0
    )
    assert (
        ProjectDashboardService._estimate_days(
            phase_idx=9, category="ALTA", readiness=50,
        )
        == 0
    )


def test_estimate_days_unknown_category_falls_back_basica():
    """Categoria invalida → fallback BASICA."""
    days = ProjectDashboardService._estimate_days(
        phase_idx=2, category="DESCONOCIDA", readiness=50,
    )
    base = sum(DAYS_REMAINING_PER_PHASE["BASICA"][2:])
    # readiness=50 → factor=1.5 NO 1.0; let's compute correctly
    # factor = max(0.7, min(1.5, 2.0 - 50/100)) = max(0.7, min(1.5, 1.5)) = 1.5
    assert days == int(base * 1.5)


def test_to_item_urgent_flag_priority_le_2():
    """priority <= 2 marca urgent · priority > 2 NO urgent."""
    from backend.app.core.workflow_schemas import NextAction

    p1 = NextAction(
        action_id="a1", label="L1", motor="M1",
        endpoint="/x", priority=1, estimated_minutes=10,
    )
    p3 = NextAction(
        action_id="a3", label="L3", motor="M3",
        endpoint="/y", priority=3, estimated_minutes=20,
    )

    item1 = ProjectDashboardService._to_item(p1, WorkflowPhase.DIAGNOSTICO)
    item3 = ProjectDashboardService._to_item(p3, WorkflowPhase.DIAGNOSTICO)

    assert item1.urgent is True
    assert item3.urgent is False


def test_to_item_blocking_only_in_critical_phases():
    """priority==1 + fase critica (verif/conformidad) → blocking. Otras NO."""
    from backend.app.core.workflow_schemas import NextAction

    high_pri = NextAction(
        action_id="a", label="L", motor="M",
        endpoint=None, priority=1, estimated_minutes=10,
    )

    item_diag = ProjectDashboardService._to_item(
        high_pri, WorkflowPhase.DIAGNOSTICO,
    )
    item_verif = ProjectDashboardService._to_item(
        high_pri, WorkflowPhase.VERIFICACION,
    )
    item_conf = ProjectDashboardService._to_item(
        high_pri, WorkflowPhase.CONFORMIDAD,
    )

    assert item_diag.blocking is False
    assert item_verif.blocking is True
    assert item_conf.blocking is True


def test_to_item_action_url_endpoint_or_hash():
    """endpoint None → action_url '#' fallback."""
    from backend.app.core.workflow_schemas import NextAction

    no_endpoint = NextAction(
        action_id="a", label="L", motor="M",
        endpoint=None, priority=2, estimated_minutes=10,
    )
    with_endpoint = NextAction(
        action_id="b", label="L2", motor="M",
        endpoint="/admin/foo", priority=2, estimated_minutes=10,
    )

    item_none = ProjectDashboardService._to_item(
        no_endpoint, WorkflowPhase.DIAGNOSTICO,
    )
    item_url = ProjectDashboardService._to_item(
        with_endpoint, WorkflowPhase.DIAGNOSTICO,
    )

    assert item_none.action_url == "#"
    assert item_url.action_url == "/admin/foo"
