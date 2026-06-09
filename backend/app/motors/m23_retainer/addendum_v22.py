"""Motor 23 — Addendum v2.2 §9.5 extensions.

Nueve submodulos del retainer extendido. Logica determinista, sin BD.
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import Literal


RetainerProfile = Literal["R_LITE", "R_STD", "R_PLUS", "R_CRITICAL"]


# ── A. Renewal Clock ──────────────────────────────────────────────────────

RENEWAL_STATES = (
    "T-180", "T-120", "T-90", "T-60", "T-30", "DUE", "IN_PROGRESS", "COMPLETED", "LAPSED",
)


class RenewalClock:
    @staticmethod
    def state_for(target_date: date, today: date | None = None) -> str:
        from backend.app.motors.m27_conformity.service import compute_renewal_state
        return compute_renewal_state(target_date, today)["state"]


# ── B. Drift Detector ─────────────────────────────────────────────────────

DRIFT_DIMENSIONS = (
    "evidence_freshness", "control_coverage", "policy_currency", "personnel_changes",
    "infrastructure_changes", "vendor_changes", "incident_volume", "audit_findings",
    "regulatory_changes", "client_engagement",
)
DRIFT_SEVERITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
DRIFT_IMPACTS = ("isolated", "tactical", "operational", "strategic", "existential")


class DriftDetector:
    @staticmethod
    def assess(metrics: dict[str, str]) -> list[dict]:
        out: list[dict] = []
        for dim in DRIFT_DIMENSIONS:
            sev = metrics.get(dim, "LOW")
            if sev not in DRIFT_SEVERITIES:
                sev = "LOW"
            out.append({"dimension": dim, "severity": sev})
        return out

    @staticmethod
    def health_score(metrics: dict[str, str]) -> int:
        weights = {"LOW": 0, "MEDIUM": 5, "HIGH": 15, "CRITICAL": 30}
        score = 100 - sum(weights.get(metrics.get(d, "LOW"), 0) for d in DRIFT_DIMENSIONS)
        return max(0, min(100, score))


# ── C. Change Intake (deriva a M28) ────────────────────────────────────────

class ChangeIntake:
    """Hand-off helper: cualquier cambio operativo se deriva a M28."""

    @staticmethod
    def derive(project_id: uuid.UUID, description: str, requested_by: str) -> dict:
        return {
            "project_id": project_id,
            "description": description,
            "requested_by": requested_by,
            "next_step": "POST /api/v1/changes/projects/{project_id}/changes",
        }


# ── D. Incident & LUCIA Assist ────────────────────────────────────────────

class IncidentLuciaAssist:
    @staticmethod
    def package(incident_id: uuid.UUID, severity: str, timeline: list[dict]) -> dict:
        return {
            "incident_id": incident_id,
            "severity": severity,
            "timeline": timeline,
            "lucia_export_required": severity in ("HIGH", "CRITICAL"),
        }


# ── E. Provider Lifecycle ─────────────────────────────────────────────────

PROVIDER_STAGES = ("onboarding", "operating", "review", "offboarding", "closed")


class ProviderLifecycle:
    @staticmethod
    def next_stage(current: str) -> str:
        order = list(PROVIDER_STAGES)
        idx = order.index(current) if current in order else 0
        return order[min(idx + 1, len(order) - 1)]


# ── F. Evidence Freshness Scheduler ───────────────────────────────────────

class EvidenceFreshnessScheduler:
    # Ejecutable 8 Pasada 16 (a · CÓDIGO): el import `from m07_evidence.addendum_v22 import
    # is_evidence_fresh` apuntaba a un MÓDULO INEXISTENTE (ModuleNotFoundError). El
    # is_evidence_fresh real (m07_evidence/freshness_service.py) es async DB-based con otra
    # firma (session, evidence_id). Aquí la frescura es days-based sobre dicts → cálculo inline
    # con umbrales por política (periodos ENS estándar). Fuente: firma divergente + intención
    # del test (annual 500d → due · monthly 10d → fresh).
    _POLICY_MAX_DAYS = {
        "weekly": 7, "monthly": 30, "quarterly": 90,
        "semiannual": 180, "annual": 365,
    }

    @staticmethod
    def due_evidences(evidences: list[dict]) -> list[dict]:
        def _fresh(e: dict) -> bool:
            days = e.get("last_refresh_days", 9999)
            policy = e.get("freshness_policy", "annual")
            max_days = EvidenceFreshnessScheduler._POLICY_MAX_DAYS.get(policy, 365)
            return days <= max_days
        return [e for e in evidences if not _fresh(e)]


# ── G. Retainer Ops Queue ─────────────────────────────────────────────────

class RetainerOpsQueue:
    @staticmethod
    def prioritize(items: list[dict]) -> list[dict]:
        def key(it: dict) -> tuple:
            crit = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}.get(
                it.get("severity", "LOW"), 3,
            )
            sla = -int(it.get("sla_hours_remaining", 9999))
            renewal = 0 if it.get("affects_renewal") else 1
            return (crit, renewal, sla)

        return sorted(items, key=key)


# ── H. Capacity Planner ───────────────────────────────────────────────────

PROFILE_HOURS_PER_MONTH = {
    "R_LITE": 8,
    "R_STD": 16,
    "R_PLUS": 32,
    "R_CRITICAL": 64,
}


class CapacityPlanner:
    @staticmethod
    def total_assigned(profiles: list[RetainerProfile]) -> int:
        return sum(PROFILE_HOURS_PER_MONTH[p] for p in profiles if p in PROFILE_HOURS_PER_MONTH)

    @staticmethod
    def utilization(profiles: list[RetainerProfile], capacity_hours: int) -> dict:
        total = CapacityPlanner.total_assigned(profiles)
        ratio = total / capacity_hours if capacity_hours > 0 else 1.0
        return {
            "assigned_hours": total,
            "capacity_hours": capacity_hours,
            "utilization": round(ratio, 3),
            "alert": ratio > 0.9,
        }


# ── I. Retainer Exit / Handover ───────────────────────────────────────────

class RetainerExit:
    @staticmethod
    def handover_checklist() -> list[str]:
        return [
            "Devolver / borrar credenciales corporativas del retainer",
            "Entregar dossier final (E-049) firmado",
            "Cerrar incidencias abiertas o transferirlas",
            "Notificar a M27 para detener Renewal Clock",
            "Generar factura de cierre via M15",
            "Archivar workspace M20",
        ]


__all__ = [
    "RenewalClock", "DriftDetector", "ChangeIntake", "IncidentLuciaAssist",
    "ProviderLifecycle", "EvidenceFreshnessScheduler", "RetainerOpsQueue",
    "CapacityPlanner", "RetainerExit",
    "DRIFT_DIMENSIONS", "DRIFT_SEVERITIES", "DRIFT_IMPACTS",
    "RENEWAL_STATES", "PROFILE_HOURS_PER_MONTH",
]
