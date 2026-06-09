"""Tests WorkflowPhase 10 fases canonical (SAN-C MB-11.1).

Cobertura:
- Enum ``WorkflowPhase`` tiene 10 valores.
- ``ordered()`` retorna 10 fases en orden lifecycle correcto.
- Sub-fases nuevas (``analisis_riesgos``, ``dda_final``) en posiciones
  correctas (entre diagnostico/adecuacion e implantacion/verificacion).
- ``ACTION_TEMPLATES`` y ``TASK_TEMPLATES`` cubren las 10 fases.
- Backward-compat: 8 fases originales siguen presentes.
"""
from __future__ import annotations

from backend.app.core.workflow_phase import WorkflowPhase
from backend.app.core.workflow_templates import ACTION_TEMPLATES, TASK_TEMPLATES


def test_workflow_phase_has_10_values():
    """SAN-C MB-11.1: 8 → 10 fases canonical."""
    assert len(WorkflowPhase) == 10


def test_ordered_lifecycle_correct_sequence():
    """Sub-fases nuevas en posiciones canonical Manual ENS plan v4.2."""
    ordered = WorkflowPhase.ordered()
    assert ordered == [
        WorkflowPhase.PRE_VENTA,
        WorkflowPhase.ONBOARDING,
        WorkflowPhase.DIAGNOSTICO,
        WorkflowPhase.ANALISIS_RIESGOS,
        WorkflowPhase.ADECUACION,
        WorkflowPhase.IMPLANTACION,
        WorkflowPhase.DDA_FINAL,
        WorkflowPhase.VERIFICACION,
        WorkflowPhase.CONFORMIDAD,
        WorkflowPhase.RETAINER_CIERRE,
    ]


def test_new_phases_string_values():
    """Persistencia DB usa strings lowercase."""
    assert WorkflowPhase.ANALISIS_RIESGOS.value == "analisis_riesgos"
    assert WorkflowPhase.DDA_FINAL.value == "dda_final"


def test_backward_compat_8_original_phases_still_present():
    """Migration extiende constraint, no rewrites projects existentes."""
    original_8 = {
        "pre_venta", "onboarding", "diagnostico", "adecuacion",
        "implantacion", "verificacion", "conformidad", "retainer_cierre",
    }
    actual_values = {p.value for p in WorkflowPhase}
    assert original_8.issubset(actual_values)


def test_previous_next_navigation_for_new_phases():
    assert WorkflowPhase.ANALISIS_RIESGOS.previous() == WorkflowPhase.DIAGNOSTICO
    assert WorkflowPhase.ANALISIS_RIESGOS.next() == WorkflowPhase.ADECUACION
    assert WorkflowPhase.DDA_FINAL.previous() == WorkflowPhase.IMPLANTACION
    assert WorkflowPhase.DDA_FINAL.next() == WorkflowPhase.VERIFICACION


def test_action_templates_cover_all_10_phases():
    assert set(ACTION_TEMPLATES.keys()) == set(WorkflowPhase)
    for phase in WorkflowPhase:
        assert len(ACTION_TEMPLATES[phase]) >= 1, f"{phase} has no actions"


def test_task_templates_cover_all_10_phases():
    assert set(TASK_TEMPLATES.keys()) == set(WorkflowPhase)
    for phase in WorkflowPhase:
        assert len(TASK_TEMPLATES[phase]) >= 1, f"{phase} has no tasks"


def test_new_phases_have_action_and_task_templates():
    assert len(ACTION_TEMPLATES[WorkflowPhase.ANALISIS_RIESGOS]) >= 1
    assert len(ACTION_TEMPLATES[WorkflowPhase.DDA_FINAL]) >= 1
    assert len(TASK_TEMPLATES[WorkflowPhase.ANALISIS_RIESGOS]) >= 1
    assert len(TASK_TEMPLATES[WorkflowPhase.DDA_FINAL]) >= 1
