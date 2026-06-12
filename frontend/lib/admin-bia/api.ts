/**
 * Admin BIA API client (SAN-C MB-11.5).
 *
 * Endpoints backend (api/v1 m19_risk.bia_api):
 *   POST /api/v1/projects/{project_id}/bia/analyses
 *   GET  /api/v1/projects/{project_id}/bia/analyses
 *   GET  /api/v1/projects/{project_id}/bia/summary
 */
"use client";

import { api } from "@/lib/api";

export interface BiaEntry {
  id: string;
  service_name: string;
  rto_hours: number;
  rpo_hours: number;
  daily_impact_eur?: string;
  stakeholders?: string[];
  minimum_resources?: Record<string, unknown>;
}

export interface BiaSummary {
  services_count: number;
  max_rto_hours: number | null;
  max_rpo_hours: number | null;
  total_daily_impact_eur: string | null;
}

export interface BiaEntryCreate {
  service_name: string;
  rto_hours: number;
  rpo_hours: number;
  daily_impact_eur?: string;
  stakeholders?: string[];
  minimum_resources?: Record<string, unknown>;
}

// feat/fulkro-100 Ola A · continuidad admin buzón (cierra el loop sync con el cliente)
export interface ContinuidadQuestionnaire {
  submitted_at: string;
  updated_at: string;
  procesos_criticos?: { nombre?: string; descripcion?: string }[] | null;
  rto_horas_tolerancia?: number | null;
  rpo_horas_tolerancia?: number | null;
  impacto_diario_eur?: string | null;
  activos_core?: { nombre?: string; tipo?: string }[] | null;
  notas_cliente?: string | null;
  completed: boolean;
}

export interface ContinuidadApproval {
  id: string;
  artifact_type: string;
  draft_id?: string | null;
  action: string;
  comment_text?: string | null;
  created_at: string;
}

export interface ContinuidadBuzon {
  has_questionnaire: boolean;
  questionnaire?: ContinuidadQuestionnaire | null;
  approvals: ContinuidadApproval[];
  pending_comments: number;
}

export interface NotifyDraftReadyBody {
  artifact_type: "bia" | "drp";
  draft_id?: string | null;
  message?: string | null;
}

const BASE = "/api/v1/projects";
const ADMIN_BASE = "/api/v1/admin/projects";

export async function getContinuidadBuzon(
  projectId: string,
): Promise<ContinuidadBuzon> {
  return api<ContinuidadBuzon>(
    `${ADMIN_BASE}/${projectId}/continuidad/buzon`,
  );
}

export async function notifyDraftReady(
  projectId: string,
  body: NotifyDraftReadyBody,
): Promise<{ ok: boolean; event_type: string }> {
  return api<{ ok: boolean; event_type: string }>(
    `${ADMIN_BASE}/${projectId}/continuidad/notify-draft-ready`,
    { method: "POST", body: JSON.stringify(body) },
  );
}

export async function createBiaEntry(
  projectId: string,
  body: BiaEntryCreate,
): Promise<BiaEntry> {
  return api<BiaEntry>(`${BASE}/${projectId}/bia/analyses`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function listBiaEntries(projectId: string): Promise<BiaEntry[]> {
  return api<BiaEntry[]>(`${BASE}/${projectId}/bia/analyses`);
}

export async function getBiaSummary(projectId: string): Promise<BiaSummary> {
  return api<BiaSummary>(`${BASE}/${projectId}/bia/summary`);
}
