"""Tests for M16-CIERRE: connectors batch 2, expanded catalog, hardening."""
from datetime import datetime, timedelta, timezone

import httpx
import pytest
import respx
from sqlalchemy import text

from backend.app.motors.m16_onboarding.catalog_loader import reload_templates
from backend.app.motors.m16_onboarding.connectors.google_workspace import GoogleWorkspaceConnector
from backend.app.motors.m16_onboarding.connectors.aws_connector import AWSConnector
from backend.app.motors.m16_onboarding.connectors.azure_connector import AzureConnector
from backend.app.motors.m16_onboarding.connectors.registry import list_available_providers
from backend.app.motors.m16_onboarding.enums import Sector, Role
from backend.tests.conftest import setup_test_project, _admin_setup

BASE = "/api/v1/onboarding"


# ==== CONNECTOR TESTS ====

class TestGoogleWorkspaceConnector:
    @respx.mock
    @pytest.mark.asyncio
    async def test_validate_ok(self):
        respx.get("https://admin.googleapis.com/admin/directory/v1/users").mock(
            return_value=httpx.Response(200, json={"users": [{"id": "u1"}]})
        )
        c = GoogleWorkspaceConnector({"access_token": "tok", "domain": "test.com"})
        assert await c.validate_credentials() is True

    @respx.mock
    @pytest.mark.asyncio
    async def test_discover_identities(self):
        respx.get("https://admin.googleapis.com/admin/directory/v1/users").mock(
            return_value=httpx.Response(200, json={"users": [
                {"id": "u1", "primaryEmail": "a@test.com", "name": {"fullName": "Ana"}, "isEnrolledIn2Sv": True, "suspended": False, "isAdmin": False},
            ]})
        )
        respx.get("https://admin.googleapis.com/admin/directory/v1/groups").mock(
            return_value=httpx.Response(200, json={"groups": [{"id": "g1", "name": "IT", "email": "it@test.com"}]})
        )
        c = GoogleWorkspaceConnector({"access_token": "tok", "domain": "test.com"})
        ids = await c.discover_identities()
        assert len(ids) == 2
        assert ids[0].mfa_enabled is True

    @respx.mock
    @pytest.mark.asyncio
    async def test_discover_assets(self):
        respx.get("https://admin.googleapis.com/admin/directory/v1/customer/my_customer/devices/mobile").mock(
            return_value=httpx.Response(200, json={"mobiledevices": [
                {"resourceId": "d1", "model": "Pixel 8", "os": "Android", "type": "ANDROID"},
            ]})
        )
        c = GoogleWorkspaceConnector({"access_token": "tok", "domain": "test.com"})
        assets = await c.discover_assets()
        assert len(assets) == 1
        assert assets[0].asset_type == "mobile_device"


class TestAWSConnector:
    @pytest.mark.asyncio
    async def test_validate_fails_without_real_aws(self):
        """Without real AWS creds, validate should fail gracefully."""
        c = AWSConnector({"role_arn": "arn:aws:iam::123:role/fake", "region": "eu-west-1"})
        result = await c.validate_credentials()
        assert result is False


class TestAzureConnector:
    @respx.mock
    @pytest.mark.asyncio
    async def test_validate_ok(self):
        respx.post("https://login.microsoftonline.com/t1/oauth2/v2.0/token").mock(
            return_value=httpx.Response(200, json={"access_token": "tok"})
        )
        c = AzureConnector({"tenant_id": "t1", "client_id": "c", "client_secret": "s", "subscription_id": "sub1"})
        assert await c.validate_credentials() is True

    @respx.mock
    @pytest.mark.asyncio
    async def test_discover_identities(self):
        respx.post("https://login.microsoftonline.com/t1/oauth2/v2.0/token").mock(
            return_value=httpx.Response(200, json={"access_token": "tok"})
        )
        respx.get("https://graph.microsoft.com/v1.0/users").mock(
            return_value=httpx.Response(200, json={"value": [
                {"id": "u1", "displayName": "Ana", "mail": "ana@az.com", "accountEnabled": True},
            ]})
        )
        respx.get("https://graph.microsoft.com/v1.0/groups").mock(
            return_value=httpx.Response(200, json={"value": [{"id": "g1", "displayName": "DevOps", "securityEnabled": True}]})
        )
        c = AzureConnector({"tenant_id": "t1", "client_id": "c", "client_secret": "s"})
        ids = await c.discover_identities()
        assert len(ids) == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_discover_assets(self):
        respx.post("https://login.microsoftonline.com/t1/oauth2/v2.0/token").mock(
            return_value=httpx.Response(200, json={"access_token": "tok"})
        )
        respx.get("https://management.azure.com/subscriptions/sub1/resources").mock(
            return_value=httpx.Response(200, json={"value": [
                {"id": "/subs/sub1/rg/rg1/Microsoft.Compute/virtualMachines/vm1", "name": "vm1", "type": "Microsoft.Compute/virtualMachines", "location": "westeurope"},
            ]})
        )
        c = AzureConnector({"tenant_id": "t1", "client_id": "c", "client_secret": "s", "subscription_id": "sub1"})
        assets = await c.discover_assets()
        assert len(assets) == 1


class TestConnectorRegistryExpanded:
    def test_5_providers_registered(self):
        # Force registration by importing all connectors
        from backend.app.motors.m16_onboarding.connectors import microsoft365, github_connector  # noqa
        from backend.app.motors.m16_onboarding.connectors import google_workspace, aws_connector, azure_connector  # noqa
        providers = list_available_providers()
        assert len(providers) == 5
        values = {p.value for p in providers}
        assert "google_workspace" in values
        assert "aws" in values
        assert "azure" in values


# ==== CATALOG TESTS ====

class TestExpandedCatalog:
    def test_full_matrix_loaded(self):
        ts = reload_templates()
        assert len(ts) >= 70, f"Expected full 10x7 matrix, got {len(ts)}"

    def test_5_sectors_covered(self):
        ts = reload_templates()
        sectors = {t.sector.value for t in ts}
        assert "servicios_profesionales" in sectors
        assert "saas_tech" in sectors
        assert "fintech" in sectors
        assert "industria" in sectors
        assert "generico" in sectors

    def test_generico_has_rrhh(self):
        ts = reload_templates()
        rrhh = [t for t in ts if t.sector.value == "generico" and t.role.value == "rrhh"]
        assert len(rrhh) == 1

    def test_all_templates_have_valid_questions(self):
        ts = reload_templates()
        for t in ts:
            assert len(t.questions) >= 3, f"{t.id} has {len(t.questions)} questions"
            ids = [q.id for q in t.questions]
            assert len(ids) == len(set(ids)), f"{t.id} has duplicate question ids"

    def test_fintech_sponsor_exists(self):
        from backend.app.motors.m16_onboarding.catalog_loader import find_template_for
        t = find_template_for(Sector.FINTECH, Role.SPONSOR)
        assert t is not None


# ==== HARDENING TESTS ====

class TestSessionExpiration:
    @pytest.mark.asyncio
    async def test_expired_session_auto_transitions(self, async_client, db):
        """Session past expires_at auto-transitions to EXPIRED on list."""
        _, project_id = await setup_test_project(db)

        r = await async_client.post(
            f"{BASE}/projects/{project_id}/sessions",
            json={"sector": "servicios_profesionales", "role": "sponsor",
                   "interlocutor_email": "a@x.com", "ttl_hours": 1},
        )
        sid = r.json()["session_id"]

        # Force expires_at to past
        async with _admin_setup(db):
            await db.execute(text(
                "UPDATE onboarding_sessions SET expires_at = :exp WHERE id = :sid"
            ), {"exp": datetime.now(timezone.utc) - timedelta(hours=2), "sid": sid})
        await db.flush()

        # List should auto-expire
        r = await async_client.get(f"{BASE}/projects/{project_id}/sessions")
        assert r.status_code == 200
        found = [s for s in r.json() if s["id"] == sid]
        assert found[0]["state"] == "expired"

    @pytest.mark.asyncio
    async def test_expired_sessions_endpoint(self, async_client, db):
        _, project_id = await setup_test_project(db)

        r = await async_client.post(
            f"{BASE}/projects/{project_id}/sessions",
            json={"sector": "servicios_profesionales", "role": "sponsor",
                   "interlocutor_email": "a@x.com", "ttl_hours": 1},
        )
        sid = r.json()["session_id"]

        async with _admin_setup(db):
            await db.execute(text(
                "UPDATE onboarding_sessions SET expires_at = :exp WHERE id = :sid"
            ), {"exp": datetime.now(timezone.utc) - timedelta(hours=2), "sid": sid})
        await db.flush()

        # Force expire via list first
        await async_client.get(f"{BASE}/projects/{project_id}/sessions")

        r = await async_client.get(f"{BASE}/projects/{project_id}/sessions/expired")
        assert r.status_code == 200
        assert len(r.json()) >= 1


class TestConnectorAPIExpanded:
    @pytest.mark.asyncio
    async def test_configure_azure(self, async_client, db):
        _, project_id = await setup_test_project(db)
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/connectors/configure",
            json={"provider": "azure", "credentials": {"tenant_id": "t", "client_id": "c", "client_secret": "s", "subscription_id": "sub"}},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "configured"

    @pytest.mark.asyncio
    async def test_configure_google(self, async_client, db):
        _, project_id = await setup_test_project(db)
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/connectors/configure",
            json={"provider": "google_workspace", "credentials": {"access_token": "tok", "domain": "test.com"}},
        )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_configure_aws(self, async_client, db):
        _, project_id = await setup_test_project(db)
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/connectors/configure",
            json={"provider": "aws", "credentials": {"role_arn": "arn:aws:iam::123:role/x"}},
        )
        assert r.status_code == 200
