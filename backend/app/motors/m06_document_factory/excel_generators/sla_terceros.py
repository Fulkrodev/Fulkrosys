"""X-014 · SLA / SLO con proveedores (CCN-STIC 823)."""
from __future__ import annotations

import uuid

from openpyxl import Workbook
from sqlalchemy.ext.asyncio import AsyncSession

from ._common import CanonicalSpec, build_canonical_workbook
from .registry import get_template_info


SPEC = CanonicalSpec(
    info=get_template_info("sla_terceros"),
    sheet_title="SLA terceros",
    headers=[
        "Proveedor", "Tipo servicio", "Categoría ENS aportada",
        "SLA disponibilidad", "SLA tiempo respuesta soporte",
        "RTO contractual", "RPO contractual",
        "Notificación incidentes (h)", "Plan salida acordado",
        "Soberanía datos (UE/España)",
        "Última revisión", "Próxima revisión",
    ],
    notes=[
        "CCN-STIC 823 cláusulas obligatorias para terceros que tratan información sistema.",
        "Notificación incidentes a cliente debe ser ≤ 24h en NIS2 / DORA.",
    ],
    sample_rows=[
        ["AWS Iberia", "Cloud IaaS+PaaS", "MEDIA",
         "99,95%", "1h business · 4h estándar",
         "4h", "1h", 24, "Sí · 90d export S3 + DBs",
         "España (eu-south-2)",
         "2026-04-01", "2027-04-01"],
    ],
)


async def generate(project_id: uuid.UUID, db: AsyncSession) -> Workbook:
    return await build_canonical_workbook(project_id, db, SPEC)
