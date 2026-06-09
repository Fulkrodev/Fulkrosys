"use client";

/**
 * useMeetingSSE — fetch + ReadableStream consumer A18 SSE
 * (sub-bloque 7.B.6 FASE 7).
 *
 * EventSource API solo soporta GET. Backend POST /api/v1/agents/18/
 * meeting-update/stream con bloques A-F payload grande → fetch +
 * stream parser manual. Pattern coherente OpenAI streaming.
 *
 * Eventos SSE emitidos backend:
 *   event: progress  data: {"phase":"thinking","ts":...}
 *   event: progress  data: {"phase":"validating_schema"}
 *   event: insight   data: <JSON insight A18>
 *   event: done      data: {"latency_ms",...}
 *   event: error     data: {"error":"..."}
 *
 * Uso:
 *   const { events, status, start, stop } = useMeetingSSE();
 *   start({ blocks: {...}, meeting_id });
 */
import * as React from "react";

import { CSRF_HEADER } from "@/lib/constants";
import { getCsrfToken } from "@/lib/csrf";
import type { SSEEvent } from "@/lib/admin-meetings/schemas";

export type SSEStatus = "idle" | "connecting" | "streaming" | "done" | "error";

interface SSEStartPayload {
  blocks: Record<string, string>;
  blocks_filled?: string[];
  meeting_id?: string;
  project_id?: string;
}

export interface UseMeetingSSEResult {
  events: SSEEvent[];
  status: SSEStatus;
  errorMsg: string | null;
  start: (payload: SSEStartPayload) => Promise<void>;
  stop: () => void;
  reset: () => void;
}

/**
 * Parser SSE chunks: "event: <name>\ndata: <json>\n\n" → SSEEvent.
 *
 * Maneja fragmentación: chunks pueden venir con eventos parciales
 * o múltiples eventos concatenados. Usa buffer interno con split
 * en doble newline.
 */
function parseSSEChunks(buffer: string): {
  events: SSEEvent[];
  remaining: string;
} {
  const events: SSEEvent[] = [];
  const blocks = buffer.split("\n\n");
  // último bloque puede ser parcial → preservar en remaining
  const remaining = blocks.pop() ?? "";

  for (const block of blocks) {
    const trimmed = block.trim();
    if (!trimmed) continue;
    let eventName = "message";
    let dataStr = "";
    for (const line of trimmed.split("\n")) {
      if (line.startsWith("event:")) {
        eventName = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        dataStr += line.slice(5).trim();
      }
    }
    if (!dataStr) continue;
    try {
      const parsed = JSON.parse(dataStr);
      if (eventName === "progress") {
        events.push({
          type: "progress",
          phase: parsed.phase,
          ts: parsed.ts,
        });
      } else if (eventName === "insight") {
        events.push({ type: "insight", data: parsed });
      } else if (eventName === "done") {
        events.push({
          type: "done",
          latency_ms: parsed.latency_ms ?? 0,
          tokens_input: parsed.tokens_input,
          tokens_output: parsed.tokens_output,
          schema_valid: parsed.schema_valid,
          fallback_used: parsed.fallback_used,
        });
      } else if (eventName === "error") {
        events.push({ type: "error", error: parsed.error ?? "unknown" });
      }
    } catch {
      // skip malformed JSON
    }
  }
  return { events, remaining };
}

export function useMeetingSSE(): UseMeetingSSEResult {
  const [events, setEvents] = React.useState<SSEEvent[]>([]);
  const [status, setStatus] = React.useState<SSEStatus>("idle");
  const [errorMsg, setErrorMsg] = React.useState<string | null>(null);
  const abortRef = React.useRef<AbortController | null>(null);

  const reset = React.useCallback(() => {
    setEvents([]);
    setStatus("idle");
    setErrorMsg(null);
  }, []);

  const stop = React.useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setStatus((prev) => (prev === "streaming" || prev === "connecting" ? "idle" : prev));
  }, []);

  React.useEffect(() => {
    return () => {
      if (abortRef.current) {
        abortRef.current.abort();
        abortRef.current = null;
      }
    };
  }, []);

  const start = React.useCallback(
    async (payload: SSEStartPayload) => {
      reset();
      setStatus("connecting");
      const ctrl = new AbortController();
      abortRef.current = ctrl;

      try {
        const csrf = getCsrfToken();
        const headers: Record<string, string> = {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
        };
        if (csrf) headers[CSRF_HEADER] = csrf;

        const res = await fetch(
          "/api/v1/agents/18/meeting-update/stream",
          {
            method: "POST",
            credentials: "include",
            headers,
            body: JSON.stringify(payload),
            signal: ctrl.signal,
          },
        );
        if (!res.ok || !res.body) {
          throw new Error(`HTTP ${res.status} ${res.statusText}`);
        }
        setStatus("streaming");

        const reader = res.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const { events: parsed, remaining } = parseSSEChunks(buffer);
          buffer = remaining;
          if (parsed.length > 0) {
            setEvents((prev) => [...prev, ...parsed]);
            // Detectar event done para cerrar stream
            const doneEvt = parsed.find((e) => e.type === "done");
            const errEvt = parsed.find((e) => e.type === "error");
            if (errEvt) {
              setErrorMsg(errEvt.error);
              setStatus("error");
              return;
            }
            if (doneEvt) {
              setStatus("done");
            }
          }
        }
        // stream cerró sin done event → considerar done
        setStatus((prev) => (prev === "streaming" ? "done" : prev));
      } catch (e) {
        if ((e as Error).name === "AbortError") return;
        setErrorMsg(e instanceof Error ? e.message : "Error SSE stream");
        setStatus("error");
      } finally {
        abortRef.current = null;
      }
    },
    [reset],
  );

  return { events, status, errorMsg, start, stop, reset };
}
