"use client";

/**
 * React Query hooks para Motor 2 - MAGERIT v3 Risk Engine.
 *
 * 0 mocks. Todos los hooks invocan endpoints reales del backend
 * (29 totales bajo /api/v1).
 *
 * Pattern equivalente a `useDiagnosis` (FASE 9.A.4 greenfield).
 */
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  type AnalysisCreateBody,
  type AssetInventoryRequest,
  type DependencyGraphRequest,
  type RequestE028SignatureBody,
  type SafeguardDeploymentRequest,
  type ThreatAssessmentRequest,
  type TreatmentPlanRequest,
  calculateEffectiveRisk,
  calculateIntrinsicRisk,
  calculateResidualRisk,
  createAnalysis,
  deploySafeguards,
  freezeAnalysis,
  generateTreatmentPlan,
  getAnalysisReport,
  getAnalysisSnapshot,
  getE028SignatureStatus,
  importAssets,
  loadAssets,
  loadDependencies,
  loadThreats,
  propagateValues,
  requestE028Signature,
  softDeleteAnalysis,
  unfreezeAnalysis,
} from "@/lib/api/magerit";

// ===================================================================
// Keys centralizadas (sub-namespaces)
// ===================================================================

export const mageritKeys = {
  all: () => ["magerit"] as const,

  // Per-analysis snapshots/reports
  analysis: (analysisId: string) =>
    ["magerit", "analysis", analysisId] as const,
  report: (analysisId: string) =>
    ["magerit", "analysis", analysisId, "report"] as const,
  snapshot: (analysisId: string) =>
    ["magerit", "analysis", analysisId, "snapshot"] as const,

  // E028 signature
  signatureStatus: (analysisId: string) =>
    ["magerit", "analysis", analysisId, "signature-status"] as const,
};

// ===================================================================
// Queries
// ===================================================================

/**
 * Hook principal: report consolidado del análisis MAGERIT.
 * Consume GET /api/v1/analysis/{id}/report.
 * Devuelve 404 si el análisis no existe; el componente debe manejarlo.
 */
export function useMageritReport(
  analysisId: string | undefined,
  options: { enabled?: boolean } = {},
) {
  const enabled = options.enabled !== false && !!analysisId;
  return useQuery({
    queryKey: mageritKeys.report(analysisId ?? ""),
    queryFn: () => getAnalysisReport(analysisId as string),
    enabled,
    retry: false,
  });
}

export function useMageritSnapshot(
  analysisId: string | undefined,
  options: { enabled?: boolean } = {},
) {
  const enabled = options.enabled !== false && !!analysisId;
  return useQuery({
    queryKey: mageritKeys.snapshot(analysisId ?? ""),
    queryFn: () => getAnalysisSnapshot(analysisId as string),
    enabled,
    retry: false,
  });
}

export function useMageritSignatureStatus(
  analysisId: string | undefined,
  options: { enabled?: boolean } = {},
) {
  const enabled = options.enabled !== false && !!analysisId;
  return useQuery({
    queryKey: mageritKeys.signatureStatus(analysisId ?? ""),
    queryFn: () => getE028SignatureStatus(analysisId as string),
    enabled,
    retry: false,
  });
}

// ===================================================================
// Mutations - Lifecycle
// ===================================================================

export function useCreateAnalysis(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: AnalysisCreateBody) => createAnalysis(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: mageritKeys.all() });
    },
  });
}

export function useSoftDeleteAnalysis() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (analysisId: string) => softDeleteAnalysis(analysisId),
    onSuccess: (_, analysisId) => {
      qc.invalidateQueries({ queryKey: mageritKeys.analysis(analysisId) });
      qc.invalidateQueries({ queryKey: mageritKeys.all() });
    },
  });
}

// ===================================================================
// Mutations - Asset / Dependency / Threat / Safeguard population
// ===================================================================

export function useLoadAssets(analysisId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: AssetInventoryRequest) => loadAssets(analysisId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: mageritKeys.report(analysisId) });
    },
  });
}

export function useImportAssets(analysisId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: AssetInventoryRequest) =>
      importAssets(analysisId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: mageritKeys.report(analysisId) });
    },
  });
}

export function useLoadDependencies(analysisId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: DependencyGraphRequest) =>
      loadDependencies(analysisId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: mageritKeys.report(analysisId) });
    },
  });
}

export function usePropagateValues(analysisId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => propagateValues(analysisId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: mageritKeys.report(analysisId) });
    },
  });
}

export function useLoadThreats(analysisId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ThreatAssessmentRequest) =>
      loadThreats(analysisId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: mageritKeys.report(analysisId) });
    },
  });
}

export function useDeploySafeguards(analysisId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: SafeguardDeploymentRequest) =>
      deploySafeguards(analysisId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: mageritKeys.report(analysisId) });
    },
  });
}

// ===================================================================
// Mutations - Risk calculations
// ===================================================================

export function useCalculateIntrinsicRisk(analysisId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => calculateIntrinsicRisk(analysisId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: mageritKeys.report(analysisId) });
    },
  });
}

export function useCalculateEffectiveRisk(analysisId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => calculateEffectiveRisk(analysisId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: mageritKeys.report(analysisId) });
    },
  });
}

export function useCalculateResidualRisk(analysisId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => calculateResidualRisk(analysisId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: mageritKeys.report(analysisId) });
    },
  });
}

// ===================================================================
// Mutations - Treatment plan
// ===================================================================

export function useGenerateTreatmentPlan(analysisId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: TreatmentPlanRequest = {}) =>
      generateTreatmentPlan(analysisId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: mageritKeys.report(analysisId) });
    },
  });
}

// ===================================================================
// Mutations - Freeze / Unfreeze
// ===================================================================

export function useFreezeAnalysis(analysisId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => freezeAnalysis(analysisId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: mageritKeys.analysis(analysisId) });
    },
  });
}

export function useUnfreezeAnalysis(analysisId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => unfreezeAnalysis(analysisId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: mageritKeys.analysis(analysisId) });
    },
  });
}

// ===================================================================
// Mutations - E028 signature
// ===================================================================

export function useRequestE028Signature(analysisId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: RequestE028SignatureBody) =>
      requestE028Signature(analysisId, body),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: mageritKeys.signatureStatus(analysisId),
      });
      qc.invalidateQueries({ queryKey: mageritKeys.analysis(analysisId) });
    },
  });
}
