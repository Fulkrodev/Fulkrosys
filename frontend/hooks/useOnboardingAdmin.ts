"use client";

/**
 * React Query hooks para Motor 16 admin perspective (SAN-E v3.MB-4.3 PARTE A).
 */

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  assignCourseToEmployee,
  cancelSession,
  createSession,
  exportCategorization,
  getCatalog,
  getProjectLMSProgress,
  getSessionDetail,
  getTemplateDetail,
  listExpiredSessions,
  listLMSCourses,
  listProjectConnectors,
  listProjectLMSAssignments,
  listProjectSessions,
  markSessionSent,
  validateConnector,
  type AssignCourseBody,
  type CreateSessionBody,
} from "@/lib/admin-onboarding/api";

// =====================================================================
// Centralized keys
// =====================================================================

export const onboardingAdminKeys = {
  all: () => ["onboarding-admin"] as const,
  catalog: () => ["onboarding-admin", "catalog"] as const,
  template: (id: string) => ["onboarding-admin", "template", id] as const,
  sessions: (projectId: string) =>
    ["onboarding-admin", "sessions", projectId] as const,
  sessionsExpired: (projectId: string) =>
    ["onboarding-admin", "sessions-expired", projectId] as const,
  sessionDetail: (sessionId: string) =>
    ["onboarding-admin", "session", sessionId] as const,
  connectors: (projectId: string) =>
    ["onboarding-admin", "connectors", projectId] as const,
  lmsCourses: () => ["onboarding-admin", "lms-courses"] as const,
  lmsAssignments: (projectId: string) =>
    ["onboarding-admin", "lms-assignments", projectId] as const,
  lmsProgress: (projectId: string) =>
    ["onboarding-admin", "lms-progress", projectId] as const,
};

// =====================================================================
// Queries
// =====================================================================

export function useOnboardingCatalog() {
  return useQuery({
    queryKey: onboardingAdminKeys.catalog(),
    queryFn: getCatalog,
    staleTime: 5 * 60 * 1000,
  });
}

export function useTemplateDetail(templateId: string | null) {
  return useQuery({
    queryKey: templateId
      ? onboardingAdminKeys.template(templateId)
      : ["onboarding-admin", "template", "_none"],
    queryFn: () => getTemplateDetail(templateId as string),
    enabled: !!templateId,
    staleTime: 5 * 60 * 1000,
  });
}

export function useProjectSessions(projectId: string) {
  return useQuery({
    queryKey: onboardingAdminKeys.sessions(projectId),
    queryFn: () => listProjectSessions(projectId),
    enabled: !!projectId,
  });
}

export function useExpiredSessions(projectId: string) {
  return useQuery({
    queryKey: onboardingAdminKeys.sessionsExpired(projectId),
    queryFn: () => listExpiredSessions(projectId),
    enabled: !!projectId,
  });
}

export function useSessionDetail(sessionId: string | null) {
  return useQuery({
    queryKey: sessionId
      ? onboardingAdminKeys.sessionDetail(sessionId)
      : ["onboarding-admin", "session", "_none"],
    queryFn: () => getSessionDetail(sessionId as string),
    enabled: !!sessionId,
  });
}

export function useProjectConnectors(projectId: string) {
  return useQuery({
    queryKey: onboardingAdminKeys.connectors(projectId),
    queryFn: () => listProjectConnectors(projectId),
    enabled: !!projectId,
  });
}

export function useLMSCourses() {
  return useQuery({
    queryKey: onboardingAdminKeys.lmsCourses(),
    queryFn: listLMSCourses,
    staleTime: 5 * 60 * 1000,
  });
}

export function useProjectLMSAssignments(projectId: string) {
  return useQuery({
    queryKey: onboardingAdminKeys.lmsAssignments(projectId),
    queryFn: () => listProjectLMSAssignments(projectId),
    enabled: !!projectId,
  });
}

export function useLMSProgress(projectId: string) {
  return useQuery({
    queryKey: onboardingAdminKeys.lmsProgress(projectId),
    queryFn: () => getProjectLMSProgress(projectId),
    enabled: !!projectId,
  });
}

// =====================================================================
// Mutations
// =====================================================================

export function useCreateSession(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateSessionBody) => createSession(projectId, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: onboardingAdminKeys.sessions(projectId) });
    },
  });
}

export function useCancelSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ sessionId, reason }: { sessionId: string; reason?: string }) =>
      cancelSession(sessionId, reason),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["onboarding-admin", "sessions"] });
    },
  });
}

export function useMarkSessionSent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: string) => markSessionSent(sessionId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["onboarding-admin", "sessions"] });
    },
  });
}

export function useValidateConnector(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (provider: string) => validateConnector(projectId, provider),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: onboardingAdminKeys.connectors(projectId) });
    },
  });
}

export function useAssignCourse(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: AssignCourseBody) => assignCourseToEmployee(projectId, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: onboardingAdminKeys.lmsAssignments(projectId) });
      void qc.invalidateQueries({ queryKey: onboardingAdminKeys.lmsProgress(projectId) });
    },
  });
}

export function useExportCategorization(projectId: string) {
  return useMutation({
    mutationFn: () => exportCategorization(projectId),
  });
}
