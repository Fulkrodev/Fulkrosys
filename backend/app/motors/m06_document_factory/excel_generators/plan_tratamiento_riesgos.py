"""X-005 · Plan de tratamiento de riesgos."""
from __future__ import annotations

import uuid

from openpyxl import Workbook
from sqlalchemy.ext.asyncio import AsyncSession

from ._common import CanonicalSpec, build_canonical_workbook
from .registry import get_template_info


SPEC = CanonicalSpec(
    info=get_template_info("plan_tratamiento_riesgos"),
    sheet_title="Plan tratamiento",
    headers=[
        "ID acción", "Riesgo asociado", "Tipo tratamiento",
        "Descripción acción", "Salvaguarda MAGERIT",
        "Responsable", "Fecha objetivo", "Coste estimado (€)",
        "Estado", "% avance", "Riesgo residual esperado",
    ],
    notes=[
        "Tipos tratamiento: aceptar · mitigar · transferir · evitar.",
        "Estados: planificada · en_curso · completada · descartada.",
    ],
    sample_rows=[
        ["A-001", "R-001", "mitigar", "Implantar cifrado at-rest BBDD",
         "S.cifrado.datos", "RSIS", "2026-09-30", 3500,
         "planificada", 0, "BAJO"],
    ],
)


async def generate(project_id: uuid.UUID, db: AsyncSession) -> Workbook:
    return await build_canonical_workbook(project_id, db, SPEC)
