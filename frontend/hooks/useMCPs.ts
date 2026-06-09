"use client";

import { useQuery } from "@tanstack/react-query";

import {
  getMCPsStatus,
  mcpsApi,
  type MCPCatalog,
  type MCPExecution,
  type MCPExecutionsHistory,
} from "@/lib/api/mcps";

export const mcpsKeys = {
  all: ["mcps"] as const,
  status: () => [...mcpsKeys.all, "status"] as const,
  catalog: () => [...mcpsKeys.all, "catalog"] as const,
  executions: (projectId: string) =>
    [...mcpsKeys.all, "executions", projectId] as const,
  execution: (projectId: string, executionId: string) =>
    [...mcpsKeys.all, "execution", projectId, executionId] as const,
};

/** GET /api/v1/mcps/status — read-only registry, refresh cada 60s. */
export function useMCPsStatus() {
  return useQuery({
    queryKey: mcpsKeys.status(),
    queryFn: getMCPsStatus,
    staleTime: 60_000,
  });
}

/**
 * Sub-atom 1.D.E.B v3.11 · catalog 13 tools project-scoped (admin).
 *
 * Cache 1h · catálogo estático (no cambia entre requests).
 */
export function useMCPsCatalog() {
  return useQuery<MCPCatalog>({
    queryKey: mcpsKeys.catalog(),
    queryFn: mcpsApi.getCatalog,
    staleTime: 60 * 60 * 1000,
  });
}

/**
 * Sub-atom 1.D.E.B v3.11 · history de ejecuciones MCP per project.
 *
 * Refresh 30s para ver running → completed transiciones.
 */
export function useMCPsExecutions(projectId: string, enabled = true) {
  return useQuery<MCPExecutionsHistory>({
    queryKey: mcpsKeys.executions(projectId),
    queryFn: () => mcpsApi.listExecutions(projectId),
    enabled: enabled && Boolean(projectId),
    staleTime: 30_000,
    refetchInterval: 30_000,
  });
}

/**
 * Sub-atom 1.D.E.B v3.11 · estado de una execution individual.
 *
 * Polling 2s mientras running · stop al completar.
 */
export function useMCPExecution(
  projectId: string,
  executionId: string | null,
) {
  return useQuery<MCPExecution>({
    queryKey: mcpsKeys.execution(projectId, executionId ?? ""),
    queryFn: () => mcpsApi.getExecution(projectId, executionId as string),
    enabled: Boolean(projectId && executionId),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 2000;
      if (data.status === "completed" || data.status === "failed") {
        return false;
      }
      return 2000;
    },
  });
}
