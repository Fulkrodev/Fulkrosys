"""M18 AEPD — reloj de deadline de notificación a la AEPD (RGPD Art.33 · 72h).

H#54 (FRENTE H · DEC-5 canal AEPD) · gemelo del reloj CCN-CERT/LUCIA (C#35).
Las brechas de datos personales con ``requires_notification = true`` tienen un
plazo de 72h (``aepd_notifications.deadline_hours``) desde su detección
(``detected_at``). Este beat vigila esos plazos y escala a Marcos (M18) cuando se
acercan o vencen mientras la notificación sigue ``pending``. Idempotente.

El árbol de decisión + API + connector ya existían (MB-11.2); lo que faltaba era
el vigilante proactivo del plazo (analogía exacta con C#35).
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from loguru import logger

from backend.app.core.celery_app import celery_app

# Ventana de pre-aviso: escala desde N horas ANTES del vencimiento (y también si
# ya está vencido). 12h sobre un plazo de 72h da margen cómodo a Marcos para
# preparar y enviar la notificación a la sede AEPD dentro del plazo legal.
PRE_WARNING_HOURS = 12


@celery_app.task(name="m18.check_aepd_notification_deadlines")
def check_aepd_notification_deadlines() -> dict:
    """Vigila plazos RGPD Art.33 (72h) de notificación AEPD · escala M18.

    Scheduled: cada hora. Cross-tenant ⇒ ``SET LOCAL ROLE fulkro_app_bypassrls`` (bypass RLS),
    patrón m07/m19/m23.
    """
    try:
        return asyncio.run(_run_check_aepd_deadlines())
    except Exception as exc:  # pragma: no cover · defensive task wrapper
        logger.error(f"M18 check_aepd_notification_deadlines fatal · {exc}")
        return {"status": "failed", "motor": "m18", "error": str(exc)}


async def _run_check_aepd_deadlines(session=None) -> dict:
    """Núcleo del reloj de deadlines AEPD (H#54).

    ``session=None`` (prod): abre su propia sesión, escala a rol fulkro y
    commitea. En tests se inyecta una sesión con rol/contexto y NO commitea
    (el caller gestiona la transacción).
    """
    from sqlalchemy import text as sa_text

    from backend.app.motors.m18_communication.escalation_service import (
        EscalationService,
    )

    owns_session = session is None
    if owns_session:
        from backend.app.database import async_session as _async_session

        _cm = _async_session()
        session = await _cm.__aenter__()

    checked = 0
    escalated = 0
    skipped_existing = 0
    try:
        if owns_session:
            await session.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))

        rows = (await session.execute(sa_text(
            "SELECT id, project_id, severity, deadline_hours, "
            "       detected_at, created_at "
            "FROM aepd_notifications "
            "WHERE notification_status = 'pending' "
            "  AND requires_notification = true "
            "  AND deadline_hours IS NOT NULL"
        ))).mappings().all()

        now = datetime.now(timezone.utc)
        svc = EscalationService()
        for r in rows:
            # detected_at es el origen del cómputo; created_at como fallback.
            origin = r["detected_at"] or r["created_at"]
            if origin is None:
                continue
            if origin.tzinfo is None:
                origin = origin.replace(tzinfo=timezone.utc)
            deadline = origin + timedelta(hours=int(r["deadline_hours"]))
            checked += 1

            # Aún lejos del plazo (más de PRE_WARNING_HOURS de margen) → nada.
            if now < deadline - timedelta(hours=PRE_WARNING_HOURS):
                continue

            # Idempotencia: ¿ya hay escalado abierto para ESTA notificación?
            already = (await session.execute(sa_text(
                "SELECT 1 FROM escalation_events "
                "WHERE project_id = :pid "
                "  AND trigger = 'aepd_deadline_notificacion_72h' "
                "  AND resuelto = false "
                "  AND descripcion LIKE :marker "
                "LIMIT 1"
            ), {"pid": str(r["project_id"]), "marker": f"%id={r['id']}%"})).first()
            if already:
                skipped_existing += 1
                continue

            overdue = now >= deadline
            estado = "VENCIDO" if overdue else "próximo a vencer"
            await svc.create_escalation(
                session,
                r["project_id"],
                "aepd_deadline_notificacion_72h",
                descripcion=(
                    f"Plazo RGPD Art.33 de notificación a la AEPD {estado} (72h) "
                    f"para la brecha {r['severity']} (id={r['id']}, vence "
                    f"{deadline.isoformat()}). Notifica a la AEPD cuanto antes."
                ),
            )
            escalated += 1

        if owns_session:
            await session.commit()
    finally:
        if owns_session:
            await _cm.__aexit__(None, None, None)

    return {
        "status": "ok",
        "motor": "m18",
        "checked": checked,
        "escalated": escalated,
        "skipped_existing": skipped_existing,
    }
