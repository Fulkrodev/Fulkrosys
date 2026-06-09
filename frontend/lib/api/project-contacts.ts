/**
 * Project-scoped contacts API client wrapper · sub-atom 1.C.F.1.
 *
 * Espejo de backend/app/motors/m30_client_contacts/project_scope_api.py.
 * Distinct de admin-contacts/api.ts (client-scoped) · este apunta a los
 * 4 endpoints project-scoped (ADR-046 v3 · constraint v3: 1 portal contact
 * con has_portal_access=true por project).
 *
 * Endpoints (BASE = `/api/v1/projects/{project_id}/contacts`):
 *   GET    BASE                         list
 *   POST   BASE                         create
 *   PATCH  BASE/{contact_id}            update
 *   DELETE BASE/{contact_id}            soft delete
 *
 * Tambien wrap m30 portal-user endpoint para gestion ClientUser portal:
 *   GET    /api/v1/projects/{project_id}/portal-user   status
 *   POST   /api/v1/projects/{project_id}/portal-user   ensure
 */
import { api } from "@/lib/api";

const contactsBase = (projectId: string) =>
  `/api/v1/projects/${projectId}/contacts`;

const portalUserBase = (projectId: string) =>
  `/api/v1/projects/${projectId}/portal-user`;

export type ProjectContact = {
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
  /** sub-atom 1.C.F.3 · FK department · null si sin asignar. */
  department_id?: string | null;
};

export type ProjectContactListResponse = {
  project_id: string;
  contacts: ProjectContact[];
  total: number;
  with_portal_access: number;
};

export type ProjectContactCreate = {
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
};

export type ProjectContactUpdate = Partial<ProjectContactCreate>;

export async function listProjectContacts(
  projectId: string,
): Promise<ProjectContactListResponse> {
  return api<ProjectContactListResponse>(contactsBase(projectId));
}

export async function createProjectContact(
  projectId: string,
  payload: ProjectContactCreate,
): Promise<ProjectContact> {
  return api<ProjectContact>(contactsBase(projectId), {
    method: "POST",
    json: payload,
  });
}

export async function updateProjectContact(
  projectId: string,
  contactId: string,
  payload: ProjectContactUpdate,
): Promise<ProjectContact> {
  return api<ProjectContact>(`${contactsBase(projectId)}/${contactId}`, {
    method: "PATCH",
    json: payload,
  });
}

export async function deleteProjectContact(
  projectId: string,
  contactId: string,
): Promise<void> {
  await api<void>(`${contactsBase(projectId)}/${contactId}`, {
    method: "DELETE",
  });
}

// === Portal user (1.C.F.1.1) ===

export type PortalUserStatus = {
  project_id: string;
  client_id: string;
  client_user: {
    id: string;
    email: string;
    full_name: string | null;
    must_change_password: boolean;
    last_login: string | null;
  } | null;
  portal_contact: {
    id: string;
    full_name: string;
    email: string;
    role_title: string;
    role_category: string;
    client_user_id: string | null;
  } | null;
  complete: boolean;
};

export type EnsurePortalUserBody = {
  email: string;
  full_name: string;
  create_contact?: boolean;
};

export type EnsurePortalUserResponse = {
  project_id: string;
  client_id: string;
  client_user_id: string;
  portal_contact_id: string | null;
  created_user: boolean;
  created_contact: boolean;
  temp_password: string | null;
};

export async function getPortalUserStatus(
  projectId: string,
): Promise<PortalUserStatus> {
  return api<PortalUserStatus>(portalUserBase(projectId));
}

export async function ensurePortalUser(
  projectId: string,
  body: EnsurePortalUserBody,
): Promise<EnsurePortalUserResponse> {
  return api<EnsurePortalUserResponse>(portalUserBase(projectId), {
    method: "POST",
    json: body,
  });
}

// === ENS required roles status (m30 ens_required_api · reuse 1.C.F.1 +
//     1.C.F.4 v3.10 extend con priority per category + assign/vacate) ===

export type EnsRoleAssignment = {
  contact_id: string;
  full_name: string;
  email: string;
  role_title: string;
} | null;

export type EnsRolePriority = "critical" | "recommended" | "optional";

export type EnsRequiredRolesStatus = {
  project_id: string;
  client_id: string;
  project_category: string | null;
  priority: Record<string, EnsRolePriority>;
  roles: Record<string, EnsRoleAssignment>;
  all_assigned: boolean;
  missing: string[];
  critical_missing: string[];
  total_assigned: number;
  total_required: number;
};

export async function getEnsRequiredRolesStatus(
  projectId: string,
): Promise<EnsRequiredRolesStatus> {
  return api<EnsRequiredRolesStatus>(
    `/api/v1/admin/projects/${projectId}/ens-required-roles`,
  );
}

export async function assignContactToEnsRole(
  projectId: string,
  role: string,
  contactId: string,
  notes: string | null = null,
): Promise<{
  role: string;
  contact_id: string;
  full_name: string;
  email: string;
  role_title: string;
}> {
  return api(
    `/api/v1/admin/projects/${projectId}/ens-required-roles/${role}`,
    {
      method: "PATCH",
      json: { contact_id: contactId, notes },
    },
  );
}

export async function vacateEnsRole(
  projectId: string,
  role: string,
): Promise<void> {
  await api<void>(
    `/api/v1/admin/projects/${projectId}/ens-required-roles/${role}`,
    { method: "DELETE" },
  );
}

export const ENS_ROLE_LABELS_FRONTEND: Record<string, string> = {
  sponsor: "Sponsor / Patrocinador",
  responsable_informacion: "Responsable de la Información",
  responsable_servicio: "Responsable del Servicio",
  responsable_seguridad: "Responsable de la Seguridad",
  responsable_sistema: "Responsable del Sistema",
  administrador_seguridad: "Administrador de la Seguridad",
};

export const ENS_ROLE_DESCRIPTIONS_FRONTEND: Record<string, string> = {
  sponsor:
    "Patrocinador del proyecto ENS · decisor económico/político.",
  responsable_informacion:
    "Determina requisitos de seguridad de la información tratada · " +
    "RD 311/2022 art. 11.a.",
  responsable_servicio:
    "Determina requisitos de seguridad del servicio prestado · " +
    "RD 311/2022 art. 11.b.",
  responsable_seguridad:
    "Mantiene la seguridad · firma DdA y declaración conformidad · " +
    "RD 311/2022 art. 11.c.",
  responsable_sistema:
    "Desarrollo · operación · mantenimiento del sistema · " +
    "RD 311/2022 art. 11.d.",
  administrador_seguridad:
    "Administra día a día las medidas operativas de seguridad · " +
    "RD 311/2022 art. 11.e.",
};
