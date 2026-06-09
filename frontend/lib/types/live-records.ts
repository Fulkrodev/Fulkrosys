/**
 * Tipos TypeScript live_records · sub-atom 1.C.B fase 4a.
 *
 * Mirror exacto Pydantic schemas backend (backend/app/motors/m_live_records/
 * schemas.py). 26 register_types E-300..E-325 · 9 bloques.
 *
 * Validacion de shape entry_data NO se hace en TS · se delega al backend
 * (validate_entry_data) que rechaza con HTTP 422 si payload invalido. Esto
 * permite que UI envie payload parcial mientras cliente edita.
 */
import type { EnsCategory } from "@/lib/feature-flags.types";

export type RegisterType =
  | "E-300" | "E-301" | "E-302"
  | "E-303" | "E-304"
  | "E-305" | "E-306" | "E-307"
  | "E-308" | "E-309" | "E-310"
  | "E-311" | "E-312" | "E-313"
  | "E-314" | "E-315" | "E-316"
  | "E-317" | "E-318" | "E-319"
  | "E-320" | "E-321" | "E-322"
  | "E-323" | "E-324" | "E-325";

export type LiveRecordBloque =
  | "activos"
  | "personas"
  | "incidentes"
  | "cambios"
  | "proveedores"
  | "backup"
  | "continuidad"
  | "auditoria"
  | "comite";

export type LiveRecordStatus = "active" | "archived";

export interface LiveRecord {
  id: string;
  project_id: string;
  register_type: RegisterType;
  entry_data: Record<string, unknown>;
  status: LiveRecordStatus;
  created_at: string;
  created_by: string;
  updated_at: string;
  updated_by: string;
}

export interface LiveRecordCreatePayload {
  entry_data: Record<string, unknown>;
}

export interface LiveRecordUpdatePayload {
  entry_data?: Record<string, unknown> | null;
  status?: LiveRecordStatus | null;
}

export interface LiveRecordListResponse {
  records: LiveRecord[];
  total: number;
  limit: number;
  offset: number;
}

export interface LiveRecordsDashboardBlock {
  register_type: RegisterType;
  label: string;
  bloque: LiveRecordBloque;
  active_count: number;
  archived_count: number;
}

export interface LiveRecordsDashboardResponse {
  project_id: string;
  blocks: LiveRecordsDashboardBlock[];
  total_active: number;
}

export const REGISTER_TYPES: readonly RegisterType[] = [
  "E-300", "E-301", "E-302",
  "E-303", "E-304",
  "E-305", "E-306", "E-307",
  "E-308", "E-309", "E-310",
  "E-311", "E-312", "E-313",
  "E-314", "E-315", "E-316",
  "E-317", "E-318", "E-319",
  "E-320", "E-321", "E-322",
  "E-323", "E-324", "E-325",
] as const;

export const REGISTER_TYPE_LABELS: Record<RegisterType, string> = {
  "E-300": "Inventario de activos",
  "E-301": "Inventario de sistemas",
  "E-302": "Inventario de aplicaciones",
  "E-303": "Inventario de empleados",
  "E-304": "Roles y accesos",
  "E-305": "Libro de incidentes",
  "E-306": "Libro de vulnerabilidades",
  "E-307": "Notificaciones a autoridades",
  "E-308": "Libro de cambios",
  "E-309": "Cambios materiales",
  "E-310": "Excepciones autorizadas",
  "E-311": "Inventario de proveedores",
  "E-312": "Evaluaciones de proveedores",
  "E-313": "Adendas firmadas",
  "E-314": "Libro de backups",
  "E-315": "Pruebas de restauracion",
  "E-316": "Verificaciones de integridad",
  "E-317": "BCP pruebas",
  "E-318": "DRP ejercicios",
  "E-319": "RTO/RPO measurements",
  "E-320": "Auditorias internas",
  "E-321": "Auditorias externas",
  "E-322": "Hallazgos NC + acciones correctivas",
  "E-323": "Actas Comite SGSI",
  "E-324": "Decisiones aprobadas",
  "E-325": "Indicadores SGSI mensuales",
};

export const REGISTER_TYPE_BLOQUES: Record<RegisterType, LiveRecordBloque> = {
  "E-300": "activos", "E-301": "activos", "E-302": "activos",
  "E-303": "personas", "E-304": "personas",
  "E-305": "incidentes", "E-306": "incidentes", "E-307": "incidentes",
  "E-308": "cambios", "E-309": "cambios", "E-310": "cambios",
  "E-311": "proveedores", "E-312": "proveedores", "E-313": "proveedores",
  "E-314": "backup", "E-315": "backup", "E-316": "backup",
  "E-317": "continuidad", "E-318": "continuidad", "E-319": "continuidad",
  "E-320": "auditoria", "E-321": "auditoria", "E-322": "auditoria",
  "E-323": "comite", "E-324": "comite", "E-325": "comite",
};

export const BLOQUE_LABELS: Record<LiveRecordBloque, string> = {
  activos: "Activos",
  personas: "Personas",
  incidentes: "Incidentes",
  cambios: "Cambios",
  proveedores: "Proveedores",
  backup: "Backup",
  continuidad: "Continuidad",
  auditoria: "Auditoria",
  comite: "Comite SGSI",
};

export const BLOQUE_ORDER: readonly LiveRecordBloque[] = [
  "activos",
  "personas",
  "incidentes",
  "cambios",
  "proveedores",
  "backup",
  "continuidad",
  "auditoria",
  "comite",
] as const;

export function isValidRegisterType(value: unknown): value is RegisterType {
  return typeof value === "string" && (REGISTER_TYPES as readonly string[]).includes(value);
}

export function registerTypesForBloque(bloque: LiveRecordBloque): RegisterType[] {
  return REGISTER_TYPES.filter((rt) => REGISTER_TYPE_BLOQUES[rt] === bloque);
}


/**
 * Mapping register_type → categorías ENS aplicables (sub-atom 1.C.C.B · GAP-5).
 *
 * Basado en ENS Anexo II + CCN-STIC 802 (audit) + Anexo K materializado:
 *   - BCP/DRP profundo · refuerzos R2-R4 · indicadores SGSI sistemáticos: ALTA-only
 *   - BCP básico · audit externa ENAC · refuerzos R1 · eval prov sistemática · backup
 *     integrity reforzado · cambios materiales · vulnerabilidades cuantificadas: MEDIA+
 *   - Resto (24/26 base) aplica a las tres categorías por defecto
 *
 * UI cliente usa este mapping para filtrar el dashboard y mostrar banner inline
 * en `/registros/[tipo]` cuando register_type no es aplicable a su categoría.
 */
export const REGISTER_TYPE_REQUIRED_CATEGORIES: Record<
  RegisterType,
  readonly EnsCategory[]
> = {
  "E-300": ["BASICA", "MEDIA", "ALTA"],
  "E-301": ["BASICA", "MEDIA", "ALTA"],
  "E-302": ["BASICA", "MEDIA", "ALTA"],
  "E-303": ["BASICA", "MEDIA", "ALTA"],
  "E-304": ["BASICA", "MEDIA", "ALTA"],
  "E-305": ["BASICA", "MEDIA", "ALTA"],
  "E-306": ["MEDIA", "ALTA"],            // vulnerabilidades cuantificadas (Anexo II refuerzos M/A)
  "E-307": ["BASICA", "MEDIA", "ALTA"],
  "E-308": ["BASICA", "MEDIA", "ALTA"],
  "E-309": ["MEDIA", "ALTA"],            // cambios materiales infrecuentes en BÁSICA
  "E-310": ["BASICA", "MEDIA", "ALTA"],
  "E-311": ["BASICA", "MEDIA", "ALTA"],
  "E-312": ["MEDIA", "ALTA"],            // eval proveedores sistemática M+
  "E-313": ["BASICA", "MEDIA", "ALTA"],
  "E-314": ["BASICA", "MEDIA", "ALTA"],
  "E-315": ["BASICA", "MEDIA", "ALTA"],
  "E-316": ["MEDIA", "ALTA"],            // refuerzo integridad backup (mp.info.6 M+)
  "E-317": ["MEDIA", "ALTA"],            // BCP solo M+ (op.cont CCN-STIC)
  "E-318": ["ALTA"],                     // DRP profundo solo ALTA (op.cont.4)
  "E-319": ["ALTA"],                     // RTO/RPO cuantificado solo ALTA
  "E-320": ["BASICA", "MEDIA", "ALTA"],
  "E-321": ["MEDIA", "ALTA"],            // auditoría externa ENAC NO BÁSICA (Art.34 RD 311/2022)
  "E-322": ["BASICA", "MEDIA", "ALTA"],
  "E-323": ["BASICA", "MEDIA", "ALTA"],
  "E-324": ["BASICA", "MEDIA", "ALTA"],
  "E-325": ["MEDIA", "ALTA"],            // indicadores SGSI mensuales sistemáticos M+
};


export function isRegisterTypeApplicable(
  registerType: RegisterType,
  category: EnsCategory,
): boolean {
  return REGISTER_TYPE_REQUIRED_CATEGORIES[registerType].includes(category);
}
