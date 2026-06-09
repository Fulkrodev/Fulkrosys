"""Phase items done computation · W1 calibracion (workflow_state refactor H1).

Contiene ``_calculate_phase_items_done`` dispatcher + 8 helpers per fase
(``_<phase>_items_done``). Cada helper ejecuta queries SQL contra tablas
motors reales · cuenta signals de completion verificables.

W1 ISSUE: la heuristica '50% midpoint' para fase actual era enganosa a UI
cliente (pct fijo independiente de progreso real). Ahora items_done refleja
completion real per fase basado en data motors.
"""
from __future__ import annotations

import uuid

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.workflow_phase import WorkflowPhase


async def _calculate_phase_items_done(
    session: AsyncSession,
    project_id: uuid.UUID,
    phase: WorkflowPhase,
) -> int:
    """Dispatch query motor-specific per fase para items_done real (W1).

    Cada helper ejecuta queries SQL contra tablas motors reales · cuenta
    signals de completion verificables. Tasks no instrumentables directas
    via project_id (e.g. proposals/contracts via lead_id) se asumen done
    cuando la fase actual ya las superó (compat con flujo lifecycle).
    """
    if phase == WorkflowPhase.PRE_VENTA:
        return await _pre_venta_items_done(session, project_id)
    if phase == WorkflowPhase.ONBOARDING:
        return await _onboarding_items_done(session, project_id)
    if phase == WorkflowPhase.DIAGNOSTICO:
        return await _diagnostico_items_done(session, project_id)
    if phase == WorkflowPhase.ADECUACION:
        return await _adecuacion_items_done(session, project_id)
    if phase == WorkflowPhase.IMPLANTACION:
        return await _implantacion_items_done(session, project_id)
    if phase == WorkflowPhase.VERIFICACION:
        return await _verificacion_items_done(session, project_id)
    if phase == WorkflowPhase.CONFORMIDAD:
        return await _conformidad_items_done(session, project_id)
    if phase == WorkflowPhase.RETAINER_CIERRE:
        return await _retainer_cierre_items_done(session, project_id)
    return 0


async def _pre_venta_items_done(
    session: AsyncSession, project_id: uuid.UUID
) -> int:
    """4 tasks: cualificar lead (A17), exploratoria (A18), propuesta (A19), contrato (M14).

    PRE_VENTA tasks 3 y 4 (proposal/contract) van via lead.id no via project.id.
    El proyecto solo existe POST cualificacion comercial · task 1 implicita done.
    Detectables directos: task 1 (project existe) + task 2 (exploratory_meeting).
    """
    pid = {"pid": str(project_id)}
    done = 0

    # Task 1 · project existe ⇒ lead cualificado (pre-existing flow comercial).
    row = await session.execute(
        sa_text("SELECT 1 FROM projects WHERE id = :pid"), pid
    )
    if row.scalar_one_or_none() is not None:
        done += 1

    # Task 2 · exploratory_meeting status=completed con project_id.
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM exploratory_meetings "
            "WHERE project_id = :pid AND status = 'completed')"
        ),
        pid,
    )
    if row.scalar():
        done += 1

    # Tasks 3 y 4 (proposal/contract) van via lead_id, sin link directo a
    # project. Si projects.fase > PRE_VENTA, el flujo lifecycle confirma
    # que ya pasaron (no mostraremos progreso parcial fiable aqui).
    return done


async def _onboarding_items_done(
    session: AsyncSession, project_id: uuid.UUID
) -> int:
    """5 tasks ONBOARDING (M16 + M12)."""
    pid = {"pid": str(project_id)}
    done = 0

    # Task 1 · onboarding_session creada para este project.
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM onboarding_sessions "
            "WHERE project_id = :pid AND deleted_at IS NULL)"
        ),
        pid,
    )
    has_session = bool(row.scalar())
    if has_session:
        done += 1

    if has_session:
        # Task 2 · interlocutor RSEG definido (interlocutor_email NOT NULL).
        row = await session.execute(
            sa_text(
                "SELECT EXISTS (SELECT 1 FROM onboarding_sessions "
                "WHERE project_id = :pid "
                "  AND deleted_at IS NULL "
                "  AND interlocutor_email IS NOT NULL)"
            ),
            pid,
        )
        if row.scalar():
            done += 1

        # Task 3 · magic link enviado (sent_at NOT NULL).
        row = await session.execute(
            sa_text(
                "SELECT EXISTS (SELECT 1 FROM onboarding_sessions "
                "WHERE project_id = :pid "
                "  AND deleted_at IS NULL "
                "  AND sent_at IS NOT NULL)"
            ),
            pid,
        )
        if row.scalar():
            done += 1

        # Task 4 · respuestas cliente recibidas (answered_questions > 0).
        row = await session.execute(
            sa_text(
                "SELECT EXISTS (SELECT 1 FROM onboarding_sessions "
                "WHERE project_id = :pid "
                "  AND deleted_at IS NULL "
                "  AND answered_questions > 0)"
            ),
            pid,
        )
        if row.scalar():
            done += 1

        # Task 5 · sesion completada.
        row = await session.execute(
            sa_text(
                "SELECT EXISTS (SELECT 1 FROM onboarding_sessions "
                "WHERE project_id = :pid "
                "  AND deleted_at IS NULL "
                "  AND estado = 'completed')"
            ),
            pid,
        )
        if row.scalar():
            done += 1

    return done


async def _diagnostico_items_done(
    session: AsyncSession, project_id: uuid.UUID
) -> int:
    """5 tasks DIAGNOSTICO (M21)."""
    pid = {"pid": str(project_id)}
    done = 0

    # Task 1 · diagnosis_run iniciado (existe).
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM diagnosis_runs "
            "WHERE project_id = :pid)"
        ),
        pid,
    )
    has_run = bool(row.scalar())
    if has_run:
        done += 1

    if has_run:
        # Task 2 · stakeholder_analysis NOT NULL.
        row = await session.execute(
            sa_text(
                "SELECT EXISTS (SELECT 1 FROM diagnosis_runs "
                "WHERE project_id = :pid AND stakeholder_analysis IS NOT NULL)"
            ),
            pid,
        )
        if row.scalar():
            done += 1

        # Task 3 · process_inventory NOT NULL.
        row = await session.execute(
            sa_text(
                "SELECT EXISTS (SELECT 1 FROM diagnosis_runs "
                "WHERE project_id = :pid AND process_inventory IS NOT NULL)"
            ),
            pid,
        )
        if row.scalar():
            done += 1

        # Task 4 · maturity_scoring NOT NULL.
        row = await session.execute(
            sa_text(
                "SELECT EXISTS (SELECT 1 FROM diagnosis_runs "
                "WHERE project_id = :pid AND maturity_scoring IS NOT NULL)"
            ),
            pid,
        )
        if row.scalar():
            done += 1

        # Task 5 · status='completed' (informe generado).
        row = await session.execute(
            sa_text(
                "SELECT EXISTS (SELECT 1 FROM diagnosis_runs "
                "WHERE project_id = :pid AND status = 'completed')"
            ),
            pid,
        )
        if row.scalar():
            done += 1

    return done


async def _adecuacion_items_done(
    session: AsyncSession, project_id: uuid.UUID
) -> int:
    """5 tasks ADECUACION (M01 + M02 + M04)."""
    pid = {"pid": str(project_id)}
    done = 0

    # Task 1 · categorizations exists. categorizations.system_id ⇒ JOIN
    # systems para link al project.
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
        pid,
    )
    if row.scalar():
        done += 1

    # Task 2 · acta firma categorizacion (signature_magic_link_id NOT NULL).
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
        pid,
    )
    if row.scalar():
        done += 1

    # Task 3 · magerit_analysis exists.
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM magerit_analysis "
            "WHERE project_id = :pid AND deleted_at IS NULL)"
        ),
        pid,
    )
    if row.scalar():
        done += 1

    # Task 4 · MAGERIT aprobado (status='approved').
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM magerit_analysis "
            "WHERE project_id = :pid AND deleted_at IS NULL "
            "  AND status = 'approved')"
        ),
        pid,
    )
    if row.scalar():
        done += 1

    # Task 5 · gap analysis (M04 · SAN-B.MB-6.1 · cierre
    # TODO-FASE-8-WORKFLOW-GAP-ANALYSIS-INSTRUMENT-001).
    # M04 GapAnalysisService persiste findings con fuente='gap_analysis'
    # (constante FUENTE_GAP en m04_gap/service.py:44).
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM findings "
            "WHERE project_id = :pid AND fuente = 'gap_analysis' "
            "  AND deleted_at IS NULL)"
        ),
        pid,
    )
    if row.scalar():
        done += 1

    return done


async def _implantacion_items_done(
    session: AsyncSession, project_id: uuid.UUID
) -> int:
    """6 tasks IMPLANTACION (M03 + M05 + M06 + M07 + M09)."""
    pid = {"pid": str(project_id)}
    done = 0

    # Task 1 · DdA entries creadas.
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM dda_entries "
            "WHERE project_id = :pid AND deleted_at IS NULL)"
        ),
        pid,
    )
    has_dda = bool(row.scalar())
    if has_dda:
        done += 1

    # Task 2 · DdA frozen (firma proyecto exists).
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM dda_project_signatures "
            "WHERE project_id = :pid)"
        ),
        pid,
    )
    if row.scalar():
        done += 1

    # Task 3 · documentacion politicas (M06 DocumentFactory ·
    # SAN-B.MB-6.1 · cierre TODO-FASE-8-WORKFLOW-POLICIES-INSTRUMENT-001).
    # M06 genera Documents con tipo='politica' (TemplateCategoria.POLITICA
    # en m06_document_factory/enums.py:8). Una política
    # contado como done cuando approved_at IS NOT NULL.
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM documents "
            "WHERE project_id = :pid AND tipo = 'politica' "
            "  AND approved_at IS NOT NULL "
            "  AND deleted_at IS NULL)"
        ),
        pid,
    )
    if row.scalar():
        done += 1

    # Task 4 · controles implementados (M06) · dda_entries con
    # estado_implementacion='implementado'.
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM dda_entries "
            "WHERE project_id = :pid AND deleted_at IS NULL "
            "  AND estado_implementacion = 'implementado')"
        ),
        pid,
    )
    if row.scalar():
        done += 1

    # Task 5 · evidencias recogidas (M07).
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM evidence "
            "WHERE project_id = :pid AND deleted_at IS NULL)"
        ),
        pid,
    )
    if row.scalar():
        done += 1

    # Task 6 · audit_checklist completo (M09 audit_checklist_items count > 0).
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM audit_checklist_items "
            "WHERE project_id = :pid)"
        ),
        pid,
    )
    if row.scalar():
        done += 1

    return done


async def _verificacion_items_done(
    session: AsyncSession, project_id: uuid.UUID
) -> int:
    """5 tasks VERIFICACION (M08 + M12)."""
    pid = {"pid": str(project_id)}
    done = 0

    # Task 1 · verification run scheduled (cualquier run existe).
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM verification_runs "
            "WHERE project_id = :pid AND deleted_at IS NULL)"
        ),
        pid,
    )
    has_run = bool(row.scalar())
    if has_run:
        done += 1

    if has_run:
        # Task 2 · authorization magic link signed (authorization_signed_at).
        row = await session.execute(
            sa_text(
                "SELECT EXISTS (SELECT 1 FROM verification_runs "
                "WHERE project_id = :pid AND deleted_at IS NULL "
                "  AND authorization_signed_at IS NOT NULL)"
            ),
            pid,
        )
        if row.scalar():
            done += 1

        # Task 3 · run completed.
        row = await session.execute(
            sa_text(
                "SELECT EXISTS (SELECT 1 FROM verification_runs "
                "WHERE project_id = :pid AND deleted_at IS NULL "
                "  AND status = 'completed')"
            ),
            pid,
        )
        if row.scalar():
            done += 1

        # Task 4 · findings revisados (al menos uno con status post 'open').
        row = await session.execute(
            sa_text(
                "SELECT EXISTS (SELECT 1 FROM verification_findings "
                "WHERE project_id = :pid "
                "  AND status IN ('confirmed', 'mitigated', "
                "                 'accepted_risk', 'false_positive'))"
            ),
            pid,
        )
        if row.scalar():
            done += 1

        # Task 5 · remediation tracking (proxy: findings con status mitigated).
        row = await session.execute(
            sa_text(
                "SELECT EXISTS (SELECT 1 FROM verification_findings "
                "WHERE project_id = :pid AND status = 'mitigated')"
            ),
            pid,
        )
        if row.scalar():
            done += 1

    return done


async def _conformidad_items_done(
    session: AsyncSession, project_id: uuid.UUID
) -> int:
    """5 tasks CONFORMIDAD (M09 + M27)."""
    pid = {"pid": str(project_id)}
    done = 0

    # Task 1 · audit_preparation_runs exists.
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM audit_preparation_runs "
            "WHERE project_id = :pid AND deleted_at IS NULL)"
        ),
        pid,
    )
    has_run = bool(row.scalar())
    if has_run:
        done += 1

    if has_run:
        # Task 2 · dossier generated (audit_prep en estado generado/completed).
        row = await session.execute(
            sa_text(
                "SELECT EXISTS (SELECT 1 FROM audit_preparation_runs "
                "WHERE project_id = :pid AND deleted_at IS NULL "
                "  AND estado IN ('generado', 'completed'))"
            ),
            pid,
        )
        if row.scalar():
            done += 1

        # Task 3 · audit prep completed.
        row = await session.execute(
            sa_text(
                "SELECT EXISTS (SELECT 1 FROM audit_preparation_runs "
                "WHERE project_id = :pid AND deleted_at IS NULL "
                "  AND estado = 'completed')"
            ),
            pid,
        )
        if row.scalar():
            done += 1

    # Task 4 · conformity_submissions exists.
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM conformity_submissions "
            "WHERE project_id = :pid)"
        ),
        pid,
    )
    has_submission = bool(row.scalar())
    if has_submission:
        done += 1

        # Task 5 · submission accepted.
        row = await session.execute(
            sa_text(
                "SELECT EXISTS (SELECT 1 FROM conformity_submissions "
                "WHERE project_id = :pid AND status = 'accepted')"
            ),
            pid,
        )
        if row.scalar():
            done += 1

    return done


async def _retainer_cierre_items_done(
    session: AsyncSession, project_id: uuid.UUID
) -> int:
    """4 tasks RETAINER_CIERRE (M23 + M25)."""
    pid = {"pid": str(project_id)}
    done = 0

    # Task 1 · retainer ofrecido (project_lifecycle_event 'retainer_offered').
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM project_lifecycle_events "
            "WHERE project_id = :pid AND event_type = 'retainer_offered')"
        ),
        pid,
    )
    if row.scalar():
        done += 1

    # Task 2 · retainer_contracts.estado='active'.
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM retainer_contracts "
            "WHERE project_id = :pid AND deleted_at IS NULL "
            "  AND estado = 'active')"
        ),
        pid,
    )
    if row.scalar():
        done += 1

    # Task 3 · quarterly reports activos (al menos 1).
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM retainer_quarterly_reports "
            "WHERE project_id = :pid)"
        ),
        pid,
    )
    if row.scalar():
        done += 1

    # Task 4 · lifecycle event 'certified'.
    row = await session.execute(
        sa_text(
            "SELECT EXISTS (SELECT 1 FROM project_lifecycle_events "
            "WHERE project_id = :pid AND event_type = 'certified')"
        ),
        pid,
    )
    if row.scalar():
        done += 1

    return done
