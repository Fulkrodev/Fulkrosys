"""Log & Monitoring Assessment (M22-C).

Evalua la capacidad de logging/SIEM/monitorizacion del cliente. Determina
cumplimiento op.exp.8 (Anexo II ENS) y calcula nivel de madurez L0-L5
con reglas deterministas. Genera alertas para gaps criticos.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.discovery import DiscoveryAlert, LoggingAssessment


MATURITY_RULES: dict[str, str] = {
    "L0": "Sin logging centralizado, sin SIEM, sin alertas",
    "L1": "Logging parcial (algunos sistemas), sin SIEM o SIEM sin configurar",
    "L2": "SIEM basico operativo, cobertura >50%, retencion cumple minimos",
    "L3": "SIEM gestionado, cobertura >80%, alertas activas revisadas, retencion ENS",
    "L4": "SOC activo, >90% cobertura, casos de uso definidos",
    "L5": "SOC 24/7, correlacion avanzada, threat hunting, mejora continua",
}

OP_EXP_8_CHECKS: list[str] = [
    "registro_accesos_usuarios",
    "registro_cambios_configuracion",
    "registro_actividad_privilegiada",
    "trazabilidad_acciones_usuario",
    "proteccion_integridad_logs",
    "sincronizacion_relojes_ntp",
]

# ENS Anexo III: 6 meses (Media), 2 anos (Alta)
ENS_RETENTION_MIN_DAYS = {"basica": 90, "media": 180, "alta": 730}


def _check_op_exp_8(logging_data: dict) -> tuple[bool, list[str]]:
    """Evalua los 6 controles de op.exp.8 basandose en logging_data."""
    controls = (logging_data or {}).get("op_exp_8_controles") or {}
    gaps: list[str] = [
        check for check in OP_EXP_8_CHECKS if not controls.get(check)
    ]
    cumple = not gaps
    return cumple, gaps


def _avg_coverage(logging_data: dict) -> int:
    cob = (logging_data or {}).get("cobertura") or {}
    vals = [
        cob.get("servidores", 0) or 0,
        cob.get("red", 0) or 0,
        cob.get("aplicaciones", 0) or 0,
        cob.get("endpoints", 0) or 0,
    ]
    return sum(vals) // max(1, len([v for v in vals if v is not None]))


def _calculate_maturity(data: dict, cumple_retencion: bool) -> str:
    tiene_siem = bool((data.get("siem") or {}).get("tiene"))
    avg_cob = _avg_coverage(data)
    alertas_activas = bool((data.get("alertas") or {}).get("activas"))
    casos_uso = int((data.get("alertas") or {}).get("casos_uso") or 0)
    revisadas_por = str((data.get("alertas") or {}).get("revisadas_por") or "").lower()
    soc_24_7 = bool(data.get("soc_24_7"))
    threat_hunting = bool(data.get("threat_hunting"))
    soc_activo = revisadas_por in {"equipo_soc", "proveedor_externo"}

    if soc_24_7 and threat_hunting and avg_cob >= 95:
        return "L5"
    if soc_activo and avg_cob >= 90 and casos_uso >= 10:
        return "L4"
    if tiene_siem and avg_cob >= 80 and alertas_activas and cumple_retencion:
        return "L3"
    if tiene_siem and avg_cob > 50 and cumple_retencion:
        return "L2"
    if tiene_siem or avg_cob >= 20:
        return "L1"
    return "L0"


def _cumple_retencion_ens(data: dict) -> bool:
    categoria = str(data.get("categoria_ens") or "media").lower()
    minimo = ENS_RETENTION_MIN_DAYS.get(categoria, 180)
    retencion_dias = data.get("retencion_minima_dias")
    if retencion_dias is None:
        return False
    try:
        return int(retencion_dias) >= minimo
    except (TypeError, ValueError):
        return False


async def assess(
    session: AsyncSession,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    logging_data: Optional[dict] = None,
) -> tuple[LoggingAssessment, list[DiscoveryAlert]]:
    """Crea LoggingAssessment + alertas por gaps criticos."""
    data = logging_data or {}
    siem = data.get("siem") or {}
    cobertura = data.get("cobertura") or {}
    alertas = data.get("alertas") or {}
    fuentes = list(data.get("fuentes") or [])

    cumple_ret = _cumple_retencion_ens(data)
    cumple_8, gaps_8 = _check_op_exp_8(data)
    madurez = _calculate_maturity(data, cumple_ret)

    retencion_vals = [
        f.get("retencion_dias")
        for f in fuentes if isinstance(f, dict) and f.get("retencion_dias") is not None
    ]
    retencion_min = data.get("retencion_minima_dias") or (
        min(retencion_vals) if retencion_vals else None
    )
    retencion_max = data.get("retencion_maxima_dias") or (
        max(retencion_vals) if retencion_vals else None
    )

    assessment = LoggingAssessment(
        project_id=project_id,
        discovery_run_id=run_id,
        tiene_siem=bool(siem.get("tiene")) if siem else None,
        siem_producto=siem.get("producto"),
        fuentes_log=fuentes,
        cobertura_servidores_pct=cobertura.get("servidores"),
        cobertura_red_pct=cobertura.get("red"),
        cobertura_aplicaciones_pct=cobertura.get("aplicaciones"),
        cobertura_endpoints_pct=cobertura.get("endpoints"),
        retencion_minima_dias=retencion_min,
        retencion_maxima_dias=retencion_max,
        cumple_retencion_ens=cumple_ret,
        tiene_alertas_activas=bool(alertas.get("activas")) if alertas else None,
        alertas_revisadas_por=alertas.get("revisadas_por"),
        casos_uso_activos=alertas.get("casos_uso"),
        cumple_op_exp_8=cumple_8,
        gaps_op_exp_8=gaps_8,
        nivel_madurez_logging=madurez,
        observaciones=data.get("observaciones"),
    )
    session.add(assessment)
    await session.flush()

    # Alertas
    new_alerts: list[DiscoveryAlert] = []
    categoria = str(data.get("categoria_ens") or "media").lower()
    if not siem.get("tiene") and categoria in {"media", "alta"}:
        new_alerts.append(DiscoveryAlert(
            project_id=project_id,
            discovery_run_id=run_id,
            modulo="logs",
            severidad="alta",
            codigo="LOG_NO_SIEM",
            titulo=f"Sin SIEM en sistema categoria ENS {categoria}",
            descripcion=(
                f"La organizacion no tiene SIEM activo y la categoria ENS es "
                f"{categoria}. Se requiere monitorizacion continua (op.mon.1-2)."
            ),
            entity_type="logging_assessment",
            entity_id=assessment.id,
            medidas_ens_afectadas=["op.mon.1", "op.mon.2"],
        ))
    if not cumple_ret:
        new_alerts.append(DiscoveryAlert(
            project_id=project_id,
            discovery_run_id=run_id,
            modulo="logs",
            severidad="alta",
            codigo="LOG_RETENCION_INSUFICIENTE",
            titulo="Retencion de logs por debajo del minimo ENS",
            descripcion=(
                f"La retencion minima ({retencion_min} dias) no cumple el umbral "
                f"ENS para categoria {categoria}."
            ),
            entity_type="logging_assessment",
            entity_id=assessment.id,
            medidas_ens_afectadas=["op.exp.8"],
        ))
    if not cumple_8:
        new_alerts.append(DiscoveryAlert(
            project_id=project_id,
            discovery_run_id=run_id,
            modulo="logs",
            severidad="media",
            codigo="LOG_OP_EXP_8_INCUMPLE",
            titulo="Incumplimiento parcial de op.exp.8",
            descripcion=(
                f"Gaps en op.exp.8: {', '.join(gaps_8) if gaps_8 else '(ninguno)'}"
            ),
            entity_type="logging_assessment",
            entity_id=assessment.id,
            medidas_ens_afectadas=["op.exp.8"],
        ))

    for a in new_alerts:
        session.add(a)
    await session.flush()
    return assessment, new_alerts


async def get_latest(
    session: AsyncSession, project_id: uuid.UUID,
) -> Optional[LoggingAssessment]:
    r = await session.execute(
        select(LoggingAssessment)
        .where(
            LoggingAssessment.project_id == project_id,
            LoggingAssessment.deleted_at.is_(None),
        )
        .order_by(LoggingAssessment.created_at.desc())
        .limit(1)
    )
    return r.scalar_one_or_none()


def to_dict(a: LoggingAssessment) -> dict:
    return {
        "id": str(a.id),
        "project_id": str(a.project_id),
        "discovery_run_id": str(a.discovery_run_id),
        "tiene_siem": a.tiene_siem,
        "siem_producto": a.siem_producto,
        "fuentes_log": a.fuentes_log or [],
        "cobertura": {
            "servidores": a.cobertura_servidores_pct,
            "red": a.cobertura_red_pct,
            "aplicaciones": a.cobertura_aplicaciones_pct,
            "endpoints": a.cobertura_endpoints_pct,
        },
        "retencion_minima_dias": a.retencion_minima_dias,
        "retencion_maxima_dias": a.retencion_maxima_dias,
        "cumple_retencion_ens": a.cumple_retencion_ens,
        "tiene_alertas_activas": a.tiene_alertas_activas,
        "alertas_revisadas_por": a.alertas_revisadas_por,
        "casos_uso_activos": a.casos_uso_activos,
        "cumple_op_exp_8": a.cumple_op_exp_8,
        "gaps_op_exp_8": a.gaps_op_exp_8 or [],
        "nivel_madurez_logging": a.nivel_madurez_logging,
        "observaciones": a.observaciones,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }
