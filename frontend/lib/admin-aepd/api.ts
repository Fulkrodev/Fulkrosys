/**
 * Admin AEPD API client (SAN-C MB-11.2).
 *
 * Endpoints backend (api/v1 m18_communication.aepd_api):
 *   POST /api/v1/projects/{id}/aepd/evaluate
 *   GET  /api/v1/projects/{id}/aepd/notifications
 */
"use client";

import { api } from "@/lib/api";

export interface AepdEvaluateRequest {
  affects_personal_data: boolean;
  risk_to_rights: "low" | "medium" | "high";
  severity?: "low" | "medium" | "high" | "critical";
  incident_id?: string;
  detected_at?: string;
  description?: string;
  data_categories?: string[];
  consequences?: string;
  measures_taken?: string;
}

export interface AepdEvaluateResponse {
  requires_notification: boolean;
  notify_subjects: boolean;
  deadline_hours: number | null;
  register_only: boolean;
  decision_path: string[];
  notification_id: string | null;
  prefilled_payload: Record<string, unknown> | null;
  submission_url: string | null;
}

export interface AepdNotification {
  id: string;
  project_id: string;
  incident_id: string | null;
  severity: string;
  requires_notification: boolean;
  notify_subjects: boolean;
  deadline_hours: number | null;
  decision_tree_path: string[] | null;
  notification_status: string;
  detected_at: string | null;
  created_at: string;
  deadline_hours_remaining: number | null;
}

const BASE = "/api/v1/projects";

export async function evaluateAepd(
  projectId: string,
  body: AepdEvaluateRequest,
): Promise<AepdEvaluateResponse> {
  return api<AepdEvaluateResponse>(`${BASE}/${projectId}/aepd/evaluate`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function listAepdNotifications(
  projectId: string,
): Promise<AepdNotification[]> {
  return api<AepdNotification[]>(`${BASE}/${projectId}/aepd/notifications`);
}
