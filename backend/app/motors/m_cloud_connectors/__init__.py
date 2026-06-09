"""m_cloud_connectors · unified cloud connections layer (sub-atom 1.D.X v3.12).

Capa unificada SOBRE M16 OAuth flows existing (NO duplicar ADR-025).

Modelo:
  - CloudConnector · link M16 ConnectorConfig + project-scoped metadata cloud-first
  - CloudResource · recursos detectados (users · VMs · storage · IAM · etc)
  - CloudGap · diagnóstico deterministic gap engine resultado
  - CloudSyncJob · tracking jobs sync (idempotente · retry · status)

OPS-045 29ª aplicación sostenida: audit-first 1.D.X.A revela M16 OAuth + M22
Discovery + M27 catalogs ~85-90% existing · POLISH layer unified solo lo nuevo.

Architecture: read-only OAuth siempre (ADR-014) · encryption at-rest reuse
M16 token_encryption Fernet · RLS project-scoped (LECCION-OPS-008).
"""
from backend.app.motors.m_cloud_connectors.models import (
    CloudConnector,
    CloudDigestSnapshot,
    CloudGap,
    CloudResource,
    CloudSyncJob,
    CloudConnectorProvider,
    CloudConnectorStatus,
    CloudGapSeverity,
    CloudGapType,
    CloudSyncJobStatus,
)
from backend.app.motors.m_cloud_connectors.digest_service import (
    DigestError,
    DigestProjectNotFoundError,
    build_client_digest_view,
    generate_monthly_digest_for_project,
    get_latest_digest_for_project,
    get_previous_digest_for_project,
)
from backend.app.motors.m_cloud_connectors.service import (
    CloudConnectorError,
    CloudConnectorNotFoundError,
    CloudConnectorRevokedError,
    CloudConnectorService,
    CloudGapNotFoundError,
    CloudSyncFailedError,
    MockModeNotAllowedError,
    list_provider_catalog,
)
from backend.app.motors.m_cloud_connectors.diagnostic_gap_engine import (
    DiagnosisReport,
    DiagnosticGapEngine,
)
from backend.app.motors.m_cloud_connectors.gap_rules import (
    GapFinding,
    GapRule,
    RULE_CATALOG,
    list_supported_measures,
    rules_for_category,
)

__all__ = [
    "CloudConnector",
    "CloudDigestSnapshot",
    "CloudConnectorError",
    "CloudConnectorNotFoundError",
    "CloudConnectorProvider",
    "CloudConnectorRevokedError",
    "CloudConnectorService",
    "CloudConnectorStatus",
    "CloudGap",
    "CloudGapNotFoundError",
    "CloudGapSeverity",
    "CloudGapType",
    "CloudResource",
    "CloudSyncFailedError",
    "CloudSyncJob",
    "CloudSyncJobStatus",
    "MockModeNotAllowedError",
    "DiagnosisReport",
    "DiagnosticGapEngine",
    "DigestError",
    "DigestProjectNotFoundError",
    "GapFinding",
    "GapRule",
    "RULE_CATALOG",
    "build_client_digest_view",
    "generate_monthly_digest_for_project",
    "get_latest_digest_for_project",
    "get_previous_digest_for_project",
    "list_provider_catalog",
    "list_supported_measures",
    "rules_for_category",
]
