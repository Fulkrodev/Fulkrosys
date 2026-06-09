"""GitHub connector via PAT (Personal Access Token)."""
from __future__ import annotations

import logging

import httpx

from .base import BaseConnector, ConnectorProvider, DiscoveredAssetDTO, DiscoveredIdentityDTO
from .registry import register_connector

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


class GitHubConnector(BaseConnector):
    provider = ConnectorProvider.GITHUB

    def __init__(self, credentials: dict):
        super().__init__(credentials)
        self.token = credentials["personal_access_token"]
        self.organization = credentials.get("organization")

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def _gh_get(self, path: str, params: dict = None) -> list | dict:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{GITHUB_API}{path}",
                headers=self._headers(),
                params=params or {},
                timeout=30,
            )
            r.raise_for_status()
            return r.json()

    async def validate_credentials(self) -> bool:
        try:
            data = await self._gh_get("/user")
            return "login" in data
        except Exception as exc:
            logger.warning(f"GitHub validate failed: {exc}")
            return False

    async def discover_assets(self) -> list[DiscoveredAssetDTO]:
        assets = []
        try:
            if self.organization:
                repos = await self._gh_get(f"/orgs/{self.organization}/repos", params={"per_page": "100", "type": "all"})
            else:
                repos = await self._gh_get("/user/repos", params={"per_page": "100", "type": "owner"})
            for repo in repos:
                tags = []
                if repo.get("private"):
                    tags.append("private")
                if repo.get("archived"):
                    tags.append("archived")
                if repo.get("language"):
                    tags.append(repo["language"])
                assets.append(DiscoveredAssetDTO(
                    external_id=str(repo["id"]),
                    name=repo["full_name"],
                    asset_type="repository",
                    provider="github",
                    tags=tags,
                    criticality="medium" if repo.get("private") else "low",
                    raw_data={
                        "id": repo["id"], "full_name": repo["full_name"],
                        "private": repo.get("private"), "default_branch": repo.get("default_branch"),
                        "language": repo.get("language"),
                    },
                ))
        except Exception as exc:
            logger.warning(f"GitHub repos failed: {exc}")
        return assets

    async def discover_identities(self) -> list[DiscoveredIdentityDTO]:
        identities = []
        if not self.organization:
            try:
                user = await self._gh_get("/user")
                identities.append(DiscoveredIdentityDTO(
                    external_id=str(user["id"]),
                    email=user.get("email"),
                    display_name=user.get("name") or user["login"],
                    identity_type="user",
                    provider="github",
                    is_active=True,
                    raw_data={"login": user["login"], "id": user["id"]},
                ))
            except Exception as exc:
                logger.warning(f"GitHub user failed: {exc}")
            return identities
        try:
            members = await self._gh_get(f"/orgs/{self.organization}/members", params={"per_page": "100"})
            for m in members:
                identities.append(DiscoveredIdentityDTO(
                    external_id=str(m["id"]),
                    email=None,
                    display_name=m["login"],
                    identity_type="user",
                    provider="github",
                    is_active=True,
                    is_privileged=m.get("site_admin", False),
                    raw_data={"login": m["login"], "id": m["id"]},
                ))
        except Exception as exc:
            logger.warning(f"GitHub members failed: {exc}")
        return identities


register_connector(ConnectorProvider.GITHUB, GitHubConnector)
