/**
 * API client alertas proactivas (MB-13.4 · ADR-035).
 *
 * Endpoints:
 *   GET  /api/v1/alerts/active                   global admin
 *   GET  /api/v1/projects/{project_id}/alerts    per proyecto
 *   POST /api/v1/alerts/{alert_id}/acknowledge   marcar leida
 */
import { api } from "@/lib/api";
import type { AlertResponse } from "./schemas";

export async function listActiveAlertsGlobal(): Promise<AlertResponse[]> {
  return api<AlertResponse[]>("/api/v1/alerts/active");
}

export async function listProjectAlerts(
  projectId: string,
): Promise<AlertResponse[]> {
  return api<AlertResponse[]>(`/api/v1/projects/${projectId}/alerts`);
}

export async function acknowledgeAlert(
  alertId: string,
): Promise<{ acknowledged: boolean }> {
  return api(`/api/v1/alerts/${alertId}/acknowledge`, { method: "POST" });
}
