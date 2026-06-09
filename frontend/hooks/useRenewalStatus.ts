"use client";

/**
 * useRenewalStatus · TanStack Query hook (SAN-E v3.MB-3.4).
 *
 * 3 queries (timeline · auditor-info · drift-summary) + 1 mutation
 * (contact-auditor). Auto-invalidate timeline + auditor-info tras
 * contactAuditor success.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  type AuditorInfoResponse,
  type ContactAuditorPayload,
  type DriftSummaryResponse,
  type RenewalTimelineResponse,
  contactAuditor,
  getAuditorInfo,
  getDriftSummary,
  getRenewalTimeline,
} from "@/lib/admin-renewal/api";

export const renewalTimelineKey = (projectId: string) =>
  ["renewal-timeline", projectId] as const;
export const auditorInfoKey = (projectId: string) =>
  ["renewal-auditor-info", projectId] as const;
export const driftSummaryKey = (projectId: string) =>
  ["drift-summary", projectId] as const;

export function useRenewalStatus(projectId: string) {
  const qc = useQueryClient();

  const timeline = useQuery<RenewalTimelineResponse>({
    queryKey: renewalTimelineKey(projectId),
    queryFn: () => getRenewalTimeline(projectId),
    enabled: Boolean(projectId),
  });

  const auditor = useQuery<AuditorInfoResponse>({
    queryKey: auditorInfoKey(projectId),
    queryFn: () => getAuditorInfo(projectId),
    enabled: Boolean(projectId),
  });

  const drift = useQuery<DriftSummaryResponse>({
    queryKey: driftSummaryKey(projectId),
    queryFn: () => getDriftSummary(projectId),
    enabled: Boolean(projectId),
  });

  const contactAuditorMutation = useMutation({
    mutationFn: (payload: ContactAuditorPayload) =>
      contactAuditor(projectId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: renewalTimelineKey(projectId) });
      qc.invalidateQueries({ queryKey: auditorInfoKey(projectId) });
    },
  });

  return {
    timeline,
    auditor,
    drift,
    contactAuditor: contactAuditorMutation,
  };
}
