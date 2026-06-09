/**
 * Admin Awareness API client (SAN-C MB-11.5).
 *
 * Endpoints backend (api/v1 m24_idms.awareness_api):
 *   POST /api/v1/projects/{id}/awareness/sessions
 *   GET  /api/v1/projects/{id}/awareness/sessions
 *   POST /api/v1/awareness/sessions/{sid}/attendance
 *   GET  /api/v1/projects/{id}/awareness/coverage
 */
"use client";

import { api } from "@/lib/api";

export interface AwarenessSession {
  id: string;
  title: string;
  scheduled_date: string;
  topics?: string[];
  mandatory: boolean;
  completed_at?: string;
}

export interface SessionCreate {
  title: string;
  scheduled_date: string;
  topics?: string[];
  mandatory?: boolean;
}

export interface AttendanceCreate {
  attendee_email: string;
  method: "in_person" | "virtual" | "recorded";
  magic_link_token?: string;
}

export interface AttendanceResponse {
  id: string;
  session_id: string;
  attendee_email: string;
  method: string;
  attended_at: string;
}

export interface CoverageResponse {
  unique_attendees: number;
  expected_attendees: number;
  coverage_pct: number;
  window_start: string;
}

const BASE = "/api/v1";

export async function scheduleSession(
  projectId: string,
  body: SessionCreate,
): Promise<AwarenessSession> {
  return api<AwarenessSession>(
    `${BASE}/projects/${projectId}/awareness/sessions`,
    { method: "POST", body: JSON.stringify(body) },
  );
}

export async function listAwarenessSessions(
  projectId: string,
): Promise<AwarenessSession[]> {
  return api<AwarenessSession[]>(
    `${BASE}/projects/${projectId}/awareness/sessions`,
  );
}

export async function recordAttendance(
  sessionId: string,
  body: AttendanceCreate,
): Promise<AttendanceResponse> {
  return api<AttendanceResponse>(
    `${BASE}/awareness/sessions/${sessionId}/attendance`,
    { method: "POST", body: JSON.stringify(body) },
  );
}

export async function getCoverage(
  projectId: string,
  expected: number,
  windowDays = 365,
): Promise<CoverageResponse> {
  return api<CoverageResponse>(
    `${BASE}/projects/${projectId}/awareness/coverage?expected=${expected}&window_days=${windowDays}`,
  );
}
