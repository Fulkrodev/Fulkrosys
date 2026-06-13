"""Atomic SQL EXISTS signal primitives · W2 calibracion (workflow_state refactor H1).

35 ``_signal_*`` checkers + ``_TASK_SIGNAL_CHECKERS`` dispatch dict.
Cada checker retorna bool · True = task completada, False = pending.
Centralizar aquí las queries de detección mantiene ``workflow_templates.py``
como configuración pura sin SQL.

35 signals mapped (39 tasks total · 4 manual_tracking sin signal).
"""
from __future__ import annotations

import uuid

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession


async def _signal_project_exists(
    session: AsyncSession, project_id: uuid.UUID
) -> bool:
    row = await session.execute(
        sa_text("SELECT 1 FROM projects WHERE id = :pid"),
        {"pid": str(project_id)},
    )
    return row.scalar_one_or_none() is not None


async def _signal_exploratory_completed(
    session: AsyncSession, project_id: uuid.UUID
) -> bool:
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM exploratory_meetings "
            "WHERE project_id = :pid AND status = 'completed')"
        ),
        {"pid": str(project_id)},
    )
    return bool(row.scalar())


# Onboarding signals
async def _signal_onboarding_session_created(
    session: AsyncSession, project_id: uuid.UUID
) -> bool:
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM onboarding_sessions "
            "WHERE project_id = :pid AND deleted_at IS NULL)"
        ),
        {"pid": str(project_id)},
    )
    return bool(row.scalar())


async def _signal_onboarding_rseg_defined(
    session: AsyncSession, project_id: uuid.UUID
) -> bool:
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM onboarding_sessions "
            "WHERE project_id = :pid AND deleted_at IS NULL "
            "  AND interlocutor_email IS NOT NULL)"
        ),
        {"pid": str(project_id)},
    )
    return bool(row.scalar())


async def _signal_onboarding_magic_link_sent(
    session: AsyncSession, project_id: uuid.UUID
) -> bool:
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM onboarding_sessions "
            "WHERE project_id = :pid AND deleted_at IS NULL "
            "  AND sent_at IS NOT NULL)"
        ),
        {"pid": str(project_id)},
    )
    return bool(row.scalar())


async def _signal_onboarding_answers_received(
    session: AsyncSession, project_id: uuid.UUID
) -> bool:
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM onboarding_sessions "
            "WHERE project_id = :pid AND deleted_at IS NULL "
            "  AND answered_questions > 0)"
        ),
        {"pid": str(project_id)},
    )
    return bool(row.scalar())


async def _signal_onboarding_session_completed(
    session: AsyncSession, project_id: uuid.UUID
) -> bool:
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM onboarding_sessions "
            "WHERE project_id = :pid AND deleted_at IS NULL "
            "  AND estado = 'completed')"
        ),
        {"pid": str(project_id)},
    )
    return bool(row.scalar())


# Diagnostico signals
async def _signal_diagnosis_run_started(
    session: AsyncSession, project_id: uuid.UUID
) -> bool:
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM diagnosis_runs "
            "WHERE project_id = :pid)"
        ),
        {"pid": str(project_id)},
    )
    return bool(row.scalar())


async def _signal_diagnosis_stakeholder_analysis(
    session: AsyncSession, project_id: uuid.UUID
) -> bool:
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM diagnosis_runs "
            "WHERE project_id = :pid AND stakeholder_analysis IS NOT NULL)"
        ),
        {"pid": str(project_id)},
    )
    return bool(row.scalar())


async def _signal_diagnosis_process_inventory(
    session: AsyncSession, project_id: uuid.UUID
) -> bool:
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM diagnosis_runs "
            "WHERE project_id = :pid AND process_inventory IS NOT NULL)"
        ),
        {"pid": str(project_id)},
    )
    return bool(row.scalar())


async def _signal_diagnosis_maturity_scoring(
    session: AsyncSession, project_id: uuid.UUID
) -> bool:
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM diagnosis_runs "
            "WHERE project_id = :pid AND maturity_scoring IS NOT NULL)"
        ),
        {"pid": str(project_id)},
    )
    return bool(row.scalar())


async def _signal_diagnosis_report_generated(
    session: AsyncSession, project_id: uuid.UUID
) -> bool:
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM diagnosis_runs "
            "WHERE project_id = :pid AND status = 'completed')"
        ),
        {"pid": str(project_id)},
    )
    return bool(row.scalar())


# Adecuacion signals
async def _signal_categorization_exists(
    session: AsyncSession, project_id: uuid.UUID
) -> bool:
    row = await session.execute(
        sa_text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM categorizations c "
            "  JOIN systems s ON s.id = c.system_id "
            "  WHERE s.project_id = :pid "
            "    AND c.deleted_at IS NULL "
            "    AND s.deleted_at IS NULL"
            ")"
        ),
        {"pid": str(project_id)},
    )
    return bool(row.scalar())


async def _signal_categorization_signed(
    session: AsyncSession, project_id: uuid.UUID
) -> bool:
    row = await session.execute(
        sa_text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM categorizations c "
            "  JOIN systems s ON s.id = c.system_id "
            "  WHERE s.project_id = :pid "
            "    AND c.deleted_at IS NULL "
            "    AND s.deleted_at IS NULL "
            "    AND c.signature_magic_link_id IS NOT NULL"
            ")"
        ),
        {"pid": str(project_id)},
    )
    return bool(row.scalar())


async def _signal_magerit_exists(
    session: AsyncSession, project_id: uuid.UUID
) -> bool:
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM magerit_analysis "
            "WHERE project_id = :pid AND deleted_at IS NULL)"
        ),
        {"pid": str(project_id)},
    )
    return bool(row.scalar())


async def _signal_magerit_approved(
    session: AsyncSession, project_id: uuid.UUID
) -> bool:
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM magerit_analysis "
            "WHERE project_id = :pid AND deleted_at IS NULL "
            "  AND status = 'approved')"
        ),
        {"pid": str(project_id)},
    )
    return bool(row.scalar())


# Implantacion signals
async def _signal_dda_entries_exist(
    session: AsyncSession, project_id: uuid.UUID
) -> bool:
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM dda_entries "
            "WHERE project_id = :pid AND deleted_at IS NULL)"
        ),
        {"pid": str(project_id)},
    )
    return bool(row.scalar())


async def _signal_dda_frozen(
    session: AsyncSession, project_id: uuid.UUID
) -> bool:
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM dda_project_signatures "
            "WHERE project_id = :pid)"
        ),
        {"pid": str(project_id)},
    )
    return bool(row.scalar())


async def _signal_dda_controls_implemented(
    session: AsyncSession, project_id: uuid.UUID
) -> bool:
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM dda_entries "
            "WHERE project_id = :pid AND deleted_at IS NULL "
            "  AND estado_implementacion = 'implantada')"
        ),
        {"pid": str(project_id)},
    )
    return bool(row.scalar())


async def _signal_evidence_collected(
    session: AsyncSession, project_id: uuid.UUID
) -> bool:
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM evidence "
            "WHERE project_id = :pid AND deleted_at IS NULL)"
        ),
        {"pid": str(project_id)},
    )
    return bool(row.scalar())


async def _signal_audit_checklist_started(
    session: AsyncSession, project_id: uuid.UUID
) -> bool:
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM audit_checklist_items "
            "WHERE project_id = :pid)"
        ),
        {"pid": str(project_id)},
    )
    return bool(row.scalar())


# Verificacion signals
async def _signal_verification_run_exists(
    session: AsyncSession, project_id: uuid.UUID
) -> bool:
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM verification_runs "
            "WHERE project_id = :pid AND deleted_at IS NULL)"
        ),
        {"pid": str(project_id)},
    )
    return bool(row.scalar())


async def _signal_verification_authorization_signed(
    session: AsyncSession, project_id: uuid.UUID
) -> bool:
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM verification_runs "
            "WHERE project_id = :pid AND deleted_at IS NULL "
            "  AND authorization_signed_at IS NOT NULL)"
        ),
        {"pid": str(project_id)},
    )
    return bool(row.scalar())


async def _signal_verification_run_completed(
    session: AsyncSession, project_id: uuid.UUID
) -> bool:
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM verification_runs "
            "WHERE project_id = :pid AND deleted_at IS NULL "
            "  AND status = 'completed')"
        ),
        {"pid": str(project_id)},
    )
    return bool(row.scalar())


async def _signal_verification_findings_reviewed(
    session: AsyncSession, project_id: uuid.UUID
) -> bool:
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM verification_findings "
            "WHERE project_id = :pid "
            "  AND status IN ('confirmed', 'mitigated', "
            "                 'accepted_risk', 'false_positive'))"
        ),
        {"pid": str(project_id)},
    )
    return bool(row.scalar())


async def _signal_verification_remediation_tracked(
    session: AsyncSession, project_id: uuid.UUID
) -> bool:
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM verification_findings "
            "WHERE project_id = :pid AND status = 'mitigated')"
        ),
        {"pid": str(project_id)},
    )
    return bool(row.scalar())


# Conformidad signals
async def _signal_audit_prep_started(
    session: AsyncSession, project_id: uuid.UUID
) -> bool:
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM audit_preparation_runs "
            "WHERE project_id = :pid AND deleted_at IS NULL)"
        ),
        {"pid": str(project_id)},
    )
    return bool(row.scalar())


async def _signal_audit_prep_dossier_generated(
    session: AsyncSession, project_id: uuid.UUID
) -> bool:
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM audit_preparation_runs "
            "WHERE project_id = :pid AND deleted_at IS NULL "
            "  AND estado IN ('generado', 'completed'))"
        ),
        {"pid": str(project_id)},
    )
    return bool(row.scalar())


async def _signal_audit_prep_completed(
    session: AsyncSession, project_id: uuid.UUID
) -> bool:
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM audit_preparation_runs "
            "WHERE project_id = :pid AND deleted_at IS NULL "
            "  AND estado = 'completed')"
        ),
        {"pid": str(project_id)},
    )
    return bool(row.scalar())


async def _signal_conformity_submission_exists(
    session: AsyncSession, project_id: uuid.UUID
) -> bool:
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM conformity_submissions "
            "WHERE project_id = :pid)"
        ),
        {"pid": str(project_id)},
    )
    return bool(row.scalar())


async def _signal_conformity_submission_accepted(
    session: AsyncSession, project_id: uuid.UUID
) -> bool:
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM conformity_submissions "
            "WHERE project_id = :pid AND status = 'accepted')"
        ),
        {"pid": str(project_id)},
    )
    return bool(row.scalar())


# Retainer signals
async def _signal_retainer_offered_event(
    session: AsyncSession, project_id: uuid.UUID
) -> bool:
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM project_lifecycle_events "
            "WHERE project_id = :pid AND event_type = 'retainer_offered')"
        ),
        {"pid": str(project_id)},
    )
    return bool(row.scalar())


async def _signal_retainer_active(
    session: AsyncSession, project_id: uuid.UUID
) -> bool:
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM retainer_contracts "
            "WHERE project_id = :pid AND deleted_at IS NULL "
            "  AND estado = 'active')"
        ),
        {"pid": str(project_id)},
    )
    return bool(row.scalar())


async def _signal_retainer_quarterly_reports_exist(
    session: AsyncSession, project_id: uuid.UUID
) -> bool:
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM retainer_quarterly_reports "
            "WHERE project_id = :pid)"
        ),
        {"pid": str(project_id)},
    )
    return bool(row.scalar())


async def _signal_lifecycle_certified_event(
    session: AsyncSession, project_id: uuid.UUID
) -> bool:
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM project_lifecycle_events "
            "WHERE project_id = :pid AND event_type = 'certified')"
        ),
        {"pid": str(project_id)},
    )
    return bool(row.scalar())


# Dispatch dict signal_id → checker async callable.
# 35 signals mapped (39 tasks total · 4 manual_tracking sin signal).
_TASK_SIGNAL_CHECKERS: dict = {
    "project_exists": _signal_project_exists,
    "exploratory_completed": _signal_exploratory_completed,
    # Onboarding
    "onboarding_session_created": _signal_onboarding_session_created,
    "onboarding_rseg_defined": _signal_onboarding_rseg_defined,
    "onboarding_magic_link_sent": _signal_onboarding_magic_link_sent,
    "onboarding_answers_received": _signal_onboarding_answers_received,
    "onboarding_session_completed": _signal_onboarding_session_completed,
    # Diagnostico
    "diagnosis_run_started": _signal_diagnosis_run_started,
    "diagnosis_stakeholder_analysis": _signal_diagnosis_stakeholder_analysis,
    "diagnosis_process_inventory": _signal_diagnosis_process_inventory,
    "diagnosis_maturity_scoring": _signal_diagnosis_maturity_scoring,
    "diagnosis_report_generated": _signal_diagnosis_report_generated,
    # Adecuacion
    "categorization_exists": _signal_categorization_exists,
    "categorization_signed": _signal_categorization_signed,
    "magerit_exists": _signal_magerit_exists,
    "magerit_approved": _signal_magerit_approved,
    # Implantacion
    "dda_entries_exist": _signal_dda_entries_exist,
    "dda_frozen": _signal_dda_frozen,
    "dda_controls_implemented": _signal_dda_controls_implemented,
    "evidence_collected": _signal_evidence_collected,
    "audit_checklist_started": _signal_audit_checklist_started,
    # Verificacion
    "verification_run_exists": _signal_verification_run_exists,
    "verification_authorization_signed": _signal_verification_authorization_signed,
    "verification_run_completed": _signal_verification_run_completed,
    "verification_findings_reviewed": _signal_verification_findings_reviewed,
    "verification_remediation_tracked": _signal_verification_remediation_tracked,
    # Conformidad
    "audit_prep_started": _signal_audit_prep_started,
    "audit_prep_dossier_generated": _signal_audit_prep_dossier_generated,
    "audit_prep_completed": _signal_audit_prep_completed,
    "conformity_submission_exists": _signal_conformity_submission_exists,
    "conformity_submission_accepted": _signal_conformity_submission_accepted,
    # Retainer
    "retainer_offered_event": _signal_retainer_offered_event,
    "retainer_active": _signal_retainer_active,
    "retainer_quarterly_reports_exist": _signal_retainer_quarterly_reports_exist,
    "lifecycle_certified_event": _signal_lifecycle_certified_event,
}
