"use client";

/**
 * React Query hooks Motor 3 — DdA (FASE 9.D · UX gate GenerateDocumentButton).
 *
 * Surface mínima · 1 query para status. Si crece scope DdA en frontend
 * (visualizar entries, freeze flow, etc) ampliar aquí siguiendo pattern
 * de useEvidence.ts.
 *
 * 0 mocks. Todos los hooks invocan endpoints reales del backend.
 */
import { useQuery } from "@tanstack/react-query";

import { getDdaStatus, type DdaStatusResponse } from "@/lib/api/dda";

// ─── Keys centralizadas ─────────────────────────────────────────────

export const ddaKeys = {
  all: (projectId: string) => ["dda", projectId] as const,
  status: (projectId: string) => ["dda", projectId, "status"] as const,
};

// ─── Queries ────────────────────────────────────────────────────────

/**
 * Estado del DdA del proyecto · FASE 9.D · TODO-FASE-9-DDA-GATE-UX-001.
 *
 * Usado por GenerateDocumentButton para decidir si habilita la generación
 * de políticas/procedimientos/entregables (categoría que requiere DdA
 * congelado en backend workflow_gates.require_frozen_dda_if_needed).
 *
 * staleTime 30s · el flow congelar DdA es manual (RSEG firma E-040), no
 * requiere refetch agresivo.
 */
export function useDdaStatus(projectId: string) {
  return useQuery<DdaStatusResponse>({
    queryKey: ddaKeys.status(projectId),
    queryFn: () => getDdaStatus(projectId),
    enabled: !!projectId,
    staleTime: 30_000,
  });
}
