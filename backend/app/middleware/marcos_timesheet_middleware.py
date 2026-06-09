"""Marcos timesheet auto-track middleware · MB-7.bis closure Q6.C.

Auto-tracks API requests made by Marcos against tracked endpoints into
``marcos_timesheet_entries`` so the timesheet UI + CapacityTile work
without manual entry for every interaction.

Aggregates consecutive requests into 30-second windows to avoid one
entry per click. Best-effort persistence: failures never block the
response.

Tracked paths (regex):
  /api/v1/projects/{id}/*
  /api/v1/admin/retainers/{id}/*  (and /retainer/ legacy alias)
  /api/v1/admin/whatsapp/threads/{id}/*
"""
from __future__ import annotations

import logging
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


logger = logging.getLogger(__name__)


# Path patterns we consider billable interactions with a client project.
# Each pattern's group 1 is the project_id or retainer_id we use as
# context for the timesheet entry.
_TRACKED_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^/api/v1/projects/([0-9a-fA-F-]{36})/"), "project_id"),
    (re.compile(r"^/api/v1/admin/retainers?/([0-9a-fA-F-]{36})/"), "retainer_id"),
    (
        re.compile(
            r"^/api/v1/admin/whatsapp/threads/([0-9a-fA-F-]{36})/"
        ),
        "thread_id",
    ),
]

AGGREGATE_WINDOW_SECONDS = 30
_SAFE_METHODS = {"OPTIONS", "HEAD"}


# In-memory per-process aggregation buffer · key=(marcos_user_id, ctx_id)
# value=(last_seen_iso, entry_id). Cleared on process restart · not a
# correctness concern (durability is in the DB · this is just batching).
_active_sessions: dict[tuple[str, str], tuple[float, str]] = {}


def _match_tracked(path: str) -> tuple[Optional[str], Optional[str]]:
    """Return (context_kind, uuid_str) for the first matching pattern."""
    for pattern, kind in _TRACKED_PATTERNS:
        m = pattern.match(path)
        if m:
            return kind, m.group(1)
    return None, None


def _is_marcos(email: str | None, owners: list[str]) -> bool:
    if not email:
        return False
    return email.lower() in {o.lower() for o in owners}


class MarcosTimesheetMiddleware(BaseHTTPMiddleware):
    """Auto-track Marcos API hits on tracked endpoints into timesheet."""

    async def dispatch(self, request: Request, call_next):
        method = request.method.upper()
        path = request.url.path

        if method in _SAFE_METHODS:
            return await call_next(request)

        kind, ctx_id = _match_tracked(path)
        if ctx_id is None:
            return await call_next(request)

        # Always let the response complete first; tracking is side-effect.
        response = await call_next(request)

        # Identify Marcos AFTER request handler so auth context is set.
        # Reuse request.state.auth_subject set by global authenticate_request
        # dep (matches conftest test stub Marcos pattern).
        #
        # IMPORTANTE: leemos ``subject.email`` (string plano capturado en auth,
        # ver AuthSubject.__slots__) y NO ``subject.user.email``. El ``user`` es
        # un ORM cuya sesión get_db ya está cerrada tras call_next → tocar un
        # atributo lazy lanza DetachedInstanceError fuera del try/except (que
        # sólo envuelve _persist_or_extend), provocando un 500 en TODOS los POST
        # project-scoped de Marcos (incl. autopilot start). Defensivo además.
        subject = getattr(request.state, "auth_subject", None)
        try:
            email = getattr(subject, "email", None)
        except Exception:  # noqa: BLE001 — ORM detached / cualquier acceso lazy
            email = None

        from backend.app.config import get_settings
        settings = get_settings()
        owners = [settings.marcos_admin_email] if settings.marcos_admin_email else []
        if not _is_marcos(email, owners):
            return response

        try:
            await self._persist_or_extend(
                request, ctx_kind=kind, ctx_id=ctx_id, path=path,
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("Marcos timesheet middleware best-effort: %s", exc)
        return response

    async def _persist_or_extend(
        self,
        request: Request,
        *,
        ctx_kind: str,
        ctx_id: str,
        path: str,
    ) -> None:
        """Aggregate consecutive hits into 30s windows."""
        from sqlalchemy import select, text
        from backend.app.database import async_session
        from backend.app.motors.m23_retainer.timesheet_models import (
            MarcosTimesheetEntry,
        )

        subject = getattr(request.state, "auth_subject", None)
        marcos_id = str(getattr(getattr(subject, "user", None), "id", ""))
        if not marcos_id:
            return

        now_ts = time.time()
        cache_key = (marcos_id, ctx_id)
        previous = _active_sessions.get(cache_key)

        async with async_session() as session:
            try:
                await session.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))

                # Resolve client_id from project_id if the context is a project.
                client_id: Optional[uuid.UUID] = None
                project_uuid: Optional[uuid.UUID] = None
                retainer_uuid: Optional[uuid.UUID] = None
                if ctx_kind == "project_id":
                    project_uuid = uuid.UUID(ctx_id)
                    row = (await session.execute(text(
                        "SELECT client_id FROM projects WHERE id = :pid"
                    ), {"pid": ctx_id})).first()
                    client_id = row[0] if row else None
                elif ctx_kind == "retainer_id":
                    retainer_uuid = uuid.UUID(ctx_id)
                    row = (await session.execute(text(
                        "SELECT client_id, project_id FROM retainer_contracts "
                        "WHERE id = :rid"
                    ), {"rid": ctx_id})).first()
                    if row:
                        client_id = row[0]
                        project_uuid = row[1]
                elif ctx_kind == "thread_id":
                    row = (await session.execute(text(
                        "SELECT t.project_id, p.client_id "
                        "FROM whatsapp_threads t "
                        "JOIN projects p ON p.id = t.project_id "
                        "WHERE t.id = :tid"
                    ), {"tid": ctx_id})).first()
                    if row:
                        project_uuid = row[0]
                        client_id = row[1]

                if not client_id:
                    return

                # Try to extend the active session if within window.
                if previous is not None and (now_ts - previous[0] < AGGREGATE_WINDOW_SECONDS):
                    entry_id = previous[1]
                    entry = (await session.execute(
                        select(MarcosTimesheetEntry).where(
                            MarcosTimesheetEntry.id == uuid.UUID(entry_id),
                        )
                    )).scalar_one_or_none()
                    if entry is not None:
                        entry.ended_at = datetime.now(timezone.utc)
                        start = entry.started_at
                        if start.tzinfo is None:
                            start = start.replace(tzinfo=timezone.utc)
                        entry.duration_minutes = max(
                            1, int((entry.ended_at - start).total_seconds() / 60),
                        )
                        await session.flush()
                        await session.commit()
                        _active_sessions[cache_key] = (now_ts, entry_id)
                        return

                # Otherwise create a new entry.
                now_utc = datetime.now(timezone.utc)
                entry = MarcosTimesheetEntry(
                    client_id=client_id,
                    retainer_id=retainer_uuid,
                    started_at=now_utc,
                    ended_at=now_utc + timedelta(seconds=AGGREGATE_WINDOW_SECONDS),
                    duration_minutes=1,
                    source="auto_endpoint",
                    endpoint_path=path[:500],
                )
                session.add(entry)
                await session.flush()
                await session.commit()
                _active_sessions[cache_key] = (now_ts, str(entry.id))
            except Exception:
                await session.rollback()
                raise
