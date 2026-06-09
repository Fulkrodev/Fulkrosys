/**
 * Admin Workflow API client wrapper (sub-bloque 8.B.2 FASE 8 · ADR-026).
 *
 * Reusa frontend/lib/api.ts (admin context — CSRF + cookies admin).
 *
 * Endpoints backend (api/v1/workflow.py registrados main.py):
 *   GET /api/v1/workflow/current-phase/{project_id}
 *   GET /api/v1/workflow/next-actions/{project_id}?limit=5
 *   GET /api/v1/workflow/phase-progress/{project_id}/{phase}
 *   GET /api/v1/workflow/phase-tasks/{project_id}/{phase}
 *   GET /api/v1/workflow/roadmap/{project_id}
 *
 * RBAC backend: require_owner (Marcos admin only).
 */
"use client";

import { api } from "@/lib/api";
import type {
  NextAction,
  PhaseProgress,
  TaskItem,
  WorkflowPhase,
  WorkflowRoadmap,
} from "./schemas";

const BASE = "/api/v1/workflow";

export async function getCurrentPhase(projectId: string): Promise<WorkflowPhase> {
  return api<WorkflowPhase>(`${BASE}/current-phase/${projectId}`);
}

export async function getNextActions(
  projectId: string,
  limit = 5,
): Promise<NextAction[]> {
  return api<NextAction[]>(`${BASE}/next-actions/${projectId}?limit=${limit}`);
}

export async function getPhaseProgress(
  projectId: string,
  phase: WorkflowPhase,
): Promise<PhaseProgress> {
  return api<PhaseProgress>(`${BASE}/phase-progress/${projectId}/${phase}`);
}

export async function getPhaseTasks(
  projectId: string,
  phase: WorkflowPhase,
): Promise<TaskItem[]> {
  return api<TaskItem[]>(`${BASE}/phase-tasks/${projectId}/${phase}`);
}

export async function getRoadmap(projectId: string): Promise<WorkflowRoadmap> {
  return api<WorkflowRoadmap>(`${BASE}/roadmap/${projectId}`);
}
