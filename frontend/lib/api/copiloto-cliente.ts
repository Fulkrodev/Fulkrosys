/**
 * Frontend API · Client Copiloto stub · sub-atom 1.C.D.C.3 v3.8.
 *
 * Schema IDÉNTICO a 1.D.B.1 LLM real cliente · swap-in zero refactor UI.
 *
 * Consume POST /api/v1/client-portal/copilot/chat (require_client_user).
 * Usa clientApi wrapper (cookie auth + CSRF · OPS-044 sostener).
 */
import { clientApi } from "@/lib/client-portal-api";

export type ClientCopilotActionId =
  | "que_hago"
  | "porque_importa"
  | "explica_concepto"
  | "necesito_ayuda"
  | "chat_send";

export interface ClientCopilotChatRequest {
  action_id: ClientCopilotActionId;
  question?: string;
  project_id?: string;
  step_template_id?: string;
  step_title?: string;
  fase_actual?: string;
  concepto?: string;
}

export interface ClientCopilotChatResponse {
  action_id: string;
  response_text: string;
  is_stub: boolean;
  next_action_hint: string | null;
  citations: unknown[];
}

export async function postCopilotoClienteChat(
  payload: ClientCopilotChatRequest,
): Promise<ClientCopilotChatResponse> {
  return clientApi<ClientCopilotChatResponse>("/client-portal/copilot/chat", {
    method: "POST",
    json: payload,
  });
}
