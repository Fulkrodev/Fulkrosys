/**
 * Cliente de invocación genérica de agentes IA (admin).
 *
 * S15 fix campaña auditoría: el LeadDrawer del pipeline comercial simulaba la
 * invocación de A17/A2/A19 con setTimeout+toast. Este wrapper llama al endpoint
 * real POST /api/v1/agents/{id}/invoke (body genérico).
 */
import { api } from "@/lib/api";

export interface AgentInvokeBody {
  message: string;
  project_id?: string;
  params?: Record<string, unknown>;
  structured_output?: boolean;
  extra_context?: string;
}

export type AgentInvokeResult = Record<string, unknown>;

export function invokeAgent(
  agentId: number,
  body: AgentInvokeBody,
): Promise<AgentInvokeResult> {
  return api<AgentInvokeResult>(`/agents/${agentId}/invoke`, {
    method: "POST",
    json: body,
  });
}
