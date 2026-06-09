"""X-007 · Plan de Adecuación tabular (CCN-STIC 806 complementario)."""
from __future__ import annotations

import uuid

from openpyxl import Workbook
from sqlalchemy.ext.asyncio import AsyncSession

from ._common import CanonicalSpec, build_canonical_workbook
from .registry import get_template_info


SPEC = CanonicalSpec(
    info=get_template_info("plantilla_pda"),
    sheet_title="PdA tabular",
    headers=[
        "Familia ENS", "Medida", "Estado actual",
        "Estado objetivo", "Acción", "Esfuerzo (h)",
        "Coste (€)", "Responsable", "Plazo", "Hito milestone",
    ],
    notes=[
        "Versión tabular del PdA narrativo E-150 (CCN-STIC 806).",
        "Útil para seguimiento operativo + visión cuantitativa.",
    ],
    sample_rows=[
        ["org", "org.1", "no_implementada", "implementada",
         "Aprobar PSI", 16, 1200, "RSEG", "2026-08-31", "M1 cierre PSI"],
    ],
)


async def generate(project_id: uuid.UUID, db: AsyncSession) -> Workbook:
    return await build_canonical_workbook(project_id, db, SPEC)
