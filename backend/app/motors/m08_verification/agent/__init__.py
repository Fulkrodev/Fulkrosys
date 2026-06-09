"""M8 Autopilot · capa agéntica (doc §7).

El agente (Opus 4.8) NO encuentra vulns (eso son los motores) ni dictamina
en libre forma: planifica, triagea, correlaciona y sugiere — siempre como
salida estructurada, logueada y advisory. La defensa anti prompt-injection
(injection_guard) es control de primera clase.
"""
from backend.app.motors.m08_verification.agent.injection_guard import (
    detect_injection_attempt,
    wrap_untrusted_target_data,
    validate_verdict_output,
    INJECTION_FINDING_TEMPLATE,
)

__all__ = [
    "detect_injection_attempt",
    "wrap_untrusted_target_data",
    "validate_verdict_output",
    "INJECTION_FINDING_TEMPLATE",
]
