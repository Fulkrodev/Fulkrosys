"""Maturity scoring L0-L5 per ENS domain. Deterministic, no LLM.

Based on CCN-STIC 804/808. Levels:
L0 Inexistente, L1 Inicial, L2 Repetible, L3 Definido, L4 Gestionado, L5 Optimizado.

PRINCIPIO DE DISEÑO · MADUREZ ≠ CONFORMIDAD (#6 · 2026-06-03):
Este motor mide MADUREZ (para dimensionar proyecto/propuesta). La CONFORMIDAD la
determina la SoA contra las medidas OBLIGATORIAS del nivel ENS, no este score. Un
cliente puede ser "maduro" y NO "conforme" (p.ej. ``mfa=solo_empleados`` puntúa +2
en madurez pero NO basta para conformidad ENS Alta, que exige MFA universal incl.
externos). NO presentar este scoring como conformidad ni mezclar los planos en UI.

Capa de normalización del drift (#6 · capa A · NO se tocan los 77 templates):
- Cada concepto acepta varias ``keys`` de cuestionario (mismo concepto, vocabulario
  divergente entre sectores · QUESTION_ALIASES).
- ``value_points`` mapea TODOS los valores de las variantes a puntos (tabla de
  equivalencias aprobada por Marcos · ver
  ``docs/audits/AUDIT_PUNTO_6_DRIFT_SCORING_RULES.md`` · VALUE_ALIASES).
- 1 entrada por concepto → ``max_possible`` = el máximo REAL del concepto (arregla el
  bug del ``max_possible`` inflado por reglas mutuamente excluyentes, que ponía un
  techo artificial a la madurez).
- ``_NEUTRAL_VALUES``: valores que NO puntúan NI cuentan como carencia (p.ej. DPO
  ``no_obligatorio``: una PYME que legalmente no necesita DPO no debe salir deficiente
  en mp.info por no tenerlo).
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.onboarding import OnboardingResponse, OnboardingSession
from backend.app.motors.m16_onboarding.enums import SessionState
from backend.app.motors.m16_onboarding.pkg_tools import pkg_get_stakeholder_roles

DOMAINS = {
    "org": "Marco organizativo",
    "op_acc": "Control de accesos",
    "op_exp": "Explotacion",
    "op_mon": "Monitorizacion",
    "op_cont": "Continuidad",
    "mp_com": "Comunicaciones",
    "mp_info": "Proteccion de informacion",
}

# Valores NEUTROS: ni puntúan ni cuentan en max_possible (no son carencia/rojo).
_NEUTRAL_VALUES = {"no_obligatorio"}

# Un concepto = una entrada. ``keys`` = alias de cuestionario (drift de KEY).
# ``value_points`` = puntos por valor (drift de VALOR). ``max_points`` = máximo real.
SCORING_CONCEPTS: list[dict] = [
    # ── org ───────────────────────────────────────────────────────────
    {"domain": "org", "concept": "sponsor_identificado", "source": "interlocutor",
     "max_points": 2, "description": "Sponsor ejecutivo identificado"},
    {"domain": "org", "concept": "experiencia_previa", "source": "question", "max_points": 1,
     "keys": ["q-experiencia_previa_certificacion", "q-proyectos_previos_seguridad",
              "q-certificacion_iso", "q-certificaciones_sector_previas"],
     "value_points": {"iso27001": 1, "iso_27001": 1, "ens_anterior": 1, "ens_previo": 1,
                      "otras": 1, "rgpd_lopdgdd": 1, "pcidss": 1,
                      "ninguna": 0, "sin_experiencia": 0,
                      "iso_9001": 0, "iso_14001": 0, "iso_45001": 0},
     "description": "Experiencia previa en seguridad"},
    {"domain": "org", "concept": "roles_coverage", "source": "pkg",
     "pkg_check": "stakeholder_roles_coverage", "threshold": 60, "max_points": 2,
     "description": "Roles ENS asignados >= 60%"},
    # ── op_acc ────────────────────────────────────────────────────────
    {"domain": "op_acc", "concept": "mfa", "source": "question", "max_points": 3,
     "keys": ["q-mfa_universal", "q-mfa_implantado"],
     "value_points": {"si_todos": 3, "empleados_y_clientes": 3, "completo": 3,
                      "solo_empleados": 2, "solo_privilegiados": 1, "parcial": 1,
                      "voluntario": 0, "no": 0},
     "description": "MFA"},
    {"domain": "op_acc", "concept": "identidad", "source": "question", "max_points": 1,
     "keys": ["q-proveedor_identidad", "q-email_identidad"],
     "value_points": {"microsoft_365": 1, "google_workspace": 1, "mixto": 1,
                      "active_directory": 1, "on_prem_ad": 1, "otro": 0},
     "description": "Identidad gestionada"},
    # ── op_exp ────────────────────────────────────────────────────────
    {"domain": "op_exp", "concept": "endpoints", "source": "question", "max_points": 2,
     "keys": ["q-endpoints_managed"],
     "value_points": {"si_mdm": 2, "solo_antivirus": 1, "no": 0},
     "description": "Gestion de endpoints"},
    {"domain": "op_exp", "concept": "pentest", "source": "question", "max_points": 2,
     "keys": ["q-pentest_ultimo", "q-ultimo_pentest", "q-pentest_frecuencia",
              "q-soc_pentest_recientes"],
     "value_points": {"ultimo_ano": 2, "trimestral": 2, "semestral": 2, "anual": 2,
                      "si_sin_hallazgos_criticos": 2,
                      "hace_1_3_anos": 1, "hace_1_2_anos": 1, "si_con_hallazgos": 1,
                      "mas_3_anos": 0, "mas_2_anos": 0, "nunca": 0, "no": 0},
     "description": "Pentest reciente"},
    # ── op_mon ────────────────────────────────────────────────────────
    {"domain": "op_mon", "concept": "siem", "source": "question", "max_points": 3,
     "keys": ["q-siem_presente", "q-siem_activo", "q-siem_soc"],
     "value_points": {True: 3, "siem_dedicado": 3, "cloud_native": 3,
                      "siem_soc_propio": 3, "soc_externo": 3,
                      "solo_siem": 2, "logs_centralizados": 1, False: 0, "no": 0},
     "description": "SIEM/monitorizacion"},
    # ── op_cont ───────────────────────────────────────────────────────
    {"domain": "op_cont", "concept": "backup", "source": "question", "max_points": 2,
     "keys": ["q-backup_estrategia", "q-backup_strategy"],
     # CRITERIO Marcos: script manual NO es continuidad fiable en ENS → scripts_manuales=0.
     "value_points": {"3_2_1": 2, "cloud": 2, "cloud_automatico": 2, "cloud_auto": 2,
                      "software_dedicado": 2,
                      "basico": 1, "manual": 1,
                      "scripts_manuales": 0, "ninguno": 0, "no_formal": 0},
     "description": "Backup"},
    # ── mp_com ────────────────────────────────────────────────────────
    {"domain": "mp_com", "concept": "infraestructura_identificada", "source": "question",
     "max_points": 1, "condition": "not_empty",
     "keys": ["q-cloud_providers", "q-cloud_provider", "q-cloud_uso"],
     "description": "Infraestructura conocida/identificada"},
    # ── mp_info ───────────────────────────────────────────────────────
    {"domain": "mp_info", "concept": "dpo", "source": "question", "max_points": 2,
     "keys": ["q-dpo_designado"],
     # CRITERIO Marcos: no_obligatorio es NEUTRO (ver _NEUTRAL_VALUES); boolean True = designado.
     "value_points": {True: 2, "interno": 2, "externo": 2,
                      False: 0, "no": 0, "deberiamos_pero_no": 0},
     "description": "DPO designado"},
    {"domain": "mp_info", "concept": "contratos_art28", "source": "question", "max_points": 2,
     "keys": ["q-contratos_art28_estado", "q-contratos_encargado_firmados",
              "q-contratos_proveedores_pagos"],
     "value_points": {"todos": 2, "mayoria": 1, "pocos": 0, "ninguno": 0},
     "description": "Contratos Art.28"},
]


def _points_to_level(points: int, max_possible: int) -> dict:
    if max_possible == 0:
        return {"level": 0, "label": "L0 — Inexistente", "percentage": 0}
    pct = points / max_possible
    if pct >= 0.9:
        return {"level": 5, "label": "L5 — Optimizado", "percentage": round(pct * 100)}
    elif pct >= 0.7:
        return {"level": 4, "label": "L4 — Gestionado", "percentage": round(pct * 100)}
    elif pct >= 0.5:
        return {"level": 3, "label": "L3 — Definido", "percentage": round(pct * 100)}
    elif pct >= 0.3:
        return {"level": 2, "label": "L2 — Repetible", "percentage": round(pct * 100)}
    elif pct > 0:
        return {"level": 1, "label": "L1 — Inicial", "percentage": round(pct * 100)}
    return {"level": 0, "label": "L0 — Inexistente", "percentage": 0}


def _unwrap(raw):
    """answer_value puede venir como {'value': x} o como x directo."""
    if isinstance(raw, dict) and "value" in raw:
        return raw["value"]
    return raw


def _first_answer(responses: dict, keys: list[str]):
    """Primer answer presente entre las keys alias (drift de KEY); None si ninguna."""
    for k in keys:
        if k in responses:
            return _unwrap(responses[k])
    return None


def _score_value(concept: dict, answer) -> tuple[int, bool]:
    """Devuelve (puntos, cuenta_en_max). cuenta_en_max=False si el valor es NEUTRO.

    multi_select: ignora valores neutros y toma el MÁXIMO entre los seleccionados
    (la mejor certificación/proveedor cuenta).
    """
    vp = concept["value_points"]
    if isinstance(answer, list):
        non_neutral = [v for v in answer if v not in _NEUTRAL_VALUES]
        if answer and not non_neutral:
            return 0, False  # todo neutro → neutral
        return max((vp.get(v, 0) for v in non_neutral), default=0), True
    if answer in _NEUTRAL_VALUES:
        return 0, False
    return vp.get(answer, 0), True


async def calculate_maturity(session: AsyncSession, project_id: uuid.UUID) -> dict:
    # Respuestas de cuestionario (cualquier sesión COMPLETED del proyecto).
    r = await session.execute(
        select(OnboardingResponse.question_id, OnboardingResponse.answer_value)
        .join(OnboardingSession, OnboardingResponse.session_id == OnboardingSession.id)
        .where(OnboardingSession.project_id == project_id, OnboardingSession.estado == SessionState.COMPLETED.value)
    )
    responses = {row[0]: row[1] for row in r.all()}

    # Sponsor identificado: derivado del interlocutor de la sesión (#6 · robusto, sin
    # exigir una pregunta técnica que solo 1 de 11 templates define).
    s = await session.execute(
        select(OnboardingSession.interlocutor_nombre)
        .where(OnboardingSession.project_id == project_id,
               OnboardingSession.estado == SessionState.COMPLETED.value,
               OnboardingSession.interlocutor_nombre.isnot(None))
        .limit(1)
    )
    interlocutor = s.scalar_one_or_none()
    sponsor_identificado = bool(interlocutor and str(interlocutor).strip())

    # Cobertura de roles ENS desde el grafo PKG.
    stakeholder_data = await pkg_get_stakeholder_roles(session, project_id)
    total_roles = len(stakeholder_data.get("ens_roles", {}))
    assigned = stakeholder_data.get("roles_assigned", 0)
    roles_coverage = round(100.0 * assigned / total_roles, 1) if total_roles else 0

    domain_scores: dict[str, dict] = {d: {"points": 0, "max_possible": 0, "rules_matched": []} for d in DOMAINS}

    for c in SCORING_CONCEPTS:
        dom = c["domain"]
        src = c["source"]
        counts = True

        if src == "interlocutor":
            points = c["max_points"] if sponsor_identificado else 0
        elif src == "pkg":
            points = c["max_points"] if roles_coverage >= c["threshold"] else 0
        else:  # question
            answer = _first_answer(responses, c["keys"])
            if answer is None:
                # No respondida = carencia (0 sobre max). La fuente cloud+copiloto
                # (#18/#22) cubrirá estos huecos para PYMEs sin perfil técnico.
                points = 0
            elif c.get("condition") == "not_empty":
                if isinstance(answer, list):
                    points = c["max_points"] if [v for v in answer if v not in _NEUTRAL_VALUES] else 0
                elif answer in _NEUTRAL_VALUES:
                    points, counts = 0, False
                else:
                    points = c["max_points"] if answer else 0
            else:
                points, counts = _score_value(c, answer)

        if not counts:
            continue
        domain_scores[dom]["max_possible"] += c["max_points"]
        domain_scores[dom]["points"] += points
        if points > 0:
            domain_scores[dom]["rules_matched"].append(c["description"])

    domains_result = {}
    total_points = 0
    total_max = 0
    for dk, dn in DOMAINS.items():
        ds = domain_scores[dk]
        level_info = _points_to_level(ds["points"], ds["max_possible"])
        domains_result[dk] = {"name": dn, "points": ds["points"], "max_possible": ds["max_possible"], **level_info, "rules_matched": ds["rules_matched"]}
        total_points += ds["points"]
        total_max += ds["max_possible"]

    overall = _points_to_level(total_points, total_max)
    return {
        "domains": domains_result,
        "overall": {**overall, "total_points": total_points, "total_max_possible": total_max},
        "verdict": "mature" if overall["level"] >= 3 else "developing" if overall["level"] >= 2 else "immature",
    }
