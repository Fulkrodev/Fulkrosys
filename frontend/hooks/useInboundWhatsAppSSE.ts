"use client";

/**
 * useInboundWhatsAppSSE · Sprint Polish block 2.D.
 *
 * Subscribes to the existing per-thread SSE endpoint and yields each new
 * `WhatsAppMessage` parsed from the `data:` frames. Backend (sse_endpoint.py)
 * emits one `data: <json>` per new message plus `: keepalive` comments
 * (ignored by the EventSource spec).
 *
 * Endpoints (already implemented in MB-8):
 *   - admin  → /api/v1/admin/whatsapp/threads/{threadId}/sse
 *   - client → /api/v1/client-portal/whatsapp/thread/{threadId}/sse
 *
 * Auto-reconnect is handled by the browser's EventSource implementation.
 * The hook closes the stream on threadId change or unmount.
 */
import { useEffect, useState } from "react";

import type { WhatsAppMessage } from "@/lib/api/whatsapp";


export interface UseInboundWhatsAppSSEOptions {
  threadId: string | null;
  mode: "admin" | "client";
  enabled?: boolean;
}


export interface UseInboundWhatsAppSSEResult {
  latestMessage: WhatsAppMessage | null;
  connected: boolean;
  error: string | null;
}


function buildSseUrl(threadId: string, mode: "admin" | "client"): string {
  if (mode === "admin") {
    return `/api/v1/admin/whatsapp/threads/${threadId}/sse`;
  }
  return `/api/v1/client-portal/whatsapp/thread/${threadId}/sse`;
}


export function useInboundWhatsAppSSE({
  threadId,
  mode,
  enabled = true,
}: UseInboundWhatsAppSSEOptions): UseInboundWhatsAppSSEResult {
  const [latestMessage, setLatestMessage] = useState<WhatsAppMessage | null>(
    null,
  );
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled || !threadId) {
      setConnected(false);
      return;
    }
    if (typeof window === "undefined" || typeof EventSource === "undefined") {
      return;
    }

    const url = buildSseUrl(threadId, mode);
    const source = new EventSource(url, { withCredentials: true });

    const handleOpen = () => {
      setConnected(true);
      setError(null);
    };

    const handleMessage = (event: MessageEvent<string>) => {
      try {
        const payload = JSON.parse(event.data) as WhatsAppMessage;
        setLatestMessage(payload);
      } catch {
        setError("Frame SSE inválido");
      }
    };

    const handleError = () => {
      setConnected(false);
      setError("Conexión SSE interrumpida (reintentando)");
    };

    source.addEventListener("open", handleOpen);
    source.addEventListener("message", handleMessage);
    source.addEventListener("error", handleError);

    return () => {
      source.removeEventListener("open", handleOpen);
      source.removeEventListener("message", handleMessage);
      source.removeEventListener("error", handleError);
      source.close();
      setConnected(false);
    };
  }, [threadId, mode, enabled]);

  return { latestMessage, connected, error };
}
