"use client";

/**
 * Hook cliente · Cloud Remediations approval (Bloque 3+5).
 *
 * Encapsula:
 *   - useClientRemediations() · TanStack Query list pending propuestas
 *   - useApproveRemediation() · mutation approve + invalidate refetch
 *   - useRejectRemediation() · mutation reject + invalidate refetch
 *
 * Integration con useClientProjectEvents SSE para auto-refresh on event_type
 * cloud_remediation_* (caller wires via invalidateQueries option).
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  clientCloudRemediationsApi,
  type RemediationListResponse,
  type RemediationActionResponse,
} from "@/lib/api/client-cloud-remediations";

export const REMEDIATIONS_QUERY_KEY = [
  "client-portal",
  "cloud-remediations",
] as const;

export function useClientRemediations(enabled: boolean = true) {
  return useQuery<RemediationListResponse>({
    queryKey: REMEDIATIONS_QUERY_KEY,
    queryFn: () => clientCloudRemediationsApi.list(),
    enabled,
    staleTime: 30_000,
  });
}

export function useApproveRemediation() {
  const queryClient = useQueryClient();
  return useMutation<
    RemediationActionResponse,
    Error,
    { gapId: string; notes?: string }
  >({
    mutationFn: ({ gapId, notes }) =>
      clientCloudRemediationsApi.approve(gapId, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: REMEDIATIONS_QUERY_KEY });
    },
  });
}

export function useRejectRemediation() {
  const queryClient = useQueryClient();
  return useMutation<
    RemediationActionResponse,
    Error,
    { gapId: string; notes?: string }
  >({
    mutationFn: ({ gapId, notes }) =>
      clientCloudRemediationsApi.reject(gapId, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: REMEDIATIONS_QUERY_KEY });
    },
  });
}
