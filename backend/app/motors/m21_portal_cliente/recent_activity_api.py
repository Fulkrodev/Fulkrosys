"""Recent Activity API · SAN-D MB-19.16 cosecha (ADR-035 deepening).

Cubre DEC-MB13-RECENT-ACTIVITY-CARD asignado MB-19 · activity feed
admin home proyecto agrega últimas N entradas de:

- ClientUserAudit hash chain rows (login · evidence_uploaded · etc)
  asociadas a project_id (MB-14.1 hash chain extension).
- ChatThread last messages (futuro · diferido si scope tightens · MB-19.C).
- ClientTask status changes (lifecycle pending → done).
- MagicLink consumed events (audit ClientInteraction).

MB-19.C scope: solo ClientUserAudit + ClientTask · resto MB-20+.

Endpoint:
- GET /api/v1/projects/{project_id}/recent-activity?limit=20
  · admin-only require_owner · serialized últimas 20 actividades

Refs:
- backend/app/models/client_portal.py:ClientUserAudit
- backend/app/motors/m21_portal_cliente/models_tasks.py:ClientTask
- ADR-035 · ADR-038 · DEC-MB13-RECENT-ACTIVITY-CARD
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db, set_tenant_context
from backend.app.models.client_portal import ClientUserAudit
from backend.app.motors.m21_portal_cliente.models_tasks import ClientTask


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/projects",
    tags=["Recent Activity"],
    dependencies=[Depends(require_owner)],
)


# ──────────────────────────────────────────────────────────────────
# Mapping action → human readable label (UI render)
# ──────────────────────────────────────────────────────────────────


_ACTION_LABELS: dict[str, str] = {
    # ClientUserAudit actions
    "LOGIN": "Login portal",
    "login_success": "Login portal exitoso",
    "login_failure": "Login portal fallido",
    "password_change": "Cambio contraseña",
    "account_locked": "Cuenta bloqueada",
    "document_downloaded": "Documento descargado",
    "evidence_uploaded": "Evidencia subida",
    "session_revoked": "Sesión revocada",
    "user_created": "Usuario creado",
    "user_deactivated": "Usuario desactivado",
    "role_changed": "Rol cambiado",
    "first_access_completed": "Primer acceso completado",
    # ClientTask transitions
    "task_started": "Tarea iniciada",
    "task_completed": "Tarea completada",
    "task_blocked": "Tarea bloqueada",
}


def _label_for_action(action: str | None) -> str:
    if not action:
        return "Actividad"
    return _ACTION_LABELS.get(action, action.replace("_", " ").capitalize())


# ──────────────────────────────────────────────────────────────────
# Endpoint
# ──────────────────────────────────────────────────────────────────


@router.get("/{project_id}/recent-activity")
async def get_recent_activity(
    project_id: uuid.UUID,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Lista últimas N actividades del proyecto (audit + tasks).

    Args:
        project_id: UUID Project.
        limit: max items return (default 20 · range 5-100).

    Returns:
        {
          "items": [
            {
              "id": str (UUID),
              "type": "audit" | "task",
              "action": str (raw enum value),
              "label": str (human readable),
              "actor_email": str | None (client_user.email si audit),
              "metadata": dict (JSONB extras),
              "occurred_at": str ISO datetime,
            },
            ...
          ],
          "total": int,
        }

    Raises:
        HTTPException 400 si limit fuera rango 5-100.
    """
    if not (5 <= limit <= 100):
        raise HTTPException(
            status_code=400,
            detail=f"limit fuera rango (5-100) · recibido {limit}",
        )

    # Lookup client_id desde project (RLS chain Marcos owner)
    client_id = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
    )).scalar()
    if not client_id:
        raise HTTPException(
            status_code=404, detail=f"Project {project_id} not found",
        )
    await set_tenant_context(db, client_id=client_id, project_id=project_id)

    items: list[dict[str, Any]] = []

    # ──────────────────────────────────────────────────────────
    # Source 1 · ClientUserAudit (MB-14.1 hash chain)
    # ──────────────────────────────────────────────────────────
    audit_stmt = (
        select(ClientUserAudit)
        .where(ClientUserAudit.project_id == project_id)
        .order_by(ClientUserAudit.created_at.desc())
        .limit(limit)
    )
    audit_rows = list((await db.scalars(audit_stmt)).all())

    # Lookup email per client_user_id (batch · evita N+1)
    client_user_ids = [a.client_user_id for a in audit_rows if a.client_user_id]
    user_email_map: dict[uuid.UUID, str] = {}
    if client_user_ids:
        from backend.app.models.client_portal import ClientUser
        users_stmt = select(ClientUser).where(
            ClientUser.id.in_(client_user_ids),
        )
        for user in (await db.scalars(users_stmt)).all():
            user_email_map[user.id] = user.email

    for audit in audit_rows:
        items.append({
            "id": str(audit.id),
            "type": "audit",
            "action": audit.action,
            "label": _label_for_action(audit.action),
            "actor_email": (
                user_email_map.get(audit.client_user_id)
                if audit.client_user_id else None
            ),
            "metadata": audit.metadata_jsonb or {},
            "occurred_at": (
                audit.created_at.isoformat() if audit.created_at else None
            ),
        })

    # ──────────────────────────────────────────────────────────
    # Source 2 · ClientTask transitions (lifecycle pending → done)
    # ──────────────────────────────────────────────────────────
    # Heuristic: rows con started_at o completed_at recientes son
    # transition events. Iteramos ambos campos para construir items.
    tasks_stmt = (
        select(ClientTask)
        .where(ClientTask.project_id == project_id)
        .where(
            (ClientTask.started_at.is_not(None))
            | (ClientTask.completed_at.is_not(None))
        )
        .order_by(
            (ClientTask.completed_at).desc().nulls_last(),
        )
        .limit(limit)
    )
    task_rows = list((await db.scalars(tasks_stmt)).all())

    for task in task_rows:
        # 1 task puede contribuir 2 events (started + completed) si ambos
        # populated · pero para keep simple agregamos solo el más reciente
        # event per task (completed > started > blocked).
        if task.completed_at:
            items.append({
                "id": f"{task.id}_completed",
                "type": "task",
                "action": "task_completed",
                "label": _label_for_action("task_completed"),
                "actor_email": None,
                "metadata": {
                    "task_id": str(task.id),
                    "title": task.title,
                    "phase": task.phase,
                    "template_id": task.template_id,
                },
                "occurred_at": task.completed_at.isoformat(),
            })
        elif task.started_at:
            items.append({
                "id": f"{task.id}_started",
                "type": "task",
                "action": "task_started",
                "label": _label_for_action("task_started"),
                "actor_email": None,
                "metadata": {
                    "task_id": str(task.id),
                    "title": task.title,
                    "phase": task.phase,
                    "template_id": task.template_id,
                },
                "occurred_at": task.started_at.isoformat(),
            })

    # ──────────────────────────────────────────────────────────
    # Combine + sort by occurred_at DESC + apply limit
    # ──────────────────────────────────────────────────────────
    items.sort(key=lambda x: x["occurred_at"] or "", reverse=True)
    items = items[:limit]

    return {"items": items, "total": len(items)}
