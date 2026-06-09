"""M8 v5.1 - Integraciones con otros motores."""
from backend.app.motors.m08_verification.integrations.m3_dda_updater import (
    detect_dda_contradictions,
    get_findings_by_measure,
    get_tech_verification_summary,
)
from backend.app.motors.m08_verification.integrations.m5_obligations import (
    create_remediation_obligations,
)
from backend.app.motors.m08_verification.integrations.m7_evidence import (
    backfill_evidence_for_run,
    create_evidence_for_finding,
    create_evidence_for_run_report,
    get_findings_for_project,
)
from backend.app.motors.m08_verification.integrations.m9_audit_prep import (
    collect_findings_for_dossier,
    count_findings_by_measure,
    get_verification_report_documents,
    has_verification_run,
)

__all__ = [
    'detect_dda_contradictions',
    'get_findings_by_measure',
    'get_tech_verification_summary',
    'create_remediation_obligations',
    'backfill_evidence_for_run',
    'create_evidence_for_finding',
    'create_evidence_for_run_report',
    'get_findings_for_project',
    'collect_findings_for_dossier',
    'count_findings_by_measure',
    'get_verification_report_documents',
    'has_verification_run',
]
