"""CloudConnectorService · CRUD + sync orchestration (sub-atom 1.D.X.B v3.12).

Responsabilidades:
  - link_or_create_connector (idempotent · UPSERT on UNIQUE(project_id, provider))
  - list/get/revoke connector
  - list resources + sync jobs
  - trigger_sync (crea CloudSyncJob · invoca adapter M16 via registry · persiste resources)
  - resolve_gap (admin marca gap resolved con evidence link opcional)

Design:
  - Idempotencia: connect → re-connect → revoke → re-connect mismo provider OK
  - sync_job lifecycle: pending → running → completed/failed (atomic transitions)
  - mock_mode: cuando MANUAL_IMPORT o M16 ConnectorConfig=None → completed inmediato 0 resources
  - Resources UPSERT por (connector_id, resource_external_id, resource_type)
  - checksum SHA-256 attributes para detectar cambios MoM (L retainer)

R1 sostener · sin LLM en service (LLM solo en gap engine para explanation_es).
R23 sostener · NO cross-project queries (project_id explicit en filter).
ADR-014 sostener · read-only siempre (no write methods al provider).
ADR-025 sostener · NO duplicar tablas ni OAuth state (reuse M16).
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Optional, Sequence

from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.models.onboarding import ConnectorConfig
from backend.app.motors.m_cloud_connectors.base_connector import (
    DiscoveryResult,
    discovery_result_to_resource_dicts,
    get_m16_connector_class,
    now_utc,
)
from backend.app.motors.m_cloud_connectors.models import (
    CloudConnector,
    CloudConnectorProvider,
    CloudConnectorStatus,
    CloudGap,
    CloudResource,
    CloudSyncJob,
    CloudSyncJobStatus,
)


logger = logging.getLogger(__name__)


# ==================================================================
# Exceptions
# ==================================================================


class CloudConnectorError(Exception):
    """Error genérico del service."""


class CloudConnectorNotFoundError(CloudConnectorError):
    """Conector no encontrado para el project_id."""


class CloudConnectorRevokedError(CloudConnectorError):
    """Conector ya revocado · no se puede operar."""


class MockModeNotAllowedError(CloudConnectorError):
    """trigger_sync sin m16_credentials requiere CLOUD_MOCK_MODE_ALLOWED env.

    Production-safety guard (1.D.X.VERIFY): cuando m16_credentials=None y el
    provider NO es MANUAL_IMPORT, el sync recurriría a mock mode (0 resources
    detected → diagnostic gap engine auto-resolve gaps reales con dataset
    vacío). En producción esto borra trazabilidad ENAC silenciosamente.

    MANUAL_IMPORT está exento del guard · es uso legítimo del provider (sin
    credenciales) · diseñado para fallback Excel/CSV upload via m24_idms.

    Override en dev/test/piloto demo: CLOUD_MOCK_MODE_ALLOWED=true.
    """


class CloudGapNotFoundError(CloudConnectorError):
    """Gap no encontrado en el project."""


class CloudSyncFailedError(CloudConnectorError):
    """Sync job lanzado pero el adapter M16 fall + persistencia."""


# ==================================================================
# Catalog providers (cliente UI consume este catalog)
# ==================================================================


_PROVIDER_CATALOG: dict[str, dict[str, Any]] = {
    "microsoft_365": {
        "display_name": "Microsoft 365 / Entra ID",
        "icon_emoji": "🔵",
        "requires_oauth": True,
        "cliente_friendly_blurb": (
            "Cuentas, grupos y MFA · solo lectura · 5 minutos. "
            "Detectamos usuarios sin MFA y privilegios excesivos."
        ),
    },
    "google_workspace": {
        "display_name": "Google Workspace",
        "icon_emoji": "🟢",
        "requires_oauth": True,
        "cliente_friendly_blurb": (
            "Usuarios, grupos y dispositivos · solo lectura · "
            "verificamos MFA y políticas Workspace."
        ),
    },
    "azure": {
        "display_name": "Azure",
        "icon_emoji": "🟦",
        "requires_oauth": True,
        "cliente_friendly_blurb": (
            "Recursos cloud Azure · subscripciones y resource groups · solo "
            "lectura · detectamos configuraciones inseguras."
        ),
    },
    "aws": {
        "display_name": "AWS",
        "icon_emoji": "🟧",
        "requires_oauth": False,
        "cliente_friendly_blurb": (
            "IAM, buckets y EC2 · pegar Access Key con permisos solo "
            "lectura · detectamos buckets públicos y IAM sin MFA."
        ),
    },
    "github": {
        "display_name": "GitHub",
        "icon_emoji": "⚫",
        "requires_oauth": True,
        "cliente_friendly_blurb": (
            "Si desarrollas software · repos, miembros y secrets · solo "
            "lectura · detectamos secrets expuestos."
        ),
    },
    "manual_import": {
        "display_name": "Subir inventario manual",
        "icon_emoji": "📊",
        "requires_oauth": False,
        "cliente_friendly_blurb": (
            "Sube un Excel con tus sistemas · te ayudamos a construir el "
            "inventario · funciona perfecto como fallback."
        ),
    },
}


def list_provider_catalog() -> list[dict[str, Any]]:
    """Catalog providers para UI cliente onboarding."""
    return [
        {"provider": k, **v}
        for k, v in _PROVIDER_CATALOG.items()
    ]


# ==================================================================
# CloudConnectorService
# ==================================================================


class CloudConnectorService:
    """Service orquestador conexiones cloud project-scoped."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ----------------------------------------------------------
    # Connector CRUD
    # ----------------------------------------------------------

    async def link_or_create_connector(
        self,
        *,
        project_id: uuid.UUID,
        provider: CloudConnectorProvider | str,
        m16_connector_config_id: Optional[uuid.UUID] = None,
        scopes: Optional[str] = None,
        created_by_user_id: Optional[uuid.UUID] = None,
    ) -> CloudConnector:
        """UPSERT idempotente · 1 conector activo per (project, provider).

        - Si NO existe → CREA en status CONNECTED (si M16 link presente) o
          PENDING_OAUTH (si M16 link ausente y provider requires OAuth).
        - Si existe revocado → reactivate + actualiza link/scopes.
        - Si existe activo → actualiza link/scopes (re-conectar OK).
        """
        provider_value = (
            provider.value if isinstance(provider, CloudConnectorProvider) else provider
        )

        # Lookup existente
        existing_q = await self.db.execute(
            select(CloudConnector).where(
                and_(
                    CloudConnector.project_id == project_id,
                    CloudConnector.provider == provider_value,
                ),
            )
        )
        existing = existing_q.scalar_one_or_none()

        target_status = (
            CloudConnectorStatus.CONNECTED.value
            if m16_connector_config_id is not None
            or provider_value == CloudConnectorProvider.MANUAL_IMPORT.value
            else CloudConnectorStatus.PENDING_OAUTH.value
        )

        if existing is not None:
            existing.m16_connector_config_id = m16_connector_config_id
            existing.scopes = scopes if scopes is not None else existing.scopes
            existing.status = target_status
            existing.revoked_at = None
            await self.db.flush()
            await self.db.refresh(existing)
            return existing

        connector = CloudConnector(
            project_id=project_id,
            provider=provider_value,
            m16_connector_config_id=m16_connector_config_id,
            scopes=scopes,
            status=target_status,
            created_by_user_id=created_by_user_id,
        )
        self.db.add(connector)
        try:
            await self.db.flush()
        except IntegrityError as exc:
            # Race condition (insert concurrente) → reintento idempotente
            await self.db.rollback()
            raise CloudConnectorError(
                f"Conflict creating connector {provider_value} · retry"
            ) from exc
        await self.db.refresh(connector)
        return connector

    async def list_connectors(
        self,
        *,
        project_id: uuid.UUID,
        include_revoked: bool = False,
    ) -> list[CloudConnector]:
        stmt = select(CloudConnector).where(
            CloudConnector.project_id == project_id,
        )
        if not include_revoked:
            stmt = stmt.where(CloudConnector.revoked_at.is_(None))
        stmt = stmt.order_by(CloudConnector.created_at.desc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_connector(
        self,
        *,
        project_id: uuid.UUID,
        connector_id: uuid.UUID,
    ) -> CloudConnector:
        res = await self.db.execute(
            select(CloudConnector).where(
                and_(
                    CloudConnector.id == connector_id,
                    CloudConnector.project_id == project_id,
                ),
            )
        )
        connector = res.scalar_one_or_none()
        if connector is None:
            raise CloudConnectorNotFoundError(
                f"Connector {connector_id} no encontrado en project {project_id}",
            )
        return connector

    async def revoke_connector(
        self,
        *,
        project_id: uuid.UUID,
        connector_id: uuid.UUID,
    ) -> CloudConnector:
        connector = await self.get_connector(
            project_id=project_id, connector_id=connector_id,
        )
        connector.status = CloudConnectorStatus.REVOKED.value
        connector.revoked_at = now_utc()
        await self.db.flush()
        await self.db.refresh(connector)
        return connector

    # ----------------------------------------------------------
    # Sync orchestration
    # ----------------------------------------------------------

    async def _resolve_m16_credentials(
        self, config_id: uuid.UUID,
    ) -> Optional[dict[str, Any]]:
        """#18 · Resuelve+descifra las credenciales OAuth de la M16
        ConnectorConfig enlazada (FK ``m16_connector_config_id``) para
        ejecutar discovery real.

        Read-only (ADR-014): solo se descifra el token ya existente · NUNCA
        se escribe al provider. Degradación elegante (OPS-049): si la config
        no existe o el token no se puede descifrar → devuelve None y el sync
        cae al guard mock_mode en vez de romper.
        """
        from backend.app.motors.m16_onboarding.token_encryption import (
            decrypt_credentials,
        )

        config = await self.db.get(ConnectorConfig, config_id)
        if config is None or not config.encrypted_credentials:
            return None
        try:
            return decrypt_credentials(config.encrypted_credentials)
        except ValueError:
            logger.warning(
                "#18 trigger_sync: credenciales M16 config=%s no "
                "descifrables · cae a mock_mode/guard", config_id,
            )
            return None

    async def trigger_sync(
        self,
        *,
        project_id: uuid.UUID,
        connector_id: uuid.UUID,
        triggered_by: str = "manual",
        m16_credentials: Optional[dict[str, Any]] = None,
    ) -> CloudSyncJob:
        """Crea CloudSyncJob + ejecuta sync inline (sync execution).

        Para producción / retainer L · trigger será async via Celery beat.
        En sub-fase B execution inline → simplifica tests + onboarding.

        Si ``m16_credentials`` provisto → ejecuta adapter M16 real.
        Si NO → mock_mode (completa con 0 resources · OK para piloto onboarding).
        """
        connector = await self.get_connector(
            project_id=project_id, connector_id=connector_id,
        )
        if connector.revoked_at is not None:
            raise CloudConnectorRevokedError(
                f"Connector {connector_id} revoked · no se puede sincronizar",
            )

        # Production-safety guard (1.D.X.VERIFY): mock_mode (m16_credentials=None
        # con OAuth provider) requiere CLOUD_MOCK_MODE_ALLOWED=true en env.
        # MANUAL_IMPORT está exento (uso legítimo sin credenciales · m24_idms
        # upload fallback). Si guard violado · NO crear CloudSyncJob (raise
        # antes de touch DB).
        is_manual_import = (
            connector.provider == CloudConnectorProvider.MANUAL_IMPORT.value
        )

        # #18 · Si no se pasaron credenciales explícitas pero el connector
        # está enlazado a una M16 ConnectorConfig (OAuth real del cliente),
        # resolverlas y descifrarlas aquí → discovery real en vez de mock.
        if (
            m16_credentials is None
            and not is_manual_import
            and connector.m16_connector_config_id is not None
        ):
            m16_credentials = await self._resolve_m16_credentials(
                connector.m16_connector_config_id,
            )

        if m16_credentials is None and not is_manual_import:
            if not get_settings().cloud_mock_mode_allowed:
                raise MockModeNotAllowedError(
                    f"trigger_sync para provider {connector.provider!r} sin "
                    "m16_credentials requiere CLOUD_MOCK_MODE_ALLOWED=true · "
                    "NEVER enable in production · auto-resolve gaps con "
                    "dataset vacío puede borrar trazabilidad ENAC.",
                )

        job = CloudSyncJob(
            project_id=project_id,
            connector_id=connector_id,
            status=CloudSyncJobStatus.RUNNING.value,
            triggered_by=triggered_by,
        )
        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)

        try:
            connector.status = CloudConnectorStatus.SYNCING.value
            await self.db.flush()

            # Mock mode: MANUAL_IMPORT o cualquier provider sin credenciales
            if m16_credentials is None:
                resources_persisted = 0
            else:
                cls = get_m16_connector_class(connector.provider)
                if cls is None:
                    raise CloudSyncFailedError(
                        f"M16 connector class no registrada para "
                        f"{connector.provider}",
                    )
                adapter = cls(m16_credentials)
                discovery: DiscoveryResult = await adapter.run_full_discovery()
                resource_dicts = discovery_result_to_resource_dicts(discovery)
                resources_persisted = await self._upsert_resources(
                    project_id=project_id,
                    connector_id=connector_id,
                    resource_dicts=resource_dicts,
                )

            # Update job + connector
            job.status = CloudSyncJobStatus.COMPLETED.value
            job.completed_at = now_utc()
            job.resources_count = resources_persisted
            connector.status = CloudConnectorStatus.CONNECTED.value
            connector.last_sync_at = now_utc()
            connector.last_sync_resources_count = resources_persisted
            await self.db.flush()
            await self.db.refresh(job)
            return job
        except Exception as exc:
            logger.exception(
                "sync failed · project=%s connector=%s err=%s",
                project_id, connector_id, exc,
            )
            job.status = CloudSyncJobStatus.FAILED.value
            job.completed_at = now_utc()
            job.errors_jsonb = {"error": str(exc)}
            connector.status = CloudConnectorStatus.SYNC_ERROR.value
            await self.db.flush()
            raise

    async def _upsert_resources(
        self,
        *,
        project_id: uuid.UUID,
        connector_id: uuid.UUID,
        resource_dicts: Sequence[dict[str, Any]],
    ) -> int:
        """UPSERT resources via INSERT ... ON CONFLICT.

        Idempotente: re-sync misma external_id + resource_type actualiza
        attributes + checksum + last_seen_at. Insert nuevos. NO borra
        ausentes (delta detection L retainer feature).
        """
        if not resource_dicts:
            return 0

        rows = []
        for r in resource_dicts:
            rows.append({
                "project_id": project_id,
                "connector_id": connector_id,
                "resource_type": r["resource_type"],
                "resource_external_id": r["resource_external_id"],
                "resource_name": r.get("resource_name"),
                "attributes": r.get("attributes", {}),
                "checksum": r.get("checksum"),
                "detected_at": r.get("detected_at") or now_utc(),
                "last_seen_at": now_utc(),
            })

        stmt = pg_insert(CloudResource).values(rows)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_cloud_resources_external_id",
            set_={
                "resource_name": stmt.excluded.resource_name,
                "attributes": stmt.excluded.attributes,
                "checksum": stmt.excluded.checksum,
                "last_seen_at": stmt.excluded.last_seen_at,
                "updated_at": now_utc(),
            },
        )
        await self.db.execute(stmt)
        return len(rows)

    # ----------------------------------------------------------
    # Resources / Jobs queries
    # ----------------------------------------------------------

    async def list_resources(
        self,
        *,
        project_id: uuid.UUID,
        connector_id: uuid.UUID,
        resource_type: Optional[str] = None,
        limit: int = 200,
    ) -> tuple[list[CloudResource], int]:
        # Verify connector ownership
        await self.get_connector(
            project_id=project_id, connector_id=connector_id,
        )
        base_q = select(CloudResource).where(
            and_(
                CloudResource.project_id == project_id,
                CloudResource.connector_id == connector_id,
            ),
        )
        count_q = select(func.count()).select_from(base_q.subquery())
        if resource_type:
            base_q = base_q.where(CloudResource.resource_type == resource_type)
            count_q = select(func.count()).select_from(base_q.subquery())

        base_q = base_q.order_by(CloudResource.detected_at.desc()).limit(limit)
        res = await self.db.execute(base_q)
        total = (await self.db.execute(count_q)).scalar() or 0
        return list(res.scalars().all()), total

    async def list_sync_jobs(
        self,
        *,
        project_id: uuid.UUID,
        connector_id: uuid.UUID,
        limit: int = 50,
    ) -> list[CloudSyncJob]:
        await self.get_connector(
            project_id=project_id, connector_id=connector_id,
        )
        stmt = (
            select(CloudSyncJob)
            .where(
                and_(
                    CloudSyncJob.project_id == project_id,
                    CloudSyncJob.connector_id == connector_id,
                ),
            )
            .order_by(CloudSyncJob.started_at.desc())
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    # ----------------------------------------------------------
    # Gaps queries / resolution
    # ----------------------------------------------------------

    async def list_gaps(
        self,
        *,
        project_id: uuid.UUID,
        severities: Optional[list[str]] = None,
        include_resolved: bool = False,
        cliente_visible_only: bool = False,
        limit: int = 200,
    ) -> tuple[list[CloudGap], int]:
        stmt = select(CloudGap).where(CloudGap.project_id == project_id)
        if not include_resolved:
            stmt = stmt.where(CloudGap.resolved_at.is_(None))
        if severities:
            stmt = stmt.where(CloudGap.severity.in_(severities))
        if cliente_visible_only:
            stmt = stmt.where(CloudGap.cliente_can_see.is_(True))
        count_q = select(func.count()).select_from(stmt.subquery())
        stmt = stmt.order_by(CloudGap.detected_at.desc()).limit(limit)
        res = await self.db.execute(stmt)
        total = (await self.db.execute(count_q)).scalar() or 0
        return list(res.scalars().all()), total

    async def resolve_gap(
        self,
        *,
        project_id: uuid.UUID,
        gap_id: uuid.UUID,
        resolution_note: Optional[str] = None,
        evidence_link_id: Optional[uuid.UUID] = None,
        resolved_by_user_id: Optional[uuid.UUID] = None,
    ) -> CloudGap:
        res = await self.db.execute(
            select(CloudGap).where(
                and_(
                    CloudGap.id == gap_id,
                    CloudGap.project_id == project_id,
                ),
            )
        )
        gap = res.scalar_one_or_none()
        if gap is None:
            raise CloudGapNotFoundError(
                f"Gap {gap_id} no encontrado en project {project_id}",
            )
        gap.resolved_at = now_utc()
        gap.resolution_note = resolution_note
        gap.evidence_link_id = evidence_link_id
        gap.resolved_by_user_id = resolved_by_user_id
        await self.db.flush()
        await self.db.refresh(gap)
        return gap
