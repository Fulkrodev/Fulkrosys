"""Discovery service for M16 connectors.

Coordinates: configure connector, validate, run discovery, persist results.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.onboarding import ConnectorConfig

from .connectors.base import ConnectorProvider, DiscoveryResult
from .connectors.registry import create_connector
from .token_encryption import encrypt_credentials, decrypt_credentials


class DiscoveryServiceError(ValueError):
    pass


async def configure_connector(
    session: AsyncSession,
    project_id: uuid.UUID,
    provider: ConnectorProvider,
    credentials: dict,
    scopes: Optional[str] = None,
) -> dict:
    """Configure (or reconfigure) a connector for a project."""
    encrypted = encrypt_credentials(credentials)

    r = await session.execute(
        select(ConnectorConfig).where(
            ConnectorConfig.project_id == project_id,
            ConnectorConfig.provider == provider.value,
        )
    )
    existing = r.scalar_one_or_none()

    if existing:
        existing.encrypted_credentials = encrypted
        existing.scopes = scopes
        existing.status = "configured"
        existing.updated_at = datetime.now(timezone.utc)
        config_id = existing.id
    else:
        config = ConnectorConfig(
            id=uuid.uuid4(),
            project_id=project_id,
            provider=provider.value,
            encrypted_credentials=encrypted,
            scopes=scopes,
            status="configured",
        )
        session.add(config)
        config_id = config.id

    await session.flush()

    return {
        "config_id": config_id,
        "project_id": project_id,
        "provider": provider.value,
        "status": "configured",
    }


async def validate_connector(
    session: AsyncSession,
    project_id: uuid.UUID,
    provider: ConnectorProvider,
) -> dict:
    """Validate credentials without full discovery."""
    config = await _load_config(session, project_id, provider)
    credentials = decrypt_credentials(config.encrypted_credentials)
    connector = create_connector(provider, credentials)

    valid = await connector.validate_credentials()

    config.status = "validated" if valid else "invalid"
    await session.flush()

    return {
        "provider": provider.value,
        "valid": valid,
        "status": config.status,
    }


async def run_discovery(
    session: AsyncSession,
    project_id: uuid.UUID,
    provider: ConnectorProvider,
) -> dict:
    """Run full discovery and persist summary."""
    config = await _load_config(session, project_id, provider)
    credentials = decrypt_credentials(config.encrypted_credentials)
    connector = create_connector(provider, credentials)

    result: DiscoveryResult = await connector.run_full_discovery()

    # Persist individual assets/identities as PKG nodes
    await _persist_discovery_results(session, project_id, provider, result)

    config.last_discovery_at = datetime.now(timezone.utc)
    config.status = "discovered" if result.success else "discovery_partial"
    config.discovery_result_summary = result.summary
    await session.flush()

    return {
        "provider": provider.value,
        "success": result.success,
        "total_assets": result.summary.get("total_assets", 0),
        "total_identities": result.summary.get("total_identities", 0),
        "errors": result.errors,
        "duration_seconds": result.duration_seconds,
    }


async def list_connectors(
    session: AsyncSession,
    project_id: uuid.UUID,
) -> list[dict]:
    r = await session.execute(
        select(ConnectorConfig).where(ConnectorConfig.project_id == project_id)
    )
    return [
        {
            "config_id": c.id,
            "provider": c.provider,
            "status": c.status,
            "last_discovery_at": c.last_discovery_at,
            "discovery_result_summary": c.discovery_result_summary,
        }
        for c in r.scalars().all()
    ]


async def _load_config(
    session: AsyncSession,
    project_id: uuid.UUID,
    provider: ConnectorProvider,
) -> ConnectorConfig:
    r = await session.execute(
        select(ConnectorConfig).where(
            ConnectorConfig.project_id == project_id,
            ConnectorConfig.provider == provider.value,
        )
    )
    config = r.scalar_one_or_none()
    if config is None:
        raise DiscoveryServiceError(
            f"No hay connector {provider.value} configurado para proyecto {project_id}. "
            "Usa POST /connectors/configure primero."
        )
    return config


async def _persist_discovery_results(
    session: AsyncSession,
    project_id: uuid.UUID,
    provider: ConnectorProvider,
    result: DiscoveryResult,
) -> None:
    """Persist each discovered asset/identity as individual PKG node."""
    from . import pkg_service as pkg

    nodes = []
    for asset in result.assets:
        nodes.append({
            "node_type": "asset",
            "label": asset.name,
            "external_id": f"discovery:{provider.value}:{asset.external_id}",
            "properties": {
                "asset_type": asset.asset_type,
                "provider": asset.provider,
                "criticality": asset.criticality,
                "tags": asset.tags,
                "source": "discovery",
            },
        })
    for identity in result.identities:
        nodes.append({
            "node_type": "identity",
            "label": identity.display_name,
            "external_id": f"discovery:{provider.value}:{identity.external_id}",
            "properties": {
                "identity_type": identity.identity_type,
                "provider": identity.provider,
                "mfa_enabled": identity.mfa_enabled,
                "is_privileged": identity.is_privileged,
                "is_active": identity.is_active,
                "source": "discovery",
            },
        })
    if nodes:
        await pkg.bulk_upsert_nodes(session, project_id, nodes)
