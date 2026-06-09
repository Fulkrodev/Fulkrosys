"""Tests de connectors M16-C con mocks HTTP (respx). Zero real HTTP calls."""
import uuid

import httpx
import pytest
import respx

from backend.app.motors.m16_onboarding.connectors.base import ConnectorProvider
from backend.app.motors.m16_onboarding.connectors.microsoft365 import Microsoft365Connector
from backend.app.motors.m16_onboarding.connectors.github_connector import GitHubConnector
from backend.app.motors.m16_onboarding.connectors.registry import (
    create_connector,
    list_available_providers,
)
from backend.app.motors.m16_onboarding.token_encryption import (
    decrypt_credentials,
    encrypt_credentials,
)

from backend.tests.conftest import setup_test_project


# ==== TOKEN ENCRYPTION ====

class TestTokenEncryption:
    def test_roundtrip(self):
        creds = {"tenant_id": "abc", "client_secret": "s3cr3t"}
        encrypted = encrypt_credentials(creds)
        assert isinstance(encrypted, bytes)
        assert decrypt_credentials(encrypted) == creds

    def test_encrypted_is_not_plaintext(self):
        creds = {"token": "my_secret_token"}
        encrypted = encrypt_credentials(creds)
        assert b"my_secret_token" not in encrypted

    def test_decrypt_corrupted_fails(self):
        with pytest.raises(ValueError, match="descifrar"):
            decrypt_credentials(b"corrupted_bytes_here_with_enough_length_to_be_realistic")


# ==== REGISTRY ====

class TestConnectorRegistry:
    def test_m365_registered(self):
        assert ConnectorProvider.MICROSOFT_365 in list_available_providers()

    def test_github_registered(self):
        assert ConnectorProvider.GITHUB in list_available_providers()

    def test_create_m365(self):
        c = create_connector(ConnectorProvider.MICROSOFT_365, {
            "tenant_id": "t", "client_id": "c", "client_secret": "s",
        })
        assert isinstance(c, Microsoft365Connector)

    def test_create_github(self):
        c = create_connector(ConnectorProvider.GITHUB, {"personal_access_token": "ghp_x"})
        assert isinstance(c, GitHubConnector)


# ==== M365 CONNECTOR ====

class TestMicrosoft365Connector:

    @respx.mock
    @pytest.mark.asyncio
    async def test_validate_ok(self):
        respx.post("https://login.microsoftonline.com/t1/oauth2/v2.0/token").mock(
            return_value=httpx.Response(200, json={"access_token": "tok", "token_type": "Bearer"})
        )
        respx.get("https://graph.microsoft.com/v1.0/organization").mock(
            return_value=httpx.Response(200, json={"value": [{"id": "org1"}]})
        )
        c = Microsoft365Connector({"tenant_id": "t1", "client_id": "c", "client_secret": "s"})
        assert await c.validate_credentials() is True

    @respx.mock
    @pytest.mark.asyncio
    async def test_validate_bad_secret(self):
        respx.post("https://login.microsoftonline.com/t1/oauth2/v2.0/token").mock(
            return_value=httpx.Response(401, json={"error": "invalid_client"})
        )
        c = Microsoft365Connector({"tenant_id": "t1", "client_id": "c", "client_secret": "bad"})
        assert await c.validate_credentials() is False

    @respx.mock
    @pytest.mark.asyncio
    async def test_discover_identities(self):
        respx.post("https://login.microsoftonline.com/t1/oauth2/v2.0/token").mock(
            return_value=httpx.Response(200, json={"access_token": "tok"})
        )
        respx.get("https://graph.microsoft.com/v1.0/users").mock(
            return_value=httpx.Response(200, json={"value": [
                {"id": "u1", "displayName": "Ana", "mail": "ana@test.com", "accountEnabled": True, "userPrincipalName": "ana@test.com", "userType": "Member"},
                {"id": "u2", "displayName": "Pedro", "mail": "pedro@test.com", "accountEnabled": False, "userPrincipalName": "pedro@test.com", "userType": "Member"},
            ]})
        )
        respx.get("https://graph.microsoft.com/v1.0/groups").mock(
            return_value=httpx.Response(200, json={"value": [
                {"id": "g1", "displayName": "IT Team", "securityEnabled": True},
            ]})
        )
        c = Microsoft365Connector({"tenant_id": "t1", "client_id": "c", "client_secret": "s"})
        ids = await c.discover_identities()
        assert len(ids) == 3
        assert sum(1 for i in ids if i.identity_type == "user") == 2
        assert sum(1 for i in ids if i.identity_type == "group") == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_discover_assets_devices(self):
        respx.post("https://login.microsoftonline.com/t1/oauth2/v2.0/token").mock(
            return_value=httpx.Response(200, json={"access_token": "tok"})
        )
        respx.get("https://graph.microsoft.com/v1.0/deviceManagement/managedDevices").mock(
            return_value=httpx.Response(200, json={"value": [
                {"id": "d1", "deviceName": "LAPTOP-ANA", "operatingSystem": "Windows", "osVersion": "11",
                 "complianceState": "compliant", "model": "ThinkPad", "manufacturer": "Lenovo", "managementAgent": "mdm"},
            ]})
        )
        c = Microsoft365Connector({"tenant_id": "t1", "client_id": "c", "client_secret": "s"})
        assets = await c.discover_assets()
        assert len(assets) == 1
        assert assets[0].asset_type == "endpoint"
        assert assets[0].name == "LAPTOP-ANA"


# ==== GITHUB CONNECTOR ====

class TestGitHubConnector:

    @respx.mock
    @pytest.mark.asyncio
    async def test_validate_ok(self):
        respx.get("https://api.github.com/user").mock(
            return_value=httpx.Response(200, json={"login": "testuser", "id": 1})
        )
        c = GitHubConnector({"personal_access_token": "ghp_test"})
        assert await c.validate_credentials() is True

    @respx.mock
    @pytest.mark.asyncio
    async def test_discover_repos(self):
        respx.get("https://api.github.com/user/repos").mock(
            return_value=httpx.Response(200, json=[
                {"id": 1, "full_name": "org/repo1", "private": True, "language": "Python",
                 "default_branch": "main", "archived": False},
                {"id": 2, "full_name": "org/repo2", "private": False, "language": "TypeScript",
                 "default_branch": "main", "archived": False},
            ])
        )
        c = GitHubConnector({"personal_access_token": "ghp_test"})
        assets = await c.discover_assets()
        assert len(assets) == 2
        assert assets[0].asset_type == "repository"
        assert "private" in assets[0].tags

    @respx.mock
    @pytest.mark.asyncio
    async def test_discover_org_members(self):
        respx.get("https://api.github.com/orgs/myorg/members").mock(
            return_value=httpx.Response(200, json=[
                {"id": 10, "login": "dev1", "site_admin": False},
                {"id": 20, "login": "admin1", "site_admin": True},
            ])
        )
        c = GitHubConnector({"personal_access_token": "ghp_test", "organization": "myorg"})
        ids = await c.discover_identities()
        assert len(ids) == 2
        assert ids[1].is_privileged is True

    @respx.mock
    @pytest.mark.asyncio
    async def test_discover_no_org_returns_self(self):
        respx.get("https://api.github.com/user").mock(
            return_value=httpx.Response(200, json={"login": "me", "id": 99, "name": "My Name", "email": "me@test.com"})
        )
        c = GitHubConnector({"personal_access_token": "ghp_test"})
        ids = await c.discover_identities()
        assert len(ids) == 1
        assert ids[0].display_name == "My Name"


# ==== API INTEGRATION ====

class TestConnectorAPI:

    @pytest.mark.asyncio
    async def test_configure_connector(self, async_client, db):
        _, project_id = await setup_test_project(db)
        r = await async_client.post(
            f"/api/v1/onboarding/projects/{project_id}/connectors/configure",
            json={"provider": "github", "credentials": {"personal_access_token": "ghp_test123"}},
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "configured"

    @pytest.mark.asyncio
    async def test_list_connectors_empty(self, async_client, db):
        _, project_id = await setup_test_project(db)
        r = await async_client.get(f"/api/v1/onboarding/projects/{project_id}/connectors")
        assert r.status_code == 200
        assert r.json() == []

    @pytest.mark.asyncio
    async def test_list_after_configure(self, async_client, db):
        _, project_id = await setup_test_project(db)
        await async_client.post(
            f"/api/v1/onboarding/projects/{project_id}/connectors/configure",
            json={"provider": "github", "credentials": {"personal_access_token": "ghp_x"}},
        )
        r = await async_client.get(f"/api/v1/onboarding/projects/{project_id}/connectors")
        assert r.status_code == 200
        assert len(r.json()) == 1
        assert r.json()[0]["provider"] == "github"

    @pytest.mark.asyncio
    async def test_configure_upserts(self, async_client, db):
        _, project_id = await setup_test_project(db)
        r1 = await async_client.post(
            f"/api/v1/onboarding/projects/{project_id}/connectors/configure",
            json={"provider": "github", "credentials": {"personal_access_token": "old"}},
        )
        r2 = await async_client.post(
            f"/api/v1/onboarding/projects/{project_id}/connectors/configure",
            json={"provider": "github", "credentials": {"personal_access_token": "new"}},
        )
        assert r1.json()["config_id"] == r2.json()["config_id"]
