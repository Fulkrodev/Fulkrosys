"use client";

/**
 * API cliente cloud-connectors · sub-atom 1.D.X.I + Sesión 3B-2B.8 Phase 1C v3.12.
 *
 * Endpoints backend (m_cloud_connectors.api_cliente):
 *   GET  /api/v1/client-portal/cloud-connectors                     · list
 *   POST /api/v1/client-portal/cloud-connectors/connect/{provider}  · init flow
 *   GET  /api/v1/client-portal/cloud-connectors/providers/catalog   · catalog
 *   POST /api/v1/client-portal/cloud-connectors/{id}/request-disconnect
 *        Phase 1C · chat-mediated (ADR-014 sostained · NO actual revoke)
 *
 * R29 sostener · friendly_message viene server-side · NO duplicar logic.
 */

import { ClientApiError, clientApi } from "@/lib/client-portal-api";

export type CloudConnectorProvider =
  | "microsoft_365"
  | "google_workspace"
  | "azure"
  | "aws"
  | "github"
  | "manual_import";

export type CloudConnectorStatus =
  | "pending_oauth"
  | "connected"
  | "syncing"
  | "sync_error"
  | "revoked"
  | "expired";

export interface CloudConnectorProviderCatalogItem {
  provider: string;
  display_name: string;
  icon_emoji: string;
  requires_oauth: boolean;
  cliente_friendly_blurb: string;
}

export interface CloudConnectorPublicSummary {
  id: string; // connector_id propio · Sesión 3B-2B.8 Phase 1C
  provider: string;
  status: string;
  last_sync_at: string | null;
  resources_count: number;
  friendly_message: string;
}

export interface ConnectInitResponse {
  connector_id: string;
  provider: string;
  next_step: "oauth_redirect" | "manual_upload";
  m16_portal_init_path?: string;
  message: string;
}

// Sesión 3B-2B.8 Phase 1C · request-disconnect chat-mediated (ADR-014 sostained).
export interface DisconnectRequestResponse {
  thread_id: string;
  provider: string;
  connector_id: string;
  friendly_message: string;
}

// Sub-fase 1.D.X.VERIFY 2b · cliente digest view (FILTERED schema)
export interface ClientDigestView {
  has_snapshot: boolean;
  compliance_score: number;
  trend_label: "mejora" | "igual" | "baja" | "primer_resumen";
  trend_emoji: string;
  trend_color_hint: "verde" | "ambar" | "naranja_suave" | "neutral";
  last_review_at: string | null;
  changes_reviewed_count: number;
  consultant_name: string;
  summary_friendly: string;
}

export const cloudConnectorsClientApi = {
  async getCatalog(): Promise<CloudConnectorProviderCatalogItem[]> {
    const res = await clientApi<{ items: CloudConnectorProviderCatalogItem[] }>(
      "/client-portal/cloud-connectors/providers/catalog",
    );
    return res.items;
  },

  async list(): Promise<{ items: CloudConnectorPublicSummary[]; project_id: string }> {
    return clientApi<{ items: CloudConnectorPublicSummary[]; project_id: string }>(
      "/client-portal/cloud-connectors",
    );
  },

  async initConnect(provider: string): Promise<ConnectInitResponse> {
    return clientApi<ConnectInitResponse>(
      `/client-portal/cloud-connectors/connect/${provider}`,
      { method: "POST", json: {} },
    );
  },

  // Sesión 3B-2B.8 Phase 1C · chat-mediated disconnect request (ADR-014).
  // NO ejecuta revoke · backend audit_log emit + chat thread con Marcos.
  async requestDisconnect(
    connectorId: string,
    justification: string,
  ): Promise<DisconnectRequestResponse> {
    return clientApi<DisconnectRequestResponse>(
      `/client-portal/cloud-connectors/${connectorId}/request-disconnect`,
      { method: "POST", json: { justification } },
    );
  },

  // 1.D.X.VERIFY 2b · cliente digest visibility
  async getLatestDigest(): Promise<{ digest: ClientDigestView }> {
    return clientApi<{ digest: ClientDigestView }>(
      "/client-portal/cloud-monitoring/digest/latest",
    );
  },
};

export { ClientApiError };
