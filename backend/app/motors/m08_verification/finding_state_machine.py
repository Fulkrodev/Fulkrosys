"""Máquina de estados del hallazgo (doc §6).

```
detected → triaged → verified → reported → in_remediation → retested → closed
                 ↘ false_positive  (SOLO desmentido activo determinista u override humano)
                 ↘ risk_accepted   (justificación + caducidad + re-revisión)
```

Reglas duras (doc §4 + §6 + §7):
- `closed` SOLO desde `retested` (delta que confirma remediación).
- `false_positive` exige `by_active_disproof=True` (verificación activa que
  desmiente, determinista) O `human_override=True`. **NUNCA por juicio del LLM**
  sobre contenido del objetivo — esto es defensa anti prompt-injection.
- `risk_accepted` es terminal-con-caducidad: requiere `risk_accepted_expires_at`,
  re-revisión obligatoria al caducar.

Módulo puro y determinista (patrón #23 cross-app · state_machine canónico).
"""
from __future__ import annotations


class FindingState:
    DETECTED = "detected"
    TRIAGED = "triaged"
    VERIFIED = "verified"
    REPORTED = "reported"
    IN_REMEDIATION = "in_remediation"
    RETESTED = "retested"
    CLOSED = "closed"
    FALSE_POSITIVE = "false_positive"
    RISK_ACCEPTED = "risk_accepted"


ALL_STATES = frozenset({
    FindingState.DETECTED, FindingState.TRIAGED, FindingState.VERIFIED,
    FindingState.REPORTED, FindingState.IN_REMEDIATION, FindingState.RETESTED,
    FindingState.CLOSED, FindingState.FALSE_POSITIVE, FindingState.RISK_ACCEPTED,
})

# Estados terminales (no admiten salida). risk_accepted es terminal pero
# con re-revisión por caducidad (puede reabrirse en otro run, no por transición).
TERMINAL_STATES = frozenset({
    FindingState.CLOSED, FindingState.FALSE_POSITIVE, FindingState.RISK_ACCEPTED,
})

# Transiciones válidas. false_positive/risk_accepted alcanzables desde casi
# cualquier estado vivo (pero false_positive con guard especial · ver transition()).
_LIVE = (
    FindingState.DETECTED, FindingState.TRIAGED, FindingState.VERIFIED,
    FindingState.REPORTED, FindingState.IN_REMEDIATION, FindingState.RETESTED,
)

VALID_TRANSITIONS: dict[str, frozenset[str]] = {
    FindingState.DETECTED: frozenset({
        FindingState.TRIAGED, FindingState.FALSE_POSITIVE, FindingState.RISK_ACCEPTED,
    }),
    FindingState.TRIAGED: frozenset({
        FindingState.VERIFIED, FindingState.REPORTED,
        FindingState.FALSE_POSITIVE, FindingState.RISK_ACCEPTED,
    }),
    FindingState.VERIFIED: frozenset({
        FindingState.REPORTED, FindingState.FALSE_POSITIVE, FindingState.RISK_ACCEPTED,
    }),
    FindingState.REPORTED: frozenset({
        FindingState.IN_REMEDIATION, FindingState.RISK_ACCEPTED,
        FindingState.FALSE_POSITIVE,
    }),
    FindingState.IN_REMEDIATION: frozenset({
        FindingState.RETESTED, FindingState.RISK_ACCEPTED,
    }),
    FindingState.RETESTED: frozenset({
        FindingState.CLOSED, FindingState.IN_REMEDIATION,  # retest falla → vuelve
        FindingState.RISK_ACCEPTED,
    }),
    FindingState.CLOSED: frozenset(),
    FindingState.FALSE_POSITIVE: frozenset(),
    FindingState.RISK_ACCEPTED: frozenset(),
}

# Eventos canónicos audit_log por transición destino (Sub-atom 5.A namespace)
STATE_EVENT_MAP: dict[str, str] = {
    FindingState.TRIAGED: "m08.finding.triaged",
    FindingState.VERIFIED: "m08.finding.verified",
    FindingState.REPORTED: "m08.finding.reported",
    FindingState.IN_REMEDIATION: "m08.finding.in_remediation",
    FindingState.RETESTED: "m08.finding.retested",
    FindingState.CLOSED: "m08.finding.closed",
    FindingState.FALSE_POSITIVE: "m08.finding.false_positive",
    FindingState.RISK_ACCEPTED: "m08.finding.risk_accepted",
}


class InvalidTransitionError(Exception):
    """Transición de estado no permitida por la máquina."""


class IntegrityGuardError(Exception):
    """Violación de la regla dura de integridad (doc §4/§7)."""


def is_terminal(state: str) -> bool:
    return state in TERMINAL_STATES


def can_transition(current: str, target: str) -> bool:
    return target in VALID_TRANSITIONS.get(current, frozenset())


def transition(
    current: str,
    target: str,
    *,
    by_active_disproof: bool = False,
    human_override: bool = False,
) -> str:
    """Valida y devuelve el estado destino, o levanta.

    Defensa anti prompt-injection (doc §7 · regla dura):
    - `false_positive` SOLO si `by_active_disproof` (verificación activa
      determinista que desmiente) O `human_override`. Jamás por el LLM.
    """
    if current not in ALL_STATES:
        raise InvalidTransitionError(f"estado origen desconocido: {current!r}")
    if target not in ALL_STATES:
        raise InvalidTransitionError(f"estado destino desconocido: {target!r}")
    if not can_transition(current, target):
        raise InvalidTransitionError(
            f"transición no permitida: {current} → {target}"
        )
    if target == FindingState.FALSE_POSITIVE and not (
        by_active_disproof or human_override
    ):
        raise IntegrityGuardError(
            "false_positive requiere desmentido activo determinista u override "
            "humano (doc §4/§7) · NUNCA por juicio del LLM"
        )
    return target


def event_for(target: str) -> str | None:
    return STATE_EVENT_MAP.get(target)
