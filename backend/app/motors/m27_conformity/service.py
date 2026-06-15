"""Motor 27 — Service layer.

Mantiene la logica de:
- Validacion de invariantes (addendum v2.2 §7.3)
- Orquestacion de declaracion / submission
- Calculo de renewal clock
- Validacion de overlay PCE / µCeENS

Patron: stateless funcional (no toca BD por ahora; cuando se anada el
schema SQL se incorporara aqui via AsyncSession).
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from backend.app.motors.m27_conformity.route_machine import (
    ACTIVE_STATES,
    RouteState,
)
from backend.app.motors.m27_conformity.submission_machine import (
    SubmissionState,
)


# ── Invariantes (§7.3) ─────────────────────────────────────────────────────

INVARIANTS = (
    "PROJECT_HAS_ROUTE_FROM_PHASE_1",
    "SINGLE_ACTIVE_ROUTE_PER_PROJECT",
    "SINGLE_ACTIVE_OVERLAY_PER_PROJECT",
    "NO_SUBMITTED_WITHOUT_PAYLOAD",
    "NO_COMPLETED_WITHOUT_PROOF_OR_JUSTIFICATION",
    "NO_RENEWAL_WITHOUT_TARGET_DATE",
    # §2.2 audit-2026-06-15 · "NEVER_ACTIVE_AND_EXPIRED_TOGETHER" retirado: una
    # ruta tiene UN solo campo `state` → no puede ser ACTIVE y EXPIRED a la vez
    # (la columna de estado ya lo garantiza). El invariante era estructuralmente
    # invioable (rama muerta `state==ACTIVE and state in TERMINAL_STATES`) → no
    # mantener una promesa de protección que nunca se evalúa.
)


def check_invariants(snapshot: dict[str, Any]) -> list[str]:
    """Return the list of invariant violations for ``snapshot``.

    ``snapshot`` is a dict with keys:
      project_phase, route, overlay, submissions, renewals.
    """
    violations: list[str] = []
    phase = snapshot.get("project_phase", 0)
    route = snapshot.get("route")
    overlays = snapshot.get("overlays", [])
    submissions = snapshot.get("submissions", [])
    renewals = snapshot.get("renewals", [])

    if phase >= 1 and not route:
        violations.append("PROJECT_HAS_ROUTE_FROM_PHASE_1")

    active_routes = [r for r in [route] if r and RouteState(r["state"]) in ACTIVE_STATES]
    if len(active_routes) > 1:
        violations.append("SINGLE_ACTIVE_ROUTE_PER_PROJECT")

    primary_overlays = [o for o in overlays if o.get("is_primary")]
    if len(primary_overlays) > 1:
        violations.append("SINGLE_ACTIVE_OVERLAY_PER_PROJECT")

    for s in submissions:
        if s["state"] == SubmissionState.SUBMITTED.value and not s.get("payload_present"):
            violations.append("NO_SUBMITTED_WITHOUT_PAYLOAD")
            break

    for s in submissions:
        if s["state"] == SubmissionState.COMPLETED.value and not (
            s.get("proof_present") or s.get("justification")
        ):
            violations.append("NO_COMPLETED_WITHOUT_PROOF_OR_JUSTIFICATION")
            break

    for r in renewals:
        if r["state"] in ("T-180", "T-120", "T-90", "T-60", "T-30", "DUE", "IN_PROGRESS"):
            if not r.get("target_renewal_date"):
                violations.append("NO_RENEWAL_WITHOUT_TARGET_DATE")
                break

    return violations


# ── Declaration ────────────────────────────────────────────────────────────

DECLARATION_DOCUMENTS = ("E-041", "E-042", "E-043", "E-044")


def generate_declaration(project_id: uuid.UUID, requested_by: str) -> dict[str, Any]:
    """Generate the four E-041..E-044 documents for a Basica project.

    Returns metadata; the actual DOCX render happens via M06 once the route is
    locked as DECLARATION.
    """
    return {
        "project_id": project_id,
        "declaration_id": uuid.uuid4(),
        "documents": list(DECLARATION_DOCUMENTS),
        "generated_at": datetime.now(timezone.utc),
        "state": "draft",
        "requested_by": requested_by,
    }


# ── Submission ─────────────────────────────────────────────────────────────

def create_submission(project_id: uuid.UUID, target: str, payload_template: str) -> dict[str, Any]:
    return {
        "submission_id": uuid.uuid4(),
        "project_id": project_id,
        "target": target,
        "state": SubmissionState.GENERATED,
        "payload_present": True,
        "proof_present": False,
        "created_at": datetime.now(timezone.utc),
        "submitted_at": None,
        "completed_at": None,
        "payload_template": payload_template,
    }


def attach_proof(submission: dict[str, Any], proof_type: str, proof_reference: str, completed: bool) -> dict[str, Any]:
    submission["proof_present"] = True
    submission["proof_type"] = proof_type
    submission["proof_reference"] = proof_reference
    if completed:
        submission["state"] = SubmissionState.COMPLETED
        submission["completed_at"] = datetime.now(timezone.utc)
    return submission


# ── Renewal Clock ──────────────────────────────────────────────────────────

RENEWAL_STATES = ("T-180", "T-120", "T-90", "T-60", "T-30", "DUE", "IN_PROGRESS", "COMPLETED", "LAPSED")


def compute_renewal_state(target_renewal_date: date, today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    delta = (target_renewal_date - today).days
    if delta > 180:
        state = "T-180"
    elif delta > 120:
        state = "T-120"  # FIX(off-by-one): era "T-180" duplicado → colapsaba la
        # ventana 120-180 y desplazaba cada umbral inferior una posición.
    elif delta > 90:
        state = "T-90"
    elif delta > 60:
        state = "T-60"
    elif delta > 30:
        state = "T-30"
    elif delta > 0:
        # Dentro de 30 días: se mantiene el hito T-30 (el más urgente pre-DUE).
        state = "T-30"
    elif delta == 0:
        state = "DUE"
    else:
        state = "LAPSED"

    actions = _renewal_actions(state)
    return {
        "state": state,
        "target_renewal_date": target_renewal_date,
        "days_remaining": delta,
        "actions_required": actions,
    }


def _renewal_actions(state: str) -> list[str]:
    return {
        "T-180": ["Notificar a sponsor", "Revisar inventario de evidencias nucleares"],
        "T-120": ["Iniciar plan de renovacion", "Solicitar disponibilidad auditor"],
        "T-90": ["Lanzar M9 RENEWAL_PREFLIGHT", "Refrescar evidencias caducadas"],
        "T-60": ["Cerrar gaps abiertos", "Programar auditoria de renovacion"],
        "T-30": ["Bloquear cambios materiales no urgentes", "Submission con fecha objetivo"],
        "DUE": ["Ejecutar submission", "Esperar resultado auditor"],
        "IN_PROGRESS": ["Atender observaciones", "Corregir hallazgos"],
        "COMPLETED": ["Notificar a sponsor", "Actualizar registro externo"],
        "LAPSED": ["URGENTE: registrar incidencia, notificar a Marcos y dirección"],
    }[state]


# ── PCE / µCeENS Overlay ───────────────────────────────────────────────────
# NOTA TARGET (AMEND-012 sostenido audit v4):
# Los códigos PCE-* son identificadores TÉCNICOS oficiales CCN-STIC (Perfil de
# Cumplimiento Específico), NO nombres de customer. FULKRO atiende empresas
# privadas que licitan AAPP en concursos públicos (AAPP = customer-of-customer).
# Cuando una empresa privada presta servicios a una Administración Local, su
# sistema puede requerir el overlay PCE-AAPP-LOCAL (perfil CCN-STIC publicado
# para sistemas que sirven AAPP local). Idéntico patrón aplica a PCE-SALUD
# (servicios sanidad), PCE-NIS2 (operadores esenciales), PCE-SSG (MSSPs).

KNOWN_OVERLAYS = {
    "PCE-PYME": {
        "name": "Perfil de Cumplimiento Especifico para PYME",
        "category_min": "BASICA",
        "extra_controls": ["op.acc.6", "mp.per.3"],
    },
    "PCE-AAPP-LOCAL": {
        # CCN-STIC overlay aplicable a sistemas privados que sirven Admón Local
        "name": "PCE Administracion Local",
        "category_min": "MEDIA",
        "extra_controls": ["op.exp.7", "mp.info.1"],
    },
    "PCE-SALUD": {
        "name": "PCE Sector Salud",
        "category_min": "MEDIA",
        "extra_controls": ["mp.info.1", "mp.info.3"],
    },
    "MICRO-CEENS": {
        "name": "Micro-CeENS (sub-PYME)",
        "category_min": "BASICA",
        "extra_controls": [],
    },
    # SAN-C.MB-10.5 · 2 PCEs nuevos
    "PCE-NIS2": {
        "name": "PCE NIS2 (CCN-STIC 892) · entidades esenciales/importantes",
        "category_min": "MEDIA",
        "extra_controls": [
            "nis2.gov.1", "nis2.gov.2",
            "nis2.notif.1", "nis2.notif.2", "nis2.notif.3",
            "nis2.supply.1", "nis2.supply.2",
            "nis2.crypto.1", "nis2.access.1",
        ],
        "ccn_stic": "892",
        "catalog_yaml": "pce_nis2.yaml",
    },
    "PCE-SSG": {
        "name": "PCE Servicios de Seguridad Gestionados (CCN-STIC 896)",
        "category_min": "MEDIA",
        "extra_controls": [
            "ssg.acred.1", "ssg.team.1", "ssg.runbook.1", "ssg.sla.1",
            "ssg.tools.1", "ssg.training.1", "ssg.report.1",
            "ssg.continuity.1",
        ],
        "ccn_stic": "896",
        "catalog_yaml": "pce_ssg.yaml",
    },
}


def detect_overlay(
    sector: str,
    category: str,
    *,
    nis2_status: str | None = None,
    provider_type: str | None = None,
) -> dict[str, Any]:
    """Detecta PCE aplicable según sector + categoría + flags opcionales NIS2/SSG.

    SAN-C.MB-10.5: ``nis2_status`` ("essential"/"important") activa PCE-NIS2.
    ``provider_type`` ("mssp"/"soc_provider"/"pentest_provider") activa PCE-SSG.
    """
    sector_lc = (sector or "").lower()
    nis2 = (nis2_status or "").lower()
    provider = (provider_type or "").lower()

    if provider in {"mssp", "soc_provider", "pentest_provider", "threat_hunting"}:
        code = "PCE-SSG"
    elif nis2 in {"essential", "important"}:
        code = "PCE-NIS2"
    elif "salud" in sector_lc or "sanid" in sector_lc:
        code = "PCE-SALUD"
    elif "ayunt" in sector_lc or "publica" in sector_lc:
        code = "PCE-AAPP-LOCAL"
    elif category == "BASICA":
        code = "PCE-PYME"
    else:
        code = None

    if not code:
        return {
            "overlay_code": None, "overlay_name": None,
            "extra_controls": [], "detection_confidence": 0.0,
            "rationale": "No PCE applicable detected",
        }

    info = KNOWN_OVERLAYS[code]
    return {
        "overlay_code": code,
        "overlay_name": info["name"],
        "extra_controls": list(info["extra_controls"]),
        "detection_confidence": 0.85,
        "rationale": f"Detected from sector='{sector}' and category='{category}'",
    }


def validate_overlay(overlay_code: str, project_category: str) -> dict[str, Any]:
    if overlay_code not in KNOWN_OVERLAYS:
        return {"valid": False, "reason": f"Unknown overlay {overlay_code}"}
    info = KNOWN_OVERLAYS[overlay_code]
    levels = ["BASICA", "MEDIA", "ALTA"]
    if levels.index(project_category) < levels.index(info["category_min"]):
        return {
            "valid": False,
            "reason": f"Overlay {overlay_code} requires at least {info['category_min']}",
        }
    return {"valid": True, "extra_controls": list(info["extra_controls"])}
