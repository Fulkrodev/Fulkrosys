"""Google Workspace connector via Service Account + Admin SDK.

Sesión 3B-2B.7 Ejecutable 4 Phase 7.1.1 polish (2026-05-27):
- Shared drives discovery via /drives.list (Drive API)
- Pagination follow nextPageToken (best-effort one extra page · MVP)
- Graceful degradation per endpoint (errors logged · NO interrumpe discovery)

ENS measures cobertura (per provider agent guidance):
- op.acc.6 nuclear MFA (mfa_enabled via isEnrolledIn2Sv) ✅ existing
- op.acc.5 privileged users (is_privileged via isAdmin) ✅ existing
- mp.s.2 Shared drives sharing settings (drive_sharing detection)
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

ADMIN_API = "https://admin.googleapis.com/admin/directory/v1"
DRIVE_API = "https://www.googleapis.com/drive/v3"
TOKEN_URL = "https://oauth2.googleapis.com/token"


class GoogleWorkspaceConnector(BaseConnector):
    """Connector using httpx against Admin SDK REST API + Drive API."""

    provider = ConnectorProvider.GOOGLE_WORKSPACE

    def __init__(self, credentials: dict):
        super().__init__(credentials)
        self.access_token: Optional[str] = credentials.get("access_token")
        self.domain = credentials.get("domain", "")

    async def _get_token(self) -> str:
        if self.access_token:
            return self.access_token
        raise ValueError("access_token required (pre-generated via service account JWT)")

    async def _admin_get(self, path: str, params: dict = None) -> dict:
        token = await self._get_token()
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{ADMIN_API}{path}",
                headers={"Authorization": f"Bearer {token}"},
                params=params or {},
                timeout=30,
            )
            r.raise_for_status()
            return r.json()

    async def _drive_get(self, path: str, params: dict = None) -> dict:
        token = await self._get_token()
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{DRIVE_API}{path}",
                headers={"Authorization": f"Bearer {token}"},
                params=params or {},
                timeout=30,
            )
            r.raise_for_status()
            return r.json()

    async def _admin_get_paged(
        self, path: str, params: dict = None, *, result_key: str, max_pages: int = 3,
    ) -> list[dict]:
        """Best-effort pagination follow nextPageToken · cap max_pages."""
        token = await self._get_token()
        all_items: list[dict] = []
        page_token: Optional[str] = None
        page = 0
        async with httpx.AsyncClient() as client:
            while page < max_pages:
                merged_params = dict(params or {})
                if page_token:
                    merged_params["pageToken"] = page_token
                r = await client.get(
                    f"{ADMIN_API}{path}",
                    headers={"Authorization": f"Bearer {token}"},
                    params=merged_params,
                    timeout=30,
                )
                r.raise_for_status()
                data = r.json()
                all_items.extend(data.get(result_key, []))
                page_token = data.get("nextPageToken")
                if not page_token:
                    break
                page += 1
        return all_items

    async def validate_credentials(self) -> bool:
        try:
            await self._admin_get("/users", params={"domain": self.domain, "maxResults": "1"})
            return True
        except Exception as exc:
            logger.warning(f"Google Workspace validate failed: {exc}")
            return False

    async def discover_identities(self) -> list[DiscoveredIdentityDTO]:
        identities: list[DiscoveredIdentityDTO] = []
        try:
            users = await self._admin_get_paged(
                "/users",
                params={"domain": self.domain, "maxResults": "500"},
                result_key="users",
            )
            for u in users:
                identities.append(DiscoveredIdentityDTO(
                    external_id=u.get("id", ""),
                    email=u.get("primaryEmail"),
                    display_name=u.get("name", {}).get("fullName", "Unknown"),
                    identity_type="user",
                    provider="google_workspace",
                    mfa_enabled=u.get("isEnrolledIn2Sv", None),
                    is_active=not u.get("suspended", False),
                    is_privileged=u.get("isAdmin", False),
                    raw_data={"primaryEmail": u.get("primaryEmail"), "isAdmin": u.get("isAdmin")},
                ))
        except Exception as exc:
            logger.warning(f"Google users failed: {exc}")
        try:
            groups = await self._admin_get_paged(
                "/groups",
                params={"domain": self.domain, "maxResults": "200"},
                result_key="groups",
            )
            for g in groups:
                identities.append(DiscoveredIdentityDTO(
                    external_id=g.get("id", ""),
                    email=g.get("email"),
                    display_name=g.get("name", "Unknown Group"),
                    identity_type="group",
                    provider="google_workspace",
                    raw_data={"email": g.get("email"), "directMembersCount": g.get("directMembersCount")},
                ))
        except Exception as exc:
            logger.warning(f"Google groups failed: {exc}")
        return identities

    async def _fetch_shared_drives(self) -> list[dict]:
        """Best-effort fetch shared drives via Drive API.

        Graceful degradation: si fails → empty list.
        Requires Drive.Read scope on service account.
        """
        try:
            data = await self._drive_get(
                "/drives",
                params={"useDomainAdminAccess": "true", "pageSize": "100"},
            )
            return data.get("drives", [])
        except Exception as exc:
            logger.warning(f"Google shared drives failed (Drive scope needed?): {exc}")
            return []

    async def discover_assets(self) -> list[DiscoveredAssetDTO]:
        assets: list[DiscoveredAssetDTO] = []
        try:
            mobile = await self._admin_get_paged(
                "/customer/my_customer/devices/mobile",
                params={"maxResults": "200"},
                result_key="mobiledevices",
            )
            for d in mobile:
                assets.append(DiscoveredAssetDTO(
                    external_id=d.get("resourceId", ""),
                    name=d.get("model", "Unknown Device"),
                    asset_type="mobile_device",
                    provider="google_workspace",
                    tags=[d.get("os", ""), d.get("type", "")],
                    raw_data=d,
                ))
        except Exception as exc:
            logger.warning(f"Google mobile devices failed: {exc}")

        for drive in await self._fetch_shared_drives():
            restrictions = drive.get("restrictions") or {}
            domain_restricted = bool(restrictions.get("domainUsersOnly"))
            is_public = not domain_restricted
            assets.append(DiscoveredAssetDTO(
                external_id=drive.get("id", ""),
                name=drive.get("name", "Unknown Drive"),
                asset_type="shared_drive",
                provider="google_workspace",
                tags=["drive", "domain_restricted" if domain_restricted else "external_sharing_possible"],
                raw_data={
                    **drive,
                    "public_access": is_public,
                    "is_public": is_public,
                    "domain_restricted": domain_restricted,
                },
            ))

        return assets


register_connector(ConnectorProvider.GOOGLE_WORKSPACE, GoogleWorkspaceConnector)
