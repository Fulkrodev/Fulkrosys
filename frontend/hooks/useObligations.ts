"use client";

/**
 * React Query hooks para Motor 4 (Gap Analysis) + Motor 5 (Obligations).
 *
 * 0 mocks. Todos los hooks invocan endpoints reales del backend
 * (19 totales bajo /api/v1).
 *
 * Pattern equivalente a `useDiagnosis` y `useMagerit` (FASE 9.A.4-5).
 */
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  type AnalyzeProjectRequest,
  type CloseGapRequest,
  type CreateObligationBody,
  type GapFindingUpdate,
  type GapListFilters,
  type GanttRequestParams,
  type InstantiateRequest,
  type ObligationsListFilters,
  type PrioritizeGapsLLMBody,
  type UpdateObligationBody,
  analyzeProjectGaps,
  closeGap,
  completeObligation,
  createObligation,
  deleteGap,
  getGap,
  getGapDashboard,
  getGapQuickWins,
  getObligation,
  getObligationsGantt,
  getObligationsSummary,
  instantiateObligations,
  listGaps,
  listObligations,
  prioritizeGapsLLM,
  startObligation,
  updateGap,
  updateObligation,
  verifyObligation,
} from "@/lib/api/obligations";

// ===================================================================
// Keys centralizadas (sub-namespaces)
// ===================================================================

export const obligationsKeys = {
  all: () => ["obligations"] as const,

  // M04 - Gaps
  gapsAll: () => ["obligations", "gaps"] as const,
  projectGaps: (projectId: string, filters?: GapListFilters) =>
    ["obligations", "gaps", "project", projectId, filters ?? {}] as const,
  gap: (gapId: string) => ["obligations", "gaps", "gap", gapId] as const,
  gapDashboard: (projectId: string) =>
    ["obligations", "gaps", "dashboard", projectId] as const,
  gapQuickWins: (projectId: string) =>
    ["obligations", "gaps", "quick-wins", projectId] as const,

  // M05 - Obligations
  obligationsAll: () => ["obligations", "list"] as const,
  projectObligations: (projectId: string, filters?: ObligationsListFilters) =>
    ["obligations", "list", "project", projectId, filters ?? {}] as const,
  obligation: (projectId: string, obligationId: string) =>
    ["obligations", "list", "project", projectId, obligationId] as const,
  summary: (projectId: string) =>
    ["obligations", "summary", projectId] as const,
  gantt: (projectId: string, params: GanttRequestParams) =>
    ["obligations", "gantt", projectId, params] as const,
};

// ===================================================================
// Queries - M04 Gaps
// ===================================================================

/**
 * Lista de gaps del proyecto con filtros opcionales.
 * Consume GET /api/v1/projects/{id}/gaps.
 */
export function useProjectGaps(
  projectId: string | undefined,
  filters: GapListFilters = {},
  options: { enabled?: boolean } = {},
) {
  const enabled = options.enabled !== false && !!projectId;
  return useQuery({
    queryKey: obligationsKeys.projectGaps(projectId ?? "", filters),
    queryFn: () => listGaps(projectId as string, filters),
    enabled,
    retry: false,
  });
}

export function useGap(
  gapId: string | undefined,
  options: { enabled?: boolean } = {},
) {
  const enabled = options.enabled !== false && !!gapId;
  return useQuery({
    queryKey: obligationsKeys.gap(gapId ?? ""),
    queryFn: () => getGap(gapId as string),
    enabled,
    retry: false,
  });
}

export function useGapDashboard(
  projectId: string | undefined,
  options: { enabled?: boolean } = {},
) {
  const enabled = options.enabled !== false && !!projectId;
  return useQuery({
    queryKey: obligationsKeys.gapDashboard(projectId ?? ""),
    queryFn: () => getGapDashboard(projectId as string),
    enabled,
    retry: false,
  });
}

export function useGapQuickWins(
  projectId: string | undefined,
  options: { enabled?: boolean } = {},
) {
  const enabled = options.enabled !== false && !!projectId;
  return useQuery({
    queryKey: obligationsKeys.gapQuickWins(projectId ?? ""),
    queryFn: () => getGapQuickWins(projectId as string),
    enabled,
    retry: false,
  });
}

// ===================================================================
// Queries - M05 Obligations
// ===================================================================

/**
 * Lista obligaciones del proyecto con filtros opcionales.
 * Consume GET /api/v1/projects/{id}/obligations.
 *
 * El response shape backend es { obligations: ObligationOut[] }.
 * Devolvemos directamente la lista para que el componente la consuma plana.
 */
export function useObligations(
  projectId: string | undefined,
  filters: ObligationsListFilters = {},
  options: { enabled?: boolean } = {},
) {
  const enabled = options.enabled !== false && !!projectId;
  return useQuery({
    queryKey: obligationsKeys.projectObligations(projectId ?? "", filters),
    queryFn: async () => {
      const res = await listObligations(projectId as string, filters);
      return res.obligations;
    },
    enabled,
    retry: false,
  });
}

export function useObligation(
  projectId: string | undefined,
  obligationId: string | undefined,
  options: { enabled?: boolean } = {},
) {
  const enabled =
    options.enabled !== false && !!projectId && !!obligationId;
  return useQuery({
    queryKey: obligationsKeys.obligation(
      projectId ?? "",
      obligationId ?? "",
    ),
    queryFn: () =>
      getObligation(projectId as string, obligationId as string),
    enabled,
    retry: false,
  });
}

export function useObligationsSummary(
  projectId: string | undefined,
  options: { enabled?: boolean } = {},
) {
  const enabled = options.enabled !== false && !!projectId;
  return useQuery({
    queryKey: obligationsKeys.summary(projectId ?? ""),
    queryFn: () => getObligationsSummary(projectId as string),
    enabled,
    retry: false,
  });
}

export function useObligationsGantt(
  projectId: string | undefined,
  params: GanttRequestParams,
  options: { enabled?: boolean } = {},
) {
  const enabled =
    options.enabled !== false && !!projectId && !!params.fecha_kickoff;
  return useQuery({
    queryKey: obligationsKeys.gantt(projectId ?? "", params),
    queryFn: () => getObligationsGantt(projectId as string, params),
    enabled,
    retry: false,
  });
}

// ===================================================================
// Mutations - M04 Gap lifecycle
// ===================================================================

export function useAnalyzeProjectGaps(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: AnalyzeProjectRequest = {}) =>
      analyzeProjectGaps(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: obligationsKeys.gapsAll() });
    },
  });
}

export function useUpdateGap() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      gapId,
      body,
    }: {
      gapId: string;
      body: GapFindingUpdate;
    }) => updateGap(gapId, body),
    onSuccess: (_, variables) => {
      qc.invalidateQueries({ queryKey: obligationsKeys.gap(variables.gapId) });
      qc.invalidateQueries({ queryKey: obligationsKeys.gapsAll() });
    },
  });
}

export function useDeleteGap() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (gapId: string) => deleteGap(gapId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: obligationsKeys.gapsAll() });
    },
  });
}

export function useCloseGap() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      gapId,
      body,
    }: {
      gapId: string;
      body: CloseGapRequest;
    }) => closeGap(gapId, body),
    onSuccess: (_, variables) => {
      qc.invalidateQueries({ queryKey: obligationsKeys.gap(variables.gapId) });
      qc.invalidateQueries({ queryKey: obligationsKeys.gapsAll() });
    },
  });
}

export function usePrioritizeGapsLLM(projectId: string) {
  return useMutation({
    mutationFn: (body: PrioritizeGapsLLMBody) =>
      prioritizeGapsLLM(projectId, body),
  });
}

// ===================================================================
// Mutations - M05 Obligation lifecycle
// ===================================================================

export function useInstantiateObligations(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: InstantiateRequest) =>
      instantiateObligations(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: obligationsKeys.obligationsAll() });
      qc.invalidateQueries({ queryKey: obligationsKeys.summary(projectId) });
    },
  });
}

export function useCreateObligation(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateObligationBody) =>
      createObligation(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: obligationsKeys.obligationsAll() });
      qc.invalidateQueries({ queryKey: obligationsKeys.summary(projectId) });
    },
  });
}

export function useUpdateObligation(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      obligationId,
      body,
    }: {
      obligationId: string;
      body: UpdateObligationBody;
    }) => updateObligation(projectId, obligationId, body),
    onSuccess: (_, variables) => {
      qc.invalidateQueries({
        queryKey: obligationsKeys.obligation(projectId, variables.obligationId),
      });
      qc.invalidateQueries({ queryKey: obligationsKeys.obligationsAll() });
      qc.invalidateQueries({ queryKey: obligationsKeys.summary(projectId) });
    },
  });
}

export function useStartObligation(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (obligationId: string) =>
      startObligation(projectId, obligationId),
    onSuccess: (_, obligationId) => {
      qc.invalidateQueries({
        queryKey: obligationsKeys.obligation(projectId, obligationId),
      });
      qc.invalidateQueries({ queryKey: obligationsKeys.obligationsAll() });
      qc.invalidateQueries({ queryKey: obligationsKeys.summary(projectId) });
    },
  });
}

export function useCompleteObligation(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (obligationId: string) =>
      completeObligation(projectId, obligationId),
    onSuccess: (_, obligationId) => {
      qc.invalidateQueries({
        queryKey: obligationsKeys.obligation(projectId, obligationId),
      });
      qc.invalidateQueries({ queryKey: obligationsKeys.obligationsAll() });
      qc.invalidateQueries({ queryKey: obligationsKeys.summary(projectId) });
    },
  });
}

export function useVerifyObligation(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (obligationId: string) =>
      verifyObligation(projectId, obligationId),
    onSuccess: (_, obligationId) => {
      qc.invalidateQueries({
        queryKey: obligationsKeys.obligation(projectId, obligationId),
      });
      qc.invalidateQueries({ queryKey: obligationsKeys.obligationsAll() });
      qc.invalidateQueries({ queryKey: obligationsKeys.summary(projectId) });
    },
  });
}
