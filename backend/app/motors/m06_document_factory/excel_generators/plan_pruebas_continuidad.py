"""X-013 · Plan de pruebas de continuidad (simulacro anual)."""
from __future__ import annotations

import uuid

from openpyxl import Workbook
from sqlalchemy.ext.asyncio import AsyncSession

from ._common import CanonicalSpec, build_canonical_workbook
from .registry import get_template_info


SPEC = CanonicalSpec(
    info=get_template_info("plan_pruebas_continuidad"),
    sheet_title="Pruebas continuidad",
    headers=[
        "ID prueba", "Tipo (tabletop/parcial/completa)",
        "Escenario", "Servicios afectados",
        "RTO esperado (h)", "RTO obtenido (h)",
        "RPO esperado (h)", "RPO obtenido (h)",
        "Resultado (OK/parcial/KO)",
        "Hallazgos", "Acciones correctivas",
        "Fecha realización", "Próxima prueba",
    ],
    notes=[
        "Frecuencia mínima Media/Alta: simulacro completo anual + pruebas parciales trimestrales.",
        "Escenarios típicos: ransomware · caída CPD · pérdida personal clave · proveedor cloud caído.",
    ],
    sample_rows=[
        ["PC-2026-Q3", "completa", "Caída total CPD principal",
         "Sede electrónica · BBDD · LDAP",
         4, 5, 1, 1, "parcial",
         "Restauración tomó 5h (1h sobre RTO) por dependencia DNS no testeada",
         "Documentar runbook DNS + automatizar failover DNS",
         "2026-09-15", "2027-09-15"],
    ],
)


async def generate(project_id: uuid.UUID, db: AsyncSession) -> Workbook:
    return await build_canonical_workbook(project_id, db, SPEC)
