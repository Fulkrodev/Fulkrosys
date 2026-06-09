"""X-008 · Registro de incidentes (CCN-STIC 817)."""
from __future__ import annotations

import uuid

from openpyxl import Workbook
from sqlalchemy.ext.asyncio import AsyncSession

from ._common import CanonicalSpec, build_canonical_workbook
from .registry import get_template_info


SPEC = CanonicalSpec(
    info=get_template_info("registro_incidentes"),
    sheet_title="Registro incidentes 817",
    headers=[
        "ID incidente", "Fecha detección", "Detector",
        "Severidad (BAJA/MEDIA/ALTA/CRITICA)",
        "Categoría incidente", "Activos afectados",
        "Descripción", "Evento detonante",
        "Acciones contención", "Acciones erradicación",
        "Notificación CCN-CERT (LUCIA)", "Notificación AEPD (RGPD)",
        "Estado", "Fecha cierre", "Lecciones aprendidas",
    ],
    notes=[
        "Formato canónico CCN-STIC 817.",
        "Incidentes significativos requieren notificación CCN-CERT vía LUCIA (art. 33 RD 311/2022).",
        "Brechas datos personales requieren notificación AEPD ≤ 72h (RGPD art. 33).",
    ],
    sample_rows=[
        ["INC-2026-001", "2026-05-05", "RSEG monitoring",
         "MEDIA", "acceso_no_autorizado",
         "[I].001 BBDD clientes",
         "Intento acceso credenciales válidas desde IP geolocalización inusual",
         "Login externo fuera horario/zona habitual",
         "Bloqueo IP + fuerza cambio password usuario",
         "Investigación trazas + revisión ACL",
         "No (impacto contenido)", "No (no brecha datos confirmada)",
         "cerrado", "2026-05-06",
         "Reforzar conditional access + alertas anomalía geo"],
    ],
)


async def generate(project_id: uuid.UUID, db: AsyncSession) -> Workbook:
    return await build_canonical_workbook(project_id, db, SPEC)
