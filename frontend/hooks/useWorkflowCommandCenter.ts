"use client";

/**
 * Hooks Workflow Command Center · sub-atom 1.C.D.B v3.8.
 *
 * Wrappers tanstack-query sobre lib/api/workflow-command-center.ts
 * Patterns sostenidos: STALE_TIME 30s · refetchInterval 30_000ms polling auto-refresh.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  advanceStep,
  getCatalog,
  getCommandCenterMultiClient,
  getCurrentStep,
  getProgress,
  getProjectCronologica,
  getTimeline,
} from "@/lib/api/workflow-command-center";

const STALE_TIME = 30 * 1000;
const REFETCH_INTERVAL = 30 * 1000;

// ============================================================
// Dashboard multi-cliente
// ============================================================

export function useCommandCenterMultiClient() {
  return useQuery({
    queryKey: ["workflow-command-center", "multi-client"],
    queryFn: () => getCommandCenterMultiClient(),
    staleTime: STALE_TIME,
    refetchInterval: REFETCH_INTERVAL,
  });
}

// ============================================================
// Per-cliente cronológica
// ============================================================

export function useProjectCronologica(projectId: string | null | undefined) {
  return useQuery({
    queryKey: ["workflow-command-center", "project-cronologica", projectId],
    queryFn: () => getProjectCronologica(projectId as string),
    enabled: Boolean(projectId),
    staleTime: STALE_TIME,
  });
}

// ============================================================
// Reader endpoints (admin + cliente)
// ============================================================

export function useCatalog(
  projectId: string | null | undefined,
  phase?: string,
) {
  return useQuery({
    queryKey: ["workflow-engine", "catalog", projectId, phase],
    queryFn: () => getCatalog(projectId as string, phase),
    enabled: Boolean(projectId),
    staleTime: STALE_TIME,
  });
}

export function useCurrentStep(projectId: string | null | undefined) {
  return useQuery({
    queryKey: ["workflow-engine", "current-step", projectId],
    queryFn: () => getCurrentStep(projectId as string),
    enabled: Boolean(projectId),
    staleTime: STALE_TIME,
  });
}

export function useProgress(projectId: string | null | undefined) {
  return useQuery({
    queryKey: ["workflow-engine", "progress", projectId],
    queryFn: () => getProgress(projectId as string),
    enabled: Boolean(projectId),
    staleTime: STALE_TIME,
  });
}

export function useTimeline(projectId: string | null | undefined) {
  return useQuery({
    queryKey: ["workflow-engine", "timeline", projectId],
    queryFn: () => getTimeline(projectId as string),
    enabled: Boolean(projectId),
    staleTime: STALE_TIME,
  });
}

// ============================================================
// Mutations
// ============================================================

export function useAdvanceStep() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      projectId,
      templateId,
    }: {
      projectId: string;
      templateId: string;
    }) => advanceStep(projectId, templateId),
    onSuccess: (_data, vars) => {
      // Invalidate relevant queries
      queryClient.invalidateQueries({
        queryKey: ["workflow-command-center", "project-cronologica", vars.projectId],
      });
      queryClient.invalidateQueries({
        queryKey: ["workflow-engine", "catalog", vars.projectId],
      });
      queryClient.invalidateQueries({
        queryKey: ["workflow-engine", "current-step", vars.projectId],
      });
      queryClient.invalidateQueries({
        queryKey: ["workflow-engine", "progress", vars.projectId],
      });
      queryClient.invalidateQueries({
        queryKey: ["workflow-engine", "timeline", vars.projectId],
      });
      queryClient.invalidateQueries({
        queryKey: ["workflow-command-center", "multi-client"],
      });
    },
  });
}
