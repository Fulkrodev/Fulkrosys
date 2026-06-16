"use client";

/**
 * useCopilotoAdmin · sub-atom 1.C.D.B.3 v3.8.
 *
 * Wrapper tanstack-query mutation para Admin Copiloto chat.
 *
 * NOTA (audit §3.1): el path vivo ejecuta la persona LLM real. El término
 * "stub" en el naming es histórico; `is_stub` en la respuesta es un runtime
 * fallback flag (true sólo sin API key o error LLM), NO un endpoint
 * placeholder.
 */
import { useMutation } from "@tanstack/react-query";

import {
  postCopilotoChat,
  type CopilotChatRequest,
  type CopilotChatResponse,
} from "@/lib/api/copiloto-admin";

export function useCopilotoChat() {
  return useMutation<CopilotChatResponse, Error, CopilotChatRequest>({
    mutationFn: (payload) => postCopilotoChat(payload),
  });
}
