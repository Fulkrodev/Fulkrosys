"""Per-agent golden dataset evaluators · sub-atom 1.E.1.B.3.D Path C-light.

Cada evaluator agent-specific se registra automáticamente al importar el
módulo (`register_evaluator` side-effect). Para activar evaluators desde
runtime · importar este package (e.g. desde tests o eval_runner CLI con
flag explicit).
"""
from backend.app.motors.m_observability.evaluators import (  # noqa: F401
    deliverable_text_auditor_evaluator,
)
