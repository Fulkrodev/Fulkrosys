"use client";

/**
 * useExitChecklist · TanStack Query hook (SAN-E v3.MB-3.1).
 *
 * Wraps lib/admin-exit/api con TanStack Query (consistente con
 * useClients hook · backend M25 exit-checklist endpoints).
 *
 * Patron mutaciones: mutate + invalidate queryKey ['exit-checklist', projectId]
 * tras success · refetch automatico de listado.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  type ExitChecklistResponse,
  type ExitReadiness,
  type ExitStatus,
  type LifecycleEvent,
  checkExitReadiness,
  completeExitItem,
  getExitChecklist,
  setExitItemStatus,
  transitionLifecycle,
  uncompleteExitItem,
} from "@/lib/admin-exit/api";

export const exitChecklistKey = (projectId: string) =>
  ["exit-checklist", projectId] as const;

export function useExitChecklist(projectId: string) {
  const qc = useQueryClient();

  const query = useQuery<ExitChecklistResponse>({
    queryKey: exitChecklistKey(projectId),
    queryFn: () => getExitChecklist(projectId),
    enabled: Boolean(projectId),
  });

  const invalidate = () =>
    qc.invalidateQueries({ queryKey: exitChecklistKey(projectId) });

  const completeMutation = useMutation({
    mutationFn: (vars: {
      itemId: string;
      evidence_id?: string | null;
      note?: string | null;
    }) =>
      completeExitItem(projectId, vars.itemId, {
        evidence_id: vars.evidence_id ?? null,
        note: vars.note ?? null,
      }),
    onSuccess: invalidate,
  });

  const uncompleteMutation = useMutation({
    mutationFn: (itemId: string) => uncompleteExitItem(projectId, itemId),
    onSuccess: invalidate,
  });

  const setStatusMutation = useMutation({
    mutationFn: (vars: {
      itemId: string;
      status: ExitStatus;
      note?: string | null;
    }) =>
      setExitItemStatus(projectId, vars.itemId, {
        status: vars.status,
        note: vars.note ?? null,
      }),
    onSuccess: invalidate,
  });

  const readinessMutation = useMutation<ExitReadiness, Error, void>({
    mutationFn: () => checkExitReadiness(projectId),
  });

  // S17 fix · cierre real del proyecto vía transición lifecycle M25.
  const closeProjectMutation = useMutation<
    LifecycleEvent,
    Error,
    { toState: string; reason?: string | null }
  >({
    mutationFn: (vars) =>
      transitionLifecycle(projectId, vars.toState, vars.reason ?? null),
    onSuccess: invalidate,
  });

  return {
    data: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
    completeItem: completeMutation,
    uncompleteItem: uncompleteMutation,
    setStatus: setStatusMutation,
    checkReadiness: readinessMutation,
    closeProject: closeProjectMutation,
  };
}
