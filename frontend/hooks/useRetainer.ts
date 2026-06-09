"use client";

/**
 * React Query hooks para Motor 23 — Retainer Management.
 *
 * 0 mocks. Todos los hooks invocan endpoints reales del backend
 * (22 en /retainer + 9 en /retainer/paso2 = 31 totales).
 *
 * Reemplaza `useRetainerOverview` y `useRetainerProject` que vivían
 * en `useSprint5Data.ts` (eliminados en 9.A.2).
 */
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  cancelProjectRetainer,
  completeActivity,
  createRetainer,
  generateActivities,
  generateMonthlyInvoice,
  getAgent26Alerts,
  getAgent26Summary,
  getDriftCatalog,
  getHealthDetail,
  getPaso2Dashboard,
  getPricingCatalog,
  getProfileCadences,
  getProjectRetainer,
  getRenewalStatus,
  getRetainerDashboard,
  getRetainerTimeline,
  listActivities,
  listDrifts,
  listOverdueActivities,
  listProfiles,
  listRetainers,
  pauseProjectRetainer,
  recalculateRag,
  registerDrift,
  renewProjectRetainer,
  resolveDrift,
  startActivity,
  suggestTier,
  triggerMaterialChange,
  updateProjectRetainer,
  upgradeTier,
  type CompleteActivityBody,
  type CreateRetainerBody,
  type GenerateActivitiesBody,
  type ListActivitiesFilters,
  type ListDriftsFilters,
  type ListRetainersFilters,
  type MaterialChangeBody,
  type RegisterDriftBody,
  type RenewBody,
  type RetainerTier,
  type SuggestTierBody,
  type UpdateRetainerBody,
} from "@/lib/api/retainer";

// ═══════════════════════════════════════════════════════════════════
// Keys centralizadas
// ═══════════════════════════════════════════════════════════════════

export const retainerKeys = {
  all: () => ["retainer"] as const,
  // Project-scoped
  project: (projectId: string) =>
    ["retainer", "project", projectId] as const,
  projectActivities: (
    projectId: string,
    filters?: ListActivitiesFilters,
  ) =>
    [
      "retainer",
      "project",
      projectId,
      "activities",
      filters ?? {},
    ] as const,
  projectOverdue: (projectId: string) =>
    ["retainer", "project", projectId, "activities", "overdue"] as const,
  projectRenewal: (projectId: string) =>
    ["retainer", "project", projectId, "renewal-status"] as const,
  projectDrifts: (projectId: string, filters?: ListDriftsFilters) =>
    [
      "retainer",
      "project",
      projectId,
      "drifts",
      filters ?? {},
    ] as const,
  // Catalogs
  profiles: () => ["retainer", "profiles"] as const,
  profileCadences: (profile: string) =>
    ["retainer", "profiles", profile, "cadences"] as const,
  driftCatalog: () => ["retainer", "drift-catalog"] as const,
  // Global
  dashboard: () => ["retainer", "dashboard"] as const,
  list: (filters?: ListRetainersFilters) =>
    ["retainer", "list", filters ?? {}] as const,
  // Paso 2
  paso2Dashboard: () => ["retainer", "paso2", "dashboard"] as const,
  paso2Timeline: (retainerId: string) =>
    ["retainer", "paso2", "timeline", retainerId] as const,
  paso2HealthDetail: (retainerId: string) =>
    ["retainer", "paso2", "health-detail", retainerId] as const,
  paso2PricingCatalog: (category?: string) =>
    ["retainer", "paso2", "pricing-catalog", category ?? "all"] as const,
  paso2Agent26Summary: () =>
    ["retainer", "paso2", "agent-26", "summary"] as const,
  paso2Agent26Alerts: () =>
    ["retainer", "paso2", "agent-26", "alerts"] as const,
};

// ═══════════════════════════════════════════════════════════════════
// Queries — catálogos
// ═══════════════════════════════════════════════════════════════════

export function useProfiles() {
  return useQuery({
    queryKey: retainerKeys.profiles(),
    queryFn: () => listProfiles(),
  });
}

export function useProfileCadences(profile: string | null) {
  return useQuery({
    queryKey: retainerKeys.profileCadences(profile ?? ""),
    queryFn: () => getProfileCadences(profile!),
    enabled: !!profile,
  });
}

export function useDriftCatalog() {
  return useQuery({
    queryKey: retainerKeys.driftCatalog(),
    queryFn: () => getDriftCatalog(),
  });
}

// ═══════════════════════════════════════════════════════════════════
// Queries — global
// ═══════════════════════════════════════════════════════════════════

export function useRetainerDashboard() {
  return useQuery({
    queryKey: retainerKeys.dashboard(),
    queryFn: () => getRetainerDashboard(),
  });
}

export function useRetainerList(filters: ListRetainersFilters = {}) {
  return useQuery({
    queryKey: retainerKeys.list(filters),
    queryFn: () => listRetainers(filters),
  });
}

/**
 * Vista global Retainer Ops.
 *
 * Reemplaza `useRetainerOverview` (mock) usando el dashboard real
 * de paso 2, que devuelve `retainers[]` + agregados (`mrr_total`,
 * `agent_26_summary`).
 */
export function useRetainerOverview() {
  return useQuery({
    queryKey: retainerKeys.paso2Dashboard(),
    queryFn: () => getPaso2Dashboard(),
  });
}

// ═══════════════════════════════════════════════════════════════════
// Queries — project-scoped
// ═══════════════════════════════════════════════════════════════════

/**
 * Devuelve el retainer de un proyecto. Distingue 404 (sin retainer)
 * de errores reales: 404 -> data === null (notFound), no isError.
 *
 * Esto permite a los componentes consumidores renderizar un empty
 * state limpio en lugar de un Alert de error cuando el proyecto
 * todavía no tiene retainer activo.
 */
export function useRetainerProject(projectId: string) {
  return useQuery({
    queryKey: retainerKeys.project(projectId),
    queryFn: async () => {
      try {
        return await getProjectRetainer(projectId);
      } catch (err: unknown) {
        const status =
          (err as { status?: number; statusCode?: number })?.status ??
          (err as { status?: number; statusCode?: number })?.statusCode;
        if (status === 404) return null;
        throw err;
      }
    },
    enabled: !!projectId,
    retry: (failureCount, err: unknown) => {
      const status =
        (err as { status?: number; statusCode?: number })?.status ??
        (err as { status?: number; statusCode?: number })?.statusCode;
      if (status === 404) return false;
      return failureCount < 3;
    },
  });
}

export function useRetainerActivities(
  projectId: string,
  filters: ListActivitiesFilters = {},
  options: { enabled?: boolean } = {},
) {
  return useQuery({
    queryKey: retainerKeys.projectActivities(projectId, filters),
    queryFn: () => listActivities(projectId, filters),
    enabled: !!projectId && (options.enabled ?? true),
  });
}

export function useOverdueActivities(
  projectId: string,
  options: { enabled?: boolean } = {},
) {
  return useQuery({
    queryKey: retainerKeys.projectOverdue(projectId),
    queryFn: () => listOverdueActivities(projectId),
    enabled: !!projectId && (options.enabled ?? true),
  });
}

export function useRenewalStatus(
  projectId: string,
  options: { enabled?: boolean } = {},
) {
  return useQuery({
    queryKey: retainerKeys.projectRenewal(projectId),
    queryFn: () => getRenewalStatus(projectId),
    enabled: !!projectId && (options.enabled ?? true),
  });
}

export function useRetainerDrifts(
  projectId: string,
  filters: ListDriftsFilters = {},
  options: { enabled?: boolean } = {},
) {
  return useQuery({
    queryKey: retainerKeys.projectDrifts(projectId, filters),
    queryFn: () => listDrifts(projectId, filters),
    enabled: !!projectId && (options.enabled ?? true),
  });
}

// ═══════════════════════════════════════════════════════════════════
// Queries — paso 2
// ═══════════════════════════════════════════════════════════════════

export function usePaso2Dashboard() {
  return useQuery({
    queryKey: retainerKeys.paso2Dashboard(),
    queryFn: () => getPaso2Dashboard(),
  });
}

export function useRetainerTimeline(retainerId: string | null) {
  return useQuery({
    queryKey: retainerKeys.paso2Timeline(retainerId ?? ""),
    queryFn: () => getRetainerTimeline(retainerId!),
    enabled: !!retainerId,
  });
}

export function useHealthDetail(retainerId: string | null) {
  return useQuery({
    queryKey: retainerKeys.paso2HealthDetail(retainerId ?? ""),
    queryFn: () => getHealthDetail(retainerId!),
    enabled: !!retainerId,
  });
}

export function usePricingCatalog(category?: string) {
  return useQuery({
    queryKey: retainerKeys.paso2PricingCatalog(category),
    queryFn: () => getPricingCatalog(category),
  });
}

export function useAgent26Summary() {
  return useQuery({
    queryKey: retainerKeys.paso2Agent26Summary(),
    queryFn: () => getAgent26Summary(),
  });
}

export function useAgent26Alerts() {
  return useQuery({
    queryKey: retainerKeys.paso2Agent26Alerts(),
    queryFn: () => getAgent26Alerts(),
  });
}

// ═══════════════════════════════════════════════════════════════════
// Mutations — lifecycle
// ═══════════════════════════════════════════════════════════════════

export function useCreateRetainer(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateRetainerBody) => createRetainer(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: retainerKeys.project(projectId) });
      qc.invalidateQueries({ queryKey: retainerKeys.all() });
    },
  });
}

export function useUpdateRetainer(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: UpdateRetainerBody) =>
      updateProjectRetainer(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: retainerKeys.project(projectId) });
      qc.invalidateQueries({ queryKey: retainerKeys.all() });
    },
  });
}

export function usePauseRetainer(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => pauseProjectRetainer(projectId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: retainerKeys.all() });
    },
  });
}

export function useCancelRetainer(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => cancelProjectRetainer(projectId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: retainerKeys.all() });
    },
  });
}

export function useRenewRetainer(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: RenewBody) => renewProjectRetainer(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: retainerKeys.all() });
    },
  });
}

// ═══════════════════════════════════════════════════════════════════
// Mutations — actividades
// ═══════════════════════════════════════════════════════════════════

export function useGenerateActivities(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: GenerateActivitiesBody) =>
      generateActivities(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["retainer", "project", projectId, "activities"],
      });
    },
  });
}

export function useStartActivity(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (activityId: string) => startActivity(projectId, activityId),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["retainer", "project", projectId, "activities"],
      });
    },
  });
}

export function useCompleteActivity(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      activityId,
      body,
    }: {
      activityId: string;
      body: CompleteActivityBody;
    }) => completeActivity(projectId, activityId, body),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["retainer", "project", projectId, "activities"],
      });
      qc.invalidateQueries({ queryKey: retainerKeys.project(projectId) });
    },
  });
}

// ═══════════════════════════════════════════════════════════════════
// Mutations — drift / RAG / billing
// ═══════════════════════════════════════════════════════════════════

export function useRegisterDrift(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: RegisterDriftBody) => registerDrift(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["retainer", "project", projectId, "drifts"],
      });
    },
  });
}

export function useResolveDrift(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (driftId: string) => resolveDrift(projectId, driftId),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["retainer", "project", projectId, "drifts"],
      });
    },
  });
}

export function useRecalculateRag(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => recalculateRag(projectId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: retainerKeys.project(projectId) });
      qc.invalidateQueries({ queryKey: retainerKeys.all() });
    },
  });
}

export function useGenerateMonthlyInvoice(projectId: string) {
  return useMutation({
    mutationFn: () => generateMonthlyInvoice(projectId),
  });
}

// ═══════════════════════════════════════════════════════════════════
// Mutations — paso 2
// ═══════════════════════════════════════════════════════════════════

export function useSuggestTier() {
  return useMutation({
    mutationFn: (body: SuggestTierBody) => suggestTier(body),
  });
}

export function useUpgradeTier(retainerId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (newTier: RetainerTier) => upgradeTier(retainerId, newTier),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: retainerKeys.all() });
    },
  });
}

export function useMaterialChange(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: MaterialChangeBody) =>
      triggerMaterialChange(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["retainer", "project", projectId, "activities"],
      });
    },
  });
}
