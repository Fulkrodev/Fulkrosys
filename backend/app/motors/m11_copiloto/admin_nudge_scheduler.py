"""Coach proactivo ADMIN · push in-app cuando Marcos lleva tiempo sin entrar (#22).

Espejo de nudge_scheduler (cliente) pero para Marcos:
- compute_pending_admin_nudges: por proyecto activo, la acción admin URGENT del
  scanner, con dos puertas conservadoras (anti-spam · "avisar poco y bien"):
    · INACTIVIDAD: Marcos no ha abierto el copiloto del proyecto en >72h
      (señal = última fila audit_log accion='copilot.hint.generated', que el
      sidebar emite al renderizar el hint).
    · COOLDOWN: no re-nudge de la misma acción/proyecto en <7 días.
  Solo prioridad urgent (nunca normal/low → no molesta por nimiedades).
- dispatch_admin_nudges: escribe un NotificationEvent IN-APP (NO email) que se
  ve en /admin/notifications + el briefing del sidebar, y emite audit_log R6.

Decisiones (Marcos · Ola 5):
- recipient_user_id = NULL (la FK de NotificationEvent es a client_users, NO al
  User admin) · recipient_email = marcos_admin_email · canal "admin_inapp".
- event_type = 'admin.copilot.nudge' · discriminador LIMPIO para no mezclar con
  notificaciones de cliente (el feed filtra por él).

RLS (audit empírico #22): projects+audit_log tienen RLS (audit_log forzado);
clients NO. Para ver todos los proyectos en producción se itera por cliente
fijando contexto (production-safe · sin SET ROLE · sin migración). El nudge
cliente original hace un SELECT projects sin contexto que en prod da 0 (defecto
latente AJENO · no se replica aquí).

ADR-014 sostenido (tracker, no executor). Sub-atom 5.A audit_log 3-way OR.
"""
from __future__ import annotations

import json as _json
import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m11_copiloto.workflow_state_scanner import (
    WorkflowScannerOptions,
    compute_workflow_state,
    top_action_for_role,
)


logger = logging.getLogger(__name__)


ADMIN_NUDGE_EVENT_TYPE = "admin.copilot.nudge"
INACTIVITY_HOURS_DEFAULT = 72   # Marcos sin abrir el proyecto · 3 días lab.
COOLDOWN_DAYS_DEFAULT = 7       # no repetir el mismo aviso en una semana
_ADMIN_INAPP_CHANNEL = "admin_inapp"


@dataclass
class AdminNudge:
    """Aviso proactivo para Marcos · 1 por proyecto inactivo con acción urgent."""

    project_id: str
    project_nombre: Optional[str]
    source_action: str   # canonical (cooldown identity · e.g. 'collect_evidence')
    motor: str
    message: str         # description_admin R30 (tutor)
    phase: str

    def to_dict(self) -> dict:
        return asdict(self)


# ════════════════════════════════════════════════════════════════════
# Private helpers
# ════════════════════════════════════════════════════════════════════


async def _set_project_context(
    db: AsyncSession, *, client_id: uuid.UUID | str, project_id: uuid.UUID | str,
) -> None:
    """Fija contexto RLS (cliente + proyecto) transaction-local."""
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": str(client_id)},
    )
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(project_id)},
    )


async def _clear_context(db: AsyncSession) -> None:
    await db.execute(text("SELECT set_config('app.current_client_id', '', true)"))
    await db.execute(text("SELECT set_config('app.current_project_id', '', true)"))


async def _last_admin_hint_view(
    db: AsyncSession, project_id: uuid.UUID | str,
) -> Optional[datetime]:
    """Última vez que Marcos abrió el copiloto del proyecto (audit_log).

    Requiere current_project_id fijado (audit_log RLS · las filas
    copilot.hint.generated llevan project_id y client_id NULL).
    """
    return (await db.execute(text(
        "SELECT MAX(timestamp) FROM audit_log "
        "WHERE project_id = :pid AND accion = 'copilot.hint.generated'"
    ), {"pid": str(project_id)})).scalar()


async def _has_recent_admin_nudge(
    db: AsyncSession,
    *,
    project_id: uuid.UUID | str,
    source_action: str,
    cooldown_days: int,
) -> bool:
    """Cooldown · ¿ya se avisó de esta acción/proyecto en la ventana?

    Requiere current_project_id fijado (notification_events RLS por project_id).
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=cooldown_days)
    row = (await db.execute(text(
        "SELECT 1 FROM notification_events "
        "WHERE event_type = :et AND project_id = :pid "
        "  AND created_at > :cutoff "
        "  AND payload_jsonb->>'source_action' = :act "
        "LIMIT 1"
    ), {
        "et": ADMIN_NUDGE_EVENT_TYPE,
        "pid": str(project_id),
        "cutoff": cutoff,
        "act": source_action,
    })).fetchone()
    return row is not None


# ════════════════════════════════════════════════════════════════════
# Public API
# ════════════════════════════════════════════════════════════════════


async def compute_pending_admin_nudges(
    db: AsyncSession,
    *,
    inactivity_hours: int = INACTIVITY_HOURS_DEFAULT,
    cooldown_days: int = COOLDOWN_DAYS_DEFAULT,
) -> list[AdminNudge]:
    """Calcula nudges admin pendientes · puro (NO escribe nada · idempotente).

    Itera clientes (sin RLS) → sus proyectos activos (contexto por cliente) y,
    por proyecto inactivo con acción urgent fuera de cooldown, produce 1 nudge.
    """
    now = datetime.now(timezone.utc)
    inactivity_cutoff = now - timedelta(hours=inactivity_hours)
    nudges: list[AdminNudge] = []

    clients = (await db.execute(text(
        "SELECT id, nombre FROM clients WHERE deleted_at IS NULL ORDER BY nombre ASC"
    ))).fetchall()

    for client_id, _client_name in clients:
        await db.execute(
            text("SELECT set_config('app.current_client_id', :cid, true)"),
            {"cid": str(client_id)},
        )
        projects = (await db.execute(text(
            """
            SELECT id, nombre FROM projects
            WHERE client_id = :cid
              AND deleted_at IS NULL
              AND fase != 'pre_venta'
              AND (lifecycle_state IS NULL
                   OR lifecycle_state NOT IN ('ARCHIVED', 'PURGED', 'ENDED_CHURN'))
            """
        ), {"cid": str(client_id)})).fetchall()

        for project_id, project_nombre in projects:
            await db.execute(
                text("SELECT set_config('app.current_project_id', :pid, true)"),
                {"pid": str(project_id)},
            )
            try:
                state = await compute_workflow_state(
                    db, project_id,
                    options=WorkflowScannerOptions(
                        role_filter="admin",
                        include_blockers=False,
                        include_phase_progress=False,
                    ),
                )
            except Exception:
                logger.exception(
                    "admin_nudge · workflow_state failed · project_id=%s",
                    project_id,
                )
                continue

            top = top_action_for_role(state, "admin")
            # Solo urgent · conservador (avisar poco y bien · anti-spam).
            if top is None or top.priority != "urgent":
                continue

            # Puerta de inactividad: si Marcos lo abrió hace poco, NO molestar.
            last_view = await _last_admin_hint_view(db, project_id)
            if last_view is not None and last_view > inactivity_cutoff:
                continue

            # Puerta de cooldown: no repetir el mismo aviso.
            if await _has_recent_admin_nudge(
                db,
                project_id=project_id,
                source_action=top.action,
                cooldown_days=cooldown_days,
            ):
                continue

            nudges.append(AdminNudge(
                project_id=str(project_id),
                project_nombre=project_nombre,
                source_action=top.action,
                motor=top.motor,
                message=top.description_admin,
                phase=state.current_phase,
            ))

    await _clear_context(db)
    return nudges


async def dispatch_admin_nudges(
    db: AsyncSession, nudges: list[AdminNudge],
) -> dict:
    """Despacha nudges admin in-app · best-effort por nudge (NO bloquea siguiente).

    Por nudge: NotificationEvent (in-app · NO email) + audit_log R6. Fija el
    contexto de proyecto antes de cada insert (RLS notification_events + audit_log).
    """
    from backend.app.config import get_settings

    recipient = get_settings().marcos_admin_email or "marcos@fulkro.es"
    channels = _json.dumps([_ADMIN_INAPP_CHANNEL])

    dispatched = 0
    failed = 0
    for nudge in nudges:
        try:
            await db.execute(
                text("SELECT set_config('app.current_project_id', :pid, true)"),
                {"pid": nudge.project_id},
            )
            payload = _json.dumps({
                "title": (
                    f"Acción pendiente · {nudge.project_nombre or 'proyecto'}"
                ),
                "message": nudge.message,
                "motor": nudge.motor,
                "source_action": nudge.source_action,
                "phase": nudge.phase,
                "project_id": nudge.project_id,
                "project_nombre": nudge.project_nombre,
            })
            await db.execute(text(
                "INSERT INTO notification_events "
                "(id, event_type, recipient_user_id, recipient_email, project_id, "
                " channels_attempted, channels_succeeded, channels_failed, "
                " payload_jsonb, status, retry_count, created_at, updated_at) "
                "VALUES (gen_random_uuid(), :et, NULL, :email, :pid, "
                " CAST(:att AS jsonb), CAST(:att AS jsonb), '[]'::jsonb, "
                " CAST(:payload AS jsonb), 'delivered', 0, now(), now())"
            ), {
                "et": ADMIN_NUDGE_EVENT_TYPE,
                "email": recipient,
                "pid": nudge.project_id,
                "att": channels,
                "payload": payload,
            })

            # audit_log R6 · Sub-atom 5.A (project_id propagation).
            await db.execute(text(
                "INSERT INTO audit_log (id, tabla, registro_id, accion, usuario, "
                "project_id, payload_new, timestamp) "
                "VALUES (gen_random_uuid(), 'notification_events', "
                "gen_random_uuid(), 'admin.copilot.nudge.dispatched', "
                "'system_coach_admin', :pid, CAST(:payload AS jsonb), now())"
            ), {
                "pid": nudge.project_id,
                "payload": _json.dumps({
                    "source_action": nudge.source_action,
                    "motor": nudge.motor,
                    "phase": nudge.phase,
                }),
            })
            dispatched += 1
        except Exception:
            failed += 1
            logger.exception(
                "admin_nudge · dispatch failed · project_id=%s action=%s",
                nudge.project_id, nudge.source_action,
            )

    if dispatched > 0:
        try:
            await db.commit()
        except Exception:
            logger.exception("admin_nudge · commit failed")
            failed += dispatched
            dispatched = 0

    await _clear_context(db)
    return {"dispatched": dispatched, "failed": failed, "total": len(nudges)}
