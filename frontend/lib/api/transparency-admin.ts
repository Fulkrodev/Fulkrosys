"use client";

/**
 * Admin API AI Act art.50 transparency · sub-atom 1.E.1.B.2.
 *
 * Endpoint backend (m_observability/transparency_api.admin_router):
 *   GET /api/v1/admin/projects/{project_id}/transparency/log?days=180&limit=200
 *
 * Admin full view · includes llm_provider/llm_model/metadata para auditor
 * ENAC forensic review.
 */

import { api } from "@/lib/api";

import type { AIActEventType } from "./transparency-client";

export interface AdminTransparencyEvent {
  id: string;
  project_id: string;
  client_id: string | null;
  event_type: AIActEventType;
  llm_provider: string;
  llm_model: string;
  agent_name: string;
  artifact_type: string | null;
  artifact_id: string | null;
  purpose: string;
  metadata: Record<string, unknown> | null;
  retention_until: string;
  created_at: string;
}

export interface AdminTransparencyLogResponse {
  project_id: string;
  days: number;
  total: number;
  items: AdminTransparencyEvent[];
}

export async function getAdminProjectTransparencyLog(
  projectId: string,
  days: number = 180,
  limit: number = 200,
): Promise<AdminTransparencyLogResponse> {
  return api<AdminTransparencyLogResponse>(
    `/api/v1/admin/projects/${projectId}/transparency/log?days=${days}&limit=${limit}`,
  );
}
