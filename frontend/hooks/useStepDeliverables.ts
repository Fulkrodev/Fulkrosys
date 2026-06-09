"use client";

/**
 * useStepDeliverables · sub-atom 1.C.D.D.2 v3.8.
 *
 * tanstack-query wrapper · GET workflow-engine/steps/{template_id}/deliverables
 * Reusable admin + cliente via ApiMode param.
 */
import { useQuery } from "@tanstack/react-query";

import {
  listStepDeliverables,
  type ApiMode,
  type StepDeliverablesResponse,
} from "@/lib/api/workflow-deliverables";

const STALE_TIME = 30_000;

export function useStepDeliverables(
  projectId: string | null,
  templateId: string | null,
  mode: ApiMode = "admin",
) {
  return useQuery<StepDeliverablesResponse>({
    queryKey: ["step-deliverables", projectId, templateId, mode],
    queryFn: () =>
      listStepDeliverables(projectId as string, templateId as string, mode),
    enabled: Boolean(projectId) && Boolean(templateId),
    staleTime: STALE_TIME,
    refetchOnWindowFocus: false,
  });
}
