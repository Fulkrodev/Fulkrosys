"""Tests M30 · project portal-user endpoint · sub-atom 1.C.F.1.

Cubre:
- GET status vacio · sin user · sin contact
- POST primer ensure crea ClientUser + ClientContact + temp_password
- POST idempotente · segundo call no duplica · returns same ids
- POST sin create_contact · solo crea user, no contact
- 404 cuando project no existe
"""
from __future__ import annotations

import pytest

from backend.tests.conftest import setup_test_project


BASE = "/api/v1/projects"


@pytest.mark.asyncio
async def test_get_status_empty(async_client, db):
    _, project_id = await setup_test_project(db)
    r = await async_client.get(f"{BASE}/{project_id}/portal-user")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["client_user"] is None
    assert body["portal_contact"] is None
    assert body["complete"] is False


@pytest.mark.asyncio
async def test_ensure_creates_user_and_contact(async_client, db):
    _, project_id = await setup_test_project(db)
    r = await async_client.post(
        f"{BASE}/{project_id}/portal-user",
        json={
            "email": "cliente@empresa.com",
            "full_name": "Cliente Piloto",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["created_user"] is True
    assert body["created_contact"] is True
    assert body["client_user_id"]
    assert body["portal_contact_id"]
    assert body["temp_password"] is not None
    assert len(body["temp_password"]) >= 8

    # Status reflects complete
    status = await async_client.get(f"{BASE}/{project_id}/portal-user")
    s = status.json()
    assert s["complete"] is True
    assert s["client_user"]["email"] == "cliente@empresa.com"
    assert s["portal_contact"]["client_user_id"] == body["client_user_id"]


@pytest.mark.asyncio
async def test_ensure_idempotent(async_client, db):
    _, project_id = await setup_test_project(db)
    first = await async_client.post(
        f"{BASE}/{project_id}/portal-user",
        json={"email": "u@e.com", "full_name": "U"},
    )
    assert first.status_code == 201
    first_user = first.json()["client_user_id"]
    first_contact = first.json()["portal_contact_id"]

    second = await async_client.post(
        f"{BASE}/{project_id}/portal-user",
        json={"email": "otro@e.com", "full_name": "Other"},
    )
    assert second.status_code == 201, second.text
    body = second.json()
    assert body["created_user"] is False
    assert body["created_contact"] is False
    assert body["client_user_id"] == first_user
    assert body["portal_contact_id"] == first_contact
    assert body["temp_password"] is None


@pytest.mark.asyncio
async def test_ensure_without_contact(async_client, db):
    _, project_id = await setup_test_project(db)
    r = await async_client.post(
        f"{BASE}/{project_id}/portal-user",
        json={
            "email": "only-user@e.com",
            "full_name": "Solo User",
            "create_contact": False,
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["created_user"] is True
    assert body["created_contact"] is False
    assert body["portal_contact_id"] is None


@pytest.mark.asyncio
async def test_ensure_unknown_project_404(async_client):
    import uuid as _uuid
    fake = _uuid.uuid4()
    r = await async_client.post(
        f"{BASE}/{fake}/portal-user",
        json={"email": "x@e.com", "full_name": "X"},
    )
    assert r.status_code == 404
