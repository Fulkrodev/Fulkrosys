"""Tests Sprint C5 — Celery scheduler + tasks."""
from __future__ import annotations


def test_c5_celery_app_importable():
    from backend.app.core.celery_app import celery_app, get_beat_schedule
    assert celery_app is not None
    # Debe tener schedule (aunque sea stub)
    schedule = get_beat_schedule()
    assert len(schedule) >= 5


def test_c5_beat_schedule_has_required_tasks():
    from backend.app.core.celery_app import get_beat_schedule
    schedule = get_beat_schedule()
    required = {
        "backup-weekly-full",
        "backup-daily-incremental",
        "retainer-check-overdue",
        "retainer-renewal-check",
        "evidence-freshness-check",
    }
    assert required.issubset(set(schedule.keys()))


def test_c5_m23_tasks_defined():
    from backend.app.motors.m23_retainer.tasks import (
        check_overdue_activities,
        update_all_renewal_statuses,
        execute_scheduled_activity,
        ACTIVITY_EXECUTORS,
    )
    assert callable(check_overdue_activities)
    assert callable(update_all_renewal_statuses)
    assert callable(execute_scheduled_activity)
    # Al menos 10 tipos de actividad mapeados
    assert len(ACTIVITY_EXECUTORS) >= 10


def test_c5_m07_task_defined():
    from backend.app.motors.m07_evidence.tasks import check_expiring_evidence
    assert callable(check_expiring_evidence)


def test_c5_m26_task_defined():
    from backend.app.motors.m26_backup.tasks import run_pgbackrest_full
    assert callable(run_pgbackrest_full)


def test_c5_retainer_has_execute_activity_method():
    from backend.app.motors.m23_retainer.retainer_service import RetainerService
    assert hasattr(RetainerService, "execute_activity")
    # Mapping de executors
    assert hasattr(RetainerService, "ACTIVITY_EXECUTORS")
    assert len(RetainerService.ACTIVITY_EXECUTORS) >= 5
