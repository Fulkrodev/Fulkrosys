"use client";

/**
 * Hook cliente · Compliance Summary aggregator (Bloque 4 Phase A).
 *
 * Encapsula TanStack Query del endpoint aggregator NEW:
 *   GET /api/v1/client-portal/compliance-summary
 *
 * Refetch automático cada 60s · staleTime 30s · compatible con SSE invalidation
 * cuando eventos compliance llegan.
 */
import { useQuery } from "@tanstack/react-query";

import {
  clientComplianceSummaryApi,
  type ComplianceSummaryResponse,
} from "@/lib/api/client-compliance-summary";

export const COMPLIANCE_SUMMARY_QUERY_KEY = [
  "client-portal",
  "compliance-summary",
] as const;

export function useClientComplianceSummary(enabled: boolean = true) {
  return useQuery<ComplianceSummaryResponse>({
    queryKey: COMPLIANCE_SUMMARY_QUERY_KEY,
    queryFn: () => clientComplianceSummaryApi.get(),
    enabled,
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}
