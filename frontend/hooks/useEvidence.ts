"use client";

/**
 * React Query hooks para Motor 7 — Evidence.
 *
 * 0 mocks. Todos los hooks invocan endpoints reales del backend.
 */
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  getExpiringEvidence,
  getPublicKey,
  listEvidence,
  renewEvidence,
  uploadEvidence,
  verifyEvidence,
  type ListEvidenceFilters,
} from "@/lib/api/evidence";

// ─── Keys centralizadas ─────────────────────────────────────────────

export const evidenceKeys = {
  all: (projectId: string) => ["evidence", projectId] as const,
  list: (projectId: string, filters?: ListEvidenceFilters) =>
    ["evidence", projectId, "list", filters ?? {}] as const,
  expiring: (projectId: string, warningDays: number) =>
    ["evidence", projectId, "expiring", warningDays] as const,
  publicKey: () => ["evidence", "public-key"] as const,
};

// ─── Queries ────────────────────────────────────────────────────────

export function useEvidenceList(
  projectId: string,
  filters: ListEvidenceFilters = {},
) {
  return useQuery({
    queryKey: evidenceKeys.list(projectId, filters),
    queryFn: () => listEvidence(projectId, filters),
    enabled: !!projectId,
  });
}

export function useExpiringEvidence(projectId: string, warningDays = 30) {
  return useQuery({
    queryKey: evidenceKeys.expiring(projectId, warningDays),
    queryFn: () => getExpiringEvidence(projectId, warningDays),
    enabled: !!projectId,
  });
}

export function useEvidencePublicKey() {
  return useQuery({
    queryKey: evidenceKeys.publicKey(),
    queryFn: () => getPublicKey(),
  });
}

// ─── Mutations ──────────────────────────────────────────────────────

export function useUploadEvidence(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      file: File;
      evidence_type_id: string;
      measure_code: string;
      obligation_id?: string;
    }) => uploadEvidence(projectId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: evidenceKeys.all(projectId) });
    },
  });
}

export function useRenewEvidence(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      evidenceId,
      motivo,
    }: {
      evidenceId: string;
      motivo?: string;
    }) => renewEvidence(projectId, evidenceId, motivo),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: evidenceKeys.all(projectId) });
    },
  });
}

export function useVerifyEvidence(projectId: string) {
  return useMutation({
    mutationFn: (evidenceId: string) => verifyEvidence(projectId, evidenceId),
  });
}
