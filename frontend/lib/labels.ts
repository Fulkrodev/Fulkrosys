/**
 * Mapas de etiquetas para presentar enums del backend al usuario en español.
 *
 * Regla: nunca renderizar el enum crudo en la UI. Cada vez que se muestre
 * un valor que viene de BD/API, pasarlo por su mapping aquí. Si falta una
 * entrada, el helper devuelve el valor crudo como fallback (visible y
 * detectable, mejor que romper la pantalla).
 */

export const ZFP_CLASSIFICATION_LABELS: Record<string, string> = {
  confirmed: "confirmado",
  probable: "probable",
  needs_review: "revisar",
  rejected: "rechazado",
  unconfirmed: "sin confirmar",
};

export const RUN_STATUS_LABELS: Record<string, string> = {
  COMPLETED: "COMPLETADO",
  completed: "completado",
  CANCELLED: "CANCELADO",
  cancelled: "cancelado",
  RUNNING: "EN CURSO",
  running: "en curso",
  FAILED: "FALLIDO",
  failed: "fallido",
  PENDING: "PENDIENTE",
  pending: "pendiente",
  AUTHORIZED: "AUTORIZADO",
  authorized: "autorizado",
  phase1_running: "en curso (fase 1)",
  phase2_running: "en curso (fase 2)",
  phase3_validating: "validando",
};

export const MATERIALITY_LABELS: Record<string, string> = {
  MATERIAL: "MATERIAL",
  MINOR: "MENOR",
  NOT_MATERIAL: "NO MATERIAL",
};

const SECTOR_PRETTY: Record<string, string> = {
  administracion_publica: "Administración Pública",
  tecnologia: "Tecnología",
  sanidad: "Sanidad",
  salud: "Salud",
  servicios: "Servicios",
  financiero: "Financiero",
  educacion: "Educación",
  energia: "Energía",
  transporte: "Transporte",
  consultoria: "Consultoría",
  consultoria_ti: "Consultoría TI",
  legal: "Legal",
  industria: "Industria",
  logistica: "Logística",
  editorial: "Editorial",
};

function formatSlugFallback(slug: string): string {
  return slug
    .replace(/_/g, " ")
    .toLowerCase()
    .split(" ")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export function formatSector(slug: string | null | undefined): string {
  if (!slug) return "";
  const key = slug.toLowerCase();
  return SECTOR_PRETTY[key] ?? formatSlugFallback(slug);
}

export function translateLabel(
  map: Record<string, string>,
  value: string | null | undefined,
): string {
  if (value == null) return "";
  return map[value] ?? value;
}
