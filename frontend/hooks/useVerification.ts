"use client";

/**
 * React Query hooks para K.17 — Verificación técnica (Motor 8 v5.1).
 *
 * 0 mocks. Todos los hooks invocan endpoints reales.
 */
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  createHandoff,
  createVerificationRun,
  generateReport,
  getDelta,
  getFindingsByMeasure,
  getHeatmap,
  getRemediationPlan,
  getScore,
  getVerificationRun,
  ingestExternalFindings,
  killRun,
  listFindings,
  listVerificationRuns,
  patchFinding,
  patchFindingMapping,
  requestRetest,
  type IngestRequestBody,
  type ListFindingsFilters,
} from "@/lib/api/verification";
import type {
  EnsMeasureInput,
} from "@/lib/api/verification";
import type {
  FindingPatchBody,
  HandoffCreateBody,
  ReportRequestBody,
  RetestRequestBody,
  RunCreateBody,
} from "@/lib/verification-types";

// ─── Keys centralizadas ─────────────────────────────────────────────

export const verificationKeys = {
  all: (projectId: string) => ["verification", projectId] as const,
  runs: (projectId: string) =>
    ["verification", projectId, "runs"] as const,
  run: (projectId: string, runId: string) =>
    ["verification", projectId, "runs", runId] as const,
  findings: (
    projectId: string,
    runId: string,
    filters?: ListFindingsFilters,
  ) =>
    [
      "verification",
      projectId,
      "runs",
      runId,
      "findings",
      filters ?? {},
    ] as const,
  heatmap: (projectId: string) =>
    ["verification", projectId, "heatmap"] as const,
  score: (projectId: string) =>
    ["verification", projectId, "score"] as const,
  delta: (projectId: string) =>
    ["verification", projectId, "delta"] as const,
  plan: (projectId: string) =>
    ["verification", projectId, "remediation-plan"] as const,
};

// ─── Queries ────────────────────────────────────────────────────────

export function useVerificationRuns(projectId: string, status?: string) {
  return useQuery({
    queryKey: [...verificationKeys.runs(projectId), status ?? "all"],
    queryFn: () => listVerificationRuns(projectId, status),
    enabled: !!projectId,
  });
}

export function useVerificationRun(projectId: string, runId: string | null) {
  return useQuery({
    queryKey: verificationKeys.run(projectId, runId ?? ""),
    queryFn: () => getVerificationRun(projectId, runId!),
    enabled: !!projectId && !!runId,
  });
}

export function useFindings(
  projectId: string,
  runId: string | null,
  filters: ListFindingsFilters = {},
) {
  return useQuery({
    queryKey: verificationKeys.findings(projectId, runId ?? "", filters),
    queryFn: () => listFindings(projectId, runId!, filters),
    enabled: !!projectId && !!runId,
  });
}

export function useHeatmap(projectId: string) {
  return useQuery({
    queryKey: verificationKeys.heatmap(projectId),
    queryFn: () => getHeatmap(projectId),
    enabled: !!projectId,
  });
}

export function useScore(projectId: string) {
  return useQuery({
    queryKey: verificationKeys.score(projectId),
    queryFn: () => getScore(projectId),
    enabled: !!projectId,
  });
}

export function useDelta(projectId: string) {
  return useQuery({
    queryKey: verificationKeys.delta(projectId),
    queryFn: () => getDelta(projectId),
    enabled: !!projectId,
  });
}

export function useVerificationForMeasure(
  projectId: string, measureCode: string | null,
) {
  return useQuery({
    queryKey: [
      "verification", projectId, "by-measure", measureCode ?? "",
    ],
    queryFn: () => getFindingsByMeasure(projectId, measureCode!),
    enabled: !!projectId && !!measureCode,
  });
}

export function useRemediationPlan(projectId: string) {
  return useQuery({
    queryKey: verificationKeys.plan(projectId),
    queryFn: () => getRemediationPlan(projectId),
    enabled: !!projectId,
  });
}

// ─── Mutations ──────────────────────────────────────────────────────

export function useCreateRun(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: RunCreateBody) =>
      createVerificationRun(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: verificationKeys.all(projectId) });
    },
  });
}

export function usePatchFinding(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      findingId,
      body,
    }: {
      findingId: string;
      body: FindingPatchBody;
    }) => patchFinding(projectId, findingId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: verificationKeys.all(projectId) });
    },
  });
}

export function usePatchFindingMapping(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      findingId,
      body,
    }: {
      findingId: string;
      body: {
        ens_measures: EnsMeasureInput[];
        ens_primary_measure?: string | null;
      };
    }) => patchFindingMapping(projectId, findingId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: verificationKeys.all(projectId) });
    },
  });
}

export function useRetestFinding(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      findingId,
      body,
    }: {
      findingId: string;
      body?: RetestRequestBody;
    }) => requestRetest(projectId, findingId, body ?? {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: verificationKeys.all(projectId) });
    },
  });
}

export function useKillRun(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (runId: string) => killRun(projectId, runId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: verificationKeys.all(projectId) });
    },
  });
}

export function useCreateHandoff(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: HandoffCreateBody) => createHandoff(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: verificationKeys.all(projectId) });
    },
  });
}

export function useIngestExternal(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: IngestRequestBody) =>
      ingestExternalFindings(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: verificationKeys.all(projectId) });
    },
  });
}

export function useGenerateReport(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      runId,
      body,
    }: {
      runId: string;
      body: ReportRequestBody;
    }) => generateReport(projectId, runId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: verificationKeys.all(projectId) });
    },
  });
}
