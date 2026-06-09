"""API endpoints NotificationOrchestrator MB-16.5 (ADR-039).

Routers:

- ``portal_router`` (cliente · ``require_client_user``) ·
  ``/api/v1/portal/notifications/preferences`` GET/PUT.

- ``admin_router`` (Marcos · ``require_owner``) ·
  ``/api/v1/admin/notifications/events`` GET listado eventos +
  ``POST /events/{id}/redispatch`` para manual replay diagnostic.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_client_user, require_owner
from backend.app.database import get_db
from backend.app.models.client_portal import ClientUser
from backend.app.models.notifications import (
    NotificationEvent,
    NotificationPreference,
    VALID_DIGEST_MODES,
    VALID_NOTIFICATION_STATUSES,
)
from backend.app.notifications.dnd import parse_hhmm
from backend.app.notifications.tasks import (
    redispatch_event_with_session,
)


_HHMM_VALIDATOR_MSG = "Formato HH:MM 24h requerido"


# ──────────────── Schemas ────────────────


class NotificationPreferenceRead(BaseModel):
    id: uuid.UUID
    client_user_id: uuid.UUID
    email_enabled: bool
    portal_sse_enabled: bool
    dnd_start_local: str | None
    dnd_end_local: str | None
    timezone: str
    digest_mode: str
    # CLUSTER 5 Phase 5E delta · WhatsApp + per-event opt-outs granular.
    whatsapp_enabled: bool
    event_opt_outs: dict[str, bool]
    created_at: datetime
    updated_at: datetime | None


class NotificationPreferenceUpdate(BaseModel):
    email_enabled: bool | None = None
    portal_sse_enabled: bool | None = None
    dnd_start_local: str | None = Field(default=None)
    dnd_end_local: str | None = Field(default=None)
    timezone: str | None = None
    digest_mode: str | None = None
    # CLUSTER 5 Phase 5E delta
    whatsapp_enabled: bool | None = None
    event_opt_outs: dict[str, bool] | None = None

    @field_validator("dnd_start_local", "dnd_end_local")
    @classmethod
    def _validate_hhmm(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        if parse_hhmm(v) is None:
            raise ValueError(_HHMM_VALIDATOR_MSG)
        return v

    @field_validator("digest_mode")
    @classmethod
    def _validate_digest(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in VALID_DIGEST_MODES:
            raise ValueError(
                f"digest_mode debe estar en {VALID_DIGEST_MODES}"
            )
        return v


class NotificationEventRead(BaseModel):
    id: uuid.UUID
    event_type: str
    recipient_user_id: uuid.UUID | None
    recipient_email: str
    project_id: uuid.UUID | None
    channels_attempted: list[str]
    channels_succeeded: list[str]
    channels_failed: list[str]
    status: str
    error: str | None
    template_used: str | None
    retry_count: int
    payload_jsonb: dict[str, Any]
    created_at: datetime
    dispatched_at: datetime | None
    delivered_at: datetime | None


class NotificationEventsListResponse(BaseModel):
    items: list[NotificationEventRead]
    total: int
    limit: int
    offset: int


class RedispatchResponse(BaseModel):
    status: str
    event_id: str | None = None
    channels_succeeded: list[str] | None = None
    channels_failed: list[str] | None = None


# ──────────────── Routers ────────────────


portal_router = APIRouter(
    prefix="/portal/notifications",
    tags=["Portal Cliente - Notifications (MB-16)"],
)

admin_router = APIRouter(
    prefix="/admin/notifications",
    tags=["Admin - Notifications Center (MB-16)"],
)


# ──────────────── Cliente endpoints ────────────────


def _serialize_pref(pref: NotificationPreference) -> NotificationPreferenceRead:
    return NotificationPreferenceRead(
        id=pref.id,
        client_user_id=pref.client_user_id,
        email_enabled=pref.email_enabled,
        portal_sse_enabled=pref.portal_sse_enabled,
        dnd_start_local=pref.dnd_start_local,
        dnd_end_local=pref.dnd_end_local,
        timezone=pref.timezone,
        digest_mode=pref.digest_mode,
        whatsapp_enabled=pref.whatsapp_enabled,
        event_opt_outs=dict(pref.event_opt_outs or {}),
        created_at=pref.created_at,
        updated_at=pref.updated_at,
    )


async def _set_client_user_rls_context(
    db: AsyncSession, user: ClientUser,
) -> None:
    """Setea ``app.current_client_user_id`` para RLS policy de
    ``notification_preferences``.
    """
    from sqlalchemy import text as _sa_text

    await db.execute(
        _sa_text(
            "SELECT set_config('app.current_client_user_id', :uid, true)"
        ),
        {"uid": str(user.id)},
    )


async def _get_or_create_pref(
    db: AsyncSession,
    user: ClientUser,
) -> NotificationPreference:
    await _set_client_user_rls_context(db, user)
    result = await db.execute(
        select(NotificationPreference).where(
            NotificationPreference.client_user_id == user.id
        )
    )
    pref = result.scalar_one_or_none()
    if pref is not None:
        return pref
    pref = NotificationPreference(client_user_id=user.id)
    db.add(pref)
    await db.flush()
    await db.refresh(pref)
    return pref


@portal_router.get(
    "/preferences",
    response_model=NotificationPreferenceRead,
)
async def get_my_preferences(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[ClientUser, Depends(require_client_user)],
):
    pref = await _get_or_create_pref(db, user)
    return _serialize_pref(pref)


@portal_router.put(
    "/preferences",
    response_model=NotificationPreferenceRead,
)
async def update_my_preferences(
    payload: NotificationPreferenceUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[ClientUser, Depends(require_client_user)],
):
    pref = await _get_or_create_pref(db, user)

    data = payload.model_dump(exclude_unset=True)

    if "dnd_start_local" in data or "dnd_end_local" in data:
        new_start = data.get("dnd_start_local", pref.dnd_start_local)
        new_end = data.get("dnd_end_local", pref.dnd_end_local)
        if (new_start is None) != (new_end is None):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "dnd_start_local y dnd_end_local deben configurarse "
                    "juntos o ambos null"
                ),
            )

    for field, value in data.items():
        setattr(pref, field, value)

    await db.flush()
    await db.refresh(pref)
    return _serialize_pref(pref)


# ──────────────── Admin endpoints ────────────────


def _serialize_event(event: NotificationEvent) -> NotificationEventRead:
    return NotificationEventRead(
        id=event.id,
        event_type=event.event_type,
        recipient_user_id=event.recipient_user_id,
        recipient_email=event.recipient_email,
        project_id=event.project_id,
        channels_attempted=event.channels_attempted or [],
        channels_succeeded=event.channels_succeeded or [],
        channels_failed=event.channels_failed or [],
        status=event.status,
        error=event.error,
        template_used=event.template_used,
        retry_count=event.retry_count,
        payload_jsonb=event.payload_jsonb or {},
        created_at=event.created_at,
        dispatched_at=event.dispatched_at,
        delivered_at=event.delivered_at,
    )


async def _set_admin_rls_context(db: AsyncSession) -> None:
    """Marca contexto admin para RLS policies que respetan role_pool.

    ``notification_preferences`` policy usa
    ``current_setting('app.current_role_pool') = 'marcos'`` para
    permitir cross-tenant. Para ``notification_events`` (project_id
    scoped) Marcos owner bypass via SET LOCAL ROLE superuser dentro
    del request scope.
    """
    from sqlalchemy import text as _sa_text

    await db.execute(
        _sa_text(
            "SELECT set_config('app.current_role_pool', 'marcos', true)"
        ),
    )
    await db.execute(_sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))


@admin_router.get(
    "/events",
    response_model=NotificationEventsListResponse,
)
async def list_events(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    _owner=Depends(require_owner),
    status_filter: Annotated[
        str | None,
        Query(alias="status", description=(
            f"Filtra por status. Valores válidos: {VALID_NOTIFICATION_STATUSES}"
        )),
    ] = None,
    event_type: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    await _set_admin_rls_context(db)
    base = select(NotificationEvent)
    if status_filter:
        if status_filter not in VALID_NOTIFICATION_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"status inválido · valores permitidos: "
                    f"{VALID_NOTIFICATION_STATUSES}"
                ),
            )
        base = base.where(NotificationEvent.status == status_filter)
    if event_type:
        base = base.where(NotificationEvent.event_type == event_type)

    total_result = await db.execute(
        base.with_only_columns(NotificationEvent.id).order_by(None)
    )
    total = len(total_result.scalars().all())

    page = await db.execute(
        base.order_by(desc(NotificationEvent.created_at))
        .offset(offset)
        .limit(limit)
    )
    items = page.scalars().all()
    return NotificationEventsListResponse(
        items=[_serialize_event(e) for e in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@admin_router.post(
    "/events/{event_id}/redispatch",
    response_model=RedispatchResponse,
)
async def redispatch_event(
    event_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _owner=Depends(require_owner),
):
    await _set_admin_rls_context(db)
    result = await redispatch_event_with_session(db, str(event_id))
    return RedispatchResponse(
        status=result.get("status", "unknown"),
        event_id=result.get("event_id"),
        channels_succeeded=result.get("channels_succeeded"),
        channels_failed=result.get("channels_failed"),
    )


__all__ = ["portal_router", "admin_router"]
