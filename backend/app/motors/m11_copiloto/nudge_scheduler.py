"""Coach proactivo · nudge scheduler service (Sesión 3B-2B.8 CLUSTER 2 Phase 2C).

compute_pending_nudges + dispatch_nudges · pure functional + best-effort
dispatch · cooldown-aware via ClientNotification.payload.source history.

Pattern #15 cumulative · Proactive nudge scheduler pure functional:
- mirror Phase C3 compute_dda_evidence_gaps + Phase 1D compute_workflow_state
- NO HTTP coupling · NO ORM coupling (raw SQL preferred where empirical faster)
- compute = NO side effects · dispatch = best-effort emit (independent)
- JSON-serializable (asdict-friendly)
- Reusable cross-consumer: Sesión 3B-2B.9 admin proactivity + Sesión 3B-2B.10
  simulacro engine forward-compat

Filosofía cliente-mínimo guards:
- Priority cap = "high" (NO "urgent" · evitar presión psicológica)
- Cooldown 24h prevents spam
- R29 friendly tone preserved (descriptions Phase 1D ya R29 compliant)
- role_filter='cliente' enforced (NO admin actions surface cliente nudges)
- audit_log Sub-atom 5.A propagation (project_id + client_id 3-way OR)

ADR-013 doble pool sostained · ADR-014 cliente VE/RECIBE (NO operations).
"""
from __future__ import annotations

import json as _json
import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.client_portal import ClientUser
from backend.app.motors.m11_copiloto.workflow_state_scanner import (
    WorkflowScannerOptions,
    compute_workflow_state,
)


logger = logging.getLogger(__name__)


# Cliente-mínimo guard · priority cap = "high" · NO "urgent" para evitar
# presión psicológica. Mapping Phase 1D action priority → nudge priority.
_PRIORITY_MAP: dict[str, str] = {
    "urgent": "high",  # cap · evitar presión cliente
    "normal": "normal",
    "low": "low",
}

_NUDGE_COOLDOWN_HOURS_DEFAULT = 24

# Notification type taxonomy reuse Phase 2B VALID_TYPES.
_NUDGE_NOTIFICATION_TYPE = "generic_alert"


@dataclass
class NudgeAction:
    """Acción nudge derivada per cliente · cooldown-aware dispatch ready."""

    project_id: str
    client_user_id: str
    source_action: str  # canonical key (e.g. 'sign_dda') · cooldown identity
    motor: str  # m01 · m02 · etc · audit_log payload
    title: str  # R29 friendly Spanish
    body: str  # context + R29 friendly tone
    priority: str  # low | normal | high (NO urgent)
    target_url: str
    notification_type: str  # generic_alert (default)

    def to_dict(self) -> dict:
        """JSON-serializable · cross consumer compat."""
        return asdict(self)


# ════════════════════════════════════════════════════════════════════
# Private helpers
# ════════════════════════════════════════════════════════════════════


async def _list_active_projects(db: AsyncSession) -> list[tuple[uuid.UUID, uuid.UUID]]:
    """Active projects + client_id · cross-cliente · production-safe bajo RLS.

    Active = NOT pre_venta (sin contrato) AND NOT lifecycle_state ARCHIVED/PURGED.
    Cliente-mínimo: NUNCA scan dormant projects (sin cliente activo).

    FIX Ola 5 (defecto latente): `projects` tiene FORCE RLS (client_isolation
    por current_client_id) y `clients` NO. Un SELECT directo sin contexto da 0
    filas como fulkro_app en producción (el beat corría en vacío). Se itera por
    cliente (legible) fijando su contexto · mirror admin_nudge_scheduler. Los
    tests inyectaban un único contexto y por eso pasaban; este fix lo hace
    correcto también en el beat real.
    """
    out: list[tuple[uuid.UUID, uuid.UUID]] = []
    clients = (await db.execute(
        text("SELECT id FROM clients WHERE deleted_at IS NULL")
    )).fetchall()
    for (client_id,) in clients:
        await db.execute(
            text("SELECT set_config('app.current_client_id', :cid, true)"),
            {"cid": str(client_id)},
        )
        rows = (await db.execute(text(
            "SELECT id FROM projects "
            "WHERE client_id = :cid "
            "  AND deleted_at IS NULL "
            "  AND fase != 'pre_venta' "
            "  AND (lifecycle_state IS NULL OR lifecycle_state NOT IN "
            "       ('ARCHIVED', 'PURGED', 'ENDED_CHURN'))"
        ), {"cid": str(client_id)})).fetchall()
        for (project_id,) in rows:
            out.append((project_id, client_id))
    # Limpia el contexto de cliente (defence-in-depth · el loop lo re-fija).
    await db.execute(text("SELECT set_config('app.current_client_id', '', true)"))
    return out


async def _list_active_users_for_client(
    db: AsyncSession, client_id: uuid.UUID,
) -> list[ClientUser]:
    """Lookup ClientUser activos per client_id · pilot single-user assumption ok."""
    res = await db.execute(
        select(ClientUser).where(
            ClientUser.client_id == client_id,
            ClientUser.deactivated_at.is_(None),
        )
    )
    return list(res.scalars().all())


async def _has_recent_nudge(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    client_user_id: uuid.UUID,
    source_action: str,
    cooldown_hours: int,
) -> bool:
    """Cooldown check · query ClientNotification.payload.source history.

    Source key canonical: f'coach_nudge:{source_action}'. Skip si created_at
    > now - cooldown_hours.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=cooldown_hours)
    source_key = f"coach_nudge:{source_action}"

    res = await db.execute(text(
        "SELECT 1 FROM client_notifications "
        "WHERE project_id = :pid "
        "  AND client_user_id = :uid "
        "  AND created_at > :cutoff "
        "  AND payload_json->>'source' = :src "
        "LIMIT 1"
    ), {
        "pid": str(project_id),
        "uid": str(client_user_id),
        "cutoff": cutoff,
        "src": source_key,
    })
    return res.fetchone() is not None


def _ensure_friendly_body(body: str) -> str:
    """R29 guard · embed "Sin prisa · cuando puedas" si NOT present.

    Phase 1D descriptions ya R29 compliant pero descriptions varían per phase.
    Safety embed para garantizar tono friendly post-composition.
    """
    if not body:
        return "Sin prisa por tu parte · cuando puedas."
    body_lower = body.lower()
    if "sin prisa" in body_lower or "cuando puedas" in body_lower:
        return body
    return f"{body.rstrip('.')}. Sin prisa por tu parte · cuando puedas."


# ════════════════════════════════════════════════════════════════════
# Public API
# ════════════════════════════════════════════════════════════════════


async def compute_pending_nudges(
    db: AsyncSession,
    *,
    cooldown_hours: int = _NUDGE_COOLDOWN_HOURS_DEFAULT,
) -> list[NudgeAction]:
    """Compute pending nudges cross all active projects · pure functional.

    Steps:
      1. List active projects (NOT pre_venta · NOT ARCHIVED/PURGED/ENDED_CHURN)
      2. Per project: compute_workflow_state(role_filter='cliente') Phase 1D reuse
      3. Per top cliente action (priority urgent|normal · skip low): build NudgeAction
      4. Cooldown filter: skip si recent dispatch <cooldown_hours
      5. Return filtered list ordered priority high → normal → low

    Pure functional · NO side effects · idempotent. Reusable cross-consumer.
    """
    nudges: list[NudgeAction] = []
    projects = await _list_active_projects(db)

    for project_id, client_id in projects:
        # Producción: fijar contexto RLS por proyecto ANTES de los reads. Sin
        # esto, como fulkro_app, compute_workflow_state / users / cooldown no ven
        # el proyecto (projects+dda+client_notifications scoped por RLS).
        await db.execute(
            text("SELECT set_config('app.current_client_id', :cid, true)"),
            {"cid": str(client_id)},
        )
        await db.execute(
            text("SELECT set_config('app.current_project_id', :pid, true)"),
            {"pid": str(project_id)},
        )
        try:
            state = await compute_workflow_state(
                db, project_id,
                options=WorkflowScannerOptions(
                    role_filter="cliente",
                    include_blockers=False,  # blockers visible via UI separate
                    include_phase_progress=False,
                ),
            )
        except Exception:
            logger.exception(
                "coach.compute_pending_nudges · workflow_state failed · "
                "project_id=%s",
                project_id,
            )
            continue

        # Filter cliente actions priority urgent|normal · skip low (NO spam)
        candidate_actions = [
            a for a in state.next_cliente_actions
            if a.priority in ("urgent", "normal")
        ]
        if not candidate_actions:
            continue

        # Top action per priority (urgent > normal · weight)
        sorted_actions = sorted(
            candidate_actions,
            key=lambda a: 0 if a.priority == "urgent" else 1,
        )
        top_action = sorted_actions[0]

        # Cliente-mínimo guard · cap priority "urgent" → "high"
        nudge_priority = _PRIORITY_MAP.get(top_action.priority, "normal")

        # Lookup active users for client (pilot single-user)
        users = await _list_active_users_for_client(db, client_id)
        for user in users:
            recent = await _has_recent_nudge(
                db,
                project_id=project_id,
                client_user_id=user.id,
                source_action=top_action.action,
                cooldown_hours=cooldown_hours,
            )
            if recent:
                continue

            title_phase = state.current_phase.replace("_", " ").title()
            body_friendly = _ensure_friendly_body(top_action.description_cliente)

            nudges.append(NudgeAction(
                project_id=str(project_id),
                client_user_id=str(user.id),
                source_action=top_action.action,
                motor=top_action.motor,
                title=f"Recordatorio · {title_phase}",
                body=body_friendly,
                priority=nudge_priority,
                target_url=top_action.target_url,
                notification_type=_NUDGE_NOTIFICATION_TYPE,
            ))

    # Order final · high first (nudges UI priority sorting)
    nudges.sort(
        key=lambda n: {"high": 0, "normal": 1, "low": 2}.get(n.priority, 3),
    )
    return nudges


async def dispatch_nudges(
    db: AsyncSession, nudges: list[NudgeAction],
) -> dict:
    """Dispatch nudges best-effort · per-nudge independent try/except.

    Per nudge:
      1. emit_client_notification (Phase 2B pattern · payload source=coach_nudge:{key})
      2. audit_log emit coach.nudge.dispatched (Sub-atom 5.A 3-way OR)
      3. try/except logger.exception (NO bloquea siguiente nudge)

    Returns: dict {dispatched: int, failed: int, total: int}
    """
    from backend.app.motors.m21_portal_cliente.notification_service import (
        emit_client_notification,
    )

    dispatched = 0
    failed = 0

    from backend.app.database import set_tenant_context

    for nudge in nudges:
        try:
            # Set RLS tenant context per nudge · ClientNotification project_id
            # isolation policy requires `app.current_project_id` match row.
            # Lookup client_id via projects table (RLS-visible per project
            # creation context · safer than client_users which may RLS-hide).
            client_id_row = (await db.execute(
                text(
                    "SELECT client_id FROM projects WHERE id = :pid"
                ),
                {"pid": nudge.project_id},
            )).fetchone()
            if client_id_row:
                await set_tenant_context(
                    db,
                    client_id=client_id_row[0],
                    project_id=uuid.UUID(nudge.project_id),
                )

            await emit_client_notification(
                db,
                project_id=uuid.UUID(nudge.project_id),
                client_user_id=uuid.UUID(nudge.client_user_id),
                type=nudge.notification_type,
                title=nudge.title,
                body=nudge.body,
                target_url=nudge.target_url,
                priority=nudge.priority,
                emitted_by_motor="m11_copiloto_coach",
                payload={
                    "source": f"coach_nudge:{nudge.source_action}",
                    "motor": nudge.motor,
                    "source_action": nudge.source_action,
                },
            )

            # audit_log emit coach.nudge.dispatched · Sub-atom 5.A 3-way OR
            await db.execute(text(
                "INSERT INTO audit_log (id, tabla, registro_id, accion, usuario, "
                "project_id, client_id, payload_new, timestamp) "
                "SELECT gen_random_uuid(), 'client_notifications', :pid, "
                "'coach.nudge.dispatched', 'system_coach', :pid, c.id, "
                ":payload, now() "
                "FROM client_users cu JOIN clients c ON cu.client_id = c.id "
                "WHERE cu.id = :uid"
            ), {
                "pid": nudge.project_id,
                "uid": nudge.client_user_id,
                "payload": _json.dumps({
                    "source_action": nudge.source_action,
                    "motor": nudge.motor,
                    "priority": nudge.priority,
                }),
            })

            dispatched += 1
        except Exception:
            failed += 1
            logger.exception(
                "coach.dispatch_nudges · single nudge failed · "
                "project_id=%s action=%s",
                nudge.project_id, nudge.source_action,
            )

    if dispatched > 0:
        try:
            await db.commit()
        except Exception:
            logger.exception("coach.dispatch_nudges · commit failed")
            failed += dispatched
            dispatched = 0

    return {
        "dispatched": dispatched,
        "failed": failed,
        "total": len(nudges),
    }
