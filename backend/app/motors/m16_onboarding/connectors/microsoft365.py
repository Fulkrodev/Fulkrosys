"""Microsoft 365 / Entra ID connector via Graph API (client_credentials).

Sesión 3B-2B.7 Ejecutable 4 Phase 7.1.1 polish (2026-05-27):
- MFA detection via /reports/authenticationMethods/userRegistrationDetails
- Privileged role detection via /directoryRoles + /directoryRoles/{id}/members
- SharePoint sites discovery via /sites?search=*
- Pagination follow @odata.nextLink (best-effort one extra page · MVP)
- Graceful degradation per endpoint (errors logged · NO interrumpe discovery)

ENS measures cobertura (per provider agent guidance):
- op.acc.6 nuclear MFA (mfa_enabled detection)
- op.acc.5 privileged users (is_privileged detection)
- mp.s.2 SharePoint sites públicos (sharing detection)
- mp.info.3 endpoint encryption (existing managedDevices)
- op.exp.1 inventory (assets discovery)

ADR-014 read-only OAuth sostained · NO destructive auto-execute.
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

from .base import BaseConnector, ConnectorProvider, DiscoveredAssetDTO, DiscoveredIdentityDTO
from .registry import register_connector

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
GRAPH_BETA = "https://graph.microsoft.com/beta"
LOGIN_BASE = "https://login.microsoftonline.com"


class Microsoft365Connector(BaseConnector):
    provider = ConnectorProvider.MICROSOFT_365

    def __init__(self, credentials: dict):
        super().__init__(credentials)
        self.tenant_id = credentials["tenant_id"]
        self.client_id = credentials["client_id"]
        self.client_secret = credentials["client_secret"]
        self._access_token: Optional[str] = None

    async def _get_access_token(self) -> str:
        if self._access_token:
            return self._access_token
        url = f"{LOGIN_BASE}/{self.tenant_id}/oauth2/v2.0/token"
        # FIX P1-4: timeout en el POST del token (PRIMERA llamada externa, contra
        # login.microsoftonline.com). httpx por defecto NO impone timeout → un
        # black-hole TCP colgaba el worker/onboarding indefinidamente (el path de
        # descubrimiento síncrono no tiene backstop Celery). Igual que los GET.
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "https://graph.microsoft.com/.default",
            })
            r.raise_for_status()
            self._access_token = r.json()["access_token"]
            return self._access_token

    async def _graph_get(self, path: str, params: dict = None, *, base: str = GRAPH_BASE) -> dict:
        token = await self._get_access_token()
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{base}{path}",
                headers={"Authorization": f"Bearer {token}"},
                params=params or {},
                timeout=30,
            )
            r.raise_for_status()
            return r.json()

    async def _graph_get_paged(
        self, path: str, params: dict = None, *, max_pages: int = 3, base: str = GRAPH_BASE,
    ) -> list[dict]:
        """Best-effort pagination follow @odata.nextLink · cap max_pages."""
        token = await self._get_access_token()
        all_items: list[dict] = []
        url = f"{base}{path}"
        page = 0
        async with httpx.AsyncClient() as client:
            while url and page < max_pages:
                r = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                    params=params if page == 0 else None,
                    timeout=30,
                )
                r.raise_for_status()
                data = r.json()
                all_items.extend(data.get("value", []))
                url = data.get("@odata.nextLink")
                page += 1
        return all_items

    async def validate_credentials(self) -> bool:
        try:
            await self._get_access_token()
            await self._graph_get("/organization", params={"$select": "id,displayName"})
            return True
        except Exception as exc:
            logger.warning(f"M365 validate failed: {exc}")
            return False

    async def _fetch_mfa_registration_map(self) -> dict[str, bool]:
        """Map user_id → mfa_registered (bool) via reports endpoint.

        Endpoint requires Reports.Read.All permission (best-practice M365 ENS).
        Graceful degradation: si fails → empty map · users default mfa_enabled=None.
        """
        mfa_map: dict[str, bool] = {}
        try:
            items = await self._graph_get_paged(
                "/reports/authenticationMethods/userRegistrationDetails",
                params={"$top": "999", "$select": "id,isMfaRegistered,isMfaCapable"},
            )
            for item in items:
                user_id = item.get("id")
                if not user_id:
                    continue
                mfa_map[user_id] = bool(item.get("isMfaRegistered", False))
        except Exception as exc:
            logger.warning(f"M365 MFA registration report failed (Reports.Read.All needed?): {exc}")
        return mfa_map

    async def _fetch_privileged_user_set(self) -> set[str]:
        """Set of user_ids that hold any directory role (admin/privileged).

        Endpoint: /directoryRoles + per-role /directoryRoles/{id}/members
        Graceful degradation: si fails → empty set · users default is_privileged=False.
        """
        privileged: set[str] = set()
        try:
            roles_data = await self._graph_get(
                "/directoryRoles", params={"$select": "id,displayName"},
            )
            for role in roles_data.get("value", []):
                role_id = role.get("id")
                if not role_id:
                    continue
                try:
                    members = await self._graph_get(
                        f"/directoryRoles/{role_id}/members",
                        params={"$select": "id", "$top": "999"},
                    )
                    for m in members.get("value", []):
                        uid = m.get("id")
                        if uid:
                            privileged.add(uid)
                except Exception as exc:
                    logger.debug(f"M365 role {role_id} members failed: {exc}")
        except Exception as exc:
            logger.warning(f"M365 directoryRoles failed (RoleManagement.Read.Directory needed?): {exc}")
        return privileged

    async def discover_identities(self) -> list[DiscoveredIdentityDTO]:
        identities: list[DiscoveredIdentityDTO] = []

        mfa_map = await self._fetch_mfa_registration_map()
        privileged_set = await self._fetch_privileged_user_set()

        try:
            users = await self._graph_get_paged("/users", params={
                "$select": "id,displayName,mail,userPrincipalName,accountEnabled,userType",
                "$top": "999",
            })
            for u in users:
                user_id = u["id"]
                mfa_enabled = mfa_map.get(user_id)
                is_privileged = user_id in privileged_set
                identities.append(DiscoveredIdentityDTO(
                    external_id=user_id,
                    email=u.get("mail") or u.get("userPrincipalName"),
                    display_name=u.get("displayName", "Unknown"),
                    identity_type="user",
                    provider="microsoft_365",
                    is_active=u.get("accountEnabled", True),
                    mfa_enabled=mfa_enabled,
                    is_privileged=is_privileged,
                    raw_data=u,
                ))
        except Exception as exc:
            logger.warning(f"M365 users failed: {exc}")
        try:
            groups = await self._graph_get_paged("/groups", params={
                "$select": "id,displayName,groupTypes,securityEnabled",
                "$top": "999",
            })
            for g in groups:
                identities.append(DiscoveredIdentityDTO(
                    external_id=g["id"],
                    email=None,
                    display_name=g.get("displayName", "Unknown Group"),
                    identity_type="group",
                    provider="microsoft_365",
                    raw_data=g,
                ))
        except Exception as exc:
            logger.warning(f"M365 groups failed: {exc}")
        return identities

    async def discover_assets(self) -> list[DiscoveredAssetDTO]:
        assets: list[DiscoveredAssetDTO] = []

        try:
            devices = await self._graph_get_paged(
                "/deviceManagement/managedDevices",
                params={
                    "$select": "id,deviceName,operatingSystem,osVersion,model,manufacturer,complianceState,managementAgent",
                    "$top": "999",
                },
            )
            for d in devices:
                assets.append(DiscoveredAssetDTO(
                    external_id=d["id"],
                    name=d.get("deviceName", "Unknown Device"),
                    asset_type="endpoint",
                    provider="microsoft_365",
                    tags=[d.get("operatingSystem", ""), d.get("complianceState", "")],
                    raw_data=d,
                ))
        except Exception as exc:
            logger.warning(f"M365 devices failed: {exc}")

        try:
            sites = await self._graph_get_paged(
                "/sites",
                params={"search": "*", "$select": "id,name,displayName,webUrl,siteCollection"},
            )
            for s in sites:
                sharing_caps = s.get("sharingCapability") or s.get("siteCollection", {}).get("sharingCapability")
                is_public = sharing_caps in {"ExternalUserAndGuestSharing", "ExistingExternalUserSharingOnly"}
                assets.append(DiscoveredAssetDTO(
                    external_id=s["id"],
                    name=s.get("displayName") or s.get("name", "Unknown Site"),
                    asset_type="sharepoint_site",
                    provider="microsoft_365",
                    tags=["sharepoint", sharing_caps or "internal"],
                    raw_data={
                        **s,
                        "public_access": is_public,
                        "is_public": is_public,
                    },
                ))
        except Exception as exc:
            logger.warning(f"M365 SharePoint sites failed (Sites.Read.All needed?): {exc}")

        return assets


register_connector(ConnectorProvider.MICROSOFT_365, Microsoft365Connector)
