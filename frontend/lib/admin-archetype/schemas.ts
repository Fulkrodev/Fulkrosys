/**
 * Admin Archetype schemas TypeScript (SAN-C MB-11.6).
 *
 * Espejo de backend/app/motors/m01_categorization/pyme_archetypes.py.
 * Mantener sincronizado manualmente al cambiar enum o adjustments.
 */

export const PYME_ARQUETIPOS = [
  "saas_only",
  "teletrabajo_total",
  "sector_salud",
  "sector_educacion",
  "desarrollador_aapp",
  "proveedor_financiero",
  "generico",
] as const;

export type PymeArquetipo = (typeof PYME_ARQUETIPOS)[number];

export const ARQUETIPO_LABELS: Record<PymeArquetipo, string> = {
  saas_only: "100% SaaS",
  teletrabajo_total: "Teletrabajo total",
  sector_salud: "Sector salud",
  sector_educacion: "Sector educación",
  desarrollador_aapp: "Desarrollador AAPP",
  proveedor_financiero: "Proveedor financiero",
  generico: "Genérico",
};

export interface ArchetypeAdjustments {
  skip_marcos: string[];
  highlight_marcos: string[];
  notes: string;
}

export interface ArchetypeResponse {
  archetype: PymeArquetipo;
  confidence: number;
  reasoning_path: string[];
  adjustments: ArchetypeAdjustments;
}

export interface ClassifyArchetypeRequest {
  cnae_code?: string;
  sector?: string;
  infrastructure_type?: "saas_only" | "on_prem" | "hybrid";
  workforce_type?: "fully_remote" | "hybrid" | "on_site";
  is_aapp_developer?: boolean;
}
