"""Templates Python constants per WorkflowPhase (FASE 8 · ADR-026).

ADR-025 coherente: NO crear tablas nuevas. action/task templates como
constants Python lookup runtime per fase. Estable cross-deploys.

TODO-PHASE-TEMPLATES-DB-001 [BAJA · post-deploy]: migrar a tabla
``phase_action_templates`` si se requiere edición dinámica per cliente.

Estructura:
- ACTION_TEMPLATES · 3-5 actions priorizadas per fase para get_next_actions
- TASK_TEMPLATES   · 3-7 tasks expected per fase para get_phase_tasks

Cada item es un dataclass simple sin lógica · transformado a NextAction /
TaskItem (Pydantic) por las funciones derive_state.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from backend.app.core.workflow_phase import WorkflowPhase


@dataclass(frozen=True)
class ActionTemplateDef:
    """Acción priorizada cliente per fase."""

    action_id: str
    label: str
    motor: str
    endpoint: str | None
    priority: int
    estimated_minutes: int


@dataclass(frozen=True)
class TaskTemplateDef:
    """Tarea expected per fase con orden recomendado.

    8.WORKFLOW.CALIBRATE W2: ``completion_signal`` mapea task → query motor
    real verificable. Si None, task es manual tracking (UI cliente muestra
    "manual_tracking" en lugar de fingir status). Signals registrados en
    workflow_state._TASK_SIGNAL_CHECKERS dispatch.
    """

    ord: int
    label: str
    motor: str
    priority: Literal["high", "medium", "low"]
    completion_signal: str | None = None


ACTION_TEMPLATES: dict[WorkflowPhase, list[ActionTemplateDef]] = {
    WorkflowPhase.PRE_VENTA: [
        ActionTemplateDef(
            "schedule_exploratoria", "Agendar reunión exploratoria",
            "A18", "/admin/meetings/new", 1, 15,
        ),
        ActionTemplateDef(
            "send_proposal", "Enviar propuesta cualificada",
            "A19", "/admin/proposals/new", 2, 30,
        ),
    ],
    WorkflowPhase.ONBOARDING: [
        ActionTemplateDef(
            "start_onboarding_session", "Iniciar onboarding cliente",
            "M16", "/admin/onboarding/sessions/new", 1, 30,
        ),
        ActionTemplateDef(
            "send_onboarding_link", "Enviar magic link onboarding",
            "M12", "/admin/magic-links/new?purpose=onboarding", 2, 5,
        ),
        ActionTemplateDef(
            "review_onboarding_answers", "Revisar respuestas cliente",
            "M16", "/admin/onboarding/sessions", 3, 20,
        ),
    ],
    WorkflowPhase.DIAGNOSTICO: [
        ActionTemplateDef(
            "run_diagnosis", "Ejecutar diagnóstico inicial",
            "M21", "/admin/diagnosis/runs/new", 1, 45,
        ),
        ActionTemplateDef(
            "review_maturity_report", "Revisar informe madurez",
            "M21", "/admin/diagnosis/runs", 2, 25,
        ),
    ],
    WorkflowPhase.ANALISIS_RIESGOS: [
        ActionTemplateDef(
            "open_magerit_analysis", "Iniciar análisis riesgos MAGERIT (M02)",
            "M02", "/admin/magerit/analysis/new", 1, 60,
        ),
        ActionTemplateDef(
            "complete_magerit_dimensions", "Completar dimensiones MAGERIT (5D)",
            "M02", "/admin/magerit/analysis", 2, 90,
        ),
        ActionTemplateDef(
            "review_risk_matrix", "Revisar matriz riesgos pre-aprobación",
            "M02", "/admin/magerit/analysis", 3, 30,
        ),
    ],
    WorkflowPhase.ADECUACION: [
        ActionTemplateDef(
            "create_categorization", "Categorizar sistema (M01)",
            "M01", "/admin/categorizations/new", 1, 30,
        ),
        ActionTemplateDef(
            "run_magerit_analysis", "Análisis riesgos MAGERIT (M02)",
            "M02", "/admin/magerit/analysis/new", 2, 60,
        ),
        ActionTemplateDef(
            "approve_magerit", "Aprobar análisis MAGERIT",
            "M02", "/admin/magerit/analysis", 3, 15,
        ),
    ],
    WorkflowPhase.IMPLANTACION: [
        ActionTemplateDef(
            "complete_dda", "Completar Declaración Aplicabilidad (M03)",
            "M03", "/admin/dda/entries", 1, 90,
        ),
        ActionTemplateDef(
            "implement_controls", "Implementar controles (M06)",
            "M06", "/admin/controls", 2, 120,
        ),
        ActionTemplateDef(
            "collect_evidence", "Recoger evidencias (M07)",
            "M07", "/admin/evidence", 3, 60,
        ),
    ],
    WorkflowPhase.DDA_FINAL: [
        ActionTemplateDef(
            "review_dda_complete", "Revisar DdA completa pre-verificación",
            "M03", "/admin/dda/entries", 1, 60,
        ),
        ActionTemplateDef(
            "freeze_dda", "Congelar DdA (frozen state)",
            "M03", "/admin/dda/entries", 2, 15,
        ),
        ActionTemplateDef(
            "validate_evidence_completeness", "Validar evidencias completas",
            "M07", "/admin/evidence", 3, 45,
        ),
    ],
    WorkflowPhase.VERIFICACION: [
        ActionTemplateDef(
            "schedule_verification_run", "Programar verificación técnica (M08)",
            "M08", "/admin/verification/runs/new", 1, 30,
        ),
        ActionTemplateDef(
            "review_findings", "Revisar findings",
            "M08", "/admin/verification/findings", 2, 60,
        ),
    ],
    WorkflowPhase.CONFORMIDAD: [
        ActionTemplateDef(
            "run_audit_preparation", "Preparar dossier auditoría (M09)",
            "M09", "/admin/audit-prep/runs/new", 1, 90,
        ),
        ActionTemplateDef(
            "submit_conformity", "Submission conformidad ENAC (M27)",
            "M27", "/admin/conformity/submissions/new", 2, 30,
        ),
    ],
    WorkflowPhase.RETAINER_CIERRE: [
        ActionTemplateDef(
            "activate_retainer", "Activar retainer cliente (M23)",
            "M23", "/admin/retainer/contracts/new", 1, 30,
        ),
        ActionTemplateDef(
            "schedule_quarterly_review", "Programar revisión trimestral",
            "M23", "/admin/retainer/quarterly-reports", 2, 20,
        ),
    ],
}


TASK_TEMPLATES: dict[WorkflowPhase, list[TaskTemplateDef]] = {
    WorkflowPhase.PRE_VENTA: [
        # Cualificacion implicita cuando project existe (proxy honesto).
        TaskTemplateDef(1, "Cualificar lead (A17)", "A17", "high", "project_exists"),
        TaskTemplateDef(2, "Reunión exploratoria (A18)", "A18", "high", "exploratory_completed"),
        # proposals/contracts viven via lead_id · sin link directo a project ⇒ manual.
        TaskTemplateDef(3, "Propuesta enviada (A19)", "A19", "medium", None),
        TaskTemplateDef(4, "Contrato firmado (M14)", "M14", "high", None),
    ],
    WorkflowPhase.ONBOARDING: [
        TaskTemplateDef(1, "Crear sesión onboarding (M16)", "M16", "high", "onboarding_session_created"),
        TaskTemplateDef(2, "Definir interlocutor RSEG", "M16", "high", "onboarding_rseg_defined"),
        TaskTemplateDef(3, "Magic link enviado (M12)", "M12", "high", "onboarding_magic_link_sent"),
        TaskTemplateDef(4, "Respuestas cliente recibidas", "M16", "high", "onboarding_answers_received"),
        TaskTemplateDef(5, "Sesión completada", "M16", "high", "onboarding_session_completed"),
    ],
    WorkflowPhase.DIAGNOSTICO: [
        TaskTemplateDef(1, "Diagnostic run iniciado (M21)", "M21", "high", "diagnosis_run_started"),
        TaskTemplateDef(2, "Stakeholder analysis", "M21", "medium", "diagnosis_stakeholder_analysis"),
        TaskTemplateDef(3, "Process inventory", "M21", "medium", "diagnosis_process_inventory"),
        TaskTemplateDef(4, "Maturity scoring completado", "M21", "high", "diagnosis_maturity_scoring"),
        TaskTemplateDef(5, "Informe diagnóstico generado", "M21", "high", "diagnosis_report_generated"),
    ],
    WorkflowPhase.ANALISIS_RIESGOS: [
        TaskTemplateDef(1, "MAGERIT analysis abierto (M02)", "M02", "high", "magerit_exists"),
        TaskTemplateDef(2, "Dimensiones C/I/D/A/T completadas", "M02", "high", None),
        TaskTemplateDef(3, "Identificación amenazas", "M02", "high", None),
        TaskTemplateDef(4, "Cálculo riesgo residual", "M02", "high", None),
        TaskTemplateDef(5, "Matriz riesgos revisada pre-aprobación", "M02", "high", None),
    ],
    WorkflowPhase.ADECUACION: [
        TaskTemplateDef(1, "Categorización sistema (M01)", "M01", "high", "categorization_exists"),
        TaskTemplateDef(2, "Acta firma categorización", "M01", "high", "categorization_signed"),
        TaskTemplateDef(3, "MAGERIT análisis (M02)", "M02", "high", "magerit_exists"),
        TaskTemplateDef(4, "MAGERIT aprobado", "M02", "high", "magerit_approved"),
        # gap_analysis tabla no existe en BD ⇒ manual.
        TaskTemplateDef(5, "Gap analysis (M04)", "M04", "medium", None),
    ],
    WorkflowPhase.IMPLANTACION: [
        TaskTemplateDef(1, "DdA entries creadas (M03)", "M03", "high", "dda_entries_exist"),
        TaskTemplateDef(2, "DdA frozen", "M03", "high", "dda_frozen"),
        # M05 sin tabla policies dedicada ⇒ manual.
        TaskTemplateDef(3, "Documentación políticas (M05)", "M05", "medium", None),
        TaskTemplateDef(4, "Controles implementados (M06)", "M06", "high", "dda_controls_implemented"),
        TaskTemplateDef(5, "Evidencias recogidas (M07)", "M07", "high", "evidence_collected"),
        TaskTemplateDef(6, "Audit checklist completo (M09)", "M09", "medium", "audit_checklist_started"),
    ],
    WorkflowPhase.DDA_FINAL: [
        TaskTemplateDef(1, "DdA todas implementadas (M03)", "M03", "high", "dda_controls_implemented"),
        TaskTemplateDef(2, "DdA frozen confirmado", "M03", "high", "dda_frozen"),
        TaskTemplateDef(3, "Evidencias completas validadas (M07)", "M07", "high", "evidence_collected"),
        TaskTemplateDef(4, "Sign-off pre-verificación", "M03", "high", None),
    ],
    WorkflowPhase.VERIFICACION: [
        TaskTemplateDef(1, "Verification run scheduled (M08)", "M08", "high", "verification_run_exists"),
        TaskTemplateDef(2, "Authorization magic link firmada (M12)", "M12", "high", "verification_authorization_signed"),
        TaskTemplateDef(3, "Verification run completed", "M08", "high", "verification_run_completed"),
        TaskTemplateDef(4, "Findings revisados", "M08", "high", "verification_findings_reviewed"),
        TaskTemplateDef(5, "Remediation tracking", "M08", "medium", "verification_remediation_tracked"),
    ],
    WorkflowPhase.CONFORMIDAD: [
        TaskTemplateDef(1, "Audit preparation iniciada (M09)", "M09", "high", "audit_prep_started"),
        TaskTemplateDef(2, "Dossier auditoría generado", "M09", "high", "audit_prep_dossier_generated"),
        TaskTemplateDef(3, "Audit prep completed", "M09", "high", "audit_prep_completed"),
        TaskTemplateDef(4, "Submission conformidad ENAC (M27)", "M27", "high", "conformity_submission_exists"),
        TaskTemplateDef(5, "Submission accepted", "M27", "high", "conformity_submission_accepted"),
    ],
    WorkflowPhase.RETAINER_CIERRE: [
        TaskTemplateDef(1, "Retainer ofrecido (M23)", "M23", "high", "retainer_offered_event"),
        TaskTemplateDef(2, "Retainer aceptado (M23)", "M23", "high", "retainer_active"),
        TaskTemplateDef(3, "Quarterly reports activos", "M23", "medium", "retainer_quarterly_reports_exist"),
        TaskTemplateDef(4, "Lifecycle event certified (M25)", "M25", "high", "lifecycle_certified_event"),
    ],
}
