"""Auditor portal canonical audit_log accion namespace.

Sesión 3B-2B.6 CLUSTER 2 Phase 6 · Marcos canonical event_type list para
auditor portal interactions. Single source of truth · usado por
public_api.py + cross-motor wire-in (M03 + M04 + M07 + M27 + M08 + M09).

Naming convention:
- ``auditor.session.*`` — auditor session lifecycle (start/refresh/end)
- ``auditor.view.*`` — read-only view fetch per section (9 sections)
- ``auditor.download.*`` — binary asset download per type
- ``auditor.search.*`` — search query con metadata propagated

Backward-compat preserved: NO CHECK constraint enforced en audit_log.accion
column (VARCHAR(60) post Sub-atom 5.A widen migration). Cross-motor existing
accion values (e.g. "marked", "approve", "evidence.upload") continue to pass.
Esta constante list es convention enforcement at code level (linter-friendly).

Hash chain inviolable R6 preserved · ningún evento aquí muta audit_log
row post-insert (only BEFORE INSERT trigger fn_audit_log_hash_chain
calcula hash_current desde prev || fields).
"""
from __future__ import annotations

# ── Session lifecycle (Phase 4) ────────────────────────────────────────

AUDITOR_SESSION_START = "auditor.session.start"
AUDITOR_SESSION_REFRESH = "auditor.session.refresh"   # Future · token rotation
AUDITOR_SESSION_END = "auditor.session.end"            # Future · explicit logout

# ── View events · 9 sections per Phase 5 ───────────────────────────────

AUDITOR_VIEW_SUMMARY = "auditor_portal.view"   # Phase 4 metadata gate
AUDITOR_VIEW_DDA = "auditor.view.dda"
AUDITOR_VIEW_MAGERIT = "auditor.view.magerit"
AUDITOR_VIEW_PLAN = "auditor.view.plan"
AUDITOR_VIEW_EVIDENCE = "auditor.view.evidence"
AUDITOR_VIEW_E041 = "auditor.view.e041"
AUDITOR_VIEW_AUDIT_LOG = "auditor.view.audit_log"
AUDITOR_VIEW_PENTEST = "auditor.view.pentest"
AUDITOR_VIEW_DOCUMENTS = "auditor.view.documents"

# ── Download events · binary asset retrieval ───────────────────────────

AUDITOR_DOWNLOAD_DDA_PDF = "auditor.download.dda_pdf"
AUDITOR_DOWNLOAD_PDA_PDF = "auditor.download.pda_pdf"
AUDITOR_DOWNLOAD_EVIDENCE_FILE = "auditor.download.evidence_file"
AUDITOR_DOWNLOAD_EVIDENCE_ZIP = "auditor.download.evidence_zip"
AUDITOR_DOWNLOAD_E041_PDF = "auditor.download.e041_pdf"
AUDITOR_DOWNLOAD_AUDIT_LOG_CSV = "auditor.download.audit_log_csv"
AUDITOR_DOWNLOAD_PENTEST_REPORT = "auditor.download.pentest_report"
AUDITOR_DOWNLOAD_DOCUMENT = "auditor.download.document"
AUDITOR_DOWNLOAD_DOCUMENTS_ZIP = "auditor.download.documents_zip"

# ── Search events · query + filter metadata ────────────────────────────

AUDITOR_SEARCH_EVIDENCE = "auditor.search.evidence"

# ── CLUSTER 3 Phase C1 · annotation events ─────────────────────────────

AUDITOR_ANNOTATION_CREATED = "auditor.annotation.created"
AUDITOR_ANNOTATION_DELETED = "auditor.annotation.deleted"
ADMIN_ANNOTATION_RESPONDED = "admin.annotation.responded"

# ── CLUSTER 3 Phase C2 · clarification events ──────────────────────────

AUDITOR_CLARIFICATION_REQUESTED = "auditor.clarification.requested"
ADMIN_CLARIFICATION_RESPONDED = "admin.clarification.responded"

# ── CLUSTER 3 Phase C3 · DdA-evidence gap events ───────────────────────

AUDITOR_VIEW_DDA_EVIDENCE_GAPS = "auditor.view.dda_evidence_gaps"
AUDITOR_VIEW_DDA_EVIDENCE_GAPS_DETAIL = (
    "auditor.view.dda_evidence_gaps_medida_detail"
)
ADMIN_EVIDENCE_REQUEST_TRIGGERED = "admin.evidence_request.triggered"

# ── CLUSTER 3 Phase C4 · draft audit report events ─────────────────────

AUDITOR_DRAFT_REPORT_GENERATED = "auditor.draft_report.generated"
AUDITOR_DRAFT_REPORT_PREVIEW = "auditor.draft_report.preview"
ADMIN_DRAFT_REPORT_GENERATED = "admin.draft_report.generated"

# ── Sesión 3B-2B.10 Phase 10 · Simulacro Pre-ENAC events ───────────────

SIMULACRO_PRE_ENAC_EXECUTED = "simulacro.pre_enac.executed"
SIMULACRO_PRE_ENAC_REPORT_GENERATED = "simulacro.pre_enac.report_generated"
AUDIT_INTEGRITY_CHECKED = "audit.integrity.checked"
CORRECTIVE_LOOP_OPENED = "corrective.loop.opened"
CORRECTIVE_LOOP_IN_PROGRESS = "corrective.loop.in_progress"
CORRECTIVE_LOOP_CLOSED = "corrective.loop.closed"


# Full canonical list for verification + test enumeration
AUDITOR_EVENT_TYPES: tuple[str, ...] = (
    # Session (3)
    AUDITOR_SESSION_START,
    AUDITOR_SESSION_REFRESH,
    AUDITOR_SESSION_END,
    # Views (9 · 1 metadata gate + 8 section specific)
    AUDITOR_VIEW_SUMMARY,
    AUDITOR_VIEW_DDA,
    AUDITOR_VIEW_MAGERIT,
    AUDITOR_VIEW_PLAN,
    AUDITOR_VIEW_EVIDENCE,
    AUDITOR_VIEW_E041,
    AUDITOR_VIEW_AUDIT_LOG,
    AUDITOR_VIEW_PENTEST,
    AUDITOR_VIEW_DOCUMENTS,
    # Downloads (9)
    AUDITOR_DOWNLOAD_DDA_PDF,
    AUDITOR_DOWNLOAD_PDA_PDF,
    AUDITOR_DOWNLOAD_EVIDENCE_FILE,
    AUDITOR_DOWNLOAD_EVIDENCE_ZIP,
    AUDITOR_DOWNLOAD_E041_PDF,
    AUDITOR_DOWNLOAD_AUDIT_LOG_CSV,
    AUDITOR_DOWNLOAD_PENTEST_REPORT,
    AUDITOR_DOWNLOAD_DOCUMENT,
    AUDITOR_DOWNLOAD_DOCUMENTS_ZIP,
    # Search (1)
    AUDITOR_SEARCH_EVIDENCE,
    # CLUSTER 3 C1 annotations (3)
    AUDITOR_ANNOTATION_CREATED,
    AUDITOR_ANNOTATION_DELETED,
    ADMIN_ANNOTATION_RESPONDED,
    # CLUSTER 3 C2 clarifications (2)
    AUDITOR_CLARIFICATION_REQUESTED,
    ADMIN_CLARIFICATION_RESPONDED,
    # CLUSTER 3 C3 DdA-evidence gaps (3)
    AUDITOR_VIEW_DDA_EVIDENCE_GAPS,
    AUDITOR_VIEW_DDA_EVIDENCE_GAPS_DETAIL,
    ADMIN_EVIDENCE_REQUEST_TRIGGERED,
    # CLUSTER 3 C4 draft audit report (3)
    AUDITOR_DRAFT_REPORT_GENERATED,
    AUDITOR_DRAFT_REPORT_PREVIEW,
    ADMIN_DRAFT_REPORT_GENERATED,
    # Sesión 3B-2B.10 Simulacro Pre-ENAC (6)
    SIMULACRO_PRE_ENAC_EXECUTED,
    SIMULACRO_PRE_ENAC_REPORT_GENERATED,
    AUDIT_INTEGRITY_CHECKED,
    CORRECTIVE_LOOP_OPENED,
    CORRECTIVE_LOOP_IN_PROGRESS,
    CORRECTIVE_LOOP_CLOSED,
)


def is_auditor_event(accion: str) -> bool:
    """True si accion pertenece al namespace auditor portal canonical."""
    return accion in AUDITOR_EVENT_TYPES


def auditor_namespace_prefix(accion: str) -> str | None:
    """Returns 'session' · 'view' · 'download' · 'search' o None."""
    if not accion.startswith("auditor"):
        return None
    parts = accion.split(".", 2)
    if len(parts) < 2:
        return None
    # auditor_portal.view (legacy Phase 4 metadata gate) → 'view'
    if parts[0] == "auditor_portal" and parts[1] == "view":
        return "view"
    if parts[0] == "auditor":
        return parts[1] if parts[1] in ("session", "view", "download", "search") else None
    return None
