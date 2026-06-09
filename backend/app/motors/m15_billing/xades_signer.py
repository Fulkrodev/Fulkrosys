"""XAdES-BES signer Facturae 3.2.x · SAN-C MB-11.3.

Stub graceful per briefing: requiere certificado FNMT del consultor +
binding xmlsec1 (lib externa C). Sin cert disponible o sin lib, la
signature NO se aplica y se documenta TODO post-cliente real.

TODO-FACE-XADES-CERT-FNMT-001 [MEDIA · post-cliente real]:
- Cliente real proporciona certificado FNMT vía pass + .p12 file
- Implementación: signxml package + xmlsec1 binding + cert path
- Reemplazar ``sign_facturae_xades`` body con firma real
- Validar contra schemaXSD Facturae 3.2.x post-firma
- Test integration con cert dummy generado para CI

Decisión: NO stub silencioso. Si caller invoca ``sign_facturae_xades``
sin cert disponible, raise ``FacturaeSignatureNotAvailable`` con mensaje
claro · caller decide si abortar o continuar sin firma (FACe permite
recibir XML sin firma sólo en sandbox).
"""
from __future__ import annotations

import os
from pathlib import Path


class FacturaeSignatureNotAvailable(RuntimeError):
    """Raise cuando XAdES no puede firmar por cert/lib ausente."""


def is_xades_available(certificate_path: str | None = None) -> tuple[bool, str]:
    """Verifica disponibilidad XAdES (lib + cert).

    Returns:
        (available, reason) · available=True si todo presente, else False
        + reason explicativa en español para mostrar al usuario.
    """
    try:
        import xmlsec  # noqa: F401
    except ImportError:
        try:
            import signxml  # noqa: F401
        except ImportError:
            return (
                False,
                "Lib XAdES no instalada (instalar 'signxml' o 'python-xmlsec')",
            )

    cert = certificate_path or os.environ.get("FULKRO_FACTURAE_CERT_PATH")
    if not cert:
        return (
            False,
            "Variable FULKRO_FACTURAE_CERT_PATH no configurada · cert FNMT no provisto",
        )
    if not Path(cert).exists():
        return (False, f"Certificado FNMT no encontrado en {cert}")

    return (True, "Lib + cert FNMT disponibles")


def sign_facturae_xades(
    xml_bytes: bytes,
    certificate_path: str | None = None,
    *,
    cert_password: str | None = None,
) -> bytes:
    """Firma XAdES-BES sobre XML Facturae 3.2.x.

    Args:
        xml_bytes: XML Facturae 3.2.x sin firmar.
        certificate_path: Path al .p12 FNMT. Si None, lee
            ``FULKRO_FACTURAE_CERT_PATH`` env var.
        cert_password: Password del .p12 FNMT.

    Returns:
        bytes con XML firmado XAdES-BES.

    Raises:
        FacturaeSignatureNotAvailable: si lib o cert no disponibles.
            Mensaje claro al caller (NO stub silencioso).
    """
    available, reason = is_xades_available(certificate_path)
    if not available:
        raise FacturaeSignatureNotAvailable(
            f"Firma XAdES no disponible: {reason}. "
            "TODO-FACE-XADES-CERT-FNMT-001 pendiente cliente real."
        )

    # Implementación real (cuando cert disponible):
    # from signxml.xades import XAdESSigner
    # signer = XAdESSigner(...)
    # return signer.sign(xml_bytes, key=..., cert=...)
    raise FacturaeSignatureNotAvailable(
        "Implementación XAdES pendiente · TODO-FACE-XADES-CERT-FNMT-001"
    )
