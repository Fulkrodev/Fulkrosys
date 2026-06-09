"""X-002 · Catálogo de servicios + valoración CIDAT."""
from __future__ import annotations

import uuid

from openpyxl import Workbook
from sqlalchemy.ext.asyncio import AsyncSession

from ._common import CanonicalSpec, build_canonical_workbook
from .registry import get_template_info


SPEC = CanonicalSpec(
    info=get_template_info("catalogo_servicios_cidat"),
    sheet_title="Servicios CIDAT",
    headers=[
        "Código servicio",
        "Nombre servicio",
        "Descripción",
        "Tipos información tratada",
        "Confidencialidad",
        "Integridad",
        "Disponibilidad",
        "Autenticidad",
        "Trazabilidad",
        "Responsable Servicio",
    ],
    notes=[
        "Niveles per dimensión: BAJO · MEDIO · ALTO (RD 311/2022 Anexo I)",
        "La regla del máximo aplicada da la categoría del sistema.",
    ],
    sample_rows=[
        ["SVC-001", "Sede electrónica", "Tramitación electrónica ciudadanos",
         "Datos personales · datos especiales art.9 RGPD",
         "ALTO", "ALTO", "MEDIO", "ALTO", "ALTO", "Director TI"],
        ["SVC-002", "Portal interno empleados", "Intranet + correo interno",
         "Datos personales empleados",
         "MEDIO", "MEDIO", "MEDIO", "MEDIO", "MEDIO", "Director RRHH"],
    ],
)


async def generate(project_id: uuid.UUID, db: AsyncSession) -> Workbook:
    return await build_canonical_workbook(project_id, db, SPEC)
