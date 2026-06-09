"""M8 v5.1 - External handoff subsystem."""
from backend.app.motors.m08_verification.external.handoff_builder import (
    HANDOFF_DOCUMENTS,
    build_handoff_package,
)
from backend.app.motors.m08_verification.external.vpn_manager import (
    VpnArtifact,
    generate_for_handoff,
)
from backend.app.motors.m08_verification.external.findings_ingester import (
    ingest_external_findings,
    parse_structured_payload,
    parse_pdf_payload,
)

__all__ = [
    'HANDOFF_DOCUMENTS',
    'build_handoff_package',
    'VpnArtifact',
    'generate_for_handoff',
    'ingest_external_findings',
    'parse_structured_payload',
    'parse_pdf_payload',
]
