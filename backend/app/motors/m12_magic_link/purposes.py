"""Motor 12 — Magic Link Purposes.

Define los 9 tipos de magic link soportados por FULKRO segun spec v2.1
seccion 5.1 Motor 12.

Cada purpose tiene configuracion asociada:
- ttl_hours: tiempo de vida del link (24h a 7d segun criticidad)
- max_uses: usos maximos del link (normalmente 1, raramente 3)
- requires_otp: si el link exige OTP adicional al hacer click
- requires_geo: si el link puede restringirse geograficamente
- action_label: descripcion humana para emails + audit log
"""
from enum import Enum
from typing import TypedDict


class MagicLinkPurpose(str, Enum):
    """35 tipos de magic link · 8 base (1 eliminado SAN-B MB-6.6) +
    5 (M8 v5.1 Sesion 7) + 3 (M25 lifecycle Sesion 8) + 3 (M21 + Agente 15)
    + 3 (M23 reporting + M27 renewal) + 12 (FASE 4.5 ADR-011) +
    1 (FIRMA_CONTRATO SAN-D MB-19.4 ADR-041) = 35."""

    ONBOARDING_INICIAL = "onboarding_inicial"
    FIRMA_DOCUMENTO = "firma_documento"
    APORTE_EVIDENCIA = "aporte_evidencia"
    APROBACION_ACTA = "aprobacion_acta"
    RESPUESTA_REQUERIMIENTO_AUDITOR = "respuesta_requerimiento_auditor"
    # AUTORIZACION_PENTEST eliminado SAN-B.MB-6.6 · superseded por
    # AUTORIZAR_PENTEST_EXTERNO (M8 v5.1 · L37 abajo). 0 rows BD verificado
    # antes de DROP. Cierre TODO-FASE-4-5-DEDUP-001.
    AUTORIZACION_ACCION_REMOTA = "autorizacion_accion_remota"
    APROBACION_OBLIGACION = "aprobacion_obligacion"
    DESCARGA_DOSSIER_FINAL = "descarga_dossier_final"

    # ── M8 v5.1 Verificacion Tecnica (Sesion 7) ──
    AUTORIZAR_VERIFICACION_TECNICA = "autorizar_verificacion_tecnica"
    AUTORIZAR_PENTEST_EXTERNO = "autorizar_pentest_externo"
    PORTAL_REMEDIACION = "portal_remediacion"
    PORTAL_PENTESTER_EXTERNO = "portal_pentester_externo"
    REVISAR_INFORME_VERIFICACION = "revisar_informe_verificacion"

    # ── M25 Project Lifecycle Paso 4 (Sesion 8) ──
    OFERTA_RETAINER = "oferta_retainer"
    DESCARGA_BACKUP_ARCHIVO = "descarga_backup_archivo"
    RECONSIDERACION_RETAINER = "reconsideracion_retainer"

    # ── M21 Portal Cliente + Agente 15 Paso 7 (Sesion 8) ──
    PRIMER_ACCESO_CLIENTE = "primer_acceso_cliente"
    NORMATIVA_ALERT_CRITICAL = "normativa_alert_critical"
    RETAINER_WELCOME = "retainer_welcome"

    # ── M23 Reporting + M27 Renewal Paso 7 final (Sesion 8) ──
    REPORTE_TRIMESTRAL = "reporte_trimestral"
    REPORTE_ANUAL = "reporte_anual"
    RENEWAL_CAMPAIGN_DETAILS = "renewal_campaign_details"

    # ── 12 FASE 4.5 · ADR-011 · #24-#35 (Sesion 11) ──
    INVITACION_REUNION = "invitacion_reunion"                           # #24
    APROBACION_PROPUESTA = "aprobacion_propuesta"                       # #25
    APROBACION_FACTURA = "aprobacion_factura"                           # #26
    SOLICITUD_INFORMACION = "solicitud_informacion"                     # #27
    VALIDACION_CAMBIO_ALCANCE = "validacion_cambio_alcance"             # #28
    ACEPTACION_RIESGO_RESIDUAL = "aceptacion_riesgo_residual"           # #29
    COMUNICACION_INCIDENTE_SEGURIDAD = "comunicacion_incidente_seguridad"  # #30
    CONSENTIMIENTO_TRATAMIENTO_DATOS = "consentimiento_tratamiento_datos"  # #31
    CONFIRMACION_CONFORMIDAD = "confirmacion_conformidad"               # #32
    DESCARGA_CERTIFICADO_CONFORMIDAD = "descarga_certificado_conformidad"  # #33
    VOTACION_COMITE_SEGURIDAD = "votacion_comite_seguridad"             # #34
    ENCUESTA_SATISFACCION_NPS = "encuesta_satisfaccion_nps"             # #35

    # ── SAN-D MB-19.4 · ADR-041 · #36 firma contrato comercial ──
    FIRMA_CONTRATO = "firma_contrato"                                   # #36

    # ── Sesión 3B-2B.6 CLUSTER 2 · #37 auditor ENAC portal optional ──
    # Per-project per-cliente único · R23 strict · token-bounded read-only
    # constrained views (summary · dda · magerit · plan · evidence · e041 ·
    # audit-log · pentest · documents). Auditor recibe link post-entrega ZIP
    # firmado · prefiere interactivo vs offline-only path.
    AUDITOR_PORTAL_ENAC = "auditor_portal_enac"                         # #37

    # ── Diagnóstico previo (captación en frío · interés legítimo art. 6.1.f) ──
    # Batch A "diagnóstico previo": el lead responde un cuestionario ENS por
    # magic-link ANTES de la reunión (sin cuenta · account-less m16). Purpose
    # limpio (NO reusar ONBOARDING_INICIAL deprecated-soft). Ver
    # docs/audits/EJECUTABLE_8_BATCH2_FASE0_RECORRIDO_AUDIT.md.
    DIAGNOSTICO_PRECLIENTE = "diagnostico_precliente"                   # #38


class PurposeConfig(TypedDict):
    """Configuracion por tipo de magic link."""
    ttl_hours: int
    max_uses: int
    requires_otp: bool
    requires_geo: bool
    action_label: str


PURPOSE_CONFIG: dict[MagicLinkPurpose, PurposeConfig] = {
    MagicLinkPurpose.ONBOARDING_INICIAL: {
        "ttl_hours": 7 * 24,          # 7 dias
        "max_uses": 1,
        "requires_otp": False,
        "requires_geo": False,
        "action_label": "Completar onboarding inicial",
    },
    MagicLinkPurpose.FIRMA_DOCUMENTO: {
        "ttl_hours": 72,              # 3 dias
        "max_uses": 1,
        "requires_otp": True,
        "requires_geo": False,
        "action_label": "Firmar documento",
    },
    MagicLinkPurpose.APORTE_EVIDENCIA: {
        "ttl_hours": 7 * 24,          # 7 dias
        "max_uses": 3,                # multiples ficheros
        "requires_otp": False,
        "requires_geo": False,
        "action_label": "Aportar evidencias",
    },
    MagicLinkPurpose.APROBACION_ACTA: {
        "ttl_hours": 72,              # 3 dias
        "max_uses": 1,
        "requires_otp": True,
        "requires_geo": False,
        "action_label": "Aprobar acta",
    },
    MagicLinkPurpose.RESPUESTA_REQUERIMIENTO_AUDITOR: {
        "ttl_hours": 48,              # 2 dias
        "max_uses": 1,
        "requires_otp": True,
        "requires_geo": False,
        "action_label": "Responder a requerimiento del auditor",
    },
    MagicLinkPurpose.AUTORIZACION_ACCION_REMOTA: {
        "ttl_hours": 24,              # 1 dia (critico)
        "max_uses": 1,
        "requires_otp": True,
        "requires_geo": True,
        "action_label": "Autorizar accion tecnica remota",
    },
    MagicLinkPurpose.APROBACION_OBLIGACION: {
        "ttl_hours": 72,              # 3 dias
        "max_uses": 1,
        "requires_otp": False,
        "requires_geo": False,
        "action_label": "Aprobar obligacion",
    },
    MagicLinkPurpose.DESCARGA_DOSSIER_FINAL: {
        "ttl_hours": 7 * 24,          # 7 dias
        "max_uses": 3,                # permitir re-descargas
        "requires_otp": True,
        "requires_geo": False,
        "action_label": "Descargar dossier final",
    },

    # ── M8 v5.1 Verificacion Tecnica (Sesion 7) ──
    MagicLinkPurpose.AUTORIZAR_VERIFICACION_TECNICA: {
        "ttl_hours": 48,                  # 2 dias para autorizar
        "max_uses": 1,
        "requires_otp": True,             # accion sensible (acceso a sistemas)
        "requires_geo": False,
        "action_label": "Autorizar verificacion tecnica",
    },
    MagicLinkPurpose.AUTORIZAR_PENTEST_EXTERNO: {
        "ttl_hours": 72,                  # 3 dias
        "max_uses": 1,
        "requires_otp": True,             # accion muy sensible
        "requires_geo": False,
        "action_label": "Autorizar pentest externo",
    },
    MagicLinkPurpose.PORTAL_REMEDIACION: {
        "ttl_hours": 90 * 24,             # 90 dias (uso continuado por IT cliente)
        "max_uses": 9999,                 # uso libre durante el periodo
        "requires_otp": False,            # cliente entra repetidamente
        "requires_geo": False,
        "action_label": "Acceder al portal de remediacion",
    },
    MagicLinkPurpose.PORTAL_PENTESTER_EXTERNO: {
        "ttl_hours": 60 * 24,             # 60 dias para el engagement
        "max_uses": 9999,                 # pentester entra repetidamente
        "requires_otp": True,             # acceso a inventario sensible
        "requires_geo": False,
        "action_label": "Acceder al portal del pentester",
    },
    MagicLinkPurpose.REVISAR_INFORME_VERIFICACION: {
        "ttl_hours": 15 * 24,             # 15 dias para revisar
        "max_uses": 5,                    # permite revisar varias veces
        "requires_otp": True,
        "requires_geo": False,
        "action_label": "Revisar informe de verificacion",
    },

    # ── M25 Project Lifecycle Paso 4 (Sesion 8) ──
    MagicLinkPurpose.OFERTA_RETAINER: {
        "ttl_hours": 30 * 24,             # 30 dias para decidir
        "max_uses": 1,                    # una decision final
        "requires_otp": False,            # RSEG ya autenticado
        "requires_geo": False,
        "action_label": "Decidir continuidad con retainer",
    },
    MagicLinkPurpose.DESCARGA_BACKUP_ARCHIVO: {
        "ttl_hours": 60 * 24,             # 60 dias disponibilidad
        "max_uses": 20,                   # permite varias descargas
        "requires_otp": True,             # acceso a datos sensibles
        "requires_geo": False,
        "action_label": "Descargar backup del proyecto cerrado",
    },
    MagicLinkPurpose.RECONSIDERACION_RETAINER: {
        "ttl_hours": 60 * 24,             # 60 dias
        "max_uses": 1,
        "requires_otp": False,
        "requires_geo": False,
        "action_label": "Reconsiderar retainer antes del borrado",
    },

    # ── M21 Portal Cliente + Agente 15 Paso 7 (Sesion 8) ──
    MagicLinkPurpose.PRIMER_ACCESO_CLIENTE: {
        "ttl_hours": 24,                  # 24h critico seguridad
        "max_uses": 1,
        "requires_otp": True,             # OTP obligatorio primer acceso
        "requires_geo": False,
        "action_label": "Primer acceso al portal cliente",
    },
    MagicLinkPurpose.NORMATIVA_ALERT_CRITICAL: {
        "ttl_hours": 7 * 24,              # 7 dias
        "max_uses": 5,
        "requires_otp": False,
        "requires_geo": False,
        "action_label": "Revisar alerta normativa critica",
    },
    MagicLinkPurpose.RETAINER_WELCOME: {
        "ttl_hours": 7 * 24,              # 7 dias
        "max_uses": 3,
        "requires_otp": False,
        "requires_geo": False,
        "action_label": "Bienvenida al retainer FULKRO",
    },

    # ── M23 Reporting + M27 Renewal Paso 7 final (Sesion 8) ──
    MagicLinkPurpose.REPORTE_TRIMESTRAL: {
        "ttl_hours": 60 * 24,             # 60 dias
        "max_uses": 10,
        "requires_otp": False,
        "requires_geo": False,
        "action_label": "Descargar reporte trimestral",
    },
    MagicLinkPurpose.REPORTE_ANUAL: {
        "ttl_hours": 90 * 24,             # 90 dias
        "max_uses": 20,
        "requires_otp": False,
        "requires_geo": False,
        "action_label": "Descargar reporte anual",
    },
    MagicLinkPurpose.RENEWAL_CAMPAIGN_DETAILS: {
        "ttl_hours": 120 * 24,            # 120 dias (campana larga)
        "max_uses": 5,
        "requires_otp": False,
        "requires_geo": False,
        "action_label": "Revisar campana de renovacion bianual",
    },

    # ── 12 FASE 4.5 · ADR-011 · #24-#35 (Sesion 11) ──
    MagicLinkPurpose.INVITACION_REUNION: {
        "ttl_hours": 7 * 24,              # 7 dias para responder
        "max_uses": 1,
        "requires_otp": False,            # solo confirmacion asistencia
        "requires_geo": False,
        "action_label": "Confirmar asistencia a reunion",
    },
    MagicLinkPurpose.APROBACION_PROPUESTA: {
        "ttl_hours": 7 * 24,              # 7 dias para decidir P-001
        "max_uses": 3,                    # permite revisar antes de aprobar
        "requires_otp": True,             # compromiso comercial vinculante
        "requires_geo": True,             # firma jurídica
        "action_label": "Aprobar propuesta",
    },
    MagicLinkPurpose.APROBACION_FACTURA: {
        "ttl_hours": 7 * 24,              # 7 dias antes envio oficial
        "max_uses": 3,
        "requires_otp": True,             # implicacion financiera
        "requires_geo": True,
        "action_label": "Aprobar factura antes de envio",
    },
    MagicLinkPurpose.SOLICITUD_INFORMACION: {
        "ttl_hours": 14 * 24,             # 14 dias asincrono
        "max_uses": 5,                    # varias visitas posibles
        "requires_otp": False,            # pregunta abierta no vinculante
        "requires_geo": False,
        "action_label": "Responder a solicitud de informacion",
    },
    MagicLinkPurpose.VALIDACION_CAMBIO_ALCANCE: {
        "ttl_hours": 7 * 24,              # 7 dias para validar cambio M28
        "max_uses": 3,
        "requires_otp": True,             # cambio scope vinculante
        "requires_geo": True,
        "action_label": "Validar cambio de alcance",
    },
    MagicLinkPurpose.ACEPTACION_RIESGO_RESIDUAL: {
        "ttl_hours": 7 * 24,              # 7 dias para aceptar riesgo MAGERIT
        "max_uses": 3,
        "requires_otp": True,             # firma RSEG sobre riesgo asumido
        "requires_geo": True,
        "action_label": "Aceptar riesgo residual",
    },
    MagicLinkPurpose.COMUNICACION_INCIDENTE_SEGURIDAD: {
        "ttl_hours": 24,                  # 24h critico (urgencia ENS)
        "max_uses": 5,                    # consultas durante incidente
        "requires_otp": True,             # autenticidad notificacion
        "requires_geo": True,
        "action_label": "Comunicar incidente de seguridad",
    },
    MagicLinkPurpose.CONSENTIMIENTO_TRATAMIENTO_DATOS: {
        "ttl_hours": 14 * 24,             # 14 dias DPA RGPD
        "max_uses": 3,
        "requires_otp": True,             # consentimiento legal
        "requires_geo": True,
        "action_label": "Firmar consentimiento de tratamiento de datos",
    },
    MagicLinkPurpose.CONFIRMACION_CONFORMIDAD: {
        "ttl_hours": 7 * 24,              # 7 dias pre-submission ENAC
        "max_uses": 3,
        "requires_otp": True,             # firma conformidad pre-auditor
        "requires_geo": True,
        "action_label": "Confirmar conformidad antes de auditoria",
    },
    MagicLinkPurpose.DESCARGA_CERTIFICADO_CONFORMIDAD: {
        "ttl_hours": 30 * 24,             # 30 dias post-ENAC
        "max_uses": 10,                   # re-descargas legitimas
        "requires_otp": False,            # certificado ya emitido
        "requires_geo": False,
        "action_label": "Descargar certificado de conformidad ENS",
    },
    MagicLinkPurpose.VOTACION_COMITE_SEGURIDAD: {
        "ttl_hours": 7 * 24,              # 7 dias para votar
        "max_uses": 1,                    # un voto por miembro
        "requires_otp": True,             # auth voto vinculante
        "requires_geo": False,            # miembros pueden estar viajando
        "action_label": "Votar en comite de seguridad",
    },
    MagicLinkPurpose.ENCUESTA_SATISFACCION_NPS: {
        "ttl_hours": 30 * 24,             # 30 dias para responder
        "max_uses": 1,                    # una respuesta NPS
        "requires_otp": False,
        "requires_geo": False,
        "action_label": "Responder encuesta de satisfaccion NPS",
    },

    # ── SAN-D MB-19.4 · ADR-041 · #36 firma contrato comercial ──
    MagicLinkPurpose.FIRMA_CONTRATO: {
        "ttl_hours": 72,                  # 3 dias firma comercial vinculante
        "max_uses": 3,                    # cliente puede revisar antes firmar
        "requires_otp": True,             # firma legal vinculante OTP
        "requires_geo": True,             # firma con captura geo (jurídico)
        "action_label": "Firmar contrato de servicios FULKRO",
    },

    # ── Sesión 3B-2B.6 CLUSTER 2 · #37 auditor ENAC portal optional ──
    MagicLinkPurpose.AUDITOR_PORTAL_ENAC: {
        "ttl_hours": 14 * 24,             # 14 días · auditoría typical review window
        "max_uses": 9999,                 # auditor entra repetidamente
        "requires_otp": True,             # acceso a evidencias + audit log sensible
        "requires_geo": False,            # auditor puede trabajar remoto
        "action_label": "Acceder al portal del auditor ENAC",
    },
    MagicLinkPurpose.DIAGNOSTICO_PRECLIENTE: {
        "ttl_hours": 14 * 24,             # 14 días · lead frío sin urgencia · ventana amplia
        "max_uses": 3,                    # permite re-clic desde el email (consume re-emite secret)
        "requires_otp": False,            # dato pre-venta de baja sensibilidad · cero fricción
        "requires_geo": False,            # captación remota
        "action_label": "Completar diagnóstico previo ENS",
    },
}


def get_config(purpose: MagicLinkPurpose) -> PurposeConfig:
    """Devuelve la configuracion de un purpose, con validacion."""
    if purpose not in PURPOSE_CONFIG:
        raise ValueError(f"Purpose desconocido: {purpose}")
    return PURPOSE_CONFIG[purpose]
