"use client";

/**
 * React Query hooks para Motor 21 - Organizational Diagnosis.
 *
 * 0 mocks. Todos los hooks invocan endpoints reales del backend
 * (17 totales bajo /api/v1/diagnosis).
 *
 * Reemplaza `useDiagnosis` que vivia en `useProjectData.ts` (extraido en 9.A.4).
 */
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  createDiagnosisLegalObligation,
  createDiagnosisProcess,
  createDiagnosisStakeholder,
  exportDiagnosisToMagerit,
  generateDiagnosisDocx,
  generateDiagnosisReport,
  getDiagnosisCompliance,
  getDiagnosisMaturity,
  getDiagnosisQuickWins,
  getDiagnosisStakeholdersSnapshot,
  getLatestDiagnosis,
  listDiagnosisLegalObligations,
  listDiagnosisProcesses,
  listDiagnosisRuns,
  listDiagnosisStakeholders,
  runDiagnosis,
  type LegalObligationBody,
  type ProcessBody,
  type RunDiagnosisBody,
  type StakeholderBody,
} from "@/lib/api/diagnosis";

// ===================================================================
// Keys centralizadas
// ===================================================================

export const diagnosisKeys = {
  all: () => ["diagnosis"] as const,
  latest: (projectId: string) =>
    ["diagnosis", "latest", projectId] as const,
  runs: (projectId: string) =>
    ["diagnosis", "runs", projectId] as const,
  maturity: (projectId: string) =>
    ["diagnosis", "maturity", projectId] as const,
  stakeholdersSnapshot: (projectId: string) =>
    ["diagnosis", "stakeholders-snapshot", projectId] as const,
  compliance: (projectId: string) =>
    ["diagnosis", "compliance", projectId] as const,
  quickWins: (projectId: string, runId: string) =>
    ["diagnosis", "quick-wins", projectId, runId] as const,
  // CRUD
  stakeholdersList: (projectId: string) =>
    ["diagnosis", "stakeholders", projectId] as const,
  processesList: (projectId: string) =>
    ["diagnosis", "processes", projectId] as const,
  legalObligationsList: (projectId: string) =>
    ["diagnosis", "legal-obligations", projectId] as const,
};

// ===================================================================
// Queries
// ===================================================================

/**
 * Hook principal: estado del diagnostico organizativo M21 para un proyecto.
 * Consume GET /api/v1/diagnosis/projects/{id}/latest. Devuelve 404 si no
 * se ha ejecutado un run; el componente debe manejar el estado vacio.
 */
export function useDiagnosis(projectId: string) {
  return useQuery({
    queryKey: diagnosisKeys.latest(projectId),
    queryFn: () => getLatestDiagnosis(projectId, false),
    enabled: !!projectId,
    retry: false, // 404 if no run yet
  });
}

export function useDiagnosisRuns(projectId: string) {
  return useQuery({
    queryKey: diagnosisKeys.runs(projectId),
    queryFn: () => listDiagnosisRuns(projectId),
    enabled: !!projectId,
  });
}

export function useDiagnosisMaturity(projectId: string) {
  return useQuery({
    queryKey: diagnosisKeys.maturity(projectId),
    queryFn: () => getDiagnosisMaturity(projectId),
    enabled: !!projectId,
    retry: false,
  });
}

export function useDiagnosisStakeholdersSnapshot(projectId: string) {
  return useQuery({
    queryKey: diagnosisKeys.stakeholdersSnapshot(projectId),
    queryFn: () => getDiagnosisStakeholdersSnapshot(projectId),
    enabled: !!projectId,
    retry: false,
  });
}

export function useDiagnosisCompliance(projectId: string) {
  return useQuery({
    queryKey: diagnosisKeys.compliance(projectId),
    queryFn: () => getDiagnosisCompliance(projectId),
    enabled: !!projectId,
    retry: false,
  });
}

export function useDiagnosisQuickWins(projectId: string, runId: string) {
  return useQuery({
    queryKey: diagnosisKeys.quickWins(projectId, runId),
    queryFn: () => getDiagnosisQuickWins(projectId, runId),
    enabled: !!projectId && !!runId,
  });
}

export function useDiagnosisStakeholdersList(projectId: string) {
  return useQuery({
    queryKey: diagnosisKeys.stakeholdersList(projectId),
    queryFn: () => listDiagnosisStakeholders(projectId),
    enabled: !!projectId,
  });
}

export function useDiagnosisProcessesList(projectId: string) {
  return useQuery({
    queryKey: diagnosisKeys.processesList(projectId),
    queryFn: () => listDiagnosisProcesses(projectId),
    enabled: !!projectId,
  });
}

export function useDiagnosisLegalObligationsList(projectId: string) {
  return useQuery({
    queryKey: diagnosisKeys.legalObligationsList(projectId),
    queryFn: () => listDiagnosisLegalObligations(projectId),
    enabled: !!projectId,
  });
}

// ===================================================================
// Mutations
// ===================================================================

export function useRunDiagnosis(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: RunDiagnosisBody) => runDiagnosis(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: diagnosisKeys.latest(projectId) });
      qc.invalidateQueries({ queryKey: diagnosisKeys.runs(projectId) });
      qc.invalidateQueries({ queryKey: diagnosisKeys.maturity(projectId) });
      qc.invalidateQueries({
        queryKey: diagnosisKeys.stakeholdersSnapshot(projectId),
      });
      qc.invalidateQueries({ queryKey: diagnosisKeys.compliance(projectId) });
    },
  });
}

export function useGenerateDiagnosisReport(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (runId: string) => generateDiagnosisReport(projectId, runId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: diagnosisKeys.latest(projectId) });
      qc.invalidateQueries({ queryKey: diagnosisKeys.runs(projectId) });
    },
  });
}

export function useGenerateDiagnosisDocx(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (runId: string) => generateDiagnosisDocx(projectId, runId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: diagnosisKeys.latest(projectId) });
    },
  });
}

export function useCreateDiagnosisStakeholder(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: StakeholderBody) =>
      createDiagnosisStakeholder(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: diagnosisKeys.stakeholdersList(projectId),
      });
    },
  });
}

export function useCreateDiagnosisProcess(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ProcessBody) => createDiagnosisProcess(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: diagnosisKeys.processesList(projectId),
      });
    },
  });
}

export function useCreateDiagnosisLegalObligation(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: LegalObligationBody) =>
      createDiagnosisLegalObligation(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: diagnosisKeys.legalObligationsList(projectId),
      });
    },
  });
}

export function useExportDiagnosisToMagerit(projectId: string) {
  return useMutation({
    mutationFn: (mageritAnalysisId: string) =>
      exportDiagnosisToMagerit(projectId, mageritAnalysisId),
  });
}
