"""X-003 · Matriz de riesgos simplificada (Categoría Básica)."""
from __future__ import annotations

import uuid

from openpyxl import Workbook
from sqlalchemy.ext.asyncio import AsyncSession

from ._common import CanonicalSpec, build_canonical_workbook
from .registry import get_template_info


SPEC = CanonicalSpec(
    info=get_template_info("matriz_riesgos"),
    sheet_title="Matriz Riesgos",
    headers=[
        "ID", "Activo", "Amenaza", "Vulnerabilidad",
        "Probabilidad (1-5)", "Impacto (1-5)", "Riesgo inherente",
        "Salvaguarda actual", "Riesgo residual", "Decisión tratamiento",
        "Responsable", "Fecha revisión",
    ],
    notes=[
        "Plantilla simplificada para Categoría BÁSICA.",
        "Para Media/Alta usar PILAR + plantilla matriz extendida.",
        "Decisión: aceptar / mitigar / transferir / evitar.",
    ],
    sample_rows=[
        ["R-001", "[I].001 BBDD clientes", "Acceso no autorizado",
         "Falta de cifrado en reposo", 3, 4, "ALTO",
         "Control de acceso lógico", "MEDIO", "Mitigar",
         "RSEG", "2026-12-31"],
    ],
)


async def generate(project_id: uuid.UUID, db: AsyncSession) -> Workbook:
    return await build_canonical_workbook(project_id, db, SPEC)
