"""X-012 · Matriz RACI roles ENS (CCN-STIC 801)."""
from __future__ import annotations

import uuid

from openpyxl import Workbook
from sqlalchemy.ext.asyncio import AsyncSession

from ._common import CanonicalSpec, build_canonical_workbook
from .registry import get_template_info


SPEC = CanonicalSpec(
    info=get_template_info("matriz_raci"),
    sheet_title="RACI roles ENS",
    headers=[
        "Actividad / Proceso",
        "RI (Resp. Información)",
        "RS (Resp. Servicio)",
        "RSEG (Resp. Seguridad)",
        "RSIS (Resp. Sistema)",
        "POC (CCN-CERT)",
        "Comité Seguridad",
        "Sponsor",
    ],
    notes=[
        "RACI: R = Responsable · A = Aprobador · C = Consultado · I = Informado.",
        "Roles canónicos CCN-STIC 801 + miembro_comite_seguridad.",
        "RSEG ≠ RSIS (segregación funcional · NC mayor en caso contrario).",
    ],
    sample_rows=[
        ["Aprobar Política Seguridad (org.1)", "C", "C", "R", "C", "I", "C", "A"],
        ["Análisis Riesgos MAGERIT", "C", "C", "R", "R", "I", "I", "I"],
        ["Notificar incidente significativo a CCN-CERT", "I", "I", "A", "C", "R", "I", "I"],
        ["Aprobar Plan Adecuación", "C", "C", "R", "C", "I", "C", "A"],
        ["Auditoría interna anual", "I", "I", "A", "I", "I", "I", "I"],
        ["Revisión por Dirección anual", "C", "C", "R", "C", "I", "R", "A"],
    ],
)


async def generate(project_id: uuid.UUID, db: AsyncSession) -> Workbook:
    return await build_canonical_workbook(project_id, db, SPEC)
