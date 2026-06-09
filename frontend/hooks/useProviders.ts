"use client";

/**
 * useProviders · TanStack Query hook (SAN-E v3.MB-3.3).
 *
 * 3 queries (list · c002-status · gaps) + 5 mutations (create · delete ·
 * generateC002 · markReviewed · refresh-gaps) auto-invalidate.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  type CreateProviderPayload,
  type ProvidersListResponse,
  type C002StatusResponse,
  type ProviderGapsResponse,
  createProvider,
  deleteProvider,
  generateC002,
  getC002Status,
  getProviderGaps,
  listProviders,
  markProviderReviewed,
} from "@/lib/admin-providers/api";

export const providersKey = (projectId: string) =>
  ["providers", projectId] as const;
export const c002Key = (projectId: string, providerId: string) =>
  ["provider-c002", projectId, providerId] as const;
export const gapsKey = (projectId: string, providerId: string) =>
  ["provider-gaps", projectId, providerId] as const;

export function useProviders(projectId: string) {
  const qc = useQueryClient();

  const list = useQuery<ProvidersListResponse>({
    queryKey: providersKey(projectId),
    queryFn: () => listProviders(projectId),
    enabled: Boolean(projectId),
  });

  const invalidateAll = () => {
    qc.invalidateQueries({ queryKey: providersKey(projectId) });
  };

  const invalidateProvider = (providerId: string) => {
    qc.invalidateQueries({ queryKey: c002Key(projectId, providerId) });
    qc.invalidateQueries({ queryKey: gapsKey(projectId, providerId) });
    invalidateAll();
  };

  const createMutation = useMutation({
    mutationFn: (payload: CreateProviderPayload) =>
      createProvider(projectId, payload),
    onSuccess: invalidateAll,
  });

  const deleteMutation = useMutation({
    mutationFn: (providerId: string) => deleteProvider(projectId, providerId),
    onSuccess: invalidateAll,
  });

  const generateC002Mutation = useMutation({
    mutationFn: (providerId: string) => generateC002(projectId, providerId),
    onSuccess: (_data, providerId) => invalidateProvider(providerId),
  });

  const markReviewedMutation = useMutation({
    mutationFn: (providerId: string) =>
      markProviderReviewed(projectId, providerId),
    onSuccess: invalidateAll,
  });

  return {
    list,
    create: createMutation,
    remove: deleteMutation,
    generateC002: generateC002Mutation,
    markReviewed: markReviewedMutation,
  };
}

export function useProviderC002Status(
  projectId: string,
  providerId: string | null,
) {
  return useQuery<C002StatusResponse>({
    queryKey: c002Key(projectId, providerId ?? ""),
    queryFn: () => getC002Status(projectId, providerId ?? ""),
    enabled: Boolean(projectId && providerId),
  });
}

export function useProviderGaps(
  projectId: string,
  providerId: string | null,
) {
  return useQuery<ProviderGapsResponse>({
    queryKey: gapsKey(projectId, providerId ?? ""),
    queryFn: () => getProviderGaps(projectId, providerId ?? ""),
    enabled: Boolean(projectId && providerId),
  });
}
