/**
 * Magic Link backend purposes — sincronizado con backend enum
 * MagicLinkPurpose en backend/app/motors/m12_magic_link/purposes.py
 *
 * 35 purposes total: 9 + 5 + 3 + 3 + 3 + 12 (FASE 4.5 ADR-011).
 * Si backend cambia, actualizar aquí (no auto-generado).
 *
 * Coexiste con `MagicLinkPurpose` en sprint4-types.ts (UI router · 4 valores).
 * Este type cubre el enum backend; aquel cubre routing public/(public)/[purpose].
 */

export const MAGIC_LINK_BACKEND_PURPOSES = [
  // 9 originales
  "onboarding_inicial",
  "firma_documento",
  "aporte_evidencia",
  "aprobacion_acta",
  "respuesta_requerimiento_auditor",
  "autorizacion_pentest",
  "autorizacion_accion_remota",
  "aprobacion_obligacion",
  "descarga_dossier_final",
  // 5 M8 v5.1
  "autorizar_verificacion_tecnica",
  "autorizar_pentest_externo",
  "portal_remediacion",
  "portal_pentester_externo",
  "revisar_informe_verificacion",
  // 3 M25 lifecycle
  "oferta_retainer",
  "descarga_backup_archivo",
  "reconsideracion_retainer",
  // 3 M21 + A15
  "primer_acceso_cliente",
  "normativa_alert_critical",
  "retainer_welcome",
  // 3 M23 + M27
  "reporte_trimestral",
  "reporte_anual",
  "renewal_campaign_details",
  // 12 FASE 4.5 (ADR-011 #24-#35)
  "invitacion_reunion",
  "aprobacion_propuesta",
  "aprobacion_factura",
  "solicitud_informacion",
  "validacion_cambio_alcance",
  "aceptacion_riesgo_residual",
  "comunicacion_incidente_seguridad",
  "consentimiento_tratamiento_datos",
  "confirmacion_conformidad",
  "descarga_certificado_conformidad",
  "votacion_comite_seguridad",
  "encuesta_satisfaccion_nps",
  // Sesión 3B-2B.6 CLUSTER 2 · auditor ENAC portal optional
  "auditor_portal_enac",
  // #36 SAN-D MB-19.4 · firma del contrato comercial (canvas Ed25519 · #43)
  "firma_contrato",
] as const;

export type MagicLinkBackendPurpose =
  (typeof MAGIC_LINK_BACKEND_PURPOSES)[number];

/**
 * Labels UI español formal (replica EXACTA del action_label de
 * PURPOSE_CONFIG backend para coherencia copy).
 */
export const MAGIC_LINK_BACKEND_LABELS: Record<MagicLinkBackendPurpose, string> = {
  onboarding_inicial: "Completar onboarding inicial",
  firma_documento: "Firmar documento",
  aporte_evidencia: "Aportar evidencias",
  aprobacion_acta: "Aprobar acta",
  respuesta_requerimiento_auditor: "Responder a requerimiento del auditor",
  autorizacion_pentest: "Autorizar pentest",
  autorizacion_accion_remota: "Autorizar accion tecnica remota",
  aprobacion_obligacion: "Aprobar obligacion",
  descarga_dossier_final: "Descargar dossier final",
  autorizar_verificacion_tecnica: "Autorizar verificacion tecnica",
  autorizar_pentest_externo: "Autorizar pentest externo",
  portal_remediacion: "Acceder al portal de remediacion",
  portal_pentester_externo: "Acceder al portal del pentester",
  revisar_informe_verificacion: "Revisar informe de verificacion",
  oferta_retainer: "Decidir continuidad con retainer",
  descarga_backup_archivo: "Descargar backup del proyecto cerrado",
  reconsideracion_retainer: "Reconsiderar retainer antes del borrado",
  primer_acceso_cliente: "Primer acceso al portal cliente",
  normativa_alert_critical: "Revisar alerta normativa critica",
  retainer_welcome: "Bienvenida al retainer FULKRO",
  reporte_trimestral: "Descargar reporte trimestral",
  reporte_anual: "Descargar reporte anual",
  renewal_campaign_details: "Revisar campana de renovacion bianual",
  invitacion_reunion: "Confirmar asistencia a reunion",
  aprobacion_propuesta: "Aprobar propuesta",
  aprobacion_factura: "Aprobar factura antes de envio",
  solicitud_informacion: "Responder a solicitud de informacion",
  validacion_cambio_alcance: "Validar cambio de alcance",
  aceptacion_riesgo_residual: "Aceptar riesgo residual",
  comunicacion_incidente_seguridad: "Comunicar incidente de seguridad",
  consentimiento_tratamiento_datos: "Firmar consentimiento de tratamiento de datos",
  confirmacion_conformidad: "Confirmar conformidad antes de auditoria",
  descarga_certificado_conformidad: "Descargar certificado de conformidad ENS",
  votacion_comite_seguridad: "Votar en comite de seguridad",
  encuesta_satisfaccion_nps: "Responder encuesta de satisfaccion NPS",
  auditor_portal_enac: "Acceder al portal del auditor ENAC",
  firma_contrato: "Firmar contrato de servicios FULKRO",
};

/**
 * Agrupación UI por categoría operativa (combobox dropdown del generator).
 * Los purposes deprecated se exponen en su propio grupo para audit visibility
 * pero el componente generator filtra el grupo "Deprecated" del select.
 */
export const MAGIC_LINK_BACKEND_CATEGORIES: Record<
  string,
  readonly MagicLinkBackendPurpose[]
> = {
  "Onboarding y acceso": [
    "onboarding_inicial",
    "primer_acceso_cliente",
    "retainer_welcome",
  ],
  "Firma documental": [
    "firma_documento",
    "aprobacion_acta",
    "aprobacion_propuesta",
    "aprobacion_factura",
    "validacion_cambio_alcance",
    "aceptacion_riesgo_residual",
    "consentimiento_tratamiento_datos",
    "confirmacion_conformidad",
    "firma_contrato",
  ],
  "Evidencias y verificación": [
    "aporte_evidencia",
    "autorizar_verificacion_tecnica",
    "autorizar_pentest_externo",
    "portal_remediacion",
    "portal_pentester_externo",
    "revisar_informe_verificacion",
    "respuesta_requerimiento_auditor",
    "auditor_portal_enac",
  ],
  "Comunicación y reporting": [
    "solicitud_informacion",
    "invitacion_reunion",
    "reporte_trimestral",
    "reporte_anual",
    "comunicacion_incidente_seguridad",
    "normativa_alert_critical",
    "votacion_comite_seguridad",
  ],
  "Cierre y descargas": [
    "descarga_dossier_final",
    "descarga_backup_archivo",
    "descarga_certificado_conformidad",
    "encuesta_satisfaccion_nps",
    "oferta_retainer",
    "reconsideracion_retainer",
    "renewal_campaign_details",
  ],
  Deprecated: [
    "autorizacion_pentest",
    "autorizacion_accion_remota",
    "aprobacion_obligacion",
  ],
};

/**
 * Response de GET /magic-links/by-token/{token} (público · sin auth).
 * Source of truth: backend MagicLinkPublicStatus en m12_magic_link/schemas.py.
 *
 * Privacidad: subset estricto · NO expone id interno, project_id,
 * recipient_email completo (solo hint enmascarado), cc_emails,
 * custom_subject/body_intro, sent_to_contact_id, allowed_countries.
 */
export interface MagicLinkStatus {
  tipo_operacion: MagicLinkBackendPurpose;
  scope: Record<string, unknown> | null;
  expira_at: string;
  max_usos: number | null;
  usos: number;
  revocado: boolean;
  /** "jor***@dataforma.es" · NULL si recipient_email no fijado. */
  recipient_email_hint: string | null;
}

/**
 * Purposes que requieren OTP (derivable client-side desde el purpose).
 * Coherente con PURPOSE_CONFIG[purpose].requires_otp del backend.
 */
export const MAGIC_LINK_OTP_REQUIRED: ReadonlySet<MagicLinkBackendPurpose> =
  new Set<MagicLinkBackendPurpose>([
    "firma_documento",
    "aprobacion_acta",
    "respuesta_requerimiento_auditor",
    "autorizacion_pentest",
    "autorizacion_accion_remota",
    "descarga_dossier_final",
    "autorizar_verificacion_tecnica",
    "autorizar_pentest_externo",
    "portal_pentester_externo",
    "revisar_informe_verificacion",
    "descarga_backup_archivo",
    "primer_acceso_cliente",
    "aprobacion_propuesta",
    "aprobacion_factura",
    "validacion_cambio_alcance",
    "aceptacion_riesgo_residual",
    "comunicacion_incidente_seguridad",
    "consentimiento_tratamiento_datos",
    "confirmacion_conformidad",
    "votacion_comite_seguridad",
    "firma_contrato",
  ]);

/**
 * Computa is_active desde MagicLinkStatus (frontend-side · spec ADR-011 B.1).
 */
export function isMagicLinkActive(status: MagicLinkStatus, now: Date = new Date()): boolean {
  if (status.revocado) return false;
  if (new Date(status.expira_at) < now) return false;
  const max = status.max_usos ?? 1;
  if (status.usos >= max) return false;
  return true;
}

/**
 * Response de POST /magic-links/generate (admin only).
 */
export interface MagicLinkRecord {
  id: string;
  project_id: string;
  tipo_operacion: MagicLinkBackendPurpose;
  recipient_email: string | null;
  cc_emails: string[] | null;
  custom_subject: string | null;
  expira_at: string;
  max_usos: number | null;
  usos: number;
  revocado: boolean;
  revoked_at: string | null;
  sent_to_contact_id: string | null;
  created_at: string;
}

/**
 * #11 · Response de POST /magic-links/generate-and-send (admin · botón manual).
 * Genera el enlace Y lo envía por email en un paso.
 */
export interface GenerateAndSendMagicLinkResponse {
  magic_link_id: string;
  url: string;
  expires_at: string;
  purpose: MagicLinkBackendPurpose;
  action_label: string;
  // OTP presente sólo si el purpose lo requiere. NO viaja en el email del enlace
  // (anularía el 2º factor) · transmitir por canal separado (SMS/teléfono).
  otp: string | null;
  email_sent: boolean;
  email_backend: string;
  email_message_id: string | null;
  email_error: string | null;
  recipient_email: string;
}

/**
 * Request body POST /magic-links/generate.
 */
export interface GenerateMagicLinkRequest {
  project_id: string;
  purpose: MagicLinkBackendPurpose;
  recipient_email: string;
  scope?: Record<string, unknown>;
  ttl_hours?: number;
  max_uses?: number;
  cc_emails?: string[];
  custom_subject?: string;
  custom_body_intro?: string;
  sent_to_contact_id?: string;
  allowed_countries?: string[];
}

/**
 * Request body POST /magic-links/consume.
 */
export interface ConsumeMagicLinkRequest {
  token: string;
  otp?: string;
  decision?: "approve" | "reject";
  justificacion?: string;
  payload?: Record<string, unknown>;
}

export interface ConsumeMagicLinkResponse {
  ok: boolean;
  consumed_at: string;
  remaining_uses: number;
}
