"use client";

/**
 * API cliente AI Act art.50 transparency · sub-atom 1.E.1.B.2.
 *
 * Endpoint backend (m_observability/transparency_api.client_router):
 *   GET /api/v1/client-portal/transparency/log?days=180&limit=200
 *
 * Cliente solo ve eventos de SU client_id (enforced server-side via
 * require_client_user + client_id filter). NUNCA cross-cliente leak.
 *
 * R29 firmísimo · response NO incluye llm_provider/llm_model/metadata
 * technical · solo friendly fields cliente-readable.
 */

import { clientApi } from "@/lib/client-portal-api";

export type AIActEventType =
  | "deliverable_generated"
  | "proposal_drafted"
  | "contract_clause_generated"
  | "diagnostic_performed"
  | "gap_analysis"
  | "risk_assessment"
  | "policy_drafted"
  | "copilot_interaction";

export interface ClientTransparencyEvent {
  id: string;
  event_type: AIActEventType;
  agent_name: string;
  artifact_type: string | null;
  artifact_id: string | null;
  purpose: string;
  created_at: string;
}

export interface ClientTransparencyLogResponse {
  client_id: string;
  days: number;
  total: number;
  items: ClientTransparencyEvent[];
}

export async function getClientTransparencyLog(
  days: number = 180,
  limit: number = 200,
): Promise<ClientTransparencyLogResponse> {
  return clientApi<ClientTransparencyLogResponse>(
    `/client-portal/transparency/log?days=${days}&limit=${limit}`,
  );
}

// Labels friendly cliente-facing
export const EVENT_TYPE_LABEL: Record<AIActEventType, string> = {
  deliverable_generated: "Documento generado",
  proposal_drafted: "Propuesta redactada",
  contract_clause_generated: "Cláusula contractual",
  diagnostic_performed: "Diagnóstico realizado",
  gap_analysis: "Análisis de brechas",
  risk_assessment: "Análisis de riesgos",
  policy_drafted: "Política redactada",
  copilot_interaction: "Asistente conversacional",
};
