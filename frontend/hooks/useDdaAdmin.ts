"use client";

/**
 * useDdaAdmin · sub-atom 1.D.F.A v3.11.
 *
 * Hooks tanstack-query para admin M03 DdA gestión completa.
 * Wraps 8 endpoints existing backend (status · entries · stats · generate ·
 * update entry · freeze · unfreeze · catalog · entry by measure).
 *
 * Sostiene OPS-045 24ª aplicación: backend production-grade existing · solo
 * frontend POLISH wire.
 */
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  freezeAdminDda,
  generateAdminDda,
  getAdminDdaStats,
  getAdminEntryByMeasure,
  getAdminMeasuresCatalog,
  getDdaStatus,
  getE040SignatureStatus,
  listAdminDdaEntries,
  requestE040Signature,
  unfreezeAdminDda,
  updateAdminDdaEntry,
  type DdaAdminEntry,
  type DdaAdminStats,
  type DdaCatalogMeasure,
  type DdaEntryUpdate,
  type DdaEntryUpdateResult,
  type DdaFreezeResult,
  type DdaGenerateRequest,
  type DdaGenerateResult,
  type DdaMarco,
  type DdaStatusResponse,
  type E040SignatureRequest,
  type E040SignatureResponse,
  type E040SignatureStatus,
} from "@/lib/api/dda";

const ADMIN_KEY = ["dda", "admin"] as const;

// ════════════════════════════════════════════════════════════════════
// Queries
// ════════════════════════════════════════════════════════════════════

export function useDdaAdminStatus(projectId: string | undefined) {
  return useQuery<DdaStatusResponse>({
    queryKey: [...ADMIN_KEY, "status", projectId],
    queryFn: () => getDdaStatus(projectId!),
    enabled: !!projectId,
    staleTime: 30_000,
  });
}

export function useDdaAdminEntries(
  projectId: string | undefined,
  filters?: { marco?: DdaMarco; familia?: string },
) {
  return useQuery<DdaAdminEntry[]>({
    queryKey: [...ADMIN_KEY, "entries", projectId, filters ?? {}],
    queryFn: () => listAdminDdaEntries(projectId!, filters),
    enabled: !!projectId,
    staleTime: 20_000,
  });
}

export function useDdaAdminStats(projectId: string | undefined) {
  return useQuery<DdaAdminStats>({
    queryKey: [...ADMIN_KEY, "stats", projectId],
    queryFn: () => getAdminDdaStats(projectId!),
    enabled: !!projectId,
    staleTime: 30_000,
  });
}

export function useDdaAdminCatalog(marco?: DdaMarco) {
  return useQuery<DdaCatalogMeasure[]>({
    queryKey: [...ADMIN_KEY, "catalog", marco ?? "all"],
    queryFn: () => getAdminMeasuresCatalog(marco),
    staleTime: 3_600_000, // 1h · catalog estable
  });
}

export function useDdaAdminEntryByMeasure(
  projectId: string | undefined,
  measureCodigo: string | undefined,
) {
  return useQuery<DdaAdminEntry>({
    queryKey: [
      ...ADMIN_KEY,
      "entry-by-measure",
      projectId,
      measureCodigo,
    ],
    queryFn: () => getAdminEntryByMeasure(projectId!, measureCodigo!),
    enabled: !!projectId && !!measureCodigo,
  });
}

export function useE040SignatureStatus(projectId: string | undefined) {
  return useQuery<E040SignatureStatus>({
    queryKey: [...ADMIN_KEY, "e040-signature-status", projectId],
    queryFn: () => getE040SignatureStatus(projectId!),
    enabled: !!projectId,
    staleTime: 15_000,
  });
}

// ════════════════════════════════════════════════════════════════════
// Mutations · invalidate ADMIN_KEY prefix on success
// ════════════════════════════════════════════════════════════════════

function useInvalidateAdminKeys() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: ADMIN_KEY });
}

export function useGenerateDda() {
  const invalidate = useInvalidateAdminKeys();
  return useMutation<DdaGenerateResult, Error, DdaGenerateRequest>({
    mutationFn: (body) => generateAdminDda(body),
    onSuccess: invalidate,
  });
}

export function useUpdateDdaEntry() {
  const invalidate = useInvalidateAdminKeys();
  return useMutation<
    DdaEntryUpdateResult,
    Error,
    { entryId: string; updates: DdaEntryUpdate }
  >({
    mutationFn: ({ entryId, updates }) => updateAdminDdaEntry(entryId, updates),
    onSuccess: invalidate,
  });
}

export function useFreezeDda() {
  const invalidate = useInvalidateAdminKeys();
  return useMutation<
    DdaFreezeResult,
    Error,
    { projectId: string; aprobadoPor: string }
  >({
    mutationFn: ({ projectId, aprobadoPor }) =>
      freezeAdminDda(projectId, aprobadoPor),
    onSuccess: invalidate,
  });
}

export function useUnfreezeDda() {
  const invalidate = useInvalidateAdminKeys();
  return useMutation<void, Error, { projectId: string }>({
    mutationFn: ({ projectId }) => unfreezeAdminDda(projectId),
    onSuccess: invalidate,
  });
}

export function useRequestE040Signature() {
  const invalidate = useInvalidateAdminKeys();
  return useMutation<
    E040SignatureResponse,
    Error,
    { projectId: string; body: E040SignatureRequest }
  >({
    mutationFn: ({ projectId, body }) => requestE040Signature(projectId, body),
    onSuccess: invalidate,
  });
}
