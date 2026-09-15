"""Contexto de la Ficha de Seguimiento de Proyecto (E-001).

POR QUE EXISTE
    E-001 es uno de los tres entregables de 28 que no salían. Su plantilla usa
    veintiuna variables bajo ``ficha.*`` y diez bajo ``proyecto.*`` —contadas
    sobre el propio ``.docx``, no de memoria— y **nadie las construía**: el
    generador genérico renderizaba con el contexto
    base (cliente + gobernanza) y Jinja2 abortaba con ``'ficha' is undefined``,
    que el endpoint devolvía como un 500 opaco.

QUE REGLA SIGUE
    La misma que ha gobernado toda la campaña: **lo que no se sabe no se
    inventa**. Las cifras de avance, horas y plazos salen del plan del proyecto
    (``project_plans``), del parte de horas (``marcos_timesheet_entries``) y de
    los hitos de facturación (``contract_milestones``). Las que no constan en
    ninguna parte —típicamente las comerciales, que viven en la propuesta y no
    en el proyecto— se emiten literalmente como «no consta».

    «No consta» es una afirmación verdadera. Un número inventado, no. Y esta
    ficha la recibe el cliente.
"""
from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

NO_CONSTA = "no consta"


def _pct(parte: float | int | None, total: float | int | None) -> float | str:
    if not total:
        return NO_CONSTA
    return round((float(parte or 0) / float(total)) * 100, 1)


def _semaforo(avance: float | str, dias_al_hito: int | str) -> str:
    """Verde / amarillo / rojo, con la regla escrita y no adivinada."""
    if isinstance(avance, str) or isinstance(dias_al_hito, str):
        return "amarillo"  # sin datos suficientes: ni tranquiliza ni alarma
    if dias_al_hito < 0:
        return "rojo"
    if dias_al_hito < 15 and avance < 60:
        return "amarillo"
    return "verde"


def _mes_siguiente(d: date) -> date:
    """La ficha es de seguimiento periódico: la próxima es el mes que viene.

    Esto decía ``date.today().replace(day=min(28, hoy.day))``, que para
    cualquier día 1-28 devuelve **hoy mismo**: la ficha que el cliente recibe
    afirmaba que su próxima actualización era el día en que la estaba leyendo.
    Falso todos los meses menos los que empiezan el 29.

    Se topa en 28 para que exista en febrero.
    """
    anyo, mes = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    return date(anyo, mes, min(d.day, 28))


async def build_ficha_seguimiento_context(
    db: AsyncSession, project_id: UUID,
) -> dict[str, Any]:
    """Contexto E-001. NUNCA lanza: los huecos se dicen, no se rellenan."""
    hoy = date.today()
    ficha: dict[str, Any] = {
        "fecha_emision": hoy.isoformat(),
        "version": 1,
        "comentario_consultor": "",
        "justificacion_desviacion": "",
        "riesgos": [],
        "decisiones_pendientes": [],
        "logros_periodo": [],
    }
    proyecto: dict[str, Any] = {}

    fila = (await db.execute(sa_text(
        "SELECT p.nombre, p.categoria_objetivo, p.fecha_kickoff, "
        "       p.fecha_objetivo_certificacion, p.client_id "
        "FROM projects p WHERE p.id = :pid"
    ), {"pid": str(project_id)})).first()
    if fila is not None:
        proyecto["alcance"] = {"descripcion_corta": fila[0] or NO_CONSTA}
        proyecto["categoria_ens"] = fila[1] or NO_CONSTA
        proyecto["fecha_inicio"] = fila[2].isoformat() if fila[2] else NO_CONSTA
        proyecto["fecha_objetivo_certificacion"] = (
            fila[3].isoformat() if fila[3] else NO_CONSTA
        )
    # La entidad certificadora la elige el cliente y es ajena a Fulkro: si no
    # está registrada, se dice. Escribir una es declarar quién te va a auditar.
    proyecto.setdefault("entidad_certificadora", NO_CONSTA)

    # ── plan del proyecto (m17) ───────────────────────────────────────
    plan = (await db.execute(sa_text(
        "SELECT total_effort_marcos_hours, total_duration_weeks, start_date, "
        "       end_date_estimated, milestones, wbs "
        "FROM project_plans WHERE project_id = :pid AND deleted_at IS NULL "
        "ORDER BY version DESC NULLS LAST, created_at DESC LIMIT 1"
    ), {"pid": str(project_id)})).first()
    horas_plan = float(plan[0]) if plan and plan[0] else None
    semanas = int(plan[1]) if plan and plan[1] else None
    proyecto["horas_contratadas"] = horas_plan if horas_plan else NO_CONSTA
    proyecto["duracion_meses"] = round(semanas / 4.345, 1) if semanas else NO_CONSTA

    # ── avance real: la DdA implantada sobre las aplicables ───────────
    avance: float | str = NO_CONSTA
    dda = (await db.execute(sa_text(
        "SELECT count(*) FILTER (WHERE aplicabilidad <> 'no_aplica'), "
        "       count(*) FILTER (WHERE estado_implementacion = 'implantada') "
        "FROM dda_entries WHERE project_id = :pid AND deleted_at IS NULL"
    ), {"pid": str(project_id)})).first()
    if dda and dda[0]:
        avance = _pct(dda[1], dda[0])
    ficha["avance_porcentaje"] = avance

    # ── fases: las del plan si las hay ────────────────────────────────
    hitos = (plan[4] if plan else None) or []
    if isinstance(hitos, dict):
        hitos = hitos.get("items", [])
    ficha["fases_totales"] = len(hitos) if hitos else NO_CONSTA
    ficha["numero_fase"] = NO_CONSTA
    ficha["fase_actual"] = NO_CONSTA

    # ── horas consumidas: el parte de horas, por cliente ──────────────
    horas_consumidas: float | str = NO_CONSTA
    if fila is not None and fila[4]:
        minutos = await db.scalar(sa_text(
            "SELECT COALESCE(SUM(duration_minutes), 0) "
            "FROM marcos_timesheet_entries "
            "WHERE client_id = :cid AND deleted_at IS NULL"
        ), {"cid": str(fila[4])})
        horas_consumidas = round(float(minutos or 0) / 60.0, 1)
    ficha["horas_consumidas"] = horas_consumidas
    ficha["porcentaje_horas_consumidas"] = _pct(
        horas_consumidas if isinstance(horas_consumidas, float) else None,
        horas_plan,
    )
    if isinstance(horas_consumidas, float) and horas_plan:
        ficha["desviacion_horas"] = round(horas_consumidas - horas_plan, 1)
    else:
        ficha["desviacion_horas"] = NO_CONSTA

    # ── hitos de facturación: honorarios y próximo hito ───────────────
    facturado = await db.scalar(sa_text(
        "SELECT COALESCE(SUM(amount_eur), 0) FROM contract_milestones "
        "WHERE project_id = :pid AND deleted_at IS NULL AND billed_at IS NOT NULL"
    ), {"pid": str(project_id)})
    total_hitos = await db.scalar(sa_text(
        "SELECT COALESCE(SUM(amount_eur), 0) FROM contract_milestones "
        "WHERE project_id = :pid AND deleted_at IS NULL"
    ), {"pid": str(project_id)})
    ficha["honorarios_consumidos"] = (
        float(facturado) if facturado else NO_CONSTA
    )
    ficha["porcentaje_consumido"] = _pct(facturado, total_hitos)
    proyecto["inversion_fulkro"] = float(total_hitos) if total_hitos else NO_CONSTA
    # La auditoría externa la contrata y la paga el cliente: Fulkro no la conoce.
    proyecto["inversion_auditoria_externa"] = NO_CONSTA

    prox = (await db.execute(sa_text(
        "SELECT milestone_name, scheduled_date FROM contract_milestones "
        "WHERE project_id = :pid AND deleted_at IS NULL AND billed_at IS NULL "
        "  AND scheduled_date IS NOT NULL "
        "ORDER BY scheduled_date LIMIT 1"
    ), {"pid": str(project_id)})).first()
    if prox is not None:
        ficha["proximo_hito"] = prox[0] or NO_CONSTA
        ficha["fecha_proximo_hito"] = prox[1].isoformat()
        ficha["dias_proximo_hito"] = (prox[1] - hoy).days
    else:
        ficha["proximo_hito"] = NO_CONSTA
        ficha["fecha_proximo_hito"] = NO_CONSTA
        ficha["dias_proximo_hito"] = NO_CONSTA

    ficha["semaforo"] = _semaforo(avance, ficha["dias_proximo_hito"])
    ficha["proxima_actualizacion"] = _mes_siguiente(hoy).isoformat()
    return {"ficha": ficha, "proyecto": proyecto}
