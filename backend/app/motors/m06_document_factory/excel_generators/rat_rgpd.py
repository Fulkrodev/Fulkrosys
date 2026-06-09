"""X-016 · Registro Actividades de Tratamiento (RAT) · Art. 30 RGPD."""
from __future__ import annotations

import uuid

from openpyxl import Workbook
from sqlalchemy.ext.asyncio import AsyncSession

from ._common import CanonicalSpec, build_canonical_workbook
from .registry import get_template_info


SPEC = CanonicalSpec(
    info=get_template_info("rat_rgpd"),
    sheet_title="RAT RGPD art. 30",
    headers=[
        "ID actividad", "Nombre tratamiento",
        "Responsable tratamiento (Identidad + DPO)",
        "Encargado tratamiento (si aplica)",
        "Finalidad",
        "Categorías interesados",
        "Categorías datos personales",
        "Categorías destinatarios",
        "Transferencias internacionales",
        "Plazo conservación",
        "Medidas técnicas y organizativas",
        "Base legitimación (art. 6 RGPD)",
        "Datos especiales (art. 9)",
    ],
    notes=[
        "Art. 30 RGPD obligatorio para responsables y encargados.",
        "Registro debe estar disponible para inspección AEPD.",
        "Datos especiales art. 9 RGPD: salud · biométricos · raciales · religiosos · políticos · sindicación · vida sexual · datos penales.",
    ],
    sample_rows=[
        ["RAT-001", "Gestión usuarios sede electrónica",
         "Acme S.L. · DPO ana.dpo@acme.es",
         "AWS Iberia (alojamiento) · ServicePro S.L. (soporte)",
         "Tramitación electrónica + autenticación",
         "Ciudadanos · empresas",
         "Identificativos · contacto · DNI/CIF",
         "Administración Pública competente",
         "No", "5 años post-tramitación",
         "Cifrado at-rest + TLS 1.3 + MFA admins",
         "Cumplimiento obligación legal (art. 6.1.c) + interés público (art. 6.1.e)",
         "No"],
    ],
)


async def generate(project_id: uuid.UUID, db: AsyncSession) -> Workbook:
    return await build_canonical_workbook(project_id, db, SPEC)
