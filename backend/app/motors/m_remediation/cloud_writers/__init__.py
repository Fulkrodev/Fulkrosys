"""Writers cloud reales por proveedor · m_remediation (ADR-055).

Cada writer implementa la interfaz `RemediationWriter` (read_state/apply/rollback)
contra la API REAL del proveedor (boto3 AWS · Graph M365/Azure · Google API). Se
construyen POR CONECTOR (cada conector trae sus credenciales descifradas de M16).

`build_writer_for_connector` es la fábrica que el motor usa en `execute_job`:
resuelve el proveedor + descifra las credenciales (read-only de M16 · OPS-026 DRY) +
instancia el writer. Devuelve None si no hay credenciales o el proveedor no soporta
remediación → el motor marca el job FAILED explícito (default seguro · jamás finge).
"""
from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from backend.app.motors.m_remediation.writers import RemediationWriter

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from backend.app.motors.m_cloud_connectors.models import CloudConnector

logger = logging.getLogger(__name__)


async def _resolve_credentials(
    db: "AsyncSession", connector: "CloudConnector",
) -> dict | None:
    """Descifra las credenciales M16 del conector (misma vía que el discovery)."""
    if connector.m16_connector_config_id is None:
        return None
    from backend.app.models.onboarding import ConnectorConfig
    from backend.app.motors.m16_onboarding.token_encryption import (
        decrypt_credentials,
    )

    config = await db.get(ConnectorConfig, connector.m16_connector_config_id)
    if config is None or not config.encrypted_credentials:
        return None
    try:
        return decrypt_credentials(config.encrypted_credentials)
    except ValueError:
        logger.warning(
            "remediation writer: credenciales conector=%s no descifrables",
            connector.id,
        )
        return None


def build_writer_from_credentials(
    provider: str, credentials: dict,
) -> RemediationWriter | None:
    """Instancia el writer del proveedor a partir de credenciales ya descifradas.

    Útil para tests (inyectar credenciales directas) y para la fábrica.
    """
    if provider == "aws":
        from backend.app.motors.m_remediation.cloud_writers.aws import (
            AwsRemediationWriter,
        )

        return AwsRemediationWriter(credentials)
    if provider == "microsoft_365":
        from backend.app.motors.m_remediation.cloud_writers.microsoft365 import (
            Microsoft365RemediationWriter,
        )

        return Microsoft365RemediationWriter(credentials)
    if provider == "azure":
        from backend.app.motors.m_remediation.cloud_writers.azure import (
            AzureRemediationWriter,
        )

        return AzureRemediationWriter(credentials)
    if provider == "google_workspace":
        from backend.app.motors.m_remediation.cloud_writers.google_workspace import (
            GoogleWorkspaceRemediationWriter,
        )

        return GoogleWorkspaceRemediationWriter(credentials)
    return None


async def build_writer_for_connector(
    db: "AsyncSession", connector: "CloudConnector",
) -> RemediationWriter | None:
    """Fábrica usada por el motor · None si no hay credenciales/soporte."""
    credentials = await _resolve_credentials(db, connector)
    if credentials is None:
        return None
    return build_writer_from_credentials(connector.provider, credentials)
