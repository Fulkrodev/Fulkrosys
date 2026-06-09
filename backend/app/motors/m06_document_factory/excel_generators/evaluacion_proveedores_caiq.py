"""X-015 · Evaluación proveedores cloud (CSA CAIQ + módulo ENS)."""
from __future__ import annotations

import uuid

from openpyxl import Workbook
from sqlalchemy.ext.asyncio import AsyncSession

from ._common import CanonicalSpec, build_canonical_workbook
from .registry import get_template_info


SPEC = CanonicalSpec(
    info=get_template_info("evaluacion_proveedores_caiq"),
    sheet_title="CAIQ + ENS",
    headers=[
        "Categoría CAIQ", "ID control", "Pregunta",
        "Respuesta proveedor (Sí/No/N.A.)", "Evidencia aportada",
        "Mapping ENS (medida)", "Verificado (Sí/No)",
        "Riesgo residual (BAJO/MEDIO/ALTO)", "Observaciones",
    ],
    notes=[
        "CSA CAIQ 4.0 (Cloud Security Alliance · Consensus Assessments Initiative Questionnaire).",
        "Módulo ENS extiende CAIQ con mapping a medidas Anexo II según CCN-STIC 823.",
        "Categorías típicas: AIS · BCR · CCC · CEK · DSP · GRC · HRS · IAM · IPY · IVS · LOG · MOS · SEF · STA · TVM · UEM.",
    ],
    sample_rows=[
        ["IAM", "IAM-01.1", "¿Existe MFA obligatorio para usuarios con acceso privilegiado?",
         "Sí", "Captura panel admin IAM + política MFA",
         "op.acc.5 / op.acc.6", "Sí", "BAJO",
         "TOTP + WebAuthn habilitados"],
        ["BCR", "BCR-01.1", "¿Existe DRP testado en últimos 12m?",
         "Sí", "Informe simulacro 2025-11", "mp.s.4 / op.cont.4",
         "Sí", "BAJO", "RTO 4h conseguido"],
    ],
)


async def generate(project_id: uuid.UUID, db: AsyncSession) -> Workbook:
    return await build_canonical_workbook(project_id, db, SPEC)
