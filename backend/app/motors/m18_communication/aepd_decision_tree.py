"""Árbol decisión AEPD RGPD art.33-34 · SAN-C MB-11.2.

¿Requiere notificación AEPD en 72h tras detección incidente?

Decision tree determinístico (sin LLM · trazabilidad legal primary):

    Step 1 · ¿Hay datos personales afectados?
            NO  → No aplica art.33 (registrar internamente, no AEPD)
            SI  → Step 2

    Step 2 · ¿Probabilidad riesgo derechos/libertades?
            BAJO    → NO obligatorio art.33 (registrar internamente · art.30)
            MEDIO   → notificar AEPD 72h (art.33)
            ALTO    → notificar AEPD + comunicar interesados (art.33+34)

Output: Decision con notify, notify_subjects, deadline_hours, path
razonamiento explicable, register_only flag.

Referencias
-----------
- RGPD art.33 · Notificación brecha datos AEPD 72h
- RGPD art.34 · Comunicación brecha interesados (alto riesgo)
- AEPD Guía Brechas Seguridad 2024 · 4 niveles severidad
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class IncidentInput:
    """Input mínimo para decision tree (independiente de modelo BD)."""

    affects_personal_data: bool
    risk_to_rights: str  # low · medium · high (insensitive)
    affected_categories: Optional[list[str]] = None
    description: Optional[str] = None


@dataclass(frozen=True)
class Decision:
    """Resultado decision tree."""

    notify: bool
    notify_subjects: bool = False
    deadline_hours: Optional[int] = None
    register_only: bool = False
    path: list[str] = field(default_factory=list)


_DEADLINE_RGPD_HOURS = 72


def evaluate_decision_tree(incident: IncidentInput) -> Decision:
    """Evalúa árbol decisión AEPD art.33-34.

    Args:
        incident: IncidentInput con flag personal_data + nivel risk.

    Returns:
        Decision determinística con path razonamiento explicable.
    """
    path: list[str] = []
    risk = (incident.risk_to_rights or "").lower()

    # Step 1: ¿Hay datos personales afectados?
    if not incident.affects_personal_data:
        path.append("No afecta datos personales · no aplica RGPD art.33")
        return Decision(notify=False, path=path)

    path.append("Afecta datos personales · aplica RGPD art.33")

    # Step 2/3: ¿Probabilidad riesgo derechos/libertades?
    if risk == "low":
        path.append(
            "Riesgo bajo · NO obligatorio AEPD (registrar internamente · art.30)"
        )
        return Decision(notify=False, register_only=True, path=path)

    if risk == "high":
        path.append(
            "Alto riesgo · notificar AEPD 72h + comunicar interesados (art.34)"
        )
        return Decision(
            notify=True,
            notify_subjects=True,
            deadline_hours=_DEADLINE_RGPD_HOURS,
            path=path,
        )

    # medium (default si risk vacío o "medium" o no reconocido pero datos personales)
    path.append("Riesgo medio · notificar AEPD 72h (art.33)")
    return Decision(
        notify=True,
        deadline_hours=_DEADLINE_RGPD_HOURS,
        path=path,
    )
