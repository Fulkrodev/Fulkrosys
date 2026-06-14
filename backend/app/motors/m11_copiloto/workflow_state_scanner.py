"""Workflow state scanner · pure functional service (Sesión 3B-2B.8 Phase 1D).

compute_workflow_state(): mirror compute_dda_evidence_gaps Phase C3 pattern.

Reusable cross-consumer:
  - m11_copiloto · /copilot/hint endpoint (Phase 1D.2)
  - Sesión 3B-2B.9 admin proactivity dashboards
  - Sesión 3B-2B.10 simulacro pre-ENAC engine
  - Sesión 3B-2B.7 cloud connections completeness gates

OPS-026 DRY · NO duplicar lógica existing:
  - REUSE backend.app.core.workflow_phase.WorkflowPhase enum (ADR-026 · 10 fases)
  - REUSE backend.app.core.workflow_state.phase.get_current_phase (CASCADE fallback)

Doctrinas:
  - Pure functional · NO HTTP coupling
  - NO ORM coupling (raw SQL preferred · async)
  - NO side effects (NO emit · NO write)
  - JSON-serializable return (dataclass.asdict() friendly)
  - Determinism: dado mismo estado DB → mismo output
  - R29 friendly Spanish per cliente_description
  - R30 admin tutor cronológico per admin_description
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Literal, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.workflow_phase import WorkflowPhase
from backend.app.core.workflow_state.phase import get_current_phase


Role = Literal["admin", "cliente"]
Priority = Literal["urgent", "normal", "low"]
WaitingOn = Literal["admin", "cliente", "external_auditor", "system"]


_PRIORITY_WEIGHT: dict[str, int] = {"urgent": 3, "normal": 2, "low": 1}


# ════════════════════════════════════════════════════════════════════
# FASE 0 · Gobierno (P10-F09 · Ejecutable 8 Batch 2)
# ════════════════════════════════════════════════════════════════════
# Opción A · solo admin · el next_step de gobierno (kickoff→alcance→roles→
# comité→plan, branch por categoría) se inyecta como acción urgent ANTES de
# la genérica de fase mientras fase0_completa=False, en fases tempranas.
# Composer read-only `compute_fase0_governance_state` (m17) · import lazy.

# Fases donde el gobierno está vivo · hasta ADECUACION inclusive (el Plan de
# Adecuación E-150 cierra en ADECUACION).
_FASE0_PHASES: frozenset[WorkflowPhase] = frozenset({
    WorkflowPhase.PRE_VENTA,
    WorkflowPhase.ONBOARDING,
    WorkflowPhase.DIAGNOSTICO,
    WorkflowPhase.ANALISIS_RIESGOS,
    WorkflowPhase.ADECUACION,
})

# #22 Ola 5 · fases donde tiene sentido cruzar el semáforo por medida (#20):
# la evidencia se recolecta en implantación → verificación. Antes/después no
# hay todavía SoA con evidencia que reclamar.
_EVIDENCE_PHASES: frozenset[WorkflowPhase] = frozenset({
    WorkflowPhase.IMPLANTACION,
    WorkflowPhase.DDA_FINAL,
    WorkflowPhase.VERIFICACION,
})

# Máximo de medidas con gap que el hint nombra (guard de performance · NO se
# llama a compute_control_status 73× · una sola SQL acotada).
_EVIDENCE_GAP_LIMIT = 3

# Target admin por paso · rutas REALES verificadas en frontend (Batch 2):
#   kickoff → onboarding (arranque proyecto · project-scoped)
#   alcance (E-155) → documents (IDMS · genera Documento de Alcance)
#   roles (E-002 + separación) → equipo (EnsRoleAssignModal · asigna roles ENS)
#   comite (E-003) → /admin/meetings (m_meetings · top-level cross-cliente)
#   plan (E-150) → plan (PdaGeneratorButton · generador Plan de Adecuación)
_GOV_STEP_URL: dict[str, str] = {
    "kickoff": "/admin/projects/{project_id}/onboarding",
    "alcance": "/admin/projects/{project_id}/documents",
    "roles": "/admin/projects/{project_id}/equipo",
    "comite": "/admin/meetings",
    "plan": "/admin/projects/{project_id}/plan",
}

# Label R30 admin tutor por paso (cronológico · primer principios).
_GOV_STEP_LABEL: dict[str, str] = {
    "kickoff": "Reunión de arranque del proyecto",
    "alcance": "Documento de Alcance del SGSI (E-155)",
    "roles": "Nombramiento de roles ENS (E-002)",
    "comite": "Constitución del Comité de Seguridad (E-003)",
    "plan": "Plan de adecuación al ENS (E-150)",
}


@dataclass
class ActionHint:
    """Acción contextual sugerida per fase + role."""

    motor: str  # m01 · m02 · m03 · etc · "system" para acciones generales
    action: str  # 'complete_categorization' · 'sign_dda' · etc
    description_cliente: str  # R29 friendly (cliente-facing · NO admin lingo)
    description_admin: str  # R30 admin tutor (Marcos-facing detail)
    priority: Priority
    target_url: str  # cliente portal route OR admin route


@dataclass
class PhaseProgress:
    """Estado per-fase del workflow lifecycle 10 fases."""

    phase: str  # WorkflowPhase value
    status: Literal["not_started", "in_progress", "completed"]
    completion_percentage: int  # 0-100


@dataclass
class Blocker:
    """Bloqueo detectado · waiting on alguna acción/parte."""

    motor: str
    description: str
    waiting_on: WaitingOn


@dataclass
class WorkflowState:
    """Estado workflow proyecto · JSON-serializable via asdict()."""

    project_id: str
    current_phase: str  # WorkflowPhase value
    phase_progress: list[PhaseProgress]
    next_admin_actions: list[ActionHint]
    next_cliente_actions: list[ActionHint]
    blockers: list[Blocker]
    last_updated_at: str  # ISO-8601
    categoria_objetivo: Optional[str] = None  # 'basica' · 'media' · 'alta'
    audit_passed_at: Optional[str] = None  # ISO-8601
    # #22 Ola 5 · medidas aplicables SIN evidencia válida (top-N · admin R30).
    # Códigos ENS (op.acc.5 …) = jerga de admin · NUNCA se exponen al cliente
    # (R29). Solo se computa en fases de evidencia + role admin.
    evidence_gap_measures: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """JSON-serializable dict · asdict friendly."""
        return asdict(self)


@dataclass
class WorkflowScannerOptions:
    """Opciones del scanner (defaults safe)."""

    include_blockers: bool = True
    include_phase_progress: bool = True
    role_filter: Optional[Role] = None  # None → both


# ════════════════════════════════════════════════════════════════════
# Action catalogs per WorkflowPhase (deterministic · NO LLM)
# ════════════════════════════════════════════════════════════════════
# Cada fase emite acciones canónicas según role · descripciones R29/R30.

_PHASE_ACTIONS: dict[WorkflowPhase, dict[str, list[ActionHint]]] = {
    WorkflowPhase.PRE_VENTA: {
        "admin": [
            ActionHint(
                motor="m14",
                action="prepare_contract",
                description_cliente="",
                description_admin=(
                    "Prepara propuesta + contrato M14 con cliente · BOE refs + "
                    "scope MEDIA/BÁSICA según diagnóstico. Wizard /admin/projects/{id}/contratos."
                ),
                priority="urgent",
                target_url="/admin/projects/{project_id}/contratos",
            ),
        ],
        "cliente": [],
    },
    WorkflowPhase.ONBOARDING: {
        "admin": [
            ActionHint(
                motor="m16",
                action="review_onboarding_responses",
                description_cliente="",
                description_admin=(
                    "Revisa respuestas onboarding cliente · ajusta dimensiones "
                    "ENS si discrepancias detectadas. Page /admin/projects/{id}/onboarding."
                ),
                priority="normal",
                target_url="/admin/projects/{project_id}/onboarding",
            ),
        ],
        "cliente": [
            ActionHint(
                motor="m16",
                action="complete_onboarding",
                description_cliente=(
                    "Completa el cuestionario de onboarding · 5-10 minutos · "
                    "Marcos lo necesita para arrancar tu proyecto ENS."
                ),
                description_admin="",
                priority="urgent",
                target_url="/client-portal/onboarding",
            ),
        ],
    },
    WorkflowPhase.DIAGNOSTICO: {
        "admin": [
            ActionHint(
                motor="m21",
                action="run_diagnosis",
                description_cliente="",
                description_admin=(
                    "Ejecuta diagnóstico M21 inicial · maturity scoring "
                    "(L0-L5) + gaps detected. Page /admin/projects/{id}/diagnostico."
                ),
                priority="urgent",
                target_url="/admin/projects/{project_id}/diagnosis",
            ),
        ],
        "cliente": [
            ActionHint(
                motor="system",
                action="awaiting_marcos_diagnosis",
                description_cliente=(
                    "Marcos está analizando tu situación actual · sin acciones "
                    "pendientes por tu parte. Te avisará cuando esté listo."
                ),
                description_admin="",
                priority="low",
                target_url="/client-portal/",
            ),
        ],
    },
    WorkflowPhase.ANALISIS_RIESGOS: {
        "admin": [
            ActionHint(
                motor="m02",
                action="register_magerit_assets",
                description_cliente="",
                description_admin=(
                    "Carga activos MAGERIT M02 · servicios · datos · valoración "
                    "I/C/T/A/D. Cliente revisa cuando esté ready. Page "
                    "/admin/projects/{id}/magerit."
                ),
                priority="urgent",
                target_url="/admin/projects/{project_id}/magerit",
            ),
        ],
        "cliente": [
            ActionHint(
                motor="m02",
                action="review_magerit_preview",
                description_cliente=(
                    "Marcos está cargando el inventario de tus sistemas. "
                    "Puedes revisar el avance cuando quieras."
                ),
                description_admin="",
                priority="low",
                target_url="/client-portal/magerit",
            ),
        ],
    },
    WorkflowPhase.ADECUACION: {
        "admin": [
            ActionHint(
                motor="m01",
                action="finalize_categorization",
                description_cliente="",
                description_admin=(
                    "Finaliza categorización ENS sistema-por-sistema M01 + "
                    "firma acta categorización. Cliente revisa post-firma."
                ),
                priority="urgent",
                target_url="/admin/projects/{project_id}/dimensiones",
            ),
            ActionHint(
                motor="m03",
                action="draft_dda",
                description_cliente="",
                description_admin=(
                    "Genera borrador DdA M03 cruzando MAGERIT × Anexo II "
                    "medidas aplicables. Wizard /admin/projects/{id}/dda."
                ),
                priority="normal",
                target_url="/admin/projects/{project_id}/dda",
            ),
        ],
        "cliente": [
            ActionHint(
                motor="m01",
                action="review_categorization",
                description_cliente=(
                    "Marcos completó la categorización ENS de tus sistemas. "
                    "Revísala cuando puedas · sin prisa."
                ),
                description_admin="",
                priority="normal",
                target_url="/client-portal/categorizacion",
            ),
        ],
    },
    WorkflowPhase.IMPLANTACION: {
        "admin": [
            ActionHint(
                motor="m04",
                action="execute_action_plan",
                description_cliente="",
                description_admin=(
                    "Ejecuta plan de acción M04 · genera/revisa políticas M06 "
                    "+ procedimientos. Page /admin/projects/{id}/plan."
                ),
                priority="urgent",
                target_url="/admin/projects/{project_id}/plan",
            ),
        ],
        "cliente": [
            ActionHint(
                motor="m03",
                action="sign_dda",
                description_cliente=(
                    "Tu DdA (Declaración de Aplicabilidad) está lista para tu "
                    "firma. Esto formaliza qué medidas ENS aplican a tus sistemas."
                ),
                description_admin="",
                priority="urgent",
                target_url="/client-portal/dda",
            ),
        ],
    },
    WorkflowPhase.DDA_FINAL: {
        "admin": [
            ActionHint(
                motor="m07",
                action="collect_evidence",
                description_cliente="",
                description_admin=(
                    "Recolecta evidencias M07 por medida implementada · "
                    "trazabilidad ENAC. Page /admin/projects/{id}/evidencias."
                ),
                priority="urgent",
                target_url="/admin/projects/{project_id}/evidence",
            ),
        ],
        "cliente": [
            ActionHint(
                motor="m07",
                action="upload_pending_evidence",
                description_cliente=(
                    "Marcos te pedirá algunas evidencias específicas. "
                    "Te llegarán via 'Subir documentos' cuando toque."
                ),
                description_admin="",
                priority="normal",
                target_url="/client-portal/files",
            ),
        ],
    },
    WorkflowPhase.VERIFICACION: {
        "admin": [
            ActionHint(
                motor="m08",
                action="run_verification",
                description_cliente="",
                description_admin=(
                    "Ejecuta verificación M08 técnica · MCPs + pentest si ALTA. "
                    "Hallazgos resueltos pre-conformidad."
                ),
                priority="urgent",
                target_url="/admin/projects/{project_id}/verificacion",
            ),
        ],
        "cliente": [
            ActionHint(
                motor="system",
                action="awaiting_verification",
                description_cliente=(
                    "Marcos está verificando técnicamente las medidas implementadas. "
                    "Sin acciones pendientes por tu parte."
                ),
                description_admin="",
                priority="low",
                target_url="/client-portal/",
            ),
        ],
    },
    WorkflowPhase.CONFORMIDAD: {
        "admin": [
            ActionHint(
                motor="m09",
                action="prepare_audit_dossier",
                description_cliente="",
                description_admin=(
                    "Prepara dossier M09 para auditoría ENAC · 10 docs canonical "
                    "+ MANIFEST.json firmado Ed25519. Auditor portal acceso."
                ),
                priority="urgent",
                target_url="/admin/projects/{project_id}/dossier",
            ),
        ],
        "cliente": [
            ActionHint(
                motor="m09",
                action="awaiting_external_audit",
                description_cliente=(
                    "Dossier listo para auditoría externa ENAC. El auditor "
                    "contactará a Marcos directamente."
                ),
                description_admin="",
                priority="low",
                target_url="/client-portal/conformidad",
            ),
        ],
    },
    WorkflowPhase.RETAINER_CIERRE: {
        "admin": [
            ActionHint(
                motor="m23",
                action="offer_retainer",
                description_cliente="",
                description_admin=(
                    "Ofrece retainer post-cert M23 · R_BÁSICO/R_MEDIO/R_ALTO según "
                    "categoría. Page /admin/projects/{id}/retainer."
                ),
                priority="urgent",
                target_url="/admin/projects/{project_id}/retainer",
            ),
        ],
        "cliente": [
            ActionHint(
                motor="m23",
                action="review_retainer_offer",
                description_cliente=(
                    "¡Felicidades! Tu certificación ENS está completa. Marcos te "
                    "propondrá un retainer para mantener el cumplimiento al día."
                ),
                description_admin="",
                priority="normal",
                target_url="/client-portal/retainer-checkin",
            ),
        ],
    },
}


# ════════════════════════════════════════════════════════════════════
# Helpers (private)
# ════════════════════════════════════════════════════════════════════


def _interpolate_url(url: str, project_id: uuid.UUID) -> str:
    """Substitute {project_id} placeholder · keep relative URL."""
    return url.replace("{project_id}", str(project_id))


def _interpolate_actions(
    actions: list[ActionHint], project_id: uuid.UUID,
) -> list[ActionHint]:
    """Apply project_id substitution per action target_url."""
    return [
        ActionHint(
            motor=a.motor,
            action=a.action,
            description_cliente=a.description_cliente,
            description_admin=a.description_admin,
            priority=a.priority,
            target_url=_interpolate_url(a.target_url, project_id),
        )
        for a in actions
    ]


def _build_governance_hint(
    governance: dict, project_id: uuid.UUID,
) -> Optional[ActionHint]:
    """ActionHint del siguiente paso de gobierno FASE 0 (Batch 2 · solo admin).

    Pure · None si next_step desconocido (defensivo · no rompe el scan).
    target_url interpolado (mirror _interpolate_url). description_cliente=""
    (gobierno NO se expone a cliente · solo admin R30).
    """
    step = governance.get("next_step")
    if step not in _GOV_STEP_URL:
        return None
    label = _GOV_STEP_LABEL.get(step, step)
    completed = governance.get("completed_steps", 0)
    total = governance.get("total_steps", 0)
    categoria = governance.get("categoria", "")
    return ActionHint(
        motor="m17",
        action=f"fase0_{step}",
        description_cliente="",
        description_admin=(
            f"FASE 0 · Gobierno ({completed}/{total} · {categoria}) · "
            f"Siguiente paso: {label}. Pendiente antes de avanzar el "
            f"recorrido ENS."
        ),
        priority="urgent",
        target_url=_interpolate_url(_GOV_STEP_URL[step], project_id),
    )


def _current_phase_pct(governance: Optional[dict]) -> int:
    """% real de la fase en curso (Ola C · progreso real 0→100%).

    Cuando hay datos de gobierno FASE 0 (``completed_steps``/``total_steps``)
    devuelve el ratio REAL (clamp 1..99 · una fase en curso nunca es 0 ni 100).
    Si no hay señal real (fases posteriores · rol cliente · gobierno completo)
    cae al heurístico 50 — el refinamiento per-fase con conteos reales de cada
    motor queda como Future-X (`workflow-scanner-percentage-refinement`).
    """
    if governance:
        total = governance.get("total_steps", 0) or 0
        completed = governance.get("completed_steps", 0) or 0
        if total > 0:
            return max(1, min(99, round(100 * completed / total)))
    return 50


async def _compute_phase_progress(
    db: AsyncSession,
    project_id: uuid.UUID,
    current: WorkflowPhase,
    governance: Optional[dict] = None,
) -> list[PhaseProgress]:
    """Marca fases del lifecycle · completed antes de current · in_progress
    en current · not_started después.

    Determinism: order canonical via WorkflowPhase.ordered(). El % de la fase
    en curso es REAL cuando hay gobierno FASE 0 (ver `_current_phase_pct`).
    """
    ordered = WorkflowPhase.ordered()
    try:
        current_idx = ordered.index(current)
    except ValueError:
        current_idx = 0

    current_pct = _current_phase_pct(governance)

    result: list[PhaseProgress] = []
    for i, phase in enumerate(ordered):
        if i < current_idx:
            status: Literal["not_started", "in_progress", "completed"] = "completed"
            pct = 100
        elif i == current_idx:
            status = "in_progress"
            pct = current_pct
        else:
            status = "not_started"
            pct = 0
        result.append(
            PhaseProgress(phase=phase.value, status=status, completion_percentage=pct),
        )
    return result


async def _detect_blockers(
    db: AsyncSession,
    project_id: uuid.UUID,
    current: WorkflowPhase,
    categoria: Optional[str],
    governance: Optional[dict] = None,
) -> list[Blocker]:
    """Detect blockers cross-motor · waiting on parts (admin · cliente · external).

    Deterministic queries · NO LLM. Each blocker is empirical fact (data state).
    """
    blockers: list[Blocker] = []

    if current == WorkflowPhase.IMPLANTACION:
        # DdA pendiente firma cliente: dda_entries existen pero
        # dda_project_signatures sin signature_magic_link_id confirmado.
        row = await db.execute(
            text(
                "SELECT EXISTS ("
                "  SELECT 1 FROM dda_entries "
                "  WHERE project_id = :pid AND deleted_at IS NULL"
                ") AND NOT EXISTS ("
                "  SELECT 1 FROM dda_project_signatures "
                "  WHERE project_id = :pid "
                "    AND signature_magic_link_id IS NOT NULL"
                ")"
            ),
            {"pid": str(project_id)},
        )
        if row.scalar():
            blockers.append(Blocker(
                motor="m03",
                description="DdA pendiente de firma cliente",
                waiting_on="cliente",
            ))

    if categoria in ("alta", "ALTA"):
        if current in (
            WorkflowPhase.IMPLANTACION,
            WorkflowPhase.DDA_FINAL,
            WorkflowPhase.VERIFICACION,
        ):
            # M08 VerificationRun semantic = pentest authorization
            # (atom 5.3.A · NO tabla pentest_authorizations dedicada).
            row = await db.execute(
                text(
                    "SELECT EXISTS ("
                    "  SELECT 1 FROM verification_runs "
                    "  WHERE project_id = :pid "
                    "    AND authorization_signed_at IS NOT NULL "
                    "    AND deleted_at IS NULL"
                    ")"
                ),
                {"pid": str(project_id)},
            )
            has_pentest_auth = bool(row.scalar())
            if not has_pentest_auth:
                blockers.append(Blocker(
                    motor="m08",
                    description="Pentest cliente authorization pendiente (ALTA category)",
                    waiting_on="cliente",
                ))

    if current == WorkflowPhase.CONFORMIDAD:
        blockers.append(Blocker(
            motor="m09",
            description="Esperando review auditor ENAC externo",
            waiting_on="external_auditor",
        ))

    # FASE 0 gobierno blockers (Batch 2 · additive · default None → no-op).
    # NO se exponen en UI en FASE 1 (quedan en WorkflowState.blockers para
    # consumidores no-UI: nudge_scheduler + simulacro). FASE 2 los renderiza
    # en CopilotoAdminSidebar via WorkflowHintResponse extendido.
    if governance is not None:
        steps = governance.get("steps", [])
        sep = next(
            (s.get("separacion") for s in steps if s.get("key") == "roles"),
            None,
        )
        if sep and sep.get("obligatoria") and not sep.get("compliant"):
            blockers.append(Blocker(
                motor="m30",
                description=(
                    "Separación RSeg≠RSis no conforme (obligatoria MEDIA/ALTA)"
                ),
                waiting_on="admin",
            ))
        cad = next(
            (s.get("cadencia") for s in steps if s.get("key") == "comite"),
            None,
        )
        if cad and cad.get("alerta_pre_auditoria"):
            blockers.append(Blocker(
                motor="m_meetings",
                description=(
                    "Comité sin cadencia/actas suficientes pre-auditoría"
                ),
                waiting_on="admin",
            ))

    return blockers


async def _resolve_project_meta(
    db: AsyncSession, project_id: uuid.UUID,
) -> tuple[Optional[str], Optional[datetime]]:
    """Lookup categoria_objetivo + audit_passed_at del project."""
    row = (
        await db.execute(
            text(
                "SELECT categoria_objetivo, audit_passed_at "
                "FROM projects WHERE id = :pid"
            ),
            {"pid": str(project_id)},
        )
    ).fetchone()
    if not row:
        return None, None
    return row[0], row[1]


async def _detect_evidence_gap_measures(
    db: AsyncSession, project_id: uuid.UUID, *, limit: int = _EVIDENCE_GAP_LIMIT,
) -> list[str]:
    """#22/#20 · top-N medidas aplicables SIN evidencia válida (semáforo cruzado).

    Reusa el criterio Evidence-based de #20 (control_status_service ·
    `scan_status = 'clean'` = evidencia validada). En vez de llamar a
    compute_control_status 73× (lento), una SOLA SQL acotada a `limit`:
    medidas de la SoA aplicables (aplicabilidad != 'no_aplica') que NO tienen
    ninguna evidencia 'clean'. Determinista (orden por measure_code).

    Permite al copiloto admin decir "te faltan evidencias en op.acc.5, op.exp.8"
    (el "hecho cuando" del punto #22). Códigos ENS = R30 admin · NO cliente.
    """
    # dda_entries enlaza la medida vía measure_id (FK) → ens_measures.codigo
    # (NO tiene columna measure_code · audit empírico). La evidencia sí lleva
    # measure_code (string · el vínculo real que usa #20).
    rows = (await db.execute(text(
        """
        SELECT m.codigo
        FROM dda_entries d
        JOIN ens_measures m ON m.id = d.measure_id
        WHERE d.project_id = :pid
          AND d.deleted_at IS NULL
          AND COALESCE(d.aplicabilidad, 'aplica') <> 'no_aplica'
          AND NOT EXISTS (
              SELECT 1 FROM evidence e
              WHERE e.project_id = d.project_id
                AND (e.measure_code = m.codigo OR e.measure_id = m.id)
                AND e.deleted_at IS NULL
                AND e.scan_status = 'clean'
          )
        ORDER BY m.codigo
        LIMIT :lim
        """
    ), {"pid": str(project_id), "lim": limit})).fetchall()
    return [r[0] for r in rows]


def _apply_level_adaptations(
    actions: list[ActionHint],
    current: WorkflowPhase,
    categoria: Optional[str],
) -> list[ActionHint]:
    """#22 Ola 5 · adapta el texto de las acciones admin por nivel ENS.

    El comportamiento de cierre/verificación NO puede ir hardcodeado: BÁSICA es
    autodeclaración 808/809 (sin ENAC, sin pentest), MEDIA exige vuln-scan, ALTA
    exige pentest CPSTIC + Red Team (tabla de niveles del plan maestro). Solo
    reescribe `description_admin` en los puntos que realmente difieren por nivel
    (CONFORMIDAD m09 · VERIFICACION m08) · el resto se mantiene.
    """
    cat = (categoria or "").strip().lower()
    if cat not in ("basica", "media", "alta"):
        return actions

    adapted: list[ActionHint] = []
    for a in actions:
        desc = a.description_admin
        if current == WorkflowPhase.CONFORMIDAD and a.motor == "m09":
            if cat == "basica":
                desc = (
                    "Prepara la Declaración de Conformidad · BÁSICA es "
                    "AUTODECLARACIÓN (CCN-STIC 808/809 · NO requiere auditoría "
                    "ENAC). Firma de Dirección + comunicación al CCN."
                )
            else:
                desc = (
                    f"Prepara el dossier M09 para auditoría ENAC ({cat.upper()} "
                    "requiere auditor acreditado) · 10 docs canonical + "
                    "MANIFEST.json firmado Ed25519."
                )
        elif current == WorkflowPhase.VERIFICACION and a.motor == "m08":
            if cat == "basica":
                desc = (
                    "Verificación técnica M08 · BÁSICA: revisión de medidas. "
                    "NO requiere vuln-scan ni pentest obligatorios."
                )
            elif cat == "media":
                desc = (
                    "Ejecuta verificación M08 · MEDIA: vuln-scan OBLIGATORIO. "
                    "Pentest solo si se contrató (opcional)."
                )
            else:  # alta
                desc = (
                    "Ejecuta verificación M08 · ALTA: vuln-scan + pentest "
                    "OBLIGATORIO (CPSTIC) + Red Team."
                )

        if desc != a.description_admin:
            adapted.append(ActionHint(
                motor=a.motor,
                action=a.action,
                description_cliente=a.description_cliente,
                description_admin=desc,
                priority=a.priority,
                target_url=a.target_url,
            ))
        else:
            adapted.append(a)
    return adapted


# ════════════════════════════════════════════════════════════════════
# Public API
# ════════════════════════════════════════════════════════════════════


async def compute_workflow_state(
    db: AsyncSession,
    project_id: uuid.UUID,
    options: Optional[WorkflowScannerOptions] = None,
) -> WorkflowState:
    """Compute workflow state per project · pure functional · reusable.

    Pattern mirror compute_dda_evidence_gaps Phase C3:
      - NO HTTP coupling · accepts db session + project_id
      - NO ORM coupling preferred (raw SQL faster · async)
      - NO side effects (NO INSERT · NO emit)
      - JSON-serializable return (asdict-friendly)
      - Deterministic (mismo input DB → mismo output)

    Reusable consumers (Sesión 3B-2B.8+ cumulative):
      - m11_copiloto · /copilot/hint endpoint (Phase 1D.2)
      - Sesión 3B-2B.9 admin proactivity dashboards
      - Sesión 3B-2B.10 simulacro pre-ENAC gap engine
    """
    opts = options or WorkflowScannerOptions()

    current = await get_current_phase(db, project_id)
    categoria, audit_passed_at = await _resolve_project_meta(db, project_id)

    phase_actions = _PHASE_ACTIONS.get(current, {"admin": [], "cliente": []})
    next_admin_actions = (
        _interpolate_actions(phase_actions.get("admin", []), project_id)
        if opts.role_filter in (None, "admin")
        else []
    )
    next_cliente_actions = (
        _interpolate_actions(phase_actions.get("cliente", []), project_id)
        if opts.role_filter in (None, "cliente")
        else []
    )

    # FASE 0 gobierno (Batch 2 · Opción A · solo admin · fases tempranas).
    # Inyecta el next_step de gobierno ANTES de la genérica de fase (prepend
    # urgent → top_action_for_role lo elige) mientras fase0_completa=False.
    # Import lazy (mirror m17/api.py:167) → scanner sigue dependency-light a
    # nivel de módulo · sin ciclo (m30/m_meetings NO importan m11/m17).
    # Solo se computa para role admin → cliente nunca lo dispara (visibilidad
    # + perf · el composer toca m30 + m_meetings).
    governance: Optional[dict] = None
    if opts.role_filter in (None, "admin") and current in _FASE0_PHASES:
        from backend.app.motors.m17_planning.fase0_governance import (
            compute_fase0_governance_state,
        )
        governance = await compute_fase0_governance_state(db, project_id)
        if governance and not governance.get("fase0_completa"):
            gov_hint = _build_governance_hint(governance, project_id)
            if gov_hint is not None:
                next_admin_actions = [gov_hint, *next_admin_actions]

    # #22 · adaptación por nivel ENS (autodeclaración BÁSICA · vuln-scan MEDIA ·
    # pentest ALTA) sobre las acciones admin · NO se hardcodea el cierre.
    next_admin_actions = _apply_level_adaptations(
        next_admin_actions, current, categoria,
    )

    phase_progress = (
        await _compute_phase_progress(db, project_id, current, governance)
        if opts.include_phase_progress
        else []
    )

    blockers = (
        await _detect_blockers(db, project_id, current, categoria, governance)
        if opts.include_blockers
        else []
    )

    # #22 · cruce del semáforo por medida (#20) · top-N medidas sin evidencia
    # válida · solo admin (códigos ENS = R30 · NUNCA cliente) y solo en fases
    # de evidencia. Backward-compat: si falla → lista vacía (NO rompe el scan).
    evidence_gaps: list[str] = []
    if opts.role_filter in (None, "admin") and current in _EVIDENCE_PHASES:
        # SAVEPOINT: si la detección falla NO aborta la transacción exterior
        # (asyncpg marca la tx como abortada tras un error · el nested la aísla).
        try:
            async with db.begin_nested():
                evidence_gaps = await _detect_evidence_gap_measures(db, project_id)
        except Exception:
            logging.getLogger(__name__).exception(
                "evidence gap detection failed · project_id=%s", project_id,
            )
            evidence_gaps = []

    return WorkflowState(
        project_id=str(project_id),
        current_phase=current.value,
        phase_progress=phase_progress,
        next_admin_actions=next_admin_actions,
        next_cliente_actions=next_cliente_actions,
        blockers=blockers,
        last_updated_at=datetime.utcnow().isoformat() + "Z",
        categoria_objetivo=categoria,
        audit_passed_at=audit_passed_at.isoformat() if audit_passed_at else None,
        evidence_gap_measures=evidence_gaps,
    )


def top_action_for_role(
    state: WorkflowState, role: Role,
) -> Optional[ActionHint]:
    """Devuelve la acción de mayor prioridad para el role · None si vacío.

    Pure helper · usable cross-consumer. Priority order: urgent > normal > low.
    Tiebreaker: orden definido en _PHASE_ACTIONS (insertion-order Python 3.7+).
    """
    actions = (
        state.next_cliente_actions if role == "cliente" else state.next_admin_actions
    )
    if not actions:
        return None
    return max(actions, key=lambda a: _PRIORITY_WEIGHT.get(a.priority, 0))
