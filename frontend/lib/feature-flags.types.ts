/**
 * Feature flags types (ADR-036 SAN-D MB-17.1) · espejo Pydantic backend.
 *
 * Values lowercase coinciden con `PymeArquetipo` enum real
 * (`backend/app/motors/m01_categorization/pyme_archetypes.py`).
 * Categorías ENS uppercase coinciden con `Project.categoria_objetivo`.
 */

export type EnsCategory = "BASICA" | "MEDIA" | "ALTA";

export type PymeArchetype =
  | "saas_only"
  | "teletrabajo_total"
  | "sector_salud"
  | "sector_educacion"
  | "desarrollador_aapp"
  | "proveedor_financiero"
  | "generico";

export type FeatureKey =
  // Categoría BÁSICA
  | "basica_autoevaluacion"
  // Categoría MEDIA+
  | "media_auditor_enac"
  | "media_auditoria_externa"
  | "refuerzos_r1"
  // Categoría ALTA
  | "alta_pentest_cpstic"
  | "alta_productos_cpstic"
  | "alta_criptografia_807"
  | "alta_red_team"
  | "alta_co_consultoria"
  | "refuerzos_r2_r3_r4"
  // Arquetipos
  | "art9_rgpd_data"
  | "pre_categorizacion_alta_salud"
  | "pce_universidades"
  | "cra_sdlc_seguro"
  | "dora_dual_compliance"
  | "skip_mp_if_instalaciones"
  | "ztna_mfa_obligatorio"
  // Mixtas
  | "pce_nis2";

export interface ProjectFeatureFlags {
  categoria: EnsCategory;
  archetype: PymeArchetype | null;
  employee_count: number | null;
  features: Record<FeatureKey, boolean>;
}

/**
 * Feature flag override types (ADR-046 · MB-10 Atom 10.2/10.3 · renamed post-audit B1.2 · was ADR-037 MB-10).
 *
 * Espejo de `backend/app/core/feature_flags/models.py::FeatureFlagOverride`
 * y schemas Pydantic en `backend/app/core/feature_flags/api.py`.
 *
 * Q5.3 cement sostained: estos types se usan SOLO en componentes admin
 * (`components/admin/feature-flags/*`). NUNCA cliente-facing.
 */

export interface FeatureFlagOverride {
  id: string;
  project_id: string | null;
  client_id: string | null;
  feature_key: string;
  override_value: unknown;
  granted_at: string;
  expires_at: string | null;
  granted_by_user_id: string | null;
  revoked_at: string | null;
  revoked_by_user_id: string | null;
  reason: string | null;
}

export interface GrantOverrideRequest {
  feature_key: string;
  override_value: unknown;
  project_id?: string | null;
  client_id?: string | null;
  expires_at?: string | null;
  reason?: string | null;
}

export interface RevokeOverrideRequest {
  reason?: string | null;
}
