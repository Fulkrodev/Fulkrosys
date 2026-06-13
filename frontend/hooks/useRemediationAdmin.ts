"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  type CreateRemediationJobBody,
  remediationAdminApi,
} from "@/lib/api/remediation-admin";

const KEY = (projectId: string) => ["remediation", "admin", projectId] as const;

export function useRemediationCatalog(projectId: string) {
  return useQuery({
    queryKey: [...KEY(projectId), "catalog"],
    queryFn: () => remediationAdminApi.catalog(projectId),
    staleTime: 5 * 60_000,
  });
}

export function useRemediationJobs(projectId: string, status?: string) {
  return useQuery({
    queryKey: [...KEY(projectId), "jobs", status ?? "all"],
    queryFn: () => remediationAdminApi.listJobs(projectId, status),
    staleTime: 10_000,
  });
}

export function useRemediationConnectors(projectId: string) {
  return useQuery({
    queryKey: [...KEY(projectId), "connectors"],
    queryFn: () => remediationAdminApi.listConnectors(projectId),
    staleTime: 60_000,
  });
}

function useInvalidateJobs(projectId: string) {
  const qc = useQueryClient();
  return () =>
    qc.invalidateQueries({ queryKey: [...KEY(projectId), "jobs"] });
}

export function useCreateRemediationJob(projectId: string) {
  const invalidate = useInvalidateJobs(projectId);
  return useMutation({
    mutationFn: (body: CreateRemediationJobBody) =>
      remediationAdminApi.createJob(projectId, body),
    onSuccess: () => void invalidate(),
  });
}

export function useAuthorizeRemediationJob(projectId: string) {
  const invalidate = useInvalidateJobs(projectId);
  return useMutation({
    mutationFn: (jobId: string) =>
      remediationAdminApi.authorize(projectId, jobId),
    onSuccess: () => void invalidate(),
  });
}

export function useExecuteRemediationJob(projectId: string) {
  const invalidate = useInvalidateJobs(projectId);
  return useMutation({
    mutationFn: (jobId: string) =>
      remediationAdminApi.execute(projectId, jobId),
    onSuccess: () => void invalidate(),
  });
}
