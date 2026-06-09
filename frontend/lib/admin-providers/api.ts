/**
 * Admin Providers API client (SAN-E v3.MB-3.3).
 *
 * Wired al backend M14 providers/c002 (commit MB-3.B 6800b5f · 7 endpoints):
 *   GET    /api/v1/projects/{id}/providers           list + counts
 *   POST   /api/v1/projects/{id}/providers           create + auto-detect gaps
 *   DELETE /api/v1/projects/{id}/providers/{id}      soft delete
 *   GET    /api/v1/projects/{id}/providers/{id}/c002-status
 *   GET    /api/v1/projects/{id}/providers/{id}/gaps recompute
 *   POST   /api/v1/projects/{id}/providers/{id}/c002/generate
 *   POST   /api/v1/projects/{id}/providers/{id}/review mark reviewed
 */
import { api } from "@/lib/api";

export type ProviderType =
  | "cloud"
  | "saas"
  | "on-prem"
  | "staffing"
  | "hardware"
  | "consultoria";

export type Criticality = "CRITICO" | "ALTO" | "MEDIO" | "BAJO";

export type C002Status =
  | "pendiente"
  | "firmado"
  | "no_aplica"
  | "revocado";

export type GapFramework = "ENS" | "GDPR" | "NIS2";

export type GapSeverity = "CRITICA" | "ALTA" | "MEDIA" | "BAJA";

export interface Provider {
  id: string;
  project_id: string;
  name: string;
  type: ProviderType;
  scope: string;
  criticality: Criticality;
  last_reviewed_at: string | null;
  last_reviewed_by: string | null;
  c002_status: C002Status;
  gaps_count: number;
}

export interface ProviderGap {
  framework: GapFramework;
  article: string;
  severity: GapSeverity;
  description: string;
  suggested_clause: string;
}

export interface ProvidersListResponse {
  project_id: string;
  providers: Provider[];
  counts: {
    total: number;
    critico: number;
    alto: number;
    firmados: number;
    con_gaps: number;
  };
}

export interface CreateProviderPayload {
  name: string;
  type: ProviderType;
  scope: string;
  criticality: Criticality;
}

export interface CreateProviderResponse extends Provider {
  auto_detected_gaps: ProviderGap[];
}

export interface C002StatusResponse {
  provider_id: string;
  status: C002Status;
  generated_at: string | null;
  evidence_id: string | null;
}

export interface ProviderGapsResponse {
  provider_id: string;
  gaps: ProviderGap[];
  gaps_count: number;
  last_gap_check_at: string | null;
}

export interface GenerateC002Response {
  provider_id: string;
  status: C002Status;
  generated_at: string;
  covered_gaps: ProviderGap[];
}

const projectBase = (projectId: string) =>
  `/api/v1/projects/${projectId}/providers`;

export function listProviders(
  projectId: string,
): Promise<ProvidersListResponse> {
  return api<ProvidersListResponse>(projectBase(projectId));
}

export function createProvider(
  projectId: string,
  payload: CreateProviderPayload,
): Promise<CreateProviderResponse> {
  return api<CreateProviderResponse>(projectBase(projectId), {
    method: "POST",
    json: payload,
  });
}

export function deleteProvider(
  projectId: string,
  providerId: string,
): Promise<void> {
  return api<void>(`${projectBase(projectId)}/${providerId}`, {
    method: "DELETE",
  });
}

export function getC002Status(
  projectId: string,
  providerId: string,
): Promise<C002StatusResponse> {
  return api<C002StatusResponse>(
    `${projectBase(projectId)}/${providerId}/c002-status`,
  );
}

export function getProviderGaps(
  projectId: string,
  providerId: string,
): Promise<ProviderGapsResponse> {
  return api<ProviderGapsResponse>(
    `${projectBase(projectId)}/${providerId}/gaps`,
  );
}

export function generateC002(
  projectId: string,
  providerId: string,
): Promise<GenerateC002Response> {
  return api<GenerateC002Response>(
    `${projectBase(projectId)}/${providerId}/c002/generate`,
    { method: "POST", json: {} },
  );
}

export function markProviderReviewed(
  projectId: string,
  providerId: string,
): Promise<{
  provider_id: string;
  last_reviewed_at: string;
  last_reviewed_by: string | null;
}> {
  return api(`${projectBase(projectId)}/${providerId}/review`, {
    method: "POST",
    json: {},
  });
}
