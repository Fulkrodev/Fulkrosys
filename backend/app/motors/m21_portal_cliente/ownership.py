"""Canonical client-portal ownership guards — IDOR-class close.

Client-portal requests run under the Postgres role ``fulkro_app_bypassrls``
(RLS is OFF for those requests), so tenant isolation is enforced HERE, in
application code, **not** by the database. Every client endpoint that reaches a
resource by id MUST resolve ownership through one of these guards BEFORE
reading / mutating / serializing the resource.

Doctrine (why these specific choices):

- **Not-owned → 404, never 403.** A 403 ("exists but not yours") is an
  enumeration oracle: an attacker learns which resource ids exist in *other*
  tenants. 404 is indistinguishable from a genuinely missing id, so the id
  space leaks nothing. The pre-existing per-motor
  ``_ensure_project_belongs_to_client`` helpers returned 403 on the
  resource-derived path — that is the "frágil" pattern the audit flagged.

- **Guards set the tenant GUC context** (``set_tenant_context``) so any
  subsequent RLS-aware query in the same transaction is scoped to the client's
  project (defence-in-depth for code paths that DO go through RLS policies).

Enforced by:
- ``tests/security/test_client_portal_idor_tripwire.py`` (static: every portal
  module that fetches a resource by id must import this guard) — fails the
  build if the fragile pattern is reintroduced silently.
- per-resource cross-tenant tests (runtime: client A → 404 on client B's id).
"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import set_tenant_context
from backend.app.models.client_portal import ClientUser


def _not_found() -> HTTPException:
    # Canonical 404 for both "missing" and "not owned" — no existence oracle.
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")


async def project_belongs_to_client(
    db: AsyncSession,
    project_id: uuid.UUID,
    client_id: uuid.UUID,
) -> bool:
    """Pure ownership predicate · NO raise · NO context mutation.

    Resolves the owner via ``get_project_owner()`` (SECURITY DEFINER), so it is
    correct regardless of the current RLS context — under both ``fulkro_app``
    (RLS on, no tenant context) and ``fulkro_app_bypassrls``. A raw
    ``SELECT ... WHERE client_id`` would return 0 rows under RLS with no context
    → spurious 404 for the legit owner (the bug m05_signing hit and fixed).
    """
    owner = (
        await db.execute(
            sa_text("SELECT get_project_owner(:pid)"),
            {"pid": str(project_id)},
        )
    ).scalar()
    return owner is not None and str(owner) == str(client_id)


async def ensure_project_owned(
    db: AsyncSession,
    project_id: uuid.UUID,
    user: ClientUser,
) -> None:
    """Project-scoped guard. Raises 404 if the project is not the client's.

    Use on endpoints whose path already carries ``project_id``. Sets tenant
    context for downstream RLS-aware queries.
    """
    if not await project_belongs_to_client(db, project_id, user.client_id):
        raise _not_found()
    await set_tenant_context(db, client_id=user.client_id, project_id=project_id)


async def ensure_owned_via_project(
    db: AsyncSession,
    project_id: uuid.UUID | None,
    user: ClientUser,
) -> uuid.UUID:
    """Resource-derived guard. Raises 404 if the resource's project is not the
    client's.

    Use **after** resolving ``project_id`` from a resource fetched by id
    (asset→analysis→project, entry→project, incident→project, document→project).
    ALWAYS 404 on mismatch — never 403 — so the resource id space is not an
    enumeration oracle. Returns the (now verified) project_id and sets tenant
    context.
    """
    if project_id is None or not await project_belongs_to_client(
        db, project_id, user.client_id,
    ):
        raise _not_found()
    await set_tenant_context(db, client_id=user.client_id, project_id=project_id)
    return project_id
