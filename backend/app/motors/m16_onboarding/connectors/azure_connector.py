"""Azure connector via Service Principal + REST API (httpx, no azure-* deps)."""
from __future__ import annotations

import logging
from typing import Optional

import httpx

from .base import BaseConnector, ConnectorProvider, DiscoveredAssetDTO, DiscoveredIdentityDTO
from .registry import register_connector

logger = logging.getLogger(__name__)

AZURE_LOGIN = "https://login.microsoftonline.com"
AZURE_MGMT = "https://management.azure.com"
AZURE_GRAPH = "https://graph.microsoft.com/v1.0"


class AzureConnector(BaseConnector):
    """Connector using httpx against Azure REST APIs (same pattern as M365)."""

    provider = ConnectorProvider.AZURE

    def __init__(self, credentials: dict):
        super().__init__(credentials)
        self.tenant_id = credentials["tenant_id"]
        self.client_id = credentials["client_id"]
        self.client_secret = credentials["client_secret"]
        self.subscription_id = credentials.get("subscription_id", "")
        self._mgmt_token: Optional[str] = None
        self._graph_token: Optional[str] = None

    async def _get_token(self, scope: str) -> str:
        url = f"{AZURE_LOGIN}/{self.tenant_id}/oauth2/v2.0/token"
        # FIX P1-4: timeout en el POST del token (PRIMERA llamada externa). Sin
        # él un black-hole TCP contra login.microsoftonline.com colgaba el worker
        # indefinidamente (descubrimiento síncrono sin backstop Celery).
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": scope,
            })
            r.raise_for_status()
            return r.json()["access_token"]

    async def _mgmt_get(self, path: str, params: dict = None) -> dict:
        if not self._mgmt_token:
            self._mgmt_token = await self._get_token("https://management.azure.com/.default")
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{AZURE_MGMT}{path}",
                headers={"Authorization": f"Bearer {self._mgmt_token}"},
                params=params or {},
                timeout=30,
            )
            r.raise_for_status()
            return r.json()

    async def _graph_get(self, path: str, params: dict = None) -> dict:
        if not self._graph_token:
            self._graph_token = await self._get_token("https://graph.microsoft.com/.default")
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{AZURE_GRAPH}{path}",
                headers={"Authorization": f"Bearer {self._graph_token}"},
                params=params or {},
                timeout=30,
            )
            r.raise_for_status()
            return r.json()

    async def validate_credentials(self) -> bool:
        try:
            await self._get_token("https://management.azure.com/.default")
            return True
        except Exception as exc:
            logger.warning(f"Azure validate failed: {exc}")
            return False

    async def discover_identities(self) -> list[DiscoveredIdentityDTO]:
        identities = []
        try:
            data = await self._graph_get("/users", params={"$select": "id,displayName,mail,accountEnabled", "$top": "999"})
            for u in data.get("value", []):
                identities.append(DiscoveredIdentityDTO(
                    external_id=u["id"],
                    email=u.get("mail"),
                    display_name=u.get("displayName", "Unknown"),
                    identity_type="user",
                    provider="azure",
                    is_active=u.get("accountEnabled", True),
                    raw_data=u,
                ))
        except Exception as exc:
            logger.warning(f"Azure users failed: {exc}")
        try:
            data = await self._graph_get("/groups", params={"$select": "id,displayName,securityEnabled", "$top": "999"})
            for g in data.get("value", []):
                identities.append(DiscoveredIdentityDTO(
                    external_id=g["id"],
                    email=None,
                    display_name=g.get("displayName", "Unknown Group"),
                    identity_type="group",
                    provider="azure",
                    raw_data=g,
                ))
        except Exception as exc:
            logger.warning(f"Azure groups failed: {exc}")
        return identities

    async def discover_assets(self) -> list[DiscoveredAssetDTO]:
        assets = []
        if not self.subscription_id:
            return assets
        try:
            data = await self._mgmt_get(
                f"/subscriptions/{self.subscription_id}/resources",
                params={"api-version": "2021-04-01"},
            )
            for res in data.get("value", []):
                assets.append(DiscoveredAssetDTO(
                    external_id=res.get("id", ""),
                    name=res.get("name", "Unknown"),
                    asset_type=res.get("type", "azure_resource").split("/")[-1],
                    provider="azure",
                    tags=list((res.get("tags") or {}).values()),
                    raw_data={"type": res.get("type"), "location": res.get("location"), "kind": res.get("kind")},
                ))
        except Exception as exc:
            logger.warning(f"Azure resources failed: {exc}")
        return assets


register_connector(ConnectorProvider.AZURE, AzureConnector)
