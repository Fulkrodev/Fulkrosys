/**
 * API client dashboard agregado admin (MB-13.1 · ADR-035).
 *
 * Reusa frontend/lib/api.ts (CSRF + cookies + ApiError).
 *
 * Endpoint:
 *   GET /api/v1/projects/{project_id}/dashboard
 */
import { api } from "@/lib/api";
import type { DashboardData } from "./schemas";

export async function getProjectDashboard(
  projectId: string,
): Promise<DashboardData> {
  return api<DashboardData>(`/api/v1/projects/${projectId}/dashboard`);
}
