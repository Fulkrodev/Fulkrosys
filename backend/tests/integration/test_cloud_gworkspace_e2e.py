"""GWorkspace connector E2E scaffold · Sesión 3B-2B.7 Ejecutable 4 Phase 7.3 (2026-05-27).

Mock httpx responses · verify discovery flow + polish additions:
- mfa_enabled detection via isEnrolledIn2Sv (existing)
- is_privileged detection via isAdmin (existing)
- Shared drives discovery via /drives Drive API (NEW)
- pagination follow nextPageToken (best-effort)
- graceful degradation per endpoint

NO requires real GWorkspace sandbox · pure unit-style integration test connector layer.
NOTE: runnable post Future-1.E.radar.alembic-version-num-widen applied (DB upgrade head pending).
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from backend.app.motors.m16_onboarding.connectors.google_workspace import (
    GoogleWorkspaceConnector,
)


def _mock_response(json_data: dict, status_code: int = 200) -> httpx.Response:
    request = httpx.Request("GET", "https://admin.googleapis.com/test")
    return httpx.Response(status_code, json=json_data, request=request)


@pytest.fixture
def gworkspace_credentials() -> dict:
    return {
        "access_token": "mock_gtoken",
        "domain": "example.com",
    }


@pytest.mark.asyncio
async def test_gworkspace_validate_credentials_success(gworkspace_credentials):
    """Users endpoint reachable → True."""
    connector = GoogleWorkspaceConnector(gworkspace_credentials)

    def side_effect_get(*args, **kwargs):
        return _mock_response({"users": [{"id": "u1"}]})

    with patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=side_effect_get)):
        result = await connector.validate_credentials()

    assert result is True


@pytest.mark.asyncio
async def test_gworkspace_discover_identities_mfa_admin(gworkspace_credentials):
    """isEnrolledIn2Sv → mfa_enabled · isAdmin → is_privileged · existing fields preserved."""
    connector = GoogleWorkspaceConnector(gworkspace_credentials)

    users_response = {
        "users": [
            {
                "id": "u1",
                "primaryEmail": "alice@example.com",
                "name": {"fullName": "Alice"},
                "isEnrolledIn2Sv": True,
                "isAdmin": True,
                "suspended": False,
            },
            {
                "id": "u2",
                "primaryEmail": "bob@example.com",
                "name": {"fullName": "Bob"},
                "isEnrolledIn2Sv": False,
                "isAdmin": False,
                "suspended": False,
            },
        ]
    }
    groups_response = {"groups": []}

    def get_side_effect(url, **kwargs):
        if "/users" in url:
            return _mock_response(users_response)
        if "/groups" in url:
            return _mock_response(groups_response)
        return _mock_response({})

    with patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=get_side_effect)):
        identities = await connector.discover_identities()

    alice = next(i for i in identities if i.external_id == "u1")
    bob = next(i for i in identities if i.external_id == "u2")

    assert alice.mfa_enabled is True
    assert alice.is_privileged is True
    assert bob.mfa_enabled is False
    assert bob.is_privileged is False


@pytest.mark.asyncio
async def test_gworkspace_discover_assets_includes_shared_drives(gworkspace_credentials):
    """Shared drives discovery emite asset_type=shared_drive con public_access detection."""
    connector = GoogleWorkspaceConnector(gworkspace_credentials)

    mobile_response = {"mobiledevices": []}
    drives_response = {
        "drives": [
            {
                "id": "drive-1",
                "name": "External Partner Drive",
                "restrictions": {"domainUsersOnly": False},
            },
            {
                "id": "drive-2",
                "name": "Internal Engineering",
                "restrictions": {"domainUsersOnly": True},
            },
        ]
    }

    def get_side_effect(url, **kwargs):
        if "devices/mobile" in url:
            return _mock_response(mobile_response)
        if "/drive/v3/drives" in url:
            return _mock_response(drives_response)
        return _mock_response({})

    with patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=get_side_effect)):
        assets = await connector.discover_assets()

    drive_assets = [a for a in assets if a.asset_type == "shared_drive"]
    assert len(drive_assets) == 2

    external = next(a for a in drive_assets if a.external_id == "drive-1")
    internal = next(a for a in drive_assets if a.external_id == "drive-2")

    assert external.raw_data["public_access"] is True
    assert external.raw_data["is_public"] is True
    assert external.raw_data["domain_restricted"] is False
    assert internal.raw_data["public_access"] is False
    assert internal.raw_data["domain_restricted"] is True


@pytest.mark.asyncio
async def test_gworkspace_graceful_degradation_drives_403(gworkspace_credentials):
    """Drive API denied → shared drives empty · identity discovery NOT affected."""
    connector = GoogleWorkspaceConnector(gworkspace_credentials)

    mobile_response = {"mobiledevices": [{"resourceId": "m1", "model": "Phone X"}]}

    def get_side_effect(url, **kwargs):
        if "/drive/v3/drives" in url:
            request = httpx.Request("GET", url)
            return httpx.Response(403, json={"error": {"code": 403}}, request=request)
        if "devices/mobile" in url:
            return _mock_response(mobile_response)
        return _mock_response({})

    with patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=get_side_effect)):
        assets = await connector.discover_assets()

    mobile_assets = [a for a in assets if a.asset_type == "mobile_device"]
    drive_assets = [a for a in assets if a.asset_type == "shared_drive"]

    assert len(mobile_assets) == 1
    assert len(drive_assets) == 0


@pytest.mark.asyncio
async def test_gworkspace_pagination_follows_nexttoken(gworkspace_credentials):
    """nextPageToken follow up to max_pages aggregating all results."""
    connector = GoogleWorkspaceConnector(gworkspace_credentials)

    page_1 = {
        "users": [{"id": f"u{i}", "primaryEmail": f"u{i}@x.com", "name": {"fullName": f"U{i}"}} for i in range(2)],
        "nextPageToken": "ptok2",
    }
    page_2 = {
        "users": [{"id": f"u{i}", "primaryEmail": f"u{i}@x.com", "name": {"fullName": f"U{i}"}} for i in range(2, 4)],
    }

    call_count = {"users": 0}

    def get_side_effect(url, **kwargs):
        params = kwargs.get("params") or {}
        if "/users" in url:
            call_count["users"] += 1
            if params.get("pageToken") == "ptok2":
                return _mock_response(page_2)
            return _mock_response(page_1)
        if "/groups" in url:
            return _mock_response({"groups": []})
        return _mock_response({})

    with patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=get_side_effect)):
        identities = await connector.discover_identities()

    users = [i for i in identities if i.identity_type == "user"]
    assert len(users) == 4
    assert call_count["users"] == 2
