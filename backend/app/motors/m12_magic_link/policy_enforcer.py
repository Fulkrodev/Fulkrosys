"""MagicLinkPolicyEnforcer · soft-deprecation policy validation (ADR-042).

SAN-D MB-19.9 · validates magic-link purpose generation requests against
hybrid policy categorization:

- 15 purposes mantienen razón (categorías A-F ADR-042 · firmas legales ·
  aprobaciones · descargas · acceso externo · lifecycle · auxiliares).
  (= len(ONE_SHOT_OR_LEGITIMATE_PURPOSES))
- 22 purposes deprecated soft (ONBOARDING_INICIAL · APORTE_EVIDENCIA + 20 v3
  client-facing) · cubiertos por portal cliente workspace MB-14 · BLOQUEAN la
  generación (hard-rejection MB-4.bis3 · ADR-020 v3): is_ok=False → ValueError
  en generate_magic_link → HTTP 422. (El nombre "soft" es histórico.)
  (= len(DEPRECATED_SOFT_PURPOSES) · 15 + 22 = 37 = len(MagicLinkPurpose))

API:
    enforcer = MagicLinkPolicyEnforcer()
    is_ok, status, reason = enforcer.validate_purpose(purpose)
    # status ∈ {"ok", "deprecated_soft", "unknown"}
    # reason · descripción humana para log + header

Convenciones:
- Solo "unknown" retorna `is_ok=False` (impide generación purpose
  no-existente · safety net).
- "deprecated_soft" retorna `is_ok=False` + reason (HARD-rejection · el cliente
  usa /client-portal · el magic link NO se genera).
- "ok" retorna `is_ok=True` + reason="" (bypass logging warning).

Integration point: `MagicLinkService.generate_magic_link()` invoca
enforcer ANTES create + persist (validation gate).

Refs: ADR-042 · MagicLinkPurpose enum 37 (15 legítimos + 22 deprecated).
"""
from __future__ import annotations

import logging
from typing import Literal

from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose


logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────
# Categorización ADR-042 · 15 mantienen + 22 deprecated soft = 37 enum
# ──────────────────────────────────────────────────────────────────


# Categoría A · Firmas legales OTP±geo (10 purposes)
_CATEGORY_A_FIRMAS = frozenset({
    MagicLinkPurpose.FIRMA_DOCUMENTO,
    MagicLinkPurpose.FIRMA_CONTRATO,
    MagicLinkPurpose.APROBACION_ACTA,
    MagicLinkPurpose.AUTORIZAR_VERIFICACION_TECNICA,
    MagicLinkPurpose.AUTORIZAR_PENTEST_EXTERNO,
    MagicLinkPurpose.ACEPTACION_RIESGO_RESIDUAL,
    MagicLinkPurpose.VALIDACION_CAMBIO_ALCANCE,
    MagicLinkPurpose.CONSENTIMIENTO_TRATAMIENTO_DATOS,
    MagicLinkPurpose.CONFIRMACION_CONFORMIDAD,
    MagicLinkPurpose.VOTACION_COMITE_SEGURIDAD,
})

# Categoría B · Aprobaciones comerciales OTP±geo (3 purposes)
_CATEGORY_B_APROBACIONES = frozenset({
    MagicLinkPurpose.APROBACION_PROPUESTA,
    MagicLinkPurpose.APROBACION_FACTURA,
    MagicLinkPurpose.AUTORIZACION_ACCION_REMOTA,
})

# Categoría C · Descargas one-shot/limitadas (8 purposes)
_CATEGORY_C_DESCARGAS = frozenset({
    MagicLinkPurpose.DESCARGA_DOSSIER_FINAL,
    MagicLinkPurpose.DESCARGA_BACKUP_ARCHIVO,
    MagicLinkPurpose.DESCARGA_CERTIFICADO_CONFORMIDAD,
    MagicLinkPurpose.REPORTE_TRIMESTRAL,
    MagicLinkPurpose.REPORTE_ANUAL,
    MagicLinkPurpose.RESPUESTA_REQUERIMIENTO_AUDITOR,
    MagicLinkPurpose.COMUNICACION_INCIDENTE_SEGURIDAD,
    MagicLinkPurpose.INVITACION_REUNION,
})

# Categoría D · Acceso externo continuo (5 purposes · cuentas externas
# NO ClientUser · razón mantenida fuerte)
# Sesión 3B-2B.6 CLUSTER 2 · AUDITOR_PORTAL_ENAC añadido (auditor externo
# NO ClientUser · accede repetidamente durante ventana auditoría 14 días)
_CATEGORY_D_EXTERNO_CONTINUO = frozenset({
    MagicLinkPurpose.PORTAL_PENTESTER_EXTERNO,
    MagicLinkPurpose.PORTAL_REMEDIACION,
    MagicLinkPurpose.REVISAR_INFORME_VERIFICACION,
    MagicLinkPurpose.RENEWAL_CAMPAIGN_DETAILS,
    MagicLinkPurpose.AUDITOR_PORTAL_ENAC,
})

# Categoría E · Workflow lifecycle/portal cliente (5 purposes)
_CATEGORY_E_LIFECYCLE = frozenset({
    MagicLinkPurpose.PRIMER_ACCESO_CLIENTE,
    MagicLinkPurpose.OFERTA_RETAINER,
    MagicLinkPurpose.RECONSIDERACION_RETAINER,
    MagicLinkPurpose.RETAINER_WELCOME,
    MagicLinkPurpose.NORMATIVA_ALERT_CRITICAL,
})

# Categoría F · Auxiliares (3 purposes)
_CATEGORY_F_AUXILIARES = frozenset({
    MagicLinkPurpose.APROBACION_OBLIGACION,
    MagicLinkPurpose.SOLICITUD_INFORMACION,
    MagicLinkPurpose.ENCUESTA_SATISFACCION_NPS,
    # Batch A diagnóstico previo · captación en frío (interés legítimo 6.1.f).
    # Informacional/cuestionario · allowed · NO deprecated.
    MagicLinkPurpose.DIAGNOSTICO_PRECLIENTE,
})

# ──────────────────────────────────────────────────────────────────
# ADR-020 v3 NEW · Cliente in-portal only (SAN-E v3.MB-4.bis)
# ──────────────────────────────────────────────────────────────────
# Cliente con cuenta portal (post-cleanup M21 single-user-RW · ADR-013 v3)
# realiza 100% acciones in-portal con login normal · NO recibe magic links.
# Mantienen razón solo terceros sin cuenta portal · pre-cliente · post-cierre.

# Purposes deprecated v3 cliente-facing post-cuenta-portal (20 NEW + 2 existing)
# Post-MB-4.bis3: APROBACION_ACTA re-clasificada como mixed-use legitimate
# (asistentes a actas pueden ser empleados/proveedores externos sin cuenta
# portal · MANTIENE razón).
DEPRECATED_V3_CLIENT_FACING = frozenset({
    # Lifecycle/portal cliente (5)
    MagicLinkPurpose.PRIMER_ACCESO_CLIENTE,
    MagicLinkPurpose.OFERTA_RETAINER,
    MagicLinkPurpose.RECONSIDERACION_RETAINER,
    MagicLinkPurpose.RETAINER_WELCOME,
    MagicLinkPurpose.NORMATIVA_ALERT_CRITICAL,
    # Firmas legales (4 que cliente firma in-portal · APROBACION_ACTA OUT)
    MagicLinkPurpose.ACEPTACION_RIESGO_RESIDUAL,
    MagicLinkPurpose.VALIDACION_CAMBIO_ALCANCE,
    MagicLinkPurpose.CONSENTIMIENTO_TRATAMIENTO_DATOS,
    MagicLinkPurpose.CONFIRMACION_CONFORMIDAD,
    MagicLinkPurpose.VOTACION_COMITE_SEGURIDAD,
    # Aprobaciones (1 cliente in-portal /billing)
    MagicLinkPurpose.APROBACION_FACTURA,
    # Descargas (5 cliente in-portal /files)
    MagicLinkPurpose.DESCARGA_CERTIFICADO_CONFORMIDAD,
    MagicLinkPurpose.REPORTE_TRIMESTRAL,
    MagicLinkPurpose.REPORTE_ANUAL,
    MagicLinkPurpose.COMUNICACION_INCIDENTE_SEGURIDAD,
    MagicLinkPurpose.INVITACION_REUNION,
    # Acceso externo (1 cliente in-portal /renewal)
    MagicLinkPurpose.RENEWAL_CAMPAIGN_DETAILS,
    # Auxiliares (3 cliente in-portal /tasks o /inbox)
    MagicLinkPurpose.APROBACION_OBLIGACION,
    MagicLinkPurpose.SOLICITUD_INFORMACION,
    MagicLinkPurpose.ENCUESTA_SATISFACCION_NPS,
})

# Total mantienen razón = 15 (excluyendo deprecated v3 · verificado empírico)
ONE_SHOT_OR_LEGITIMATE_PURPOSES = (
    _CATEGORY_A_FIRMAS
    | _CATEGORY_B_APROBACIONES
    | _CATEGORY_C_DESCARGAS
    | _CATEGORY_D_EXTERNO_CONTINUO
    | _CATEGORY_E_LIFECYCLE
    | _CATEGORY_F_AUXILIARES
) - DEPRECATED_V3_CLIENT_FACING

# Deprecated soft = 22 (2 existing pre-MB-4.bis + 20 v3 client-facing · empírico)
DEPRECATED_SOFT_PURPOSES = frozenset({
    MagicLinkPurpose.ONBOARDING_INICIAL,
    MagicLinkPurpose.APORTE_EVIDENCIA,
}) | DEPRECATED_V3_CLIENT_FACING

# Mensajes deprecation per purpose · descriptivos para log + header
_DEPRECATION_REASONS: dict[MagicLinkPurpose, str] = {
    MagicLinkPurpose.ONBOARDING_INICIAL: (
        "ONBOARDING_INICIAL deprecated soft · cubierto por portal cliente "
        "/client-portal/onboarding (MB-4.3) · ver ADR-020"
    ),
    MagicLinkPurpose.APORTE_EVIDENCIA: (
        "APORTE_EVIDENCIA deprecated soft · cubierto por portal cliente "
        "/client-portal/evidencias (MB-14.7) · ver ADR-020"
    ),
    MagicLinkPurpose.PRIMER_ACCESO_CLIENTE: (
        "PRIMER_ACCESO_CLIENTE deprecated v3 · cliente login normal con "
        "password en /client-portal/login (cleanup M21 single-user-RW) · ADR-020"
    ),
    MagicLinkPurpose.OFERTA_RETAINER: (
        "OFERTA_RETAINER deprecated v3 · cliente acepta retainer in-portal "
        "/client-portal/retainer · ADR-020"
    ),
    MagicLinkPurpose.RECONSIDERACION_RETAINER: (
        "RECONSIDERACION_RETAINER deprecated v3 · cliente reconsidera in-portal "
        "/client-portal/retainer · ADR-020"
    ),
    MagicLinkPurpose.RETAINER_WELCOME: (
        "RETAINER_WELCOME deprecated v3 · banner in-portal /client-portal/dashboard · ADR-020"
    ),
    MagicLinkPurpose.NORMATIVA_ALERT_CRITICAL: (
        "NORMATIVA_ALERT_CRITICAL deprecated v3 · alertas in-portal "
        "/client-portal/inbox · ADR-020"
    ),
    MagicLinkPurpose.APROBACION_ACTA: (
        "APROBACION_ACTA deprecated v3 · cliente aprueba in-portal "
        "/client-portal/workflow · ADR-020"
    ),
    MagicLinkPurpose.ACEPTACION_RIESGO_RESIDUAL: (
        "ACEPTACION_RIESGO_RESIDUAL deprecated v3 · cliente acepta in-portal "
        "/client-portal/risks · ADR-020"
    ),
    MagicLinkPurpose.VALIDACION_CAMBIO_ALCANCE: (
        "VALIDACION_CAMBIO_ALCANCE deprecated v3 · cliente valida in-portal "
        "/client-portal/risks · ADR-020"
    ),
    MagicLinkPurpose.CONSENTIMIENTO_TRATAMIENTO_DATOS: (
        "CONSENTIMIENTO_TRATAMIENTO_DATOS deprecated v3 · cliente firma DPA "
        "in-portal /client-portal/firma · ADR-020"
    ),
    MagicLinkPurpose.CONFIRMACION_CONFORMIDAD: (
        "CONFIRMACION_CONFORMIDAD deprecated v3 · cliente firma conformidad "
        "in-portal /client-portal/firma · ADR-020"
    ),
    MagicLinkPurpose.VOTACION_COMITE_SEGURIDAD: (
        "VOTACION_COMITE_SEGURIDAD deprecated v3 · miembros votan in-portal "
        "/client-portal/inbox · ADR-020"
    ),
    MagicLinkPurpose.APROBACION_FACTURA: (
        "APROBACION_FACTURA deprecated v3 · cliente aprueba in-portal "
        "/client-portal/billing · ADR-020"
    ),
    MagicLinkPurpose.DESCARGA_CERTIFICADO_CONFORMIDAD: (
        "DESCARGA_CERTIFICADO_CONFORMIDAD deprecated v3 · cliente descarga "
        "in-portal /client-portal/files · ADR-020"
    ),
    MagicLinkPurpose.REPORTE_TRIMESTRAL: (
        "REPORTE_TRIMESTRAL deprecated v3 · cliente accede in-portal "
        "/client-portal/files · ADR-020"
    ),
    MagicLinkPurpose.REPORTE_ANUAL: (
        "REPORTE_ANUAL deprecated v3 · cliente accede in-portal "
        "/client-portal/files · ADR-020"
    ),
    MagicLinkPurpose.COMUNICACION_INCIDENTE_SEGURIDAD: (
        "COMUNICACION_INCIDENTE_SEGURIDAD deprecated v3 · cliente comunica "
        "in-portal /client-portal/tasks · ADR-020"
    ),
    MagicLinkPurpose.INVITACION_REUNION: (
        "INVITACION_REUNION deprecated v3 · cliente confirma asistencia in-portal "
        "/client-portal/inbox · ADR-020"
    ),
    MagicLinkPurpose.RENEWAL_CAMPAIGN_DETAILS: (
        "RENEWAL_CAMPAIGN_DETAILS deprecated v3 · cliente revisa in-portal "
        "/client-portal/renewal · ADR-020"
    ),
    MagicLinkPurpose.APROBACION_OBLIGACION: (
        "APROBACION_OBLIGACION deprecated v3 · cliente aprueba in-portal "
        "/client-portal/tasks · ADR-020"
    ),
    MagicLinkPurpose.SOLICITUD_INFORMACION: (
        "SOLICITUD_INFORMACION deprecated v3 · cliente responde in-portal "
        "/client-portal/tasks · ADR-020"
    ),
    MagicLinkPurpose.ENCUESTA_SATISFACCION_NPS: (
        "ENCUESTA_SATISFACCION_NPS deprecated v3 · cliente responde in-portal "
        "/client-portal/inbox · ADR-020"
    ),
}


# ──────────────────────────────────────────────────────────────────
# Service
# ──────────────────────────────────────────────────────────────────


PolicyStatus = Literal["ok", "deprecated_soft", "unknown"]


class MagicLinkPolicyEnforcer:
    """Validates magic-link purpose generation against ADR-042 policy.

    Stateless service · safe single-instance per request.
    """

    def validate_purpose(
        self,
        purpose: MagicLinkPurpose | str,
    ) -> tuple[bool, PolicyStatus, str]:
        """Validates purpose · returns (is_ok, status, reason).

        Args:
            purpose: MagicLinkPurpose enum o string value (e.g. "firma_documento").

        Returns:
            tuple (is_ok: bool, status: PolicyStatus, reason: str)

            - status="ok" · is_ok=True · reason="" (15 mantienen razón · empírico)
            - status="deprecated_soft" · is_ok=False · reason="..." (22 deprecated
              v3 · HARD-rejection ADR-020 v3 · ValueError → HTTP 422 · el "soft"
              es histórico; NO permite generación)
            - status="unknown" · is_ok=False · reason="purpose desconocido..."
              (purpose no en enum · safety net)

        Estado actual (ADR-020 v3 IMPLEMENTED FULLY · MB-4.bis3): deprecated_soft
        Y unknown retornan is_ok=False · ambos fuerzan ValueError → HTTP 422 en
        MagicLinkService.generate_magic_link. Solo "ok" permite la generación.
        """
        # Coerce string → enum si necesario
        if isinstance(purpose, str):
            try:
                purpose = MagicLinkPurpose(purpose)
            except ValueError:
                return (
                    False,
                    "unknown",
                    f"purpose desconocido: {purpose!r} · no en enum MagicLinkPurpose",
                )

        # Categorización
        if purpose in ONE_SHOT_OR_LEGITIMATE_PURPOSES:
            return (True, "ok", "")

        if purpose in DEPRECATED_SOFT_PURPOSES:
            reason = _DEPRECATION_REASONS.get(
                purpose,
                f"{purpose.value} deprecated v3 · cliente usa portal · ver ADR-020",
            )
            logger.warning(
                "MagicLinkPolicyEnforcer · HARD-REJECT deprecated purpose: %s",
                reason,
            )
            # MB-4.bis3 (ADR-020 v3 IMPLEMENTED FULLY): hard-rejection ·
            # is_ok=False fuerza ValueError en MagicLinkService.generate_magic_link
            # · cliente con cuenta portal usa /client-portal/X.
            return (False, "deprecated_soft", reason)

        # Purpose existe en enum pero NO está categorizado · edge case ·
        # safety net · trata como unknown para no permitir generation
        # silenciosa de purpose nuevo sin clasificar (forzar update
        # ADR-042 + categorización per nuevo purpose).
        logger.error(
            "MagicLinkPolicyEnforcer · purpose %s en enum pero NO categorizado · "
            "actualizar ADR-042 + ONE_SHOT_OR_LEGITIMATE_PURPOSES",
            purpose.value,
        )
        return (
            False,
            "unknown",
            f"purpose {purpose.value} no categorizado en ADR-042 · "
            f"actualizar policy_enforcer.py categorías A-F",
        )

    def is_deprecated(self, purpose: MagicLinkPurpose | str) -> bool:
        """Quick check si purpose es deprecated (post-MB-4.bis2 hard-rejection).

        Post-ADR-020: deprecated_soft retorna is_ok=False · helper detecta
        ambos casos (deprecated_soft) sin importar el is_ok flag.
        """
        _, status, _ = self.validate_purpose(purpose)
        return status == "deprecated_soft"

    def get_categorization(self, purpose: MagicLinkPurpose | str) -> str:
        """Returns categoría humana per purpose · diagnostics/admin UI.

        Returns:
            "A_firmas" | "B_aprobaciones" | "C_descargas" |
            "D_externo_continuo" | "E_lifecycle" | "F_auxiliares" |
            "deprecated_soft" | "unknown"
        """
        if isinstance(purpose, str):
            try:
                purpose = MagicLinkPurpose(purpose)
            except ValueError:
                return "unknown"

        if purpose in _CATEGORY_A_FIRMAS:
            return "A_firmas"
        if purpose in _CATEGORY_B_APROBACIONES:
            return "B_aprobaciones"
        if purpose in _CATEGORY_C_DESCARGAS:
            return "C_descargas"
        if purpose in _CATEGORY_D_EXTERNO_CONTINUO:
            return "D_externo_continuo"
        if purpose in _CATEGORY_E_LIFECYCLE:
            return "E_lifecycle"
        if purpose in _CATEGORY_F_AUXILIARES:
            return "F_auxiliares"
        if purpose in DEPRECATED_SOFT_PURPOSES:
            return "deprecated_soft"
        return "unknown"

    def get_summary_stats(self) -> dict[str, int]:
        """Stats categorización · útil tests + admin UI dashboard."""
        return {
            "A_firmas": len(_CATEGORY_A_FIRMAS),
            "B_aprobaciones": len(_CATEGORY_B_APROBACIONES),
            "C_descargas": len(_CATEGORY_C_DESCARGAS),
            "D_externo_continuo": len(_CATEGORY_D_EXTERNO_CONTINUO),
            "E_lifecycle": len(_CATEGORY_E_LIFECYCLE),
            "F_auxiliares": len(_CATEGORY_F_AUXILIARES),
            "deprecated_soft": len(DEPRECATED_SOFT_PURPOSES),
            "total_legitimate": len(ONE_SHOT_OR_LEGITIMATE_PURPOSES),
            "total_deprecated": len(DEPRECATED_SOFT_PURPOSES),
            "total": (
                len(ONE_SHOT_OR_LEGITIMATE_PURPOSES)
                + len(DEPRECATED_SOFT_PURPOSES)
            ),
        }
