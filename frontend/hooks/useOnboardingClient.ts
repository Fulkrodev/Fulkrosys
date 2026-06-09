"use client";

/**
 * React Query hooks para Motor 16 cliente in-portal (SAN-E v3.MB-4.3 PARTE B).
 */

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  awsCredentials,
  completeLMSAssignment,
  finishOnboarding,
  getNextQuestion,
  getOnboardingStatus,
  listPortalConnectors,
  listPortalLMS,
  oauthCallback,
  oauthInit,
  submitAnswer,
  syncConnector,
  type AWSCredentialsBody,
} from "@/lib/client-onboarding/api";

// =====================================================================
// Centralized keys
// =====================================================================

export const onboardingClientKeys = {
  all: () => ["onboarding-client"] as const,
  status: (projectId: string) =>
    ["onboarding-client", "status", projectId] as const,
  nextQuestion: (projectId: string) =>
    ["onboarding-client", "next-question", projectId] as const,
  connectors: (projectId: string) =>
    ["onboarding-client", "connectors", projectId] as const,
  lms: (projectId: string) =>
    ["onboarding-client", "lms", projectId] as const,
};

// =====================================================================
// Queries
// =====================================================================

export function usePortalStatus(projectId: string) {
  return useQuery({
    queryKey: onboardingClientKeys.status(projectId),
    queryFn: () => getOnboardingStatus(projectId),
    enabled: !!projectId,
    staleTime: 10_000,
  });
}

export function useNextQuestion(projectId: string) {
  return useQuery({
    queryKey: onboardingClientKeys.nextQuestion(projectId),
    queryFn: () => getNextQuestion(projectId),
    enabled: !!projectId,
  });
}

export function usePortalConnectors(projectId: string) {
  return useQuery({
    queryKey: onboardingClientKeys.connectors(projectId),
    queryFn: () => listPortalConnectors(projectId),
    enabled: !!projectId,
  });
}

export function usePortalLMS(projectId: string) {
  return useQuery({
    queryKey: onboardingClientKeys.lms(projectId),
    queryFn: () => listPortalLMS(projectId),
    enabled: !!projectId,
  });
}

// =====================================================================
// Mutations
// =====================================================================

export function useSubmitAnswer(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { question_id: string; answer: unknown }) =>
      submitAnswer(projectId, payload),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: onboardingClientKeys.status(projectId) });
      void qc.invalidateQueries({ queryKey: onboardingClientKeys.nextQuestion(projectId) });
    },
  });
}

export function useOAuthInit(projectId: string) {
  return useMutation({
    mutationFn: ({
      connectorType,
      redirectUri,
    }: {
      connectorType: string;
      redirectUri: string;
    }) => oauthInit(projectId, connectorType, { redirect_uri: redirectUri }),
  });
}

export function useOAuthCallback(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      connectorType,
      code,
      state,
    }: {
      connectorType: string;
      code: string;
      state: string;
    }) => oauthCallback(projectId, connectorType, { code, state }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: onboardingClientKeys.connectors(projectId) });
    },
  });
}

export function useAWSCredentials(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: AWSCredentialsBody) => awsCredentials(projectId, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: onboardingClientKeys.connectors(projectId) });
    },
  });
}

export function useSyncConnector(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (connectorType: string) => syncConnector(projectId, connectorType),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: onboardingClientKeys.connectors(projectId) });
    },
  });
}

export function useCompleteLMS(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (assignmentId: string) => completeLMSAssignment(projectId, assignmentId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: onboardingClientKeys.lms(projectId) });
    },
  });
}

export function useFinishOnboarding(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => finishOnboarding(projectId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: onboardingClientKeys.status(projectId) });
    },
  });
}
