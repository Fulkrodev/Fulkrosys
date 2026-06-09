"""M365 connector E2E scaffold · Sesión 3B-2B.7 Ejecutable 4 Phase 7.3 (2026-05-27).

Mock httpx responses · verify discovery flow + polish additions:
- mfa_enabled detection via /reports/authenticationMethods/userRegistrationDetails
- is_privileged detection via /directoryRoles + members
- SharePoint sites discovery via /sites?search=*
- pagination follow @odata.nextLink (best-effort)
- graceful degradation per endpoint

NO requires real M365 sandbox · pure unit-style integration test connector layer.
NOTE: runnable post Future-1.E.radar.alembic-version-num-widen applied (DB upgrade head pending).
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from backend.app.motors.m16_onboarding.connectors.microsoft365 import (
    Microsoft365Connector,
)


def _mock_response(json_data: dict, status_code: int = 200) -> httpx.Response:
    request = httpx.Request("GET", "https://graph.microsoft.com/v1.0/test")
    return httpx.Response(status_code, json=json_data, request=request)


def _token_response() -> httpx.Response:
    request = httpx.Request("POST", "https://login.microsoftonline.com/tenant/oauth2/v2.0/token")
    return httpx.Response(200, json={"access_token": "mock_token", "expires_in": 3600}, request=request)


@pytest.fixture
def m365_credentials() -> dict:
    return {
        "tenant_id": "11111111-2222-3333-4444-555555555555",
        "client_id": "aaaa1111-bbbb-2222-cccc-333333333333",
        "client_secret": "mock_secret",
    }


@pytest.mark.asyncio
async def test_m365_validate_credentials_success(m365_credentials):
    """Token + organization endpoint reachable → True."""
    connector = Microsoft365Connector(m365_credentials)

    def side_effect_get(*args, **kwargs):
        return _mock_response({"id": "org-1", "displayName": "Test Org"})

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=_token_response())):
        with patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=side_effect_get)):
            result = await connector.validate_credentials()

    assert result is True


@pytest.mark.asyncio
async def test_m365_validate_credentials_failure_graceful(m365_credentials):
    """Token endpoint fails → False (NO raise)."""
    connector = Microsoft365Connector(m365_credentials)

    def raise_400(*args, **kwargs):
        request = httpx.Request("POST", "https://login.microsoftonline.com/error")
        return httpx.Response(400, json={"error": "invalid_client"}, request=request)

    with patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=raise_400)):
        result = await connector.validate_credentials()

    assert result is False


@pytest.mark.asyncio
async def test_m365_discover_identities_with_mfa_and_privileged(m365_credentials):
    """MFA + privileged detection enriches identities (op.acc.6 + op.acc.5 unlocked)."""
    connector = Microsoft365Connector(m365_credentials)

    mfa_report = {
        "value": [
            {"id": "user-1", "isMfaRegistered": True},
            {"id": "user-2", "isMfaRegistered": False},
        ]
    }
    roles_response = {
        "value": [{"id": "role-admin", "displayName": "Global Administrator"}]
    }
    role_members = {"value": [{"id": "user-1"}]}
    users_response = {
        "value": [
            {"id": "user-1", "displayName": "Alice", "mail": "alice@test.com", "accountEnabled": True},
            {"id": "user-2", "displayName": "Bob", "mail": "bob@test.com", "accountEnabled": True},
        ]
    }
    groups_response = {"value": []}

    call_count = {"i": 0}

    def get_side_effect(url, **kwargs):
        call_count["i"] += 1
        if "userRegistrationDetails" in url:
            return _mock_response(mfa_report)
        if "/directoryRoles/role-admin/members" in url:
            return _mock_response(role_members)
        if "/directoryRoles" in url:
            return _mock_response(roles_response)
        if "/users" in url:
            return _mock_response(users_response)
        if "/groups" in url:
            return _mock_response(groups_response)
        return _mock_response({"value": []})

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=_token_response())):
        with patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=get_side_effect)):
            identities = await connector.discover_identities()

    user_alice = next(i for i in identities if i.external_id == "user-1")
    user_bob = next(i for i in identities if i.external_id == "user-2")

    assert user_alice.mfa_enabled is True
    assert user_alice.is_privileged is True
    assert user_bob.mfa_enabled is False
    assert user_bob.is_privileged is False


@pytest.mark.asyncio
async def test_m365_discover_assets_includes_sharepoint(m365_credentials):
    """SharePoint sites discovery emite asset_type=sharepoint_site con public_access."""
    connector = Microsoft365Connector(m365_credentials)

    devices_response = {"value": []}
    sites_response = {
        "value": [
            {
                "id": "site-1",
                "displayName": "Public HR Site",
                "sharingCapability": "ExternalUserAndGuestSharing",
            },
            {
                "id": "site-2",
                "displayName": "Internal Team Site",
                "sharingCapability": "Disabled",
            },
        ]
    }

    def get_side_effect(url, **kwargs):
        if "managedDevices" in url:
            return _mock_response(devices_response)
        if "/sites" in url:
            return _mock_response(sites_response)
        return _mock_response({"value": []})

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=_token_response())):
        with patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=get_side_effect)):
            assets = await connector.discover_assets()

    sharepoint_assets = [a for a in assets if a.asset_type == "sharepoint_site"]
    assert len(sharepoint_assets) == 2

    public_site = next(a for a in sharepoint_assets if a.external_id == "site-1")
    internal_site = next(a for a in sharepoint_assets if a.external_id == "site-2")

    assert public_site.raw_data["public_access"] is True
    assert public_site.raw_data["is_public"] is True
    assert internal_site.raw_data["public_access"] is False


@pytest.mark.asyncio
async def test_m365_graceful_degradation_mfa_endpoint_403(m365_credentials):
    """MFA endpoint denied (insufficient scopes) → users keep mfa_enabled=None · NO crash."""
    connector = Microsoft365Connector(m365_credentials)

    users_response = {"value": [{"id": "user-1", "displayName": "Alice", "accountEnabled": True}]}

    def get_side_effect(url, **kwargs):
        if "userRegistrationDetails" in url:
            request = httpx.Request("GET", url)
            return httpx.Response(403, json={"error": "Insufficient privileges"}, request=request)
        if "/directoryRoles" in url and "members" not in url:
            return _mock_response({"value": []})
        if "/users" in url:
            return _mock_response(users_response)
        return _mock_response({"value": []})

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=_token_response())):
        with patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=get_side_effect)):
            identities = await connector.discover_identities()

    user = next((i for i in identities if i.external_id == "user-1"), None)
    assert user is not None
    assert user.mfa_enabled is None
    assert user.is_privileged is False


@pytest.mark.asyncio
async def test_m365_pagination_follows_nextlink(m365_credentials):
    """Pagination @odata.nextLink follow caps max 3 pages · all items aggregated."""
    connector = Microsoft365Connector(m365_credentials)

    page_1 = {
        "value": [{"id": f"user-{i}", "displayName": f"U{i}", "accountEnabled": True} for i in range(2)],
        "@odata.nextLink": "https://graph.microsoft.com/v1.0/users?$skiptoken=page2",
    }
    page_2 = {
        "value": [{"id": f"user-{i}", "displayName": f"U{i}", "accountEnabled": True} for i in range(2, 4)],
    }

    call_count = {"users": 0, "mfa": 0, "roles": 0, "groups": 0}

    def get_side_effect(url, **kwargs):
        if "userRegistrationDetails" in url:
            call_count["mfa"] += 1
            return _mock_response({"value": []})
        if "/directoryRoles" in url:
            call_count["roles"] += 1
            return _mock_response({"value": []})
        if "/groups" in url:
            call_count["groups"] += 1
            return _mock_response({"value": []})
        if "/users" in url:
            call_count["users"] += 1
            if "skiptoken=page2" in url:
                return _mock_response(page_2)
            return _mock_response(page_1)
        return _mock_response({"value": []})

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=_token_response())):
        with patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=get_side_effect)):
            identities = await connector.discover_identities()

    users = [i for i in identities if i.identity_type == "user"]
    assert len(users) == 4
    assert call_count["users"] == 2
