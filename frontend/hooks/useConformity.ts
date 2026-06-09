"use client";

/**
 * React Query hooks para Motor 27 - Conformity Lifecycle.
 *
 * 0 mocks. Todos los hooks invocan endpoints reales del backend
 * (14 en /api/v1/conformity + 15 en /api/v1/projects/{id}/conformity = 29 totales).
 *
 * Reemplaza `useConformity` que vivía en `useSprint5Data.ts` (eliminado en 9.A.3).
 */
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  applyOverlay,
  claraIngest,
  createExternalExport,
  createSubmission,
  detectOverlay,
  generateDeclaration,
  generateRoleTopology,
  getConformityStatusLifecycle,
  getConformityStatusPaso5,
  getRenewal,
  getRoleTopology,
  getRouteHistory,
  inesSnapshot,
  initializeConformity,
  listConformitySubmissions,
  listExternalExports,
  listMaterialChanges,
  lockRoute,
  pilarExportMgr,
  prepareEnacCertification,
  recategorize,
  registerMaterialChange,
  revalidateRoute,
  startRenewal,
  submitBasicDeclaration,
  submitSubmissionProof,
  triggerRenewal,
  uploadExportProof,
  validateOverlay,
  type ApplyOverlayBody,
  type BasicDeclarationBody,
  type CategoryLevel,
  type ClaraIngestBody,
  type DeclarationGenerateBody,
  type EnacCertificationBody,
  type ExternalExportCreateBody,
  type InitializeRouteBody,
  type MaterialChangeBody,
  type RecategorizeBody,
  type RoleTopologyGenerateBody,
  type RouteLockBody,
  type SubmissionCreateBody,
  type SubmissionProofBody,
} from "@/lib/api/conformity";

// =====================================================================
// Keys centralizadas
// =====================================================================

export const conformityKeys = {
  all: () => ["conformity"] as const,
  // Lifecycle (api.py)
  status: (projectId: string) =>
    ["conformity", "status", projectId] as const,
  routeHistory: (projectId: string) =>
    ["conformity", "route-history", projectId] as const,
  renewal: (projectId: string) =>
    ["conformity", "renewal", projectId] as const,
  externalExports: (projectId: string) =>
    ["conformity", "external-exports", projectId] as const,
  overlay: (projectId: string, sector: string, category: CategoryLevel) =>
    ["conformity", "pce-overlay", projectId, sector, category] as const,
  // Paso 5 (api_paso5.py)
  statusPaso5: (projectId: string) =>
    ["conformity", "paso5-status", projectId] as const,
  materialChanges: (projectId: string) =>
    ["conformity", "material-changes", projectId] as const,
  roleTopology: (projectId: string) =>
    ["conformity", "role-topology", projectId] as const,
  submissionsList: (projectId: string) =>
    ["conformity", "submissions-list", projectId] as const,
};

// =====================================================================
// Queries
// =====================================================================

/** Hook principal: estado lifecycle conformidad ENS para un proyecto. */
export function useConformity(projectId: string) {
  return useQuery({
    queryKey: conformityKeys.status(projectId),
    queryFn: () => getConformityStatusLifecycle(projectId),
    enabled: !!projectId,
  });
}

export function useConformityStatusPaso5(projectId: string) {
  return useQuery({
    queryKey: conformityKeys.statusPaso5(projectId),
    queryFn: () => getConformityStatusPaso5(projectId),
    enabled: !!projectId,
  });
}

export function useRouteHistory(projectId: string) {
  return useQuery({
    queryKey: conformityKeys.routeHistory(projectId),
    queryFn: () => getRouteHistory(projectId),
    enabled: !!projectId,
  });
}

export function useRenewal(projectId: string) {
  return useQuery({
    queryKey: conformityKeys.renewal(projectId),
    queryFn: () => getRenewal(projectId),
    enabled: !!projectId,
  });
}

export function useExternalExports(projectId: string) {
  return useQuery({
    queryKey: conformityKeys.externalExports(projectId),
    queryFn: () => listExternalExports(projectId),
    enabled: !!projectId,
  });
}

export function useDetectOverlay(
  projectId: string,
  sector = "generico",
  category: CategoryLevel = "BASICA",
) {
  return useQuery({
    queryKey: conformityKeys.overlay(projectId, sector, category),
    queryFn: () => detectOverlay(projectId, sector, category),
    enabled: !!projectId,
  });
}

export function useMaterialChanges(projectId: string) {
  return useQuery({
    queryKey: conformityKeys.materialChanges(projectId),
    queryFn: () => listMaterialChanges(projectId),
    enabled: !!projectId,
  });
}

export function useRoleTopology(projectId: string) {
  return useQuery({
    queryKey: conformityKeys.roleTopology(projectId),
    queryFn: () => getRoleTopology(projectId),
    enabled: !!projectId,
    retry: false, // 404 if not generated yet
  });
}

export function useConformitySubmissionsList(projectId: string) {
  return useQuery({
    queryKey: conformityKeys.submissionsList(projectId),
    queryFn: () => listConformitySubmissions(projectId),
    enabled: !!projectId,
  });
}

// =====================================================================
// Mutations - Lifecycle (api.py)
// =====================================================================

export function useLockRoute(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: RouteLockBody) => lockRoute(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: conformityKeys.status(projectId) });
      qc.invalidateQueries({
        queryKey: conformityKeys.routeHistory(projectId),
      });
    },
  });
}

export function useRevalidateRoute(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => revalidateRoute(projectId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: conformityKeys.status(projectId) });
      qc.invalidateQueries({
        queryKey: conformityKeys.routeHistory(projectId),
      });
    },
  });
}

export function useGenerateDeclaration(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: DeclarationGenerateBody) =>
      generateDeclaration(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: conformityKeys.status(projectId) });
    },
  });
}

export function useCreateSubmission(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: SubmissionCreateBody) =>
      createSubmission(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: conformityKeys.status(projectId) });
      qc.invalidateQueries({
        queryKey: conformityKeys.submissionsList(projectId),
      });
    },
  });
}

export function useSubmitProof(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      sid,
      body,
    }: {
      sid: string;
      body: SubmissionProofBody;
    }) => submitSubmissionProof(projectId, sid, body),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: conformityKeys.submissionsList(projectId),
      });
    },
  });
}

export function useStartRenewal(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (targetDate: string) => startRenewal(projectId, targetDate),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: conformityKeys.renewal(projectId) });
    },
  });
}

export function useCreateExternalExport(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ExternalExportCreateBody) =>
      createExternalExport(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: conformityKeys.externalExports(projectId),
      });
    },
  });
}

export function useUploadExportProof(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      eid,
      proofReference,
    }: {
      eid: string;
      proofReference: string;
    }) => uploadExportProof(projectId, eid, proofReference),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: conformityKeys.externalExports(projectId),
      });
    },
  });
}

export function useValidateOverlay(projectId: string) {
  return useMutation({
    mutationFn: ({
      overlayCode,
      projectCategory,
    }: {
      overlayCode: string;
      projectCategory: string;
    }) => validateOverlay(projectId, overlayCode, projectCategory),
  });
}

// =====================================================================
// Mutations - Paso 5 (api_paso5.py)
// =====================================================================

export function useInitializeConformity(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: InitializeRouteBody = {}) =>
      initializeConformity(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: conformityKeys.statusPaso5(projectId) });
      qc.invalidateQueries({ queryKey: conformityKeys.status(projectId) });
    },
  });
}

export function useSubmitBasicDeclaration(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: BasicDeclarationBody) =>
      submitBasicDeclaration(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: conformityKeys.statusPaso5(projectId) });
    },
  });
}

export function usePrepareEnacCertification(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: EnacCertificationBody) =>
      prepareEnacCertification(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: conformityKeys.statusPaso5(projectId) });
    },
  });
}

export function useRegisterMaterialChange(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: MaterialChangeBody) =>
      registerMaterialChange(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: conformityKeys.materialChanges(projectId),
      });
      qc.invalidateQueries({ queryKey: conformityKeys.statusPaso5(projectId) });
    },
  });
}

export function useRecategorize(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: RecategorizeBody) => recategorize(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: conformityKeys.statusPaso5(projectId) });
    },
  });
}

export function useApplyOverlay(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ApplyOverlayBody) => applyOverlay(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: conformityKeys.statusPaso5(projectId) });
    },
  });
}

export function useGenerateRoleTopology(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: RoleTopologyGenerateBody) =>
      generateRoleTopology(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: conformityKeys.roleTopology(projectId),
      });
    },
  });
}

export function useTriggerRenewal(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (auto: boolean = true) => triggerRenewal(projectId, auto),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: conformityKeys.renewal(projectId) });
      qc.invalidateQueries({ queryKey: conformityKeys.statusPaso5(projectId) });
    },
  });
}

export function usePilarExportMgr(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => pilarExportMgr(projectId),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: conformityKeys.externalExports(projectId),
      });
    },
  });
}

export function useInesSnapshot(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (year?: number) => inesSnapshot(projectId, year),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: conformityKeys.externalExports(projectId),
      });
    },
  });
}

export function useClaraIngest(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ClaraIngestBody) => claraIngest(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: conformityKeys.statusPaso5(projectId) });
    },
  });
}