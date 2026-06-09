"""M8 Autopilot · determinismo demostrable (doc §11) + grafo de activos (§3).

run_manifest_hash + golden runs hacen el determinismo *demostrable* ante
auditoría: misma entrada (scope+tools+templates+config+modelo+snapshot) →
mismo hash → mismos hallazgos esperables. El asset graph (PKG-lite) modela
la superficie para blast-radius/MTTR.
"""
from backend.app.motors.m08_verification.determinism.manifest import (
    RunManifest,
    compute_run_manifest_hash,
    build_run_manifest,
    compare_to_golden,
)

__all__ = [
    "RunManifest",
    "compute_run_manifest_hash",
    "build_run_manifest",
    "compare_to_golden",
]
