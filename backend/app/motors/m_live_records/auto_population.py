"""Auto-population live_records desde eventos M19/M28/M14 · sub-atom 1.C.B fase 3c.

Patron non-invasive: M19/M28/M14 NO importan live_records. Tres helpers async
puros materializan entradas E-305 / E-308 / E-312 a partir del row insertado
en motores origen. Los listeners SQLAlchemy ``after_insert`` (ver
``listeners.py``) disparan ``_safe_fire`` con un snapshot de los campos
necesarios -- crucial: NO se accede al session del listener desde el task
asincrono porque puede estar mid-transaction o cerrado.

Failure handling (LECCION-OPS-033 sostenido):
- Cada helper captura excepciones internas (log warning).
- NUNCA propagan: auto-population es side-effect, su fallo NO debe romper el
  flow del motor origen (incidente queda creado · solo se pierde la entrada
  espejo del libro vivo).
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import async_session, set_tenant_context
from backend.app.motors.m_live_records.service import LiveRecordsService

logger = logging.getLogger(__name__)


_NIST_DEFAULT_PHASE = "deteccion"
_PROVIDER_ASSESSMENT_RISK_DECISION_MAP: dict[str, str] = {
    "APROBADO": "renovar",
    "CONDICIONAL": "monitorizar",
    "PENDIENTE": "monitorizar",
    "RECHAZADO": "rescindir",
}
_PROVIDER_ASSESSMENT_RISK_SCORE_DEFAULT = 5.0


def _safe_str(v: Any, max_len: int | None = None) -> str:
    s = "" if v is None else str(v)
    return s[:max_len] if max_len else s


async def _create_in_new_session(
    *,
    project_id: uuid.UUID,
    register_type: str,
    entry_data: dict[str, Any],
    created_by: uuid.UUID,
) -> uuid.UUID | None:
    """Open a NEW session (post-parent-commit) and create the live_records row.

    Wrapped in try/except: any failure logs a warning and returns None
    instead of propagating (side-effect must not break the origin motor).
    """
    try:
        async with async_session() as session:
            await set_tenant_context(session, project_id=project_id)
            svc = LiveRecordsService(session)
            record = await svc.create_record(
                project_id=project_id,
                register_type=register_type,
                entry_data=entry_data,
                created_by=created_by,
            )
            await session.commit()
            return record.id
    except Exception as exc:  # noqa: BLE001 (deliberately broad)
        logger.warning(
            "auto_populate %s failed for project=%s: %s",
            register_type,
            project_id,
            exc,
        )
        return None


# ─── M19 Incident → E-305 Libro de Incidentes ─────────────────────────────


async def auto_populate_incident_to_e305(
    *,
    project_id: uuid.UUID,
    incident_id: uuid.UUID,
    severidad: str | None,
    descripcion: str | None,
    fecha: datetime | None,
    created_by: uuid.UUID | None = None,
    db: AsyncSession | None = None,
) -> uuid.UUID | None:
    """M19 incident insert → E-305 entry.

    ``db`` opcional permite usar el session del caller (tests) en lugar de
    abrir uno nuevo. Production listener invoca sin ``db`` para abrir session
    separada (transaccion independiente).
    """
    sev_raw = (severidad or "medio").lower().strip()
    sev_map = {
        "critica": "critico",
        "critical": "critico",
        "alta": "alto",
        "media": "medio",
        "baja": "bajo",
        "info": "informativo",
        "informativa": "informativo",
    }
    nivel = sev_map.get(sev_raw, sev_raw if sev_raw in {
        "critico", "alto", "medio", "bajo", "informativo",
    } else "medio")

    desc = _safe_str(descripcion, max_len=10_000) or "(sin descripción)"
    fecha_iso = (fecha or datetime.now(timezone.utc)).isoformat()

    entry_data = {
        "codigo_incidente": f"INC-{str(incident_id)[:8].upper()}",
        "fecha_deteccion": fecha_iso,
        "nivel_criticidad": nivel,
        "descripcion_breve": desc[:200],
        "descripcion_detallada": desc,
        "activos_afectados": [],
        "notificado_lucia": False,
        "notificado_aepd": False,
        "fase_nist": _NIST_DEFAULT_PHASE,
    }

    creator = created_by or uuid.UUID("00000000-0000-0000-0000-000000000000")

    if db is not None:
        try:
            svc = LiveRecordsService(db)
            await set_tenant_context(db, project_id=project_id)
            record = await svc.create_record(
                project_id=project_id,
                register_type="E-305",
                entry_data=entry_data,
                created_by=creator,
            )
            return record.id
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "auto_populate E-305 (caller session) failed for project=%s: %s",
                project_id,
                exc,
            )
            return None

    return await _create_in_new_session(
        project_id=project_id,
        register_type="E-305",
        entry_data=entry_data,
        created_by=creator,
    )


# ─── M28 Change → E-308 Libro de Cambios ──────────────────────────────────


async def auto_populate_change_to_e308(
    *,
    project_id: uuid.UUID,
    change_id: uuid.UUID,
    descripcion: str | None,
    solicitante: str | None,
    fecha: datetime | None = None,
    created_by: uuid.UUID | None = None,
    db: AsyncSession | None = None,
) -> uuid.UUID | None:
    """M28 change insert → E-308 entry."""
    desc = _safe_str(descripcion, max_len=10_000) or "(sin descripción)"
    fecha_iso = (fecha or datetime.now(timezone.utc)).date().isoformat()
    solic = _safe_str(solicitante, max_len=200) or "(no especificado)"

    entry_data = {
        "codigo_cambio": f"CHG-{str(change_id)[:8].upper()}",
        "tipo_cambio": "normal",
        "descripcion": desc,
        "sistemas_afectados": [],
        "fecha_solicitud": fecha_iso,
        "solicitante": solic,
        "resultado": "pendiente",
    }

    creator = created_by or uuid.UUID("00000000-0000-0000-0000-000000000000")

    if db is not None:
        try:
            svc = LiveRecordsService(db)
            await set_tenant_context(db, project_id=project_id)
            record = await svc.create_record(
                project_id=project_id,
                register_type="E-308",
                entry_data=entry_data,
                created_by=creator,
            )
            return record.id
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "auto_populate E-308 (caller session) failed for project=%s: %s",
                project_id,
                exc,
            )
            return None

    return await _create_in_new_session(
        project_id=project_id,
        register_type="E-308",
        entry_data=entry_data,
        created_by=creator,
    )


# ─── M14 ProviderAssessment → E-312 Evaluaciones Proveedores ──────────────


async def auto_populate_provider_assessment_to_e312(
    *,
    project_id: uuid.UUID,
    assessment_id: uuid.UUID,
    provider_id: uuid.UUID,
    assessment_date: Any,
    assessor: str | None,
    risk_score: float | None,
    risk_level: str | None,
    decision: str | None,
    created_by: uuid.UUID | None = None,
    db: AsyncSession | None = None,
) -> uuid.UUID | None:
    """M14 provider_assessments insert → E-312 entry."""
    if hasattr(assessment_date, "isoformat"):
        date_iso = assessment_date.isoformat()
    else:
        date_iso = str(assessment_date) if assessment_date else datetime.now(
            timezone.utc
        ).date().isoformat()

    # risk_score viene en 0-1 desde M14; el schema E-312 espera 0-10.
    if risk_score is None:
        punt = _PROVIDER_ASSESSMENT_RISK_SCORE_DEFAULT
    else:
        try:
            punt = float(risk_score) * 10.0
            punt = max(0.0, min(10.0, punt))
        except (TypeError, ValueError):
            punt = _PROVIDER_ASSESSMENT_RISK_SCORE_DEFAULT

    decision_upper = (decision or "PENDIENTE").upper()
    decision_e312 = _PROVIDER_ASSESSMENT_RISK_DECISION_MAP.get(
        decision_upper, "monitorizar",
    )

    periodo = date_iso[:7] if len(date_iso) >= 7 else "2026-01"

    entry_data = {
        "codigo_evaluacion": f"EVA-{str(assessment_id)[:8].upper()}",
        "proveedor_codigo": str(provider_id),
        "periodo": periodo,
        "fecha_evaluacion": date_iso,
        "puntuacion_global": punt,
        "evaluador": _safe_str(assessor, max_len=200) or "(no especificado)",
        "decision": decision_e312,
    }
    if risk_level:
        entry_data["hallazgos"] = [f"risk_level={risk_level}"]

    creator = created_by or uuid.UUID("00000000-0000-0000-0000-000000000000")

    if db is not None:
        try:
            svc = LiveRecordsService(db)
            await set_tenant_context(db, project_id=project_id)
            record = await svc.create_record(
                project_id=project_id,
                register_type="E-312",
                entry_data=entry_data,
                created_by=creator,
            )
            return record.id
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "auto_populate E-312 (caller session) failed for project=%s: %s",
                project_id,
                exc,
            )
            return None

    return await _create_in_new_session(
        project_id=project_id,
        register_type="E-312",
        entry_data=entry_data,
        created_by=creator,
    )
