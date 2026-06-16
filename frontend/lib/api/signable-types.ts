/**
 * Canonical frontend SignableType catalog · single source of truth.
 *
 * Espeja 1:1 el catálogo backend `backend/app/motors/m05_signing/signable_types.py`
 * (18 tipos firmables). Antes existían dos uniones FE divergentes — `signing.ts`
 * (12 valores) y `signing-history.ts` (7 valores) — ninguna alineada con los 18
 * del backend. Este módulo unifica el linaje (§4.1 / line 341-342 · OPS-026 DRY).
 *
 * Mantener en sincronía con el backend al añadir nuevos tipos firmables.
 */

/** 18 tipos firmables · idéntico al `SignableType` Literal del backend M05. */
export type SignableType =
  | "dda"
  | "magerit_validation"
  | "pentest_authorization"
  | "conformidad_ens"
  | "declaracion_conformidad_basica"
  | "acta_comite"
  | "retainer_offer"
  | "retainer_quarterly_signoff"
  | "policy_approval"
  | "incident_close"
  | "dpc_anual"
  | "renewal"
  | "acta_nombramiento_roles"
  | "acta_decision_direccion"
  | "plan_adecuacion"
  | "documento_alcance"
  | "contrato_comercial"
  | "document_generic";

/**
 * Etiquetas ES por tipo firmable · espejo de `SIGNABLE_TYPE_LABELS` del backend.
 *
 * Fuente única de etiquetas en el frontend. Los flujos de firma reciben hoy un
 * `signableLabel: string` por botón; este mapa permite resolver la etiqueta
 * canónica cuando sólo se dispone del `signable_type` (p. ej. el firmas-hub).
 */
export const SIGNABLE_TYPE_LABELS_ES: Record<SignableType, string> = {
  dda: "Declaración de Aplicabilidad (SoA · 73 medidas del Anexo II)",
  magerit_validation: "Validación de activos MAGERIT",
  pentest_authorization: "Autorización de pentest externo",
  conformidad_ens: "Declaración de Conformidad ENS",
  declaracion_conformidad_basica:
    "Declaración de Conformidad ENS BÁSICA (autodeclaración · Dirección)",
  acta_comite: "Acta del Comité de Seguridad",
  retainer_offer: "Aceptación de oferta de retainer",
  retainer_quarterly_signoff: "Comité Retainer trimestral · revisión y firma",
  policy_approval: "Aprobación de política",
  incident_close: "Cierre de incidente de seguridad",
  dpc_anual: "Declaración Protección Continuidad (DPC) anual",
  renewal: "Renovación bianual ENS",
  acta_nombramiento_roles: "Acta de Nombramiento de Roles ENS",
  acta_decision_direccion:
    "Acta de Decisión de Adecuación al ENS de la Dirección",
  plan_adecuacion: "Plan de Adecuación al ENS",
  documento_alcance: "Documento de Alcance del SGSI",
  contrato_comercial: "Contrato comercial de servicios FULKRO",
  document_generic: "Documento",
};

/**
 * Resuelve la etiqueta ES canónica de un `signable_type`. Si llega un tipo
 * desconocido (drift backend no propagado), cae al genérico sin romper la UI.
 */
export function signableLabelEs(signableType: string): string {
  return (
    SIGNABLE_TYPE_LABELS_ES[signableType as SignableType] ??
    SIGNABLE_TYPE_LABELS_ES.document_generic
  );
}
