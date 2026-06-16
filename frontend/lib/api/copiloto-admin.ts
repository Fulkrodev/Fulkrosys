/**
 * Frontend API · Admin Copiloto · sub-atom 1.C.D.B.3 v3.8.
 *
 * NOTA (audit §3.1): el nombre "stub" es histórico. El endpoint
 * /api/v1/admin/copilot/chat ejecuta la persona LLM real cuando hay API
 * key; `is_stub` es un *runtime fallback flag* (true sólo sin API key o
 * error LLM, sirviendo entonces respuesta-plantilla determinista). NO es
 * un endpoint placeholder.
 */
import { api } from "@/lib/api";

export type CopilotActionId =
  | "que_hago"
  | "explica_paso"
  | "draft_email"
  | "briefing_reunion"
  | "chat_send";

export interface CopilotChatRequest {
  action_id: CopilotActionId;
  question?: string;
  project_id?: string;
  project_nombre?: string;
  step_template_id?: string;
  step_title?: string;
  fase_actual?: string;
  // 1.D.F.0.D · screen-aware context · admin tutor referencia botones específicos UI
  current_screen?: string;
  active_motor?: string;
}

export interface CopilotChatResponse {
  action_id: string;
  response_text: string;
  /** Runtime fallback flag: true = respuesta determinista de fallback
   * (sin API key / error LLM), NO un endpoint stub permanente. */
  is_stub: boolean;
  next_action_hint: string | null;
  citations: unknown[];
}

export async function postCopilotoChat(
  payload: CopilotChatRequest,
): Promise<CopilotChatResponse> {
  return api<CopilotChatResponse>("/api/v1/admin/copilot/chat", {
    method: "POST",
    json: payload,
  });
}
