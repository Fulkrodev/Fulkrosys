"""X-010 · Informe auditoría interna (CCN-STIC 802)."""
from __future__ import annotations

import uuid

from openpyxl import Workbook
from sqlalchemy.ext.asyncio import AsyncSession

from ._common import CanonicalSpec, build_canonical_workbook
from .registry import get_template_info


SPEC = CanonicalSpec(
    info=get_template_info("informe_auditoria_interna"),
    sheet_title="Auditoria interna 802",
    headers=[
        "Pregunta auditor", "Medida ENS", "Evidencia solicitada",
        "Evidencia aportada (Sí/No)", "Veredicto (Conforme/NC/OBS)",
        "Severidad (Mayor/Menor)", "Hallazgo", "Acción correctiva propuesta",
        "Plazo subsanación",
    ],
    notes=[
        "Plantilla CCN-STIC 802 · separación funcional implantador ≠ auditor.",
        "Veredicto: Conforme · No-Conformidad · Observación.",
        "NC mayor bloquea conformidad ENAC · NC menor permite plan acción.",
    ],
    sample_rows=[
        ["¿Existe PSI aprobada formalmente por Dirección?", "org.1",
         "PSI firmada + acta aprobación", "Sí",
         "Conforme", "—", "PSI v1.0 firmada 2026-04-15", "—", "—"],
        ["¿Se realizan pruebas de continuidad anualmente?", "op.cont.4",
         "Acta simulacro + lecciones aprendidas", "No",
         "No-Conformidad", "Mayor",
         "No hay registro de simulacro en últimos 12 meses",
         "Programar simulacro Q3 + acta firmada", "2026-09-30"],
    ],
)


async def generate(project_id: uuid.UUID, db: AsyncSession) -> Workbook:
    return await build_canonical_workbook(project_id, db, SPEC)
