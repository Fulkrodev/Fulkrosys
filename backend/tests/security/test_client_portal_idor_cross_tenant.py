"""IDOR-class cross-tenant guard tests (runtime) · ownership.py primitive.

Prod-faithful: client-portal requests run under ``fulkro_app_bypassrls`` (RLS
OFF) — isolation is enforced by the guard's ``WHERE client_id`` clause, NOT by
RLS. We therefore exercise the guard inside ``_admin_setup`` (bypassrls), which
mirrors the production role, and assert that a foreign resource's project
resolves to **404 (never 403)** so the resource-id space is not an enumeration
oracle. The static wiring (every fragile endpoint calls this guard) is locked by
test_client_portal_idor_tripwire.py.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m21_portal_cliente.ownership import (
    ensure_owned_via_project,
    ensure_project_owned,
    project_belongs_to_client,
)
from backend.tests.conftest import _admin_setup


class _StubUser:
    def __init__(self, client_id: uuid.UUID) -> None:
        self.id = uuid.uuid4()
        self.client_id = client_id
        self.email = f"idor-{self.id.hex[:8]}@test.invalid"


async def _seed_client_project(db: AsyncSession) -> tuple[uuid.UUID, uuid.UUID]:
    """INSERT a client + project via _admin_setup (bypass RLS for the seed)."""
    cid = uuid.uuid4()
    pid = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, 'IDOR test', :cif, now())"
            ),
            {"id": str(cid), "cif": cif},
        )
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, fase, created_at) "
                "VALUES (:id, :cid, 'IDOR proj', 'implantacion', now())"
            ),
            {"id": str(pid), "cid": str(cid)},
        )
    return cid, pid


@pytest.mark.asyncio
async def test_foreign_project_resolves_to_404_not_403(db: AsyncSession):
    """Client A reaching client B's project → 404 (no 403 existence oracle)."""
    cid_a, pid_a = await _seed_client_project(db)
    _cid_b, pid_b = await _seed_client_project(db)
    user_a = _StubUser(cid_a)

    async with _admin_setup(db):  # mirror prod bypassrls role
        # Own project: passes, returns the verified project_id.
        assert await ensure_owned_via_project(db, pid_a, user_a) == pid_a

        # Foreign project: 404 with the SAME body as a missing id (no oracle).
        with pytest.raises(HTTPException) as exc:
            await ensure_owned_via_project(db, pid_b, user_a)
        assert exc.value.status_code == 404
        assert exc.value.detail == "No encontrado"


@pytest.mark.asyncio
async def test_none_project_resolves_to_404(db: AsyncSession):
    """A resource with no resolvable project → 404 (orphan must not leak/500)."""
    cid_a, _pid_a = await _seed_client_project(db)
    user_a = _StubUser(cid_a)
    async with _admin_setup(db):
        with pytest.raises(HTTPException) as exc:
            await ensure_owned_via_project(db, None, user_a)
        assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_ensure_project_owned_foreign_is_404(db: AsyncSession):
    """Project-path guard variant: foreign project → 404."""
    cid_a, _pid_a = await _seed_client_project(db)
    _cid_b, pid_b = await _seed_client_project(db)
    user_a = _StubUser(cid_a)
    async with _admin_setup(db):
        with pytest.raises(HTTPException) as exc:
            await ensure_project_owned(db, pid_b, user_a)
        assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_project_belongs_to_client_predicate(db: AsyncSession):
    """Pure predicate isolates strictly by (project_id, client_id)."""
    cid_a, pid_a = await _seed_client_project(db)
    cid_b, pid_b = await _seed_client_project(db)
    async with _admin_setup(db):
        assert await project_belongs_to_client(db, pid_a, cid_a) is True
        assert await project_belongs_to_client(db, pid_a, cid_b) is False
        assert await project_belongs_to_client(db, pid_b, cid_a) is False
