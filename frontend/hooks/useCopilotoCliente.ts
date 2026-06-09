"use client";

/**
 * useCopilotoCliente · sub-atom 1.C.D.C.3 v3.8.
 *
 * Wrapper tanstack-query mutation para Client Copiloto chat stub.
 * Schema IDÉNTICO admin (useCopilotoAdmin) · swap-in 1.D.B.1 zero refactor.
 *
 * R29 sostener · NO auto-polling · NO interval triggers ·
 * mutation user-driven (cliente clic explícito).
 */
import { useMutation } from "@tanstack/react-query";

import {
  postCopilotoClienteChat,
  type ClientCopilotChatRequest,
  type ClientCopilotChatResponse,
} from "@/lib/api/copiloto-cliente";

export function useCopilotoClienteChat() {
  return useMutation<ClientCopilotChatResponse, Error, ClientCopilotChatRequest>(
    {
      mutationFn: (payload) => postCopilotoClienteChat(payload),
    },
  );
}
