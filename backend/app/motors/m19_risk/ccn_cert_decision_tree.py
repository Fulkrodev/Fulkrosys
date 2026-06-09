"""CCN-CERT decision tree · SAN-E v3.MB-6 atom 3.

Lightweight decision tree para determinar routing CCN-CERT per incident:
  1. Gate severity · medium/low → internal_only (NO notificación externa)
  2. Gate severity · critical/high → deadline determinado (24h/72h)
  3. Gate project.lucia_enabled · True → auto-submit LUCIA federation
                                 · False → manual notification template E-CCN-NOTIFY

Pattern replicado de m18_communication/aepd_decision_tree.py (RGPD AEPD).
Compliance ITS Notificación Incidentes CCN + RD 311/2022 art op.exp.10.

Q7 cement · admin-only helper · NO cliente-facing.
Refinement MB-7 · integrar CCN-STIC 817 incident response runbook complete.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


CcnCertRouteType = Literal[
    "internal_only",       # medium/low severity · workflow interno suficiente
    "lucia_federation",    # high/critical + lucia_enabled=True · auto submit
    "manual_notification", # high/critical + lucia_enabled=False · template E-CCN-NOTIFY
]


@dataclass(frozen=True)
class IncidentEvaluationInput:
    severity: str  # critical | high | medium | low
    lucia_enabled: bool
    project_tier: str | None = None  # BASICA/MEDIA/ALTA · informational


@dataclass(frozen=True)
class CcnCertRouting:
    """Decision output · serializable jsonb para incidents.ccn_cert_routing_decision."""

    route_type: CcnCertRouteType
    deadline_hours: int | None  # NULL si internal_only
    action_required: str
    reasoning: str

    def to_dict(self) -> dict:
        return {
            "route_type": self.route_type,
            "deadline_hours": self.deadline_hours,
            "action_required": self.action_required,
            "reasoning": self.reasoning,
        }


_CRITICAL_DEADLINE_HOURS = 24
_HIGH_DEADLINE_HOURS = 72

_SEVERITIES_REQUIRING_ROUTING: frozenset[str] = frozenset({"critical", "high"})


def evaluate_routing(input_: IncidentEvaluationInput) -> CcnCertRouting:
    """Decision tree CCN-CERT routing per incident.

    Output cacheable en incidents.ccn_cert_routing_decision JSONB column.
    Re-evaluable si severity cambia o lucia_enabled toggle.
    """
    severity_norm = (input_.severity or "").lower().strip()

    if severity_norm not in _SEVERITIES_REQUIRING_ROUTING:
        return CcnCertRouting(
            route_type="internal_only",
            deadline_hours=None,
            action_required="workflow_close_only",
            reasoning=(
                f"Severidad '{severity_norm}' · medium/low · workflow interno "
                f"suficiente · NO notificación externa CCN-CERT requerida"
            ),
        )

    deadline_hours = (
        _CRITICAL_DEADLINE_HOURS
        if severity_norm == "critical"
        else _HIGH_DEADLINE_HOURS
    )

    if input_.lucia_enabled:
        return CcnCertRouting(
            route_type="lucia_federation",
            deadline_hours=deadline_hours,
            action_required="auto_submit_lucia",
            reasoning=(
                f"Severidad '{severity_norm}' · LUCIA federation activada para "
                f"proyecto · auto-submit via lucia_federation.py "
                f"(deadline {deadline_hours}h CCN-CERT)"
            ),
        )

    return CcnCertRouting(
        route_type="manual_notification",
        deadline_hours=deadline_hours,
        action_required="generate_manual_notification_template",
        reasoning=(
            f"Severidad '{severity_norm}' · LUCIA NO habilitada en proyecto · "
            f"plantilla manual E-CCN-NOTIFY requerida (deadline {deadline_hours}h "
            f"CCN-CERT · cliente firma + envía email incidencias@ccn-cert.cni.es)"
        ),
    )
