"use client";

/**
 * React Query hooks para Motor 22 - Technical Discovery (SAN-E v3.MB-4.1).
 *
 * 0 mocks. Todos los hooks invocan endpoints reales del backend
 * (37 totales bajo /api/v1/projects/{id}).
 */

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  cancelDiscoveryRun,
  createDiscoveryRun,
  generateDataFlows,
  getAlertsSummary,
  getAssetsSummary,
  getConfigsSummary,
  getContinuityAssessment,
  getDataStoresSummary,
  getDiscoverySummary,
  getIdentitiesSummary,
  getLoggingAssessment,
  getVulnsSummary,
  listDataFlows,
  listDiscoveryAlerts,
  listDiscoveryAssets,
  listDiscoveryConfigs,
  listDiscoveryDataStores,
  listDiscoveryIdentities,
  listDiscoveryRuns,
  listDiscoveryVulns,
  recordContinuityAssessment,
  recordLoggingAssessment,
  updateVulnerability,
  type ContinuityBody,
  type CreateRunBody,
  type GenerateDataflowBody,
  type LoggingBody,
  type VulnUpdateBody,
} from "@/lib/admin-discovery/api";

// =====================================================================
// Centralized keys
// =====================================================================

export const discoveryKeys = {
  all: () => ["discovery"] as const,
  summary: (projectId: string) => ["discovery", "summary", projectId] as const,
  runs: (projectId: string) => ["discovery", "runs", projectId] as const,
  assets: (projectId: string) => ["discovery", "assets", projectId] as const,
  assetsSummary: (projectId: string) =>
    ["discovery", "assets", "summary", projectId] as const,
  identities: (projectId: string) =>
    ["discovery", "identities", projectId] as const,
  identitiesSummary: (projectId: string) =>
    ["discovery", "identities", "summary", projectId] as const,
  dataStores: (projectId: string) =>
    ["discovery", "data-stores", projectId] as const,
  dataStoresSummary: (projectId: string) =>
    ["discovery", "data-stores", "summary", projectId] as const,
  vulns: (projectId: string) => ["discovery", "vulns", projectId] as const,
  vulnsSummary: (projectId: string) =>
    ["discovery", "vulns", "summary", projectId] as const,
  configs: (projectId: string) => ["discovery", "configs", projectId] as const,
  configsSummary: (projectId: string) =>
    ["discovery", "configs", "summary", projectId] as const,
  dataflows: (projectId: string) => ["discovery", "dataflows", projectId] as const,
  continuity: (projectId: string) =>
    ["discovery", "continuity", projectId] as const,
  logging: (projectId: string) => ["discovery", "logging", projectId] as const,
  alerts: (projectId: string) => ["discovery", "alerts", projectId] as const,
  alertsSummary: (projectId: string) =>
    ["discovery", "alerts", "summary", projectId] as const,
};

// =====================================================================
// Queries
// =====================================================================

export function useDiscoverySummary(projectId: string) {
  return useQuery({
    queryKey: discoveryKeys.summary(projectId),
    queryFn: () => getDiscoverySummary(projectId),
    enabled: !!projectId,
    staleTime: 30_000,
  });
}

export function useDiscoveryRuns(projectId: string) {
  return useQuery({
    queryKey: discoveryKeys.runs(projectId),
    queryFn: () => listDiscoveryRuns(projectId),
    enabled: !!projectId,
  });
}

export function useDiscoveryAssets(projectId: string) {
  return useQuery({
    queryKey: discoveryKeys.assets(projectId),
    queryFn: () => listDiscoveryAssets(projectId),
    enabled: !!projectId,
  });
}

export function useAssetsSummary(projectId: string) {
  return useQuery({
    queryKey: discoveryKeys.assetsSummary(projectId),
    queryFn: () => getAssetsSummary(projectId),
    enabled: !!projectId,
  });
}

export function useDiscoveryIdentities(projectId: string) {
  return useQuery({
    queryKey: discoveryKeys.identities(projectId),
    queryFn: () => listDiscoveryIdentities(projectId),
    enabled: !!projectId,
  });
}

export function useIdentitiesSummary(projectId: string) {
  return useQuery({
    queryKey: discoveryKeys.identitiesSummary(projectId),
    queryFn: () => getIdentitiesSummary(projectId),
    enabled: !!projectId,
  });
}

export function useDiscoveryDataStores(projectId: string) {
  return useQuery({
    queryKey: discoveryKeys.dataStores(projectId),
    queryFn: () => listDiscoveryDataStores(projectId),
    enabled: !!projectId,
  });
}

export function useDataStoresSummary(projectId: string) {
  return useQuery({
    queryKey: discoveryKeys.dataStoresSummary(projectId),
    queryFn: () => getDataStoresSummary(projectId),
    enabled: !!projectId,
  });
}

export function useDiscoveryVulns(projectId: string) {
  return useQuery({
    queryKey: discoveryKeys.vulns(projectId),
    queryFn: () => listDiscoveryVulns(projectId),
    enabled: !!projectId,
  });
}

export function useVulnsSummary(projectId: string) {
  return useQuery({
    queryKey: discoveryKeys.vulnsSummary(projectId),
    queryFn: () => getVulnsSummary(projectId),
    enabled: !!projectId,
  });
}

export function useDiscoveryConfigs(projectId: string) {
  return useQuery({
    queryKey: discoveryKeys.configs(projectId),
    queryFn: () => listDiscoveryConfigs(projectId),
    enabled: !!projectId,
  });
}

export function useConfigsSummary(projectId: string) {
  return useQuery({
    queryKey: discoveryKeys.configsSummary(projectId),
    queryFn: () => getConfigsSummary(projectId),
    enabled: !!projectId,
  });
}

export function useDataFlows(projectId: string) {
  return useQuery({
    queryKey: discoveryKeys.dataflows(projectId),
    queryFn: () => listDataFlows(projectId),
    enabled: !!projectId,
  });
}

export function useContinuityAssessment(projectId: string) {
  return useQuery({
    queryKey: discoveryKeys.continuity(projectId),
    queryFn: () => getContinuityAssessment(projectId),
    enabled: !!projectId,
  });
}

export function useLoggingAssessment(projectId: string) {
  return useQuery({
    queryKey: discoveryKeys.logging(projectId),
    queryFn: () => getLoggingAssessment(projectId),
    enabled: !!projectId,
  });
}

export function useDiscoveryAlerts(projectId: string) {
  return useQuery({
    queryKey: discoveryKeys.alerts(projectId),
    queryFn: () => listDiscoveryAlerts(projectId),
    enabled: !!projectId,
  });
}

export function useAlertsSummary(projectId: string) {
  return useQuery({
    queryKey: discoveryKeys.alertsSummary(projectId),
    queryFn: () => getAlertsSummary(projectId),
    enabled: !!projectId,
  });
}

// =====================================================================
// Mutations
// =====================================================================

export function useCreateDiscoveryRun(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateRunBody = {}) => createDiscoveryRun(projectId, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["discovery"] });
    },
  });
}

export function useCancelDiscoveryRun(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (runId: string) => cancelDiscoveryRun(projectId, runId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: discoveryKeys.runs(projectId) });
    },
  });
}

export function useUpdateVulnerability(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ findingId, body }: { findingId: string; body: VulnUpdateBody }) =>
      updateVulnerability(projectId, findingId, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: discoveryKeys.vulns(projectId) });
      void qc.invalidateQueries({ queryKey: discoveryKeys.vulnsSummary(projectId) });
    },
  });
}

export function useGenerateDataFlows(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: GenerateDataflowBody) => generateDataFlows(projectId, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: discoveryKeys.dataflows(projectId) });
    },
  });
}

export function useRecordContinuity(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ContinuityBody) => recordContinuityAssessment(projectId, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: discoveryKeys.continuity(projectId) });
    },
  });
}

export function useRecordLogging(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: LoggingBody) => recordLoggingAssessment(projectId, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: discoveryKeys.logging(projectId) });
    },
  });
}
