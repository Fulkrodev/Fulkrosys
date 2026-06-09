"""
Custom ruff rule preventing new files with paso{N}_* prefix in motor packages.
Existing files (paso2_extensions, paso6_*, etc.) are allowed (legacy).
New files with this pattern fail lint.

Why: arqueología paso{N}_* es deuda cognitiva. README explica histórico.
Nuevos ficheros deben usar nombres descriptivos sin prefijo numérico.
"""
import re
from pathlib import Path
import sys

LEGACY_ALLOWED = {
    "backend/app/motors/m22_discovery/paso6_aws_connector.py",
    "backend/app/motors/m22_discovery/paso6_demo_mocks.py",
    "backend/app/motors/m22_discovery/paso6_m365_connector.py",
    "backend/app/motors/m22_discovery/paso6_config_detector.py",
    "backend/app/motors/m22_discovery/paso6_e090_technical.py",
    "backend/app/motors/m22_discovery/paso6_data_flow_mapper.py",
    "backend/app/motors/m22_discovery/paso6_asset_discoverer.py",
    "backend/app/motors/m22_discovery/paso6_orchestrator.py",
    "backend/app/motors/m22_discovery/paso6_vuln_inventory.py",
    "backend/app/motors/m23_retainer/paso2_extensions.py",
    "backend/app/motors/m23_retainer/api_paso2.py",
    "backend/app/motors/m25_lifecycle/lifecycle_paso4.py",
    "backend/app/motors/m25_lifecycle/api_paso4.py",
    "backend/app/motors/m27_conformity/conformity_service_paso5.py",
    "backend/app/motors/m27_conformity/api_paso5.py",
    "backend/app/motors/m21_diagnosis/paso5_orchestrator.py",
    # Legacy adicional detectado al instrumentar pre-commit (S7-S8, no en plan v4.2):
    "backend/app/models/commercial_paso7.py",
    "backend/app/models/operations_paso7.py",
    "backend/tests/motors/m09_audit_prep/test_m09_paso4.py",
    "backend/tests/motors/m21_portal_cliente/test_portal_cliente_paso3.py",
    "backend/tests/motors/m23_retainer/test_m23_paso2.py",
}

PATTERN = re.compile(r"^(paso\d+_|api_paso\d+|.*_paso\d+\.py$)")

def main(paths: list[str]) -> int:
    errors = []
    for path_str in paths:
        path = Path(path_str)
        if path.suffix != ".py":
            continue
        rel = str(path).replace("\\", "/")
        if rel in LEGACY_ALLOWED:
            continue
        if PATTERN.match(path.name):
            errors.append(
                f"{rel}: PASO_PREFIX_FORBIDDEN — files with paso{{N}}_* prefix are legacy. "
                "New files must use descriptive names without numeric prefix. "
                "See progress/session_11/REGLAS_DURAS.md regla 6."
            )
    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
