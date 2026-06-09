"""M8 Autopilot · observabilidad (doc §12) + evidencia ENAC (§16).

Métricas: cobertura% (honestidad), FP-rate post-gate4, MTTR por severidad,
tendencia, drift de determinismo, salud del pipeline. Pack de evidencia que
sintetiza proceso + evidencia + cierre para la auditoría ENAC.
"""
from backend.app.motors.m08_verification.observability.metrics import (
    compute_observability_metrics,
)
from backend.app.motors.m08_verification.observability.evidence_pack import (
    build_enac_evidence_pack,
)

__all__ = ["compute_observability_metrics", "build_enac_evidence_pack"]
