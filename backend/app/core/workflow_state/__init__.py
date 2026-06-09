"""Workflow state derivation · 4 funciones derive_state (FASE 8 · ADR-026).

Modular split del original ``workflow_state.py`` (52.482 bytes monolítico) en
sub-módulos lógicos · refactor FASE 2 H1 (2026-05-13):

- ``phase``    · ``get_current_phase`` + ``_derive_phase_cascade`` (CASCADE
                 strategy ADR-026 sobre 7 motors EXISTS subqueries)
- ``items``    · ``_calculate_phase_items_done`` + 8 per-phase helpers
                 (W1 calibración · items reales por fase)
- ``signals``  · 35 ``_signal_*`` atomic SQL EXISTS primitives +
                 ``_TASK_SIGNAL_CHECKERS`` dispatch dict (W2 calibración)
- ``views``    · ``get_next_actions`` + ``get_phase_progress`` +
                 ``get_phase_tasks`` + ``verify_client_owns_project`` +
                 ``get_workflow_roadmap``

Backward compat preservada · callers existentes ``from backend.app.core.workflow_state
import X`` continúan funcionando vía re-export de este ``__init__.py``.

Separado conceptualmente de ``workflow_gates.py`` (gates checkpointing
require_*) que enforces ordering. Aquí las funciones DERIVE state actual
del proyecto para vista guiada cliente UI.

Strategy ``get_current_phase`` (ADR-026 · híbrida):
    1. Priority: ``projects.fase`` persisted (CHECK constraint enum 8 fases · NOT NULL)
    2. Fallback CASCADE: 7 EXISTS subqueries derived from motors si fase
       desactualizada vs realidad latest activity
"""
from backend.app.core.workflow_state.items import (
    _adecuacion_items_done,
    _implantacion_items_done,
)
from backend.app.core.workflow_state.phase import (
    _derive_phase_cascade,
    get_current_phase,
)
from backend.app.core.workflow_state.views import (
    get_next_actions,
    get_phase_progress,
    get_phase_tasks,
    get_workflow_roadmap,
    verify_client_owns_project,
)

__all__ = [
    "get_current_phase",
    "get_next_actions",
    "get_phase_progress",
    "get_phase_tasks",
    "get_workflow_roadmap",
    "verify_client_owns_project",
]

# Private symbols re-exportados para backward compat con tests que importan
# directamente desde el package (test_workflow_state.py). NO incluidos en
# __all__ · acceso explícito por nombre solo.
