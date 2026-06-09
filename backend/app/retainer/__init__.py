"""MB-18 retainer state machine + churn predictor (ADR-040).

Centraliza extensión RetainerContract.estado con upgraded/downgraded/
churned + ChurnPredictor heurístico explicable (NO ML black-box).
"""
from backend.app.retainer.state_machine import (  # noqa: F401
    RetainerStateMachine,
    RetainerStateMachineError,
    VALID_RETAINER_STATES,
    VALID_TRANSITIONS,
)
from backend.app.retainer.churn_predictor import (  # noqa: F401
    ChurnPredictor,
    compute_churn_score,
)
