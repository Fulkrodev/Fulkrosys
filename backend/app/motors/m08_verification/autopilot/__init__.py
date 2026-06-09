"""M8 Autopilot · orquestación end-to-end (doc §13) + conector efímero (§2).

Entre el Gate humano 1 (autorización/scope) y el Gate humano 2 (validación/
atestación Alto), todo es autopilot determinista: conecta (efímero, zero
standing access), ejecuta los motores pinneados, gates 1-5, triage agéntico
anti-injection, normaliza (SARIF), enriquece (CVSS+EPSS), mapea ENS, persiste
con evidencia R6, y revoca el acceso al cerrar.
"""
from backend.app.motors.m08_verification.autopilot.ephemeral_connector import (
    create_ephemeral_session,
    revoke_ephemeral_session,
    is_session_active,
    build_authorization_json,
    sign_authorization,
)
from backend.app.motors.m08_verification.autopilot.orchestrator import (
    orchestrate_run,
    AUTOPILOT_PHASES,
)

__all__ = [
    "create_ephemeral_session",
    "revoke_ephemeral_session",
    "is_session_active",
    "build_authorization_json",
    "sign_authorization",
    "orchestrate_run",
    "AUTOPILOT_PHASES",
]
