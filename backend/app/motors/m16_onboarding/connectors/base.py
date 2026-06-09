"""Base framework for discovery connectors."""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class ConnectorProvider(str, Enum):
    MICROSOFT_365 = "microsoft_365"
    GITHUB = "github"
    GOOGLE_WORKSPACE = "google_workspace"
    AWS = "aws"
    AZURE = "azure"


@dataclass
class DiscoveredAssetDTO:
    external_id: str
    name: str
    asset_type: str
    provider: str
    raw_data: dict = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    criticality: Optional[str] = None
    discovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DiscoveredIdentityDTO:
    external_id: str
    email: Optional[str]
    display_name: str
    identity_type: str
    provider: str
    mfa_enabled: Optional[bool] = None
    is_privileged: bool = False
    is_active: bool = True
    raw_data: dict = field(default_factory=dict)
    discovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DiscoveryResult:
    provider: str
    success: bool
    assets: list[DiscoveredAssetDTO] = field(default_factory=list)
    identities: list[DiscoveredIdentityDTO] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    summary: dict = field(default_factory=dict)


class BaseConnector(ABC):
    provider: ConnectorProvider

    def __init__(self, credentials: dict):
        self.credentials = credentials

    @abstractmethod
    async def validate_credentials(self) -> bool: ...

    @abstractmethod
    async def discover_assets(self) -> list[DiscoveredAssetDTO]: ...

    @abstractmethod
    async def discover_identities(self) -> list[DiscoveredIdentityDTO]: ...

    async def run_full_discovery(self) -> DiscoveryResult:
        start = time.monotonic()
        errors: list[str] = []
        assets: list[DiscoveredAssetDTO] = []
        identities: list[DiscoveredIdentityDTO] = []

        try:
            assets = await self.discover_assets()
        except Exception as exc:
            errors.append(f"assets: {exc}")

        try:
            identities = await self.discover_identities()
        except Exception as exc:
            errors.append(f"identities: {exc}")

        duration = time.monotonic() - start

        return DiscoveryResult(
            provider=self.provider.value,
            success=len(errors) == 0,
            assets=assets,
            identities=identities,
            errors=errors,
            duration_seconds=round(duration, 2),
            summary={
                "total_assets": len(assets),
                "total_identities": len(identities),
                "asset_types": list({a.asset_type for a in assets}),
                "identity_types": list({i.identity_type for i in identities}),
            },
        )
