/**
 * API client cliente · M01 Categorización sync admin → cliente.
 *
 * Sesión 3B-2B.8 CLUSTER 1 Phase 1A · cliente reads project categorización
 * (READ-ONLY · admin owns write). audit_log emit cliente.categorizacion.viewed
 * automatic backend (project_id + client_id Sub-atom 5.A pattern).
 *
 * ADR-013 doble pool · /client-portal/* prefix cliente · NO admin endpoints.
 */
import { api } from "@/lib/api";

const BASE = "/api/v1/client-portal/categorizacion";

export interface ClientCategorizacionSystem {
  id: string;
  nombre: string;
  descripcion: string | null;
  categorization_id: string | null;
  categoria_resultante: "BASICA" | "MEDIA" | "ALTA" | string | null;
  fecha_acta: string | null;
  aprobado_por: string | null;
  created_at: string | null;
}

export interface ClientCategorizacionResponse {
  project_id: string;
  project_nombre: string;
  categoria_objetivo: "BASICA" | "MEDIA" | "ALTA" | string | null;
  systems: ClientCategorizacionSystem[];
  last_updated_at: string | null;
  total_systems: number;
  categorized_systems: number;
}

export async function getClientCategorizacion(): Promise<ClientCategorizacionResponse> {
  return api<ClientCategorizacionResponse>(BASE);
}

// ══════════════════════════════════════════════════════════════════════
// UI helpers
// ══════════════════════════════════════════════════════════════════════

export const CATEGORIA_LABEL: Record<string, string> = {
  BASICA: "Básica",
  MEDIA: "Media",
  ALTA: "Alta",
};

export const CATEGORIA_VARIANT: Record<
  string,
  "secondary" | "warning" | "success"
> = {
  BASICA: "secondary",
  MEDIA: "warning",
  ALTA: "success",
};
