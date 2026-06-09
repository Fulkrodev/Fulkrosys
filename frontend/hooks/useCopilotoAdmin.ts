"use client";

/**
 * useCopilotoAdmin · sub-atom 1.C.D.B.3 v3.8.
 *
 * Wrapper tanstack-query mutation para Admin Copiloto chat.
 * Stub LLM endpoint · swap-in 1.D.B.2 zero refactor (schema idéntico).
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
