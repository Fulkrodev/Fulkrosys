"""M21 Paso 5 — Orquestador de diagnostico completo.

Une los 4 servicios Paso 5:
- stakeholders_service (Agente 22)
- processes_service (Agente 23)
- cross_compliance_service (Agente 24)
- m1_m2_feeds (hints a M1 + M2)

Y construye el contexto rico para el informe E-090.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m21_diagnosis import (
    cross_compliance_service as cc,
    m1_m2_feeds,
    processes_service,
    stakeholders_service,
)


async def run_full_diagnosis_paso5(
    db: AsyncSession, project_id: uuid.UUID,
    sector: str,
    *,
    empleados: int = 50,
    datos_sensibles: bool | None = None,
    seed_processes: bool = True,
    persist_obligations: bool = True,
) -> dict[str, Any]:
    """Ejecuta el diagnostico completo Paso 5 y devuelve contexto E-090.

    Pasos:
    1. (Opcional) Seed procesos segun sector si no existen
    2. Detectar obligaciones cruzadas y persistir
    3. Resumen stakeholders (ENS responsibles + conflictos)
    4. BIA feed desde procesos
    5. Sugerencia M1 categoria + M2 assets
    6. Empaquetar todo como contexto para E-090
    """
    result: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sector": sector,
    }

    # 1. Procesos por sector (opcional)
    if seed_processes:
        try:
            created = await processes_service.seed_sector_processes(
                db, project_id, sector,
            )
            result["processes_seeded"] = len(created)
        except KeyError:
            result["processes_seeded"] = 0
            result["processes_seed_error"] = (
                f"sector '{sector}' no tiene template"
            )

    # 2. Cross compliance
    ctx = cc.context_from_hints(
        sector=sector,
        empleados=empleados,
        datos_sensibles=datos_sensibles,
    )
    obligations = cc.detect_obligations(ctx)
    if persist_obligations:
        await cc.persist_obligations(db, project_id, ctx)
    result["compliance"] = cc.build_summary(ctx, obligations)

    # 3. Stakeholders
    result["stakeholders"] = await stakeholders_service.build_summary(
        db, project_id,
    )

    # 4. BIA feed
    result["bia"] = await processes_service.feed_bia(db, project_id)

    # 5. Hints M1 + M2
    result["m1_category_hint"] = await m1_m2_feeds.suggest_category(
        db, project_id,
    )
    result["m2_assets_hint"] = await m1_m2_feeds.suggest_magerit_assets(
        db, project_id,
    )

    await db.flush()
    return result


def build_e090_context(
    diagnosis: dict[str, Any], cliente: dict[str, Any],
    proyecto: dict[str, Any], responsables: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Contexto para template E-090 Diagnostico (M6 Document Factory)."""
    bia = diagnosis.get("bia") or {}
    cc_summary = diagnosis.get("compliance") or {}
    stk = diagnosis.get("stakeholders") or {}
    m1 = diagnosis.get("m1_category_hint") or {}
    m2_assets = diagnosis.get("m2_assets_hint") or []

    # Quick wins: primeros 5 cross_compliance items + conflictos stakeholder
    quick_wins = []
    for o in cc_summary.get("por_norma", {}).get("RGPD", [])[:3]:
        quick_wins.append({
            "titulo": o["obligacion"],
            "descripcion": o["accion_requerida"],
            "esfuerzo": "medio",
        })
    for c in stk.get("conflictos", [])[:2]:
        quick_wins.append({
            "titulo": f"Resolver conflicto de roles: {c['nombre']}",
            "descripcion": c["descripcion"],
            "esfuerzo": "bajo",
        })

    return {
        "cliente": cliente,
        "proyecto": proyecto,
        "responsables": responsables or {},
        "diagnostico": {
            "fecha_emision": diagnosis.get("generated_at"),
            "sector": diagnosis.get("sector"),
            "categoria_sugerida": m1.get("categoria_sugerida"),
            "justificacion_categoria": m1.get("justificacion"),
            "total_procesos": bia.get("total_procesos", 0),
            "rto_objetivo": bia.get("rto_objetivo_horas"),
            "rpo_objetivo": bia.get("rpo_objetivo_horas"),
            "recomendacion_continuidad": bia.get("recomendacion"),
            "total_obligaciones": cc_summary.get("total_obligaciones", 0),
            "obligaciones_por_norma": cc_summary.get("por_norma", {}),
            "flags_compliance": cc_summary.get("flags", {}),
            "total_personas": stk.get("total_personas", 0),
            "cobertura_ens_roles": stk.get(
                "ens_responsibles", {},
            ).get("coverage_pct", 0),
            "roles_ens_missing": stk.get(
                "ens_responsibles", {},
            ).get("missing", []),
            "conflictos_roles": len(stk.get("conflictos", [])),
            "assets_sugeridos_m2": len(m2_assets),
        },
        "procesos_por_criticidad": bia.get("por_criticidad", {}),
        "obligaciones": cc_summary.get("por_norma", {}),
        "stakeholders": stk,
        "quick_wins": quick_wins,
        "recomendaciones_fase2": [
            (
                "Completar asignacion de roles ENS pendientes "
                f"({len(stk.get('ens_responsibles', {}).get('missing', []))}) "
                "antes de iniciar Analisis de Riesgos."
            ),
            (
                f"Iniciar Categorizacion ENS ({m1.get('categoria_sugerida', 'MEDIA')}) "
                "con alcance preliminar basado en los procesos nucleares."
            ),
            (
                "Arrancar registro de actividades de tratamiento (Art. 30 RGPD) "
                "antes de la auditoria interna pre-ENAC."
            ),
        ],
    }


__all__ = ["build_e090_context", "run_full_diagnosis_paso5"]
