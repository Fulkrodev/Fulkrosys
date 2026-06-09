"""M8 Autopilot · enriquecimiento de hallazgos (doc §3 Capa 3 + §8).

CVSS (severidad técnica) + EPSS (probabilidad real de explotación) +
dedup cross-motor determinista + severidad efectiva para SLA.
"""
from backend.app.motors.m08_verification.enrichment.epss import (
    EpssClient,
    get_epss_client,
    enrich_findings_with_epss,
)
from backend.app.motors.m08_verification.enrichment.scoring import (
    DEDUP_NAMESPACE,
    compute_dedup_group_id,
    effective_severity,
    severity_rank,
    assign_dedup_groups,
)

__all__ = [
    "EpssClient",
    "get_epss_client",
    "enrich_findings_with_epss",
    "DEDUP_NAMESPACE",
    "compute_dedup_group_id",
    "effective_severity",
    "severity_rank",
    "assign_dedup_groups",
]
