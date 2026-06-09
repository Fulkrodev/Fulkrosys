"use client";

/**
 * Hook admin · Cross-Project Compliance aggregator (Bloque 4 Phase B).
 *
 * TanStack Query · refetchInterval 60s + staleTime 30s.
 */
import { useQuery } from "@tanstack/react-query";

import {
  adminCrossProjectComplianceApi,
  type CrossProjectComplianceResponse,
} from "@/lib/api/admin-cross-project-compliance";

export const ADMIN_CROSS_PROJECT_COMPLIANCE_KEY = [
  "admin",
  "cross-project-compliance",
] as const;

export function useAdminCrossProjectCompliance(
  options: { onlyActive?: boolean; enabled?: boolean } = {},
) {
  const { onlyActive = true, enabled = true } = options;
  return useQuery<CrossProjectComplianceResponse>({
    queryKey: [...ADMIN_CROSS_PROJECT_COMPLIANCE_KEY, onlyActive],
    queryFn: () =>
      adminCrossProjectComplianceApi.list({ only_active: onlyActive }),
    enabled,
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}
