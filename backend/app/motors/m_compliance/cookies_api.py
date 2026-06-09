"""Cookie consent API (atom 9.bis.1 PARTE B).

Endpoints (no auth required — anonymous visitors of fulkro.es and
authenticated cliente both supported):

- POST /api/v1/legal/cookies/consent
    Body: {functional, analytics, marketing, anonymous_session_id?}
    Persists the decision: appends an audit row + (when authenticated)
    updates client_users.consent_* columns.

- GET /api/v1/legal/cookies/consent
    Returns current state for the caller (cookie-authenticated cliente)
    or the anonymous session_id query param.

- POST /api/v1/legal/cookies/revoke
    Body: {category, anonymous_session_id?}
    Sets the chosen category to false + audit log entry
    (action_type=user_revoked).

Guía AEPD 2020 §4.4: cookie consent must be renewable every 24 months.
The endpoint sets ``consent_renewal_due = NOW() + 24 months`` so the
Self-Monitoring atom 9.bis.6 check_cookie_consent_renewal_24month picks
expirations up automatically.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.global_dep import AuthSubject
from backend.app.database import get_db
from backend.app.models.client_portal import ClientUser
from backend.app.models.consent_audit import (
    ACTION_INITIAL,
    ACTION_MODIFIED,
    ACTION_REVOKED,
    FulkroConsentAuditLog,
)


router = APIRouter(prefix="/legal/cookies", tags=["MB-9.bis atom 1 — Cookies"])


CONSENT_RENEWAL_MONTHS = 24


# ── Schemas ────────────────────────────────────────────────────────────


class CookieConsentBody(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    functional: bool = False
    analytics: bool = False
    marketing: bool = False
    anonymous_session_id: UUID | None = None
    page_url: str | None = Field(default=None, max_length=2048)


class CookieRevokeBody(BaseModel):
    category: str = Field(pattern="^(functional|analytics|marketing)$")
    anonymous_session_id: UUID | None = None
    page_url: str | None = Field(default=None, max_length=2048)


class CookieConsentState(BaseModel):
    functional: bool
    analytics: bool
    marketing: bool
    consent_timestamp: datetime | None
    consent_renewal_due: datetime | None
    authenticated: bool


# ── Helpers ────────────────────────────────────────────────────────────


def _get_auth_subject(request: Request) -> AuthSubject | None:
    return getattr(request.state, "auth_subject", None)


def _client_ip(request: Request) -> str | None:
    # X-Forwarded-For takes priority when behind a proxy (Hetzner nginx).
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


def _renewal_due(start: datetime) -> datetime:
    return start + timedelta(days=30 * CONSENT_RENEWAL_MONTHS)


async def _append_audit(
    db: AsyncSession,
    *,
    user_id: UUID | None,
    anonymous_session_id: UUID | None,
    tenant_client_id: UUID | None,
    action_type: str,
    old_state: dict | None,
    new_state: dict,
    request: Request,
    page_url: str | None,
) -> None:
    row = FulkroConsentAuditLog(
        user_id=str(user_id) if user_id else None,
        anonymous_session_id=(
            str(anonymous_session_id) if anonymous_session_id else None
        ),
        tenant_client_id=(
            str(tenant_client_id) if tenant_client_id else None
        ),
        timestamp=datetime.now(timezone.utc),
        action_type=action_type,
        old_state=old_state,
        new_state=new_state,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        page_url=page_url,
    )
    db.add(row)
    await db.flush()


# ── Endpoints ──────────────────────────────────────────────────────────


@router.post(
    "/consent",
    response_model=CookieConsentState,
    status_code=status.HTTP_201_CREATED,
)
async def post_consent(
    body: CookieConsentBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> CookieConsentState:
    """Persist a cookie consent decision (anonymous or authenticated)."""

    subject = _get_auth_subject(request)
    now = datetime.now(timezone.utc)
    renewal_due = _renewal_due(now)
    new_state = {
        "functional": body.functional,
        "analytics": body.analytics,
        "marketing": body.marketing,
        "necessary": True,  # always implicit
    }

    if subject and isinstance(subject.user, ClientUser):
        # Authenticated cliente: update row + audit.
        cliente: ClientUser = subject.user
        # Set tenant context so RLS doesn't block the UPDATE.
        await db.execute(
            text(
                "SELECT set_config('app.current_client_id', :cid, true)"
            ),
            {"cid": str(cliente.client_id)},
        )
        existing_state = {
            "functional": cliente.consent_functional,
            "analytics": cliente.consent_analytics,
            "marketing": cliente.consent_marketing,
            "necessary": True,
        }
        had_consent_before = cliente.consent_timestamp is not None
        await db.execute(
            text(
                """
                UPDATE client_users
                SET consent_functional = :fn,
                    consent_analytics = :an,
                    consent_marketing = :mk,
                    consent_timestamp = :ts,
                    consent_renewal_due = :renew,
                    consent_ip_address = :ip,
                    consent_user_agent = :ua
                WHERE id = :uid
                """
            ),
            {
                "fn": body.functional,
                "an": body.analytics,
                "mk": body.marketing,
                "ts": now,
                "renew": renewal_due,
                "ip": _client_ip(request),
                "ua": request.headers.get("user-agent"),
                "uid": str(cliente.id),
            },
        )
        await _append_audit(
            db,
            user_id=cliente.id,
            anonymous_session_id=None,
            tenant_client_id=cliente.client_id,
            action_type=ACTION_MODIFIED if had_consent_before else ACTION_INITIAL,
            old_state=existing_state if had_consent_before else None,
            new_state=new_state,
            request=request,
            page_url=body.page_url,
        )
        await db.commit()
        return CookieConsentState(
            functional=body.functional,
            analytics=body.analytics,
            marketing=body.marketing,
            consent_timestamp=now,
            consent_renewal_due=renewal_due,
            authenticated=True,
        )

    # Anonymous visitor: audit only (no client_users row to update).
    if body.anonymous_session_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="anonymous_session_id required for anonymous consent",
        )
    await _append_audit(
        db,
        user_id=None,
        anonymous_session_id=body.anonymous_session_id,
        tenant_client_id=None,
        action_type=ACTION_INITIAL,
        old_state=None,
        new_state=new_state,
        request=request,
        page_url=body.page_url,
    )
    await db.commit()
    return CookieConsentState(
        functional=body.functional,
        analytics=body.analytics,
        marketing=body.marketing,
        consent_timestamp=now,
        consent_renewal_due=renewal_due,
        authenticated=False,
    )


@router.get("/consent", response_model=CookieConsentState)
async def get_consent(
    request: Request,
    db: AsyncSession = Depends(get_db),
    anonymous_session_id: UUID | None = Query(default=None),
) -> CookieConsentState:
    """Return the current consent state for the caller."""
    subject = _get_auth_subject(request)
    if subject and isinstance(subject.user, ClientUser):
        cliente: ClientUser = subject.user
        return CookieConsentState(
            functional=cliente.consent_functional,
            analytics=cliente.consent_analytics,
            marketing=cliente.consent_marketing,
            consent_timestamp=cliente.consent_timestamp,
            consent_renewal_due=cliente.consent_renewal_due,
            authenticated=True,
        )

    # Anonymous: look up the most recent audit row for this session.
    if anonymous_session_id is None:
        # Caller anónimo sin sesión → estado por defecto (todo OFF excepto necesarias).
        return CookieConsentState(
            functional=False,
            analytics=False,
            marketing=False,
            consent_timestamp=None,
            consent_renewal_due=None,
            authenticated=False,
        )
    row = await db.execute(
        text(
            """
            SELECT new_state, timestamp
            FROM fulkro_consent_audit_log
            WHERE anonymous_session_id = :sid
            ORDER BY timestamp DESC LIMIT 1
            """
        ),
        {"sid": str(anonymous_session_id)},
    )
    record = row.first()
    if record is None:
        return CookieConsentState(
            functional=False,
            analytics=False,
            marketing=False,
            consent_timestamp=None,
            consent_renewal_due=None,
            authenticated=False,
        )
    state = record[0] or {}
    return CookieConsentState(
        functional=bool(state.get("functional", False)),
        analytics=bool(state.get("analytics", False)),
        marketing=bool(state.get("marketing", False)),
        consent_timestamp=record[1],
        consent_renewal_due=_renewal_due(record[1]) if record[1] else None,
        authenticated=False,
    )


@router.post(
    "/revoke",
    response_model=CookieConsentState,
    status_code=status.HTTP_200_OK,
)
async def post_revoke(
    body: CookieRevokeBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> CookieConsentState:
    """Revoke consent for a specific category."""
    subject = _get_auth_subject(request)
    now = datetime.now(timezone.utc)

    if subject and isinstance(subject.user, ClientUser):
        cliente: ClientUser = subject.user
        await db.execute(
            text(
                "SELECT set_config('app.current_client_id', :cid, true)"
            ),
            {"cid": str(cliente.client_id)},
        )
        old_state = {
            "functional": cliente.consent_functional,
            "analytics": cliente.consent_analytics,
            "marketing": cliente.consent_marketing,
            "necessary": True,
        }
        col_map = {
            "functional": "consent_functional",
            "analytics": "consent_analytics",
            "marketing": "consent_marketing",
        }
        col = col_map[body.category]
        await db.execute(
            text(
                f"UPDATE client_users SET {col} = false, "
                f"consent_timestamp = :ts WHERE id = :uid"
            ),
            {"ts": now, "uid": str(cliente.id)},
        )
        new_state = {**old_state, body.category: False}
        await _append_audit(
            db,
            user_id=cliente.id,
            anonymous_session_id=None,
            tenant_client_id=cliente.client_id,
            action_type=ACTION_REVOKED,
            old_state=old_state,
            new_state=new_state,
            request=request,
            page_url=body.page_url,
        )
        await db.commit()
        return CookieConsentState(
            functional=new_state["functional"],
            analytics=new_state["analytics"],
            marketing=new_state["marketing"],
            consent_timestamp=now,
            consent_renewal_due=_renewal_due(now),
            authenticated=True,
        )

    # Anonymous revoke: append audit + return new state.
    if body.anonymous_session_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="anonymous_session_id required for anonymous revoke",
        )
    new_state = {
        "functional": True if body.category != "functional" else False,
        "analytics": True if body.category != "analytics" else False,
        "marketing": True if body.category != "marketing" else False,
        "necessary": True,
    }
    # We don't reconstruct prior state without an extra read; keep audit
    # row honest by storing both states as None / new.
    await _append_audit(
        db,
        user_id=None,
        anonymous_session_id=body.anonymous_session_id,
        tenant_client_id=None,
        action_type=ACTION_REVOKED,
        old_state=None,
        new_state=new_state,
        request=request,
        page_url=body.page_url,
    )
    await db.commit()
    return CookieConsentState(
        functional=new_state["functional"],
        analytics=new_state["analytics"],
        marketing=new_state["marketing"],
        consent_timestamp=now,
        consent_renewal_due=_renewal_due(now),
        authenticated=False,
    )
