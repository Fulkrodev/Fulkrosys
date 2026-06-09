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

const BASE = "/api/v1/projects";

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
