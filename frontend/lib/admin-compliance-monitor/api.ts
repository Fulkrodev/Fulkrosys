/**
 * API client for /admin/compliance/monitor (FULKRO Self-Monitoring).
 *
 * Mirrors `backend/app/motors/m_compliance_monitor/api.py`. All endpoints
 * require Marcos (admin) authentication — handled by global cookie auth.
 */
import { api } from "@/lib/api";
import type {
  ComplianceAlert,
  ComplianceCheck,
  ComplianceReport,
  MonitorStatus,
  TriggerCheckResult,
} from "./schemas";

const BASE = "/api/v1/admin/compliance/monitor";

export async function getMonitorStatus(): Promise<MonitorStatus> {
  return api<MonitorStatus>(`${BASE}/status`);
}

export async function listChecks(params?: {
  category?: string;
  status?: string;
}): Promise<ComplianceCheck[]> {
  const qs = new URLSearchParams();
  if (params?.category) qs.set("category", params.category);
  if (params?.status) qs.set("status", params.status);
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return api<ComplianceCheck[]>(`${BASE}/checks${suffix}`);
}

export async function runCheck(name: string): Promise<TriggerCheckResult> {
  return api<TriggerCheckResult>(`${BASE}/checks/${name}/run`, {
    method: "POST",
  });
}

export async function listAlerts(params?: {
  status?: string;
  limit?: number;
}): Promise<ComplianceAlert[]> {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  if (params?.limit) qs.set("limit", String(params.limit));
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return api<ComplianceAlert[]>(`${BASE}/alerts${suffix}`);
}

export async function resolveAlert(
  alertId: string,
  resolutionNote: string,
): Promise<ComplianceAlert> {
  return api<ComplianceAlert>(`${BASE}/alerts/${alertId}/resolve`, {
    method: "POST",
    json: { resolution_note: resolutionNote },
  });
}

export async function listReports(limit = 20): Promise<ComplianceReport[]> {
  return api<ComplianceReport[]>(`${BASE}/reports?limit=${limit}`);
}

export async function syncRegistry(): Promise<{
  created: number;
  total_registered: number;
}> {
  return api(`${BASE}/sync-registry`, { method: "POST" });
}
