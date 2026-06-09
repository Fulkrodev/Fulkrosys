"use client";

/**
 * useClientWorkflowGuide · sub-atom 1.C.D.C.1 v3.8.
 *
 * Wrapper tanstack-query · GET workflow-guide subset friendly cliente.
 * STALE_TIME 60s · cliente UX calmer (NO 30s polling agresivo admin).
 *
 * R29 sostenido · NO polling agresivo cada 30s · cliente avanza a su ritmo.
 */
import { useQuery } from "@tanstack/react-query";

import {
  clientWorkflowGuideApi,
  type WorkflowGuideResponse,
} from "@/lib/api/client-workflow-guide";

const STALE_60S = 60_000;

export function useClientWorkflowGuide(projectId: string | null) {
  return useQuery<WorkflowGuideResponse>({
    queryKey: ["client-workflow-guide", projectId],
    queryFn: () => clientWorkflowGuideApi.get(projectId as string),
    enabled: Boolean(projectId),
    staleTime: STALE_60S,
    refetchOnWindowFocus: false,
  });
}
