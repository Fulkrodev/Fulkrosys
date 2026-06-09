"use client";

/**
 * Hooks admin · Cloud Remediations orchestrator (Bloque 3+5).
 *
 * Encapsula:
 *   - useAuditLog(projectId, gapId) · TanStack Query audit log per gap
 *   - useProposeToCliente() · mutation propose
 *   - useStartExecution() · mutation execute
 *   - useMarkExecuted() · mutation mark-executed
 *   - useMarkFailed() · mutation mark-failed
 *
 * Cada mutation invalida queryKey audit-log + cloud-connectors gaps list
 * para refresh UI inmediato.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  adminCloudRemediationsApi,
  type AdminAuditLogResponse,
  type AdminRemediationGap,
} from "@/lib/api/cloud-remediations-admin";

export const ADMIN_AUDIT_LOG_KEY = (
  projectId: string,
  gapId: string,
) => ["admin", "cloud-remediation", "audit-log", projectId, gapId] as const;

export const ADMIN_CLOUD_GAPS_KEY = (projectId: string) =>
  ["admin", "cloud-connectors", projectId, "gaps"] as const;

export function useAdminAuditLog(
  projectId: string,
  gapId: string | null,
  enabled: boolean = true,
) {
  return useQuery<AdminAuditLogResponse>({
    queryKey: ADMIN_AUDIT_LOG_KEY(projectId, gapId ?? ""),
    queryFn: () => adminCloudRemediationsApi.auditLog(projectId, gapId!),
    enabled: enabled && Boolean(gapId),
    staleTime: 15_000,
  });
}

function _invalidate(
  queryClient: ReturnType<typeof useQueryClient>,
  projectId: string,
  gapId: string,
) {
  queryClient.invalidateQueries({
    queryKey: ADMIN_AUDIT_LOG_KEY(projectId, gapId),
  });
  queryClient.invalidateQueries({
    queryKey: ADMIN_CLOUD_GAPS_KEY(projectId),
  });
}

export function useProposeToCliente(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation<
    AdminRemediationGap,
    Error,
    { gapId: string; notes?: string }
  >({
    mutationFn: ({ gapId, notes }) =>
      adminCloudRemediationsApi.proposeToCliente(projectId, gapId, notes),
    onSuccess: (_, { gapId }) => _invalidate(queryClient, projectId, gapId),
  });
}

export function useStartExecution(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation<
    AdminRemediationGap,
    Error,
    { gapId: string; notes?: string }
  >({
    mutationFn: ({ gapId, notes }) =>
      adminCloudRemediationsApi.execute(projectId, gapId, notes),
    onSuccess: (_, { gapId }) => _invalidate(queryClient, projectId, gapId),
  });
}

export function useMarkExecuted(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation<
    AdminRemediationGap,
    Error,
    { gapId: string; evidence_link_id?: string; notes?: string }
  >({
    mutationFn: ({ gapId, evidence_link_id, notes }) =>
      adminCloudRemediationsApi.markExecuted(projectId, gapId, {
        evidence_link_id,
        notes,
      }),
    onSuccess: (_, { gapId }) => _invalidate(queryClient, projectId, gapId),
  });
}

export function useMarkFailed(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation<
    AdminRemediationGap,
    Error,
    {
      gapId: string;
      error_notes: string;
      error_metadata?: Record<string, unknown>;
    }
  >({
    mutationFn: ({ gapId, error_notes, error_metadata }) =>
      adminCloudRemediationsApi.markFailed(projectId, gapId, {
        error_notes,
        error_metadata,
      }),
    onSuccess: (_, { gapId }) => _invalidate(queryClient, projectId, gapId),
  });
}
