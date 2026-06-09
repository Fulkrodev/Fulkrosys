"use client";

import * as React from "react";

import {
  chatWithCopilotStream,
  type CopilotCitationEvent,
  type CopilotPageContext,
  rawCitationsToCitations,
} from "@/lib/api/copilot";
import { useCopilotStore } from "@/lib/stores/copilot-store";
import type { Citation, CopilotMessage } from "@/lib/sprint4-types";

/**
 * Client for the copiloto (Agent 14).
 *
 * Streams tokens from POST /api/v1/copilot/chat/stream (SSE). Each delta event
 * appends to the assistant message; citation events push enriched chips
 * (with chunk preview) progressively; the done event finalizes citations
 * and copies confidence/corpus_gap to the message metadata.
 */
function greetingMessage(): CopilotMessage {
  return {
    id: "msg-greet",
    role: "assistant",
    content:
      "Hola Marcos. Soy tu copiloto ENS. Preguntame por cualquier obligacion, evidencia o hito del proyecto.",
    createdAt: new Date().toISOString(),
  };
}

function citationEventToCitation(
  event: CopilotCitationEvent,
  index: number,
): Citation {
  return {
    id: `cit-${event.norm}-${index}`,
    framework: event.raw,
    article: event.measure ?? "",
    excerpt: event.raw,
    chunk_id: event.chunk_id ?? undefined,
    measure: event.measure ?? undefined,
    preview: event.preview ?? undefined,
  };
}

export function useCopilot(projectId?: string) {
  const panelContext = useCopilotStore((s) => s.panelContext);
  const [messages, setMessages] = React.useState<CopilotMessage[]>(() => [
    greetingMessage(),
  ]);
  const [isStreaming, setIsStreaming] = React.useState(false);
  const abortRef = React.useRef<AbortController | null>(null);

  const effectiveProjectId =
    projectId ?? panelContext.projectId ?? undefined;
  const apiPageContext: CopilotPageContext | undefined = React.useMemo(() => {
    if (
      !panelContext.url &&
      !panelContext.clientId &&
      !panelContext.activeMotor &&
      !panelContext.projectPhase
    ) {
      return undefined;
    }
    return {
      url: panelContext.url,
      clientId: panelContext.clientId,
      activeMotor: panelContext.activeMotor,
      projectPhase: panelContext.projectPhase,
    };
  }, [panelContext]);

  async function sendMessage(content: string) {
    if (!content.trim() || isStreaming) return;
    const userMsg: CopilotMessage = {
      id: `msg-${Date.now()}-u`,
      role: "user",
      content: content.trim(),
      createdAt: new Date().toISOString(),
    };
    const assistantId = `msg-${Date.now()}-a`;
    const assistant: CopilotMessage = {
      id: assistantId,
      role: "assistant",
      content: "",
      citations: [],
      actions: [],
      createdAt: new Date().toISOString(),
      streaming: true,
    };
    setMessages((prev) => [...prev, userMsg, assistant]);
    setIsStreaming(true);
    abortRef.current = new AbortController();

    const seenCitations = new Set<string>();
    let citationOrder = 0;

    try {
      for await (const event of chatWithCopilotStream(
        {
          question: userMsg.content,
          projectId: effectiveProjectId,
          pageContext: apiPageContext,
        },
        abortRef.current.signal,
      )) {
        if (event.type === "delta") {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, content: (m.content ?? "") + event.text }
                : m,
            ),
          );
        } else if (event.type === "citation") {
          if (seenCitations.has(event.data.norm)) continue;
          seenCitations.add(event.data.norm);
          const citation = citationEventToCitation(event.data, citationOrder++);
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, citations: [...(m.citations ?? []), citation] }
                : m,
            ),
          );
        } else if (event.type === "done") {
          const done = event.data;
          setMessages((prev) =>
            prev.map((m) => {
              if (m.id !== assistantId) return m;
              const finalCitations =
                (m.citations?.length ?? 0) > 0
                  ? m.citations!
                  : rawCitationsToCitations(
                      done.citations_found,
                      done.chunk_ids_used,
                    );
              return {
                ...m,
                content: done.answer,
                streaming: false,
                citations: finalCitations,
                actions: [],
                metadata: {
                  confidence: done.confidence,
                  corpus_gap: done.corpus_gap,
                  chunks_used: done.chunks_used,
                  model_used: done.model_used,
                },
              };
            }),
          );
        } else if (event.type === "error") {
          throw new Error(event.error);
        }
      }
    } catch (err) {
      const message =
        err instanceof DOMException && err.name === "AbortError"
          ? "Consulta cancelada."
          : `No he podido consultar el copiloto (${
              err instanceof Error ? err.message : "error"
            }).`;
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, streaming: false, content: m.content || message }
            : m,
        ),
      );
    } finally {
      setIsStreaming(false);
      abortRef.current = null;
    }
  }

  function cancel() {
    abortRef.current?.abort();
  }

  function clear() {
    setMessages([greetingMessage()]);
  }

  return { messages, isStreaming, sendMessage, cancel, clear };
}
