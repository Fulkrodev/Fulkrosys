"""Cross-compliance detection. Deterministic rules, no LLM."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.onboarding import OnboardingResponse, OnboardingSession
from backend.app.motors.m16_onboarding.enums import SessionState

SECTOR_NORMATIVAS: dict[str, list[dict]] = {
    "fintech": [
        {"code": "ENS", "name": "Esquema Nacional de Seguridad", "obligatorio": True},
        {"code": "RGPD", "name": "RGPD/LOPDGDD", "obligatorio": True},
        {"code": "PCI-DSS", "name": "PCI-DSS v4.0", "obligatorio": False, "condition": "Si procesan tarjetas"},
        {"code": "PSD2", "name": "PSD2/SCA", "obligatorio": True, "condition": "Servicios de pago"},
        {"code": "DORA", "name": "DORA", "obligatorio": True, "condition": "Entidades financieras UE"},
        {"code": "NIS2", "name": "NIS2", "obligatorio": False, "condition": "Si esenciales/importantes"},
    ],
    "sanidad_privada": [
        {"code": "ENS", "name": "ENS", "obligatorio": True},
        {"code": "RGPD", "name": "RGPD/LOPDGDD", "obligatorio": True},
        {"code": "RGPD-SALUD", "name": "RGPD Art. 9 (datos salud)", "obligatorio": True},
    ],
    "saas_tech": [
        {"code": "ENS", "name": "ENS", "obligatorio": True},
        {"code": "RGPD", "name": "RGPD/LOPDGDD", "obligatorio": True},
        {"code": "ISO27001", "name": "ISO 27001:2022", "obligatorio": False, "condition": "Si quieren cert internacional"},
    ],
    "industria": [
        {"code": "ENS", "name": "ENS", "obligatorio": True},
        {"code": "RGPD", "name": "RGPD/LOPDGDD", "obligatorio": True},
        {"code": "NIS2", "name": "NIS2", "obligatorio": False, "condition": "Sector esencial"},
        {"code": "IEC62443", "name": "IEC 62443 (OT/ICS)", "obligatorio": False, "condition": "Si tienen SCADA/ICS"},
    ],
    "servicios_profesionales": [
        {"code": "ENS", "name": "ENS", "obligatorio": True},
        {"code": "RGPD", "name": "RGPD/LOPDGDD", "obligatorio": True},
        {"code": "PBC", "name": "Prevencion Blanqueo Capitales", "obligatorio": False, "condition": "Abogados, auditores"},
    ],
    "energia": [
        {"code": "ENS", "name": "ENS", "obligatorio": True},
        {"code": "RGPD", "name": "RGPD/LOPDGDD", "obligatorio": True},
        {"code": "NIS2", "name": "NIS2", "obligatorio": True, "condition": "Sector esencial"},
    ],
    "generico": [
        {"code": "ENS", "name": "ENS", "obligatorio": True},
        {"code": "RGPD", "name": "RGPD/LOPDGDD", "obligatorio": True},
    ],
}
# Fill remaining sectors with generico as fallback
for _s in ["retail_ecommerce", "logistica", "educacion_privada"]:
    if _s not in SECTOR_NORMATIVAS:
        SECTOR_NORMATIVAS[_s] = SECTOR_NORMATIVAS["generico"]


async def detect_compliance_obligations(
    session: AsyncSession, project_id: uuid.UUID, sector: str,
) -> dict:
    base = SECTOR_NORMATIVAS.get(sector, SECTOR_NORMATIVAS["generico"])
    responses = await _load_project_responses(session, project_id)

    enriched = []
    for norm in base:
        applies = norm.get("obligatorio", False)
        reason = "Obligatorio por sector" if applies else norm.get("condition", "Evaluar")

        if norm["code"] == "ISO27001" and _has_prev_iso27001(responses):
            enriched.append({**norm, "applies": True, "reason": "ISO 27001 previa — cross-compliance", "cross_compliance_opportunity": True})
            continue

        enriched.append({**norm, "applies": applies, "reason": reason, "cross_compliance_opportunity": False})

    applicable = [n for n in enriched if n["applies"]]
    return {
        "sector": sector,
        "total_normativas_evaluated": len(enriched),
        "applicable": applicable,
        "total_applicable": len(applicable),
        "potential": [n for n in enriched if not n["applies"] and n.get("condition")],
        "cross_compliance_opportunities": [n for n in enriched if n.get("cross_compliance_opportunity")],
        "verdict": "multi_compliance" if len(applicable) > 2 else "standard_ens_rgpd",
    }


async def _load_project_responses(session: AsyncSession, project_id: uuid.UUID) -> dict[str, Any]:
    r = await session.execute(
        select(OnboardingResponse.question_id, OnboardingResponse.answer_value)
        .join(OnboardingSession, OnboardingResponse.session_id == OnboardingSession.id)
        .where(OnboardingSession.project_id == project_id, OnboardingSession.estado == SessionState.COMPLETED.value)
    )
    return {row[0]: row[1] for row in r.all()}


def _response_matches_any(responses: dict, qid: str, values: list) -> bool:
    raw = responses.get(qid)
    if raw is None:
        return False
    answer = raw.get("value") if isinstance(raw, dict) else raw
    if isinstance(answer, list):
        return any(v in answer for v in values)
    return answer in values


# Capa de normalización drift #6: la "experiencia previa en seguridad" vive bajo varias
# keys según el sector (servicios_prof: q-proyectos_previos_seguridad; 9 sectores:
# q-experiencia_previa_certificacion; industria: q-certificacion_iso con valor `iso_27001`).
_PREV_SEC_KEYS = [
    "q-experiencia_previa_certificacion",
    "q-proyectos_previos_seguridad",
    "q-certificacion_iso",
    "q-certificaciones_sector_previas",
]


def _has_prev_iso27001(responses: dict) -> bool:
    """ISO 27001 previa, normalizando `iso_27001`→`iso27001` (drift industria · #6)."""
    for qid in _PREV_SEC_KEYS:
        raw = responses.get(qid)
        if raw is None:
            continue
        answer = raw.get("value") if isinstance(raw, dict) and "value" in raw else raw
        vals = answer if isinstance(answer, list) else [answer]
        if any(str(v).replace("_", "") == "iso27001" for v in vals):
            return True
    return False
