"""Clasificador de riesgo + resolución de política · m_remediation (ADR-055).

Determinista (R1): el tier viene SIEMPRE del catálogo de código; aquí solo se
resuelve QUÉ se hace con ese tier dada la política del conector/agente y el
kill-switch global. Fail-closed en todos los caminos desconocidos.

Kill-switch en 3 capas (basta UNA en off para NO aplicar):
  1. Global   · env `FULKRO_REMEDIATION_ENABLED` (default `false`)
  2. Conector · `cloud_connectors.remediation_enabled` (default `false`)
  3. Política  · `auto_remediation_policy` (default `off`)
"""
from __future__ import annotations

import enum
import os

from backend.app.motors.m_remediation.catalog import (
    RemediationTier,
    get_action_spec,
)


class AutoRemediationPolicy(str, enum.Enum):
    """Política de auto-remediación por conector/agente."""

    OFF = "off"
    """No se aplica nada · todo queda como plan (humano externo)."""
    SAFE_AUTO_ONLY = "safe_auto_only"
    """Solo SAFE_AUTO se aplica solo · GUARDED queda como plan (no se ofrece)."""
    FULL = "full"
    """Híbrido Marcos: SAFE_AUTO auto + GUARDED con autorización previa."""


class ExecutionMode(str, enum.Enum):
    """Resultado de la resolución: qué hace el motor con un action_type dado."""

    AUTO = "auto"
    """Se aplica automáticamente (preflight→snapshot→apply→verify→rollback)."""
    REQUIRE_AUTHORIZATION = "require_authorization"
    """Se aplica SOLO tras autorización previa (tier GUARDED · política FULL)."""
    BLOCKED = "blocked"
    """Destructivo · nunca auto · solo plan (humano externo)."""
    DISABLED = "disabled"
    """Kill-switch/política lo deja como plan · no se aplica."""


def global_remediation_enabled() -> bool:
    """Capa 1 del kill-switch · env global (default false · fail-closed)."""
    return os.getenv("FULKRO_REMEDIATION_ENABLED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def resolve_execution_mode(
    action_type: str,
    *,
    target_enabled: bool,
    policy: str | AutoRemediationPolicy,
) -> ExecutionMode:
    """Resuelve el modo de ejecución de una acción (determinista · fail-closed).

    Args:
        action_type: clave del catálogo.
        target_enabled: capa 2 · ``remediation_enabled`` del conector (cloud) o
            estado ``active`` del agente (host).
        policy: capa 3 · política del conector/agente.

    Returns:
        ExecutionMode. Cualquier camino ambiguo/desconocido → DISABLED (o BLOCKED
        si la acción es destructiva, que prevalece siempre).
    """
    spec = get_action_spec(action_type)
    if spec is None:
        # Acción no catalogada · NUNCA se aplica (fail-closed).
        return ExecutionMode.DISABLED

    # BLOCKED prevalece SIEMPRE, incluso con kill-switches off (semántica clara:
    # un destructivo nunca es auto, independientemente de flags).
    if spec.tier == RemediationTier.BLOCKED:
        return ExecutionMode.BLOCKED

    # Capa 1 · global.
    if not global_remediation_enabled():
        return ExecutionMode.DISABLED

    # Capa 2 · conector/agente.
    if not target_enabled:
        return ExecutionMode.DISABLED

    # Capa 3 · política.
    pol = AutoRemediationPolicy(policy) if not isinstance(policy, AutoRemediationPolicy) else policy
    if pol == AutoRemediationPolicy.OFF:
        return ExecutionMode.DISABLED

    if spec.tier == RemediationTier.SAFE_AUTO:
        # SAFE_AUTO se aplica solo bajo SAFE_AUTO_ONLY y FULL.
        return ExecutionMode.AUTO

    if spec.tier == RemediationTier.GUARDED:
        if pol == AutoRemediationPolicy.FULL:
            return ExecutionMode.REQUIRE_AUTHORIZATION
        # SAFE_AUTO_ONLY: los GUARDED no se ofrecen · quedan como plan.
        return ExecutionMode.DISABLED

    # Defensivo · tier no contemplado → fail-closed.
    return ExecutionMode.DISABLED
