"""FASE 0 · Gobierno · orquestador thin pure-functional (P10-F09).

Ejecutable 8 Pasada 16 F0-5. NO es un motor nuevo ni una tabla de estado nueva
(decisión Marcos): es un COMPOSER puro que calcula el estado de la FASE 0 de
gobierno reuniendo lo que YA existe:

  * secuencia WBS FASE 0 (m17_planning.wbs_catalog · WBS-001..005)
  * documentos generados (m06 · E-155 alcance · E-002 roles · E-003 comité ·
    E-150 plan) leídos de la tabla ``documents``
  * roles + separación RSeg≠RSis (m30_client_contacts · canónico · category-aware)
  * cadencia del comité (m_meetings.evaluate_comite_cadence · F0-4)

Branch por categoría (mirror m_audit_accompaniment): BÁSICA acumulable · MEDIA/ALTA
separación obligatoria + comité. Devuelve un dict JSON-serializable (sin
side-effects) para el panel admin / checklist FASE 0.
"""
from __future__ import annotations

import uuid

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m30_client_contacts.roles_ens import (
    validate_role_segregation,
)
from backend.app.motors.m_meetings.actas_service import evaluate_comite_cadence


# E-codes de gobierno FASE 0 por paso (fuente: WBS FASE 0 + catálogo m06).
# documento de alcance canónico = E-155 (F0 Batch E · CCN-STIC 805/809).
_ALL = ("BASICA", "MEDIA", "ALTA")
_FASE0_STEPS: tuple[dict, ...] = (
    {"key": "kickoff", "label": "Reunión de arranque", "wbs": "WBS-001",
     "ecode": None, "categorias": _ALL},
    # R24 · primer acto formal de la Dirección: decisión de adecuar al ENS (org.1).
    {"key": "decision", "label": "Decisión de adecuación de la Dirección", "wbs": "WBS-001",
     "ecode": "E-010", "categorias": _ALL},
    {"key": "alcance", "label": "Documento de Alcance del SGSI", "wbs": "WBS-002",
     "ecode": "E-155", "categorias": _ALL},
    {"key": "roles", "label": "Nombramiento de roles ENS", "wbs": "WBS-003",
     "ecode": "E-002", "categorias": _ALL},
    {"key": "comite", "label": "Constitución del Comité de Seguridad", "wbs": "WBS-004",
     "ecode": "E-003", "categorias": ("MEDIA", "ALTA")},
    {"key": "plan", "label": "Plan de adecuación al ENS", "wbs": "WBS-005",
     "ecode": "E-150", "categorias": _ALL},
)

_GOVERNANCE_ECODES = {"E-010", "E-155", "E-002", "E-003", "E-150"}


async def compute_fase0_governance_state(
    db: AsyncSession, project_id: uuid.UUID,
) -> dict:
    """Calcula el estado de la FASE 0 de gobierno (puro · sin side-effects)."""
    row = (await db.execute(sa_text(
        "SELECT client_id, categoria_objetivo FROM projects WHERE id = :pid"
    ), {"pid": str(project_id)})).first()
    client_id = row[0] if row else None
    categoria = (row[1] if row and row[1] else "BASICA").upper()
    branch = "MEDIO_ALTO" if categoria in {"MEDIA", "ALTA"} else "BASICO"

    # Documentos de gobierno generados para el proyecto.
    docs_res = await db.execute(sa_text(
        "SELECT DISTINCT template_codigo FROM documents "
        "WHERE project_id = :pid AND template_codigo IS NOT NULL "
        "AND deleted_at IS NULL"
    ), {"pid": str(project_id)})
    generated = {r[0] for r in docs_res.fetchall()}

    # Separación de roles (m30 canónico · category-aware). Solo si hay client_id.
    separacion = None
    if client_id is not None:
        report = await validate_role_segregation(db, client_id, categoria)
        sep_violations = [
            {"rule": v.rule, "severity": v.severity, "detail": v.detail}
            for v in report.violations if v.rule == "CCN-STIC-801"
        ]
        separacion = {
            "compliant": not sep_violations,
            "obligatoria": branch == "MEDIO_ALTO",
            "violations": sep_violations,
        }

    # Cadencia del comité (solo MEDIA/ALTA · F0-4).
    cadencia_comite = None
    if branch == "MEDIO_ALTO":
        cadencia_comite = await evaluate_comite_cadence(db, project_id)

    kickoff_started = bool(generated & _GOVERNANCE_ECODES)

    steps: list[dict] = []
    for spec in _FASE0_STEPS:
        if categoria not in spec["categorias"]:
            continue
        ecode = spec["ecode"]
        if ecode is None:  # kickoff
            done = kickoff_started
        else:
            done = ecode in generated
        step = {
            "key": spec["key"],
            "label": spec["label"],
            "wbs": spec["wbs"],
            "ecode": ecode,
            "done": done,
        }
        # Enriquecimiento por paso.
        if spec["key"] == "roles" and separacion is not None:
            # El paso roles NO está completo si la separación obligatoria falla.
            step["separacion"] = separacion
            if separacion["obligatoria"] and not separacion["compliant"]:
                step["done"] = False
                step["bloqueo"] = "separacion_rseg_rsis_no_conforme"
        if spec["key"] == "comite" and cadencia_comite is not None:
            step["cadencia"] = cadencia_comite
            if cadencia_comite["alerta_pre_auditoria"]:
                step["done"] = False
        steps.append(step)

    total = len(steps)
    completos = sum(1 for s in steps if s["done"])
    siguiente = next((s["key"] for s in steps if not s["done"]), None)

    return {
        "project_id": str(project_id),
        "categoria": categoria,
        "branch": branch,
        "steps": steps,
        "total_steps": total,
        "completed_steps": completos,
        "progress_pct": round(100.0 * completos / total, 1) if total else 0.0,
        "next_step": siguiente,
        "fase0_completa": completos == total,
        "norma": "RD 311/2022 art. 11 · CCN-STIC 801 · WBS FASE 0 (P10-F09)",
    }
