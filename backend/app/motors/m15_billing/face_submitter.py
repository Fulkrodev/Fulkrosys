"""FACe submitter · SAN-C MB-11.3.

FACe (Punto General de Entrada de Facturas Electrónicas AAPP) requiere
registro plataforma + certificado AAPP. Para pre-cliente real,
implementación devuelve flow "manual_portal" honesto con URL portal +
manual_steps + flag xml_attached.

NO stub silencioso. Caller (UI) muestra al usuario claramente que el
envío es manual hasta integración API.

TODO-FACE-API-INTEGRATION-001 [BAJA · post-cliente real]:
- Registro plataforma FACe vía formulario gob.es
- Certificado de plataforma (no FNMT consultor)
- Implementar submit_via_api(xml_signed, dir3) con SOAP/REST FACe
"""
from __future__ import annotations

from typing import Optional


FACE_PORTAL_URL = "https://face.gob.es/es/proveedores/remitir-factura"
FACE_API_URL_FUTURE = "https://webservice.face.gob.es/"  # post-integración


def submit_to_face(
    xml_signed: Optional[bytes],
    *,
    dir3_oficina_contable: str,
    dir3_organo_gestor: str,
    dir3_unidad_tramitadora: str,
) -> dict:
    """Submit invoice XML al portal FACe (manual mode).

    Args:
        xml_signed: XML XAdES-signed (None si signature no disponible).
        dir3_*: códigos DIR3 obligatorios.

    Returns:
        Payload con submission_method=manual_portal + URL + manual_steps.
    """
    return {
        "submission_method": "manual_portal",
        "face_portal_url": FACE_PORTAL_URL,
        "xml_attached": xml_signed is not None,
        "xml_signed": xml_signed is not None,
        "dir3_codes": {
            "oficina_contable": dir3_oficina_contable,
            "organo_gestor": dir3_organo_gestor,
            "unidad_tramitadora": dir3_unidad_tramitadora,
        },
        "manual_steps": [
            "1. Login FACe portal con certificado AAPP del consultor",
            "2. Acceder a 'Remitir factura'",
            "3. Subir XML adjunto (descargado de FULKRO)",
            "4. Verificar códigos DIR3 pre-rellenados",
            "5. Confirmar envío y guardar referencia FACe",
        ],
        "warning_no_signature": (
            "XML sin firma XAdES (cert FNMT no disponible). "
            "FACe puede rechazar producción · únicamente sandbox."
        ) if xml_signed is None else None,
    }
