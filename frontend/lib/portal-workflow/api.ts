/**
 * Portal Workflow API client wrapper (sub-bloque 8.B.2 FASE 8 · ADR-026).
 *
 * Reusa frontend/lib/client-portal-api.ts (cliente context — cookies cliente
 * + CSRF triple binding ADR-019).
 *
 * Endpoints backend (api/v1/portal_workflow.py registrados main.py):
 *   GET /api/v1/portal/workflow/current-phase/{project_id}
 *   GET /api/v1/portal/workflow/next-actions/{project_id}?limit=5
 *   GET /api/v1/portal/workflow/roadmap/{project_id}
 *
 * RBAC backend: require_client_user + verify_client_owns_project
 * (cross-tenant guard).
 */
"use client";

import { clientApi } from "@/lib/client-portal-api";
import type {
  NextAction,
  WorkflowPhase,
  WorkflowRoadmap,
} from "./schemas";

const BASE = "/api/v1/portal/workflow";

export async function getCurrentPhasePortal(
  projectId: string,
): Promise<WorkflowPhase> {
  return clientApi<WorkflowPhase>(`${BASE}/current-phase/${projectId}`);
}

export async function getNextActionsPortal(
  projectId: string,
  limit = 5,
): Promise<NextAction[]> {
  return clientApi<NextAction[]>(
    `${BASE}/next-actions/${projectId}?limit=${limit}`,
  );
}

export async function getRoadmapPortal(
  projectId: string,
): Promise<WorkflowRoadmap> {
  return clientApi<WorkflowRoadmap>(`${BASE}/roadmap/${projectId}`);
}
