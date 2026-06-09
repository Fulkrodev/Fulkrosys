"""X-006 · Matriz Gap Analysis CCN-STIC 808."""
from __future__ import annotations

import uuid

from openpyxl import Workbook
from sqlalchemy.ext.asyncio import AsyncSession

from ._common import CanonicalSpec, build_canonical_workbook
from .registry import get_template_info


SPEC = CanonicalSpec(
    info=get_template_info("matriz_gap_analysis"),
    sheet_title="Gap CCN-STIC 808",
    headers=[
        "Medida ENS", "Requisito",
        "Implementado (Sí/No/Parcial)", "Evidencia disponible",
        "Madurez actual (L0-L5)", "Madurez objetivo",
        "Gap", "Acción correctiva", "Plazo", "Responsable",
    ],
    notes=[
        "Check-list canónica CCN-STIC 808 verificación cumplimiento.",
        "Madurez CMM: L0 inexistente · L1 inicial · L2 repetible · L3 definido · L4 gestionado · L5 optimizado.",
    ],
    sample_rows=[
        ["org.1", "Política Seguridad Información aprobada",
         "Parcial", "Borrador sin firmar", 1, 3, "L1→L3",
         "Aprobar formalmente por Dirección", "2026-08-31", "Sponsor"],
    ],
)


async def generate(project_id: uuid.UUID, db: AsyncSession) -> Workbook:
    return await build_canonical_workbook(project_id, db, SPEC)
