"""Tests M22 Paso 6 — OAuth connectors (M365 + AWS) con fetcher mockeado."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.app.motors.m22_discovery.paso6_aws_connector import (
    AWSDiscoveryResult,
)
from backend.app.motors.m22_discovery.paso6_demo_mocks import (
    EXPECTED_DATAFORMA_METRICS,
    build_aws_connector_dataforma,
    build_aws_fetcher,
    build_m365_connector_dataforma,
)
from backend.app.motors.m22_discovery.paso6_m365_connector import (
    M365DiscoveryResult,
    REQUIRED_SCOPES,
    authorization_url,
    needs_refresh,
)


# ════════════════════════════════════════════════════════════════════
# OAuth helpers
# ════════════════════════════════════════════════════════════════════

class TestM365OAuthHelpers:
    def test_scopes_covers_required(self):
        assert "User.Read.All" in REQUIRED_SCOPES
        assert "SecurityEvents.Read.All" in REQUIRED_SCOPES
        assert "offline_access" in REQUIRED_SCOPES
        assert len(REQUIRED_SCOPES) >= 7

    def test_authorization_url_includes_state_and_scopes(self):
        url = authorization_url(
            tenant_id="tnt-123", client_id="cli-456",
            redirect_uri="https://fulkro.es/cb",
            state="abc-xyz",
        )
        assert "tnt-123" in url
        assert "client_id=cli-456" in url
        assert "state=abc-xyz" in url
        assert "User.Read.All" in url

    def test_needs_refresh_expired(self):
        past = datetime.now(timezone.utc) - timedelta(minutes=5)
        assert needs_refresh({"expires_at": past.isoformat()}) is True

    def test_needs_refresh_fresh(self):
        future = datetime.now(timezone.utc) + timedelta(hours=2)
        assert needs_refresh({"expires_at": future.isoformat()}) is False


# ════════════════════════════════════════════════════════════════════
# M365 Paso 6 discovery (via mock fetcher)
# ════════════════════════════════════════════════════════════════════

class TestM365DiscoveryDataForma:
    @pytest.mark.asyncio
    async def test_discover_users_returns_20(self):
        connector = build_m365_connector_dataforma()
        users = await connector.discover_users()
        assert len(users) == 20
        assert all(u.identity_type == "user" for u in users)
        assert all(u.provider == "microsoft_365" for u in users)

    @pytest.mark.asyncio
    async def test_discover_conditional_access_policies(self):
        connector = build_m365_connector_dataforma()
        policies = await connector.discover_conditional_access_policies()
        assert len(policies) == 3
        enabled = [p for p in policies if p.state == "enabled"]
        assert len(enabled) == 2

    @pytest.mark.asyncio
    async def test_discover_secure_score(self):
        connector = build_m365_connector_dataforma()
        score = await connector.discover_secure_score()
        assert score is not None
        assert score.percentage == pytest.approx(45.0, abs=0.1)
        assert score.max_score == 720

    @pytest.mark.asyncio
    async def test_run_paso6_discovery_assembles_result(self):
        connector = build_m365_connector_dataforma()
        result: M365DiscoveryResult = await connector.run_paso6_discovery()
        assert len(result.identities) == 24  # 20 users + 4 groups
        assert len(result.assets) == 8  # devices
        assert len(result.conditional_access_policies) == 3
        assert len(result.privileged_users) == 3
        mfa_true = sum(1 for v in result.mfa_by_user.values() if v)
        assert mfa_true == EXPECTED_DATAFORMA_METRICS["mfa_covered_users"]

    @pytest.mark.asyncio
    async def test_to_discovery_result_produces_summary(self):
        connector = build_m365_connector_dataforma()
        r = await connector.run_paso6_discovery()
        dr = r.to_discovery_result()
        assert dr.summary["total_identities"] == 24
        assert dr.summary["ca_policies_enabled"] == 2
        assert dr.summary["privileged_count"] == 3


# ════════════════════════════════════════════════════════════════════
# AWS Paso 6 discovery (via mock fetcher)
# ════════════════════════════════════════════════════════════════════

class TestAWSDiscoveryDataForma:
    @pytest.mark.asyncio
    async def test_discover_iam_users_and_roles(self):
        connector = build_aws_connector_dataforma()
        identities = await connector.discover_iam()
        users = [i for i in identities if i.identity_type == "user"]
        roles = [i for i in identities if i.identity_type == "service_account"]
        assert len(users) == 2
        assert len(roles) == 3
        admin_roles = [r for r in roles if r.is_privileged]
        assert len(admin_roles) == 1  # DataFormaAdminRole

    @pytest.mark.asyncio
    async def test_discover_s3_finds_unencrypted(self):
        connector = build_aws_connector_dataforma()
        assets, configs = await connector.discover_s3()
        assert len(assets) == 5
        unencrypted = [c for c in configs if not c.encryption_enabled]
        assert len(unencrypted) == 3
        unencrypted_names = {c.name for c in unencrypted}
        assert "dataforma-public-marketing" in unencrypted_names

    @pytest.mark.asyncio
    async def test_discover_rds_identifies_unencrypted(self):
        connector = build_aws_connector_dataforma()
        _, configs = await connector.discover_rds()
        assert len(configs) == 2
        unenc = [c for c in configs if not c.storage_encrypted]
        assert len(unenc) == 1
        assert unenc[0].instance_id == "df-facturacion-prod"

    @pytest.mark.asyncio
    async def test_discover_cloudtrail_multiregion(self):
        connector = build_aws_connector_dataforma()
        trails = await connector.discover_cloudtrail()
        assert len(trails) == 1
        t = trails[0]
        assert t.is_multi_region is True
        assert t.is_logging is True
        assert t.log_file_validation_enabled is True

    @pytest.mark.asyncio
    async def test_discover_guardduty_parses_findings(self):
        connector = build_aws_connector_dataforma()
        findings = await connector.discover_guardduty()
        assert len(findings) == 2
        high_sev = [f for f in findings if f.severity >= 7.0]
        assert len(high_sev) == 1
        assert high_sev[0].severity_label == "alta"

    @pytest.mark.asyncio
    async def test_run_paso6_discovery_aws_assembles(self):
        connector = build_aws_connector_dataforma()
        result: AWSDiscoveryResult = await connector.run_paso6_discovery()
        # 5 identities (2 users + 3 roles)
        assert len(result.identities) == 5
        # 12 assets = 5 EC2 + 5 S3 + 2 RDS
        assert len(result.assets) == 12
        s3_unenc = sum(1 for b in result.s3_buckets if not b.encryption_enabled)
        assert s3_unenc == 3
        rds_unenc = sum(1 for r in result.rds_instances if not r.storage_encrypted)
        assert rds_unenc == 1
        assert result.security_hub is not None
        assert result.security_hub.enabled is True
        assert "eu-west-1" in result.active_regions

    @pytest.mark.asyncio
    async def test_aws_fetcher_handles_unknown_operation_gracefully(self):
        fetcher = build_aws_fetcher()
        assert await fetcher("unknown", "nothing", None) == {}
