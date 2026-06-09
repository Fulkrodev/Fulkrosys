/**
 * Admin API client · cloud-connectors (sub-atom 1.D.X.J v3.12).
 *
 * Endpoints servidos (backend m_cloud_connectors.api):
 *   GET    /api/v1/admin/projects/{pid}/cloud-connectors                       · list
 *   POST   /api/v1/admin/projects/{pid}/cloud-connectors                       · link M16 → connector
 *   POST   /api/v1/admin/projects/{pid}/cloud-connectors/{cid}/sync            · trigger sync
 *   GET    /api/v1/admin/projects/{pid}/cloud-connectors/{cid}/resources       · browse
 *   GET    /api/v1/admin/projects/{pid}/cloud-connectors/{cid}/sync-jobs       · history
 *   DELETE /api/v1/admin/projects/{pid}/cloud-connectors/{cid}                 · revoke
 *   GET    /api/v1/admin/projects/{pid}/cloud-gaps                             · list gaps
 *   POST   /api/v1/admin/projects/{pid}/cloud-gaps/{gid}/resolve               · resolve
 *   POST   /api/v1/admin/projects/{pid}/cloud-diagnosis/run                    · run engine
 *   GET    /api/v1/cloud-connectors/providers/catalog                          · catalog
 *   GET    /api/v1/cloud-connectors/supported-measures                         · catalog ENS
 *
 * R23 sostener firmísimo · TODO project-scoped (directiva Marcos).
 */
import { api } from "@/lib/api";

const BASE = "/api/v1";

export interface CloudConnectorAdmin {
  id: string;
  project_id: string;
  provider: string;
  status: string;
  m16_connector_config_id: string | null;
  scopes: string | null;
  last_sync_at: string | null;
  last_sync_resources_count: number;
  revoked_at: string | null;
  metadata_extra: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface CloudResource {
  id: string;
  project_id: string;
  connector_id: string;
  resource_type: string;
  resource_external_id: string;
  resource_name: string | null;
  attributes: Record<string, unknown>;
  checksum: string | null;
  detected_at: string;
  last_seen_at: string;
}

export interface CloudGap {
  id: string;
  project_id: string;
  connector_id: string | null;
  gap_type: string;
  severity: string;
  ens_measure_code: string;
  title: string;
  explanation_es: string | null;
  suggested_action: string | null;
  estimated_effort_days: number | null;
  auto_fixable: boolean;
  cliente_can_see: boolean;
  resolved_at: string | null;
  resolution_note: string | null;
  evidence_link_id: string | null;
  detected_at: string;
}

export interface CloudSyncJob {
  id: string;
  project_id: string;
  connector_id: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  resources_count: number;
  errors_jsonb: Record<string, unknown> | null;
  triggered_by: string;
}

export interface CloudProviderCatalogItem {
  provider: string;
  display_name: string;
  icon_emoji: string;
  requires_oauth: boolean;
  cliente_friendly_blurb: string;
}

export interface DiagnosisReport {
  project_id: string;
  category: string | null;
  rules_evaluated: number;
  findings_emitted: number;
  gaps_created: number;
  gaps_updated: number;
  gaps_resolved: number;
  gap_codes: string[];
  no_cloud_data: boolean;
}

export interface DigestSnapshot {
  id: string;
  project_id: string;
  generated_at: string;
  triggered_by: string;  // 'celery_monthly' | 'admin_manual'
  triggered_by_user_id: string | null;
  compliance_score: number;
  open_gaps_total: number;
  open_gaps_by_severity: Record<string, number>;
  snapshot_jsonb: Record<string, unknown>;
}

export interface DigestGenerateResponse {
  snapshot: DigestSnapshot;
  message: string;
}

export type ConsolidatedProvenance = "manual" | "cloud" | "both";

export interface ConsolidatedAsset {
  name: string;
  resource_type_normalized: string;
  provenance: ConsolidatedProvenance;
  criticidad: string | null;
  provider: string | null;
  manual_asset_id: string | null;
  cloud_resource_id: string | null;
  cloud_attributes: Record<string, unknown> | null;
}

export interface DiscoveryConsolidatedResponse {
  project_id: string;
  assets: ConsolidatedAsset[];
  counts: {
    manual_only: number;
    cloud_only: number;
    both: number;
    total: number;
  };
}

export const PROVENANCE_LABEL: Record<ConsolidatedProvenance, string> = {
  manual: "Manual",
  cloud: "Cloud detected",
  both: "Consolidado",
};

export const PROVENANCE_VARIANT: Record<ConsolidatedProvenance, "default" | "info" | "success"> = {
  manual: "default",
  cloud: "info",
  both: "success",
};

export interface EnrichedMageritAsset {
  asset_id: string;
  analysis_id: string;
  code: string;
  name: string;
  asset_type_code: string;
  value_d: number | null;
  value_i: number | null;
  value_c: number | null;
  value_a: number | null;
  value_t: number | null;
  cloud_verified: boolean;
  cloud_provider: string | null;
  cloud_resource_id: string | null;
  cloud_detected_at: string | null;
  cloud_attributes: Record<string, unknown> | null;
}

export interface MageritEnrichedInventoryResponse {
  project_id: string;
  assets: EnrichedMageritAsset[];
  counts: {
    total: number;
    cloud_verified: number;
    manual_only: number;
  };
}

export interface FamiliaBreakdown {
  familia: string;
  verified: number;
  total: number;
}

export interface ConformityCloudScoreResponse {
  project_id: string;
  project_category: string | null;
  measures_cloud_verified: number;
  measures_total_aplicable: number;
  score_percentage: number;
  per_familia_breakdown: FamiliaBreakdown[];
}

export const SEVERITY_VARIANT: Record<string, "danger" | "warning" | "info" | "default"> = {
  critical: "danger",
  high: "danger",
  medium: "warning",
  low: "info",
};

export const SEVERITY_LABEL: Record<string, string> = {
  critical: "Crítico",
  high: "Alto",
  medium: "Medio",
  low: "Bajo",
};

export const GAP_TYPE_LABEL: Record<string, string> = {
  structural: "Estructural",
  reinforcement: "Refuerzo",
  configuration: "Configuración",
  documental: "Documental",
};

export const STATUS_LABEL: Record<string, string> = {
  pending_oauth: "Pendiente OAuth",
  connected: "Conectado",
  syncing: "Sincronizando",
  sync_error: "Error sync",
  revoked: "Revocado",
  expired: "Expirado",
};

export const cloudConnectorsAdminApi = {
  // Catalog (cross-project)
  async getProvidersCatalog(): Promise<CloudProviderCatalogItem[]> {
    const res = await api<{ items: CloudProviderCatalogItem[] }>(
      `${BASE}/cloud-connectors/providers/catalog`,
    );
    return res.items;
  },
  async getSupportedMeasures(): Promise<string[]> {
    const res = await api<{ measures: string[] }>(
      `${BASE}/cloud-connectors/supported-measures`,
    );
    return res.measures;
  },

  // Connectors per project
  async listConnectors(projectId: string, includeRevoked = false): Promise<{
    items: CloudConnectorAdmin[];
    total: number;
  }> {
    return api(
      `${BASE}/admin/projects/${projectId}/cloud-connectors`
      + `?include_revoked=${includeRevoked}`,
    );
  },
  async linkConnector(
    projectId: string,
    body: {
      provider: string;
      m16_connector_config_id?: string | null;
      scopes?: string | null;
    },
  ): Promise<CloudConnectorAdmin> {
    return api(
      `${BASE}/admin/projects/${projectId}/cloud-connectors`,
      { method: "POST", json: body },
    );
  },
  async triggerSync(projectId: string, connectorId: string): Promise<{
    job_id: string;
    status: string;
    started_at: string;
    message: string;
  }> {
    return api(
      `${BASE}/admin/projects/${projectId}/cloud-connectors/${connectorId}/sync`,
      { method: "POST", json: {} },
    );
  },
  async revokeConnector(
    projectId: string,
    connectorId: string,
  ): Promise<CloudConnectorAdmin> {
    return api(
      `${BASE}/admin/projects/${projectId}/cloud-connectors/${connectorId}`,
      { method: "DELETE" },
    );
  },
  async listResources(
    projectId: string,
    connectorId: string,
    opts: { resourceType?: string; limit?: number } = {},
  ): Promise<{ items: CloudResource[]; total: number }> {
    const params = new URLSearchParams();
    if (opts.resourceType) params.set("resource_type", opts.resourceType);
    if (opts.limit) params.set("limit", String(opts.limit));
    const qs = params.toString();
    return api(
      `${BASE}/admin/projects/${projectId}/cloud-connectors/${connectorId}/resources`
      + (qs ? `?${qs}` : ""),
    );
  },
  async listSyncJobs(
    projectId: string,
    connectorId: string,
    limit = 50,
  ): Promise<{ items: CloudSyncJob[]; total: number }> {
    return api(
      `${BASE}/admin/projects/${projectId}/cloud-connectors/${connectorId}/sync-jobs?limit=${limit}`,
    );
  },

  // Gaps
  async listGaps(
    projectId: string,
    opts: { severities?: string[]; includeResolved?: boolean; limit?: number } = {},
  ): Promise<{ items: CloudGap[]; total: number }> {
    const params = new URLSearchParams();
    if (opts.severities) {
      for (const s of opts.severities) params.append("severity", s);
    }
    if (opts.includeResolved) params.set("include_resolved", "true");
    if (opts.limit) params.set("limit", String(opts.limit));
    const qs = params.toString();
    return api(
      `${BASE}/admin/projects/${projectId}/cloud-gaps`
      + (qs ? `?${qs}` : ""),
    );
  },
  async resolveGap(
    projectId: string,
    gapId: string,
    body: { resolution_note?: string | null; evidence_link_id?: string | null } = {},
  ): Promise<CloudGap> {
    return api(
      `${BASE}/admin/projects/${projectId}/cloud-gaps/${gapId}/resolve`,
      { method: "POST", json: body },
    );
  },

  // Diagnosis
  async runDiagnosis(
    projectId: string,
    body: { category_override?: string | null } = {},
  ): Promise<DiagnosisReport> {
    return api(
      `${BASE}/admin/projects/${projectId}/cloud-diagnosis/run`,
      { method: "POST", json: body },
    );
  },

  // Monitoring digest (sub-fase 1.D.X.VERIFY 2a)
  async getLatestDigest(projectId: string): Promise<DigestSnapshot | null> {
    return api(
      `${BASE}/admin/projects/${projectId}/cloud-monitoring/digest/latest`,
    );
  },
  async triggerDigest(projectId: string): Promise<DigestGenerateResponse> {
    return api(
      `${BASE}/admin/projects/${projectId}/cloud-monitoring/digest/generate`,
      { method: "POST", json: {} },
    );
  },

  // Discovery consolidation (sub-fase 1.D.J.B.M22)
  async getDiscoveryConsolidated(
    projectId: string,
  ): Promise<DiscoveryConsolidatedResponse> {
    return api(
      `${BASE}/admin/projects/${projectId}/cloud-integrations/discovery-consolidated`,
    );
  },

  // MAGERIT enriched inventory (sub-fase 1.D.J.B.M02)
  async getMageritEnrichedInventory(
    projectId: string,
    analysisId?: string,
  ): Promise<MageritEnrichedInventoryResponse> {
    const qs = analysisId ? `?analysis_id=${analysisId}` : "";
    return api(
      `${BASE}/admin/projects/${projectId}/cloud-integrations/magerit-enriched-inventory${qs}`,
    );
  },

  // Conformity cloud score aggregate (sub-fase 1.D.J.B.M27)
  async getConformityCloudScore(
    projectId: string,
  ): Promise<ConformityCloudScoreResponse> {
    return api(
      `${BASE}/admin/projects/${projectId}/cloud-integrations/conformity-cloud-score`,
    );
  },
};
