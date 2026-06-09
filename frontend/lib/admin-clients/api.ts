/**
 * Admin Clients API client wrapper (sub-fase 5.B FASE 5).
 *
 * Reusa frontend/lib/api.ts (CSRF + cookies + ApiError) — heredamos
 * el manejo común y solo añadimos typing por endpoint.
 *
 * Endpoints backend (sub-fase 5.A FASE 5 commit a97f514):
 *   GET    /api/v1/clients                            list
 *   POST   /api/v1/clients                            create
 *   GET    /api/v1/clients/{id}                       detail
 *   PATCH  /api/v1/clients/{id}                       update partial
 *   POST   /api/v1/clients/{id}/suspend               soft delete
 *   POST   /api/v1/clients/{id}/resume                unset deleted_at
 *   GET    /api/v1/clients/{id}/audit                 audit log paginated
 *   GET    /api/v1/clients/{id}/projects              list projects
 *   GET    /api/v1/billing/clients/{id}/invoices      aggregated invoices
 *
 * Cockpit users (m21 prefix /clients/{client_id}/users) · ADR-013 v3:
 *   POST   ""                                         create user (RW único)
 *   POST   /{user_id}/resend-invite
 *   GET    ""                                         list users
 *   POST   /{user_id}/reset-password
 *   DELETE /{user_id}                                 deactivate
 *
 * NOTA MB-3 cleanup: PATCH /{user_id}/role + GET /roles dropped backend ·
 * single-user-RW.
 */
import { api } from "@/lib/api";
import type {
  AuditLogPage,
  ClientCreate,
  ClientDetail,
  ClientInvoiceAggregated,
  ClientOut,
  ClientUpdate,
  CockpitCreateUserBody,
  CockpitUserOut,
  ProjectOut,
} from "./schemas";

// Re-export para consumidores que importan el tipo junto a las funciones CRUD
// desde este módulo (p.ej. EditClientMetaModal).
export type { ClientUpdate } from "./schemas";

// === Clients CRUD ===

export async function listClients(): Promise<ClientOut[]> {
  return api<ClientOut[]>("/api/v1/clients");
}

export async function getClientDetail(
  clientId: string,
): Promise<ClientDetail> {
  return api<ClientDetail>(`/api/v1/clients/${clientId}`);
}

export async function createClient(
  payload: ClientCreate,
): Promise<ClientOut> {
  return api<ClientOut>("/api/v1/clients", {
    method: "POST",
    json: payload,
  });
}

export async function updateClient(
  clientId: string,
  payload: ClientUpdate,
): Promise<ClientOut> {
  return api<ClientOut>(`/api/v1/clients/${clientId}`, {
    method: "PATCH",
    json: payload,
  });
}

export async function suspendClient(
  clientId: string,
): Promise<ClientDetail> {
  return api<ClientDetail>(`/api/v1/clients/${clientId}/suspend`, {
    method: "POST",
  });
}

export async function resumeClient(
  clientId: string,
): Promise<ClientDetail> {
  return api<ClientDetail>(`/api/v1/clients/${clientId}/resume`, {
    method: "POST",
  });
}

// === Audit log ===

export async function getClientAuditLog(
  clientId: string,
  page = 1,
  size = 25,
): Promise<AuditLogPage> {
  const params = new URLSearchParams({
    page: String(page),
    size: String(size),
  });
  return api<AuditLogPage>(
    `/api/v1/clients/${clientId}/audit?${params.toString()}`,
  );
}

// === Projects (existing) ===

export async function listClientProjects(
  clientId: string,
): Promise<ProjectOut[]> {
  return api<ProjectOut[]>(`/api/v1/clients/${clientId}/projects`);
}

// Sub-atom 1.E.2.bis Phase A · project CRUD wrappers
export interface ProjectCreateBody {
  nombre: string;
  categoria_objetivo?: "BASICA" | "MEDIA" | "ALTA" | null;
  fase?: string | null;
}

export async function createClientProject(
  clientId: string,
  body: ProjectCreateBody,
): Promise<ProjectOut> {
  return api<ProjectOut>(`/api/v1/clients/${clientId}/projects`, {
    method: "POST",
    json: body,
  });
}

export async function archiveClientProject(
  clientId: string,
  projectId: string,
): Promise<ProjectOut> {
  return api<ProjectOut>(
    `/api/v1/clients/${clientId}/projects/${projectId}`,
    { method: "DELETE" },
  );
}

// === Billing aggregated (sub-fase 5.A H4) ===

export async function listClientInvoices(
  clientId: string,
): Promise<ClientInvoiceAggregated[]> {
  return api<ClientInvoiceAggregated[]>(
    `/api/v1/billing/clients/${clientId}/invoices`,
  );
}

// === Cockpit users (m21) ===

export async function listCockpitUsers(
  clientId: string,
): Promise<CockpitUserOut[]> {
  return api<CockpitUserOut[]>(`/api/v1/clients/${clientId}/users`);
}

export async function cockpitCreateUser(
  clientId: string,
  body: CockpitCreateUserBody,
): Promise<{
  user: CockpitUserOut;
  temp_password?: string | null;
  magic_link_sent?: boolean;
}> {
  return api(`/api/v1/clients/${clientId}/users`, {
    method: "POST",
    json: body,
  });
}

export async function cockpitResendInvite(
  clientId: string,
  userId: string,
): Promise<{ ok: boolean }> {
  return api(`/api/v1/clients/${clientId}/users/${userId}/resend-invite`, {
    method: "POST",
  });
}

export async function cockpitResetPassword(
  clientId: string,
  userId: string,
): Promise<{ temp_password: string }> {
  return api(
    `/api/v1/clients/${clientId}/users/${userId}/reset-password`,
    { method: "POST" },
  );
}

export async function cockpitDeactivate(
  clientId: string,
  userId: string,
): Promise<{ ok: boolean }> {
  return api(`/api/v1/clients/${clientId}/users/${userId}`, {
    method: "DELETE",
  });
}
