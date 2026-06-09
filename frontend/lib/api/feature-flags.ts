/**
 * Feature Flags API client (ADR-036 SAN-D MB-17.1 + ADR-046 MB-10 Atom 10.2/10.3).
 *
 * 5 endpoints backend:
 *   GET    /api/v1/feature-flags/catalog                    · catalog estático
 *   GET    /api/v1/projects/{id}/feature-flags              · evaluadas + overrides merged
 *   POST   /api/v1/admin/feature-flags/override             · grant override (admin-only)
 *   DELETE /api/v1/admin/feature-flags/override/{id}        · revoke override (admin-only)
 *   GET    /api/v1/admin/feature-flags/overrides            · list per project/client
 *
 * Usa `api()` wrapper con CSRF + credentials.
 *
 * Q5.3 cement sostained: admin endpoints SOLO consumidos desde
 * `components/admin/feature-flags/*`. NUNCA cliente-facing.
 */
import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type {
  FeatureFlagOverride,
  GrantOverrideRequest,
  ProjectFeatureFlags,
  RevokeOverrideRequest,
} from "@/lib/feature-flags.types";

export const featureFlagsApi = {
  getProjectFeatureFlags: (projectId: string): Promise<ProjectFeatureFlags> =>
    api<ProjectFeatureFlags>(`/api/v1/projects/${projectId}/feature-flags`),

  getCatalog: () => api<unknown>("/api/v1/feature-flags/catalog"),

  // ADR-046 · admin override management (renamed post-audit B1.2 · was ADR-037 MB-10)
  grantOverride: (body: GrantOverrideRequest): Promise<FeatureFlagOverride> =>
    api<FeatureFlagOverride>("/api/v1/admin/feature-flags/override", {
      json: body,
    }),

  revokeOverride: (
    overrideId: string,
    body?: RevokeOverrideRequest,
  ): Promise<FeatureFlagOverride> =>
    api<FeatureFlagOverride>(
      `/api/v1/admin/feature-flags/override/${overrideId}`,
      {
        method: "DELETE",
        json: body ?? {},
      },
    ),

  listOverrides: (params: {
    projectId?: string;
    clientId?: string;
    includeRevoked?: boolean;
  }): Promise<FeatureFlagOverride[]> => {
    const qs = new URLSearchParams();
    if (params.projectId) qs.set("project_id", params.projectId);
    if (params.clientId) qs.set("client_id", params.clientId);
    if (params.includeRevoked) qs.set("include_revoked", "true");
    return api<FeatureFlagOverride[]>(
      `/api/v1/admin/feature-flags/overrides?${qs.toString()}`,
    );
  },
};

/**
 * Hook lectura overrides activos per project · admin-only consumer.
 *
 * `staleTime` 30s alineado con cadencia mutation grant/revoke admin
 * (raro · no daily). Invalidate queryKey `["feature-flag-overrides", projectId]`
 * post mutations para refresh inmediato.
 */
export function useFeatureFlagOverrides(
  projectId: string,
  options?: { includeRevoked?: boolean },
) {
  return useQuery({
    queryKey: [
      "feature-flag-overrides",
      projectId,
      options?.includeRevoked ?? false,
    ],
    queryFn: () =>
      featureFlagsApi.listOverrides({
        projectId,
        includeRevoked: options?.includeRevoked,
      }),
    staleTime: 30_000,
    enabled: Boolean(projectId),
  });
}
