"""Phase derivation · CASCADE strategy ADR-026 (workflow_state refactor H1).

Contiene ``get_current_phase`` (public) + ``_derive_phase_cascade`` (private
fallback). El cascade ordena 7 EXISTS subqueries sobre motors para inferir
fase actual cuando ``projects.fase`` persistido está ausente o desactualizado.

ISSUE-W3 calibración: filtros temporales post-último ``phase_changed`` event
(retrocompat épocha si no hay events).
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.workflow_phase import WorkflowPhase

log = logging.getLogger(__name__)


async def get_current_phase(
    session: AsyncSession,
    project_id: uuid.UUID,
) -> WorkflowPhase:
    """Retrieve current workflow phase del proyecto.

    Strategy híbrida ADR-026:
    1. Priority: ``projects.fase`` persisted (source of truth primaria;
       cliente avanza fase explícitamente vía UI o motor service).
    2. Fallback CASCADE: derive desde motors si ``projects.fase`` ausente
       (pre-migration legacy) o no encontrado en enum.

    Raises:
        ValueError: si el proyecto no existe.
    """
    row = await session.execute(
        sa_text("SELECT fase FROM projects WHERE id = :pid"),
        {"pid": str(project_id)},
    )
    fase_persisted = row.scalar_one_or_none()

    if fase_persisted is None:
        raise ValueError(f"Project {project_id} not found")

    try:
        return WorkflowPhase(fase_persisted)
    except ValueError:
        # Fallback CASCADE · valor persistido inválido (legacy pre-migration)
        return await _derive_phase_cascade(session, project_id)


async def _derive_phase_cascade(
    session: AsyncSession,
    project_id: uuid.UUID,
) -> WorkflowPhase:
    """Derive fase desde motors latest activity (CASCADE fallback).

    Order: retainer_cierre → conformidad → verificacion → implantacion
    → adecuacion → diagnostico → onboarding → pre_venta (default).

    Cada chequeo es un EXISTS subquery sobre tabla específica per fase.

    ISSUE-W3 calibracion: cada query filtra data motor con created_at
    posterior al ultimo phase_changed event del proyecto. Sin ese filtro,
    una regresion de fase (X → fase_anterior) dejaba data motor pre-
    regresion disparando CASCADE incorrecto. El COALESCE→epoch garantiza
    retrocompat: si no hay phase_changed events, comportamiento equivale
    al pre-W3 (toda data cuenta).

    Activacion efectiva W3 (SAN-B.MB-6.1): trigger BD
    `tg_projects_phase_changed` (migracion `san_b_workflow_phase_changed_trigger_lifecycle`)
    emite project_lifecycle_events cuando projects.fase cambia ·
    cierre TODO-FASE-8-WORKFLOW-PHASE-CHANGED-TRIGGER-001.
    """
    pid = {"pid": str(project_id)}

    # Subquery reutilizable: timestamp del ultimo phase_changed event,
    # epoch si no existen (descarte cero · retrocompat).
    LAST_PHASE_CHANGE = (
        "COALESCE("
        "  (SELECT MAX(event_date) FROM project_lifecycle_events "
        "   WHERE project_id = :pid AND event_type = 'phase_changed'), "
        "  '1970-01-01 00:00:00+00'::timestamptz"
        ")"
    )

    # Retainer/cierre · M23 retainer activo OR M25 evento data_deleted
    # ISSUE-W5: project_lifecycle_events sin columna deleted_at (no soft-delete).
    # ISSUE-W3: filtro temporal post-ultimo phase_changed event.
    row = await session.execute(
        sa_text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM retainer_contracts "
            "  WHERE project_id = :pid AND estado = 'active' "
            "    AND deleted_at IS NULL "
            f"    AND created_at > {LAST_PHASE_CHANGE}"
            ") OR EXISTS ("
            "  SELECT 1 FROM project_lifecycle_events "
            "  WHERE project_id = :pid "
            "    AND event_type IN ('certified', 'data_deleted') "
            f"    AND event_date > {LAST_PHASE_CHANGE}"
            ")"
        ),
        pid,
    )
    if row.scalar():
        return WorkflowPhase.RETAINER_CIERRE

    # Conformidad · M27 submission accepted OR M09 audit_preparation completed
    # ISSUE-W5: conformity_submissions sin columna deleted_at (no soft-delete).
    # ISSUE-W3: filtro temporal post-ultimo phase_changed event.
    row = await session.execute(
        sa_text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM conformity_submissions "
            "  WHERE project_id = :pid AND status = 'accepted' "
            f"    AND created_at > {LAST_PHASE_CHANGE}"
            ") OR EXISTS ("
            "  SELECT 1 FROM audit_preparation_runs "
            "  WHERE project_id = :pid AND estado = 'completed' "
            "    AND deleted_at IS NULL "
            f"    AND created_at > {LAST_PHASE_CHANGE}"
            ")"
        ),
        pid,
    )
    if row.scalar():
        return WorkflowPhase.CONFORMIDAD

    # Verificación · M08 verification run completed
    # ISSUE-W3: filtro temporal post-ultimo phase_changed event.
    row = await session.execute(
        sa_text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM verification_runs "
            "  WHERE project_id = :pid AND status = 'completed' "
            "    AND deleted_at IS NULL "
            f"    AND created_at > {LAST_PHASE_CHANGE}"
            ")"
        ),
        pid,
    )
    if row.scalar():
        return WorkflowPhase.VERIFICACION

    # DdA Final · todas DdA implantadas, sin parcial pendiente
    # (SAN-C MB-11.1 · sub-fase separada de implantacion · pre-verificación)
    # ISSUE-W3: filtro temporal post-ultimo phase_changed event.
    # FIX: enum canónico EstadoImplementacion = implantada/parcial (NO
    # implementado/en_proceso · valores que NUNCA existieron en BD → ramas muertas).
    row = await session.execute(
        sa_text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM dda_entries "
            "  WHERE project_id = :pid "
            "    AND estado_implementacion = 'implantada' "
            "    AND deleted_at IS NULL "
            f"    AND created_at > {LAST_PHASE_CHANGE}"
            ") AND NOT EXISTS ("
            "  SELECT 1 FROM dda_entries "
            "  WHERE project_id = :pid "
            "    AND estado_implementacion = 'parcial' "
            "    AND deleted_at IS NULL "
            f"    AND created_at > {LAST_PHASE_CHANGE}"
            ")"
        ),
        pid,
    )
    if row.scalar():
        return WorkflowPhase.DDA_FINAL

    # Implantación · M03 DdA entries con implementación en proceso
    # ISSUE-W3: filtro temporal post-ultimo phase_changed event.
    # Hallazgo W3 pre-existente: query original hacia JOIN measures + systems
    # pero la tabla `measures` no existe en BD (solo dda_entries con FK
    # measure_id huerfana hacia un schema que nunca se materializo). El
    # JOIN producia UndefinedTableError si CASCADE llegaba a esta rama.
    # Simplificado: dda_entries.project_id existe directo · sin JOIN.
    # SAN-C MB-11.1: cascade discrimina 'parcial' (IMPLANTACION) vs
    # 'implantada' all-done (DDA_FINAL · check anterior).
    row = await session.execute(
        sa_text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM dda_entries "
            "  WHERE project_id = :pid "
            "    AND estado_implementacion = 'parcial' "
            "    AND deleted_at IS NULL "
            f"    AND created_at > {LAST_PHASE_CHANGE}"
            ")"
        ),
        pid,
    )
    if row.scalar():
        return WorkflowPhase.IMPLANTACION

    # Adecuación · M02 MAGERIT analysis approved
    # ISSUE-W3: filtro temporal post-ultimo phase_changed event.
    row = await session.execute(
        sa_text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM magerit_analysis "
            "  WHERE project_id = :pid AND status = 'approved' "
            "    AND deleted_at IS NULL "
            f"    AND created_at > {LAST_PHASE_CHANGE}"
            ")"
        ),
        pid,
    )
    if row.scalar():
        return WorkflowPhase.ADECUACION

    # Análisis Riesgos · MAGERIT analysis iniciado pero no aprobado
    # (SAN-C MB-11.1 · sub-fase separada de diagnostico · pre-adecuacion)
    # ISSUE-W3: filtro temporal post-ultimo phase_changed event.
    row = await session.execute(
        sa_text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM magerit_analysis "
            "  WHERE project_id = :pid "
            "    AND status != 'approved' "
            "    AND deleted_at IS NULL "
            f"    AND created_at > {LAST_PHASE_CHANGE}"
            ")"
        ),
        pid,
    )
    if row.scalar():
        return WorkflowPhase.ANALISIS_RIESGOS

    # Diagnóstico · M21 diagnosis run completed
    # ISSUE-W5: diagnosis_runs sin columna deleted_at (no soft-delete · check no aplica).
    # ISSUE-W3: filtro temporal post-ultimo phase_changed event.
    row = await session.execute(
        sa_text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM diagnosis_runs "
            "  WHERE project_id = :pid AND status = 'completed' "
            f"    AND created_at > {LAST_PHASE_CHANGE}"
            ")"
        ),
        pid,
    )
    if row.scalar():
        return WorkflowPhase.DIAGNOSTICO

    # Onboarding · M16 session estado completed
    # ISSUE-W3: filtro temporal post-ultimo phase_changed event.
    row = await session.execute(
        sa_text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM onboarding_sessions "
            "  WHERE project_id = :pid AND estado = 'completed' "
            "    AND deleted_at IS NULL "
            f"    AND created_at > {LAST_PHASE_CHANGE}"
            ")"
        ),
        pid,
    )
    if row.scalar():
        return WorkflowPhase.ONBOARDING

    # Default · proyecto creado sin actividad detectada
    return WorkflowPhase.PRE_VENTA
