/**
 * DiscrepanciasCriticalBadge · 1.D.A.B v3.10
 *
 * Badge inline rendered en ProjectTabs Discrepancias entry · cuenta
 * discrepancias open con severidad critical para draw attention admin.
 *
 * Patrón react-query lightweight con stale 60s (NO consume infra costoso).
 * Si data error / no critical · renderiza null (badge invisible).
 */
"use client";

import { useQuery } from "@tanstack/react-query";

import { agent21Api, type DiscrepancyOut } from "@/lib/api/agent-21";

export function DiscrepanciasCriticalBadge({
  projectId,
}: {
  projectId: string;
}) {
  const query = useQuery<DiscrepancyOut[]>({
    queryKey: ["a21", "discrepancies", projectId, "critical-badge"],
    queryFn: () =>
      agent21Api.listDiscrepancies(projectId, {
        resolutionStatus: "open",
        severity: "critical",
      }),
    enabled: Boolean(projectId),
    staleTime: 60_000,
    retry: false,
  });

  const criticalOpen = (query.data ?? []).length;
  if (criticalOpen === 0) return null;

  return (
    <span
      aria-label={`${criticalOpen} discrepancias críticas abiertas`}
      className="ml-1 inline-flex min-w-[1.25rem] items-center justify-center rounded-full bg-red-600 px-1.5 text-[11px] font-bold text-white"
    >
      {criticalOpen}
    </span>
  );
}
