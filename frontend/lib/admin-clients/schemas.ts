/**
 * Admin Clients schemas TypeScript (sub-fase 5.B FASE 5).
 *
 * Espejo de backend/app/core/clients/schemas.py + cockpit_router m21.
 * Mantener sincronizado manualmente al cambiar contratos backend.
 */

export type ClientOut = {
  id: string;
  nombre: string;
  cif: string;
  sector: string | null;
  contacto_email: string | null;
  contacto_telefono: string | null;
  created_at: string;
  // Campo derivado en frontend para listado (no presente en /clients GET):
  // se calcula post-fetch usando deleted_at del detail si necesario.
  deleted_at?: string | null;
};

export type ClientDetail = {
  id: string;
  nombre: string;
  cif: string;
  sector: string | null;
  provincia: string | null;
  numero_empleados: number | null;
  contacto_email: string | null;
  contacto_telefono: string | null;
  lead_source: string | null;
  logo_path: string | null;
  created_at: string;
  updated_at: string | null;
  deleted_at: string | null;
  projects_count: number;
  users_count: number;
  last_activity_at: string | null;
};

export type ClientCreate = {
  nombre: string;
  cif: string;
  sector?: string | null;
  contacto_email?: string | null;
  contacto_telefono?: string | null;
};

export type ClientUpdate = {
  nombre?: string | null;
  sector?: string | null;
  provincia?: string | null;
  numero_empleados?: number | null;
  contacto_email?: string | null;
  contacto_telefono?: string | null;
  lead_source?: string | null;
};

// === Audit log ===

export type AuditLogEntry = {
  id: string;
  tabla: string;
  registro_id: string;
  accion: string;
  usuario: string | null;
  timestamp: string;
  payload_old: Record<string, unknown> | null;
  payload_new: Record<string, unknown> | null;
  hash_prev: string | null;
  hash_current: string | null;
};

export type AuditLogPage = {
  items: AuditLogEntry[];
  total: number;
  page: number;
  size: number;
};

// === Facturas agregadas (m15 cross-project) ===

export type ClientInvoiceAggregated = {
  invoice_id: string;
  project_id: string | null;
  project_name: string | null;
  numero_correlativo: string | null;
  tipo: string | null;
  total: number | null;
  estado_pago: string | null;
  fecha_emision: string | null;
  fecha_vencimiento: string | null;
};

// === Cockpit users (m21 cockpit_router) ===

// ADR-013 v3 single-user-RW (MB-3 cleanup): drop role/scopes fields ·
// 1 usuario por cliente con acceso RW unico.
export type CockpitUserOut = {
  id: string;
  email: string;
  full_name: string | null;
  must_change_password: boolean;
  last_login: string | null;
  locked: boolean;
  deactivated: boolean;
};

export type CockpitCreateUserBody = {
  email: string;
  full_name: string;
  dni?: string | null;
  send_magic_link?: boolean;
  base_url?: string;
};

// === Project listing ===

export type ProjectOut = {
  id: string;
  client_id: string;
  nombre: string;
  fase: string | null;
  categoria_objetivo: string | null;
  estado: string | null;
  // Sub-atom 1.E.2.bis Phase A · lifecycle + soft delete metadata
  lifecycle_state: string | null;
  deleted_at: string | null;
  created_at: string;
};
