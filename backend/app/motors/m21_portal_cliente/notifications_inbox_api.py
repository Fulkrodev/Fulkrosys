"""API endpoints ClientNotification inbox (SAN-E v3.MB-4.bis3 · ADR-020).

Cliente accede sus notifications · marca read/dismissed/actioned.
Auth: ClientUser session (cookie + CSRF triple binding).

Rutas (prefix /api/v1/portal/inbox):
- GET  /                        · list notifications
- GET  /count-unread            · badge count
- POST /{id}/mark-read          · marca leída
- POST /{id}/dismiss            · descartar
- POST /{id}/mark-actioned      · cliente clicked target_url

NO emit endpoint público · motors backend llaman directamente
notification_service.emit_client_notification().
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models.client_portal import ClientUser
from backend.app.motors.m21_portal_cliente import notification_service
from backend.app.motors.m21_portal_cliente.api import get_current_client_user


router = APIRouter(
    prefix="/api/v1/portal/inbox",
    tags=["m21-notifications-inbox"],
)


# ──────────────── Schemas ────────────────

class NotificationOut(BaseModel):
    id: str
    type: str
    title: str
    body: str | None = None
    target_url: str
    priority: str
    payload: dict | None = None
    emitted_by_motor: str
    read_at: str | None = None
    dismissed_at: str | None = None
    actioned_at: str | None = None
    expires_at: str | None = None
    created_at: str


class InboxResponse(BaseModel):
    notifications: list[NotificationOut]
    total: int
    has_more: bool


class CountUnreadResponse(BaseModel):
    count: int


class ActionResponse(BaseModel):
    ok: bool


# ──────────────── Helpers ────────────────

def _to_out(n) -> NotificationOut:
    return NotificationOut(
        id=str(n.id),
        type=n.type,
        title=n.title,
        body=n.body,
        target_url=n.target_url,
        priority=n.priority,
        payload=n.payload_json,
        emitted_by_motor=n.emitted_by_motor,
        read_at=n.read_at.isoformat() if n.read_at else None,
        dismissed_at=n.dismissed_at.isoformat() if n.dismissed_at else None,
        actioned_at=n.actioned_at.isoformat() if n.actioned_at else None,
        expires_at=n.expires_at.isoformat() if n.expires_at else None,
        created_at=n.created_at.isoformat() if n.created_at else "",
    )


async def _set_inbox_rls(db: AsyncSession, user: ClientUser) -> None:
    """Fija el contexto de tenant del cliente para que la RLS de
    client_notifications (por project_id/client_id) NO deje el inbox vacío en
    producción (fail-closed). El service además filtra por client_user_id, así
    que esto es defensa en profundidad. Patrón chat_api._resolve_client_project_id.
    """
    from sqlalchemy import text as _t
    await db.execute(
        _t("SELECT set_config('app.current_client_id', :c, true)"),
        {"c": str(user.client_id)},
    )
    row = (await db.execute(_t(
        "SELECT id FROM projects WHERE client_id = :c AND deleted_at IS NULL "
        "ORDER BY created_at DESC LIMIT 1"
    ), {"c": str(user.client_id)})).first()
    if row is not None:
        await db.execute(
            _t("SELECT set_config('app.current_project_id', :p, true)"),
            {"p": str(row[0])},
        )


# ──────────────── Endpoints ────────────────

@router.get("", response_model=InboxResponse)
async def list_inbox(
    include_read: bool = Query(False),
    include_dismissed: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> InboxResponse:
    await _set_inbox_rls(db, user)
    notifications = await notification_service.list_inbox(
        db, user.id,
        include_read=include_read,
        include_dismissed=include_dismissed,
        limit=limit + 1,  # peek next page
        offset=offset,
    )
    has_more = len(notifications) > limit
    notifications = notifications[:limit]
    return InboxResponse(
        notifications=[_to_out(n) for n in notifications],
        total=len(notifications),
        has_more=has_more,
    )


@router.get("/count-unread", response_model=CountUnreadResponse)
async def count_unread(
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> CountUnreadResponse:
    await _set_inbox_rls(db, user)
    count = await notification_service.count_unread(db, user.id)
    return CountUnreadResponse(count=count)


@router.post("/{notification_id}/mark-read", response_model=ActionResponse)
async def mark_read(
    notification_id: uuid.UUID,
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> ActionResponse:
    await _set_inbox_rls(db, user)
    ok = await notification_service.mark_read(db, notification_id, user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Notification not found")
    await db.commit()
    return ActionResponse(ok=True)


class MarkAllReadResponse(BaseModel):
    ok: bool
    marked_count: int


@router.post("/mark-all-read", response_model=MarkAllReadResponse)
async def mark_all_read_endpoint(
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> MarkAllReadResponse:
    """Mark every unread notification of the user as read · MB-7 atom 7.4."""
    await _set_inbox_rls(db, user)
    n = await notification_service.mark_all_read(db, user.id)
    await db.commit()
    return MarkAllReadResponse(ok=True, marked_count=n)


@router.post("/{notification_id}/dismiss", response_model=ActionResponse)
async def dismiss(
    notification_id: uuid.UUID,
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> ActionResponse:
    await _set_inbox_rls(db, user)
    ok = await notification_service.dismiss(db, notification_id, user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Notification not found")
    await db.commit()
    return ActionResponse(ok=True)


@router.post("/{notification_id}/mark-actioned", response_model=ActionResponse)
async def mark_actioned(
    notification_id: uuid.UUID,
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> ActionResponse:
    await _set_inbox_rls(db, user)
    ok = await notification_service.mark_actioned(db, notification_id, user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Notification not found")
    await db.commit()
    return ActionResponse(ok=True)
