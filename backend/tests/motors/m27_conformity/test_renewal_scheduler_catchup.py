"""Tests M27 renewal scheduler · §2.8/274 catch-up + idempotencia por hito.

Antes el scheduler disparaba los hitos 6m/3m/1m por IGUALDAD EXACTA de días
(== N), así que si el beat no corría el día exacto (worker caído, deploy) el hito
se perdía PARA SIEMPRE. Ahora usa cruce-de-umbral (<=) con guarda de idempotencia
por hito (espejo de m25 lifecycle_paso4), de modo que cada hito cruzado pendiente
dispara una sola vez aunque el día exacto se haya saltado.
"""
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import text as sa_text

from backend.app.motors.m27_conformity.renewal_scheduler import (
    ALERT_1M_BEFORE_DAYS,
    ALERT_6M_BEFORE_DAYS,
    run_renewal_bianual_check,
)
from backend.tests.conftest import _admin_setup, setup_test_project

# O1 · el bienio del art. 31 es de ANYOS de calendario. El ayudante que calcula
# la fecha vivia aqui y lo necesitaba tambien test_paso7_final: se mudo a
# backend/tests/helpers_bienio.py para no tenerlo escrito dos veces.
from backend.tests.helpers_bienio import (
    certificado_para_que_falten as _certificado_para_que_falten,
)


async def _certify_project_at(db, project_id: str, certified_at: date) -> None:
    async with _admin_setup(db):
        await db.execute(sa_text(
            "UPDATE projects SET certified_at = :c, "
            "lifecycle_state = 'CERTIFIED' WHERE id = :pid"
        ), {"pid": project_id, "c": certified_at})


async def _count_renewal_events(db, project_id: str, renewal_type: str) -> int:
    await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
    try:
        return (await db.execute(sa_text(
            "SELECT count(*) FROM project_lifecycle_events "
            "WHERE project_id = :pid AND event_type = 'warning_sent' "
            "AND metadata_jsonb->>'renewal' = :rt"
        ), {"pid": project_id, "rt": renewal_type})).scalar()
    finally:
        await db.execute(sa_text("RESET ROLE"))


@pytest.mark.asyncio
async def test_1m_alert_fires_even_if_exact_day_skipped(db):
    """El beat se salta el día exacto (days_to == 30) y corre en days_to == 25:
    el hito 1m igual dispara (cruce-de-umbral, no igualdad exacta)."""
    _, project_id = await setup_test_project(db)
    # Certificado de modo que HOY days_to_aniversario = 25 (saltado el 30 exacto).
    certified = _certificado_para_que_falten(ALERT_1M_BEFORE_DAYS - 5)
    await _certify_project_at(db, project_id, certified)

    result = await run_renewal_bianual_check(db, today=date.today())
    assert str(project_id) in result.alerts_1m
    assert await _count_renewal_events(db, project_id, "alert_1m_marcos") == 1


@pytest.mark.asyncio
async def test_1m_alert_idempotent_across_runs(db):
    """Aunque el scheduler corra varios días seguidos cruzado el umbral 1m, el
    hito dispara una SOLA vez (guarda de idempotencia por hito)."""
    _, project_id = await setup_test_project(db)
    certified = _certificado_para_que_falten(ALERT_1M_BEFORE_DAYS - 5)
    await _certify_project_at(db, project_id, certified)

    r1 = await run_renewal_bianual_check(db, today=date.today())
    r2 = await run_renewal_bianual_check(db, today=date.today())

    assert str(project_id) in r1.alerts_1m
    assert str(project_id) not in r2.alerts_1m  # ya no re-dispara
    assert await _count_renewal_events(db, project_id, "alert_1m_marcos") == 1


@pytest.mark.asyncio
async def test_6m_alert_fires_even_if_exact_day_skipped(db):
    """El beat se salta el día exacto (days_to == 180) y corre en days_to == 175:
    el hito 6m igual dispara una sola vez."""
    _, project_id = await setup_test_project(db)
    certified = _certificado_para_que_falten(ALERT_6M_BEFORE_DAYS - 5)
    await _certify_project_at(db, project_id, certified)

    r1 = await run_renewal_bianual_check(db, today=date.today())
    r2 = await run_renewal_bianual_check(db, today=date.today())

    assert str(project_id) in r1.alerts_6m
    assert str(project_id) not in r2.alerts_6m
    assert await _count_renewal_events(db, project_id, "alert_6m_marcos") == 1
