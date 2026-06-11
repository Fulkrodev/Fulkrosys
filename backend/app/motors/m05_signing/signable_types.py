"""Signable types catalog · SAN-E v3.MB-5.2.

11 tipos de documentos firmables in-portal cliente. Subset requiere
step-up OTP (criticality high).
"""
from __future__ import annotations

from typing import Literal


SignableType = Literal[
    "dda",                       # DdA 73 medidas Anexo II (E-040)
    "magerit_validation",        # MAGERIT activos validation
    "pentest_authorization",     # Autorización ventana pentest
    "conformidad_ens",           # Declaración Conformidad ENS final (E-041)
    # #44 (FRENTE D): Declaración de Conformidad BÁSICA (autodeclaración · cierre
    # E-808C · CCN-STIC 809) firmada por la DIRECCIÓN (no el RSeg · asume la
    # responsabilidad sobre la seguridad). BÁSICA no va a ENAC → esta firma es el
    # artefacto de cierre. Distinta de conformidad_ens (E-041 final MEDIA/ALTA).
    "declaracion_conformidad_basica",
    "acta_comite",               # Acta comité seguridad (E-006/E-012)
    "retainer_offer",            # Aceptación oferta retainer (post-cert)
    "retainer_quarterly_signoff",  # Comité retainer trimestral (MB-6 atom 4)
    "policy_approval",           # Aprobación política (E-100..E-126)
    "incident_close",            # Cierre incidente seguridad
    "dpc_anual",                 # Declaración Cumplimiento anual
    "renewal",                   # Renovación bianual
    # F0-3 (Ejecutable 8 Pasada 16 · F-14-07/P10-F04): firmables de gobierno
    # FASE 0 con tipo dedicado (antes caían a document_generic).
    "acta_nombramiento_roles",   # E-002 Acta nombramiento roles ENS
    "plan_adecuacion",           # E-150 Plan de adecuación al ENS
    "documento_alcance",         # E-155 Documento de alcance del SGSI
    # #43 · contrato comercial C-001 firmado por el lead vía canvas Ed25519.
    # Puerta = magic-link FIRMA_CONTRATO (OTP+geo) · NO step-up OTP adicional
    # (el OTP ya está en la puerta · decisión B).
    "contrato_comercial",        # C-001 Contrato comercial de servicios
    "document_generic",          # Genérico (escape hatch)
]


SIGNABLE_TYPES: tuple[SignableType, ...] = (
    "dda",
    "magerit_validation",
    "pentest_authorization",
    "conformidad_ens",
    "declaracion_conformidad_basica",
    "acta_comite",
    "retainer_offer",
    "retainer_quarterly_signoff",
    "policy_approval",
    "incident_close",
    "dpc_anual",
    "renewal",
    "acta_nombramiento_roles",
    "plan_adecuacion",
    "documento_alcance",
    "contrato_comercial",
    "document_generic",
)


# Documentos que requieren step-up OTP (criticality high · audit ENAC mayor).
REQUIRES_STEP_UP_OTP: frozenset[SignableType] = frozenset({
    "dda",
    "pentest_authorization",
    "conformidad_ens",
    "declaracion_conformidad_basica",  # cierre BÁSICA firmado por Dirección (#44)
    "dpc_anual",
    "renewal",
    "retainer_quarterly_signoff",  # Comité retainer · audit ENAC trimestral
})


SIGNABLE_TYPE_LABELS: dict[SignableType, str] = {
    "dda": "Declaración de Aplicabilidad (73 medidas Anexo II)",
    "magerit_validation": "Validación de activos MAGERIT",
    "pentest_authorization": "Autorización de pentest externo",
    "conformidad_ens": "Declaración de Conformidad ENS",
    "declaracion_conformidad_basica": (
        "Declaración de Conformidad ENS BÁSICA (autodeclaración · Dirección)"
    ),
    "acta_comite": "Acta del Comité de Seguridad",
    "retainer_offer": "Aceptación de oferta de retainer",
    "retainer_quarterly_signoff": "Comité Retainer trimestral · revisión y firma",
    "policy_approval": "Aprobación de política",
    "incident_close": "Cierre de incidente de seguridad",
    "dpc_anual": "Declaración Protección Continuidad (DPC) anual",
    "renewal": "Renovación bianual ENS",
    "acta_nombramiento_roles": "Acta de Nombramiento de Roles ENS",
    "plan_adecuacion": "Plan de Adecuación al ENS",
    "documento_alcance": "Documento de Alcance del SGSI",
    "contrato_comercial": "Contrato comercial de servicios FULKRO",
    "document_generic": "Documento",
}


# F0-3 (Ejecutable 8 Pasada 16): mapeo E-code → SignableType para los firmables
# de gobierno FASE 0. Permite que el flujo de firma asigne el tipo dedicado en
# vez de caer a ``document_generic`` (gap F-14-07/P10-F04). Fuente: catálogo m06.
_ECODE_TO_SIGNABLE_TYPE: dict[str, SignableType] = {
    "E-002": "acta_nombramiento_roles",
    "E-003": "acta_comite",
    "E-012": "acta_comite",
    "E-150": "plan_adecuacion",
    "E-155": "documento_alcance",
}


def signable_type_for_ecode(ecode: str | None) -> SignableType:
    """Devuelve el SignableType dedicado de un E-code de gobierno FASE 0.

    Para E-002 / E-003 / E-012 / E-150 / E-155 retorna su tipo propio; para el resto
    ``document_generic`` (escape hatch). El flujo de firma debe usar esto para
    no etiquetar documentos de gobierno como genéricos.
    """
    if not ecode:
        return "document_generic"
    return _ECODE_TO_SIGNABLE_TYPE.get(ecode.upper().strip(), "document_generic")


SIGNING_STATUS = Literal[
    "pending",
    "otp_required",
    "otp_verified",
    "signed",
    "rejected",
    "expired",
]


SIGNING_EVENT_TYPE = Literal[
    "intent_created",
    "otp_sent",
    "otp_verified",
    "signature_generated",
    "rejected",
    "expired",
]


# OTP config
OTP_CODE_LENGTH = 6
OTP_TTL_SECONDS = 300  # 5 min
OTP_MAX_ATTEMPTS = 5

# Intent TTL
DEFAULT_INTENT_TTL_HOURS = 48
