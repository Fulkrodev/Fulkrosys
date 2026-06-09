"""X-009 · Indicadores y métricas (CCN-STIC 815)."""
from __future__ import annotations

import uuid

from openpyxl import Workbook
from sqlalchemy.ext.asyncio import AsyncSession

from ._common import CanonicalSpec, build_canonical_workbook
from .registry import get_template_info


SPEC = CanonicalSpec(
    info=get_template_info("indicadores_metricas"),
    sheet_title="Indicadores 815",
    headers=[
        "ID KPI", "Nombre indicador", "Familia ENS",
        "Fórmula cálculo", "Frecuencia medición",
        "Umbral verde", "Umbral ámbar", "Umbral rojo",
        "Valor actual", "Tendencia (↑/→/↓)", "Responsable",
    ],
    notes=[
        "KPIs catálogo CCN-STIC 815 (métricas obligatorias Media/Alta).",
        "Frecuencia: continuo · diario · semanal · mensual · trimestral · anual.",
    ],
    sample_rows=[
        ["KPI-001", "Disponibilidad servicios críticos", "mp.s",
         "(uptime / total) × 100", "continuo",
         "≥ 99,5%", "99,0-99,5%", "< 99,0%",
         "99,7%", "→", "RSIS"],
        ["KPI-002", "MTTR incidentes seguridad", "op.exp.7",
         "tiempo_total_resolucion / num_incidentes", "mensual",
         "≤ 4h", "4-8h", "> 8h",
         "3,2h", "↓", "RSEG"],
        ["KPI-003", "% cumplimiento medidas Anexo II", "general",
         "(medidas_conformes / 73) × 100", "trimestral",
         "≥ 90%", "75-90%", "< 75%",
         "82%", "↑", "RSEG"],
        ["KPI-004", "Cobertura concienciación personal", "mp.per.3",
         "(empleados_formados_anio / total) × 100", "anual",
         "100%", "90-99%", "< 90%",
         "—", "—", "RRHH"],
    ],
)


async def generate(project_id: uuid.UUID, db: AsyncSession) -> Workbook:
    return await build_canonical_workbook(project_id, db, SPEC)
