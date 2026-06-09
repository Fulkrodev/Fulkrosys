"""Tests M22-A Technical Discovery Foundation.

Cubre: orchestrator, asset_discovery, identity_discovery y API.
Los connectors M16 se aislan via fetcher mockeado (monkeypatch sobre
orchestrator._default_fetcher) para no ejecutar llamadas HTTP reales.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from backend.app.motors.m16_onboarding.connectors.base import (
    DiscoveredAssetDTO,
    DiscoveredIdentityDTO,
    DiscoveryResult,
)
from backend.app.motors.m22_discovery import (
    asset_discovery,
    identity_discovery,
    orchestrator,
)
from backend.tests.conftest import setup_test_project

BASE = "/api/v1/discovery"


# ========== Fetcher mock helpers ==========

def _asset_dto(external_id: str, name: str, atype: str, provider: str, **raw) -> DiscoveredAssetDTO:
    return DiscoveredAssetDTO(
        external_id=external_id, name=name, asset_type=atype,
        provider=provider, raw_data=raw,
    )


def _identity_dto(
    external_id: str, name: str, provider: str, itype: str = "user",
    mfa: bool | None = None, privileged: bool = False, active: bool = True,
    email: str | None = None, **raw,
) -> DiscoveredIdentityDTO:
    return DiscoveredIdentityDTO(
        external_id=external_id, email=email, display_name=name,
        identity_type=itype, provider=provider, mfa_enabled=mfa,
        is_privileged=privileged, is_active=active, raw_data=raw,
    )


def make_fetcher(by_provider: dict[str, DiscoveryResult]):
    async def fetcher(provider: str, config: dict):
        return by_provider.get(provider, DiscoveryResult(provider=provider, success=True))
    return fetcher


def install_fetcher(monkeypatch, by_provider: dict[str, DiscoveryResult]):
    monkeypatch.setattr(orchestrator, "_default_fetcher", make_fetcher(by_provider))


# ========== A. Unit-level: classify + infer ==========

class TestAssetClassify:
    def test_classify_m365_mailbox_to_D(self):
        assert asset_discovery.classify_magerit_type("m365_mailbox") == "D"

    def test_classify_aws_vpc_to_COM(self):
        assert asset_discovery.classify_magerit_type("aws_vpc") == "COM"

    def test_classify_server_to_HW(self):
        assert asset_discovery.classify_magerit_type("server") == "HW"

    def test_classify_unknown_bucket_fallback_D(self):
        assert asset_discovery.classify_magerit_type("some_custom_bucket") == "D"

    def test_infer_criticality_production_bumps(self):
        base = asset_discovery.infer_criticality("HW", {"environment": "prod"})
        assert base == "alta"

    def test_infer_criticality_pii_data_is_alta_min(self):
        assert asset_discovery.infer_criticality("SW", {"has_pii": True}) == "alta"

    def test_infer_criticality_public_bumps(self):
        crit = asset_discovery.infer_criticality("SW", {"internet_facing": True})
        assert crit == "alta"


# ========== B. Discovery Run CRUD + execution ==========

class TestDiscoveryRun:
    @pytest.mark.asyncio
    async def test_create_run(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        install_fetcher(monkeypatch, {})
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"modules": ["assets"], "connector_sources": {}, "execute": False},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "pending"
        assert body["modules"] == ["assets"]
        assert body["progress"]["assets"]["status"] == "pending"

    @pytest.mark.asyncio
    async def test_create_run_rejects_invalid_module(self, async_client, db):
        _, project_id = await setup_test_project(db)
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"modules": ["nope"], "connector_sources": {}, "execute": False},
        )
        assert r.status_code == 422, r.text

    @pytest.mark.asyncio
    async def test_execute_run_skips_unimplemented_modules(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        install_fetcher(monkeypatch, {})
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={
                "modules": ["assets", "vulnerabilities", "logs"],
                "connector_sources": {},
                "execute": True,
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "completed"
        assert body["progress"]["assets"]["status"] == "completed"
        # M22-B: vulnerabilities -> awaiting_import (import manual, no scan)
        assert body["progress"]["vulnerabilities"]["status"] == "awaiting_import"
        # M22-C: logs ya esta implementado -> completed
        assert body["progress"]["logs"]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_list_and_get_run(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        install_fetcher(monkeypatch, {})
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"modules": ["assets"], "connector_sources": {}, "execute": False},
        )
        rid = r.json()["id"]
        rl = await async_client.get(f"{BASE}/projects/{project_id}/runs")
        assert rl.status_code == 200
        assert any(x["id"] == rid for x in rl.json())
        rg = await async_client.get(f"{BASE}/projects/{project_id}/runs/{rid}")
        assert rg.status_code == 200
        assert rg.json()["id"] == rid

    @pytest.mark.asyncio
    async def test_cancel_run(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        install_fetcher(monkeypatch, {})
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"modules": ["assets"], "connector_sources": {}, "execute": False},
        )
        rid = r.json()["id"]
        cancel = await async_client.post(f"{BASE}/projects/{project_id}/runs/{rid}/cancel")
        assert cancel.status_code == 200
        assert cancel.json()["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_soft_delete_run(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        install_fetcher(monkeypatch, {})
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"modules": ["assets"], "connector_sources": {}, "execute": False},
        )
        rid = r.json()["id"]
        d = await async_client.delete(f"{BASE}/projects/{project_id}/runs/{rid}")
        assert d.status_code == 200
        gone = await async_client.get(f"{BASE}/projects/{project_id}/runs/{rid}")
        assert gone.status_code == 404


# ========== C. Assets via API con fetcher mockeado ==========

class TestAssetDiscovery:
    @pytest.mark.asyncio
    async def test_run_assets_m365_and_aws(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        fetched = {
            "microsoft_365": DiscoveryResult(
                provider="microsoft_365", success=True,
                assets=[
                    _asset_dto("mbx1", "Buzon CEO", "m365_mailbox", "microsoft_365", has_pii=True),
                    _asset_dto("site1", "SP Finance", "m365_sharepoint_site", "microsoft_365"),
                ],
            ),
            "aws": DiscoveryResult(
                provider="aws", success=True,
                assets=[
                    _asset_dto("vpc-1", "vpc-prod", "aws_vpc", "aws", environment="prod"),
                    _asset_dto("i-1", "web-prod", "aws_ec2_instance", "aws",
                               environment="prod", internet_facing=True),
                    _asset_dto("bkt-1", "data-lake", "aws_s3_bucket", "aws", has_pii=True),
                ],
            ),
        }
        install_fetcher(monkeypatch, fetched)
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={
                "modules": ["assets"],
                "connector_sources": {"microsoft_365": {}, "aws": {}},
                "execute": True,
            },
        )
        assert r.status_code == 200, r.text
        assert r.json()["progress"]["assets"]["count"] == 5

        lst = await async_client.get(f"{BASE}/projects/{project_id}/assets")
        assets = lst.json()
        assert len(assets) == 5
        tipos = {a["tipo_magerit"] for a in assets}
        assert tipos == {"D", "COM", "HW"}

    @pytest.mark.asyncio
    async def test_assets_summary_groups_by_type_and_criticality(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        fetched = {
            "aws": DiscoveryResult(
                provider="aws", success=True,
                assets=[
                    _asset_dto("vpc-1", "vpc", "aws_vpc", "aws"),
                    _asset_dto("bkt-1", "b1", "aws_s3_bucket", "aws", has_pii=True),
                    _asset_dto("i-1", "ec2", "aws_ec2_instance", "aws"),
                ],
            ),
        }
        install_fetcher(monkeypatch, fetched)
        await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={
                "modules": ["assets"],
                "connector_sources": {"aws": {}},
                "execute": True,
            },
        )
        s = await async_client.get(f"{BASE}/projects/{project_id}/assets/summary")
        assert s.status_code == 200
        body = s.json()
        assert body["total"] == 3
        assert body["by_tipo_magerit"]["COM"] == 1
        assert body["by_tipo_magerit"]["D"] == 1
        assert body["by_tipo_magerit"]["HW"] == 1
        assert body["by_fuente"]["aws"] == 3

    @pytest.mark.asyncio
    async def test_asset_creates_pkg_node(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        fetched = {
            "aws": DiscoveryResult(
                provider="aws", success=True,
                assets=[_asset_dto("vpc-1", "vpc", "aws_vpc", "aws")],
            ),
        }
        install_fetcher(monkeypatch, fetched)
        await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={
                "modules": ["assets"],
                "connector_sources": {"aws": {}},
                "execute": True,
            },
        )
        lst = await async_client.get(f"{BASE}/projects/{project_id}/assets")
        asset = lst.json()[0]
        assert asset["pkg_node_id"] is not None

    @pytest.mark.asyncio
    async def test_assets_filter_by_tipo_magerit(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        fetched = {
            "aws": DiscoveryResult(
                provider="aws", success=True,
                assets=[
                    _asset_dto("vpc-1", "vpc", "aws_vpc", "aws"),
                    _asset_dto("i-1", "ec2", "aws_ec2_instance", "aws"),
                ],
            ),
        }
        install_fetcher(monkeypatch, fetched)
        await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={
                "modules": ["assets"],
                "connector_sources": {"aws": {}},
                "execute": True,
            },
        )
        r = await async_client.get(f"{BASE}/projects/{project_id}/assets?tipo_magerit=COM")
        assert r.status_code == 200
        items = r.json()
        assert len(items) == 1
        assert items[0]["tipo_magerit"] == "COM"

    @pytest.mark.asyncio
    async def test_soft_delete_asset(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        fetched = {
            "aws": DiscoveryResult(
                provider="aws", success=True,
                assets=[_asset_dto("vpc-1", "vpc", "aws_vpc", "aws")],
            ),
        }
        install_fetcher(monkeypatch, fetched)
        await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={
                "modules": ["assets"],
                "connector_sources": {"aws": {}},
                "execute": True,
            },
        )
        lst = await async_client.get(f"{BASE}/projects/{project_id}/assets")
        aid = lst.json()[0]["id"]
        d = await async_client.delete(f"{BASE}/projects/{project_id}/assets/{aid}")
        assert d.status_code == 200
        gone = await async_client.get(f"{BASE}/projects/{project_id}/assets/{aid}")
        assert gone.status_code == 404


# ========== D. Identity Discovery + Alerts ==========

class TestIdentityDiscovery:
    @pytest.mark.asyncio
    async def test_run_identities_from_m365(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        stale = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
        fetched = {
            "microsoft_365": DiscoveryResult(
                provider="microsoft_365", success=True,
                identities=[
                    _identity_dto("priv_admin", "Ana Admin", "microsoft_365",
                                  mfa=False, privileged=True),
                    _identity_dto("std_user", "User Std", "microsoft_365",
                                  mfa=True),
                    _identity_dto("stale_user", "Stale U", "microsoft_365",
                                  mfa=True, last_sign_in=stale),
                ],
            ),
        }
        install_fetcher(monkeypatch, fetched)
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={
                "modules": ["identities"],
                "connector_sources": {"microsoft_365": {}},
                "execute": True,
            },
        )
        assert r.status_code == 200, r.text
        assert r.json()["progress"]["identities"]["count"] == 3

        lst = await async_client.get(f"{BASE}/projects/{project_id}/identities")
        ids = lst.json()
        assert len(ids) == 3
        priv = next(i for i in ids if i["username"] == "priv_admin")
        assert priv["tipo_cuenta"] == "privilegiada"
        assert priv["es_privilegiada"] is True
        assert priv["mfa_activo"] is False

    @pytest.mark.asyncio
    async def test_alert_priv_no_mfa_is_critica(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        fetched = {
            "microsoft_365": DiscoveryResult(
                provider="microsoft_365", success=True,
                identities=[_identity_dto("priv_admin", "Ana", "microsoft_365",
                                          mfa=False, privileged=True)],
            ),
        }
        install_fetcher(monkeypatch, fetched)
        await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={
                "modules": ["identities"],
                "connector_sources": {"microsoft_365": {}},
                "execute": True,
            },
        )
        alerts = (await async_client.get(
            f"{BASE}/projects/{project_id}/alerts?severidad=critica"
        )).json()
        codes = {a["codigo"] for a in alerts}
        assert "PRIV_NO_MFA" in codes

    @pytest.mark.asyncio
    async def test_alert_inactive_90d_is_alta(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        stale = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
        fetched = {
            "microsoft_365": DiscoveryResult(
                provider="microsoft_365", success=True,
                identities=[_identity_dto("stale", "S", "microsoft_365",
                                          mfa=True, last_sign_in=stale)],
            ),
        }
        install_fetcher(monkeypatch, fetched)
        await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={
                "modules": ["identities"],
                "connector_sources": {"microsoft_365": {}},
                "execute": True,
            },
        )
        alerts = (await async_client.get(f"{BASE}/projects/{project_id}/alerts")).json()
        assert any(a["codigo"] == "INACTIVE_90D" and a["severidad"] == "alta" for a in alerts)

    @pytest.mark.asyncio
    async def test_alert_external_privileged_critica(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        fetched = {
            "microsoft_365": DiscoveryResult(
                provider="microsoft_365", success=True,
                identities=[_identity_dto("ext_adm", "Ext", "microsoft_365",
                                          mfa=True, privileged=True, itype="guest",
                                          userType="Guest")],
            ),
        }
        install_fetcher(monkeypatch, fetched)
        await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={
                "modules": ["identities"],
                "connector_sources": {"microsoft_365": {}},
                "execute": True,
            },
        )
        alerts = (await async_client.get(f"{BASE}/projects/{project_id}/alerts")).json()
        codes = {a["codigo"] for a in alerts}
        assert "EXTERNAL_PRIVILEGED" in codes

    @pytest.mark.asyncio
    async def test_identity_summary_mfa_coverage(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        fetched = {
            "microsoft_365": DiscoveryResult(
                provider="microsoft_365", success=True,
                identities=[
                    _identity_dto("u1", "U1", "microsoft_365", mfa=True),
                    _identity_dto("u2", "U2", "microsoft_365", mfa=True),
                    _identity_dto("u3", "U3", "microsoft_365", mfa=False),
                    _identity_dto("u4", "U4", "microsoft_365", mfa=False, privileged=True),
                ],
            ),
        }
        install_fetcher(monkeypatch, fetched)
        await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={
                "modules": ["identities"],
                "connector_sources": {"microsoft_365": {}},
                "execute": True,
            },
        )
        s = await async_client.get(f"{BASE}/projects/{project_id}/identities/summary")
        body = s.json()
        assert body["total"] == 4
        assert body["privilegiadas"] == 1
        assert body["sin_mfa"] == 2
        assert body["mfa_coverage"]["percentage"] == 50.0

    @pytest.mark.asyncio
    async def test_filter_privilegiadas_only(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        fetched = {
            "microsoft_365": DiscoveryResult(
                provider="microsoft_365", success=True,
                identities=[
                    _identity_dto("std", "S", "microsoft_365", mfa=True),
                    _identity_dto("adm", "A", "microsoft_365", mfa=True, privileged=True),
                ],
            ),
        }
        install_fetcher(monkeypatch, fetched)
        await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={
                "modules": ["identities"],
                "connector_sources": {"microsoft_365": {}},
                "execute": True,
            },
        )
        r = await async_client.get(
            f"{BASE}/projects/{project_id}/identities?es_privilegiada=true"
        )
        items = r.json()
        assert len(items) == 1
        assert items[0]["username"] == "adm"

    @pytest.mark.asyncio
    async def test_identity_creates_pkg_node(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        fetched = {
            "microsoft_365": DiscoveryResult(
                provider="microsoft_365", success=True,
                identities=[_identity_dto("u1", "U1", "microsoft_365", mfa=True)],
            ),
        }
        install_fetcher(monkeypatch, fetched)
        await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={
                "modules": ["identities"],
                "connector_sources": {"microsoft_365": {}},
                "execute": True,
            },
        )
        lst = await async_client.get(f"{BASE}/projects/{project_id}/identities")
        assert lst.json()[0]["pkg_node_id"] is not None


# ========== E. Alerts summary ==========

class TestAlertsSummary:
    @pytest.mark.asyncio
    async def test_alerts_summary_by_severidad_and_modulo(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        stale = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
        fetched = {
            "microsoft_365": DiscoveryResult(
                provider="microsoft_365", success=True,
                identities=[
                    _identity_dto("priv", "P", "microsoft_365", mfa=False, privileged=True),
                    _identity_dto("stale", "S", "microsoft_365",
                                  mfa=True, last_sign_in=stale),
                ],
            ),
        }
        install_fetcher(monkeypatch, fetched)
        await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={
                "modules": ["identities"],
                "connector_sources": {"microsoft_365": {}},
                "execute": True,
            },
        )
        s = await async_client.get(f"{BASE}/projects/{project_id}/alerts/summary")
        body = s.json()
        assert body["total"] >= 2
        assert body["by_severidad"].get("critica", 0) >= 1
        assert body["by_severidad"].get("alta", 0) >= 1
        assert body["by_modulo"].get("identities", 0) >= 2
