"use client";

/**
 * tanstack-query hooks · cloud-connectors admin (sub-atom 1.D.X.J v3.12).
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  type CloudConnectorAdmin,
  type CloudGap,
  type CloudProviderCatalogItem,
  type CloudResource,
  type CloudSyncJob,
  type DiagnosisReport,
  type DigestGenerateResponse,
  type ConformityCloudScoreResponse,
  type DigestSnapshot,
  type DiscoveryConsolidatedResponse,
  type MageritEnrichedInventoryResponse,
  cloudConnectorsAdminApi,
} from "@/lib/api/cloud-connectors-admin";

const KEY = ["cloud-connectors", "admin"] as const;

export function useProvidersCatalog() {
  return useQuery<CloudProviderCatalogItem[]>({
    queryKey: [...KEY, "catalog"],
    queryFn: () => cloudConnectorsAdminApi.getProvidersCatalog(),
    staleTime: 1000 * 60 * 60, // 1h
  });
}

export function useSupportedMeasures() {
  return useQuery<string[]>({
    queryKey: [...KEY, "supported-measures"],
    queryFn: () => cloudConnectorsAdminApi.getSupportedMeasures(),
    staleTime: 1000 * 60 * 60,
  });
}

export function useCloudConnectors(projectId: string, includeRevoked = false) {
  return useQuery<{ items: CloudConnectorAdmin[]; total: number }>({
    queryKey: [...KEY, "list", projectId, includeRevoked],
    queryFn: () =>
      cloudConnectorsAdminApi.listConnectors(projectId, includeRevoked),
    refetchInterval: 30_000,
  });
}

export function useCloudResources(
  projectId: string,
  connectorId: string | null,
  resourceType?: string,
) {
  return useQuery<{ items: CloudResource[]; total: number }>({
    queryKey: [...KEY, "resources", projectId, connectorId, resourceType],
    queryFn: () =>
      cloudConnectorsAdminApi.listResources(projectId, connectorId!, {
        resourceType,
        limit: 500,
      }),
    enabled: !!connectorId,
  });
}

export function useCloudSyncJobs(projectId: string, connectorId: string | null) {
  return useQuery<{ items: CloudSyncJob[]; total: number }>({
    queryKey: [...KEY, "sync-jobs", projectId, connectorId],
    queryFn: () =>
      cloudConnectorsAdminApi.listSyncJobs(projectId, connectorId!),
    enabled: !!connectorId,
    refetchInterval: 15_000,
  });
}

export function useCloudGaps(
  projectId: string,
  opts: { severities?: string[]; includeResolved?: boolean } = {},
) {
  return useQuery<{ items: CloudGap[]; total: number }>({
    queryKey: [...KEY, "gaps", projectId, opts],
    queryFn: () =>
      cloudConnectorsAdminApi.listGaps(projectId, opts),
    refetchInterval: 30_000,
  });
}

export function useTriggerSync(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (connectorId: string) =>
      cloudConnectorsAdminApi.triggerSync(projectId, connectorId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [...KEY, "list", projectId] });
      qc.invalidateQueries({ queryKey: [...KEY, "sync-jobs", projectId] });
      qc.invalidateQueries({ queryKey: [...KEY, "resources", projectId] });
    },
  });
}

export function useRevokeConnector(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (connectorId: string) =>
      cloudConnectorsAdminApi.revokeConnector(projectId, connectorId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [...KEY, "list", projectId] });
    },
  });
}

export function useResolveGap(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      gapId,
      note,
      evidenceLinkId,
    }: {
      gapId: string;
      note?: string;
      evidenceLinkId?: string | null;
    }) =>
      cloudConnectorsAdminApi.resolveGap(projectId, gapId, {
        resolution_note: note,
        evidence_link_id: evidenceLinkId,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [...KEY, "gaps", projectId] });
    },
  });
}

export function useRunDiagnosis(projectId: string) {
  const qc = useQueryClient();
  return useMutation<DiagnosisReport>({
    mutationFn: () =>
      cloudConnectorsAdminApi.runDiagnosis(projectId, {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [...KEY, "gaps", projectId] });
    },
  });
}

// Monitoring digest hooks (sub-fase 1.D.X.VERIFY 2a)

export function useAdminLatestDigest(projectId: string) {
  return useQuery<DigestSnapshot | null>({
    queryKey: [...KEY, "digest-latest", projectId],
    queryFn: () => cloudConnectorsAdminApi.getLatestDigest(projectId),
    refetchInterval: 60_000,
  });
}

export function useTriggerDigest(projectId: string) {
  const qc = useQueryClient();
  return useMutation<DigestGenerateResponse>({
    mutationFn: () => cloudConnectorsAdminApi.triggerDigest(projectId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [...KEY, "digest-latest", projectId] });
    },
  });
}

// Discovery consolidation hook (sub-fase 1.D.J.B.M22)

export function useConsolidatedDiscovery(projectId: string) {
  return useQuery<DiscoveryConsolidatedResponse>({
    queryKey: [...KEY, "discovery-consolidated", projectId],
    queryFn: () => cloudConnectorsAdminApi.getDiscoveryConsolidated(projectId),
    refetchInterval: 30_000,
  });
}

// MAGERIT enriched inventory hook (sub-fase 1.D.J.B.M02)

export function useEnrichedMageritInventory(
  projectId: string,
  analysisId?: string,
) {
  return useQuery<MageritEnrichedInventoryResponse>({
    queryKey: [...KEY, "magerit-enriched", projectId, analysisId ?? "all"],
    queryFn: () =>
      cloudConnectorsAdminApi.getMageritEnrichedInventory(projectId, analysisId),
    refetchInterval: 60_000,
    enabled: Boolean(projectId),
  });
}

// Conformity cloud score hook (sub-fase 1.D.J.B.M27)
//
// refetch 60s · score deriva de gap_engine state que cambia post-syncs cloud
// (intervalo Celery beat L-light retainer · 5-15 min típico) · 60s balance
// stale-while-revalidate vs server load · NO realtime needed (declaración
// es ceremonia anual · score visible es snapshot post último diagnosis).
export function useConformityCloudScore(projectId: string) {
  return useQuery<ConformityCloudScoreResponse>({
    queryKey: [...KEY, "conformity-cloud-score", projectId],
    queryFn: () => cloudConnectorsAdminApi.getConformityCloudScore(projectId),
    refetchInterval: 60_000,
    enabled: Boolean(projectId),
  });
}
