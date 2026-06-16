"""M19 Risk — tasks programadas.

C#35 (FRENTE C) · reloj de deadline de notificación CCN-CERT/LUCIA (Art.33).
Los incidentes critical/high con routing lucia/manual tienen plazo 24/72h
(decision tree CCN-CERT · persistido en
``incidents.ccn_cert_routing_decision.deadline_hours``). Este beat vigila esos
plazos y escala a Marcos (M18) cuando se acercan o vencen y el incidente AÚN no
se ha notificado (``reported_to_ccn_cert_at IS NULL``). Idempotente.
"""
from __future__ import annotations

import asyncio
import json as _json
from datetime import datetime, timedelta, timezone

from loguru import logger

from backend.app.core.celery_app import celery_app

# Ventana de pre-aviso: escala desde N horas ANTES del vencimiento (y también
# si ya está vencido) para que Marcos llegue a tiempo al plazo legal Art.33.
PRE_WARNING_HOURS = 6


@celery_app.task(name="m19.check_incident_notification_deadlines")
def check_incident_notification_deadlines() -> dict:
    """Vigila plazos Art.33 de notificación CCN-CERT/LUCIA · escala M18.

    Scheduled: cada hora (un plazo de 24h exige aviso oportuno). Cross-tenant ⇒
    ``SET LOCAL ROLE fulkro_app_bypassrls`` (bypass RLS), patrón m07/m23.
    """
    try:
        return asyncio.run(_run_check_incident_deadlines())
    except Exception as exc:  # pragma: no cover · defensive task wrapper
        logger.error(f"M19 check_incident_notification_deadlines fatal · {exc}")
        return {"status": "failed", "motor": "m19", "error": str(exc)}


async def _run_check_incident_deadlines(session=None) -> dict:
    """Núcleo del reloj de deadlines (C#35).

    ``session=None`` (prod): abre su propia sesión, escala a rol fulkro y
    commitea. En tests se inyecta una sesión con rol/contexto y NO commitea
    (el caller gestiona la transacción).
    """
    from sqlalchemy import text as sa_text

    from backend.app.motors.m18_communication.escalation_service import (
        EscalationService,
        source_ref_like,
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
            "SELECT id, project_id, fecha, severidad, "
            "       ccn_cert_routing_decision "
            "FROM incidents "
            "WHERE reported_to_ccn_cert_at IS NULL "
            "  AND notificado_lucia = false "
            "  AND deleted_at IS NULL "
            "  AND ccn_cert_routing_decision IS NOT NULL"
        ))).mappings().all()

        now = datetime.now(timezone.utc)
        svc = EscalationService()
        for r in rows:
            routing = r["ccn_cert_routing_decision"]
            if isinstance(routing, str):
                try:
                    routing = _json.loads(routing)
                except ValueError:
                    routing = {}
            deadline_hours = (routing or {}).get("deadline_hours")
            if not deadline_hours:
                continue  # internal_only · sin plazo legal

            fecha = r["fecha"]
            if fecha is None:
                continue
            if fecha.tzinfo is None:
                fecha = fecha.replace(tzinfo=timezone.utc)
            deadline = fecha + timedelta(hours=int(deadline_hours))
            checked += 1

            # Aún lejos del plazo (más de PRE_WARNING_HOURS de margen) → nada.
            if now < deadline - timedelta(hours=PRE_WARNING_HOURS):
                continue

            # Idempotencia por origen estructurado (WAVE C1 · §4.4/370): marcador
            # canónico [src:<id>] en vez de un UUID embebido en la prosa.
            already = (await session.execute(sa_text(
                "SELECT 1 FROM escalation_events "
                "WHERE project_id = :pid "
                "  AND trigger = 'incidente_deadline_notificacion_lucia' "
                "  AND resuelto = false "
                "  AND descripcion LIKE :marker "
                "LIMIT 1"
            ), {"pid": str(r["project_id"]), "marker": source_ref_like(str(r["id"]))})).first()
            if already:
                skipped_existing += 1
                continue

            overdue = now >= deadline
            estado = "VENCIDO" if overdue else "próximo a vencer"
            await svc.create_escalation(
                session,
                r["project_id"],
                "incidente_deadline_notificacion_lucia",
                descripcion=(
                    f"Plazo Art.33 de notificación CCN-CERT/LUCIA {estado} "
                    f"({deadline_hours}h) para el incidente {r['severidad']} "
                    f"(vence {deadline.isoformat()}). "
                    f"Notifica al CCN-CERT/LUCIA cuanto antes."
                ),
                source_ref=str(r["id"]),
            )
            escalated += 1

        if owns_session:
            await session.commit()
    finally:
        if owns_session:
            await _cm.__aexit__(None, None, None)

    return {
        "status": "ok",
        "motor": "m19",
        "checked": checked,
        "escalated": escalated,
        "skipped_existing": skipped_existing,
    }
