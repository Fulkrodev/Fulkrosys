"""X-004 · Declaración de Aplicabilidad (DdA) · 73 medidas Anexo II."""
from __future__ import annotations

import uuid

from openpyxl import Workbook
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from ._common import CanonicalSpec, build_canonical_workbook
from .registry import get_template_info


SPEC = CanonicalSpec(
    info=get_template_info("dda_matriz"),
    sheet_title="DdA 73 medidas",
    headers=[
        "Código medida",
        "Familia",
        "Nombre",
        "Aplicabilidad",
        "Refuerzos aplicados",
        "Estado implementación",
        "Evidencia (E-código)",
        "Responsable",
        "Justificación no aplica",
        "Observaciones",
    ],
    notes=[
        "73 medidas canónicas RD 311/2022 Anexo II (4 [org] + 33 [op] + 36 [mp]).",
        "Aplicabilidad: aplica · aplica_con_refuerzos · no_aplica.",
        "Refuerzos: +R1, +R2, ... según Anexo II y categoría sistema.",
    ],
)


async def _load(project_id: uuid.UUID, db: AsyncSession) -> list[list[object]]:
    """Aglutina las 73 medidas + DdA entries del proyecto si existen."""
    try:
        # Obtener medidas canónicas + entry DdA si existe
        rows = await db.execute(
            sa_text(
                "SELECT em.codigo, em.familia, em.nombre, "
                "       COALESCE(de.aplicabilidad, '') AS apl, "
                "       COALESCE(array_to_string("
                "          ARRAY(SELECT jsonb_array_elements_text(de.refuerzos_aplicados)), "
                "          ', '), '') AS ref, "
                "       COALESCE(de.estado_implementacion, '') AS estado, "
                "       '' AS evidencia, "
                "       COALESCE(de.responsable, '') AS resp, "
                "       COALESCE(de.justificacion_no_aplica, '') AS just, "
                "       COALESCE(de.observaciones, '') AS obs "
                "FROM ens_measures em "
                "LEFT JOIN dda_entries de ON de.measure_id = em.id "
                "  AND de.project_id = :pid "
                "WHERE em.deleted_at IS NULL "
                "ORDER BY em.marco, em.familia, em.codigo"
            ),
            {"pid": str(project_id)},
        )
        return [list(r) for r in rows.fetchall()]
    except Exception:
        return []


async def generate(project_id: uuid.UUID, db: AsyncSession) -> Workbook:
    return await build_canonical_workbook(project_id, db, SPEC, _load)
