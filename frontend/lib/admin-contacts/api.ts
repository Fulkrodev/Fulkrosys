/**
 * Admin Contacts API client wrapper (sub-fase 5.5.E FASE 5.5).
 *
 * Reusa frontend/lib/api.ts (CSRF + cookies + ApiError) — heredamos
 * el manejo común y solo añadimos typing por endpoint.
 *
 * Endpoints backend (sub-bloque 5.5.A-D commit 40b81ff):
 *   GET    /api/v1/clients/{client_id}/contacts                    list
 *   POST   /api/v1/clients/{client_id}/contacts                    create
 *   GET    /api/v1/clients/{client_id}/contacts/{contact_id}       detail
 *   PATCH  /api/v1/clients/{client_id}/contacts/{contact_id}       update
 *   POST   .../contacts/{contact_id}/deactivate
 *   POST   .../contacts/{contact_id}/activate
 *   DELETE .../contacts/{contact_id}                                hard delete
 *   GET    .../contacts/{contact_id}/timeline                       interactions
 *   POST   .../contacts/import-csv                                  bulk import
 *   GET    .../contacts/export-csv                                  bulk export
 */
import { ApiError, api } from "@/lib/api";
import type {
  ClientContactCreate,
  ClientContactListItem,
  ClientContactOut,
  ClientContactUpdate,
  ListContactsFilters,
  TimelineEntryOut,
} from "./schemas";

const base = (clientId: string) => `/api/v1/clients/${clientId}/contacts`;

function buildQuery(filters?: ListContactsFilters): string {
  if (!filters) return "";
  const params: string[] = [];
  if (filters.role_category) {
    params.push(`role_category=${encodeURIComponent(filters.role_category)}`);
  }
  if (filters.is_active !== null && filters.is_active !== undefined) {
    params.push(`is_active=${filters.is_active}`);
  }
  if (filters.is_signatory !== null && filters.is_signatory !== undefined) {
    params.push(`is_signatory=${filters.is_signatory}`);
  }
  if (filters.search && filters.search.trim()) {
    params.push(`search=${encodeURIComponent(filters.search.trim())}`);
  }
  return params.length > 0 ? `?${params.join("&")}` : "";
}

// === CRUD ===

export async function listContacts(
  clientId: string,
  filters?: ListContactsFilters,
): Promise<ClientContactListItem[]> {
  return api<ClientContactListItem[]>(`${base(clientId)}${buildQuery(filters)}`);
}

export async function getContact(
  clientId: string,
  contactId: string,
): Promise<ClientContactOut> {
  return api<ClientContactOut>(`${base(clientId)}/${contactId}`);
}

export async function createContact(
  clientId: string,
  payload: ClientContactCreate,
): Promise<ClientContactOut> {
  return api<ClientContactOut>(base(clientId), {
    method: "POST",
    json: payload,
  });
}

export async function updateContact(
  clientId: string,
  contactId: string,
  payload: ClientContactUpdate,
): Promise<ClientContactOut> {
  return api<ClientContactOut>(`${base(clientId)}/${contactId}`, {
    method: "PATCH",
    json: payload,
  });
}

export async function deactivateContact(
  clientId: string,
  contactId: string,
  reason: string,
): Promise<ClientContactOut> {
  return api<ClientContactOut>(
    `${base(clientId)}/${contactId}/deactivate`,
    { method: "POST", json: { reason } },
  );
}

export async function activateContact(
  clientId: string,
  contactId: string,
): Promise<ClientContactOut> {
  return api<ClientContactOut>(
    `${base(clientId)}/${contactId}/activate`,
    { method: "POST" },
  );
}

export async function deleteContact(
  clientId: string,
  contactId: string,
): Promise<void> {
  await api<void>(`${base(clientId)}/${contactId}`, { method: "DELETE" });
}

// === Timeline ===

export async function getContactTimeline(
  clientId: string,
  contactId: string,
  limit = 50,
): Promise<TimelineEntryOut[]> {
  return api<TimelineEntryOut[]>(
    `${base(clientId)}/${contactId}/timeline?limit=${limit}`,
  );
}

// === CSV import / export ===

export async function importContactsCsv(
  clientId: string,
  csvContent: string,
): Promise<ClientContactOut[]> {
  return api<ClientContactOut[]>(`${base(clientId)}/import-csv`, {
    method: "POST",
    json: { csv_content: csvContent },
  });
}

export async function exportContactsCsv(clientId: string): Promise<string> {
  // El endpoint devuelve text/csv plano — usamos fetch directo y leemos
  // como text para evitar el JSON parse del wrapper api().
  const res = await fetch(`${base(clientId)}/export-csv`, {
    method: "GET",
    credentials: "include",
    headers: { Accept: "text/csv" },
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new ApiError(res.status, detail || res.statusText, null);
  }
  return await res.text();
}
