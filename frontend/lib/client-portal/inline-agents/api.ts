/**
 * Inline agents API client · MB-7 atom 7.4-bis.
 */
import { clientApi } from "@/lib/client-portal-api";


export type InlineAgentSlug =
  | "a04_redactor_summary"
  | "a06_contratos_analysis"
  | "a11_auditor_virtual_check"
  | "a12_coach_suggestion"
  | "a18_reunion_summary"
  | "a19_propuestas_justify"
  | "a20_negociacion_counter"
  | "a21_discrepancias_scan"
  | "a27_clasificador_upload"
  | "a31_enriquecedor_dda";


export interface InlineAgentInvokeBody {
  user_message: string;
  extra_context?: string;
  page_url?: string;
  structured_output?: boolean;
}


export interface InlineAgentResponse {
  agent_id: number;
  agent_name: string;
  response: string;
  tokens_input: number;
  tokens_output: number;
  latency_ms: number;
  citations: string[];
}


export interface QuickSuggestion {
  available: boolean;
  cached?: boolean;
  reason?: string;
  agent_id?: number;
  agent_name?: string;
  response?: string;
  citations?: string[];
}


export async function invokeInlineAgent(
  slug: InlineAgentSlug,
  body: InlineAgentInvokeBody,
): Promise<InlineAgentResponse> {
  return clientApi<InlineAgentResponse>(
    `/client-portal/inline-agents/${slug}/invoke`,
    {
      method: "POST",
      json: body,
    },
  );
}


export async function fetchQuickSuggestion(
  slug: InlineAgentSlug,
  pageUrl?: string,
): Promise<QuickSuggestion> {
  const qs = pageUrl ? `?page_url=${encodeURIComponent(pageUrl)}` : "";
  return clientApi<QuickSuggestion>(
    `/client-portal/inline-agents/${slug}/quick-suggestion${qs}`,
  );
}


export interface InlineAgentListItem {
  slug: InlineAgentSlug;
  agent_id: number;
  min_tier: string;
  available: boolean;
}


export interface InlineAgentList {
  tier: string | null;
  agents: InlineAgentListItem[];
}


export async function listInlineAgents(): Promise<InlineAgentList> {
  return clientApi<InlineAgentList>("/client-portal/inline-agents");
}
