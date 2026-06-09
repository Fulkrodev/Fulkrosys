"""Conector AEPD sede electrónica · SAN-C MB-11.2.

AEPD no expone API REST pública oficial para notificación brechas.
Aproximación: pre-fill payload estructurado + URL portal sede para
submission manual con guidance al usuario.

Si AEPD habilita API formal en futuro, este módulo extender con
``submit_via_api(payload)``.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional


AEPD_PORTAL_URL = (
    "https://sedeagpd.gob.es/sede-electronica-web/vistas/formNuevaReclamacion/"
    "tramitaReclamacion.jsf"
)


def prepare_aepd_payload(
    *,
    responsable_nombre: str,
    responsable_cif: str,
    detected_at: Optional[datetime] = None,
    description: Optional[str] = None,
    data_categories: Optional[list[str]] = None,
    consequences: Optional[str] = None,
    measures_taken: Optional[str] = None,
) -> dict:
    """Genera payload pre-filled para sede electrónica AEPD.

    Mantenemos campos estructurados Marcos puede pegar manualmente al
    formulario AEPD. NO submit automático (no API pública).
    """
    return {
        "responsable": {
            "nombre": responsable_nombre,
            "cif": responsable_cif,
        },
        "fecha_incidente": detected_at.isoformat() if detected_at else None,
        "naturaleza": description or "",
        "categorias_datos_afectados": data_categories or [],
        "consecuencias_probables": consequences or "",
        "medidas_adoptadas": measures_taken or "",
        "submission_method": "manual_portal",
        "portal_url": AEPD_PORTAL_URL,
        "manual_steps": [
            "1. Login AEPD sede con certificado FNMT del responsable",
            "2. Acceder a formulario notificación brecha",
            "3. Pegar datos del payload pre-filled",
            "4. Adjuntar evidencias si las hay",
            "5. Enviar y registrar referencia AEPD",
        ],
    }
