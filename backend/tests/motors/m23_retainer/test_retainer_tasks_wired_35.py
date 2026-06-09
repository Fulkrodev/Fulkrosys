"""#35 Ola8 · los 4 tasks stub del retainer ahora invocan sus servicios reales.

Los tasks abren su propia async_session (asyncio.run), así que el test verifica la
ORQUESTACIÓN: que cada task invoca el servicio real, hace commit y devuelve
status='ok' con los datos del servicio (no el dict-stub viejo). Servicios y
async_session mockeados (unit, sin BD).
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from backend.app.motors.m23_retainer import tasks as m23_tasks


def _fake_session():
    sess = MagicMock(name="session")
    result = MagicMock(name="result")
    result.scalars.return_value.all.return_value = []
    sess.execute = AsyncMock(return_value=result)
    sess.flush = AsyncMock()
    sess.commit = AsyncMock()
    sess.rollback = AsyncMock()
    return sess


class _FakeCM:
    def __init__(self, sess):
        self.sess = sess

    async def __aenter__(self):
        return self.sess

    async def __aexit__(self, *a):
        return False


def test_check_overdue_activities_wired():
    sess = _fake_session()
    with patch("backend.app.database.async_session", lambda: _FakeCM(sess)), patch(
        "backend.app.motors.m23_retainer.retainer_service.RetainerService.get_overdue_activities",
        AsyncMock(return_value=[]),
    ) as mock_svc:
        out = m23_tasks.check_overdue_activities()
    assert out["status"] == "ok"
    assert out["marked"] == 0
    assert mock_svc.await_count == 1
    sess.commit.assert_awaited()


def test_update_all_renewal_statuses_wired():
    sess = _fake_session()
    with patch("backend.app.database.async_session", lambda: _FakeCM(sess)):
        out = m23_tasks.update_all_renewal_statuses()
    assert out["status"] == "ok"
    assert out["updated"] == 0  # select devolvió [] (sin retainers activos)
    sess.commit.assert_awaited()


def test_renewal_trigger_daily_wired():
    fake_res = SimpleNamespace(
        processed_projects=2,
        alerts_6m=["p1"],
        campaigns_created_3m=[],
        alerts_1m=[],
        errors=[],
    )
    sess = _fake_session()
    with patch("backend.app.database.async_session", lambda: _FakeCM(sess)), patch(
        "backend.app.motors.m27_conformity.renewal_scheduler.run_renewal_bianual_check",
        AsyncMock(return_value=fake_res),
    ) as mock_svc:
        out = m23_tasks.renewal_trigger_daily()
    assert out["status"] == "ok"
    assert out["processed_projects"] == 2
    assert out["alerts_6m"] == 1
    assert mock_svc.await_count == 1


def test_agent_26_weekly_analysis_wired():
    summary = {"total_alerts": 3, "by_priority": {"high": 1}, "by_code": {}, "top_5": []}
    sess = _fake_session()
    with patch("backend.app.database.async_session", lambda: _FakeCM(sess)), patch(
        "backend.app.motors.m23_retainer.agent_26.summary_for_marcos",
        AsyncMock(return_value=summary),
    ) as mock_svc:
        out = m23_tasks.agent_26_weekly_analysis()
    assert out["status"] == "ok"
    assert out["agent"] == "26"
    assert out["total_alerts"] == 3
    assert mock_svc.await_count == 1
