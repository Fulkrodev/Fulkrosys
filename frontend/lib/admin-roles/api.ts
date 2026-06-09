/**
 * Admin Roles API client (SAN-E v3.MB-3.5).
 *
 * Wired al backend M28 role-topology (commit MB-3.E 6daaae2 + GET endpoint
 * añadido en MB-3.5) + M30 EXTENDED project-scoped contacts (commit MB-3.C
 * 8f40347 · constraint v3 partial UNIQUE).
 *
 * Backend M28:
 *   GET  /api/v1/projects/{id}/role-topology
 *   POST /api/v1/projects/{id}/role-topology/{role_code}/assign
 *   POST /api/v1/projects/{id}/role-topology/{role_code}/vacate
 *
 * Backend M30 EXTENDED project-scoped:
 *   GET    /api/v1/projects/{id}/contacts
 *   POST   /api/v1/projects/{id}/contacts
 *   PATCH  /api/v1/projects/{id}/contacts/{contact_id}
 *   DELETE /api/v1/projects/{id}/contacts/{contact_id}
 */
import { api } from "@/lib/api";

export type RoleCode =
  | "sponsor"
  | "responsable_informacion"
  | "responsable_servicio"
  | "responsable_seguridad"
  | "responsable_sistema"
  | "dpo"
  | "ciso"
  | "responsable_proteccion_datos"
  | "auditor"
  | "punto_contacto_ccn"
  | "miembro_comite_seguridad";

export interface RoleMeta {
  code: RoleCode;
  label: string;
  short: string;
  description: string;
  ensOfficial: boolean;
}

export const ROLES_ENS_REQUIRED: RoleMeta[] = [
  {
    code: "sponsor",
    label: "Sponsor",
    short: "Sponsor",
    description: "Patrocinador del proyecto · CEO o equivalente · aprueba presupuestos.",
    ensOfficial: true,
  },
  {
    code: "responsable_informacion",
    label: "Responsable de la Información",
    short: "RI",
    description: "Decide qué datos trata el sistema y su sensibilidad.",
    ensOfficial: true,
  },
  {
    code: "responsable_servicio",
    label: "Responsable del Servicio",
    short: "RS",
    description: "Define qué presta el sistema y disponibilidad requerida.",
    ensOfficial: true,
  },
  {
    code: "responsable_seguridad",
    label: "Responsable de Seguridad",
    short: "RSEG",
    description: "Diseña y supervisa medidas. Firma DdA y políticas.",
    ensOfficial: true,
  },
  {
    code: "responsable_sistema",
    label: "Responsable del Sistema",
    short: "RSIS",
    description: "Implementa técnicamente las medidas. Suele ser Director TI.",
    ensOfficial: true,
  },
];

export const ROLES_CROSS_COMPLIANCE: RoleMeta[] = [
  {
    code: "dpo",
    label: "DPO · Delegado Protección Datos",
    short: "DPO",
    description: "Garantiza cumplimiento RGPD · obligatorio si tratamiento datos personales a gran escala.",
    ensOfficial: false,
  },
  {
    code: "ciso",
    label: "CISO · Chief Information Security Officer",
    short: "CISO",
    description: "Liderazgo seguridad información · alineado con ISO 27001.",
    ensOfficial: false,
  },
  {
    code: "auditor",
    label: "Auditor interno",
    short: "Auditor",
    description: "Auditoría continua · separación de funciones · independiente del RSEG.",
    ensOfficial: false,
  },
];

export const ROLE_LABELS: Record<RoleCode, RoleMeta> = Object.fromEntries(
  [...ROLES_ENS_REQUIRED, ...ROLES_CROSS_COMPLIANCE].map((r) => [r.code, r]),
) as Record<RoleCode, RoleMeta>;

export interface ContactSummary {
  id: string;
  full_name: string;
  email: string;
  phone: string | null;
  role_title: string;
  has_portal_access: boolean;
}

export interface RoleAssignment {
  role_code: RoleCode;
  is_required: boolean;
  is_cross_compliance: boolean;
  assignment_id: string | null;
  contact_id: string | null;
  contact: ContactSummary | null;
  assigned_at: string | null;
  assigned_by: string | null;
  notes: string | null;
}

export interface RoleTopologyResponse {
  project_id: string;
  roles_required: RoleAssignment[];
  cross_compliance_extras: RoleAssignment[];
  coverage_pct: number;
  assigned_required: number;
  total_required: number;
  blockers: RoleCode[];
}

export interface ProjectContact {
  id: string;
  client_id: string;
  project_id: string | null;
  full_name: string;
  email: string;
  phone: string | null;
  linkedin_url: string | null;
  role_title: string;
  role_category: string;
  is_primary: boolean;
  is_signatory: boolean;
  has_portal_access: boolean;
  notes_marcos: string | null;
  is_active: boolean;
  created_at: string | null;
}

export interface ProjectContactsListResponse {
  project_id: string;
  contacts: ProjectContact[];
  total: number;
  with_portal_access: number;
}

export interface AssignRolePayload {
  contact_id: string;
  notes?: string | null;
}

export interface AssignRoleResponse {
  id: string;
  project_id: string;
  role_code: string;
  contact_id: string;
  contact_name: string;
  assigned_at: string;
  is_required: boolean;
  is_cross_compliance: boolean;
}

export interface CreateContactPayload {
  full_name: string;
  email: string;
  phone?: string | null;
  linkedin_url?: string | null;
  role_title: string;
  role_category: string;
  has_portal_access?: boolean;
  notes_marcos?: string | null;
  is_primary?: boolean;
  is_signatory?: boolean;
}

const projectBase = (projectId: string) => `/api/v1/projects/${projectId}`;

// ─── M28 role-topology ──────────────────────────────────────────────

export function getRoleTopology(
  projectId: string,
): Promise<RoleTopologyResponse> {
  return api<RoleTopologyResponse>(`${projectBase(projectId)}/role-topology`);
}

export function assignRole(
  projectId: string,
  roleCode: RoleCode,
  payload: AssignRolePayload,
): Promise<AssignRoleResponse> {
  return api<AssignRoleResponse>(
    `${projectBase(projectId)}/role-topology/${roleCode}/assign`,
    { method: "POST", json: payload },
  );
}

export function vacateRole(
  projectId: string,
  roleCode: RoleCode,
): Promise<{
  id: string;
  project_id: string;
  role_code: string;
  vacated: boolean;
}> {
  return api(`${projectBase(projectId)}/role-topology/${roleCode}/vacate`, {
    method: "POST",
    json: {},
  });
}

// ─── M30 project-scoped contacts ────────────────────────────────────

export function listProjectContacts(
  projectId: string,
): Promise<ProjectContactsListResponse> {
  return api<ProjectContactsListResponse>(`${projectBase(projectId)}/contacts`);
}

export function createProjectContact(
  projectId: string,
  payload: CreateContactPayload,
): Promise<ProjectContact> {
  return api<ProjectContact>(`${projectBase(projectId)}/contacts`, {
    method: "POST",
    json: payload,
  });
}

export function updateProjectContact(
  projectId: string,
  contactId: string,
  payload: Partial<CreateContactPayload>,
): Promise<ProjectContact> {
  return api<ProjectContact>(`${projectBase(projectId)}/contacts/${contactId}`, {
    method: "PATCH",
    json: payload,
  });
}

export function deleteProjectContact(
  projectId: string,
  contactId: string,
): Promise<void> {
  return api<void>(`${projectBase(projectId)}/contacts/${contactId}`, {
    method: "DELETE",
  });
}
