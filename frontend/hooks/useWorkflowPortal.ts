/**
 * Hooks workflow portal cliente (sub-bloque 8.B.4 FASE 8 · ADR-026).
 *
 * Wrapper React Query sobre frontend/lib/portal-workflow/api.ts.
 * Subset hooks: cliente NO accede a /phase-progress detalle ni /phase-tasks
 * templates internos · solo current-phase + next-actions + roadmap.
 */
"use client";

import { useQuery } from "@tanstack/react-query";

import {
  getCurrentPhasePortal,
  getNextActionsPortal,
  getRoadmapPortal,
} from "@/lib/portal-workflow/api";

const STALE_TIME = 30 * 1000;

export function useCurrentPhasePortal(projectId: string | null | undefined) {
  return useQuery({
    queryKey: ["portal-workflow", "current-phase", projectId],
    queryFn: () => getCurrentPhasePortal(projectId as string),
    enabled: Boolean(projectId),
    staleTime: STALE_TIME,
  });
}

export function useNextActionsPortal(
  projectId: string | null | undefined,
  limit = 5,
) {
  return useQuery({
    queryKey: ["portal-workflow", "next-actions", projectId, limit],
    queryFn: () => getNextActionsPortal(projectId as string, limit),
    enabled: Boolean(projectId),
    staleTime: STALE_TIME,
  });
}

export function useRoadmapPortal(projectId: string | null | undefined) {
  return useQuery({
    queryKey: ["portal-workflow", "roadmap", projectId],
    queryFn: () => getRoadmapPortal(projectId as string),
    enabled: Boolean(projectId),
    staleTime: STALE_TIME,
  });
}
