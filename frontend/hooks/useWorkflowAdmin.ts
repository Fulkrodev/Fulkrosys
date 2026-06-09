/**
 * Hooks workflow admin (sub-bloque 8.B.4 FASE 8 · ADR-026).
 *
 * Wrapper React Query sobre frontend/lib/admin-workflow/api.ts.
 * Cache 30s revalidation, suspense compatible.
 */
"use client";

import { useQuery } from "@tanstack/react-query";

import {
  getCurrentPhase,
  getNextActions,
  getPhaseProgress,
  getPhaseTasks,
  getRoadmap,
} from "@/lib/admin-workflow/api";
import type { WorkflowPhase } from "@/lib/admin-workflow/schemas";

const STALE_TIME = 30 * 1000;

export function useCurrentPhase(projectId: string | null | undefined) {
  return useQuery({
    queryKey: ["admin-workflow", "current-phase", projectId],
    queryFn: () => getCurrentPhase(projectId as string),
    enabled: Boolean(projectId),
    staleTime: STALE_TIME,
  });
}

export function useNextActions(
  projectId: string | null | undefined,
  limit = 5,
) {
  return useQuery({
    queryKey: ["admin-workflow", "next-actions", projectId, limit],
    queryFn: () => getNextActions(projectId as string, limit),
    enabled: Boolean(projectId),
    staleTime: STALE_TIME,
  });
}

export function usePhaseProgress(
  projectId: string | null | undefined,
  phase: WorkflowPhase | null | undefined,
) {
  return useQuery({
    queryKey: ["admin-workflow", "phase-progress", projectId, phase],
    queryFn: () => getPhaseProgress(projectId as string, phase as WorkflowPhase),
    enabled: Boolean(projectId) && Boolean(phase),
    staleTime: STALE_TIME,
  });
}

export function usePhaseTasks(
  projectId: string | null | undefined,
  phase: WorkflowPhase | null | undefined,
) {
  return useQuery({
    queryKey: ["admin-workflow", "phase-tasks", projectId, phase],
    queryFn: () => getPhaseTasks(projectId as string, phase as WorkflowPhase),
    enabled: Boolean(projectId) && Boolean(phase),
    staleTime: STALE_TIME,
  });
}

export function useRoadmap(projectId: string | null | undefined) {
  return useQuery({
    queryKey: ["admin-workflow", "roadmap", projectId],
    queryFn: () => getRoadmap(projectId as string),
    enabled: Boolean(projectId),
    staleTime: STALE_TIME,
  });
}
