"""X-011 · BIA · Análisis de Impacto en el Negocio."""
from __future__ import annotations

import uuid

from openpyxl import Workbook
from sqlalchemy.ext.asyncio import AsyncSession

from ._common import CanonicalSpec, build_canonical_workbook
from .registry import get_template_info


SPEC = CanonicalSpec(
    info=get_template_info("bia_business_impact"),
    sheet_title="BIA",
    headers=[
        "Proceso de negocio", "Criticidad",
        "Servicios soporte", "Activos involucrados",
        "Impacto 1h", "Impacto 4h", "Impacto 1d", "Impacto 1w",
        "RTO objetivo (h)", "RPO objetivo (h)",
        "Salvaguarda continuidad", "Responsable proceso",
    ],
    notes=[
        "RTO = Recovery Time Objective (tiempo máx restauración).",
        "RPO = Recovery Point Objective (pérdida máx datos aceptable).",
        "Criticidad: muy_alta · alta · media · baja.",
    ],
    sample_rows=[
        ["Tramitación electrónica ciudadanos", "muy_alta",
         "Sede electrónica · BBDD · LDAP",
         "[SW].001 · [I].001 · [HW].001",
         "BAJO", "MEDIO", "ALTO", "MUY_ALTO",
         4, 1, "Cluster activo-pasivo + backup horario", "Director TI"],
    ],
)


async def generate(project_id: uuid.UUID, db: AsyncSession) -> Workbook:
    return await build_canonical_workbook(project_id, db, SPEC)
