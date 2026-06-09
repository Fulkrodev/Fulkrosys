/**
 * API client live_records · sub-atom 1.C.B fase 4a.
 *
 * 8 funciones REST sobre /api/v1/projects/{id}/records/*. Backend
 * usa require_marcos_or_client → portal cliente accede directamente
 * via clientApi (cookies httpOnly + CSRF) sin necesidad de wrapper admin.
 *
 * Export CSV/XLSX devuelve Blob (fetch directo no via clientApi porque
 * la respuesta es binaria · no JSON).
 */
import { CSRF_HEADER } from "@/lib/constants";
import { getCsrfToken } from "@/lib/csrf";
import { clientApi, ClientApiError } from "@/lib/client-portal-api";

import type {
  LiveRecord,
  LiveRecordCreatePayload,
  LiveRecordListResponse,
  LiveRecordUpdatePayload,
  LiveRecordsDashboardResponse,
  LiveRecordStatus,
  RegisterType,
} from "@/lib/types/live-records";

// `clientApi` ya antepone "/api/v1" — aquí solo el segmento desde la raíz.
const BASE = "/projects";

function pathFor(projectId: string, segments: string[]): string {
  const tail = segments.join("/");
  return `${BASE}/${projectId}/records${tail ? `/${tail}` : ""}`;
}

export async function getLiveRecordsDashboard(
  projectId: string,
): Promise<LiveRecordsDashboardResponse> {
  return clientApi<LiveRecordsDashboardResponse>(pathFor(projectId, ["dashboard"]));
}

export interface ListLiveRecordsParams {
  status?: LiveRecordStatus | "all";
  limit?: number;
  offset?: number;
}

export async function listLiveRecords(
  projectId: string,
  registerType: RegisterType,
  params: ListLiveRecordsParams = {},
): Promise<LiveRecordListResponse> {
  const query = new URLSearchParams();
  if (params.status !== undefined) query.set("status", params.status);
  if (params.limit !== undefined) query.set("limit", String(params.limit));
  if (params.offset !== undefined) query.set("offset", String(params.offset));
  const qs = query.toString();
  return clientApi<LiveRecordListResponse>(
    pathFor(projectId, [registerType]) + (qs ? `?${qs}` : ""),
  );
}

export async function getLiveRecord(
  projectId: string,
  registerType: RegisterType,
  recordId: string,
): Promise<LiveRecord> {
  return clientApi<LiveRecord>(pathFor(projectId, [registerType, recordId]));
}

export async function createLiveRecord(
  projectId: string,
  registerType: RegisterType,
  entryData: Record<string, unknown>,
): Promise<LiveRecord> {
  const payload: LiveRecordCreatePayload = { entry_data: entryData };
  return clientApi<LiveRecord>(pathFor(projectId, [registerType]), {
    json: payload,
  });
}

export async function updateLiveRecord(
  projectId: string,
  registerType: RegisterType,
  recordId: string,
  payload: LiveRecordUpdatePayload,
): Promise<LiveRecord> {
  return clientApi<LiveRecord>(pathFor(projectId, [registerType, recordId]), {
    method: "PATCH",
    json: payload,
  });
}

export async function archiveLiveRecord(
  projectId: string,
  registerType: RegisterType,
  recordId: string,
): Promise<void> {
  await clientApi<void>(pathFor(projectId, [registerType, recordId]), {
    method: "DELETE",
  });
}

async function fetchBlob(path: string, accept: string): Promise<Blob> {
  const csrf = getCsrfToken();
  const headers = new Headers({ Accept: accept });
  if (csrf) headers.set(CSRF_HEADER, csrf);

  // `fetchBlob` no usa `clientApi`; añade el prefijo /api/v1 aquí mismo.
  const response = await fetch(`/api/v1${path}`, {
    method: "GET",
    credentials: "include",
    headers,
  });

  if (!response.ok) {
    throw new ClientApiError(
      response.status,
      response.statusText || "export failed",
      null,
    );
  }
  return response.blob();
}

export async function exportLiveRecordsCsv(
  projectId: string,
  registerType: RegisterType,
): Promise<Blob> {
  return fetchBlob(
    pathFor(projectId, [registerType, "export", "csv"]),
    "text/csv",
  );
}

export async function exportLiveRecordsXlsx(
  projectId: string,
  registerType: RegisterType,
): Promise<Blob> {
  return fetchBlob(
    pathFor(projectId, [registerType, "export", "xlsx"]),
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  );
}

export function triggerBlobDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}
