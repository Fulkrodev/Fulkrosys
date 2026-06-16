"""M23 Sesion 8 Paso 2 — Extensiones al retainer_service existente.

Agrega sobre el base service (`retainer_service.py`):
- R_MICRO tier (4o perfil segun imagen pricing 2026-04-21)
- Pricing lookup desde pricing_catalog (no hardcoded)
- suggest_tier(project_id) segun categoria + empleados + complejidad
- calculate_health_status mapea rag_status existente a verde/ambar/rojo
- schedule_renewal_prep (disparado desde Celery beat diario)
- trigger_material_change_audit (crea actividad extraordinaria)
- initialize_retainer_complete: crea contract + calendario 12m + primera
  factura (wrapper sobre create_retainer + generate_annual_activities +
  M15 generate_retainer_invoice)
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.retainer import (
    PricingCatalog, RetainerActivity, RetainerContract,
    RetainerQuarterlyReport,
)


# ════════════════════════════════════════════════════════════════════
# R_MICRO cadencias (adendum al existing CADENCES_BY_PROFILE)
# ════════════════════════════════════════════════════════════════════

CADENCES_R_MICRO = {
    "comite_seguridad": {"frecuencia": "semestral", "meses": [6, 12]},
    "reporte_trimestral": {"frecuencia": "trimestral",
                            "meses": [3, 6, 9, 12]},
    "revision_privilegios": {"frecuencia": "anual", "meses": [10]},
    "vigilancia_vulnerabilidades": {"frecuencia": "mensual"},
    "simulacro_phishing": {"frecuencia": "anual", "meses": [9]},
    "prueba_continuidad": {"frecuencia": "anual", "meses": [11]},
    # No incluye auditoria interna (se oferta como extra)
    "revision_ar_dda": {"frecuencia": "anual", "meses": [7]},
    "formacion_anual": {"frecuencia": "anual", "meses": [5]},
}


SLA_R_MICRO_HOURS = 120  # best effort, SLA 120h


# ════════════════════════════════════════════════════════════════════
# Pricing lookup
# ════════════════════════════════════════════════════════════════════

async def get_tier_price(db: AsyncSession, tier_code: str) -> Decimal | None:
    """Busca precio base del tier en pricing_catalog."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    r = await db.execute(
        select(PricingCatalog).where(
            PricingCatalog.category == "retainer",
            PricingCatalog.tier_code == tier_code,
            PricingCatalog.is_active.is_(True),
            PricingCatalog.deleted_at.is_(None),
        ).order_by(PricingCatalog.effective_from.desc()).limit(1)
    )
    row = r.scalar_one_or_none()
    return Decimal(str(row.base_price)) if row else None


async def get_tier_extras(
    db: AsyncSession, tier_code: str,
) -> dict[str, Any]:
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    r = await db.execute(
        select(PricingCatalog).where(
            PricingCatalog.category == "retainer",
            PricingCatalog.tier_code == tier_code,
            PricingCatalog.is_active.is_(True),
            PricingCatalog.deleted_at.is_(None),
        ).limit(1)
    )
    row = r.scalar_one_or_none()
    return dict(row.extras_jsonb or {}) if row else {}


# ════════════════════════════════════════════════════════════════════
# suggest_tier — recomendacion basada en categoria + empleados + sector
# ════════════════════════════════════════════════════════════════════

REGULATED_SECTORS = {
    "sanidad_privada", "sanidad", "fintech", "financiero",
    "administracion_publica", "admin_publica", "seguros",
    "telecom", "energia", "farma",
}


def suggest_tier(
    categoria: str,
    empleados: int,
    sector: str | None = None,
    ubicaciones: int = 1,
    datos_sensibles: bool = False,
) -> dict[str, Any]:
    """Sugerencia de tier retainer a partir del perfil del proyecto.

    Logic:
    - Categoria ALTA + complejidad alta -> R_PLUS
    - Categoria MEDIA + >=150 empleados o multi-sede -> R_PLUS
    - Categoria MEDIA -> R_STD
    - Categoria BASICA + regulado -> R_LITE
    - Categoria BASICA -> R_MICRO
    """
    cat = (categoria or "BASICA").upper()
    regulado = sector and sector.lower() in REGULATED_SECTORS
    is_multi = ubicaciones >= 2

    if cat == "ALTA":
        tier = "R_PLUS"
        reason = "Categoria ALTA requiere cadencia mensual + pentest anual"
    elif cat == "MEDIA" and (empleados >= 150 or is_multi or datos_sensibles):
        tier = "R_PLUS"
        reason = (
            f"Categoria MEDIA compleja (empleados={empleados}, "
            f"multi-sede={is_multi}, sensibles={datos_sensibles}) -> R_PLUS"
        )
    elif cat == "MEDIA":
        tier = "R_STD"
        reason = "Categoria MEDIA estandar (base del negocio)"
    elif cat == "BASICA" and regulado:
        tier = "R_LITE"
        reason = f"Categoria BASICA en sector regulado ({sector})"
    else:
        tier = "R_MICRO"
        reason = "Categoria BASICA sector no regulado, empresa pequena"
    from backend.app.motors.m23_retainer.retainer_service import (
        tier_to_commercial,
    )
    return {
        "tier_sugerido": tier,
        "tier_comercial": tier_to_commercial(tier),  # #33 · label cliente
        "justificacion": reason,
        "categoria_evaluada": cat, "empleados": empleados,
        "sector_regulado": regulado, "multi_ubicacion": is_multi,
    }


# ════════════════════════════════════════════════════════════════════
# calculate_health_status — traduce rag_status existente a verde/ambar/rojo
# ════════════════════════════════════════════════════════════════════

async def calculate_health_status(
    db: AsyncSession, retainer_contract_id: uuid.UUID,
) -> dict[str, Any]:
    """Verde/Ambar/Rojo segun activities + drift events + renewal clock."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    rc = await db.get(RetainerContract, retainer_contract_id)
    if rc is None:
        raise ValueError(f"RetainerContract {retainer_contract_id} no existe")

    today = date.today()

    # 1. activities overdue
    r = await db.execute(
        select(func.count(RetainerActivity.id)).where(
            RetainerActivity.retainer_contract_id == retainer_contract_id,
            RetainerActivity.estado.in_(["programada", "en_curso"]),
            RetainerActivity.fecha_programada < today,
            RetainerActivity.deleted_at.is_(None),
        )
    )
    overdue = r.scalar() or 0

    # 2. activities proximas 30d
    r = await db.execute(
        select(func.count(RetainerActivity.id)).where(
            RetainerActivity.retainer_contract_id == retainer_contract_id,
            RetainerActivity.estado == "programada",
            RetainerActivity.fecha_programada >= today,
            RetainerActivity.fecha_programada <= today + timedelta(days=30),
            RetainerActivity.deleted_at.is_(None),
        )
    )
    proximas = r.scalar() or 0

    # 3. drift events CRITICAL open
    from backend.app.models.retainer import RetainerDriftEvent
    r = await db.execute(
        select(func.count(RetainerDriftEvent.id)).where(
            RetainerDriftEvent.retainer_contract_id == retainer_contract_id,
            RetainerDriftEvent.severidad == "CRITICAL",
            RetainerDriftEvent.estado.in_(["open", "acknowledged"]),
            RetainerDriftEvent.deleted_at.is_(None),
        )
    )
    drift_critical = r.scalar() or 0

    # 4. renewal clock
    renewal_urgency = rc.renewal_status in {
        "T_MINUS_30", "LAPSED",
    }

    # Scoring
    if drift_critical > 0 or overdue >= 3 or renewal_urgency:
        health = "rojo"
    elif overdue >= 1 or drift_critical == 0 and proximas >= 5:
        health = "ambar"
    else:
        health = "verde"

    return {
        "health": health,
        "drivers": {
            "overdue_activities": overdue,
            "proximas_30d": proximas,
            "drift_critical_open": drift_critical,
            "renewal_status": rc.renewal_status,
            "renewal_urgency": renewal_urgency,
        },
        "rag_status_db": rc.rag_status,
    }


# ════════════════════════════════════════════════════════════════════
# renewal_prep + material_change
# ════════════════════════════════════════════════════════════════════

async def schedule_renewal_prep(
    db: AsyncSession,
    retainer_contract_id: uuid.UUID,
    *,
    months_before: int = 3,
) -> RetainerActivity:
    """Crea actividad renewal_prep 3 meses antes del aniversario bianual.

    Se invoca por el Celery beat `renewal_trigger` cuando se detecta
    que un proyecto esta a X meses del aniversario de certificacion.
    """
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    rc = await db.get(RetainerContract, retainer_contract_id)
    if rc is None:
        raise ValueError(f"RetainerContract {retainer_contract_id} no existe")

    renewal_date = rc.next_renewal_date or (
        (rc.inicio or date.today()) + timedelta(days=730)
    )
    fecha_programada = renewal_date - timedelta(days=months_before * 30)

    # Idempotente: si ya existe una actividad renewal_prep para este
    # retainer con la misma fecha, no duplicar.
    r = await db.execute(
        select(RetainerActivity).where(
            RetainerActivity.retainer_contract_id == retainer_contract_id,
            RetainerActivity.tipo_actividad == "renewal_prep",
            RetainerActivity.fecha_programada == fecha_programada,
            RetainerActivity.deleted_at.is_(None),
        )
    )
    existing = r.scalar_one_or_none()
    if existing:
        return existing

    activity = RetainerActivity(
        retainer_contract_id=retainer_contract_id,
        project_id=rc.project_id,
        tipo_actividad="renewal_prep",
        titulo="Preparacion re-certificacion bianual",
        descripcion=(
            f"Preparar dossier de re-certificacion para auditoria externa. "
            f"Fecha aniversario: {renewal_date}. "
            f"Incluye: actualizar MAGERIT + DdA + politicas vigentes + "
            f"dossier completo M9."
        ),
        fecha_programada=fecha_programada,
        estado="programada",
        horas_estimadas=16.0,
        prioridad="alta",
    )
    db.add(activity)
    await db.flush()
    return activity


async def trigger_material_change_audit(
    db: AsyncSession,
    project_id: uuid.UUID,
    change_description: str,
    *,
    urgent: bool = False,
) -> RetainerActivity:
    """Cliente notifica cambio material -> crea actividad extraordinaria."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    r = await db.execute(
        select(RetainerContract).where(
            RetainerContract.project_id == project_id,
            RetainerContract.estado == "active",
            RetainerContract.deleted_at.is_(None),
        ).limit(1)
    )
    rc = r.scalar_one_or_none()
    if rc is None:
        raise ValueError(
            f"No hay retainer activo para project_id={project_id}"
        )

    dias_delay = 7 if urgent else 21
    activity = RetainerActivity(
        retainer_contract_id=rc.id,
        project_id=project_id,
        tipo_actividad="auditoria_extraordinaria_cambio_material",
        titulo=f"Auditoria extraordinaria - {change_description[:80]}",
        descripcion=(
            f"Cambio material reportado por el cliente. Accion: analizar "
            f"impacto en categorizacion + DdA + ARMAGERIT. "
            f"Descripcion: {change_description}"
        ),
        fecha_programada=date.today() + timedelta(days=dias_delay),
        estado="programada",
        horas_estimadas=8.0 if not urgent else 12.0,
        prioridad="urgente" if urgent else "alta",
    )
    db.add(activity)
    await db.flush()
    return activity


# ════════════════════════════════════════════════════════════════════
# Quarterly / annual report generation
# ════════════════════════════════════════════════════════════════════

def _compute_period_bounds(
    period_type: str, reference: date,
) -> tuple[date, date]:
    """Devuelve (start, end) del periodo terminado (completo).

    - trimestral: trimestre anterior al de `reference`
    - anual: año anterior al de `reference`
    """
    if period_type == "anual":
        return date(reference.year - 1, 1, 1), date(reference.year - 1, 12, 31)

    # Trimestral: calcular trimestre anterior
    month = reference.month
    year = reference.year
    curr_q = (month - 1) // 3 + 1  # 1..4
    prev_q = curr_q - 1
    prev_year = year
    if prev_q == 0:
        prev_q = 4
        prev_year = year - 1
    start_month = (prev_q - 1) * 3 + 1
    end_month = start_month + 2
    from calendar import monthrange
    end_day = monthrange(prev_year, end_month)[1]
    return (
        date(prev_year, start_month, 1),
        date(prev_year, end_month, end_day),
    )


async def generate_quarterly_report(
    db: AsyncSession,
    retainer_contract_id: uuid.UUID,
    period_type: str = "trimestral",
    reference_date: date | None = None,
) -> RetainerQuarterlyReport:
    """Agrega metricas del periodo y crea RetainerQuarterlyReport.

    El DOCX E-801 / E-802 se renderiza via M6 DocumentFactory (aparte).
    Aqui solo creamos el registro + JSON resumen.
    """
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    rc = await db.get(RetainerContract, retainer_contract_id)
    if rc is None:
        raise ValueError(f"Retainer {retainer_contract_id} no existe")

    ref = reference_date or date.today()
    start, end = _compute_period_bounds(period_type, ref)

    # Activities del periodo
    base_where = (
        RetainerActivity.retainer_contract_id == retainer_contract_id,
        RetainerActivity.deleted_at.is_(None),
        RetainerActivity.fecha_programada >= start,
        RetainerActivity.fecha_programada <= end,
    )
    completed = (await db.execute(
        select(func.count(RetainerActivity.id)).where(
            *base_where, RetainerActivity.estado == "completada",
        )
    )).scalar() or 0
    pending = (await db.execute(
        select(func.count(RetainerActivity.id)).where(
            *base_where, RetainerActivity.estado.in_(["programada", "en_curso"]),
        )
    )).scalar() or 0
    overdue = (await db.execute(
        select(func.count(RetainerActivity.id)).where(
            *base_where, RetainerActivity.estado == "vencida",
        )
    )).scalar() or 0

    # Drift events del periodo
    from backend.app.models.retainer import RetainerDriftEvent
    r = await db.execute(
        select(func.count(RetainerDriftEvent.id)).where(
            RetainerDriftEvent.retainer_contract_id == retainer_contract_id,
            RetainerDriftEvent.severidad.in_(["HIGH", "CRITICAL"]),
            RetainerDriftEvent.created_at >= datetime(start.year, start.month, start.day, tzinfo=timezone.utc),
            RetainerDriftEvent.created_at <= datetime(end.year, end.month, end.day, 23, 59, 59, tzinfo=timezone.utc),
            RetainerDriftEvent.deleted_at.is_(None),
        )
    )
    incidents = r.scalar() or 0

    # FIX(claim/impl): normativa_changes_relevant y vulns_critical eran 0 fijos
    # enviados al portal cliente. Se computan del estado real (m23 normativa_alerts
    # del periodo + m08 findings CRITICAL/ALTA del proyecto en el periodo).
    from sqlalchemy import text as sa_text
    _ps = datetime(start.year, start.month, start.day, tzinfo=timezone.utc)
    _pe = datetime(end.year, end.month, end.day, 23, 59, 59, tzinfo=timezone.utc)
    normativa_changes_relevant = (await db.execute(
        sa_text(
            "SELECT count(*) FROM normativa_alerts WHERE detected_at BETWEEN :s AND :e"
        ),
        {"s": _ps, "e": _pe},
    )).scalar() or 0
    vulns_critical = 0
    if rc.project_id:
        vulns_critical = (await db.execute(
            sa_text(
                "SELECT count(*) FROM findings WHERE project_id = :pid "
                "AND severidad IN ('CRITICAL', 'critical', 'ALTA', 'HIGH', 'high') "
                "AND created_at BETWEEN :s AND :e"
            ),
            {"pid": str(rc.project_id), "s": _ps, "e": _pe},
        )).scalar() or 0

    health = await calculate_health_status(db, retainer_contract_id)

    report = RetainerQuarterlyReport(
        retainer_contract_id=retainer_contract_id,
        project_id=rc.project_id,
        period_type=period_type,
        period_start=start, period_end=end,
        activities_completed=completed,
        activities_pending=pending,
        activities_overdue=overdue,
        incidents_detected=incidents,
        normativa_changes_relevant=normativa_changes_relevant,
        vulns_critical=vulns_critical,
        rag_overall=health["health"],
        summary_jsonb={
            "health_drivers": health["drivers"],
            "period_type": period_type,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    db.add(report)
    await db.flush()
    return report


__all__ = [
    "CADENCES_R_MICRO",
    "SLA_R_MICRO_HOURS",
    "get_tier_price",
    "get_tier_extras",
    "suggest_tier",
    "calculate_health_status",
    "schedule_renewal_prep",
    "trigger_material_change_audit",
    "generate_quarterly_report",
    "_compute_period_bounds",
]
