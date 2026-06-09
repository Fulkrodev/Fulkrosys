"""Severidad efectiva (CVSS+EPSS) + dedup cross-motor determinista.

doc §8: el SLA combina CVSS (severidad técnica) y EPSS (probabilidad real
de explotación). `effective_severity` deriva la severidad para SLA, pero
**NUNCA baja del suelo determinista** que reportó el motor (regla dura §4):
el enriquecimiento solo puede subir la prioridad, jamás rebajarla.

dedup cross-motor (doc §3): `compute_dedup_group_id` deriva un UUID estable
(uuid5) del finding_hash, de modo que el MISMO hallazgo detectado por
distintos motores o en distintos runs comparte dedup_group_id — habilita
correlación y tendencia sin depender del LLM.
"""
from __future__ import annotations

import uuid
from typing import Any

# Namespace fijo (determinista) para dedup cross-motor/run.
DEDUP_NAMESPACE = uuid.UUID("f0a1b2c3-d4e5-4f60-8a90-fd8e7c6b5a40")

_SEVERITY_RANK = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
_RANK_SEVERITY = {v: k for k, v in _SEVERITY_RANK.items()}


def severity_rank(severity: str | None) -> int:
    return _SEVERITY_RANK.get((severity or "info").lower(), 0)


def compute_dedup_group_id(finding_hash: str) -> uuid.UUID:
    """UUID5 estable derivado del finding_hash · determinista cross-run."""
    return uuid.uuid5(DEDUP_NAMESPACE, finding_hash or "")


def assign_dedup_groups(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Asigna dedup_group_id a cada finding desde su finding_hash (in-place).

    Requiere que el finding ya tenga `finding_hash` (lo pone gate1/ZFP).
    """
    for f in findings:
        fh = f.get("finding_hash")
        if fh:
            f["dedup_group_id"] = str(compute_dedup_group_id(fh))
    return findings


def effective_severity(
    *,
    base_severity: str | None,
    cvss_score: float | None = None,
    epss_score: float | None = None,
) -> str:
    """Severidad efectiva para SLA combinando CVSS + EPSS (doc §8).

    Regla dura §4: el resultado es ``max(base_severity, computed)`` — el
    enriquecimiento NUNCA rebaja la severidad determinista del motor.

    Matriz (computed):
      - critical: CVSS>=9 · OR EPSS>=0.7 · OR (CVSS>=7 AND EPSS>=0.5)
      - high:     CVSS>=7 · OR EPSS>=0.3 · OR (CVSS>=4 AND EPSS>=0.3)
      - medium:   CVSS>=4 · OR EPSS>=0.1
      - low:      CVSS>0  · OR EPSS>0
      - info:     resto
    """
    cvss = cvss_score if isinstance(cvss_score, (int, float)) else None
    epss = epss_score if isinstance(epss_score, (int, float)) else None

    computed = "info"
    if (cvss is not None and cvss >= 9.0) \
            or (epss is not None and epss >= 0.7) \
            or (cvss is not None and cvss >= 7.0 and epss is not None and epss >= 0.5):
        computed = "critical"
    elif (cvss is not None and cvss >= 7.0) \
            or (epss is not None and epss >= 0.3) \
            or (cvss is not None and cvss >= 4.0 and epss is not None and epss >= 0.3):
        computed = "high"
    elif (cvss is not None and cvss >= 4.0) or (epss is not None and epss >= 0.1):
        computed = "medium"
    elif (cvss is not None and cvss > 0) or (epss is not None and epss > 0):
        computed = "low"

    floor = severity_rank(base_severity)
    return _RANK_SEVERITY[max(severity_rank(computed), floor)]
