"use client";

/**
 * React Query hooks para M8 Autopilot (doc §13-§14).
 *
 * 0 mocks. Todos los hooks invocan endpoints reales bajo
 * /api/v1/projects/{id}/verification/* (wrapper `api` admin · OPS-044).
 *
 * Polling pattern espejo de `useMCPExecution`: refetchInterval 2000ms MIENTRAS
 * autopilot_status ∈ {authorized, running} · stop en completed/partial/failed/
 * paused_gate2 (estados terminales o que requieren intervención humana).
 */
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  acceptRisk,
  attestRun,
  getAutopilotMetrics,
  getAutopilotStatus,
  getEvidencePack,
  startAutopilot,
  type AcceptRiskBody,
  type AttestBody,
  type AutopilotStartBody,
  type AutopilotStatus,
  type AutopilotStatusResponse,
} from "@/lib/api/autopilot";

// ─── Keys centralizadas ─────────────────────────────────────────────

export const autopilotKeys = {
  all: (projectId: string) => ["autopilot", projectId] as const,
  status: (projectId: string, runId: string | null) =>
    ["autopilot", projectId, "status", runId ?? "latest"] as const,
  metrics: (projectId: string) =>
    ["autopilot", projectId, "metrics"] as const,
  evidencePack: (projectId: string, runId: string) =>
    ["autopilot", projectId, "evidence-pack", runId] as const,
};

/** Estados en los que el autopilot sigue progresando → seguir poll. */
const ACTIVE_STATUSES: AutopilotStatus[] = ["authorized", "running"];

// ─── Queries ────────────────────────────────────────────────────────

/**
 * Estado live del autopilot · polling 2s mientras autorizado/ejecutando.
 * Se detiene en estados terminales o que requieren intervención (Gate 2).
 */
export function useAutopilotStatus(
  projectId: string,
  runId: string | null = null,
  enabled = true,
) {
  return useQuery<AutopilotStatusResponse>({
    queryKey: autopilotKeys.status(projectId, runId),
    queryFn: () => getAutopilotStatus(projectId, runId),
    enabled: enabled && Boolean(projectId),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 2000;
      return ACTIVE_STATUSES.includes(data.autopilot_status) ? 2000 : false;
    },
    // 404 = aún no hay runs · no spamear retries.
    retry: false,
  });
}

/** Observabilidad (§12) · refresh 30s para ver coverage/FP-rate/drift evolucionar. */
export function useAutopilotMetrics(projectId: string, enabled = true) {
  return useQuery({
    queryKey: autopilotKeys.metrics(projectId),
    queryFn: () => getAutopilotMetrics(projectId),
    enabled: enabled && Boolean(projectId),
    staleTime: 30_000,
    refetchInterval: 30_000,
  });
}

/** Pack de evidencia ENAC (§16) · estático por run completado. */
export function useEvidencePack(
  projectId: string,
  runId: string | null,
  enabled = true,
) {
  return useQuery({
    queryKey: autopilotKeys.evidencePack(projectId, runId ?? ""),
    queryFn: () => getEvidencePack(projectId, runId as string),
    enabled: enabled && Boolean(projectId && runId),
    staleTime: 5 * 60 * 1000,
  });
}

// ─── Mutations ──────────────────────────────────────────────────────

/** Gate 1 superado → "Continuar": lanza el autopilot. */
export function useStartAutopilot(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: AutopilotStartBody) => startAutopilot(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: autopilotKeys.all(projectId) });
    },
  });
}

/** Aceptación de riesgo de un finding (§8). */
export function useAcceptRisk(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      findingId,
      body,
    }: {
      findingId: string;
      body: AcceptRiskBody;
    }) => acceptRisk(projectId, findingId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: autopilotKeys.all(projectId) });
    },
  });
}

/** Gate 2 atestación (Alto · §14). */
export function useAttestRun(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ runId, body }: { runId: string; body: AttestBody }) =>
      attestRun(projectId, runId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: autopilotKeys.all(projectId) });
    },
  });
}
