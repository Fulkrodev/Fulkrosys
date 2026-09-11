"""Workflow gates that enforce the correct ordering of ENS artefacts.

Each gate is a stand-alone ``async`` function that takes an
``AsyncSession`` + identifying ids and raises ``WorkflowGateError``
when the precondition is not met. Motors call them at the start of
state-changing methods so that, for example, an operator cannot
generate a Declaración de Aplicabilidad without first having signed
the Categorización, or close a project without a complete audit
dossier.

All queries run with whatever tenant context is already on the
session — callers are responsible for ``set_tenant_context`` before
invocation. The module has no SQLAlchemy model imports; it uses raw
SQL so it can be called from any motor without worrying about
circular imports.

Test shortcut: setting ``FULKRO_SKIP_WORKFLOW_GATES=1`` in the
environment disables every gate. The test ``conftest`` sets this so
existing unit tests that construct state piecemeal do not need to
satisfy the full prerequisite chain.
"""
from __future__ import annotations

import os
import uuid

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession


def _gates_enabled() -> bool:
    return os.environ.get("FULKRO_SKIP_WORKFLOW_GATES", "").strip() not in {"1", "true", "yes"}


class WorkflowGateError(Exception):
    """Raised when a motor is invoked before its prerequisites are met.

    The ``gate`` attribute identifies which gate failed so that the API
    layer can map it to a meaningful HTTP code (typically 409 Conflict).
    """

    def __init__(self, gate: str, message: str) -> None:
        super().__init__(message)
        self.gate = gate


# ---------------------------------------------------------------------------
# GATE 1: Categorización firmada antes de DdA
# ---------------------------------------------------------------------------

async def require_signed_categorization(
    session: AsyncSession, project_id: uuid.UUID
) -> None:
    """A categorisation (Motor 1) must exist for the project and have
    ``aprobado_por`` set before the DdA (Motor 3) is generated.
    """
    if not _gates_enabled():
        return
    row = await session.execute(
        sa_text(
            "SELECT COUNT(*) FROM categorizations c "
            "JOIN systems s ON s.id = c.system_id "
            "WHERE s.project_id = :pid "
            "  AND c.deleted_at IS NULL "
            "  AND c.aprobado_por IS NOT NULL"
        ),
        {"pid": str(project_id)},
    )
    if int(row.scalar() or 0) == 0:
        raise WorkflowGateError(
            gate="signed_categorization",
            message=(
                "No es posible generar la Declaración de Aplicabilidad: "
                "el proyecto no dispone aún de una categorización firmada "
                "por el Responsable de Seguridad."
            ),
        )


# ---------------------------------------------------------------------------
# GATE 2: DdA congelada antes de políticas / procedimientos / entregables
# ---------------------------------------------------------------------------

_DOC_KINDS_THAT_REQUIRE_DDA = {
    "politica", "procedimiento", "entregable",
}


async def require_frozen_dda(
    session: AsyncSession, project_id: uuid.UUID
) -> None:
    """The DdA must be generated AND frozen (approved) for the project
    before documents classified as políticas / procedimientos /
    entregables can be rendered and signed.
    """
    if not _gates_enabled():
        return
    row = await session.execute(
        sa_text(
            "SELECT COUNT(*) FROM dda_entries "
            "WHERE project_id = :pid AND deleted_at IS NULL "
            "  AND fecha_aprobacion IS NOT NULL"
        ),
        {"pid": str(project_id)},
    )
    approved = int(row.scalar() or 0)
    if approved == 0:
        raise WorkflowGateError(
            gate="frozen_dda",
            message=(
                "No es posible generar el documento: la Declaración de "
                "Aplicabilidad del proyecto aún no ha sido congelada "
                "(aprobada) por el Responsable de Seguridad."
            ),
        )


async def require_frozen_dda_if_needed(
    session: AsyncSession, project_id: uuid.UUID, document_kind: str
) -> None:
    """Variant of ``require_frozen_dda`` that only enforces the gate
    when the document ``categoria`` requires it (policies, procedures,
    deliverables). Commercial documents (C-*, P-*) bypass the gate.
    """
    if document_kind in _DOC_KINDS_THAT_REQUIRE_DDA:
        await require_frozen_dda(session, project_id)


# ---------------------------------------------------------------------------
# GATE 3: Dossier M9 completo antes de cerrar proyecto
# ---------------------------------------------------------------------------

async def require_complete_audit_prep(
    session: AsyncSession, project_id: uuid.UUID
) -> None:
    """Before a project transitions to ``CERTIFIED`` / ``RETAINER`` /
    ``ENDED_*`` state, at least one ``audit_preparation_runs`` record
    must exist with a ``completada`` status for that project.
    """
    if not _gates_enabled():
        return
    row = await session.execute(
        sa_text(
            "SELECT COUNT(*) FROM audit_preparation_runs "
            "WHERE project_id = :pid AND deleted_at IS NULL "
            "  AND LOWER(COALESCE(estado,'')) IN "
            "      ('completada','completed','ready','dossier_ready')"
        ),
        {"pid": str(project_id)},
    )
    if int(row.scalar() or 0) == 0:
        raise WorkflowGateError(
            gate="complete_audit_prep",
            message=(
                "No es posible cerrar el proyecto: no se ha completado "
                "el dossier de preparación de auditoría (Motor 9)."
            ),
        )


# ---------------------------------------------------------------------------
# GATE 4: Evidencias presentes antes de preparar dossier
# ---------------------------------------------------------------------------

async def require_some_evidence(
    session: AsyncSession, project_id: uuid.UUID, minimum: int = 1
) -> None:
    """Audit preparation cannot start if no evidence has been uploaded
    for the project.
    """
    if not _gates_enabled():
        return
    row = await session.execute(
        sa_text(
            "SELECT COUNT(*) FROM evidence "
            "WHERE project_id = :pid AND deleted_at IS NULL"
        ),
        {"pid": str(project_id)},
    )
    count = int(row.scalar() or 0)
    if count < minimum:
        raise WorkflowGateError(
            gate="require_some_evidence",
            message=(
                f"No es posible preparar la auditoría: el proyecto "
                f"dispone de {count} evidencia(s), se requiere al menos "
                f"{minimum}."
            ),
        )


# ---------------------------------------------------------------------------
# GATE 5: AR MAGERIT completo antes de obligaciones
# ---------------------------------------------------------------------------

async def require_magerit_analysis(
    session: AsyncSession, project_id: uuid.UUID
) -> None:
    """The MAGERIT v3 risk analysis (Motor 2) must exist for the project
    before the Obligations engine instantiates the action plan.
    """
    if not _gates_enabled():
        return
    # O2 · misma regla que el resto del sistema, leida de su unica fuente.
    from backend.app.motors.m02_magerit.analisis_vigente import analisis_vigente

    if await analisis_vigente(session, project_id) is None:
        raise WorkflowGateError(
            gate="magerit_analysis",
            message=(
                "No es posible instanciar el plan de obligaciones: "
                "el análisis de riesgos MAGERIT v3 aún no ha sido "
                "ejecutado para el proyecto."
            ),
        )


# ---------------------------------------------------------------------------
# GATE 6: Pentest solo tras aprobación cliente
# ---------------------------------------------------------------------------

async def require_pentest_authorisation(
    session: AsyncSession, project_id: uuid.UUID
) -> None:
    """No pentesting run can start without an explicit authorisation
    magic link approved by the client (Motor 12 purpose
    ``autorizar_accion_tecnica``).
    """
    if not _gates_enabled():
        return
    row = await session.execute(
        sa_text(
            "SELECT COUNT(*) FROM magic_links "
            "WHERE project_id = :pid "
            "  AND tipo_operacion = 'autorizar_accion_tecnica' "
            "  AND usos > 0 "
            "  AND revoked_at IS NULL"
        ),
        {"pid": str(project_id)},
    )
    if int(row.scalar() or 0) == 0:
        raise WorkflowGateError(
            gate="pentest_authorisation",
            message=(
                "No es posible iniciar el pentesting: falta la "
                "autorización del cliente mediante enlace seguro."
            ),
        )


# ---------------------------------------------------------------------------
# GATE 7 (#40 · FRENTE D): Simulacro pre-ENAC limpio (sin NC mayores) antes de
# solicitar la auditoría ENAC o firmar la Declaración de Conformidad. + (#43)
# exigir que exista un simulacro ejecutado antes de marcar la auditoría interna
# como completada. Premisa #1: que el auditor ENAC apruebe ANTES de ir a la ENAC.
# ---------------------------------------------------------------------------

# Transiciones del state machine m_audit_accompaniment que materializan
# "solicitud ENAC / firma de conformidad" (bloquean si hay NC mayores abiertas).
_ENAC_REQUEST_OR_SIGN_STATES = frozenset({
    "enac_audit_scheduled",   # MEDIA/ALTA · solicitar auditoría ENAC
    "declaration_signed",     # BÁSICA · firmar la Declaración de Conformidad
})
# Transición que exige (al menos) un simulacro ejecutado (#43).
_INTERNAL_AUDIT_COMPLETED_STATE = "internal_audit_completed"
_SIMULACRO_REPORT_EVENT = "simulacro.pre_enac.report_generated"


async def require_clean_audit_sim(
    session: AsyncSession,
    project_id: uuid.UUID,
    *,
    target_state: str,
    allow_open_nc: bool = False,
) -> None:
    """GATE-7 · gobierna el parón pre-auditoría sobre el último simulacro.

    - target_state ∈ {enac_audit_scheduled, declaration_signed} (#40):
      exige un simulacro ejecutado Y con 0 NC mayores (critical). El override
      administrativo justificado (``allow_open_nc=True``) permite continuar
      (escape-hatch · queda trazado por el caller en audit_log).
    - target_state == internal_audit_completed (#43): exige (al menos) un
      simulacro ejecutado.
    - cualquier otra transición: no-op.

    Lee el ÚLTIMO ``simulacro.pre_enac.report_generated`` del proyecto y sus
    conteos reales (``critical_gaps``) del payload (#42). Raw SQL · sin imports
    de modelos (evita circular · llamable desde cualquier motor).
    """
    if not _gates_enabled():
        return
    requires_sim = (
        target_state in _ENAC_REQUEST_OR_SIGN_STATES
        or target_state == _INTERNAL_AUDIT_COMPLETED_STATE
    )
    if not requires_sim:
        return

    row = (await session.execute(
        sa_text(
            "SELECT payload_new FROM audit_log "
            "WHERE accion = :acc AND project_id = :pid "
            "ORDER BY seq DESC LIMIT 1"
        ),
        {"acc": _SIMULACRO_REPORT_EVENT, "pid": str(project_id)},
    )).first()

    if row is None:
        raise WorkflowGateError(
            gate="clean_audit_sim",
            message=(
                "Debes ejecutar el Simulacro pre-ENAC antes de "
                + (
                    "solicitar la auditoría ENAC o firmar la Declaración de "
                    "Conformidad."
                    if target_state in _ENAC_REQUEST_OR_SIGN_STATES
                    else "marcar la auditoría interna como completada."
                )
            ),
        )

    # #43: para internal_audit_completed basta con que exista un simulacro.
    if target_state == _INTERNAL_AUDIT_COMPLETED_STATE:
        return

    # #40: solicitud ENAC / firma → 0 NC mayores (critical) salvo override admin.
    payload = row[0]
    if isinstance(payload, str):
        import json as _json
        try:
            payload = _json.loads(payload or "{}")
        except ValueError:
            payload = {}
    critical = int((payload or {}).get("critical_gaps", 0) or 0)
    if critical > 0 and not allow_open_nc:
        raise WorkflowGateError(
            gate="clean_audit_sim",
            message=(
                f"No se puede solicitar la auditoría ENAC ni firmar la "
                f"conformidad: el último simulacro tiene {critical} no "
                f"conformidad(es) mayor(es) abierta(s). Resuélvelas (cierra los "
                f"bucles correctivos) o aplica el override administrativo "
                f"justificado."
            ),
        )
