/**
 * Motor 30 — Client Contacts API client (subset · MB-9.bis.4).
 *
 * Endpoints expuestos:
 *  - GET /api/v1/clients/{client_id}/contacts/validate-roles-ens
 *
 * Refs: SAN-C.MB-9.5 (backend) · SAN-C.MB-9.bis.4 (frontend wire-up).
 */
import { api } from "@/lib/api";

const BASE = "/api/v1";

export type EnsCategoryTarget = "BASICA" | "MEDIA" | "ALTA";
export type RoleViolationSeverity = "mayor" | "menor";

export interface RoleViolation {
  rule: string;
  severity: RoleViolationSeverity;
  detail: string;
  contact_ids: string[];
}

export interface RoleValidationResult {
  client_id: string;
  target_category: EnsCategoryTarget;
  compliant: boolean;
  assigned_roles: Record<string, string[]>;
  missing_roles: string[];
  violations: RoleViolation[];
}

/**
 * GET /api/v1/clients/{client_id}/contacts/validate-roles-ens
 *
 * Valida segregación funcional ENS (CCN-STIC 801) + roles obligatorios per
 * categoría. Reglas:
 *  - RSEG y RSIS no pueden ser misma persona (severity mayor)
 *  - BÁSICA exige RI/RS/RSEG/RSIS · MEDIA añade POC · ALTA añade Comité
 */
export function validateRolesEns(
  clientId: string,
  targetCategory: EnsCategoryTarget = "BASICA",
): Promise<RoleValidationResult> {
  const qs = new URLSearchParams({ target_category: targetCategory });
  return api(
    `${BASE}/clients/${clientId}/contacts/validate-roles-ens?${qs.toString()}`,
  );
}
