"""Base adapter · m_cloud_connectors (sub-atom 1.D.X.B v3.12).

Layer thin sobre M16 ``connectors.base.BaseConnector`` existing.

Diseño OPS-045 29ª aplicación: NO reinventar abstract class.
M16 ya provee ``BaseConnector`` con ``discover_assets`` + ``discover_identities``
+ ``run_full_discovery`` + 5 implementaciones concretas (Microsoft365 · Google
Workspace · Azure · AWS · GitHub).

Esta capa adapta el resultado M16 DiscoveryResult a CloudResource records
persistidos en nuestras tablas. Es PURE FUNCTION (sin OAuth flow nuevo · sin
HTTP calls nuevos · sin abstract methods nuevos).

ADR-014 sostener · read-only OAuth siempre. ADR-025 sostener · NO duplicar.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from backend.app.motors.m16_onboarding.connectors.base import (
    BaseConnector,
    DiscoveredAssetDTO,
    DiscoveredIdentityDTO,
    DiscoveryResult,
)
from backend.app.motors.m16_onboarding.connectors.registry import (
    get_connector_class,
)


def m16_provider_id(provider: str) -> str:
    """Map CloudConnectorProvider value → M16 ConnectorProvider value.

    Ambos enums comparten valores (decisión deliberada · OPS-045 sostener).
    """
    return provider


def get_m16_connector_class(provider: str):
    """Lookup M16 connector class by provider string · None si MANUAL_IMPORT."""
    from backend.app.motors.m16_onboarding.connectors.base import (
        ConnectorProvider,
    )

    try:
        return get_connector_class(ConnectorProvider(provider))
    except ValueError:
        return None


def normalize_asset_to_resource_dict(
    asset: DiscoveredAssetDTO,
) -> dict[str, Any]:
    """DiscoveredAssetDTO → dict listo para insertar como CloudResource."""
    attrs = {
        "asset_type": asset.asset_type,
        "tags": asset.tags,
        "criticality": asset.criticality,
        **asset.raw_data,
    }
    return {
        "resource_type": f"asset.{asset.asset_type}",
        "resource_external_id": asset.external_id,
        "resource_name": asset.name,
        "attributes": attrs,
        "checksum": _checksum_attrs(attrs),
        "detected_at": asset.discovered_at,
    }


def normalize_identity_to_resource_dict(
    identity: DiscoveredIdentityDTO,
) -> dict[str, Any]:
    """DiscoveredIdentityDTO → dict CloudResource."""
    attrs = {
        "identity_type": identity.identity_type,
        "email": identity.email,
        "mfa_enabled": identity.mfa_enabled,
        "is_privileged": identity.is_privileged,
        "is_active": identity.is_active,
        **identity.raw_data,
    }
    return {
        "resource_type": f"identity.{identity.identity_type}",
        "resource_external_id": identity.external_id,
        "resource_name": identity.display_name,
        "attributes": attrs,
        "checksum": _checksum_attrs(attrs),
        "detected_at": identity.discovered_at,
    }


def discovery_result_to_resource_dicts(
    result: DiscoveryResult,
) -> list[dict[str, Any]]:
    """Aplana DiscoveryResult M16 a lista CloudResource dicts."""
    rows: list[dict[str, Any]] = []
    for asset in result.assets:
        rows.append(normalize_asset_to_resource_dict(asset))
    for identity in result.identities:
        rows.append(normalize_identity_to_resource_dict(identity))
    return rows


def _checksum_attrs(attrs: dict[str, Any]) -> str:
    """SHA-256 estable de attributes para detectar cambios MoM (retainer L)."""
    canonical = json.dumps(attrs, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


__all__ = [
    "BaseConnector",  # re-export M16 abstract for callers
    "DiscoveredAssetDTO",
    "DiscoveredIdentityDTO",
    "DiscoveryResult",
    "discovery_result_to_resource_dicts",
    "get_m16_connector_class",
    "m16_provider_id",
    "normalize_asset_to_resource_dict",
    "normalize_identity_to_resource_dict",
    "now_utc",
]
